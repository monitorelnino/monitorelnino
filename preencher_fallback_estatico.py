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
        h = sub_id(h, "respCorte", corte, n)
        badge = f'<span class="gfaixa-pill">{n_mun_fmt} municípios · {fmt(fm)}% dos municípios</span>'
        h = re.sub(r'(<span class="gfaixa-badge" id="respBadge">)[^<]*(</span>)', lambda m: m.group(1) + badge + m.group(2), h, count=1)
        h = re.sub(r'(id="respFill" data-alvo=")[\d.]+(" style="--galvo:)[\d.]+(;")', rf'\g<1>{alvo:.2f}\g<2>{max(ir, 0.1):.2f}\g<3>', h, count=1)
        rotulo = f"Barra de progresso: índice de resposta em {ir_fmt} de 100 (população em municípios sob decreto)"
        h = re.sub(r'aria-label="Barra de progresso: índice de resposta[^"]*"', f'aria-label="{rotulo}"', h, count=1)
        h = sub_id(h, "respLinha", "", n)   # 15/09/2026: JS também deixa vazio — a contagem vive só na interpretação
        interp = (f'<strong>{n_mun_fmt}</strong> municípios, <strong>{fmt((N.get("pop_sob_decreto") or 0) / 1e6)}</strong> milhões de pessoas. '
                  f'Primeiro decreto do ciclo: <strong>{N.get("primeiro_decreto") or "—"}</strong>. '
                  f'{N.get("reconhecidos") or 0} aceitos pelo governo federal · {N.get("decretados_sem_reconhecimento") or 0} ainda não. '
                  f'Entre 04/07 e 25/10, transferências voluntárias ficam suspensas; transferências por regra e por decreto de emergência continuam '
                  f'(<a href="calendario-eleitoral.html">calendário →</a>).')
        h = re.sub(r'(<p class="note" id="interpResposta"[^>]*>)[^<]*(</p>)', lambda m: m.group(1) + interp + m.group(2), h, count=1)
        n[0] += 1

    if h != h0:
        p.write_text(h, encoding="utf-8")
    print(f"index.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_saude():
    p = RAIZ / "saude.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    mon = ler("monitor_saude.json", {}) or {}
    suf = ler("saude_uf.json", {}) or {}
    meta = ler("meta.json", {}) or {}
    corte_saude = suf.get("corte") or "—"

    h = sub_id(h, "corteSaude", corte_saude, n)

    res = mon.get("resumo") or {}
    media = res.get("media_das_verificadas")
    if media is not None:
        h = sub_id(h, "gaugeSaudeNum", fmt(media), n)
        h = sub_id(h, "gaugeSaudeN", str(res.get("verificadas", "—")), n)
        h = sub_id(h, "gaugeSaudeNV", str(res.get("nao_verificadas", "—")), n)
        h = sub_id(h, "gaugeSaudeCorte", mon.get("corte") or meta.get("corte") or "—", n)
        h = re.sub(r'(id="gaugeSaudeFill" data-alvo=")[\d.]+(" style="--galvo:)[\d.]+(;")', rf'\g<1>{media}\g<2>{max(media, 0.1)}\g<3>', h, count=1)
        rotulo_verif = res.get("verificadas", "—")
        h = re.sub(r'aria-label="Barra de progresso: MARÉ · Saúde[^"]*"',
                    f'aria-label="Barra de progresso: MARÉ · Saúde em {fmt(media)} de 100 (média de {rotulo_verif} estados verificados)"', h, count=1)
        n[0] += 1

    resposta = mon.get("resposta") or {}
    ir = resposta.get("indice")
    if ir is not None:
        emerg = resposta.get("emergencias") or 0
        plural = "" if emerg == 1 else "s"
        h = sub_id(h, "rsNum", fmt(ir), n)
        h = sub_id(h, "rsCorte", mon.get("corte") or "—", n)
        badge = f'<span class="gfaixa-pill">{emerg} emergência{plural} sanitária{plural} declarada{plural}</span>'
        h = re.sub(r'(<span class="gfaixa-badge" id="rsBadge">)[^<]*(</span>)', lambda m: m.group(1) + badge + m.group(2), h, count=1)
        alvo = max(ir, 0.6 if emerg else 0)
        h = re.sub(r'(id="rsFill" data-alvo=")[\d.]+(" style="--galvo:)[\d.]+(;")', rf'\g<1>{alvo}\g<2>{max(ir, 0.1)}\g<3>', h, count=1)
        interp = (f'<strong>{emerg}</strong> emergência{plural} sanitária{plural} declarada{plural} desde {resposta.get("desde", "29/06/2026")} '
                  f'(ESPIN federal e decretos estaduais), <strong>{fmt((resposta.get("pop_sob_emergencia") or 0) / 1e6)}</strong> '
                  f'milhões de pessoas nos estados que as declararam. Antecipação mede preparo; resposta mede o que foi declarado depois, mostrados em separado.')
        h = re.sub(r'(<p class="note"[^>]*id="interpRespostaSaude"[^>]*>)[^<]*(</p>)', lambda m: m.group(1) + interp + m.group(2), h, count=1)
        n[0] += 1

    if h != h0:
        p.write_text(h, encoding="utf-8")
    print(f"saude.html: {n[0]} campo(s) de fallback estático regravado(s)")


def preencher_financiamento():
    p = RAIZ / "financiamento.html"; h = p.read_text(encoding="utf-8"); h0 = h
    n = [0]
    rotas = ler("financiamento/rotas_preventivas.json", {}) or {}
    corte = rotas.get("corte") or "—"
    h = sub_id(h, "corteFin", corte, n)
    h = sub_id(h, "notaFogoCorte", corte, n)
    if h != h0:
        p.write_text(h, encoding="utf-8")
    print(f"financiamento.html: {n[0]} campo(s) de fallback estático regravado(s)")


if __name__ == "__main__":
    preencher_index()
    preencher_saude()
    preencher_financiamento()
    sys.exit(0)
