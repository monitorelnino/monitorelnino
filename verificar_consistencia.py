#!/usr/bin/env python3
"""Verificador de consistência do Monitor El Niño Brasil — MARÉ.
Cruza dados, índice, HTML e README; falha ruidosamente em qualquer divergência.

Caminhos relativos ao próprio arquivo (não ao diretório de trabalho nem a um
sandbox específico) — corrigido em 26/08/2026: a versão anterior usava um
caminho absoluto fixo (/home/claude/build/...) que só existia no sandbox de
edição e faria este portão BLOQUEANTE quebrar com FileNotFoundError em
qualquer outro ambiente real (a Action do GitHub, a máquina de quem publica)."""
import json, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

ERROS, AVISOS = [], []
def erro(m):
    """Registra falha bloqueante — sua presença ao final faz o portão terminar com código de saída 1."""
    ERROS.append(m)
def aviso(m):
    """Registra observação não bloqueante, exibida ao final mas que não impede a publicação."""
    AVISOS.append(m)

D = str(RAIZ / "data")
municipios = json.load(open(f"{D}/municipios.json"))
pontos = json.load(open(f"{D}/pontos_mapa.json"))
pct = json.load(open(f"{D}/percentual_uf.json"))
indice = json.load(open(f"{D}/indice.json"))
transf = json.load(open(f"{D}/transferencias.json"))
atos_resposta = json.load(open(f"{D}/atos_resposta.json"))

CATS = {"plano","plano_antigo","plano_elaboracao","decreto","coberto_estadual","nao_el_nino","nao_localizado","nao_verificado"}
CANAIS = {"DOM","DOU","repositorio_estadual","orgao_estadual","site_municipal","imprensa","—"}

# 1. Vocabulário controlado e campos obrigatórios
for r in municipios:
    if r["categoria"] not in CATS: erro(f"categoria fora do vocabulário: {r['nome']}/{r['uf']} → {r['categoria']}")
    if r.get("canal") not in CANAIS: erro(f"canal inválido: {r['nome']}/{r['uf']} → {r.get('canal')}")
    for k in ("nome","uf","documento","data","fonte","lat","lon"):
        if k not in r: erro(f"campo ausente {k}: {r.get('nome')}")

# 1b. Atos de resposta (data/atos_resposta.json — eventos de decreto de emergência,
# NUNCA pontuam; arquivo separado de municipios.json porque é log de eventos, não
# status por município — ver _governanca do arquivo, achado de 31/08/2026).
_vistos_atos = set()
for e in atos_resposta["eventos"]:
    for k in ("nome","uf","data","causa","decreto","fonte","lat","lon","canal"):
        if k not in e: erro(f"atos_resposta: campo ausente {k}: {e.get('nome')}/{e.get('uf')}")
    if e.get("canal") not in CANAIS: erro(f"atos_resposta: canal inválido: {e.get('nome')}/{e.get('uf')} → {e.get('canal')}")
    chave = (e.get("nome"), e.get("uf"), e.get("data"), e.get("causa"))
    if chave in _vistos_atos: erro(f"atos_resposta: evento duplicado (mesmo nome/UF/data/causa): {chave}")
    _vistos_atos.add(chave)
    if not (-34 <= e.get("lat", 0) <= 6) or not (-74 <= e.get("lon", 0) <= -32):
        erro(f"atos_resposta: coordenada fora do território brasileiro: {e.get('nome')}/{e.get('uf')}")

# 2. municipios ↔ pontos_mapa (mesmo universo e categorias)
mset = {(r["nome"], r["uf"], r["categoria"]) for r in municipios}
pset = {(p["nome"], p["uf"], p["categoria"]) for p in pontos}
if mset != pset:
    for x in sorted(mset - pset): erro(f"em municipios mas não em pontos: {x}")
    for x in sorted(pset - mset): erro(f"em pontos mas não em municipios: {x}")

# 3. Percentuais: composição soma com_ato; pct recalcula
for uf, v in pct.items():
    if v["n_plano"] + v["n_decreto"] != v["com_ato"]:
        erro(f"{uf}: n_plano+n_decreto ≠ com_ato ({v['n_plano']}+{v['n_decreto']}≠{v['com_ato']})")
    calc = round(100*v["com_ato"]/v["total"], 2)
    if abs(calc - v["pct"]) > 0.011: erro(f"{uf}: pct divergente ({v['pct']} vs {calc})")

