#!/usr/bin/env python3
"""
coletar_doe.py
==============
Diários Oficiais dos ESTADOS (27 DOEs): homologações estaduais de decretos
municipais → `data/atos_resposta.json` (resposta, peso zero, campo
`decreto_estadual_homologacao`); atos estaduais sobre o ciclo → `data/pistas_doe.json`
(fila de pista: promover a registro é humano, §3.2). Confere nível "estadual" no
livro de fontes consultadas para os municípios da UF quando o DOE da UF foi lido
com sucesso no período.

Cobertura (§15, "a verificar por UF"): `data/fontes_doe.json` declara, por UF,
`{"adaptador": "querido_diario"|"direto"|null, "url": ..., "status": ...}`.
UF sem adaptador confirmado → lacuna declarada (nunca inferida). Em 02/09/2026
todas as 27 nascem `a_verificar`; a Action preenche o status ao tentar.

USO
  python coletar_doe.py --autoteste
  python coletar_doe.py --regiao NE            # lote por região (§13: NE, N, CO, SE, S)
  python coletar_doe.py --uf SC --desde 2026-06-29
"""
import json, re, sys, urllib.parse
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            ler, gravar, rodar_autoteste, eh_suspensao_defeso)

REGIOES = {"N": "AC AM AP PA RO RR TO", "NE": "AL BA CE MA PB PE PI RN SE", "CO": "DF GO MS MT",
           "SE": "ES MG RJ SP", "S": "PR RS SC"}
TERMOS = ["homologa a situação de emergência", "homologa o decreto", "situação de emergência",
          "estado de calamidade pública", "plano de contingência El Niño", "plano de contingência"]
QD_API = "https://queridodiario.ok.org.br/api/gazettes?{params}"
PADRAO_HOMOLOGA = re.compile(r"homologa\s+(?:o\s+)?(?:decreto\s+(?:municipal\s+)?n[ºo°\.]?\s*([\d\.\/-]+))?[^.]{0,160}?munic[íi]pio de ([^,;\.\-–]+?)(?:\s*[-–]\s*([A-Z]{2}))?[\.,;]", re.I)


def fontes_doe_padrao():
    return {"_governanca": "Cobertura dos 27 DOEs (v2.2.4, §4.2). 'a_verificar' = adaptador não confirmado; "
                           "a Action registra o resultado da tentativa. Nunca inferir cobertura.",
            "ufs": {uf: {"adaptador": None, "url": None, "status": "a_verificar", "ultima_tentativa": None}
                    for r in REGIOES.values() for uf in r.split()}}


def parse_querido_diario(dados: dict) -> list:
    """Normaliza a resposta da API do Querido Diário em itens {data, url, trechos, territorio}."""
    out = []
    for g in (dados or {}).get("gazettes", []):
        out.append({"data": g.get("date", ""), "url": g.get("url") or g.get("txt_url", ""),
                    "trechos": [t for t in g.get("excerpts", []) if t], "territorio": str(g.get("territory_id", ""))})
    return out


def extrair_homologacoes(itens: list, uf: str) -> list:
    """Homologações com município identificável; número do decreto pode faltar (vai como pista)."""
    saida = []
    for it in itens:
        for tr in it["trechos"]:
            for numero, municipio, uf_txt in PADRAO_HOMOLOGA.findall(tr):
                saida.append({"municipio": municipio.strip(), "uf": (uf_txt or uf).upper(),
                              "decreto_municipal": numero or None, "data": it["data"], "url": it["url"],
                              "trecho": tr[:300]})
    return saida


def iso_para_br(s: str) -> str:
    try:
        y, m, d = s[:10].split("-"); return f"{d}/{m}/{y}"
    except ValueError:
        return s


