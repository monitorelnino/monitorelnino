#!/usr/bin/env python3
"""
coletar_financiamento.py — página "Por onde o dinheiro chega" (doc de redesenho §7.8; E9, E10, E12)
====================================================================================================
Peso ZERO no MARÉ (provado por verificar_financiamento.py). Reproduz registros oficiais com
órgão, consulta reproduzível (endpoint, parâmetros, data, hash da resposta) e data; separa
ex-ante de ex-post; lacuna exibida como ausência, nunca estimada.

Registros em data/financiamento/:
  rotas.json                  — as sete rotas + estadual (ordem e cores fixas; chave de acesso;
                                 base legal; o que o decreto destranca). Modelo do §28 da METODOLOGIA.
  por_uf.json                 — convergência do que já existia: financiamento_uf.json (fundo a fundo
                                 estadual preventivo), recursos_uf.json (capacidade fiscal), repasses
                                 do Prepara RS (transferencias.json) — com a fonte original em cada campo.
  compromissos_federais.json  — Plano federal El Niño (R$ 1,335 bi) e demais compromissos com dinheiro
                                 e prazo já verificados; execução por ação: aguardando coleta.
  serie_nacional.json         — série semanal 2026 das transferências da União a municípios por rota
                                 (aguardando primeira coleta pela Action; faixa do defeso declarada).
  emendas.json                — emendas por rota/UF/município; SEM campo de autor (E10: descartado
                                 na coleta; o portão prova a ausência).
  consultas.json              — toda consulta a API: endpoint, parâmetros, data, hash, nº de itens.

Adaptadores (rede só na Action): Portal da Transparência (chave PORTAL_TRANSPARENCIA_API_KEY;
endpoints /transferencias-voluntarias, /convenios e /emendas, com limite de 60 req/min);
Tesouro (constitucionais), FNS, FNAS, Transferegov, MDS/PVAC: `a_verificar` (§15) → lacuna.
Parsers provados por fixture (--autoteste). Uso: --semear · --autoteste · (coleta) --uf XX
"""
import hashlib, json, os, pathlib, sys, time, urllib.parse
from datetime import date
from coletores_base import buscar, log_busca, registrar_lacuna, ler, gravar, rodar_autoteste, referencia_ibge, sha256

RAIZ = pathlib.Path(__file__).parent; FIN = RAIZ / "data" / "financiamento"
API = "https://api.portaldatransparencia.gov.br/api-de-dados"
CAMPOS_AUTOR = ("nomeAutor", "codigoAutor", "autor", "nomeParlamentar", "autorEmenda", "codigoEmenda_autor")
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()


def _g(nome, obj):
    FIN.mkdir(parents=True, exist_ok=True)
    with open(FIN / nome, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1); f.write("\n")


def _l(nome, padrao=None):
    p = FIN / nome
    return json.load(open(p, encoding="utf-8")) if p.exists() else padrao


