#!/usr/bin/env python3
"""Internações do SUS por grupo de causa, UF e mês: SIH/SUS (AIH reduzida, arquivos RD do DATASUS).

Faixa E2 (HANDOVER_SUS_DESFECHOS_16-10-2026, camada C). Peso zero, como todo o MARÉ Saúde: conta
internações registradas; não atribui nenhuma ao El Niño.

O QUE A SÉRIE CONTA
-------------------
Internações aprovadas (AIH) por UF do HOSPITAL e mês de PROCESSAMENTO (competência `ANO_CMPT`/
`MES_CMPT`), como o TabNet "Internações" (que exclui a AIH de longa permanência, `IDENT` 5). O
diagnóstico é o principal (`DIAG_PRINC`). A competência é preliminar por meses: AIH reapresentada
entra depois, e o último mês publicado é sempre `parcial`.

ROTA
----
FTP público do DATASUS. Leitor `.dbc` e FTP (senha anônima que identifica o cliente, pausa entre
conexões, novas tentativas) são os de `coletar_datasus_dbc.py` (E1), importados.

LEITURA EM RODADAS
------------------
Um arquivo por UF e mês (27 × 94 desde jan/2019, alguns MB cada). A rodada lê do mês mais recente ao
mais antigo até o orçamento de tempo acabar; o que não foi lido fica fora da série (ausência, nunca
zero) e a lacuna é declarada no arquivo. Os três meses mais recentes são relidos quando o tamanho do
arquivo no FTP mudou (AIH reapresentada). Enquanto houver mês por ler, os cortes do mapa são
recalculados; completa a leitura, congelam (§108).

DESFECHOS (um arquivo por grupo, na forma comum de `desfechos_sus.py`)
`internacoes_respiratorias`, `internacoes_cardio`, `internacoes_renal`, `internacoes_desidratacao`,
`internacoes_fumaca`, `internacoes_calor` e `hepatite_a` (internações com diagnóstico principal B15:
internações, não casos notificados; o SINAN de hepatite A no FTP parou em 2023).

USO
  python3 coletar_sih.py --autoteste
  python3 coletar_sih.py --sondar          # só mede e imprime; não grava nada
  python3 coletar_sih.py [--orcamento S]   # lê o FTP por até S segundos e grava os sete arquivos comuns
"""
import datetime
import pathlib
import re
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

FTP_DIR_RD = "/dissemin/publicos/SIHSUS/200801_/Dados"
CAMPOS = ("ANO_CMPT", "MES_CMPT", "IDENT", "DIAG_PRINC")
TABNET_DEF = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/niuf.def"
TABNET_TAB = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/niuf.def"
UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()
RE_RD = re.compile(r"^RD([A-Z]{2})(\d{2})(\d{2})\.DBC$", re.I)

# grupo -> faixas de CID-10 (inclusivas, por letra e dois dígitos), do mapa do handover §1.
GRUPOS = {
    "respiratorias": [("J00", "J22")],
    "cardio": [("I20", "I25"), ("I60", "I64")],
    "renal": [("N17", "N19")],
    "desidratacao": [("E86", "E86")],
    "fumaca": [("T59", "T59")],
    "calor": [("T67", "T67")],
    "hepatite_a": [("B15", "B15")],
}
# grupo -> (desfecho do arquivo comum, rótulo). O rótulo descreve a contagem, sem interpretar.
DESFECHOS = {
    "respiratorias": ("internacoes_respiratorias", "Internações por doenças respiratórias agudas (CID-10 J00 a J22)"),
    "cardio": ("internacoes_cardio", "Internações por doença isquêmica do coração e cerebrovascular (CID-10 I20 a I25 e I60 a I64)"),
    "renal": ("internacoes_renal", "Internações por insuficiência renal (CID-10 N17 a N19)"),
    "desidratacao": ("internacoes_desidratacao", "Internações por desidratação (CID-10 E86)"),
    "fumaca": ("internacoes_fumaca", "Internações por efeito tóxico de gases, fumaças e vapores (CID-10 T59)"),
    "calor": ("internacoes_calor", "Internações por efeitos do calor e da luz (CID-10 T67)"),
    "hepatite_a": ("hepatite_a", "Internações por hepatite aguda A (CID-10 B15)"),
}
INICIO = "2019-01"
ORCAMENTO_S = 3000   # tempo de leitura por rodada (medido: 4,5 s por arquivo com três downloads à frente)
REPEDIR = 3          # meses mais recentes relidos quando o arquivo mudou de tamanho
PARADA_APOS = 5      # falhas seguidas: a fonte caiu, a rodada para
JANELA = 3           # downloads em voo ao mesmo tempo