# 3b. percentual_uf.json REALMENTE deriva de municipios.json (não apenas consistente
# consigo mesmo — pega o caso de editar municipios.json e esquecer de rodar
# recalcular_mare.py --write; achado e corrigido em 26/08/2026)
sys.path.insert(0, str(RAIZ))
from recalcular_mare import derivar_percentual_uf
_cnt = {}
for r in municipios:
    _cnt.setdefault(r["uf"], {}).setdefault(r["categoria"], 0)
    _cnt[r["uf"]][r["categoria"]] += 1
_totais = {uf: v["total"] for uf, v in pct.items()}
_pct_esperado = derivar_percentual_uf(_cnt, _totais, pct)
for uf, esperado in _pct_esperado.items():
    real = pct.get(uf, {})
    for campo in ("com_ato", "n_plano", "n_decreto", "pct"):
        if real.get(campo) != esperado.get(campo):
            erro(f"{uf}: percentual_uf.json desatualizado vs municipios.json — "
                 f"{campo}={real.get(campo)}, deveria ser {esperado.get(campo)} "
                 f"(rode: python3 recalcular_mare.py --write)")

# 4. Índice v2.2: total = média dos 3 componentes; média nacional vs veredito no HTML
for uf, v in indice.items():
    calc = round((v["estado"]+v["cobertura_pop"]+v["antecipacao"])/3, 1)
    if abs(calc - v["total"]) > 0.06: erro(f"MARÉ {uf}: total ≠ média dos componentes ({v['total']} vs {calc})")
media = round(sum(v["total"] for v in indice.values())/27, 1)

# 5. Transferências: soma dos repasses = 32,3 mi; todos geocodificados
soma = sum(r["valor"] for r in transf["repasses_rs"])
if soma != 32300000: erro(f"repasses RS somam {soma}, esperado 32300000")
if not all("lat" in r for r in transf["repasses_rs"]): erro("repasse RS sem geocodificação")

# 6. Números no pacote + (se presente) paridade com a prévia single-file.
# O single-file é um artefato de PRÉVIA gerado à parte para revisão em chat —
# não faz parte do pacote publicado e não existe em CI nem na máquina de quem
# publica. A checagem de paridade roda apenas quando ele existe (sessão de
# edição); nos demais ambientes, é pulada com aviso, não falha o portão.
pk = open(RAIZ / "index.html", encoding="utf-8").read()
ver = f"{media:.1f}".replace(".", ",")
if f'id="gaugeNum">{ver}<' not in pk: erro(f"pacote: veredito (gaugeNum) ≠ média nacional {ver}")
if "IPREN" in pk or "Águas Quentes" in pk: erro("pacote: resíduo de nome antigo")
if pk.count("<div") != pk.count("</div>") or pk.count("<script") != pk.count("</script>"):
    erro("pacote: tags desbalanceadas")

SINGLE_FILE = Path("/mnt/user-data/outputs/prototipo_plataforma_el_nino.html")
if SINGLE_FILE.exists():
    sf = SINGLE_FILE.read_text(encoding="utf-8")
    if f'id="gaugeNum">{ver}<' not in sf: erro(f"single-file: veredito (gaugeNum) ≠ média nacional {ver}")
    if "IPREN" in sf or "Águas Quentes" in sf: erro("single-file: resíduo de nome antigo")
    if sf.count("<div") != sf.count("</div>") or sf.count("<script") != sf.count("</script>"):
        erro("single-file: tags desbalanceadas")
    for pat, dado, nome in [(r"const TABELA_MUNICIPIOS = (\[.*?\]);\nconst MARE", municipios, "municipios"),
                            (r"const MARE = (\{.*?\});\nconst TRANSFERENCIAS", indice, "indice"),
                            (r"const PCT_POR_UF = (\{.*?\});\n", pct, "percentual"),
                            (r"const TRANSFERENCIAS = (\{.*?\});\nconst MAP_POINTS", transf, "transferencias"),
                            (r"const MAP_POINTS = (\[.*?\]);\n</script>", pontos, "pontos")]:
        m = re.search(pat, sf, re.S)
        if not m: erro(f"single-file: const {nome} não encontrado"); continue
        if json.loads(m.group(1)) != dado: erro(f"DIVERGÊNCIA single-file × pacote: {nome}")
else:
    aviso("prévia single-file não encontrada — checagem de paridade pulada (normal fora da sessão de edição)")

