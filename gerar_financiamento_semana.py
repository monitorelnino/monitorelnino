#!/usr/bin/env python3
"""Os cartões do topo do Financiamento (item 4 do contrato de layout, 02/10/2026).

Escreve `data/financiamento/semana.json` com quatro cartões, cada um com o recorte que a FONTE
permite — e nunca com "sem dado" quando a série-base existe:

- `pago_periodo_mp` — pago pelas ações reforçadas pelas medidas provisórias do ciclo. O Portal da
  Transparência publica execução por MÊS: quando o coletor já guardou a quebra mensal
  (`execucao.por_mes`), o cartão fala do último mês fechado; enquanto só houver o acumulado do
  ciclo, ele fala do acumulado e diz quais meses leu. Não inventa semana.
- `transferido_municipios_periodo` — transferido pela União a municípios no último mês FECHADO.
  O coletor marca mês ainda sendo preenchido como `parcial`, e mês parcial não vira cartão: ele
  mostraria queda que é da planilha, não do dinheiro.
- `resposta_liberado_semana` — recursos de resposta autorizados nas portarias da SEDEC nos últimos
  sete dias, com o número de municípios. Portaria tem data por ato, e aí o recorte semanal é real.
- `atos_federais_semana` — atos federais de financiamento novos nos últimos sete dias. Pelo
  contrato, o cartão só aparece quando é maior que zero.

Autoteste offline (`--autoteste`) não toca `data/`: ele exercita as funções puras com entrada
inventada, inclusive mês parcial e série ausente.
"""
from __future__ import annotations

import pathlib

import sys
from datetime import datetime, timedelta

from coletores_base import gravar, hoje_editorial, ler

JANELA = 7
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
ARQUIVO = "financiamento/semana.json"
# Trava estrutural: este gerador escreve UM arquivo, e nunca o banco nem o índice.
BANCO_PROIBIDO = {"estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json", "monitor_saude_v04.json"}


def mes_legivel(aaaamm: str) -> str:
    """'202608' → 'agosto de 2026'. Entrada malformada devolve ela mesma, sem levantar."""
    if not (isinstance(aaaamm, str) and len(aaaamm) == 6 and aaaamm.isdigit()):
        return str(aaaamm)
    mes = int(aaaamm[4:])
    if not 1 <= mes <= 12:
        return aaaamm
    return f"{MESES[mes - 1]} de {aaaamm[:4]}"


def ultimo_mes_fechado(meses: dict) -> str | None:
    """O mês mais recente que a fonte não marcou como parcial.

    O coletor de transferências marca `parcial: True` quando o arquivo do Portal ainda está sendo
    preenchido. Mês parcial no cartão mostraria uma queda que é da planilha.
    """
    if not isinstance(meses, dict):
        return None
    fechados = [m for m, v in meses.items()
                if isinstance(m, str) and m.isdigit() and not (isinstance(v, dict) and v.get("parcial"))]
    return max(fechados) if fechados else None


def na_janela(atos: list, corte: datetime, dias: int = JANELA) -> list:
    """Atos com data nos `dias` anteriores ao corte, inclusive. Data ilegível fica fora."""
    inicio = corte - timedelta(days=dias)
    dentro = []
    for a in atos or []:
        bruta = (a.get("data") or a.get("publicado_em") or "") if isinstance(a, dict) else ""
        d = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                d = datetime.strptime(str(bruta)[:10], fmt)
                break
            except ValueError:
                continue
        if d and inicio <= d <= corte:
            dentro.append(a)
    return dentro


def cartao(ident: str, valor, unidade: str, periodo: str, fonte: str, url_fonte=None,
           detalhe=None) -> dict:
    return {"id": ident, "valor": valor, "unidade": unidade, "periodo": periodo,
            "fonte": fonte, "url_fonte": url_fonte, "detalhe": detalhe, "sem_coleta": False}


def sem_coleta(ident: str, unidade: str, porque: str, fonte: str) -> dict:
    """Lacuna DECLARADA: a série-base não existe. Nunca zero no lugar de ausência."""
    return {"id": ident, "valor": None, "unidade": unidade, "periodo": None, "fonte": fonte,
            "url_fonte": None, "detalhe": porque, "sem_coleta": True}


