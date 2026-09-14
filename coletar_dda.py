#!/usr/bin/env python3
"""
coletar_dda.py — Doenças diarreicas agudas (DDA), Brasil e por UF (catálogo: dda; 14/09/2026, item 1 do §5)
============================================================================================================
Fonte: Sivep-DDA (Ministério da Saúde) — agregado SEMANAL por MUNICÍPIO das unidades sentinela (MDDA).
Não existe publicação aberta do MS: o OpenDataSUS não hospeda o Sivep-DDA (verificado no runner em
14/09/2026, relatório dda_opendatasus) e o portal deixou de ser CKAN. O que existe é a resposta do MS a
um pedido LAI (processo 25072.030308202612) redistribuída no Zenodo por Raphael Saldanha
(Fiocruz / Observatório de Clima e Saúde), CC BY 4.0, com MD5 publicado, codebook e manifesto:
  · 2008–2024 (série histórica)          → registro 20752238
  · 2025–2026 (preliminar, mensal)       → registro 20752301
O crédito no site diz exatamente isso: MS/Sivep-DDA via LAI · depósito Zenodo · data de publicação do
depósito. O coletor segue `links.latest` de cada registro (novas versões trocam o id) e confere o MD5
de cada arquivo contra o publicado — arquivo com MD5 diferente é lacuna, nunca dado.

Formato verificado no runner (relatório 2026-09-14_111941_dda_zenodo.txt): CSV com vírgula, 26 colunas
(`sem_epid_week`, `sem_epid_year`, `uf_sigla`, `municipio_ibge` com 6 dígitos, casos por faixa etária
`nu_m1ano/nu_1a4/nu_5a9/nu_10oumais/nu_faixign`). Mesmo assim as colunas são localizadas por PADRÃO
(nunca por índice), e o coletor falha alto se um papel obrigatório não casar.

Casos da semana = soma das cinco faixas etárias (a contagem é de atendimentos em unidades sentinela,
não do total de casos no país — o rótulo do eixo diz isso). Mesmo tratamento do §35/§36: canal
endêmico 2019–2025 (mediana/p75/p90), últimas 4 semanas do ano corrente vazadas do consolidado (atraso
de digitação; não há nowcasting nesta fonte — as barras "parciais" são o valor bruto). Peso zero.
Anos históricos são baixados uma vez e reaproveitados enquanto o MD5 publicado não mudar.
  python coletar_dda.py --autoteste
"""
import csv, hashlib, io, json, re, sys, unicodedata, zipfile
from collections import defaultdict
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste
from coletar_srag_gripe import canal_endemico, vazar_incompletas, ANOS_CANAL, SE_INCOMPLETAS

RAIZ = Path(__file__).resolve().parent
REGISTROS = {"historico": "20752238", "preliminar": "20752301"}
ANO_CORRENTE = 2026
ANOS = list(range(2019, ANO_CORRENTE + 1))
ARQUIVO = "saude_desfechos/dda_serie.json"
ARQUIVO_PAINEL = "saude_desfechos/dda_serie_painel.json"
API = "https://zenodo.org/api/records/{id}"
LAI = "25072.030308202612"
RESSALVA = ("O Monitor não atribui casos ao El Niño; a série é a do Sivep-DDA (Ministério da Saúde) obtida por LAI "
            f"(processo {LAI}) e redistribuída no Zenodo por Raphael Saldanha (Fiocruz), CC BY 4.0; conta atendimentos "
            "em unidades sentinela (MDDA), não o total de casos.")
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]