# 7. README declara o que o código faz
readme = open(RAIZ / "README.md", encoding="utf-8").read()
for termo in ["v2.1", "declaração vale metade", "MARÉ", "canal", "0,4", "0,5"]:
    if termo.lower() not in readme.lower(): aviso(f"README sem menção a: {termo}")

# 8. FIGURAS: mapas e gráficos da página dedicada versus dados e classificação canônica
# (portão criado em 27/08/2026 após o caso chartAreas/COBRADE e o aria fóssil; migrado
# em 31/08/2026 de index.html para mapas-e-graficos.html, quando mapas/gráficos ganharam
# página própria — CONSIST também deixou de ser JS embutido e virou data/consist.json,
# fonte única compartilhada pelas duas páginas que ainda precisam dele.)
import re as _re
_h = open(RAIZ / "mapas-e-graficos.html", encoding="utf-8").read()
_est = json.load(open(RAIZ / "data" / "estados.json", encoding="utf-8"))
_lac = {u["uf"] for u in _est["ufs"] if u["status"] == "LAC"}
_nao_lac = {u["uf"] for u in _est["ufs"]} - _lac
_cons = json.load(open(RAIZ / "data" / "consist.json", encoding="utf-8"))
if len(_cons) != 27: erro(f"figuras: consist.json com {len(_cons)} UFs")
_sem = {u for u, v in _cons.items() if v["cat"] == "SEM"}
if _sem != _lac: erro(f"figuras: consist.json SEM difere dos LAC: {sorted(_sem ^ _lac)}")
for _u, _v in _cons.items():
    if (_v["cat"] == "SEM") != _v["instr"].startswith("Nenhum"):
        erro(f"figuras: consist.json {_u} cat×instr inconsistentes")
_mA = _re.search(r"const AREAS = \[(.*?)\];", _h, _re.S)
if not _mA:
    erro("figuras: AREAS não encontrado em mapas-e-graficos.html")
else:
    _ufsA = set(_re.findall(r"'([A-Z]{2})'", _mA.group(1)))
    if _ufsA != _nao_lac:
        erro(f"figuras: união das AREAS difere dos estados com instrumento: {sorted(_ufsA ^ _nao_lac)}")
    # A tabela "risco × instrumento" deixou de ser uma cópia estática em HTML e passou
    # a ser gerada em runtime DIRETO de CONSIST (31/08/2026, eliminação de duplicação —
    # ver renderTabelaConsistencia() em mapas-e-graficos.html). Drift entre tabela e
    # CONSIST deixa de ser possível por construção; a checagem correspondente migrou para
    # scripts/verificar_runtime.js (que renderiza a página de verdade e confere a
    # tabela já populada), então a checagem estática de HTML bruto foi removida daqui.
    for _n in _re.findall(r"(\d+) munic[íi]pios verificados", _h):
        if int(_n) != len(municipios):
            erro(f"figuras: contagem fóssil de municípios verificados: {_n} × banco {len(municipios)}")
_p = open(RAIZ / "proteja-se.html", encoding="utf-8").read()
_mR = _re.search(r"const RISCO_UF\s*=\s*\{(.*?)\};", _p, _re.S)
if _mR:
    _ufsR = set(_re.findall(r"['\"]?([A-Z]{2})['\"]?\s*:", _mR.group(1)))
    if len(_ufsR & _nao_lac | _ufsR & _lac) != 27:
        aviso(f"figuras: RISCO_UF (proteja-se) com {len(_ufsR)} UFs reconhecidas")

# 10. SELOS (31/08/2026): um por UF + nacional, regravados pelo pipeline; o número
# dentro de cada SVG precisa ser o do índice publicado (e a faixa, a mesma do site).
_selos = RAIZ / "selos"
if not _selos.exists():
    erro("selos/ ausente — rode gerar_selos.py")
else:
    for _uf, _v in indice.items():
        _p = _selos / f"mare-{_uf}.svg"
        if not _p.exists():
            erro(f"selo ausente: {_p.name}"); continue
        _s = _p.read_text(encoding="utf-8")
        _num = f"{_v['total']:.1f}".replace(".", ",")
        if f">{_num}<" not in _s:
            erro(f"selo {_uf}: número no SVG não bate com indice.json ({_num})")
    if not (_selos / "mare-brasil.svg").exists():
        erro("selo nacional ausente: selos/mare-brasil.svg")

# 11. FEEDS (31/08/2026): 27 UFs + nacional, Atom bem formado, e o histórico existe.
_feeds = RAIZ / "feeds"
if not _feeds.exists() or not (RAIZ / "data" / "historico_mudancas.json").exists():
    erro("feeds/ ou data/historico_mudancas.json ausente — rode gerar_feeds.py")