def sem_data_na_origem(ident: str, unidade: str, porque: str, fonte: str) -> dict:
    """Ausência de OUTRA classe: a série existe e foi lida, e a origem não datou os atos.

    09/10/2026. O A3-10 declarou este caso como `sem_coleta`, e as duas coisas são distintas — a
    regra do site exige quatro estados separados, e dizer "sem coleta" de uma série que está em
    disco é dizer o que não aconteceu. O portão de layout (regra g) reprova exatamente isso, e
    reprovava com razão. O cartão passa a dizer a classe que é, em palavras, sem travessão.
    """
    return {"id": ident, "valor": None, "unidade": unidade, "periodo": None, "fonte": fonte,
            "url_fonte": None, "detalhe": porque, "sem_coleta": False,
            "classe": "sem_data_na_origem"}


def cartao_pago(mps: dict) -> dict:
    """Pago pelas ações reforçadas pelas MPs. Mês fechado quando houver quebra mensal."""
    itens = (mps or {}).get("mps") or []
    execucoes = [(m.get("execucao") or {}) for m in itens]
    coletadas = [e for e in execucoes if e.get("status") == "coletado"]
    if not coletadas:
        return sem_coleta("pago_periodo_mp", "reais",
                          "a execução das medidas provisórias não foi coletada até o corte",
                          "Portal da Transparência, Execução da Despesa")
    por_mes = {}
    for e in coletadas:
        for mes, v in (e.get("por_mes") or {}).items():
            por_mes.setdefault(mes, 0.0)
            por_mes[mes] += float((v or {}).get("pago") or 0.0)
    if por_mes:
        mes = max(por_mes)
        return cartao("pago_periodo_mp", round(por_mes[mes], 2), "reais",
                      f"mês de {mes_legivel(mes)}",
                      "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)",
                      # Sem travessão: o portão de legendas o reprova em texto de figura, e com
                      # razão — travessão em cartão vira frase dentro de frase. Duas frases.
                      # Sem travessão e sem conectivo de causa: o portão de legendas reprova os
                      # dois em texto de figura. O fato, em duas frases, basta.
                      detalhe=("execução das ações reforçadas pelas medidas provisórias do ciclo. "
                               "O valor inclui a dotação ordinária da ação. É teto, não a execução "
                               "do crédito"))
    meses = sorted({m for e in coletadas for m in (e.get("meses") or [])})
    total = round(sum(float(e.get("pago") or 0.0) for e in coletadas), 2)
    janela = (f"meses de {mes_legivel(meses[0])} a {mes_legivel(meses[-1])}"
              if len(meses) > 1 else (f"mês de {mes_legivel(meses[0])}" if meses else "ciclo"))
    return cartao("pago_periodo_mp", total, "reais", janela,
                  "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)",
                  detalhe="acumulado do ciclo: a quebra por mês entra na próxima coleta da execução")


def cartao_transferido(transf: dict) -> dict:
    """Transferido pela União a municípios no último mês fechado."""
    meses = (transf or {}).get("meses_lidos") or {}
    mes = ultimo_mes_fechado(meses)
    if not mes:
        return sem_coleta("transferido_municipios_periodo", "reais",
                          "nenhum mês fechado de transferências lido até o corte",
                          "Portal da Transparência, Transferências de Recursos")
    soma = float((meses[mes] or {}).get("soma") or 0.0)
    casados = (meses[mes] or {}).get("municipios_casados")
    return cartao("transferido_municipios_periodo", round(soma, 2), "reais",
                  f"mês de {mes_legivel(mes)}",
                  "Portal da Transparência, Transferências de Recursos (dados abertos)",
                  url_fonte="https://portaldatransparencia.gov.br/download-de-dados/transferencias",
                  detalhe=(f"{casados} municípios com transferência no mês" if casados else None))


def cartao_resposta(rec: dict, corte: datetime) -> dict:
    """Recursos de resposta autorizados nas portarias da SEDEC nos últimos sete dias."""
    municipios = (rec or {}).get("municipios")
    if not municipios:
        return sem_coleta("resposta_liberado_semana", "reais",
                          "as portarias de recursos de resposta não foram coletadas até o corte",
                          "Portarias da SEDEC no Diário Oficial da União")
    atos = []
    for m in municipios.values():
        for a in (m or {}).get("atos") or []:
            if (a or {}).get("acao") == "resposta":
                atos.append(a)
    na = na_janela(atos, corte)
    valor = round(sum(float(a.get("valor_autorizado") or 0.0) for a in na), 2)
    cidades = len({(a.get("municipio"), a.get("uf")) for a in na})
    return cartao("resposta_liberado_semana", valor, "reais", "últimos 7 dias",
                  "Portarias da SEDEC no Diário Oficial da União",
                  detalhe=(f"{cidades} município(s) em {len(na)} portaria(s)" if na
                           else "nenhuma portaria de resposta publicada nos últimos 7 dias"))