ROTAS = [
    {"id": "r1", "n": 1, "nome": "Repartição constitucional", "curta": "FPM · cota ICMS/IPVA", "chave": "regra", "cor": "#35566B",
     "base_legal": "CF art. 158–159; FPM = 22,5% de IR+IPI mais adicionais de 1% (jul/set/dez); cota de 25% do ICMS estadual",
     "decreto_destranca": "nada — flui por regra, sem condição de emergência", "ex_ante": True},
    {"id": "r2", "n": 2, "nome": "Fundo a fundo setorial", "curta": "FNS · FNAS · FUNDEB/FNDE", "chave": "regra", "cor": "#5E7C93",
     "base_legal": "SUS (Lei 8.080/1990, blocos de financiamento); SUAS (Lei 8.742/1993); FUNDEB (Lei 14.113/2020)",
     "decreto_destranca": "nada na regra; abre a exceção da rota 4", "ex_ante": True},
    {"id": "r3", "n": 3, "nome": "Defesa civil obrigatória", "curta": "resposta · recuperação · prevenção-obra (CPDC)", "chave": "decreto", "cor": "#7C4A34",
     "base_legal": "Lei 12.340/2010; Decreto 11.219/2022 (arts. 6–8: prevenção = obra em área de risco mapeada; art. 4º par. único: sem ressarcimento de gasto próprio; art. 37: suspensão sem risco ou decreto)",
     "decreto_destranca": "resposta e recuperação exigem reconhecimento federal do decreto; prevenção-obra exige área mapeada e plano de trabalho de engenharia", "ex_ante": False},
    {"id": "r4", "n": 4, "nome": "Emergência setorial", "curta": "SUAS/PVAC · portarias do MS", "chave": "decreto", "cor": "#A65F3F",
     "base_legal": "SUAS: portaria de 2026 por porte (PVAC); SUS: portarias específicas do MS por evento",
     "decreto_destranca": "o repasse extraordinário; sem ressarcimento retroativo (penaliza quem age antes)", "ex_ante": False},
    {"id": "r5", "n": 5, "nome": "Voluntárias e emendas com finalidade", "curta": "Transferegov · emendas individuais/bancada", "chave": "discricionária", "cor": "#C69B72",
     "base_legal": "Lei 9.504/1997, art. 73, VI, 'a': suspensas de 04/07 a 25/10/2026, salvo obrigações preexistentes e emergência/calamidade; Lei 14.133/2021 art. 75, VIII (dispensa de licitação em emergência); LRF art. 65",
     "decreto_destranca": "a exceção da vedação eleitoral e a dispensa de licitação", "ex_ante": True},
    {"id": "r6", "n": 6, "nome": "Transferências especiais", "curta": "art. 166-A, I (emendas 'pix')", "chave": "discricionária", "cor": "#87855C",
     "base_legal": "CF art. 166-A, I (EC 105/2019): sem finalidade definida, sem convênio", "decreto_destranca": "nada", "ex_ante": True},
    {"id": "r7", "n": 7, "nome": "Execução direta da União no território", "curta": "Carro-Pipa · Cisternas · Garantia-Safra · obras federais", "chave": "direta", "cor": "#647A7E",
     "base_legal": "Garantia-Safra (Lei 10.420/2002: adesão anual antes do plantio, cotas 2/6/12/40%); Programa Cisternas (MDS); Operação Carro-Pipa (Exército/MIDR)",
     "decreto_destranca": "Carro-Pipa: inclusão condicionada a reconhecimento federal na maior parte dos casos; Garantia-Safra: nenhum decreto", "ex_ante": True},
    {"id": "rE", "n": 8, "nome": "Rota estadual", "curta": "cota ICMS · fundo a fundo preventivo (Prepara RS) · convênios", "chave": "regra/discricionária", "cor": "#4F7D48",
     "base_legal": "Prepara RS: Resolução nº 008/FUNDEC/2026 (12/06/2026) — fundo a fundo estadual PREVENTIVO, condicionado a plano de contingência atualizado (precedente, E12)",
     "decreto_destranca": "nada no Prepara RS (é ex-ante); convênios seguem a regra estadual", "ex_ante": True},
]


