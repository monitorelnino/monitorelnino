#!/usr/bin/env python3
"""Internações do SUS por grupo de causa, UF e mês: SIH/SUS (AIH reduzida, arquivos RD do DATASUS).

Faixa E2 (HANDOVER_SUS_DESFECHOS_16-10-2026, camada C). Peso zero, como todo o MARÉ Saúde: conta
internações registradas; não atribui nenhuma ao El Niño.

O QUE A SÉRIE CONTA
-------------------
Internações aprovadas (AIH) por UF do HOSPITAL e mês de PROCESSAMENTO: uma célula UF × mês é um
arquivo `RD<UF><AAMM>.dbc`, contado inteiro, sem a AIH de longa permanência (`IDENT` 5), como o
TabNet "Internações por local de internação" (conferido em 17/10/2026: Amapá, jul/2026, 6.160 e
6.160). O grupo vem do diagnóstico principal (`DIAG_PRINC`). Arquivo lido sem caso do grupo é zero
medido; mês sem arquivo publicado é `null` (lacuna), nunca zero.

ROTA E RITMO
------------
FTP público do DATASUS, pelo leitor `.dbc` e pelo FTP de `coletar_datasus_dbc.py` (E1, importados:
senha anônima que identifica o cliente, pausa entre conexões, novas tentativas). São ~2.500 arquivos
e ~7 GB de 2019 em diante (medido em 17/10/2026; ~2,4 s por MB entre baixar e ler), então a rodada
tem PRAZO: lê do mais novo para o mais velho até o prazo, grava o progresso
(`internacoes_progresso.json`: tamanho de cada arquivo lido e as contagens) e a rodada seguinte
continua. Arquivo republicado com outro tamanho é relido. Os arquivos por grupo só nascem com o
histórico completo, porque os cortes do mapa são congelados na primeira gravação.

USO
  python3 coletar_sih.py --autoteste
  python3 coletar_sih.py --sondar          # só mede e imprime (inclui a célula do TabNet)
  python3 coletar_sih.py [--prazo 40]      # minutos de leitura nesta rodada
"""
import datetime
import pathlib
import re
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

FTP_DIR_RD = "/dissemin/publicos/SIHSUS/200801_/Dados"
CAMPOS = ("IDENT", "DIAG_PRINC")
DESDE = "2019-01"
PROGRESSO = "saude_desfechos/internacoes_progresso.json"
PRAZO_MIN = 40
TABNET_DEF = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/niuf.def"
TABNET_TAB = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/niuf.def"
UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()
RE_RD = re.compile(r"^RD([A-Z]{2})(\d{2})(\d{2})\.DBC$", re.I)

# grupo -> faixas de CID-10 (inclusivas, três caracteres), do mapa do handover §1, e o rótulo.
GRUPOS = {
    "respiratorias": ([("J00", "J22")], "Internações por infecções respiratórias agudas (CID-10 J00–J22)"),
    "cardio": ([("I20", "I25"), ("I60", "I64")],
               "Internações por doenças isquêmicas do coração e cerebrovasculares (CID-10 I20–I25, I60–I64)"),
    "renal": ([("N17", "N19")], "Internações por insuficiência renal (CID-10 N17–N19)"),
    "desidratacao": ([("E86", "E86")], "Internações por desidratação (CID-10 E86)"),
    "fumaca": ([("T59", "T59")], "Internações por efeito tóxico de gases, fumaças e vapores (CID-10 T59)"),
    "calor": ([("T67", "T67")], "Internações por efeitos do calor e da luz (CID-10 T67)"),
}


# ============================================================================================
# Funções puras
# ============================================================================================
def grupo_do_cid(cid: str) -> list:
    """Grupos aos quais o CID principal pertence (pelos três primeiros caracteres). Função pura."""
    c = (cid or "").strip().upper()[:3]
    if not re.fullmatch(r"[A-Z]\d{2}", c):
        return []
    return [g for g, (faixas, _r) in GRUPOS.items() if any(a <= c <= b for a, b in faixas)]


def contar_arquivo(linhas) -> dict:
    """{'total': n, grupo: n, ...} de um arquivo RD inteiro; grupo sem caso é 0. Função pura."""
    out = dict.fromkeys(["total", *GRUPOS], 0)
    for r in linhas:
        if str(r.get("IDENT") or "").strip() == "5":
            continue
        out["total"] += 1
        for g in grupo_do_cid(r.get("DIAG_PRINC")):
            out[g] += 1
    return out


