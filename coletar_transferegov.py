#!/usr/bin/env python3
"""
coletar_transferegov.py
=======================
Transferências da União a municípios SEM chave de API, pelos dados abertos do
TransfereGov (04/09/2026, caminho escolhido pela editoria depois de o Portal da
Transparência recusar a chave nos endpoints de transferências — HTTP 403).

Fontes (todas sondadas com rede real antes de escrever este arquivo):
  • Módulo Discricionárias e Legais — CSVs diários em
    https://repositorio.dados.gov.br/seges/detru/  (siconv_proposta.csv.zip,
    siconv_convenio.csv.zip; data da carga em data_carga_siconv.txt).
  • API PostgREST pública de Fundo a Fundo —
    https://api.transferegov.gestao.gov.br/fundoafundo/programa?ano_programa=eq.2026

O que produz (peso zero no MARÉ; camada de financiamento, §7.8/§10-bis):
  • data/financiamento/serie_nacional.json — série SEMANAL 2026 da rota r5
    (voluntárias: convênios e contratos de repasse a municípios, por data de
    assinatura), com `total` = soma das rotas coletadas (só r5 por enquanto; as
    demais ficam em 0 com status declarado).
  • data/financiamento/por_uf.json — r5.valor_2026 por UF (assinado em 2026).
  • data/transferegov_el_nino_revisar.json — instrumentos 2025–2026 cujo objeto
    cita defesa civil/desastre/estiagem/etc.: FILA DE REVISÃO HUMANA, nunca
    publicada como "recurso do El Niño" sem leitura (regra do projeto).
  • data/financiamento/consultas.json — proveniência (URL, hash, nº de linhas).

Sem rede (sandbox) nada quebra: lacuna declarada, arquivos intocados.
  python coletar_transferegov.py --autoteste   # prova parsers e agregações sem rede
"""
import csv, hashlib, io, json, re, sys, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from coletores_base import ler, gravar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
FIN = RAIZ / "data" / "financiamento"
REPO = "https://repositorio.dados.gov.br/seges/detru/"
API_FAF = "https://api.transferegov.gestao.gov.br/fundoafundo/programa?ano_programa=eq.2026&limit=500"
UA = {"User-Agent": "MonitorElNinoBrasil/3.0 (coletor TransfereGov; dados abertos)"}
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]

# Objeto que fala do ciclo: mesmas famílias de risco do teste do objeto (§5.2.1) + defesa civil.
PAD_EL_NINO = re.compile(r"defesa civil|desastre|calamidade|emerg[êe]nci|estiagem|\bseca\b|enchente|inunda[çc]|alagamento|"
                         r"deslizamento|el ni[ñn]o|conting[êe]ncia|cisterna|abastecimento de [áa]gua|inc[êe]ndio|queimad", re.I)


def _baixar(url: str, timeout: int = 900) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def _csv_do_zip(bruto: bytes):
    """Itera as linhas (dict) do CSV dentro do zip do TransfereGov (latin-1, ';', BOM no cabeçalho)."""
    z = zipfile.ZipFile(io.BytesIO(bruto))
    with z.open(z.namelist()[0]) as f:
        txt = io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline="")
        rd = csv.DictReader(txt, delimiter=";")
        rd.fieldnames = [c.replace("\ufeff", "").replace("ï»¿", "").strip() for c in rd.fieldnames]
        for row in rd:
            yield row


# ----------------------------- funções puras (testadas) -----------------------------
def numero(v) -> float:
    """'1134,75' → 1134.75; '' → 0.0."""
    try:
        return float(str(v or "0").replace(".", "").replace(",", ".")) if "," in str(v) else float(str(v or "0") or 0)
    except ValueError:
        return 0.0