else:
    import xml.etree.ElementTree as _ET
    for _nome in ["brasil"] + sorted(indice):
        _p = _feeds / f"{_nome}.xml"
        if not _p.exists():
            erro(f"feed ausente: {_p.name}"); continue
        try:
            _ET.fromstring(_p.read_bytes())
        except _ET.ParseError as _e:
            erro(f"feed {_p.name} mal formado: {_e}")

# 12. DADOS ABERTOS (31/08/2026): os CSVs exportados têm exatamente as linhas dos JSON de origem.
_da = RAIZ / "dados-abertos"
if not _da.exists():
    erro("dados-abertos/ ausente — rode gerar_dados_abertos.py")
else:
    import csv as _csv
    _esperado = {"indice": len(indice), "estados": len(json.load(open(f"{D}/estados.json", encoding="utf-8"))["ufs"]), "municipios": len(municipios),
                 "atos_resposta": len(atos_resposta["eventos"])}
    for _nome, _n in _esperado.items():
        _p = _da / f"{_nome}.csv"
        if not _p.exists():
            erro(f"dados abertos: {_p.name} ausente"); continue
        _linhas = list(_csv.DictReader(open(_p, encoding="utf-8")))
        if len(_linhas) != _n:
            erro(f"dados abertos: {_p.name} tem {len(_linhas)} linha(s), JSON tem {_n}")
    if "zenodo.XXXXXXX" not in (RAIZ / "CITATION.cff").read_text(encoding="utf-8") and "doi" not in (RAIZ / "CITATION.cff").read_text(encoding="utf-8").lower():
        erro("CITATION.cff sem o bloco de DOI (placeholder ou valor)")

# 9. NOMENCLATURA DAS FAIXAS — os quatro nomes precisam ser idênticos em todo lugar
# (portão criado em 31/08/2026, na quarta renomeação: a METODOLOGIA estava com uma
# nomenclatura e o site com outra, sem que nada acusasse).
FAIXAS = ["estágio inicial", "em construção", "consolidado", "avançado"]
APOSENTADOS = ["ponto de partida", "caminho aberto", "avanço consistente", "referência nacional",
               "em desenvolvimento", "em consolidação"]
_alvos = {
    "index.html (pílula)": _re.search(r"var f = v < 25 \? \[(.*?)\];", _h_idx := open(RAIZ / "index.html", encoding="utf-8").read()).group(1).lower(),
    "index.html (PDF)": _re.search(r"const fx = v\.total < 25 \? (.*?);", _h_idx).group(1).lower(),
    "index.html (régua)": _re.search(r'<div class="gauge-tick-labels">[\s\S]*?<div class="gauge-ends">[\s\S]*?</div>', _h_idx).group(0).lower(),
    "index.html (Como ler)": _re.search(r"As faixas descrevem[^<]*</strong>:([^<]*)", _h_idx).group(1).lower(),
    "METODOLOGIA.md": _re.search(r"Quarta renomeação[^\n]*", open(RAIZ / "METODOLOGIA.md", encoding="utf-8").read()).group(0).lower(),
    "gerar_pdf_indice.py": _re.search(r"Faixas \(estágio[^\"]*", open(RAIZ / "gerar_pdf_indice.py", encoding="utf-8").read()).group(0).lower(),
}
for _nome, _txt in _alvos.items():
    _falta = [f for f in FAIXAS if f not in _txt]
    if _falta: erro(f"faixas: {_nome} sem {_falta}")
_site_sem_script = _re.sub(r"<script[\s\S]*?</script>", "", _h_idx).lower()
for _pag in ["mapas-e-graficos.html", "proteja-se.html", "envie-dados.html", "obrigado.html"]:
    _site_sem_script += _re.sub(r"<script[\s\S]*?</script>", "", open(RAIZ / _pag, encoding="utf-8").read()).lower()
_velhos = [a for a in APOSENTADOS if a in _site_sem_script or a in _h_idx.lower()]
if _velhos: erro(f"faixas: nomenclatura aposentada ainda no site: {_velhos}")

