#!/usr/bin/env python3
"""TabNet do DATASUS, último recurso (janela E1, 17/10/2026).

Decisão da editoria (16/10, 20:45 UTC; HANDOVER_SUS_DESFECHOS §2.3 e §3.2): o TabNet entra como
consulta pública automatizada, sem contrato de máquina, só para desfecho sem outra rota (DDA, DTHA,
malária). Travas: cliente identificado (`coletores_base.enviar`), uma consulta por desfecho e
rodada, parar no primeiro 401/403/429, e detector de mudança de tela: formulário sem os campos
esperados é lacuna declarada, nunca número velho apresentado como novo.

USO
  python3 coletar_tabnet.py --autoteste
  python3 coletar_tabnet.py --sondar        # só mede e imprime; não escreve em data/
"""
import html as _html
import re
import urllib.parse
import sys
import time

from coletores_base import buscar, enviar, rodar_autoteste

TABNET = "http://tabnet.datasus.gov.br/cgi/"
TODAS = "TODAS_AS_CATEGORIAS__"


class TelaMudou(ValueError):
    """O formulário ou a resposta do TabNet não têm a forma esperada: lacuna, nunca número."""


def formulario(pagina: str) -> dict:
    """{'acao', 'selects': {nome: [(valor, rotulo, marcado)]}} do formulário de um `.def`. Função pura."""
    m = re.search(r'<form[^>]*action="([^"]+)"', pagina, re.I)
    if not m:
        raise TelaMudou("página do TabNet sem formulário")
    selects = {}
    for nome, corpo in re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', pagina, re.I | re.S):
        ops = re.findall(r'<option([^>]*)value="([^"]*)"[^>]*>([^<]*)', corpo, re.I)
        selects[nome] = [(v, _html.unescape(r).strip(), "selected" in a.lower()) for a, v, r in ops]
    return {"acao": _html.unescape(m.group(1)), "selects": selects}


def ler_prn(pagina: str) -> list:
    """Linhas (listas de células) da tabela em formato `prn` (separada por `;`, dentro de <PRE>). Função pura."""
    m = re.search(r"<pre>(.*?)</pre>", pagina, re.I | re.S)
    if not m:
        raise TelaMudou("resposta do TabNet sem tabela <PRE>")
    linhas = []
    for ln in _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).splitlines():
        if ";" in ln:
            linhas.append([c.strip().strip('"') for c in ln.split(";")])
    if len(linhas) < 2:
        raise TelaMudou("tabela do TabNet vazia")
    return linhas


def consulta(form: dict, linha: str, coluna: str, incremento: str, arquivos: list) -> dict:
    """Corpo do POST: rótulos exatos do formulário; todo filtro `S*` em todas as categorias."""
    corpo = {"Linha": linha, "Coluna": coluna, "Incremento": incremento, "Arquivos": arquivos,
             "formato": "prn", "mostre": "Mostra"}
    for nome in form["selects"]:
        if nome.startswith("S") and nome not in corpo:
            corpo[nome] = TODAS
    return corpo


def _codificar(corpo: dict) -> dict:
    # O TabNet é latin-1: os rótulos vão como bytes nessa codificação. Lista vira valor repetido.
    out = []
    for k, v in corpo.items():
        for x in (v if isinstance(v, list) else [v]):
            out.append((k.encode("latin-1"), x.encode("latin-1")))
    return out