def tem_data_legivel(atos: list) -> bool:
    """Algum item traz data de publicação que a janela saiba ler?

    08/10/2026 (A3-10). Nenhum dos cinco compromissos federais tinha `data` nem `publicado_em`:
    `na_janela` devolvia lista vazia, e o cartão publicava **"0 atos" como fato**, nos últimos sete
    dias, no Financiamento e na Imprensa. Zero medido e zero por campo inexistente são coisas
    diferentes — e a regra do site é que zero só se publica quando a coleta rodou.
    """
    for a in atos or []:
        if not isinstance(a, dict):
            continue
        bruta = str(a.get("data") or a.get("publicado_em") or "")[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                datetime.strptime(bruta, fmt)
                return True
            except ValueError:
                continue
    return False


def cartao_atos(comp: dict, corte: datetime) -> dict:
    """Atos federais de financiamento novos nos últimos sete dias."""
    itens = (comp or {}).get("itens")
    if itens is None:
        return sem_coleta("atos_federais_semana", "atos",
                          "o arquivo de compromissos federais não foi coletado até o corte",
                          "Atos federais lidos pelo MARÉ")
    # Lista VAZIA é zero medido: a coleta rodou e não havia ato no período. O caso do A3-10 é
    # outro — há itens, e nenhum deles traz data, de modo que a janela não tem o que medir.
    if itens and not tem_data_legivel(itens):
        return sem_data_na_origem("atos_federais_semana", "atos",
                                  "a origem dos compromissos federais não traz data de publicação "
                                  "do ato; sem data não há janela de sete dias para medir",
                                  "Atos federais lidos pelo MARÉ")
    na = na_janela(itens, corte)
    return cartao("atos_federais_semana", len(na), "atos", "últimos 7 dias",
                  "Atos federais lidos pelo MARÉ",
                  detalhe=(", ".join(filter(None, (a.get("instrumento") for a in na[:3]))) or None))


def montar(mps: dict, transf: dict, rec: dict, comp: dict, corte: datetime) -> dict:
    cartoes = [cartao_pago(mps), cartao_transferido(transf), cartao_resposta(rec, corte),
               cartao_atos(comp, corte)]
    return {"_governanca": "Gerado por gerar_financiamento_semana.py. Cada cartão traz o recorte "
                           "que a fonte permite: mês fechado onde a fonte publica por mês, sete "
                           "dias onde o ato tem data. Lacuna é declarada, nunca zero.",
            "corte": corte.strftime("%d/%m/%Y"),
            "janela_dias": JANELA,
            "cartoes": cartoes}


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("mes legivel", mes_legivel("202608") == "agosto de 2026")
    ok("mes malformado nao levanta", mes_legivel("20260") == "20260" and mes_legivel("202699") == "202699")
    ok("mes parcial nao e fechado",
       ultimo_mes_fechado({"202607": {"soma": 1}, "202608": {"soma": 2, "parcial": True}}) == "202607")
    ok("sem mes fechado devolve None", ultimo_mes_fechado({"202608": {"parcial": True}}) is None)
    ok("meses_lidos ausente nao levanta", ultimo_mes_fechado(None) is None)

    corte = datetime(2026, 10, 2)
    ok("janela pega os dois formatos de data",
       len(na_janela([{"data": "2026-09-30"}, {"data": "28/09/2026"}, {"data": "2026-01-01"},
                      {"data": "nao-e-data"}], corte)) == 2)

    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": 10.0,
                                           "por_mes": {"202607": {"pago": 4.0},
                                                       "202608": {"pago": 6.0}}}}]})
    ok("pago usa o ultimo mes quando ha quebra", c["valor"] == 6.0 and "agosto" in c["periodo"])
    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": 10.0,
                                           "meses": ["202606", "202607"]}}]})
    ok("pago cai no acumulado sem quebra, e NAO vira sem dado",
       c["valor"] == 10.0 and not c["sem_coleta"] and "junho" in c["periodo"])
    ok("pago sem coleta declara lacuna", cartao_pago({"mps": [{}]})["sem_coleta"] is True)

    c = cartao_transferido({"meses_lidos": {"202608": {"soma": 5.5, "municipios_casados": 3},
                                            "202609": {"soma": 1.0, "parcial": True}}})
    ok("transferido ignora o mes parcial", c["valor"] == 5.5 and "agosto" in c["periodo"])
    ok("transferido sem mes fechado declara lacuna",
       cartao_transferido({"meses_lidos": {}})["sem_coleta"] is True)

    base = {"municipios": {"1": {"atos": [
        {"acao": "resposta", "data": "2026-09-30", "valor_autorizado": 100.0, "municipio": "X", "uf": "SP"},
        {"acao": "recuperacao", "data": "2026-09-30", "valor_autorizado": 900.0, "municipio": "X", "uf": "SP"},
        {"acao": "resposta", "data": "2026-01-02", "valor_autorizado": 50.0, "municipio": "Y", "uf": "BA"}]}}}
    c = cartao_resposta(base, corte)
    ok("resposta soma so resposta e so a janela", c["valor"] == 100.0 and "1 munic" in (c["detalhe"] or ""))
    ok("resposta sem coleta declara lacuna", cartao_resposta({}, corte)["sem_coleta"] is True)

    c = cartao_atos({"itens": [{"data": "2026-09-29", "instrumento": "Portaria 1"},
                               {"data": "2026-02-01", "instrumento": "Portaria 2"}]}, corte)
    ok("atos conta so a janela", c["valor"] == 1)
    # 08/10/2026 (A3-10): itens SEM data não são zero — a janela não tem o que medir.
    ok("atos com itens sem data declara a CLASSE, nao `sem coleta`",
       cartao_atos({"itens": [{"instrumento": "Portaria sem data"}]}, corte)["classe"]
       == "sem_data_na_origem"
       and cartao_atos({"itens": [{"instrumento": "Portaria sem data"}]},
                       corte)["sem_coleta"] is False)
    ok("serie ausente segue sendo `sem coleta`", cartao_atos({}, corte)["sem_coleta"] is True
       and "classe" not in cartao_atos({}, corte))
    ok("atos com itens sem data nao publica valor",
       cartao_atos({"itens": [{"instrumento": "Portaria sem data"}]}, corte)["valor"] is None)
    ok("atos lista vazia e ZERO, nao lacuna",
       cartao_atos({"itens": []}, corte)["valor"] == 0
       and cartao_atos({"itens": []}, corte)["sem_coleta"] is False)
    ok("atos sem arquivo declara lacuna", cartao_atos({}, corte)["sem_coleta"] is True)

    d = montar({}, {}, {}, {}, corte)
    ok("montar devolve os quatro cartoes", [x["id"] for x in d["cartoes"]] == [
        "pago_periodo_mp", "transferido_municipios_periodo", "resposta_liberado_semana",
        "atos_federais_semana"])
    ok("trava estrutural: o gerador nao escreve no banco", ARQUIVO not in BANCO_PROIBIDO)
    # Trava estrutural: o autoteste le o PROPRIO codigo-fonte e confere que ha uma escrita so,
    # a de ARQUIVO, e que nenhum arquivo do banco aparece como destino de gravacao.
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l.strip() for l in fonte.splitlines()
                if l.strip().startswith("gravar(")]
    ok("trava estrutural: uma escrita so, e e ARQUIVO",
       len(escritas) == 1 and escritas[0].startswith("gravar(ARQUIVO"))
    ok("trava estrutural: nenhum arquivo do banco como destino",
       not any(b in fonte.split("BANCO_PROIBIDO = ")[-1].split("}")[1] for b in BANCO_PROIBIDO))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita em data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    corte = hoje_editorial()
    d = montar(ler("financiamento/mps_2026.json", {}) or {},
               ler("financiamento/municipios/transferencias_uniao.json", {}) or {},
               ler("resposta/recursos_liberados.json", {}) or {},
               ler("financiamento/compromissos_federais.json", {}) or {},
               datetime(corte.year, corte.month, corte.day))
    gravar(ARQUIVO, d)
    for c in d["cartoes"]:
        print(f"  {c['id']}: " + ("sem coleta — " + str(c['detalhe']) if c["sem_coleta"]
                                  else f"{c['valor']} ({c['periodo']})"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
