#!/usr/bin/env python3
"""Gera METODOLOGIA.pdf a partir do METODOLOGIA.md vivo.

Substitui o antigo gerar_pdf_puro.py (ausente do repositório; achado A8 da
auditoria de 27/08/2026). Diferença estrutural em relação ao antecessor: o PDF
é RENDERIZADO do markdown publicado, sem nenhum texto próprio — portanto não
pode divergir da metodologia vigente. Regenerado automaticamente pela Action a
cada execução do pipeline (mesma disciplina do MARE_Indice_Documentacao.pdf).

  python3 gerar_pdf_metodologia.py     # grava METODOLOGIA.pdf

Requer: reportlab.

DETERMINISMO (R1 da segunda auditoria, 29/08/2026): mesma correção aplicada
em gerar_pdf_indice.py — SOURCE_DATE_EPOCH fixado a partir de data/meta.json
(corte dos dados), tornando o PDF função determinística dos dados publicados
em vez do instante de geração. Ver docstring de gerar_pdf_indice.py para o
detalhe da verificação.
"""
import json, pathlib, re, os, datetime

_META = json.load(open(pathlib.Path(__file__).parent / "data" / "meta.json", encoding="utf-8"))
os.environ.setdefault(
    "SOURCE_DATE_EPOCH",
    str(int(datetime.datetime.strptime(_META["corte"], "%d/%m/%Y")
                              .replace(tzinfo=datetime.timezone.utc).timestamp()))
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

RAIZ = pathlib.Path(__file__).parent
TERRA = colors.HexColor("#A65F3F")
AZUL = colors.HexColor("#35566B")
TINTA = colors.HexColor("#1A0E08")
CINZA = colors.HexColor("#6B6257")

S_KICK = ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=TERRA, spaceAfter=2)
S_TIT = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=TINTA, spaceAfter=2)
S_SUB = ParagraphStyle("s", fontName="Helvetica-Oblique", fontSize=11, leading=14, textColor=AZUL, spaceAfter=2)
S_META = ParagraphStyle("m", fontName="Helvetica", fontSize=9.5, leading=13, textColor=CINZA, spaceAfter=12)
S_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=TERRA, spaceBefore=13, spaceAfter=5)
S_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=AZUL, spaceBefore=8, spaceAfter=3)
S_P = ParagraphStyle("p", fontName="Helvetica", fontSize=9.3, leading=12.6, textColor=TINTA, spaceAfter=5, alignment=4)
S_LI = ParagraphStyle("li", parent=S_P, leftIndent=6 * mm, bulletIndent=1.5 * mm, spaceAfter=3)
S_DEF = ParagraphStyle("d", fontName="Courier", fontSize=8.2, leading=11, textColor=TINTA,
                       leftIndent=5 * mm, spaceAfter=2, backColor=colors.HexColor("#F5EFE6"))
S_TOC = ParagraphStyle("toc", fontName="Helvetica", fontSize=9.3, leading=13.4, textColor=TINTA, leftIndent=2 * mm)


def _inline(t):
    """Converte um trecho de markdown inline (negrito, itálico, links) em runs formatados do PDF."""
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("\\[", "[").replace("\\]", "]")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"<i>\1</i>", t)
    t = t.replace("`", "")
    return t


def _eh_titulo(linha):
    """Linha inteiramente em negrito → título. Nível pela numeração N. / N.N."""
    m = re.fullmatch(r"\*\*(.+?)\*\*", linha.strip())
    if not m:
        return None, None
    txt = m.group(1).strip()
    mnum = re.match(r"(\d+)(\.\d+)*", txt)
    if txt == "Sumário":
        return "SUMARIO", txt
    if mnum:
        return ("H1" if mnum.group(0).count(".") == 0 else "H2"), txt
    return "H2", txt


def construir():
    """Monta o PDF da metodologia a partir do texto vivo de METODOLOGIA.md, preservando a estrutura de seções e o versionamento."""
    md = (RAIZ / "METODOLOGIA.md").read_text(encoding="utf-8")
    linhas = md.split("\n")

    # capa: primeiras linhas fixas do documento
    E = []
    corpo_ini = 0
    cab = [l for l in linhas[:12] if l.strip()]
    E.append(Paragraph(_inline(cab[0]), S_KICK))                      # FUTURA · EVIDENCE LAB
    E.append(Paragraph(_inline(re.sub(r"\*\*", "", cab[1])), S_TIT))  # Monitor El Niño Brasil
    E.append(Paragraph(_inline(re.sub(r"\*", "", cab[2])), S_SUB))    # MARÉ — ...
    E.append(Paragraph(_inline(cab[3]), S_META))                      # Documento Técnico-Metodológico
    E.append(Paragraph(_inline(cab[4]), S_META))                      # Edição · versão · corte
    for i, l in enumerate(linhas):
        if l.strip() == "**Sumário**":
            corpo_ini = i
            break

    # sumário gerado dos títulos reais (o PDF nunca desatualiza o próprio índice)
    E.append(Paragraph("Sumário", S_H1))
    for l in linhas[corpo_ini + 1:]:
        nivel, txt = _eh_titulo(l)
        if nivel == "H1":
            E.append(Paragraph(_inline(txt), S_TOC))
    E.append(PageBreak())

    for l in linhas[corpo_ini + 1:]:
        s = l.rstrip()
        if not s.strip():
            continue
        nivel, txt = _eh_titulo(s)
        if nivel == "H1":
            E.append(Paragraph(_inline(txt), S_H1))
        elif nivel == "H2":
            E.append(Paragraph(_inline(txt), S_H2))
        elif s.startswith("-   ") or s.startswith("- "):
            E.append(Paragraph(_inline(re.sub(r"^-\s+", "", s)), S_LI, bulletText="•"))
        elif s.startswith("  ") and not s.startswith("    "):
            E.append(Paragraph(_inline(s.strip()), S_DEF))
        else:
            E.append(Paragraph(_inline(s.strip()), S_P))

    versao = re.search(r"Metodologia (v[\d.]+)", md)
    versao = versao.group(1) if versao else ""

    def rodape(canvas, doc):
        """Escreve o rodapé padrão (numeração de página, versão do documento) em cada página do PDF."""
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(CINZA)
        canvas.drawString(18 * mm, 12 * mm,
                          f"Monitor El Niño Brasil · Futura Evidence Lab — Documento Técnico-Metodológico ({versao}, renderizado do METODOLOGIA.md vigente)")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"página {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#D8CFC2"))
        canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(str(RAIZ / "METODOLOGIA.pdf"), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=22 * mm,
                            title=f"Monitor El Niño Brasil — Metodologia {versao}",
                            author="Futura Evidence Lab · Monitor El Niño Brasil")
    n_blocos = len(E)  # doc.build consome a lista — capturar antes
    doc.build(E, onFirstPage=rodape, onLaterPages=rodape)
    print(f"METODOLOGIA.pdf gerado ({versao}) — renderizado de METODOLOGIA.md, {n_blocos} blocos")


if __name__ == "__main__":
    construir()