# ============================================================================================
# Funções puras
# ============================================================================================
def grupo_do_cid(cid: str) -> list:
    """Grupos aos quais o CID principal pertence (pelos três primeiros caracteres). Função pura."""
    c = (cid or "").strip().upper()[:3]
    if not re.fullmatch(r"[A-Z]\d{2}", c):
        return []
    return [g for g, faixas in GRUPOS.items() if any(a <= c <= b for a, b in faixas)]


def agregar(registros) -> dict:
    """{'total'|grupo: {UF: {'AAAA-MM': n}}} a partir de registros RD (dicts). Função pura.

    Conta AIH que não são de longa permanência (IDENT != '5'). A UF vem de `UF_ZI` (dois primeiros
    dígitos IBGE do gestor) só quando o chamador não a fornece em `_UF`."""
    out = {}
    for r in registros:
        if str(r.get("IDENT") or "").strip() == "5":
            continue
        uf = r.get("_UF")
        ano, mes = str(r.get("ANO_CMPT") or "").strip(), str(r.get("MES_CMPT") or "").strip()
        if not uf or not (ano.isdigit() and mes.isdigit()):
            continue
        chave = f"{int(ano):04d}-{int(mes):02d}"
        for g in ["total"] + grupo_do_cid(r.get("DIAG_PRINC")):
            d = out.setdefault(g, {}).setdefault(uf, {})
            d[chave] = d.get(chave, 0) + 1
    # Mês lido sem caso do grupo é ZERO medido (o arquivo inteiro foi lido); mês sem arquivo não
    # aparece em lugar nenhum — essa é a ausência, e ela não vira zero.
    for uf, por_mes in out.get("total", {}).items():
        for g in GRUPOS:
            d = out.setdefault(g, {}).setdefault(uf, {})
            for chave in por_mes:
                d.setdefault(chave, 0)
    return out


def ultimo_por_uf(nomes) -> dict:
    """{UF: 'AAAA-MM'} da competência mais recente publicada, a partir da listagem. Função pura."""
    out = {}
    for n in nomes:
        m = RE_RD.match(n.strip())
        if not m:
            continue
        uf, aa, mm = m.group(1).upper(), int(m.group(2)), int(m.group(3))
        chave = f"{2000 + aa:04d}-{mm:02d}"
        if chave > out.get(uf, ""):
            out[uf] = chave
    return out


def meses_de_atraso(competencia: str, hoje: datetime.date) -> int:
    """Meses entre a competência 'AAAA-MM' e o mês de hoje. Função pura."""
    a, m = int(competencia[:4]), int(competencia[5:7])
    return (hoje.year - a) * 12 + (hoje.month - m)


def celula_tabnet(html: str, rotulo: str):
    """Número que segue o rótulo na tabela do TabNet (texto sem marcação), ou None. Função pura.

    O TabNet nem sempre fecha `<td>`; ler o texto plano evita depender da marcação."""
    import html as _h
    plano = re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", html or "")))
    m = re.search(re.escape(rotulo) + r"\s+([\d.]+)(?!\d)", plano, re.I)
    return int(m.group(1).replace(".", "")) if m else None


def form_tabnet(html: str) -> dict:
    """{nome_do_select: [(valor, texto, selecionado)]} do formulário do TabNet. Função pura."""
    out = {}
    for nome, corpo in re.findall(r'<select[^>]*name="?([^"\s>]+)"?[^>]*>(.*?)</select>',
                                  html or "", re.S | re.I):
        ops = []
        for attrs, texto in re.findall(r"<option([^>]*)>([^<]*)", corpo, re.I):
            v = re.search(r'value="([^"]*)"', attrs, re.I)
            ops.append((v.group(1) if v else texto.strip(), texto.strip(), "selected" in attrs.lower()))
        out[nome] = ops
    return out


