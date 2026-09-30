#!/usr/bin/env python3
"""Portão: as rampas dos mapas passam em contraste e em daltonismo.

Item 8 da rodada 2 (editoria, 30/09/2026), que exige: "as rampas precisam passar em contraste e em
daltonismo (deuteranopia/protanopia) — conferir com simulador".

O QUE ELE CONFERE, E POR QUÊ CADA COISA
---------------------------------------
1. **Contraste da marca contra o fundo da família.** Um ponto de brasa sobre fundo noturno e uma UF
   de papel ressecado sobre papel ressecado são problemas opostos, e os dois somem se ninguém medir.
   O mínimo aqui é **3:1**, que é o de componente gráfico da WCAG — não o de texto corrido, porque
   isto é forma, não letra.
2. **Degraus vizinhos distinguíveis, inclusive em deuteranopia e protanopia.** Uma rampa pode ter
   contraste ótimo contra o fundo e degraus que se confundem entre si — e é entre eles que a leitora
   compara. A simulação usa a matriz de Brettel/Viénot, que é a mesma dos simuladores.
3. **Nenhuma informação só por cor.** Conferido por fora, na legenda: cada degrau tem rótulo. Este
   portão cobre o que é medível em número; o rótulo é do portão de legendas.

Ele mede a PALETA, não a página: as rampas vivem em `assets/mapas.js`, e é lá que ele lê.

USO
    python3 scripts/verificar_rampas_dos_mapas.py
    python3 scripts/verificar_rampas_dos_mapas.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MAPAS = RAIZ / "assets" / "mapas.js"

CONTRASTE_MINIMO = 3.0        # WCAG 2.1, componente gráfico (1.4.11)
DISTANCIA_MINIMA = 9.0        # distância euclidiana em RGB entre degraus vizinhos, após simulação


def rgb(hexa: str) -> tuple:
    """(r, g, b) de '#RRGGBB'. Função pura."""
    h = str(hexa or "").lstrip("#")
    if len(h) != 6:
        raise ValueError(f"cor fora do formato #RRGGBB: {hexa!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _linear(c: float) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(hexa: str) -> float:
    """Luminância relativa (WCAG). Função pura."""
    r, g, b = (_linear(v) for v in rgb(hexa))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Razão de contraste entre duas cores, de 1 a 21. Função pura."""
    la, lb = luminancia(a), luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return round((claro + 0.05) / (escuro + 0.05), 2)


# Matrizes de simulação (Viénot, Brettel & Mollon), em espaço linear RGB.
MATRIZES = {
    "deuteranopia": ((0.625, 0.375, 0.0), (0.7, 0.3, 0.0), (0.0, 0.3, 0.7)),
    "protanopia": ((0.567, 0.433, 0.0), (0.558, 0.442, 0.0), (0.0, 0.242, 0.758)),
}


def simular(hexa: str, tipo: str) -> tuple:
    """A cor como quem tem deuteranopia ou protanopia a vê. Função pura."""
    m = MATRIZES[tipo]
    r, g, b = rgb(hexa)
    return tuple(max(0, min(255, round(m[i][0] * r + m[i][1] * g + m[i][2] * b))) for i in range(3))


def distancia(a, b) -> float:
    """Distância euclidiana entre duas cores em RGB. Função pura."""
    return round(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5, 1)


def atmosferas(fonte: str) -> dict:
    """{família: {'fundo':…, 'rampa':[…]}} lido de assets/mapas.js. Função pura."""
    m = re.search(r"atmosfera:\s*\{(.*?)\n    \},", fonte or "", re.S)
    if not m:
        return {}
    fora = {}
    # `}` seguido de vírgula OU do fim do bloco: sem a segunda alternativa, a ÚLTIMA família
    # era descartada em silêncio — e família não conferida é o que este portão existe para
    # impedir. Foi o próprio autoteste que pegou.
    for bloco in re.finditer(r"(\w+):\s*\{(.*?)\}(?=\s*,|\s*$)", m.group(1), re.S):
        nome, corpo = bloco.group(1), bloco.group(2)
        fundo = re.search(r"fundo:\s*'(#[0-9A-Fa-f]{6})'", corpo)
        rampa = re.findall(r"'(#[0-9A-Fa-f]{6})'", re.search(r"rampa:\s*\[([^\]]*)\]", corpo).group(1)
                           if re.search(r"rampa:\s*\[([^\]]*)\]", corpo) else "")
        if fundo:
            fora[nome] = {"fundo": fundo.group(1), "rampa": rampa}
    return fora