def sondar_def(caminho_def: str, procura_linha: str, procura_incr: str = "") -> None:
    url = f"{TABNET}deftohtm.exe?{caminho_def}"
    t0 = time.time()
    try:
        pag = buscar(url, timeout=60).decode("latin-1")
    except Exception as e:  # noqa: BLE001
        print(f"[tabnet] {caminho_def}: FALHA {type(e).__name__}: {e}"); return
    f = formulario(pag)
    sel = f["selects"]
    print(f"[tabnet] {caminho_def}: {len(pag)} B em {time.time()-t0:.1f}s; ação {f['acao']}; selects {list(sel)}")
    for k in ("Linha", "Coluna", "Incremento", "Arquivos"):
        print(f"   {k}: {[r for _, r, _ in sel.get(k, [])][:40]}")
    linha = next((v for v, r, _ in sel.get("Linha", []) if procura_linha.lower() in r.lower()), None)
    incr = next((v for v, r, _ in sel.get("Incremento", []) if procura_incr.lower() in r.lower()), None) \
        or (sel.get("Incremento") or [(None,)])[0][0]
    arq = [v for v, _, _ in sel.get("Arquivos", [])][:1]
    col = next((v for v, r, _ in sel.get("Coluna", []) if "ano" in r.lower() and "not" in r.lower()), None) \
        or next((v for v, r, _ in sel.get("Coluna", []) if "mês" in r.lower() or "mes" in r.lower()), "--Não-Ativa--")
    if not (linha and arq):
        print("   sem linha/arquivo esperado: tela mudou?"); return
    corpo = consulta(f, linha, col, incr, arq)
    acao = urllib.parse.urljoin(url, f["acao"])
    t0 = time.time()
    try:
        r = enviar(acao, _codificar(corpo), timeout=120).decode("latin-1")
    except Exception as e:  # noqa: BLE001
        print(f"   POST {acao}: FALHA {type(e).__name__}: {e}"); return
    try:
        tab = ler_prn(r)
        print(f"   POST {acao} ({time.time()-t0:.1f}s) linha={linha!r} col={col!r} incr={incr!r} arq={arq}")
        for ln in tab[:35]:
            print("   | " + " ; ".join(ln))
    except TelaMudou as e:
        print(f"   resposta sem tabela ({e}); início: {re.sub(r'<[^>]+>', ' ', r)[:600]!r}")


def sondar() -> int:
    for pag in ("https://datasus.saude.gov.br/informacoes-de-saude-tabnet/",
                "https://datasus.saude.gov.br/acesso-a-informacao/doencas-e-agravos-de-notificacao-de-2007-em-diante-sinan/"):
        try:
            h = buscar(pag, timeout=60).decode("utf-8", "replace")
            defs = sorted(set(re.findall(r"deftohtm\.exe\?([\w/\.]+\.def)", h)))
            print(f"[tabnet] índice {pag}: {len(defs)} .def → {defs}")
        except Exception as e:  # noqa: BLE001
            print(f"[tabnet] índice {pag}: FALHA {type(e).__name__}: {e}")
    sondar_def("sinannet/cnv/leptobr.def", "resid")
    for d in ("sivepdda/cnv/ddabr.def", "sinannet/cnv/ddabr.def", "mdda/cnv/ddabr.def"):
        sondar_def(d, "resid")
    return 0


def _teste_formulario():
    p = ('<form action="/cgi/tabcgi.exe?sinannet/cnv/leptobr.def" method=post>'
         '<select name="Linha"><option value="UF_de_resid&ecirc;ncia" selected>UF de resid&ecirc;ncia</option></select>'
         '<select name="SUF_de_resid&ecirc;ncia" multiple><option value="TODAS_AS_CATEGORIAS__">Todas</option></select>'
         '<select name="Arquivos"><option value="leptbr24.dbf">2024</option></select></form>')
    f = formulario(p)
    c = consulta(f, "UF_de_residência", "--Não-Ativa--", "Casos_confirmados", ["leptbr24.dbf"])
    return f["selects"]["Linha"][0][1] == "UF de residência" and c["SUF_de_resid&ecirc;ncia"] == TODAS


def _teste_prn():
    p = '<PRE>"UF de residência";"Casos"\n"23 Ceará";12\n"Total";12\n</PRE>'
    return ler_prn(p) == [["UF de residência", "Casos"], ["23 Ceará", "12"], ["Total", "12"]]


def _teste_tela_mudou():
    try:
        ler_prn("<html>manutenção</html>"); return False
    except TelaMudou:
        return True


def _teste_latin1():
    return _codificar({"Linha": "UF_de_residência"}) == [(b"Linha", "UF_de_residência".encode("latin-1"))]


def _teste_fonte_nao_escreve_banco():
    fonte = open(__file__, encoding="utf-8").read().split("def _teste_fonte_nao_escreve_banco")[0]
    return not any(f'"{p}"' in fonte for p in ("estados.json", "saude_uf.json", "municipios.json",
                                                "indice.json", "monitor_saude.json"))


TESTES = {
    "formulário: rótulos e filtros em todas as categorias": _teste_formulario,
    "prn: células da tabela": _teste_prn,
    "tela mudada é recusa, nunca número": _teste_tela_mudou,
    "corpo do POST em latin-1": _teste_latin1,
    "trava estrutural: não escreve nos arquivos do índice": _teste_fonte_nao_escreve_banco,
}

if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(rodar_autoteste(TESTES))
    if "--sondar" in sys.argv:
        sys.exit(sondar())
    print(__doc__)