# ============================================================================================
# Sondagem (rede; só mede e imprime)
# ============================================================================================
def _arquivos_por_uf(listagem: dict) -> dict:
    """{UF: {'AAAA-MM': nome}} dos RD de 2019 em diante, a partir de {nome: bytes}. Função pura."""
    out = {}
    for nome in listagem:
        m = RE_RD.match(nome.strip())
        if m and m.group(1).upper() in UFS and f"{2000 + int(m.group(2)):04d}-{m.group(3)}" >= INICIO:
            out.setdefault(m.group(1).upper(), {})[f"{2000 + int(m.group(2)):04d}-{m.group(3)}"] = nome
    return out


def a_ler(listagem: dict, lidos: set, tamanhos: dict, repetir: int = REPEDIR) -> list:
    """[(uf, 'AAAA-MM', nome)] a baixar, do mês mais recente ao mais antigo (as UFs de um mês antes do
    mês anterior): o que ainda não foi lido e, entre os `repetir` meses mais recentes de cada UF, o que
    mudou de tamanho desde a última leitura. Função pura."""
    fila = []
    for uf, d in _arquivos_por_uf(listagem).items():
        recentes = sorted(d)[-repetir:]
        fila += [(uf, c, n) for c, n in d.items()
                 if (uf, c) not in lidos or (c in recentes and listagem[n] != tamanhos.get(n))]
    return sorted(fila, key=lambda t: (t[1], t[0]), reverse=True)


def tamanhos_recentes(listagem: dict, lidos: set, repetir: int = REPEDIR) -> dict:
    """{nome: bytes} dos `repetir` meses mais recentes já lidos de cada UF. Função pura."""
    return {n: listagem[n] for uf, d in _arquivos_por_uf(listagem).items()
            for c, n in d.items() if c in sorted(d)[-repetir:] and (uf, c) in lidos}


def espacar(baixar, pausa: float, dormir=time.sleep, agora=time.monotonic):
    """`baixar` com no mínimo `pausa` segundos entre o início de dois downloads, mesmo em threads
    diferentes (a pausa do `_ftp` é por thread e não impede três conexões no mesmo instante)."""
    trava, ultimo = threading.Lock(), [None]

    def com_pausa(caminho):
        with trava:
            if ultimo[0] is not None and agora() - ultimo[0] < pausa:
                dormir(pausa - (agora() - ultimo[0]))
            ultimo[0] = agora()
        return baixar(caminho)
    return com_pausa


