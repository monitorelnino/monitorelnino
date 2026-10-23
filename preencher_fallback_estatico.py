#!/usr/bin/env python3
"""preencher_fallback_estatico.py

Handover urgente de 16/09/2026: o medidor de resposta, o corte no cabeçalho, a data de última
verificação e uma das duas datas do rodapé ficavam com "—" (ou, pior, com data velha) no HTML
estático de index.html, saude.html e financiamento.html — o que qualquer leitor sem JavaScript,
leitor de tela ou indexador recebe. O medidor de antecipação de index.html já era preenchido por
recalcular_mare.py; este script estende a mesma ideia aos campos que ficaram de fora, lendo os
MESMOS arquivos de dados e replicando a MESMA fórmula que assets/js/*.js já usa em runtime — não
reinventa texto nem número.

Chamado por atualizar.py logo depois do cálculo do índice e da resposta, antes da regeneração
dos PDFs. Idempotente: pode rodar mais de uma vez sem duplicar nem desalinhar.
"""
import json, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def ler(nome, padrao=None):
    p = RAIZ / "data" / nome
    if not p.exists():
        return padrao
    return json.load(open(p, encoding="utf-8"))


def ler_catalogo(pagina):
    """Os textos públicos de uma página, da única fonte que os guarda (handover de 05/10/2026)."""
    p = RAIZ / "conteudo" / f"{pagina}.json"
    return (json.load(open(p, encoding="utf-8")).get("textos") or {}) if p.exists() else {}


def fmt(v):
    return f"{v:.1f}".replace(".", ",")


def sub_id(html, id_, novo_texto, contador=[0]):
    """Troca o conteúdo de <... id="id_">CONTEÚDO< por novo_texto, contando trocas feitas."""
    padrao = re.compile(r'(id="' + re.escape(id_) + r'"[^>]*>)[^<]*(<)')
    novo, n = padrao.subn(lambda m: m.group(1) + novo_texto + m.group(2), html, count=1)
    contador[0] += n
    return novo


def sub_attr(html, atributo, valor_do_atributo, novo_texto, contador=[0]):
    """Troca o conteúdo de <... atributo="valor">CONTEÚDO< por novo_texto.

    §253: os cartões da Imprensa são identificados por `data-imprensa`, não por `id` — há oito, e
    dar `id` a cada um só para o fallback seria ruído. O portão verificar_imprensa.py lê o mesmo
    atributo para conferir paridade.
    """
    padrao = re.compile(r'(' + re.escape(atributo) + r'="' + re.escape(valor_do_atributo)
                        + r'"[^>]*>)[^<]*(<)')
    novo, n = padrao.subn(lambda m: m.group(1) + novo_texto + m.group(2), html, count=1)
    contador[0] += n
    return novo


def medidor(html, fill_id, nome, rotulo, alvo, galvo, contador=[0]):
    """Reescreve as TRÊS cópias do mesmo número num medidor: `data-alvo`, `--galvo` e o
    `aria-label` do trilho.

    Uma chamada por medidor, porque escrever só uma delas é o defeito: em 21/10 o número grande
    do MARÉ Saúde passou a vir de `resumo.indice_nacional` e a barra ao lado dele ficou com o
    valor anterior, escrito à mão. Quem lê sem JavaScript via a barra de um número e o número de
    outro, e o leitor de tela ouvia o número velho.
    """
    padrao = re.compile(r'(id="' + re.escape(fill_id) + r'" data-alvo=")[\d.]+(" style="--galvo:)[\d.]+(;")')
    novo, n = padrao.subn(
        lambda m: m.group(1) + f"{alvo:.2f}" + m.group(2) + f"{galvo:.2f}" + m.group(3), html, count=1)
    novo = re.sub(r'aria-label="Barra de progresso: ' + re.escape(nome) + r'[^"]*"',
                  'aria-label="' + rotulo + '"', novo, count=1)
    contador[0] += n
    return novo