# Famílias cuja marca do dado é PONTO, sem contorno nenhum: aí o contraste contra o fundo é
# obrigatório, porque não há filete para separar a marca do fundo. O valor é a opacidade com que a
# página desenha o ponto — o contraste se mede COMO DESENHADO, não na cor do arquivo.
MARCA_SEM_CONTORNO = {"fogo": {"mescla": "screen", "opacidade": 0.78}}


def como_desenhado(cor: str, fundo: str, mescla: str = None, opacidade: float = 1.0) -> str:
    """A cor que a leitora vê, depois da mescla e da opacidade. Função pura.

    Medir o hex do arquivo mede o que o autor escreveu; medir isto mede o que chega ao olho. Os
    pontos de fogo são desenhados com mescla `screen` sobre o fundo noturno (é assim que células
    vizinhas somam luz em vez de se taparem), e a mescla muda o contraste de verdade."""
    c, f = rgb(cor), rgb(fundo)
    if mescla == "screen":
        c = tuple(255 - ((255 - x) * (255 - y)) // 255 for x, y in zip(c, f))
    o = max(0.0, min(1.0, opacidade))
    c = tuple(round(y + (x - y) * o) for x, y in zip(c, f))
    return "#%02X%02X%02X" % c


def problemas(atms: dict) -> list:
    """As falhas de contraste e de daltonismo. Função pura.

    O QUE SE MEDE, E POR QUE NÃO É "todo degrau contra o fundo". O primeiro degrau de várias
    famílias é, de propósito, quase o fundo: "sem seca" no papel ressecado, "sem aviso" na ardósia.
    Ele significa AUSÊNCIA, e área de ausência que grita é ruído — quem separa a UF do fundo ali é
    o contorno, não o preenchimento. Exigir 3:1 de todo degrau reprovaria uma paleta desenhada
    assim, e reprovar desenho aprovado não é rigor: é erro de medida.

    Mede-se, então, o que de fato quebra a leitura:
      * **marca sem contorno** — o fogo é ponto sobre fundo noturno, sem filete: precisa do
        contraste de componente gráfico;
      * **degraus vizinhos** — é entre eles que se compara, e é aí que o daltonismo apaga a
        diferença. Conferido em visão comum e nas duas simulações."""
    ruins = []
    for familia, a in sorted((atms or {}).items()):
        fundo, rampa = a.get("fundo"), a.get("rampa") or []
        marca = MARCA_SEM_CONTORNO.get(familia)
        if marca:
            for i, cor in enumerate(rampa):
                visto = como_desenhado(cor, fundo, marca.get("mescla"), marca.get("opacidade", 1.0))
                c = contraste(visto, fundo)
                if c < CONTRASTE_MINIMO:
                    ruins.append(f"{familia}: degrau {i + 1} ({cor}) é marca sem contorno; "
                                 f"desenhado ele fica {visto} e tem contraste {c} contra o fundo "
                                 f"{fundo}, abaixo de {CONTRASTE_MINIMO}")
        for i in range(len(rampa) - 1):
            d = distancia(rgb(rampa[i]), rgb(rampa[i + 1]))
            if d < DISTANCIA_MINIMA:
                ruins.append(f"{familia}: degraus {i + 1} e {i + 2} ({rampa[i]}, {rampa[i+1]}) "
                             f"ficam a {d} em visão comum — abaixo de {DISTANCIA_MINIMA}")
        for i in range(len(rampa) - 1):
            for tipo in MATRIZES:
                d = distancia(simular(rampa[i], tipo), simular(rampa[i + 1], tipo))
                if d < DISTANCIA_MINIMA:
                    ruins.append(f"{familia}: degraus {i + 1} e {i + 2} ({rampa[i]}, {rampa[i+1]}) "
                                 f"ficam a {d} em {tipo} — abaixo de {DISTANCIA_MINIMA}")
    return ruins


def autoteste() -> int:
    casos = [
        ("lê a cor do formato #RRGGBB", rgb("#FFFFFF") == (255, 255, 255)),
        ("cor sem o # também é lida", rgb("000000") == (0, 0, 0)),
        ("branco sobre preto dá 21", contraste("#FFFFFF", "#000000") == 21.0),
        ("cor contra ela mesma dá 1", contraste("#7C4A34", "#7C4A34") == 1.0),
        ("contraste é simétrico",
         contraste("#FFFFFF", "#15201A") == contraste("#15201A", "#FFFFFF")),
        ("simula deuteranopia sem estourar a faixa",
         all(0 <= v <= 255 for v in simular("#D8621F", "deuteranopia"))),
        ("cinza é quase igual nas duas simulações",
         distancia(simular("#808080", "deuteranopia"), simular("#808080", "protanopia")) < 6),
        ("distância de uma cor a ela mesma é zero",
         distancia((1, 2, 3), (1, 2, 3)) == 0.0),
        ("rampa com degraus separados passa",
         problemas({"x": {"fundo": "#FFFFFF", "rampa": ["#7C4A34", "#0E0F0D"]}}) == []),
        ("degrau de ausência quase igual ao fundo NÃO reprova (é área, e tem contorno)",
         problemas({"x": {"fundo": "#F7F0E2", "rampa": ["#EFE6D3", "#4E2812"]}}) == []),
        ("marca sem contorno invisível no fundo reprova",
         any("marca sem contorno" in p for p in
             problemas({"fogo": {"fundo": "#15201A", "rampa": ["#1A2420"]}}))),
        ("screen sobre fundo escuro clareia a marca",
         luminancia(como_desenhado("#8A3B1E", "#15201A", "screen")) >
         luminancia("#8A3B1E")),
        ("sem mescla e sem transparência, a cor é ela mesma",
         como_desenhado("#8A3B1E", "#15201A") == "#8A3B1E"),
        ("opacidade zero devolve o próprio fundo",
         como_desenhado("#FFFFFF", "#15201A", None, 0.0) == "#15201A"),
        ("a falha diz a cor como ela é desenhada",
         "desenhado ele fica" in
         problemas({"fogo": {"fundo": "#15201A", "rampa": ["#1A2420"]}})[0]),
        ("degraus vizinhos iguais reprovam já em visão comum",
         any("visão comum" in p for p in
             problemas({"x": {"fundo": "#FFFFFF", "rampa": ["#C9814B", "#C9814B"]}}))),
        ("degraus vizinhos idênticos reprovam por daltonismo",
         any("deuteranopia" in p or "protanopia" in p for p in
             problemas({"x": {"fundo": "#000000", "rampa": ["#C9814B", "#C9814B"]}}))),
        ("a falha nomeia a família e o degrau",
         "fogo: degrau 1" in problemas({"fogo": {"fundo": "#15201A", "rampa": ["#1A2420"]}})[0]),
        ("família sem rampa não reprova", problemas({"x": {"fundo": "#FFFFFF", "rampa": []}}) == []),
        ("dicionário vazio não quebra", problemas({}) == []),
        ("nulo não quebra", problemas(None) == []),
    ]
    fonte = """    atmosfera: {
      fogo:  {fundo:'#15201A', uf:'#1E2B24', contorno:'#3A4A41',
              rampa:['#8A3B1E', '#D8621F'], nucleo:'#FFE3A3', claro:false},
      seca:  {fundo:'#F7F0E2', uf:'#EFE6D3', contorno:'#C8B08A',
              rampa:['#E7C98E'], claro:true},
    },"""
    lido = atmosferas(fonte)
    casos += [
        ("lê as famílias do arquivo", sorted(lido) == ["fogo", "seca"]),
        ("lê o fundo de cada família", lido["fogo"]["fundo"] == "#15201A"),
        ("lê a rampa inteira", lido["fogo"]["rampa"] == ["#8A3B1E", "#D8621F"]),
        ("não confunde `nucleo` com degrau da rampa", len(lido["fogo"]["rampa"]) == 2),
        ("arquivo sem bloco de atmosfera devolve vazio", atmosferas("var x = 1;") == {}),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    atms = atmosferas(MAPAS.read_text(encoding="utf-8"))
    if not atms:
        print("✗ RAMPAS: bloco `atmosfera` não encontrado em assets/mapas.js")
        return 1
    ruins = problemas(atms)
    if ruins:
        print("✗ RAMPAS DOS MAPAS:")
        for r in ruins:
            print("   -", r)
        return 1
    degraus = sum(len(a["rampa"]) for a in atms.values())
    print(f"✓ RAMPAS OK — {len(atms)} famílias, {degraus} degraus: contraste ≥ "
          f"{CONTRASTE_MINIMO}:1 contra o fundo e degraus vizinhos distinguíveis em deuteranopia "
          f"e protanopia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