def semear():
    hoje = date.today().strftime("%d/%m/%Y")
    _g("rotas.json", {"_governanca": "Modelo das sete rotas + estadual (§7.8, §28 da METODOLOGIA). Ordem e cores fixas em todas as figuras. "
                                     "Cláusula de neutralidade: descreve rotas existentes, não recomenda desenho de política.", "corte": hoje, "rotas": ROTAS})
    fin_uf = ler("financiamento_uf.json", {}) or {}; rec = ler("recursos_uf.json", {}) or {}; tr = ler("transferencias.json", {}) or {}
    rs = {}
    for r in tr.get("repasses_rs", []):
        rs[r.get("municipio") or r.get("nome")] = r
    por_uf = {}
    for uf in UFS:
        f = fin_uf.get(uf, {}) if isinstance(fin_uf, dict) else {}
        por_uf[uf] = {"fundo_a_fundo_preventivo": {"status": f.get("status", "nao_verificado"), "instrumento": f.get("instrumento") or f.get("doc"),
                                                    "norma": f.get("norma"), "condicionalidade": f.get("condicionalidade"), "url": f.get("fonte") or f.get("url"),
                                                    "verificado_em": f.get("verificado_em"), "fonte_original": "data/financiamento_uf.json"},
                      "capacidade_fiscal": {"pib_per_capita": (rec.get("pib_per_capita") or {}).get(uf) if isinstance(rec.get("pib_per_capita"), dict) else None,
                                            "fonte": rec.get("fonte"), "fonte_original": "data/recursos_uf.json"},
                      "rotas": {r["id"]: {"valor_2026": None, "status": "aguardando_coleta"} for r in ROTAS}}
    por_uf["RS"]["fundo_a_fundo_preventivo"].update({"programa": "Prepara RS", "repasses": len(tr.get("repasses_rs", [])),
                                                    "valor_total": next((p.get("valor_total") for p in tr.get("programas", []) if "Prepara RS" in p.get("nome", "")), None),
                                                    "fonte": next((p.get("fonte") for p in tr.get("programas", []) if "Prepara RS" in p.get("nome", "")), None),
                                                    "precedente_E12": True})
    _g("por_uf.json", {"_governanca": "Por UF: fundo a fundo estadual preventivo (rota E), capacidade fiscal e as rotas 1–7 (aguardando coleta). "
                                      "Convergência de financiamento_uf.json, recursos_uf.json e transferencias.json com a fonte original declarada por campo.",
                       "corte": hoje, "uf": por_uf})
    compromissos = [{"nome": p.get("nome"), "esfera": p.get("esfera"), "instrumento": p.get("instrumento"), "valor_total": p.get("valor_total"),
                     "condicionalidade": p.get("condicionalidade"), "fonte": p.get("fonte"), "rota": ("r3" if "obrigat" in (p.get("nome") or "").lower() else "rE" if "RS" in (p.get("esfera") or "") or "PR" in (p.get("esfera") or "") else "r5"),
                     "execucao": {"status": "aguardando_coleta", "fonte_prevista": "Portal da Transparência — execução por ação orçamentária"}}
                    for p in tr.get("programas", [])]
    compromissos.append({"nome": "PPA 2024–2027 — Programa 1158 (Enfrentamento da Emergência Climática), ação 20YJ", "esfera": "Federal", "instrumento": "PPA 2024–2027 / LOA 2026",
                         "valor_total": None, "condicionalidade": None, "fonte": None, "rota": "r3", "execucao": {"status": "a_verificar", "fonte_prevista": "SIOP/Portal da Transparência (§15: verificar antes de citar valores)"}})
    _g("compromissos_federais.json", {"_governanca": "Compromissos federais e estaduais com dinheiro e prazo, já verificados em fonte primária (transferencias.json), "
                                                     "e a execução correspondente no Portal (aguardando coleta). Nada estimado.", "corte": hoje, "itens": compromissos})
    _g("serie_nacional.json", {"_governanca": "Série semanal 2026 das transferências da União a municípios, empilhada por rota (fonte: dados abertos mensais do Portal + API para o mês corrente). "
                                              "Aguardando primeira coleta pela Action. A faixa do defeso (04/07–25/10/2026) é exibida sempre — inclusive depois de 25/10 (memória, E13).",
                               "defeso": {"inicio": "2026-07-04", "fim": "2026-10-25", "base": "Lei 9.504/1997, art. 73, VI, a"}, "semanas": [], "status": "aguardando_primeira_coleta", "corte": hoje})
    _g("emendas.json", {"_governanca": "Emendas por rota (r5/r6), UF e município. E10: o campo de autor é DESCARTADO na coleta e não existe aqui; nenhuma figura, tabela, tooltip ou link identifica parlamentar.",
                        "itens": [], "status": "aguardando_primeira_coleta", "corte": hoje})
    _g("consultas.json", {"_governanca": "Registro de toda consulta a API: endpoint, parâmetros, data, hash da resposta, nº de itens. É a proveniência das figuras alimentadas por API.", "consultas": []})
    print("financiamento: 6 registros semeados em data/financiamento/ (rotas, por_uf, compromissos, série, emendas, consultas)")


def registrar_consulta(endpoint, params, bruto, n):
    c = _l("consultas.json", {"consultas": []})
    c["consultas"].append({"endpoint": endpoint, "parametros": params, "data": date.today().isoformat(), "hash_resposta": sha256(bruto), "itens": n, "bytes": len(bruto)})
    _g("consultas.json", c)


def limpar_autor(item: dict) -> dict:
    """E10: remove qualquer campo de autor de emenda antes de qualquer gravação. Função pura."""
    return {k: v for k, v in item.items() if not any(k.lower().startswith(a.lower()) for a in CAMPOS_AUTOR)}


def parse_transferencias(dados) -> list:
    """Normaliza itens do Portal (/transferencias-voluntarias | /convenios): {rota, valor, ano, municipio_ibge, objeto, orgao}."""
    out = []
    for it in (dados or []):
        it = limpar_autor(it)
        ibge = str(it.get("codigoIBGE") or (it.get("municipio") or {}).get("codigoIBGE") or "")
        out.append({"rota": "r5", "valor": float(it.get("valor") or it.get("valorLiberado") or 0), "ano": int(str(it.get("ano") or it.get("dataReferencia") or "2026")[:4]),
                    "municipio_ibge": ibge.zfill(7) if ibge.isdigit() else None, "objeto": (it.get("objeto") or it.get("descricao") or "")[:200],
                    "orgao": (it.get("orgao") or {}).get("nome") if isinstance(it.get("orgao"), dict) else it.get("orgao")})
    return out


