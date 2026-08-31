#!/usr/bin/env python3
"""
gerar_selos.py — selos SVG embutíveis do índice MARÉ, um por estado e um nacional.

Sugestão aceita por Patricia em 31/08/2026: um selo "MARÉ · SC · avançado · 78,6"
que Defesas Civis, câmaras, prefeituras e veículos possam embutir (<img>) — o
índice se espalha, e quem embute assume publicamente a própria faixa.

Regras:
- Determinístico: mesma entrada → mesmo SVG, byte a byte (nenhum carimbo além do
  corte dos dados). A verificação de consistência confere que o número do selo é o
  do índice publicado.
- Cores e nomes de faixa são os mesmos do site (pares com contraste AA conferidos
  em 31/08/2026). Fontes de sistema (Georgia / Arial Narrow), porque o selo vive em
  páginas alheias, sem as webfonts do site.
- Linguagem probatória: o selo diz "preparação demonstrável publicamente", nunca
  "preparado".
Uso: python3 gerar_selos.py [--self-test]
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"
SAIDA = RAIZ / "selos"
SITE = "https://monitorelnino.com.br"

# [rótulo, fundo, texto] — idêntico ao index.html (pílula do medidor)
FAIXAS = [(25, "Estágio inicial", "#7C4A34", "#F5F1E8"), (50, "Em construção", "#C69B72", "#15201A"),
          (70, "Consolidado", "#6B6A44", "#F5F1E8"), (101, "Avançado", "#35566B", "#F5F1E8")]


def faixa(v):
    """Devolve (rótulo, fundo, texto) da faixa do valor — mesmos cortes do site."""
    for corte, rot, bg, fg in FAIXAS:
        if v < corte:
            return rot, bg, fg
    return FAIXAS[-1][1:]


def fmt(v):
    """Número com vírgula decimal e uma casa, como no site."""
    return f"{v:.1f}".replace(".", ",")


def esc(s):
    """Escape mínimo para texto em SVG."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_selo(nome, uf, valor, corte, nacional=False):
    """Um selo 360×92, projetado para fontes de sistema (Georgia/Arial): marca à esquerda, lugar + nota + faixa à direita."""
    rot, bg, fg = faixa(valor)
    titulo = "Brasil · média nacional" if nacional else f"{nome} ({uf})"
    aria = f"MARÉ, Monitor El Niño Brasil: {titulo}, {fmt(valor)} de 100, faixa {rot.lower()}, dados até {corte}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="92" viewBox="0 0 360 92" role="img" aria-labelledby="t">
<title id="t">{esc(aria)}</title>
<rect x="0.5" y="0.5" width="359" height="91" rx="10" fill="#F5F1E8" stroke="#D6C4AC"/>
<rect x="0.5" y="0.5" width="6" height="91" rx="3" fill="{bg}"/>
<text x="18" y="30" font-family="Georgia, 'Times New Roman', serif" font-size="22" font-weight="700" fill="#15201A">MARÉ</text>
<text x="18" y="47" font-family="Arial, Helvetica, sans-serif" font-size="9.5" letter-spacing="0.5" fill="#55645B">MONITOR EL NIÑO BRASIL</text>
<text x="18" y="65" font-family="Arial, Helvetica, sans-serif" font-size="10" fill="#55645B">preparação demonstrável publicamente</text>
<text x="18" y="79" font-family="Arial, Helvetica, sans-serif" font-size="10" fill="#55645B">dados até {esc(corte)}</text>
<line x1="196" y1="14" x2="196" y2="78" stroke="#D6C4AC"/>
<text x="208" y="28" font-family="Arial, Helvetica, sans-serif" font-size="12.5" fill="#15201A">{esc(titulo)}</text>
<text x="208" y="62" font-family="Georgia, 'Times New Roman', serif" font-size="32" font-weight="700" fill="#15201A">{fmt(valor)}<tspan font-size="14" font-weight="400" fill="#55645B"> / 100</tspan></text>
<rect x="208" y="68" width="{14 + 6.6 * len(rot):.0f}" height="18" rx="9" fill="{bg}"/>
<text x="215" y="81" font-family="Arial, Helvetica, sans-serif" font-size="11.5" fill="{fg}">{esc(rot)}</text>
</svg>
"""


def gerar():
    """Escreve selos/mare-UF.svg para as 27 UFs, selos/mare-brasil.svg e o README de uso."""
    indice = json.load(open(DATA / "indice.json", encoding="utf-8"))
    estados = {u["uf"]: u["nome"] for u in json.load(open(DATA / "estados.json", encoding="utf-8"))["ufs"]}
    corte = json.load(open(DATA / "meta.json", encoding="utf-8")).get("corte", "")
    SAIDA.mkdir(exist_ok=True)
    for uf, v in sorted(indice.items()):
        (SAIDA / f"mare-{uf}.svg").write_text(svg_selo(estados[uf], uf, v["total"], corte), encoding="utf-8")
    media = round(sum(v["total"] for v in indice.values()) / len(indice), 1)
    (SAIDA / "mare-brasil.svg").write_text(svg_selo("Brasil", "BR", media, corte, nacional=True), encoding="utf-8")
    (SAIDA / "README.md").write_text(f"""# Selos do índice MARÉ

Um selo SVG por estado (`mare-UF.svg`) e um nacional (`mare-brasil.svg`),
regravados a cada atualização semanal com o número publicado no índice.
Para embutir no seu site, cole:

```html
<a href="{SITE}/#SC"><img src="{SITE}/selos/mare-SC.svg" width="360" height="92"
   alt="MARÉ, Monitor El Niño Brasil: Santa Catarina, preparação demonstrável publicamente"></a>
```

O selo diz o que o índice mede — preparação *demonstrável publicamente* — e
nunca "preparado". Não altere o número: o arquivo é regravado pelo pipeline e
o site confere, a cada publicação, que cada selo bate com `data/indice.json`.
Licença: MIT, como o restante do projeto.
""", encoding="utf-8")
    return len(indice) + 1


def self_test():
    """Cortes de faixa iguais aos do site; render contém o número; determinismo."""
    assert faixa(11.9)[0] == "Estágio inicial" and faixa(25)[0] == "Em construção"
    assert faixa(49.9)[0] == "Em construção" and faixa(50)[0] == "Consolidado" and faixa(70)[0] == "Avançado"
    s = svg_selo("Santa Catarina", "SC", 78.6, "31/08/2026")
    assert "78,6" in s and "Avançado" in s and 'role="img"' in s and "&" not in s.replace("&amp;", "").replace("&lt;", "").replace("&gt;", "")
    assert s == svg_selo("Santa Catarina", "SC", 78.6, "31/08/2026"), "render não determinístico"
    print("✓ self-test OK — faixas iguais ao site, render com número e faixa, determinístico")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    n = gerar()
    print(f"✓ {n} selos gravados em selos/ (27 UFs + Brasil)")