def arquivos_rd(listagem, desde: str = DESDE) -> dict:
    """{(UF, 'AAAA-MM'): (nome, tamanho)} dos RD de `desde` em diante. Função pura."""
    out = {}
    for nome, tam in listagem:
        m = RE_RD.match((nome or "").strip())
        if m and m.group(1).upper() in UFS:
            comp = f"{2000 + int(m.group(2)):04d}-{m.group(3)}"
            if comp >= desde:
                out[(m.group(1).upper(), comp)] = (nome, tam)
    return out


def pendentes(arqs: dict, progresso: dict) -> list:
    """Chaves a ler, do mês mais novo para o mais velho: nunca lidas ou com outro tamanho. Pura."""
    lidos = (progresso or {}).get("arquivos") or {}
    return sorted((k for k, (nome, tam) in arqs.items() if lidos.get(nome) != tam),
                  key=lambda k: (k[1], k[0]), reverse=True)


def series(progresso: dict, arqs: dict) -> dict:
    """{grupo: {UF: {AAAA-MM: n | None}}} de `DESDE` ao mês mais recente publicado. Função pura."""
    cont = (progresso or {}).get("contagens") or {}
    fim = max(c for _u, c in arqs)
    a, m = int(DESDE[:4]), int(DESDE[5:])
    chaves = []
    while f"{a:04d}-{m:02d}" <= fim:
        chaves.append(f"{a:04d}-{m:02d}")
        a, m = a + (m == 12), m % 12 + 1
    return {g: {uf: {p: (cont.get(f"{uf}|{p}") or {}).get(g) for p in chaves} for uf in UFS} for g in GRUPOS}


def ultimo_por_uf(arqs: dict) -> dict:
    """{UF: 'AAAA-MM'} da competência mais recente publicada. Função pura."""
    out = {}
    for uf, comp in arqs:
        out[uf] = max(comp, out.get(uf, ""))
    return out


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
# Coleta
# ============================================================================================
def coletar(listar=None, baixar=None, decodificar=None, ler_fn=None, gravar_fn=None, hoje=None,
            prazo_s: float = PRAZO_MIN * 60, relogio=time.monotonic) -> bool:
    """Lê arquivos até o prazo, grava o progresso e, com o histórico completo, os arquivos por grupo."""
    import desfechos_sus as ds
    from coletar_datasus_dbc import baixar_ftp, ler_dbc, listar_ftp
    from coletores_base import gravar, hoje_editorial, ler
    listar = listar or listar_ftp
    baixar = baixar or baixar_ftp
    decodificar = decodificar or (lambda b: ler_dbc(b, CAMPOS)[1])
    ler_fn = ler_fn or ler
    gravar_fn = gravar_fn or gravar
    hoje = hoje or hoje_editorial()
    arqs = arquivos_rd(listar(FTP_DIR_RD))
    if not arqs:
        print("SIH: nenhum arquivo RD na listagem do FTP; nada a gravar")
        return False
    progresso = ler_fn(PROGRESSO) or {"arquivos": {}, "contagens": {}}
    falhas, lidos, t0 = [], 0, relogio()
    for uf, comp in pendentes(arqs, progresso):
        if relogio() - t0 > prazo_s:
            break
        nome, tam = arqs[(uf, comp)]
        try:
            progresso["contagens"][f"{uf}|{comp}"] = contar_arquivo(decodificar(baixar(f"{FTP_DIR_RD}/{nome}")))
            progresso["arquivos"][nome] = tam
            lidos += 1
        except Exception as e:  # noqa: BLE001 — arquivo que falha fica pendente para a próxima rodada
            falhas.append(f"{nome}: {type(e).__name__}")
    faltam = len(pendentes(arqs, progresso))
    progresso.update({"atualizado_em": hoje.isoformat(), "faltam": faltam, "falhas_da_rodada": falhas})
    if lidos:
        gravar_fn(PROGRESSO, progresso, compacto=True)
    print(f"SIH: {lidos} arquivo(s) lido(s), {len(falhas)} falha(s), faltam {faltam} de {len(arqs)}")
    ja_gravados = all(ler_fn(ds.caminho(f"internacoes_{g}")) for g in GRUPOS)
    if faltam or (not lidos and ja_gravados):
        return bool(lidos)
    pop, ult = ds.populacao_por_uf(ler_fn), ultimo_por_uf(arqs)
    atrasadas = sorted(uf for uf, c in ult.items() if c < max(ult.values()))
    lacunas = [f"UF ainda sem o mês mais recente no FTP: {', '.join(atrasadas)}"] if atrasadas else []
    fonte = {"sistema": "SIH/SUS (Ministério da Saúde), arquivos RD no FTP do DATASUS",
             "url": f"ftp://ftp.datasus.gov.br{FTP_DIR_RD}/", "conta": "AIH aprovadas, sem longa permanência",
             "uf": "do hospital", "mes": "de processamento", "arquivos_lidos": len(progresso["arquivos"])}
    ok = True
    for g, serie in series(progresso, arqs).items():
        nome = f"internacoes_{g}"
        obj = ds.montar(desfecho=nome, rotulo=GRUPOS[g][1], unidade="internações", periodo="mes",
                        territorio="UF do hospital", serie=serie, fonte=fonte,
                        cadencia="mensal; o DATASUS publica cada mês com cerca de dois meses de atraso",
                        coletado_em=hoje.isoformat(), populacao=pop, anterior=ler_fn(ds.caminho(nome)),
                        lacunas=lacunas)
        ok = ds.gravar_desfecho(obj, gravar_fn=gravar_fn) and ok
    return ok