def preencher_imprensa():
    """Os oito cartões de "Esta semana em números", para quem não roda JS.

    Formata igual ao portão (`verificar_imprensa.formatar`) e igual ao JS: se os três divergirem,
    a paridade reprova por diferença de idioma em vez de diferença de dado.
    """
    p = RAIZ / "imprensa.html"
    if not p.exists():
        return
    semana = ler("imprensa/semana.json")
    if not semana:
        print("imprensa.html: data/imprensa/semana.json ausente — nada a preencher")
        return
    h = p.read_text(encoding="utf-8")
    h0 = h
    n = [0]

    def formatar(v):
        if v is None:
            return "sem coleta"
        if isinstance(v, float):
            return f"{v:.1f}".replace(".", ",")
        if isinstance(v, int):
            return f"{v:,}".replace(",", ".")
        return str(v)

    for c in semana.get("cartoes", []):
        texto = "sem coleta" if c.get("sem_coleta") else formatar(c.get("valor"))
        h = sub_attr(h, "data-imprensa", c["id"], texto, n)
    if semana.get("texto_pronto"):
        h = sub_id(h, "semanaTextoPronto", semana["texto_pronto"], n)
    if h != h0:
        p.write_text(h, encoding="utf-8", newline="\n")
    print(f"imprensa.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_index():
    p = RAIZ / "index.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    meta = ler("meta.json", {}) or {}
    corte = meta.get("corte") or "—"
    atualizado = meta.get("atualizado_em") or corte

    h = sub_id(h, "heroCorte", corte, n)
    h = sub_id(h, "metaAtualizado", atualizado, n)
    h = sub_id(h, "corteDados", corte, n)   # 16/09/2026: tirado o literal 26/08/2026 hardcoded

    resp = ler("resposta/por_uf.json", {}) or {}
    N = resp.get("nacional")
    if N:
        ir = N.get("indice")
        if ir is None:
            ir = round(100 * (N.get("fracao_populacao") or 0), 1)
        ir_fmt = fmt(ir)
        fm = 100 * (N.get("fracao_municipios") or 0)
        n_mun = N.get("n_municipios") or 0
        n_mun_fmt = f"{n_mun:,}".replace(",", ".")
        alvo = max(ir, 0.6 if n_mun else 0)

        h = sub_id(h, "respNum", ir_fmt, n)
        badge = f'<span class="gfaixa-pill">{n_mun_fmt} municípios · {fmt(fm)}% dos municípios</span>'
        h = re.sub(r'(<span class="gfaixa-badge" id="respBadge">)[^<]*(</span>)', lambda m: m.group(1) + badge + m.group(2), h, count=1)
        h = medidor(h, "respFill", "índice de resposta",
                    f"Barra de progresso: índice de resposta em {ir_fmt} de 100 "
                    "(população em municípios sob decreto)", alvo, max(ir, 0.1), n)

    if h != h0:
        p.write_text(h, encoding="utf-8", newline="\n")
    print(f"index.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_saude():
    p = RAIZ / "saude.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    mon = ler("monitor_saude.json", {}) or {}
    # 02/10/2026 (bloco A): os cartões do topo passaram a ser os cinco indicadores dinâmicos. O
    # fallback escreve o que o JavaScript escreveria, para que a página sem JS não mostre "—".
    den = ler("saude_desfechos/dengue_sinan_serie.json", {}) or {}
    br = ((den.get("serie") or {}).get("BR") or {})
    ano = str(den.get("ano_corrente") or "")
    fechadas = sorted(k for k, v in br.items() if k.startswith(ano) and v is not None)
    if fechadas:
        h = sub_id(h, "nDengueSE", f"{br[fechadas[-1]]:,}".replace(",", "."), n)
    srag = ler("saude_desfechos/srag_serie.json", {}) or {}
    serie = srag.get("serie") or {}
    ano_s = str(srag.get("ano_corrente") or "")
    total = {}
    for por_se in serie.values():
        if isinstance(por_se, dict):
            for se, v in por_se.items():
                if se.startswith(ano_s) and isinstance(v, (int, float)):
                    total[se] = total.get(se, 0) + v
    if total:
        ult = sorted(total)[-1]
        h = sub_id(h, "nSragSE", f"{int(total[ult]):,}".replace(",", "."), n)
    painel = ler("saude_desfechos/serie_painel.json", {}) or {}
    ufs_alerta = {m.get("uf") for m in (painel.get("municipios") or {}).values()
                  if (m.get("nivel_ultima_se") or 0) >= 3 and m.get("uf")}
    if painel:
        h = sub_id(h, "nUFsAlerta", f"{len(ufs_alerta)} de 27", n)
    sinais = ler("saude_sinais.json", {}) or {}
    resumo_calor = ((sinais.get("calor_excesso") or {}).get("resumo") or {})
    if resumo_calor:
        acima = int(resumo_calor.get("severo") or 0) + int(resumo_calor.get("extremo") or 0)
        h = sub_id(h, "nCalorMun", f"{acima:,}".replace(",", "."), n)
    # 21/10/2026: o medidor do MARÉ Saúde no topo da página, pela mesma regra do MARÉ Legal. O
    # número e a barra saem do MESMO valor: foi escrever só o número que deixou a barra em 31,9
    # ao lado dele. Os três ids do antigo cartão (rótulo, fonte e o cartão de emergência) saíram
    # da página em 02 e 19/10, e com eles as escritas que caíam no vazio.
    res = mon.get("resumo") or {}
    media = res.get("indice_nacional")
    if media is not None:
        h = sub_id(h, "nIndiceSaude", fmt(media), n)
        h = medidor(h, "gaugeFillSaude", "MARÉ Saúde",
                    f"Barra de progresso: MARÉ Saúde em {fmt(media)} de 100",
                    media, max(media, 0.1), n)

    # 22/10/2026 (v0.6, editoria): a legenda do mapa do índice nomeia os componentes que ENTRAM na
    # nota, e quem decide isso é o peso declarado no arquivo, não uma lista escrita aqui. Trocar o
    # identificador junto com o texto é o que faz o leitor do catálogo escrever a mesma frase: se
    # só o texto trocasse, `MonitorCatalogo.aplicar` o sobrescreveria pela frase do identificador
    # antigo antes de a página carregar o dado.
    pesos = (mon.get("metodo") or {}).get("pesos") or {}
    id_legenda = ("saude.estadual.monitor.legenda" if (pesos.get("cobertura") or 0) > 0
                  else "saude.estadual.monitor.legenda_dois_componentes")
    legenda = (ler_catalogo("saude").get(id_legenda) or "")
    if legenda:
        h = re.sub(r'data-conteudo="saude\.estadual\.monitor\.legenda[^"]*"',
                   f'data-conteudo="{id_legenda}"', h, count=1)
        h = sub_attr(h, "data-conteudo", id_legenda, legenda, n)

    if h != h0:
        p.write_text(h, encoding="utf-8", newline="\n")
    print(f"saude.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_financiamento():
    p = RAIZ / "financiamento.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    rotas = ler("financiamento/rotas_preventivas.json", {}) or {}
    corte = rotas.get("corte") or "—"
    h = sub_id(h, "corteFin", corte, n)

    # 02/10/2026 (contrato de layout): os três cartões do topo, com o recorte que a fonte permite.
    # Quem calcula é gerar_financiamento_semana.py; aqui só se escreve o que o JavaScript
    # escreveria, para que a página sem JS não mostre travessão.
    sem = ler("financiamento/semana.json", {}) or {}
    cartoes = {c.get("id"): c for c in (sem.get("cartoes") or [])}

    def curto(v):
        v = float(v or 0)
        if v >= 1e9:
            return "R$ " + f"{v / 1e9:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " bi"
        if v >= 1e6:
            return "R$ " + f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " mi"
        if v >= 1e3:
            return "R$ " + f"{v / 1e3:,.0f}".replace(",", ".") + " mil"
        return "R$ " + f"{v:,.0f}".replace(",", ".")

    for ident, idv, idr, idf, rotulo in [
            ("pago_periodo_mp", "topoPagoMes", "topoPagoMesRotulo", "topoPagoMesFonte",
             "pago pelas ações reforçadas pelas medidas provisórias"),
            ("transferido_municipios_periodo", "topoTransfMes", "topoTransfMesRotulo",
             "topoTransfMesFonte", "transferido pela União aos municípios"),
            ("resposta_liberado_semana", "topoRespostaSemana", None, "topoRespostaFonte", None)]:
        c = cartoes.get(ident)
        if not c:
            continue
        if c.get("sem_coleta"):
            h = sub_id(h, idv, "sem coleta", n)
            h = sub_id(h, idf, c.get("detalhe") or "", n)
            continue
        h = sub_id(h, idv, curto(c.get("valor")), n)
        if idr and rotulo:
            h = sub_id(h, idr, f"{rotulo}, no {c.get('periodo')}", n)
        exato = "R$ " + f"{round(float(c.get('valor') or 0)):,}".replace(",", ".") + " · " \
            if c.get("unidade") == "reais" else ""
        h = sub_id(h, idf, exato + (c.get("fonte") or "")
                   + (" · " + c["detalhe"] if c.get("detalhe") else ""), n)
    # `notaFogoCorte` saiu com o painel da rota do fogo (bloco B, 01/10/2026): o caso do fogo
    # virou texto, sem mapa por município e sem carimbo próprio.
    if h != h0:
        p.write_text(h, encoding="utf-8", newline="\n")
    print(f"financiamento.html: {n[0]} campo(s) de fallback estático regravado(s)")


if __name__ == "__main__":
    preencher_index()
    preencher_saude()
    preencher_financiamento()
    preencher_imprensa()
    sys.exit(0)
