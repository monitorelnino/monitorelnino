#!/usr/bin/env python3
"""SISAB, relatório público de produção da atenção primária: diarreias por UF e mês (janela E1, 17/10/2026).

HANDOVER_SUS_DESFECHOS §2.2. O relatório de produção do SISAB é formulário público, sem login
(robots.txt inexistente, 404), que exporta CSV de atendimentos individuais por estado e mês
(competência), com filtro por CIAP-2 e CID-10. É a rota de máquina que existe para as diarreias:
o Sivep-DDA não tem conjunto aberto nem página no TabNet público (sondagem de 17/10/2026).

O QUE A SÉRIE CONTA
-------------------
Atendimentos individuais na atenção primária registrados com CIAP-2 D11 (diarreia), D70 (infecção
gastrointestinal) ou D73 (gastroenterite, presumível infecção), ou CID-10 A00 a A09 (doenças
intestinais infecciosas), por UF e competência. É atendimento, não caso: a mesma pessoa pode voltar,
e a série acompanha também a adoção do registro eletrônico na atenção primária ao longo dos anos.
O relatório avisa "dados sujeitos à alteração": as duas últimas competências são parciais.

DETECTOR DE MUDANÇA DE TELA
--------------------------
O CSV devolve a lista dos filtros que aplicou. O coletor confere que a lista de CIAP/CID é
exatamente a pedida e que o cabeçalho é "Estado;<competências>"; qualquer diferença é lacuna
declarada, e o arquivo anterior fica.

USO
  python3 coletar_sisab.py --autoteste
  python3 coletar_sisab.py --desfecho diarreias
"""
import http.cookiejar
import re
import sys
import time
import urllib.parse
import urllib.request

from coletores_base import ua_de, rodar_autoteste, normalizar_nome, detectar_muro_de_robo

RELATORIO = ("https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/"
             "RelSauProducao.xhtml")
PAUSA = 2
MESES = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
         "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}
DESFECHOS = {
    "diarreias": {
        "rotulo": "Diarreias, atendimentos na atenção primária",
        # sufixo -4 = CIAP-2, -1 = CID-10, como o próprio formulário os nomeia
        "codigos": ("D11-4", "D70-4", "D73-4") + tuple(f"A0{i}-1" for i in range(10)),
        "criterio": "atendimento individual com CIAP-2 D11, D70 ou D73, ou CID-10 A00 a A09",
        "n_parciais": 2,
    },
}
ANO_INICIAL = 2019


class TelaMudou(ValueError):
    """O formulário ou o CSV do SISAB não têm a forma esperada: lacuna, nunca número."""


# ---------------------------------------------------------------- funções puras
def formulario(pagina: str) -> dict:
    """ViewState, ação, competências oferecidas e códigos CIAP/CID do formulário. Função pura."""
    vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', pagina)
    acao = re.search(r'<form id="j_idt44"[^>]*action="([^"]+)"', pagina)
    csv = re.search(r"\{'(j_idt\d+)':'\1'\},''\);return false\">Csv<", pagina)
    if not (vs and acao and csv):
        raise TelaMudou("formulário do SISAB sem ViewState, ação ou botão de CSV")
    return {"viewstate": vs.group(1), "acao": acao.group(1), "csv": csv.group(1),
            "competencias": re.findall(r'<option value="(\d{6})">[A-Z]{3}/\d{4}</option>', pagina),
            "codigos": set(re.findall(r'id="cid-([A-Z0-9]+-[14])"', pagina)),
            "equipes": re.findall(r'<option value="(eq-[a-z]+)"', pagina)}


def corpo_da_consulta(form: dict, competencias: list, codigos: tuple) -> list:
    """Campos do POST: linha Estado, coluna Competência, atendimento individual. Função pura."""
    campos = [("j_idt44", "j_idt44"), ("unidGeo", "brasil"), ("selectLinha", "ATD.CO_UF_IBGE"),
              ("selectcoluna", "NU_COMPETENCIA"), ("tpProducao", "4"), ("lsCid", ",".join(codigos) + ","),
              ("javax.faces.ViewState", form["viewstate"]), (form["csv"], form["csv"])]
    campos += [("j_idt76", c) for c in competencias] + [("j_idt89", e) for e in form["equipes"]]
    return campos