print(f"municípios={len(municipios)} pontos={len(pontos)} UFs pct={len(pct)} UFs índice={len(indice)} média MARÉ={media}")
if AVISOS: print("AVISOS:"); [print("  ⚠", a) for a in AVISOS]
# ── Portão de natureza dos instrumentos estaduais (29/08/2026) ──────────────
# Impede a classe de erro encontrada na revisão de 29/08/2026 (AC/PE): ato de
# resposta (situação de emergência do rito SINPDEC) pontuado como instrumento
# ex-ante. Regras bloqueantes: (1) sincronia estados.json ↔ ESTADOS do motor;
# (2) status pontuável exige natureza_doc "ex-ante"; (3) doc com léxico de
# emergência + natureza "ex-ante" exige justificativa_ex_ante preenchida
# (teste do objeto declarado — casos legítimos: emergência ambiental/climática
# PREVENTIVA, como MS e AM). Cards de capitais com léxico sem a fórmula de
# registro ("não pontua"/"registro") geram aviso.
try:
    _est = json.load(open(f"{D}/estados.json"))
    sys.path.insert(0, str(RAIZ))
    sys.path.insert(0, str(RAIZ / "scripts"))
    from recalcular_mare import ESTADOS as _MOTOR
    from validar_dicionario import get_sinalizadores_resposta
    _SINAIS = get_sinalizadores_resposta()  # fonte única: data/dicionario_busca.json (29/08/2026)
    _LEX = re.compile("|".join(re.escape(s) for s in _SINAIS), re.I)
    for _u in _est["ufs"]:
        _uf = _u["uf"]
        _st_motor = _MOTOR[_uf][0]
        if _u.get("status") != _st_motor:
            erro(f"natureza[{_uf}]: status dessincronizado — estados.json '{_u.get('status')}' × motor '{_st_motor}'")
        _nat = _u.get("natureza_doc")
        if _nat not in ("ex-ante", "resposta_registro", "nenhum"):
            erro(f"natureza[{_uf}]: campo natureza_doc ausente ou fora do vocabulário ('{_nat}')")
        if _st_motor != "LAC" and _nat != "ex-ante":
            erro(f"natureza[{_uf}]: status pontuável '{_st_motor}' exige natureza_doc 'ex-ante' (encontrado '{_nat}') — ato de resposta não pontua (Correção B)")
        if _nat == "ex-ante" and _LEX.search(_u.get("doc","")) and not _u.get("justificativa_ex_ante","").strip():
            erro(f"natureza[{_uf}]: doc com léxico de emergência classificado ex-ante SEM justificativa_ex_ante — o teste do objeto deve ser declarado no registro")
        _cap = _u.get("capital", {})
        if _LEX.search(_cap.get("info","")) and not re.search(r"não pontua|registro", _cap.get("info",""), re.I):
            aviso(f"natureza[{_uf}]: card da capital menciona emergência sem a fórmula de registro ('não pontua') — revisar texto")
except Exception as _e:
    erro(f"portão de natureza falhou ao executar: {_e}")

# ── Portão de segredos (C10, achado do auditor, 30/08/2026) ─────────────────
# A chave de API não é parte do projeto — é credencial pessoal, como senha de
# e-mail. Este portão bloqueia se um .env.example deixar de ser modelo (algum
# dos três valores preenchido) ou se um arquivo .env real (com segredo de
# verdade) escapar do .gitignore e acabar no pacote/commit. Nunca decodifica
# nem imprime o valor encontrado — só aponta o arquivo e a variável.
try:
    _env_ex = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for _linha in _env_ex.splitlines():
        if re.match(r"^(PORTAL_TRANSPARENCIA_API_KEY|NETLIFY_AUTH_TOKEN|NETLIFY_SITE_ID)=.+", _linha):
            erro(f"segredos: .env.example tem valor preenchido em '{_linha.split('=')[0]}' — deve ficar vazio (é modelo, não credencial real)")
    _gi = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    if not re.search(r"^\.env$", _gi, re.M):
        erro("segredos: .gitignore não cobre '.env' — risco de vazamento se o arquivo local for versionado por engano")
    for _f in RAIZ.glob("*.env"):
        if _f.name != ".env.example":
            erro(f"segredos: arquivo real de ambiente encontrado no pacote: {_f.name} — nunca deve ser distribuído")
except Exception as _e:
    erro(f"portão de segredos falhou ao executar: {_e}")