def data_br(v: str):
    """'31/12/2019' → date; inválida → None."""
    try:
        return datetime.strptime(str(v).strip(), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def semana_de(d: date) -> str:
    """Segunda-feira da semana ISO, em ISO 8601 (chave da série semanal)."""
    return (d - timedelta(days=d.weekday())).isoformat()


def filtrar_propostas(linhas, ano_min: int = 2025) -> dict:
    """ID_PROPOSTA → {ibge, uf, municipio, orgao, objeto, el_nino, ano} para propostas de MUNICÍPIOS
    a partir de `ano_min`. Só municipal (natureza jurídica), porque a série é 'União → municípios'."""
    out = {}
    for r in linhas:
        try:
            ano = int(r.get("ANO_PROP") or 0)
        except ValueError:
            continue
        if ano < ano_min or "Municipal" not in (r.get("NATUREZA_JURIDICA") or ""):
            continue
        ibge = (r.get("COD_MUNIC_IBGE") or "").strip()
        if not ibge.isdigit():
            continue
        objeto = (r.get("OBJETO_PROPOSTA") or "").strip()
        out[r.get("ID_PROPOSTA")] = {"ibge": ibge.zfill(7), "uf": (r.get("UF_PROPONENTE") or "").strip().upper(),
                                     "municipio": (r.get("MUNIC_PROPONENTE") or "").strip(), "orgao": (r.get("DESC_ORGAO_SUP") or "").strip(),
                                     "objeto": objeto[:400], "el_nino": bool(PAD_EL_NINO.search(objeto)), "ano": ano,
                                     "modalidade": (r.get("MODALIDADE") or "").strip()}
    return out


def cruzar_convenios(linhas, propostas: dict, ano_serie: int = 2026) -> tuple:
    """Devolve (semanas, por_uf, itens_el_nino) a partir dos convênios cujas propostas estão em `propostas`.
    semanas: {segunda_iso: valor_repasse assinado naquela semana de `ano_serie`} — só instrumentos assinados.
    por_uf:  {UF: valor_repasse assinado em `ano_serie`}.
    itens_el_nino: lista para revisão humana (objeto cita o ciclo), qualquer ano das propostas filtradas."""
    semanas = defaultdict(float); por_uf = defaultdict(float); itens = []
    for r in linhas:
        p = propostas.get(r.get("ID_PROPOSTA"))
        if not p:
            continue
        assinatura = data_br(r.get("DIA_ASSIN_CONV"))
        repasse = numero(r.get("VL_REPASSE_CONV")); desembolsado = numero(r.get("VL_DESEMBOLSADO_CONV"))
        if assinatura and assinatura.year == ano_serie:
            semanas[semana_de(assinatura)] += repasse
            por_uf[p["uf"]] += repasse
        if p["el_nino"]:
            itens.append({"nr_convenio": r.get("NR_CONVENIO"), "ibge": p["ibge"], "uf": p["uf"], "municipio": p["municipio"],
                          "orgao": p["orgao"], "modalidade": p["modalidade"], "objeto": p["objeto"],
                          "assinatura": assinatura.isoformat() if assinatura else None, "situacao": (r.get("SIT_CONVENIO") or "").strip(),
                          "vl_repasse": repasse, "vl_desembolsado": desembolsado})
    return dict(semanas), dict(por_uf), itens


def montar_serie(semanas: dict, rotas_ids: list, ano: int = 2026) -> list:
    """Uma linha por semana do ano (segunda a segunda) com todas as rotas: r5 coletada, demais 0; total = soma."""
    out = []
    d = date(ano, 1, 1); d -= timedelta(days=d.weekday())
    hoje = date.today()
    while d.year <= ano and d <= hoje:
        linha = {"semana": d.isoformat()}
        for rid in rotas_ids:
            linha[rid] = round(semanas.get(d.isoformat(), 0.0), 2) if rid == "r5" else 0
        linha["total"] = round(sum(float(linha[rid]) for rid in rotas_ids), 2)
        out.append(linha); d += timedelta(days=7)
    return out


def programas_faf(dados) -> list:
    """Programas fundo a fundo 2026 que citam defesa civil/desastre (vocabulário da fonte)."""
    out = []
    for p in dados or []:
        nome = (p.get("nome_programa") or "").strip()
        if PAD_EL_NINO.search(nome + " " + (p.get("objetivo_programa") or "")):
            out.append({"codigo": p.get("codigo_programa"), "nome": nome, "orgao": p.get("nome_orgao_superior_programa"), "ano": p.get("ano_programa")})
    return out


# ------------------------------------ coleta ------------------------------------
def coletar() -> int:
    hoje = date.today().strftime("%d/%m/%Y")
    consultas = ler("financiamento/consultas.json", {"_governanca": "", "consultas": []}) or {"consultas": []}
    try:
        carga = _baixar(REPO + "data_carga_siconv.txt", 60).decode("utf-8", "replace").replace("\ufeff", "").strip()[:19]
        bp = _baixar(REPO + "siconv_proposta.csv.zip"); bc = _baixar(REPO + "siconv_convenio.csv.zip")
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("TransfereGov — CSVs Discricionárias e Legais", f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[REPO])
        print(f"transferegov: sem rede/arquivo ({type(e).__name__}) — lacuna declarada, nada alterado"); return 0
    propostas = filtrar_propostas(_csv_do_zip(bp), 2025)
    semanas, por_uf_r5, itens = cruzar_convenios(_csv_do_zip(bc), propostas, 2026)
    for nome, b in (("siconv_proposta.csv.zip", bp), ("siconv_convenio.csv.zip", bc)):
        consultas["consultas"].append({"endpoint": REPO + nome, "params": {"carga": carga}, "data": hoje,
                                       "hash": hashlib.sha256(b).hexdigest(), "bytes": len(b), "fonte": "TransfereGov — Dados Abertos (sem chave)"})
    # série nacional (rota r5)
    rotas = ler("financiamento/rotas.json", {}) or {}
    ids = [r["id"] for r in rotas.get("rotas", [])] or ["r1","r2","r3","r4","r5","r6","r7","rE"]
    serie = ler("financiamento/serie_nacional.json", {}) or {}
    serie.update({"semanas": montar_serie(semanas, ids, 2026), "status": "coletado", "corte": hoje,
                  "fonte": "TransfereGov — Dados Abertos, módulo Discricionárias e Legais (convênios e contratos de repasse a municípios, por data de assinatura)",
                  "carga_da_fonte": carga, "rotas_coletadas": ["r5"],
                  "nota": "r5 = valor de repasse dos instrumentos assinados na semana; demais rotas em 0 até coleta própria (r2 fundo a fundo, r6 especiais)."})
    gravar("financiamento/serie_nacional.json", serie)
    # por UF
    puf = ler("financiamento/por_uf.json", {}) or {}
    for uf in UFS:
        u = puf.setdefault("uf", {}).setdefault(uf, {}); rr = u.setdefault("rotas", {})
        rr["r5"] = {"valor_2026": round(por_uf_r5.get(uf, 0.0), 2), "status": "coletado", "fonte": "TransfereGov — Dados Abertos", "carga_da_fonte": carga}
    puf["corte"] = hoje; gravar("financiamento/por_uf.json", puf)
    # fila de revisão
    gravar("transferegov_el_nino_revisar.json", {
        "_governanca": ("Instrumentos 2025–2026 (convênios/contratos de repasse a municípios) cujo OBJETO cita o ciclo "
                        "(defesa civil, desastre, estiagem, enchente, contingência…). FILA DE REVISÃO HUMANA: nada aqui é "
                        "publicado como 'recurso do El Niño' sem leitura; a palavra-chave só ordena. Fonte: TransfereGov — "
                        f"Dados Abertos, carga {carga}."),
        "gerado_em": hoje, "carga_da_fonte": carga, "n": len(itens), "itens": sorted(itens, key=lambda x: x.get("assinatura") or "", reverse=True)})
    # fundo a fundo 2026 (API sem chave)
    try:
        faf = json.loads(_baixar(API_FAF, 120).decode("utf-8", "replace"))
        rel = programas_faf(faf)
        consultas["consultas"].append({"endpoint": API_FAF, "params": {}, "data": hoje, "hash": hashlib.sha256(json.dumps(faf, sort_keys=True).encode()).hexdigest(),
                                       "n": len(faf), "fonte": "TransfereGov — API Fundo a Fundo (sem chave)"})
        gravar("financiamento/programas_faf_2026.json", {"_governanca": "Programas fundo a fundo de 2026 (API pública do TransfereGov) cujo nome/objetivo cita defesa civil ou desastre. Vocabulário da fonte.", "gerado_em": hoje, "total_programas_2026": len(faf), "relevantes": rel})
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("TransfereGov — API fundo a fundo", f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[API_FAF])
    gravar("financiamento/consultas.json", consultas)
    log_busca("DOU", 1, [REPO, API_FAF], "registro", nivel="nacional", n_resultados=len(itens),
              resultados=f"TransfereGov: {len(propostas):,} propostas municipais ≥2025; r5 2026 em {sum(1 for v in semanas.values() if v)} semanas; {len(itens)} instrumentos com objeto do ciclo (fila de revisão); carga {carga}")
    print(f"transferegov: propostas {len(propostas):,} | semanas com valor {sum(1 for v in semanas.values() if v)} | fila El Niño {len(itens)} | carga {carga}")
    return 0


def autoteste() -> int:
    P = [{"ID_PROPOSTA": "1", "ANO_PROP": "2026", "NATUREZA_JURIDICA": "Administração Pública Municipal", "COD_MUNIC_IBGE": "3505401", "UF_PROPONENTE": "SP",
          "MUNIC_PROPONENTE": "BARRA DO TURVO", "DESC_ORGAO_SUP": "MIDR", "OBJETO_PROPOSTA": "Aquisição de cisternas para enfrentamento da estiagem", "MODALIDADE": "CONVENIO"},
         {"ID_PROPOSTA": "2", "ANO_PROP": "2026", "NATUREZA_JURIDICA": "Administração Pública Municipal", "COD_MUNIC_IBGE": "4115457", "UF_PROPONENTE": "PR",
          "MUNIC_PROPONENTE": "MARQUINHO", "DESC_ORGAO_SUP": "TURISMO", "OBJETO_PROPOSTA": "Pavimentação de via urbana", "MODALIDADE": "CONTRATO DE REPASSE"},
         {"ID_PROPOSTA": "3", "ANO_PROP": "2019", "NATUREZA_JURIDICA": "Administração Pública Municipal", "COD_MUNIC_IBGE": "3505401", "UF_PROPONENTE": "SP", "OBJETO_PROPOSTA": "defesa civil"},
         {"ID_PROPOSTA": "4", "ANO_PROP": "2026", "NATUREZA_JURIDICA": "Administração Pública Estadual", "COD_MUNIC_IBGE": "3505401", "UF_PROPONENTE": "SP", "OBJETO_PROPOSTA": "defesa civil"}]
    C = [{"NR_CONVENIO": "100", "ID_PROPOSTA": "1", "DIA_ASSIN_CONV": "10/08/2026", "VL_REPASSE_CONV": "490038", "VL_DESEMBOLSADO_CONV": "1134,75", "SIT_CONVENIO": "Em execução"},
         {"NR_CONVENIO": "101", "ID_PROPOSTA": "2", "DIA_ASSIN_CONV": "12/08/2026", "VL_REPASSE_CONV": "100000", "VL_DESEMBOLSADO_CONV": "0", "SIT_CONVENIO": "Em execução"},
         {"NR_CONVENIO": "102", "ID_PROPOSTA": "1", "DIA_ASSIN_CONV": "31/12/2025", "VL_REPASSE_CONV": "5", "VL_DESEMBOLSADO_CONV": "0", "SIT_CONVENIO": "Concluído"},
         {"NR_CONVENIO": "103", "ID_PROPOSTA": "9", "DIA_ASSIN_CONV": "12/08/2026", "VL_REPASSE_CONV": "999", "VL_DESEMBOLSADO_CONV": "0"}]
    def t1():  # filtra: municipal, ≥2025, IBGE válido; marca objeto do ciclo
        p = filtrar_propostas(P); return set(p) == {"1", "2"} and p["1"]["el_nino"] and not p["2"]["el_nino"] and p["1"]["ibge"] == "3505401"
    def t2():  # semana: segunda-feira ISO; 10/08/2026 e 12/08/2026 caem na mesma semana (10/08)
        return semana_de(date(2026, 8, 12)) == "2026-08-10" and semana_de(date(2026, 8, 10)) == "2026-08-10"
    def t3():  # cruzamento: soma por semana e por UF só do ano da série; proposta desconhecida ignorada
        s, u, it = cruzar_convenios(C, filtrar_propostas(P)); return s == {"2026-08-10": 590038.0} and u == {"SP": 490038.0, "PR": 100000.0}
    def t4():  # fila El Niño: só objetos do ciclo, inclusive de outros anos; valores com vírgula lidos
        _, _, it = cruzar_convenios(C, filtrar_propostas(P)); return {i["nr_convenio"] for i in it} == {"100", "102"} and any(i["vl_desembolsado"] == 1134.75 for i in it)
    def t5():  # série: total = soma das rotas (reconciliação do portão), r5 preenchida, demais 0
        lin = montar_serie({"2026-08-10": 590038.0}, ["r1", "r5", "rE"]); s = next(l for l in lin if l["semana"] == "2026-08-10")
        return s["r5"] == 590038.0 and s["r1"] == 0 and s["total"] == 590038.0 and all(l["total"] == sum(float(l[r]) for r in ("r1", "r5", "rE")) for l in lin)
    def t6():  # negativo: números e datas malformados não quebram
        return numero("abc") == 0.0 and data_br("31/02/2026") is None and data_br(None) is None and filtrar_propostas([{"ANO_PROP": "x"}]) == {}
    def t7():  # fundo a fundo: só programas que citam o ciclo
        f = programas_faf([{"nome_programa": "Apoio à Defesa Civil 2026", "ano_programa": 2026}, {"nome_programa": "Segurança Pública", "objetivo_programa": "x"}])
        return len(f) == 1 and f[0]["nome"].startswith("Apoio")
    return rodar_autoteste({"propostas: municipal, ≥2025, objeto do ciclo marcado": t1, "semana ISO (segunda-feira)": t2,
                            "cruzamento: soma por semana/UF só do ano da série": t3, "fila El Niño: só objeto do ciclo, valores com vírgula": t4,
                            "série: total = soma das rotas (reconciliação)": t5, "negativo: malformados não quebram": t6,
                            "fundo a fundo: só programas do ciclo": t7})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