def ler_csv(texto: str, codigos: tuple, siglas: dict) -> dict:
    """{UF: {AAAA-MM: int}} do CSV, depois de conferir os filtros aplicados. Função pura.

    `siglas` = {NOME NORMALIZADO: sigla}. Célula vazia é lacuna (None), nunca zero."""
    filtro = re.search(r'"CIAP/CID: (.*?)\."', texto, re.S)
    if not filtro:
        raise TelaMudou("CSV sem a linha de filtros CIAP/CID")
    aplicados = {f"{c}-{'4' if t == 'CIAP' else '1'}" for t, c in re.findall(r"(CIAP|CID) \(([A-Z0-9]+)\)", filtro.group(1))}
    if aplicados != set(codigos):
        raise TelaMudou(f"filtros aplicados diferentes dos pedidos: {sorted(aplicados ^ set(codigos))}")
    if "Tipo de Produção: Atendimento Individual" not in texto:
        raise TelaMudou("CSV sem o tipo de produção pedido")
    linhas = [(ln[:-1] if ln.endswith(";") else ln).split(";") for ln in texto.splitlines()]
    cab = next((ln for ln in linhas if ln and ln[0] == "Estado"), None)
    if not cab or len(cab) < 2:
        raise TelaMudou("CSV sem o cabeçalho Estado;competências")
    pers = []
    for c in cab[1:]:
        m = re.fullmatch(r"([A-Z]{3})/(\d{4})", c.strip())
        if not m or m.group(1) not in MESES:
            raise TelaMudou(f"competência ilegível no cabeçalho: {c!r}")
        pers.append(f"{m.group(2)}-{MESES[m.group(1)]:02d}")
    out = {}
    for ln in linhas[linhas.index(cab) + 1:]:
        if len(ln) != len(cab):
            continue
        uf = siglas.get(normalizar_nome(ln[0]))
        if not uf:
            continue
        out[uf] = {p: (int(v.replace(".", "")) if v.strip().replace(".", "").isdigit() else None)
                   for p, v in zip(pers, ln[1:])}
    if len(out) != 27:
        raise TelaMudou(f"CSV com {len(out)} UFs, esperadas 27")
    return out


def lotes(competencias: list, ano_inicial: int = ANO_INICIAL) -> list:
    """Competências de `ano_inicial` em diante, em lotes de um ano. Função pura."""
    por_ano = {}
    for c in sorted(competencias):
        if int(c[:4]) >= ano_inicial:
            por_ano.setdefault(c[:4], []).append(c)
    return [por_ano[a] for a in sorted(por_ano)]


def siglas_de(geo: dict) -> dict:
    return {normalizar_nome(f["properties"]["name"]): f["properties"]["sigla"] for f in geo.get("features", [])}


# ---------------------------------------------------------------- rede
class Sessao:
    """Uma sessão do formulário (o JSF guarda o estado no cookie), cliente identificado."""

    def __init__(self, timeout: int = 180):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.ua = ua_de("SISAB relatorio publico")
        self.timeout = timeout

    def pedir(self, url: str, campos=None) -> bytes:
        time.sleep(PAUSA)
        dados = urllib.parse.urlencode(campos).encode() if campos is not None else None
        cab = {"User-Agent": self.ua}
        if dados is not None:
            cab["Content-Type"] = "application/x-www-form-urlencoded"
        with self.op.open(urllib.request.Request(url, data=dados, headers=cab), timeout=self.timeout) as r:
            corpo = r.read()
        marca = detectar_muro_de_robo(corpo)
        if marca:
            raise TelaMudou(f"muro de robô no SISAB: {marca}")
        return corpo