def _hoje():
    import datetime as _dt
    try:
        a = json.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def _plano(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn").strip()


def detectar_colunas(cabecalho: list) -> dict:
    """Papéis: semana, ano, uf, municipio (6 ou 7 dígitos IBGE) e a lista de colunas de casos por faixa etária.
    Função pura; ValueError se um papel obrigatório não casar (falha alto, nunca adivinha)."""
    norm = [_plano(h) for h in cabecalho]
    PADROES = {"semana": [r"^sem_?epid_?week$", r"^semana"], "ano": [r"^sem_?epid_?year$", r"^ano"],
               "uf": [r"^uf_?sigla$", r"^sg_?uf$"], "municipio": [r"^municipio_?ibge$", r"^cd_?mun_?ibge$"]}
    achado = {}
    for papel, pats in PADROES.items():
        for i, h in enumerate(norm):
            if any(re.search(p, h) for p in pats):
                achado[papel] = i; break
        if papel not in achado:
            raise ValueError(f"coluna para '{papel}' não encontrada no cabeçalho Sivep-DDA: {cabecalho}")
    faixas = [i for i, h in enumerate(norm) if re.search(r"^nu_(m1ano|1a4|5a9|10oumais|faixign)$", h)]
    if len(faixas) != 5:
        raise ValueError(f"esperava 5 colunas de casos por faixa etária (nu_*), achei {len(faixas)} em {cabecalho}")
    achado["faixas"] = faixas
    return achado


def parse_csv(texto: str, painel: set | None = None) -> tuple:
    """(serie {BR/UF: {'AAAA-SS': casos}}, cobertura {BR/UF: {'AAAA-SS': n_municipios}}, painel {ibge7: {'AAAA-SS': casos}}).
    `painel` = conjunto de códigos IBGE de 7 dígitos; o CSV traz 6 — casa por prefixo. Função pura."""
    linhas = list(csv.reader(io.StringIO(texto)))
    if not linhas:
        raise ValueError("CSV vazio")
    col = detectar_colunas(linhas[0])
    serie = defaultdict(lambda: defaultdict(float)); cob = defaultdict(lambda: defaultdict(set)); pain = defaultdict(dict)
    prefixo = {p[:6]: p for p in (painel or set())}
    for r in linhas[1:]:
        try:
            se = int(r[col["semana"]]); ano = int(r[col["ano"]]); uf = r[col["uf"]].strip().upper()
        except (ValueError, IndexError):
            continue
        if not (1 <= se <= 53) or uf not in UFS:
            continue
        casos = 0.0
        for i in col["faixas"]:
            v = r[i].strip() if i < len(r) else ""
            if v:
                try:
                    casos += float(v)
                except ValueError:
                    pass
        k = f"{ano}-{se:02d}"; mun = r[col["municipio"]].strip()
        for loc in ("BR", uf):
            serie[loc][k] += casos; cob[loc][k].add(mun)
        if mun[:6] in prefixo:
            pain[prefixo[mun[:6]]][k] = pain[prefixo[mun[:6]]].get(k, 0.0) + casos
    return ({l: dict(s) for l, s in serie.items()}, {l: {k: len(v) for k, v in c.items()} for l, c in cob.items()}, dict(pain))


def _registro(id_: str) -> dict:
    """Metadados do registro, já na versão mais recente (`links.latest`)."""
    rec = json.loads(buscar(API.format(id=id_), timeout=60))
    latest = (rec.get("links") or {}).get("latest")
    if latest and latest != rec.get("links", {}).get("self"):
        try:
            rec2 = json.loads(buscar(latest, timeout=60))
            if rec2.get("id") and str(rec2["id"]) != str(rec.get("id")):
                print(f"  registro {id_}: versão mais nova é {rec2['id']} — usando-a")
                rec = rec2
        except Exception as e:  # noqa: BLE001
            print(f"  registro {id_}: não resolvi `latest` ({e}); sigo com a versão pedida")
    return rec


def _arquivo(rec: dict, nome: str) -> dict | None:
    for f in rec.get("files", []):
        if f.get("key") == nome:
            return f
    return None


def _csv_do_zip(corpo: bytes) -> str:
    z = zipfile.ZipFile(io.BytesIO(corpo))
    nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if len(nomes) != 1:
        raise ValueError(f"esperava 1 CSV no zip, achei {nomes}")
    return z.read(nomes[0]).decode("utf-8", "replace")


def _painel() -> set:
    d = ler("saude_desfechos/serie_painel.json") or {}
    return {k for k in (d.get("municipios") or {}) if isinstance(k, str) and len(k) == 7 and k.isdigit()}


def coletar() -> int:
    hoje = _hoje().strftime("%d/%m/%Y")
    anterior = ler(ARQUIVO) or {}
    cache = anterior.get("arquivos") or {}
    try:
        recs = {chave: _registro(id_) for chave, id_ in REGISTROS.items()}
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("Sivep-DDA (Zenodo)", f"API do Zenodo não respondeu: {str(e)[:160]}", canal="DOU", camada=1)
        return 0
    painel = _painel()
    serie: dict = defaultdict(dict); cobertura: dict = defaultdict(dict); pain: dict = defaultdict(dict)
    arquivos = {}; urls = []
    for ano in ANOS:
        rec = recs["preliminar"] if ano >= 2025 else recs["historico"]
        nome = f"sivep_dda_{ano}_csv.zip"; f = _arquivo(rec, nome)
        if not f:
            registrar_lacuna(f"Sivep-DDA {ano}", f"{nome} não está no registro Zenodo {rec.get('id')}", canal="DOU", camada=1)
            continue
        md5_pub = (f.get("checksum") or "").replace("md5:", "")
        antigo = cache.get(str(ano)) or {}
        if antigo.get("md5") == md5_pub and antigo.get("serie") and ano < ANO_CORRENTE - 1:
            # ano histórico inalterado: reaproveita o que já foi lido (evita baixar ~5 MB × 7 toda semana)
            for loc, s in antigo["serie"].items(): serie[loc].update(s)
            for loc, c in (antigo.get("cobertura") or {}).items(): cobertura[loc].update(c)
            for m, s in (antigo.get("painel") or {}).items(): pain[m].update(s)
            arquivos[str(ano)] = antigo; continue
        try:
            corpo = buscar(f["links"]["self"], timeout=180)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"Sivep-DDA {ano}", f"download falhou: {str(e)[:160]}", canal="DOU", camada=1); continue
        md5 = hashlib.md5(corpo).hexdigest()
        if md5 != md5_pub:
            registrar_lacuna(f"Sivep-DDA {ano}", f"MD5 diferente do publicado ({md5} ≠ {md5_pub}) — arquivo descartado", canal="DOU", camada=1); continue
        try:
            s, c, p = parse_csv(_csv_do_zip(corpo), painel)
        except (ValueError, zipfile.BadZipFile) as e:
            registrar_lacuna(f"Sivep-DDA {ano} (formato)", str(e)[:180], canal="DOU", camada=1); continue
        for loc, x in s.items(): serie[loc].update(x)
        for loc, x in c.items(): cobertura[loc].update(x)
        for m, x in p.items(): pain[m].update(x)
        arquivos[str(ano)] = {"md5": md5, "registro": rec.get("id"), "publicado_em": (rec.get("metadata") or {}).get("publication_date"),
                              "serie": s, "cobertura": c, "painel": p}
        urls.append(f["links"]["self"]); print(f"  {ano}: {len(s.get('BR', {}))} semana(s), MD5 ok")
    if not serie.get("BR") or not any(k.startswith(str(ANO_CORRENTE)) for k in serie["BR"]):
        registrar_lacuna("Sivep-DDA", f"nenhuma semana de {ANO_CORRENTE} lida — lacuna declarada", canal="DOU", camada=1)
        return 0
    consolidada = {}; parcial = {}; canal = {}
    for loc, s in serie.items():
        cons, vaz = vazar_incompletas(s, ANO_CORRENTE)
        consolidada[loc] = cons; parcial[loc] = {k: s[k] for k in vaz if k in s}; canal[loc] = canal_endemico(s)
    pre = recs["preliminar"]
    gov = (f"Peso zero (§31/§35). {RESSALVA} Semanas de 2026 até a última presente no depósito; as {SE_INCOMPLETAS} últimas são "
           "'parciais' (atraso de digitação; a fonte não publica nowcasting). Anos históricos reaproveitados enquanto o MD5 publicado não muda.")
    gravar(ARQUIVO, {"_governanca": gov, "gerado_em": hoje, "fonte": f"https://doi.org/10.5281/zenodo.{REGISTROS['preliminar']}",
                     "fonte_primaria": f"Sivep-DDA / Ministério da Saúde, resposta LAI {LAI}",
                     "deposito_publicado_em": (pre.get("metadata") or {}).get("publication_date"), "indicador": "dda",
                     "ano_corrente": ANO_CORRENTE, "anos_canal": ANOS_CANAL, "se_incompletas": SE_INCOMPLETAS,
                     "serie": consolidada, "parcial": parcial, "canal_endemico": canal, "cobertura": dict(cobertura),
                     "arquivos": arquivos})
    gravar(ARQUIVO_PAINEL, {"_governanca": gov + " Só os municípios do painel amostral (casamento por prefixo IBGE de 6 dígitos).",
                            "gerado_em": hoje, "fonte": f"https://doi.org/10.5281/zenodo.{REGISTROS['preliminar']}",
                            "municipios": {m: {"semanas": dict(sorted(s.items()))} for m, s in pain.items()}})
    log_busca("DOU", 1, urls or [API.format(id=REGISTROS['preliminar'])], "registro", nivel="nacional",
              n_resultados=len(serie), resultados=f"DDA: {len(serie)} localidade(s) (BR + UFs), {len(pain)} município(s) do painel, anos {ANOS[0]}–{ANOS[-1]}")
    print(f"✓ DDA: BR + {len(serie) - 1} UF(s), {len(pain)}/{len(painel)} município(s) do painel")
    return 0