# ── Portões v2.2.4 (doc de redesenho 02/09/2026, §2, §3, §6) ────────────────
try:
    _lg = json.load(open(RAIZ / "data" / "log_buscas.json", encoding="utf-8"))
    if _lg.get("formato_versao") != 2:
        erro("log_buscas: esquema v2 ausente (formato_versao != 2)")
    _NIVEIS = {None, "nacional", "estadual", "municipal_completo"}
    _DEC_OK = ("registro", "pista", "nada localizado", "fonte suspensa (defeso)", "erro")
    _completos = set()
    for _i, _e in enumerate(_lg.get("execucoes", [])):
        for _k in ("data", "canal", "strings", "decisao", "executor"):
            if _k not in _e: erro(f"log_buscas[{_i}]: campo ausente '{_k}'")
        if _e.get("nivel") not in _NIVEIS: erro(f"log_buscas[{_i}]: nivel inválido: {_e.get('nivel')}")
        if _e.get("nivel") == "municipal_completo" and not (_e.get("municipio") and _e.get("uf")):
            erro(f"log_buscas[{_i}]: municipal_completo exige municipio e uf estruturados")
        if str(_e.get("decisao","")).strip().lower().startswith("nada localizado") and _e.get("nivel") != "municipal_completo":
            erro(f"log_buscas[{_i}]: decisão 'nada localizado' com nivel '{_e.get('nivel')}' — regra §2.1: só com bateria municipal completa")
        if _e.get("nivel") == "municipal_completo" and str(_e.get("decisao","")).strip().lower().startswith("nada localizado"):
            _completos.add((_e.get("municipio"), _e.get("uf")))
    # nada-localizado no banco exige o log correspondente
    _tab = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    for _r in _tab:
        if _r.get("categoria") == "nao_localizado" and (_r["nome"], _r["uf"]) not in _completos:
            erro(f"'{_r['nome']}/{_r['uf']}' está nao_localizado sem bateria municipal completa no log (§2.1) — reclassificar para nao_verificado")
except Exception as _e:
    erro(f"portão do log v2 falhou ao executar: {_e}")

try:
    _dic = json.load(open(RAIZ / "data" / "dicionario_busca.json", encoding="utf-8")).get("grupos", {})
    for _g in ("saude", "programas_permanentes", "rotas_sem_decreto"):
        if _g not in _dic: erro(f"dicionario_busca: grupo '{_g}' ausente (§2.4)")
        else:
            _gg = _dic[_g]
            _termos = _gg.get("termos") if isinstance(_gg, dict) else _gg
            if not _termos: erro(f"dicionario_busca: grupo '{_g}' vazio")
            if isinstance(_gg, dict) and _gg.get("origem") != "sessão metodológica 02/09/2026":
                erro(f"dicionario_busca: grupo '{_g}' sem origem declarada")
except Exception as _e:
    erro(f"portão do dicionário v2.2.4 falhou ao executar: {_e}")

try:
    _vm = json.load(open(RAIZ / "data" / "verificacao_municipal.json", encoding="utf-8"))
    if len(_vm) != 5571: erro(f"verificacao_municipal: {len(_vm)} municípios (esperados 5.571)")
    _NV = {"nao_verificado", "nacional", "estadual", "municipal_completo"}
    for _v in _vm:
        if _v.get("nivel_verificacao") not in _NV:
            erro(f"verificacao_municipal: nível inválido em {_v.get('nome')}/{_v.get('uf')}"); break
    _fila = json.load(open(RAIZ / "data" / "citacao_incompleta.json", encoding="utf-8"))
    if "regra" not in _fila or "fila" not in _fila: erro("citacao_incompleta: sem regra declarada ou sem fila")
except Exception as _e:
    erro(f"portão da verificação municipal falhou ao executar: {_e}")

# ── Portão de fósseis (v2.2.4, doc de redesenho §11.2): strings do modelo de 4 componentes ──
try:
    _FOSSEIS = ("4 componentes", "Dirichlet(1,1,1,1)", "componentes (25%)", "1,0/0,7/0,4")
    for _f in ("METODOLOGIA.md", "README.md", "DOCUMENTACAO_TECNICA.md", "gerar_pdf_indice.py", "gerar_pdf_metodologia.py", "recalcular_mare.py"):
        _t = (RAIZ / _f).read_text(encoding="utf-8") if (RAIZ / _f).exists() else ""
        for _k in _FOSSEIS:
            if _k in _t: erro(f"fóssil do modelo de 4 componentes em {_f}: '{_k}'")
except Exception as _e:
    erro(f"portão de fósseis falhou ao executar: {_e}")

if ERROS:  print("ERROS:");  [print("  ✗", e) for e in ERROS]; sys.exit(1)
print("✓ CONSISTENTE — todas as verificações passaram.")