def baixar_serie(codigos: tuple, siglas: dict, sessao=None) -> tuple:
    """({UF: {AAAA-MM: int}}, competências lidas), lote a lote, numa sessão."""
    s = sessao or Sessao()
    form = formulario(s.pedir(RELATORIO).decode("utf-8", "replace"))
    falta = set(codigos) - form["codigos"]
    if falta:
        raise TelaMudou(f"códigos ausentes do formulário: {sorted(falta)}")
    url = urllib.parse.urljoin(RELATORIO, form["acao"])
    serie = {}
    for lote in lotes(form["competencias"]):
        texto = s.pedir(url, corpo_da_consulta(form, lote, codigos)).decode("latin-1")
        for uf, meses in ler_csv(texto, codigos, siglas).items():
            serie.setdefault(uf, {}).update(meses)
    return serie, sorted(form["competencias"])


def coletar(nome: str, baixar=None, ler_fn=None, gravar_fn=None, hoje: str = None) -> bool:
    """Lê o SISAB e grava o arquivo comum; só regrava se a série mudou."""
    import desfechos_sus as ds
    from coletores_base import ler, gravar, data_da_edicao
    ler_fn = ler_fn or ler; gravar_fn = gravar_fn or gravar
    cfg = DESFECHOS[nome]
    siglas = siglas_de(ler_fn("geo_uf.json") or {})
    serie, _ = (baixar or baixar_serie)(cfg["codigos"], siglas)
    anterior = ler_fn(ds.caminho(nome))
    if anterior and {u: s for u, s in anterior.get("serie", {}).items() if u != "BR"} == serie:
        print(f"{nome}: série do SISAB igual à última leitura; nada a regravar"); return False
    data = hoje or data_da_edicao().isoformat()
    fonte = {"sistema": "SISAB (Ministério da Saúde/SAPS), relatório público de produção", "url": RELATORIO,
             "criterio": cfg["criterio"], "producao": "atendimento individual, todas as equipes",
             "uf": "UF do estabelecimento (linha Estado do relatório)", "lido_em": data}
    obj = ds.montar(desfecho=nome, rotulo=cfg["rotulo"], unidade="atendimentos", periodo="mes",
                    territorio="UF", serie=serie, fonte=fonte,
                    cadencia="mensal; o SISAB fecha a competência depois do envio dos municípios",
                    coletado_em=data, anos_preliminares=[int(data[:4])], n_parciais=cfg["n_parciais"],
                    populacao=ds.populacao_por_uf(ler_fn), anterior=anterior)
    return ds.gravar_desfecho(obj, gravar_fn=gravar_fn)


# ---------------------------------------------------------------- autoteste
_PAGINA = ('<form id="j_idt44" name="j_idt44" method="post" action="/paginas/x.xhtml;jsessionid=AB">'
           '<select name="j_idt76"><option value="202608">AGO/2026</option><option value="202607">JUL/2026</option>'
           '<option value="201812">DEZ/2018</option></select>'
           '<select name="j_idt89"><option value="eq-esf">ESF</option></select>'
           + "".join(f'<input type="checkbox" id="cid-{c}" />' for c in DESFECHOS["diarreias"]["codigos"]) +
           '<a href="#" onclick="mojarra.jsfcljs(document.getElementById(\'j_idt44\'),{\'j_idt192\':\'j_idt192\'},\'\');return false">Csv</a>'
           '<input type="hidden" name="javax.faces.ViewState" value="vs:1" /></form>')
_SIGLAS = {normalizar_nome(n): s for s, n in [("AC", "Acre"), ("SP", "São Paulo")] + [(f"X{i}", f"UF {i}") for i in range(25)]}


def _csv(codigos=None, linhas=None):
    cods = codigos or DESFECHOS["diarreias"]["codigos"]
    filtro = ", ".join(f"{'CIAP' if c.endswith('-4') else 'CID'} ({c[:-2]}) Nome" for c in cods)
    corpo = linhas if linhas is not None else (["ACRE;1.398;1.445;", "SAO PAULO;50.906;;"] + [f"UF {i};1;2;" for i in range(25)])
    return ('Secretaria de Atenção Primária à Saúde - SAPS/MS \nDados sujeitos à alteração \n'
            '"Competência: AGO/2026, JUL/2026."\nTipo de Produção: Atendimento Individual.\n'
            f'"CIAP/CID: {filtro}."\n\n\nEstado;AGO/2026;JUL/2026;\n' + "\n".join(corpo) + "\n\nFonte: SISAB;\n")