def parse_emendas(dados) -> list:
    out = []
    for it in (dados or []):
        it = limpar_autor(it)
        out.append({"rota": "r6" if "especial" in str(it.get("tipoEmenda") or "").lower() else "r5",
                    "valor_empenhado": float(it.get("valorEmpenhado") or 0), "valor_pago": float(it.get("valorPago") or 0), "ano": it.get("ano"),
                    "uf": it.get("uf") or (it.get("localidadeDoGasto") or "")[-2:], "funcao": it.get("funcao"), "codigo_emenda": it.get("codigoEmenda")})
    return out


def coletar(uf=None):
    chave = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "")
    if not chave:
        registrar_lacuna("Portal da Transparência", "PORTAL_TRANSPARENCIA_API_KEY ausente", canal="DOU", camada=1); return 0
    import urllib.request
    por_cod, _ = referencia_ibge(); alvos = [c for c, r in por_cod.items() if (not uf or r["uf"] == uf)][:60]
    itens = []; ok = lac = 0
    for cod in alvos:
        params = {"codigoIBGE": cod, "ano": date.today().year, "pagina": 1, "itens": 100}
        url = f"{API}/transferencias-voluntarias?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"chave-api-dados": chave, "User-Agent": "MonitorElNinoBrasil/2.3"})
            with urllib.request.urlopen(req, timeout=40) as r: bruto = r.read()
            dados = json.loads(bruto.decode("utf-8", "replace")); registrar_consulta("/transferencias-voluntarias", params, bruto, len(dados)); itens += parse_transferencias(dados); ok += 1
            time.sleep(1.0)  # 60 req/min
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"Portal/{cod}", type(e).__name__, canal="DOU", camada=1, ibge=cod); lac += 1
    em = _l("emendas.json", {"itens": []}); em["itens"] = [i for i in itens if i["rota"] in ("r5", "r6")]; em["status"] = "coletado" if ok else "aguardando_primeira_coleta"; _g("emendas.json", em)
    print(f"Portal: {ok} consultas, {lac} lacunas, {len(itens)} itens")
    return 0


FIX_T = [{"codigoIBGE": "4202404", "valor": "1500.50", "ano": 2026, "objeto": "Convênio defesa civil", "orgao": {"nome": "MIDR"}, "nomeAutor": "FULANO", "codigoAutor": "123"}]
FIX_E = [{"tipoEmenda": "Transferência Especial", "valorEmpenhado": 100000, "valorPago": 0, "ano": 2026, "uf": "SC", "funcao": "Saúde", "codigoEmenda": "2026X", "nomeAutor": "BELTRANO"}]


def autoteste():
    def t1(): semear(); return all((FIN / n).exists() for n in ("rotas.json", "por_uf.json", "compromissos_federais.json", "serie_nacional.json", "emendas.json", "consultas.json"))
    def t2(): r = _l("rotas.json")["rotas"]; return [x["n"] for x in r] == list(range(1, 9)) and len({x["cor"] for x in r}) == 8
    def t3(): p = parse_transferencias(FIX_T); return len(p) == 1 and p[0]["valor"] == 1500.5 and p[0]["municipio_ibge"] == "4202404" and "nomeAutor" not in json.dumps(p)
    def t4(): p = parse_emendas(FIX_E); return p[0]["rota"] == "r6" and "BELTRANO" not in json.dumps(p) and "nomeAutor" not in json.dumps(p)
    def t5(): return parse_transferencias(None) == [] and parse_emendas([]) == []
    def t6(): u = _l("por_uf.json")["uf"]; return len(u) == 27 and u["RS"]["fundo_a_fundo_preventivo"].get("precedente_E12") is True
    return rodar_autoteste({"semear cria os 6 registros": t1, "8 rotas em ordem, cores únicas": t2, "parser transferências descarta autor (E10)": t3,
                            "parser emendas descarta autor (E10)": t4, "negativo: resposta nula": t5, "por_uf: 27 UFs, Prepara RS como precedente": t6})


if __name__ == "__main__":
    if "--autoteste" in sys.argv: sys.exit(autoteste())
    if "--semear" in sys.argv: semear(); sys.exit(0)
    sys.exit(coletar(sys.argv[sys.argv.index("--uf") + 1] if "--uf" in sys.argv else None))
