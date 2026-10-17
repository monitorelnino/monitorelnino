#!/usr/bin/env python3
"""SISAB, relatórios públicos de produção da atenção primária (janela E1, 17/10/2026).

HANDOVER_SUS_DESFECHOS §2.2: o relatório de produção do SISAB é formulário JSF público, sem login,
com exportação; dá atendimentos por CID-10/CIAP-2, por UF e mês. É formulário: entra com detector
de mudança de tela (quebrou → lacuna declarada, nunca número velho como novo).

USO
  python3 coletar_sisab.py --autoteste
  python3 coletar_sisab.py --sondar        # só mede e imprime; não escreve em data/
"""
import re
import sys
import time

from coletores_base import buscar, rodar_autoteste

RELATORIO = ("https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/"
             "RelSauProducao.xhtml")


class TelaMudou(ValueError):
    """O formulário do SISAB não tem a forma esperada: lacuna, nunca número."""


def campos_do_formulario(pagina: str) -> dict:
    """{'viewstate', 'selects': {id: n_opcoes}, 'botoes': [...]} de uma página JSF. Função pura."""
    vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', pagina)
    if not vs:
        raise TelaMudou("página do SISAB sem ViewState (não é o formulário JSF)")
    selects = {n: len(re.findall(r"<option", c, re.I))
               for n, c in re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', pagina, re.I | re.S)}
    botoes = re.findall(r'<(?:button|input)[^>]*type="(?:submit|button)"[^>]*(?:id|name)="([^"]+)"', pagina, re.I)
    return {"viewstate": vs.group(1), "selects": selects, "botoes": botoes}


def sondar() -> int:
    for url in ("https://sisab.saude.gov.br/robots.txt", RELATORIO):
        t0 = time.time()
        try:
            corpo = buscar(url, timeout=60).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"[sisab] {url}: FALHA {type(e).__name__}: {e}"); continue
        print(f"[sisab] {url}: {len(corpo)} B em {time.time()-t0:.1f}s")
        if url.endswith("robots.txt"):
            print("   " + corpo[:400].replace("\n", " | ")); continue
        try:
            f = campos_do_formulario(corpo)
            print(f"   viewstate ok; selects {f['selects']}; botões {f['botoes'][:20]}")
            print("   rótulos: " + str(sorted(set(re.findall(r"<label[^>]*>([^<]{3,60})</label>", corpo)))[:60]))
        except TelaMudou as e:
            print(f"   {e}; início: {re.sub(r'<[^>]+>', ' ', corpo)[:500]!r}")
    return 0


def _teste_formulario():
    p = ('<form><select name="selectLinha"><option>UF</option><option>Mês</option></select>'
         '<input type="hidden" name="javax.faces.ViewState" value="abc:1"/>'
         '<button type="submit" id="btnBuscar">Buscar</button></form>')
    f = campos_do_formulario(p)
    return f["viewstate"] == "abc:1" and f["selects"] == {"selectLinha": 2} and f["botoes"] == ["btnBuscar"]


def _teste_tela_mudou():
    try:
        campos_do_formulario("<html>Em manutenção</html>"); return False
    except TelaMudou:
        return True


def _teste_fonte_nao_escreve_banco():
    fonte = open(__file__, encoding="utf-8").read().split("def _teste_fonte_nao_escreve_banco")[0]
    return not any(f'"{p}"' in fonte for p in ("estados.json", "saude_uf.json", "municipios.json",
                                                "indice.json", "monitor_saude.json"))


TESTES = {
    "formulário JSF: ViewState, selects e botões": _teste_formulario,
    "tela mudada é recusa, nunca número": _teste_tela_mudou,
    "trava estrutural: não escreve nos arquivos do índice": _teste_fonte_nao_escreve_banco,
}

if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(rodar_autoteste(TESTES))
    if "--sondar" in sys.argv:
        sys.exit(sondar())
    print(__doc__)