# ============================================================================================
# Sondagem (rede; só mede e imprime)
# ============================================================================================
def sondar() -> int:
    from coletar_datasus_dbc import baixar_ftp, ler_dbc, listar_ftp
    from coletores_base import buscar, enviar, hoje_editorial
    print(f"== SIH/SUS · FTP {FTP_DIR_RD} · {hoje_editorial()}")
    arqs = arquivos_rd(listar_ftp(FTP_DIR_RD))
    ult = ultimo_por_uf(arqs)
    print(f"  {len(arqs)} arquivos desde {DESDE}; mais recente por UF: {ult}")
    uf_c, nome_c = "AP", "Amapá"  # UF pequena para a célula de conferência
    comp = ult.get(uf_c)
    if not comp:
        return 0
    meu = contar_arquivo(ler_dbc(baixar_ftp(f"{FTP_DIR_RD}/{arqs[(uf_c, comp)][0]}"), CAMPOS)[1])
    print(f"  {uf_c} {comp}: {meu}")
    try:
        form = form_tabnet(buscar(TABNET_DEF, timeout=60).decode("latin-1"))
        arq = [v for v, _t, _s in form.get("Arquivos", []) if f"{comp[2:4]}{comp[5:7]}" in v]
        dados = {k.encode("latin-1"): ([v for v, _t, s in ops if s] or [ops[0][0] if ops else ""])[0].encode("latin-1")
                 for k, ops in form.items()}
        linha = next((v for v, t, _s in form.get("Linha", []) if "Unidade da Federa" in t), "")
        incr = next((v for v, t, _s in form.get("Incremento", []) if t.startswith("Interna")), "")
        dados.update({b"Linha": linha.encode("latin-1"), b"Coluna": "--Não-Ativa--".encode("latin-1"),
                      b"Incremento": incr.encode("latin-1"), b"Arquivos": (arq[0] if arq else "").encode("latin-1"),
                      b"formato": b"table", b"mostre": b"Mostra"})
        tab = celula_tabnet(enviar(TABNET_TAB, dados, timeout=90).decode("latin-1"), nome_c)
        print(f"  TabNet {nome_c} {comp}: {tab} · arquivo: {meu['total']} · bate: {tab == meu['total']}")
    except Exception as e:  # noqa: BLE001
        print(f"  TabNet: falhou ({type(e).__name__}: {str(e)[:200]})")
    return 0


# ============================================================================================
# Autoteste (sem rede, sem escrita: listar, baixar, ler e gravar são falsos)
# ============================================================================================
def _falsos(progresso=None, tamanhos=None):
    tamanhos = tamanhos or {}
    listagem = [(f"RD{uf}{a % 100:02d}{m:02d}.dbc", tamanhos.get(uf, 10))
                for uf in UFS for a in range(2019, 2027) for m in range(1, 13) if (a, m) <= (2026, 8)]
    listagem += [("RDAC1812.dbc", 10), ("LEIAME.txt", 1)]
    banco, baixados = {PROGRESSO: progresso}, []

    def baixar(c):
        baixados.append(c)
        return c.encode()

    def decodificar(_b):
        return [{"IDENT": "1", "DIAG_PRINC": "J180"}, {"IDENT": "1", "DIAG_PRINC": "A09"},
                {"IDENT": "5", "DIAG_PRINC": "J180"}]

    def ler_fn(c):
        if c == "municipios_ibge_referencia.json":
            return [{"codigo_ibge": f"{i + 11}00000", "uf": u} for i, u in enumerate(UFS)]
        if c == "populacao_censo2022.json":
            return {f"{i + 11}00000": 100000 for i in range(27)}
        return banco.get(c)

    def gravar_fn(c, obj, **_kw):
        banco[c] = obj
    return dict(listar=lambda _d: listagem, baixar=baixar, decodificar=decodificar, ler_fn=ler_fn,
                gravar_fn=gravar_fn, hoje=datetime.date(2026, 10, 17)), banco, baixados