def autoteste() -> int:
    cab = "notification_year,sem_epid_week,sem_epid_year,tx_semepid,cd_estado,cd_municipio,nu_m1ano,nu_1a4,nu_5a9,nu_10oumais,nu_faixign,nu_planoa,nu_planob,nu_planoc,nu_planoign,lo_alteracao,lo_surto,nu_surto,nu_surto_invest,nu_surto_amostra,nu_usaude_sem,nu_unidades_inf,uf_sigla,municipio_nome,uf_ibge,municipio_ibge"
    def linha(ano, se, uf, mun6, faixas):
        f = ",".join(str(x) for x in faixas)
        return f"{ano},{se},{ano},{se:02d}/{ano},1,1,{f},0,0,0,0,Nao,Nao,,,,1,1,{uf},X,29,{mun6}"
    txt = cab + "\n"
    for ano in (2019, 2020, 2021, 2022, 2023, 2025):
        txt += linha(ano, 10, "BA", "291450", [1, 2, 3, 4, 0]) + "\n" + linha(ano, 10, "SP", "355030", [0, 0, 0, 5, 0]) + "\n"
    for se in range(18, 24):
        txt += linha(2026, se, "BA", "291450", [10, 10, 10, 10, 0]) + "\n"
    txt += linha(2026, 18, "BA", "291450", [1, 0, 0, 0, "" ]) + "\n"   # célula vazia = 0, não erro
    txt += linha(2026, 18, "XX", "999999", [9, 9, 9, 9, 9]) + "\n"    # UF inválida: ignorada
    def t1():
        c = detectar_colunas(cab.split(",")); return c["semana"] == 1 and c["uf"] == 22 and c["municipio"] == 25 and c["faixas"] == [6, 7, 8, 9, 10]
    def t2():
        try:
            detectar_colunas(["a", "b"]); return False
        except ValueError:
            return True
    def t3():
        s, c, _ = parse_csv(txt); return s["BR"]["2026-18"] == 41 and s["BA"]["2026-19"] == 40 and s["BR"]["2019-10"] == 15 and c["BR"]["2019-10"] == 2 and "XX" not in s
    def t4():
        _, _, p = parse_csv(txt, {"2914505", "3550308", "1100015"}); return p["2914505"]["2026-19"] == 40 and p["3550308"]["2025-10"] == 5 and "1100015" not in p
    def t5():
        s, _, _ = parse_csv(txt); c = canal_endemico(s["BR"]); return c["10"]["n_anos"] == 6 and c["10"]["p90"] >= c["10"]["mediana"]
    def t6():
        s, _, _ = parse_csv(txt); cons, vaz = vazar_incompletas(s["BR"], 2026); return vaz == ["2026-20", "2026-21", "2026-22", "2026-23"] and cons["2026-19"] == 40 and cons["2026-23"] is None
    def t7():
        return "não atribui casos ao El Niño" in RESSALVA and LAI in RESSALVA and "sentinela" in RESSALVA and REGISTROS["preliminar"] == "20752301"
    def t8():
        try:
            _csv_do_zip(b"nao e zip"); return False
        except zipfile.BadZipFile:
            buf = io.BytesIO(); z = zipfile.ZipFile(buf, "w"); z.writestr("a.csv", "x"); z.writestr("b.csv", "y"); z.close()
            try:
                _csv_do_zip(buf.getvalue()); return False
            except ValueError:
                return True
    return rodar_autoteste({"detecção de colunas por padrão": t1, "coluna ausente falha alto (nunca adivinha)": t2,
                            "parse: BR e UF, soma das faixas, cobertura, UF inválida ignorada": t3,
                            "painel: casamento por prefixo de 6 dígitos": t4, "canal endêmico 2019–2025": t5,
                            "últimas 4 SE do ano corrente vazadas": t6, "ressalva, LAI e registro": t7,
                            "zip inválido ou com 2 CSVs falha alto": t8})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