def coletar(listar=None, baixar=None, ler_fn=None, gravar_fn=None, hoje=None, decodificar=None,
            orcamento_s: int = ORCAMENTO_S, relogio=None, pausa: float = None) -> bool:
    """Lê o que falta no FTP e grava os sete arquivos comuns. Sem nenhum arquivo lido, nada é regravado."""
    import desfechos_sus as ds
    from coletar_datasus_dbc import PAUSA, baixar_ftp, ler_dbc, listar_ftp
    from coletores_base import gravar, hoje_editorial, ler
    listar = listar or listar_ftp; baixar = baixar or baixar_ftp; decodificar = decodificar or ler_dbc
    ler_fn = ler_fn or ler; gravar_fn = gravar_fn or gravar; relogio = relogio or time.monotonic
    hoje = hoje or hoje_editorial()
    baixar = espacar(baixar, PAUSA if pausa is None else pausa)
    ant = {g: ds.ler_desfecho(d, ler_fn) for g, (d, _r) in DESFECHOS.items()}
    base = ant["respiratorias"] or {}
    lidos = {(uf, p) for uf, s in base.get("serie", {}).items() if uf != "BR" for p, v in s.items() if v is not None}
    listagem = dict(listar(FTP_DIR_RD))
    fila = a_ler(listagem, lidos, base.get("fonte", {}).get("tamanhos_recentes", {}))
    novos = {g: {} for g in GRUPOS}
    falhas, seguidas, feitos, inicio = [], 0, set(), relogio()
    # Os downloads (a maior parte do tempo; medido em 19/10/2026: 11 s por arquivo em fila, 4,5 s com três à frente) correm
    # `JANELA` à frente da decodificação; a decodificação e a agregação seguem em ordem, numa linha só.
    with ThreadPoolExecutor(JANELA) as ex:
        voo, itens = deque(), iter(fila)
        while True:
            while len(voo) < JANELA and relogio() - inicio <= orcamento_s and seguidas < PARADA_APOS:
                t = next(itens, None)
                if t is None:
                    break
                voo.append((t, ex.submit(baixar, f"{FTP_DIR_RD}/{t[2]}")))
            if not voo:
                break
            (uf, comp, nome), pedido = voo.popleft()
            try:
                _desc, linhas = decodificar(pedido.result(), CAMPOS)
                ag = agregar({**r, "_UF": uf} for r in linhas)
                if comp not in ag.get("total", {}).get(uf, {}):
                    raise ValueError("arquivo sem registro da competência")
                for g in GRUPOS:
                    novos[g].setdefault(uf, {})[comp] = ag[g][uf][comp]
                feitos.add((uf, comp)); seguidas = 0
            except Exception as e:  # noqa: BLE001
                falhas.append(f"{nome}: {type(e).__name__}"); seguidas += 1
    if not feitos:
        print(f"SIH: nenhum arquivo lido ({len(fila)} na fila, {len(falhas)} falha(s)); os arquivos anteriores ficam")
        return False
    pendentes = [t for t in fila if (t[0], t[1]) not in lidos | feitos]
    ultimo = ultimo_por_uf(listagem)
    atrasadas = sorted(u for u, c in ultimo.items() if u != "BR" and c < max(ultimo.values()))
    lacunas = ([f"{len(pendentes)} arquivo(s) de UF e mês ainda não lidos; a leitura segue nas próximas rodadas"]
               if pendentes else []) + \
              ([f"falha de leitura nesta rodada: {', '.join(falhas[:5])}" + (" e outras" if len(falhas) > 5 else "")]
               if falhas else []) + \
              ([f"UF cujo último mês publicado é anterior ao do país: {', '.join(atrasadas)}"] if atrasadas else [])
    fonte = {"sistema": "SIH/SUS, AIH reduzida (arquivos RD), Ministério da Saúde, microdados no FTP do DATASUS",
             "url": f"ftp://ftp.datasus.gov.br{FTP_DIR_RD}/",
             "criterio": "AIH aprovadas, exceto longa permanência (IDENT 5); diagnóstico principal (DIAG_PRINC)",
             "data_do_periodo": "competência de processamento (ANO_CMPT e MES_CMPT)", "uf": "UF do hospital",
             "tamanhos_recentes": tamanhos_recentes(listagem, lidos | feitos)}
    ufs = sorted(ds.uf_por_codigo(ler_fn).values())
    populacao = ds.populacao_por_uf(ler_fn)
    ok = True
    for g, (desfecho, rotulo) in DESFECHOS.items():
        velho = (ant[g] or {}).get("serie", {})
        serie = {uf: {**velho.get(uf, {}), **novos[g].get(uf, {})} for uf in ufs}
        obj = ds.montar(desfecho=desfecho, rotulo=rotulo, unidade="internações", periodo="mes",
                        territorio="UF do hospital", serie={u: s for u, s in serie.items() if s}, fonte=fonte,
                        cadencia="mensal; o DATASUS publica o mês cerca de 45 dias depois do fim e ele cresce com AIH reapresentada",
                        coletado_em=hoje.isoformat(), anos_preliminares=[hoje.year], n_parciais=1,
                        populacao=populacao, anterior=ant[g] if not pendentes and _leitura_completa(ant[g]) else None, lacunas=lacunas)
        ok = ds.gravar_desfecho(obj, gravar_fn=gravar_fn) and ok
    print(f"SIH: {len(feitos)} arquivo(s) lido(s), {len(falhas)} falha(s), {len(pendentes)} por ler; gravado: {ok}")
    return ok


def _leitura_completa(obj) -> bool:
    """Cortes só congelam sobre leitura completa: o arquivo anterior não pode ter nascido com mês por ler (§108)."""
    return bool(obj) and not any("ainda não lidos" in x for x in obj.get("lacunas", []))