def _t_formulario():
    f = formulario(_PAGINA)
    c = corpo_da_consulta(f, ["202608"], ("D11-4",))
    return (f["csv"] == "j_idt192" and f["viewstate"] == "vs:1" and f["equipes"] == ["eq-esf"]
            and ("lsCid", "D11-4,") in c and ("j_idt192", "j_idt192") in c and ("j_idt76", "202608") in c)


def _t_csv():
    s = ler_csv(_csv(), DESFECHOS["diarreias"]["codigos"], _SIGLAS)
    return s["AC"] == {"2026-08": 1398, "2026-07": 1445} and s["SP"] == {"2026-08": 50906, "2026-07": None}


def _t_filtro_diferente_recusa():
    try:
        ler_csv(_csv(codigos=("D11-4", "A09-1")), DESFECHOS["diarreias"]["codigos"], _SIGLAS); return False
    except TelaMudou:
        return True


def _t_ufs_faltando_recusa():
    try:
        ler_csv(_csv(linhas=["ACRE;1;2;"]), DESFECHOS["diarreias"]["codigos"], _SIGLAS); return False
    except TelaMudou:
        return True


def _t_tela_mudou():
    try:
        formulario("<html>Em manutenção</html>"); return False
    except TelaMudou:
        return True


def _t_lotes():
    return lotes(["201812", "201901", "201902", "202001"]) == [["201901", "201902"], ["202001"]]


def _t_coletar_offline_e_idempotente():
    siglas = ["RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA",
              "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF"]
    serie = {u: {f"{a}-{m:02d}": 10 + m for a in range(2019, 2027) for m in range(1, 13)} for u in siglas}
    banco = {"geo_uf.json": {"features": []},
             "municipios_ibge_referencia.json": [{"codigo_ibge": 1100015 + i, "uf": u} for i, u in enumerate(siglas)],
             "populacao_censo2022.json": {str(1100015 + i): 1000 for i in range(27)}}
    escritos = []
    def gravar_falso(nome, obj, compacto=False):
        banco[nome] = obj; escritos.append(nome)
    kw = dict(baixar=lambda c, s: (serie, []), ler_fn=banco.get, gravar_fn=gravar_falso, hoje="2026-10-17")
    ok1 = coletar("diarreias", **kw); ok2 = coletar("diarreias", **kw)
    o = banco.get("saude_desfechos/diarreias.json") or {}
    return ok1 and not ok2 and escritos == ["saude_desfechos/diarreias.json"] and o["parcial"] == ["2026-11", "2026-12"] \
        and o["por_100mil"]["CE"]["2019-01"] == 1100.0


def _t_fonte_nao_escreve_banco():
    from desfechos_sus import fonte_cita_banco
    return not fonte_cita_banco(__file__)


TESTES = {
    "formulário: ViewState, botão de CSV, competências, códigos": _t_formulario,
    "CSV: milhar, célula vazia é lacuna": _t_csv,
    "filtro aplicado diferente do pedido é recusa": _t_filtro_diferente_recusa,
    "CSV sem as 27 UFs é recusa": _t_ufs_faltando_recusa,
    "tela mudada é recusa, nunca número": _t_tela_mudou,
    "lotes anuais desde 2019": _t_lotes,
    "coleta ponta a ponta offline; série igual não regrava": _t_coletar_offline_e_idempotente,
    "trava estrutural: não escreve nos arquivos do índice": _t_fonte_nao_escreve_banco,
}

if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(rodar_autoteste(TESTES))
    if "--desfecho" in sys.argv:
        nome = sys.argv[sys.argv.index("--desfecho") + 1]
        try:
            coletar(nome)
        except Exception as e:  # noqa: BLE001 — falha de fonte é lacuna; o arquivo anterior fica
            from coletores_base import registrar_lacuna
            registrar_lacuna(f"{RELATORIO} ({nome})", f"{type(e).__name__}: {e}; o arquivo anterior fica",
                             canal="desfechos_sus", camada=3)
            sys.exit(1)
        sys.exit(0)
    print(__doc__)
