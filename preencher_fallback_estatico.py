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
    h = sub_id(h, "metaUltimaVerif", atualizado, n)
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
        h = re.sub(r'(id="respFill" data-alvo=")[\d.]+(" style="--galvo:)[\d.]+(;")', rf'\g<1>{alvo:.2f}\g<2>{max(ir, 0.1):.2f}\g<3>', h, count=1)
        rotulo = f"Barra de progresso: índice de resposta em {ir_fmt} de 100 (população em municípios sob decreto)"
        h = re.sub(r'aria-label="Barra de progresso: índice de resposta[^"]*"', f'aria-label="{rotulo}"', h, count=1)
        n[0] += 1

    if h != h0:
        p.write_text(h, encoding="utf-8", newline="\n")
    print(f"index.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_saude():
    p = RAIZ / "saude.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    mon = ler("monitor_saude.json", {}) or {}
    suf = ler("saude_uf.json", {}) or {}
    meta = ler("meta.json", {}) or {}
    corte_saude = suf.get("corte") or "—"

    h = sub_id(h, "corteSaude", corte_saude, n)

    # 01/10/2026 (bloco C.1): o contador de semanas saiu do topo e no lugar entraram os três
    # contadores. Eles contam DOCUMENTO LIDO, não categoria — e o fallback estático reproduz
    # exatamente o que o JavaScript escreveria, para que a página sem JS não mostre "—".
    ufs_saude = mon.get("ufs") or {}
    com_plano = sum(1 for v in ufs_saude.values()
                    if isinstance(v, dict) and (v.get("instrumento") or {}).get("doc"))
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
    h = sub_id(h, "nEmergSaude", str((mon.get("resposta") or {}).get("emergencias") or 0), n)

    # 02/10/2026 (contrato de layout): o sexto cartao e o proprio numero do MARE Saude, com o
    # rotulo dizendo de quantos estados e a media enquanto nao forem 27 - a mesma frase que o
    # JavaScript escreve, para que a pagina sem JS nao diga menos nem mais.
    res = mon.get("resumo") or {}
    media = res.get("media_das_verificadas")
    if media is not None:
        verificadas = res.get("verificadas") or 0
        h = sub_id(h, "nIndiceSaude", fmt(media), n)
        h = sub_id(h, "rotuloIndiceSaude",
                   "de 100, na prepara\u00e7\u00e3o publicada em sa\u00fade" if verificadas >= 27
                   else f"de 100, m\u00e9dia dos {verificadas} estados verificados", n)
        h = sub_id(h, "fonteIndiceSaude",
                   f"MAR\u00c9, sobre documentos oficiais lidos \u00b7 {verificadas} de 27 estados verificados", n)

    if h != h0:
        p.write_text(h, encoding="utf-8", newline="\n")
    print(f"saude.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_financiamento():
    p = RAIZ / "financiamento.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    rotas = ler("financiamento/rotas_preventivas.json", {}) or {}
    corte = rotas.get("corte") or "—"
    h = sub_id(h, "corteFin", corte, n)
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