def sondar() -> int:
    from coletar_datasus_dbc import baixar_ftp, ler_dbc, listar_ftp
    from coletores_base import buscar, enviar, hoje_editorial
    hoje = hoje_editorial()
    print(f"== SIH/SUS · FTP {FTP_DIR_RD} · {hoje}")
    t0 = time.time()
    try:
        nomes = [n for n, _t in listar_ftp(FTP_DIR_RD)]
    except Exception as e:  # noqa: BLE001
        print(f"FTP: falhou ({type(e).__name__}: {e})")
        return 0
    print(f"listagem: {len(nomes)} nomes em {time.time() - t0:.1f}s")
    ult = ultimo_por_uf(nomes)
    for uf in UFS:
        c = ult.get(uf)
        print(f"  {uf}: {c or 'sem RD'}" + (f" · atraso {meses_de_atraso(c, hoje)} meses" if c else ""))
    if not ult:
        return 0
    # Célula de conferência: UF pequena; em 17/10/2026 AC e RR faltavam no TabNet de jul/2026.
    uf_c, nome_c = "AP", "Amapá"
    comp = ult.get(uf_c) or max(ult.values())
    dbc = baixar_ftp(f"{FTP_DIR_RD}/RD{uf_c}{comp[2:4]}{comp[5:7]}.dbc")
    _desc, linhas = ler_dbc(dbc, CAMPOS)
    regs = [dict(r, _UF=uf_c) for r in linhas]
    print(f"registros: {len(regs)} · {len(dbc)} bytes")
    ag = agregar(regs)
    for g in ag:
        print(f"  {g}: {ag[g].get(uf_c)}")
    # TabNet: uma célula (UF de conferência, internações, competência do arquivo)
    try:
        form = form_tabnet(buscar(TABNET_DEF, timeout=60).decode("latin-1"))
        aamm = f"{comp[2:4]}{comp[5:7]}"
        arq = [v for v, _t, _s in form.get("Arquivos", []) if aamm in v]
        linha = next((v for v, t, _s in form.get("Linha", []) if "Unidade da Federa" in t), None)
        incr = next((v for v, t, _s in form.get("Incremento", []) if t.startswith("Interna")), None)
        dados = {}
        for nome_s, ops in form.items():
            sel = [v for v, _t, s in ops if s] or ([ops[0][0]] if ops else [])
            dados[nome_s.encode("latin-1")] = (sel[0] if sel else "").encode("latin-1")
        dados.update({b"Linha": (linha or "").encode("latin-1"),
                      b"Coluna": "--Não-Ativa--".encode("latin-1"),
                      b"Incremento": (incr or "").encode("latin-1"),
                      b"Arquivos": (arq[0] if arq else "").encode("latin-1"),
                      b"formato": b"table", b"mostre": b"Mostra"})
        html = enviar(TABNET_TAB, dados, timeout=90).decode("latin-1")
        tab = celula_tabnet(html, nome_c)
        meu = ag.get("total", {}).get(uf_c, {}).get(comp)
        print(f"TabNet {nome_c} {comp}: {tab} · arquivo decodificado: {meu} · bate: {tab == meu}")
    except Exception as e:  # noqa: BLE001
        print(f"TabNet: falhou ({type(e).__name__}: {str(e)[:200]})")
    return 0