def coletar_uf(uf: str, desde: str, cfg: dict) -> str:
    por_cod, por_nome = referencia_ibge()
    f = cfg["ufs"][uf]
    f["ultima_tentativa"] = date.today().isoformat()
    if not f.get("adaptador") or not f.get("url"):
        registrar_lacuna(f"DOE/{uf}", "adaptador não confirmado (a_verificar)", canal="repositorio_estadual",
                         camada=1, uf=uf)
        f["status"] = "a_verificar"; return "lacuna"
    if f["adaptador"] == "querido_diario":
        params = urllib.parse.urlencode({"territory_ids": f["url"], "published_since": desde,
                                         "querystring": " OR ".join(f'"{t}"' for t in TERMOS[:4]), "size": 100})
        url = QD_API.format(params=params)
    else:
        url = f["url"]
    try:
        bruto = buscar(url)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"DOE/{uf}", f"{type(e).__name__}: {e}", canal="repositorio_estadual", camada=1, uf=uf, strings=[url])
        f["status"] = f"erro: {type(e).__name__}"; return "erro"
    texto = bruto.decode("utf-8", "replace")
    h = preservar_evidencia(bruto, url, "json" if f["adaptador"] == "querido_diario" else "html", "coletar_doe")
    if f["adaptador"] != "querido_diario" and eh_suspensao_defeso(texto):
        registrar_lacuna(f"DOE/{uf}", "aviso de período eleitoral na fonte", canal="repositorio_estadual",
                         camada=1, uf=uf, strings=[url], suspensa=True, hash_evidencia=h)
        f["status"] = "fonte suspensa (defeso)"; return "suspensa"
    if f["adaptador"] == "querido_diario":
        try:
            itens = parse_querido_diario(json.loads(texto))
        except json.JSONDecodeError:
            registrar_lacuna(f"DOE/{uf}", "resposta não é JSON", canal="repositorio_estadual", camada=1, uf=uf, hash_evidencia=h)
            f["status"] = "erro: formato"; return "erro"
    else:
        itens = [{"data": date.today().isoformat(), "url": url, "trechos": [texto[:20000]], "territorio": uf}]
    homol = extrair_homologacoes(itens, uf)
    atos = ler("atos_resposta.json"); pistas = ler("pistas_doe.json", {"_governanca": "Pistas de DOE (v2.2.4): "
                                                                        "descoberta, nunca registro.", "itens": []})
    vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    novos = pist = 0
    for hm in homol:
        cod = por_nome.get((hm["municipio"], hm["uf"]))
        if not cod or not hm["decreto_municipal"]:
            pistas["itens"].append({**hm, "motivo": "sem número do decreto ou município não casou com IBGE",
                                    "hash_evidencia": h, "registrado_em": date.today().isoformat()}); pist += 1
            continue
        ref = por_cod[cod]; dbr = iso_para_br(hm["data"])
        chave = (ref["nome"], hm["uf"], dbr, "homologação estadual")
        if chave in vistos:
            continue
        atos["eventos"].append({"nome": ref["nome"], "uf": hm["uf"], "ibge": cod, "data": dbr,
                                "causa": "homologação estadual", "decreto": f"Decreto municipal nº {hm['decreto_municipal']}",
                                "decreto_estadual_homologacao": f"DOE/{hm['uf']} {dbr}", "url_doe": hm["url"],
                                "fonte": f"Diário Oficial do Estado ({hm['uf']})", "url": hm["url"],
                                "lat": ref["lat"], "lon": ref["lon"], "canal": "repositorio_estadual", "hash_evidencia": h})
        marcar_fato_municipal(cod, "decreto_homologado", True); vistos.add(chave); novos += 1
    gravar("atos_resposta.json", atos); gravar("pistas_doe.json", pistas)
    ibges_uf = [c for c, r in por_cod.items() if r["uf"] == uf]
    marcar_fonte_consultada(ibges_uf, f"DOE/{uf}", "estadual", resultado=f"{len(itens)} edição(ões)/trecho(s)")
    log_busca("repositorio_estadual", 1, TERMOS[:4], "registro" if novos else "pista", uf=uf, nivel="estadual",
              n_resultados=len(itens), resultados=f"{len(homol)} homologações, {novos} novas, {pist} pistas", hash_evidencia=h)
    f["status"] = "ok"; return "ok"


FIXTURE_QD = {"total_gazettes": 1, "gazettes": [{"territory_id": "42", "date": "2026-08-31", "url": "https://x/doe.pdf",
              "excerpts": ["DECRETO Nº 5.000 — Homologa o Decreto Municipal nº 123/2026 que declara situação de emergência no Município de Blumenau - SC."]}]}


def autoteste() -> int:
    def t1(): return len(parse_querido_diario(FIXTURE_QD)) == 1
    def t2():
        h = extrair_homologacoes(parse_querido_diario(FIXTURE_QD), "SC")
        return len(h) == 1 and h[0]["municipio"] == "Blumenau" and h[0]["decreto_municipal"] == "123/2026"
    def t3(): return parse_querido_diario({}) == [] and parse_querido_diario(None) == []
    def t4():
        cfg = fontes_doe_padrao(); return len(cfg["ufs"]) == 27 and all(v["status"] == "a_verificar" for v in cfg["ufs"].values())
    return rodar_autoteste({"parser Querido Diário": t1, "extrai homologação com nº e município": t2,
                            "negativo: resposta vazia/nula": t3, "config nasce a_verificar nas 27 UFs": t4})


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    cfg = ler("fontes_doe.json", None) or fontes_doe_padrao()
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else "2026-06-29"
    if "--uf" in sys.argv:
        ufs = [sys.argv[sys.argv.index("--uf") + 1].upper()]
    elif "--regiao" in sys.argv:
        ufs = REGIOES[sys.argv[sys.argv.index("--regiao") + 1].upper()].split()
    else:
        ufs = [u for r in REGIOES.values() for u in r.split()]
    res = {u: coletar_uf(u, desde, cfg) for u in ufs}
    gravar("fontes_doe.json", cfg)
    print("DOE:", ", ".join(f"{u}={r}" for u, r in res.items()))
    sys.exit(0)