def _t_grupos():
    return (grupo_do_cid("J189") == ["respiratorias"] and grupo_do_cid("I219") == ["cardio"] == grupo_do_cid("I64")
            and grupo_do_cid("I26") == [] and grupo_do_cid("") == grupo_do_cid("9XX") == []
            and [grupo_do_cid(c) for c in ("E86", "T590", "T671", "N189")]
            == [["desidratacao"], ["fumaca"], ["calor"], ["renal"]])


def _t_contar():
    c = contar_arquivo([{"IDENT": "1", "DIAG_PRINC": "J180"}, {"IDENT": "1", "DIAG_PRINC": "A09"},
                        {"IDENT": "5", "DIAG_PRINC": "J180"}])
    return c["total"] == 2 and c["respiratorias"] == 1 and c["cardio"] == 0


def _t_prazo():
    kw, banco, baixados = _falsos()
    passos = iter(range(10**6))
    coletar(**kw, prazo_s=4, relogio=lambda: next(passos))
    p = banco[PROGRESSO]
    return (len(baixados) == 4 and p["faltam"] == 27 * 92 - 4 and "RDSP2608.dbc" in p["arquivos"]
            and not any(k.startswith("saude_desfechos/internacoes_r") for k in banco))


def _t_completo():
    kw, banco, _b = _falsos()
    coletar(**kw)
    o = banco["saude_desfechos/internacoes_respiratorias.json"]
    c = banco["saude_desfechos/internacoes_cardio.json"]
    return (o["serie"]["AC"]["2019-01"] == 1 and c["serie"]["SP"]["2026-08"] == 0 and o["serie"]["BR"]["2026-08"] == 27
            and "2018-12" not in o["serie"]["AC"] and o["territorio"] == "UF do hospital")


def _t_rele_so_o_que_mudou():
    kw, banco, _b = _falsos()
    coletar(**kw)
    kw2, _banco2, baixados2 = _falsos(progresso=banco[PROGRESSO], tamanhos={"RR": 11})
    coletar(**kw2)
    return len(baixados2) == 92 and all("RDRR" in c for c in baixados2)


def _t_mes_sem_arquivo_e_null():
    arqs = arquivos_rd([("RDAC1901.dbc", 1), ("RDAC1903.dbc", 1), ("RDSP1903.dbc", 1)])
    prog = {"contagens": {"AC|2019-01": {"respiratorias": 2}, "AC|2019-03": {"respiratorias": 0},
                          "SP|2019-03": {"respiratorias": 5}}}
    s = series(prog, arqs)["respiratorias"]
    return s["AC"] == {"2019-01": 2, "2019-02": None, "2019-03": 0} and s["SP"]["2019-01"] is None


def _t_trava_estrutural():
    texto = pathlib.Path(__file__).read_text(encoding="utf-8")
    corpo = texto.split("# Autoteste")[0]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json\"", "indice.json", "monitor_saude.json")
    sonda = texto.split("def sondar")[1].split("# =====")[0]
    return not any(p in corpo for p in proibidos) and "gravar" not in sonda


TESTES = {
    "grupos de CID do handover": _t_grupos,
    "arquivo contado inteiro, sem longa permanência; grupo sem caso é zero": _t_contar,
    "prazo: lê do mais novo, grava o progresso, não grava grupo com histórico incompleto": _t_prazo,
    "histórico completo: seis arquivos pela forma comum, 2018 fora, zero medido": _t_completo,
    "arquivo republicado com outro tamanho é relido, e só ele": _t_rele_so_o_que_mudou,
    "mês sem arquivo publicado é null, não zero": _t_mes_sem_arquivo_e_null,
    "trava estrutural: não escreve no índice; a sondagem não grava": _t_trava_estrutural,
}


def main() -> int:
    from coletores_base import rodar_autoteste
    if "--autoteste" in sys.argv:
        return rodar_autoteste(TESTES)
    if "--sondar" in sys.argv:
        return sondar()
    prazo = PRAZO_MIN
    if "--prazo" in sys.argv:
        prazo = float(sys.argv[sys.argv.index("--prazo") + 1])
    coletar(prazo_s=prazo * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