# ============================================================================================
# Autoteste (sem rede, sem escrita)
# ============================================================================================
def autoteste() -> int:
    casos = []
    casos.append(("J18 é respiratória", grupo_do_cid("J189") == ["respiratorias"]))
    casos.append(("I21 e I63 são cardio", grupo_do_cid("I219") == ["cardio"] == grupo_do_cid("I64")))
    casos.append(("I26 não é cardio deste recorte", grupo_do_cid("I26") == []))
    casos.append(("E86, T59, T67 e N18", [grupo_do_cid(c) for c in ("E86", "T590", "T671", "N189")]
                  == [["desidratacao"], ["fumaca"], ["calor"], ["renal"]]))
    casos.append(("CID ilegível não entra em grupo", grupo_do_cid("") == grupo_do_cid("9XX") == []))
    regs = [{"_UF": "AC", "ANO_CMPT": "2026", "MES_CMPT": "07", "IDENT": "1", "DIAG_PRINC": "J180"},
            {"_UF": "AC", "ANO_CMPT": "2026", "MES_CMPT": "07", "IDENT": "1", "DIAG_PRINC": "A09"},
            {"_UF": "AC", "ANO_CMPT": "2026", "MES_CMPT": "07", "IDENT": "5", "DIAG_PRINC": "J180"},
            {"_UF": "AC", "ANO_CMPT": "", "MES_CMPT": "07", "IDENT": "1", "DIAG_PRINC": "J180"}]
    ag = agregar(regs)
    casos.append(("total conta AIH não de longa permanência", ag["total"]["AC"] == {"2026-07": 2}))
    casos.append(("grupo conta só o seu CID", ag["respiratorias"]["AC"] == {"2026-07": 1}))
    casos.append(("competência ilegível não vira mês", "2026-00" not in ag["total"]["AC"]))
    casos.append(("mês lido sem caso do grupo é zero medido", ag["cardio"]["AC"] == {"2026-07": 0}))
    casos.append(("UF sem arquivo lido não aparece (ausência ≠ zero)", "RR" not in ag["cardio"]))
    ult = ultimo_por_uf(["RDAC2606.dbc", "RDAC2607.dbc", "RDSP2605.DBC", "LEIAME.txt", "RDBR2607.dbc"])
    casos.append(("última competência por UF", ult == {"AC": "2026-07", "SP": "2026-05", "BR": "2026-07"}))
    casos.append(("atraso em meses", meses_de_atraso("2026-07", datetime.date(2026, 10, 17)) == 3))
    html = ("<table><tr><th>UF</th><th>Interna&ccedil;&otilde;es</th></tr><tr><td>.. Acre<td>3.456"
            "<tr><td>Total</td><td>9.999</td></tr></table>")
    casos.append(("célula do TabNet com separador de milhar", celula_tabnet(html, "Acre") == 3456))
    casos.append(("rótulo ausente é None, não zero", celula_tabnet(html, "Roraima") is None))
    form = form_tabnet('<select name="Arquivos"><option value="niuf2607.dbf" selected>Jul/2026'
                       '<option value="niuf2606.dbf">Jun/2026</select>')
    casos.append(("lê o formulário", form == {"Arquivos": [("niuf2607.dbf", "Jul/2026", True),
                                                           ("niuf2606.dbf", "Jun/2026", False)]}))
    # ---- gravação na forma comum (fixtures; ler, gravar, listar, baixar e decodificar são falsos)
    gravados, lidos_n = {}, []

    def fake_ler(c):
        if c == "municipios_ibge_referencia.json":
            return [{"codigo_ibge": f"{i + 11}00000", "uf": u} for i, u in enumerate(UFS)]
        if c == "populacao_censo2022.json":
            return {f"{i + 11}00000": 100000 for i in range(27)}
        return gravados.get(c)

    def fake_gravar(c, obj, **_kw):
        gravados[c] = obj

    meses = ("2025-07", "2025-08")
    listagem = [(f"RD{u}{m[2:4]}{m[5:]}.dbc", 1000) for u in UFS for m in meses]

    def fake_baixar(caminho):
        lidos_n.append(caminho)
        return caminho

    def fake_decod(dados, campos):
        aa, mm = dados[-8:-6], dados[-6:-4]
        if "AC2507" in dados:
            raise OSError("fora do ar")
        reg = [{"ANO_CMPT": f"20{aa}", "MES_CMPT": mm, "IDENT": "1", "DIAG_PRINC": c}
               for c in ("J180", "J189", "I219", "A09", "B150")]
        return None, iter(reg)

    ok1 = coletar(lambda c: listagem, fake_baixar, fake_ler, fake_gravar, datetime.date(2026, 10, 19), fake_decod, pausa=0)
    o = gravados.get("saude_desfechos/internacoes_respiratorias.json", {})
    casos.append(("1ª rodada grava os sete arquivos comuns", ok1 and len(gravados) == 7))
    casos.append(("grupo conta só o seu CID; BR soma só onde as 27 UFs têm valor",
                  o["serie"]["SP"]["2025-08"] == 2 and o["serie"]["BR"]["2025-08"] == 54 and o["serie"]["BR"].get("2025-07") is None))
    casos.append(("mês que falhou (AC 2025-07) fica fora, não vira zero; lacuna declarada",
                  "2025-07" not in o["serie"]["AC"] and any("AC2507" in x for x in o["lacunas"])))
    casos.append(("hepatite A por B15 é zero medido onde o arquivo foi lido",
                  gravados["saude_desfechos/hepatite_a.json"]["serie"]["SP"]["2025-08"] == 1))
    casos.append(("cortes do mapa calculados sobre 2019 a 2025", len(o["cortes_mapa"]["cortes"]) == 4))
    # segunda rodada: nada novo, tamanhos iguais → só o mês que falhou é pedido de novo
    lidos_n.clear()
    coletar(lambda c: listagem, fake_baixar, fake_ler, fake_gravar, datetime.date(2026, 10, 20), fake_decod, pausa=0)
    casos.append(("2ª rodada pede só o que faltou", len(lidos_n) == 1 and lidos_n[0].endswith("RDAC2507.dbc")))
    # arquivo recente que mudou de tamanho é relido
    lidos_n.clear()
    listagem2 = [(n, 2000 if n.startswith("RDSP") else t) for n, t in listagem]
    coletar(lambda c: listagem2, fake_baixar, fake_ler, fake_gravar, datetime.date(2026, 10, 21), fake_decod, pausa=0)
    casos.append(("mês recente com tamanho novo é relido", sum("RDSP" in x for x in lidos_n) == 2))
    # orçamento de tempo e queda da fonte
    gravados.clear(); lidos_n.clear(); t = iter(range(0, 10 ** 6, 100))
    coletar(lambda c: listagem, fake_baixar, fake_ler, fake_gravar, datetime.date(2026, 10, 19), fake_decod,
            orcamento_s=350, relogio=lambda: next(t), pausa=0)
    casos.append(("orçamento acaba: lê o mais recente primeiro e declara os pendentes",
                  len(lidos_n) == 3 and all("2508" in x for x in lidos_n)
                  and any("ainda não lidos" in x for x in gravados["saude_desfechos/hepatite_a.json"]["lacunas"])))
    # leitura que completa depois de parcial: os cortes vêm de nova conta, não do arquivo que nasceu incompleto
    gravados["saude_desfechos/hepatite_a.json"]["cortes_mapa"]["cortes"] = [9, 9, 9, 9]
    coletar(lambda c: listagem, fake_baixar, fake_ler, fake_gravar, datetime.date(2026, 10, 20),
            lambda d, c: (None, iter([{"ANO_CMPT": "20" + d[-8:-6], "MES_CMPT": d[-6:-4], "IDENT": "1", "DIAG_PRINC": "B150"}])),
            pausa=0)
    h = gravados["saude_desfechos/hepatite_a.json"]
    casos.append(("completada a leitura, os cortes são recalculados e congelam",
                  h["cortes_mapa"]["cortes"] != [9, 9, 9, 9] and not h["lacunas"]))
    gravados.clear(); lidos_n.clear()
    caiu = coletar(lambda c: listagem, fake_baixar, fake_ler, fake_gravar, datetime.date(2026, 10, 19),
                   lambda d, c: (_ for _ in ()).throw(OSError("fora")), pausa=0)
    casos.append(("fonte fora do ar: nada gravado e a rodada para na 5ª falha seguida",
                  caiu is False and not gravados and PARADA_APOS <= len(lidos_n) < PARADA_APOS + JANELA))
    dormidas, relo = [], [0.0]
    e = espacar(lambda c: c, 2, dormir=lambda x: (dormidas.append(x), relo.__setitem__(0, relo[0] + x)),
                agora=lambda: relo[0])
    e("a"); e("b"); e("c")
    casos.append(("três downloads iniciam com no mínimo 2 s entre si", dormidas == [2, 2]))
    fila = a_ler(dict(listagem), set(), {})
    casos.append(("fila vai do mês mais recente ao mais antigo", fila[0][1] == "2025-08" and fila[-1][1] == "2025-07"))
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json")
    casos.append(("trava estrutural: não escreve nos arquivos do índice",
                  not any(p in fonte for p in proibidos)))
    casos.append(("trava estrutural: a sondagem não grava série (só o rastro de robots do `buscar`)",
                  "gravar" not in fonte.split("def sondar")[1]))
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--sondar" in sys.argv:
        return sondar()
    orcamento = int(sys.argv[sys.argv.index("--orcamento") + 1]) if "--orcamento" in sys.argv else ORCAMENTO_S
    return 0 if coletar(orcamento_s=orcamento) else 1


if __name__ == "__main__":
    sys.exit(main())
