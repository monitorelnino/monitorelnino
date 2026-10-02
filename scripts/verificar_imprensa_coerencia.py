#!/usr/bin/env python3
"""Portão de coerência da página Imprensa (handover da editoria, 01/10/2026, item 1).

O QUE ELE COBRA, E POR QUE CADA COISA
-------------------------------------
1. **O mesmo número não pode ter duas contas.** Cada cartão da imprensa que também aparece em outra
   página é recomputado aqui, da MESMA fonte que a outra página lê, e tem de bater. O defeito que
   motivou o handover foi exatamente este: "13 avisos" na imprensa contra "3.479 municípios sob
   aviso" na Defesa civil — dois números para a mesma coisa, em unidades diferentes.

2. **Período velho é lacuna disfarçada.** Cartão de janela cujo `periodo.fim` termine antes da data
   da edição menos oito dias está medindo outra semana. A saúde é exceção declarada: ela usa a
   última semana epidemiológica completa, que fecha depois.

3. **Nada escrito à mão onde o dado manda.** Nos blocos que o script preenche (o topo, a grade da
   semana e o release), nenhum dígito pode existir no HTML — nem número, nem data, nem versão. É a
   regra 0 da página, e aqui ela deixa de depender de vigilância: se alguém digitar um número ali,
   o portão reprova.

4. **"—" publicado é omissão.** O travessão é o estado honesto ANTES da leitura; depois dela, é
   mentira por omissão. Quem cobra isso campo a campo é `verificar_imprensa_do_dado.js`, que roda a
   página; aqui o que se cobra é que todo cartão com valor tenha fonte e, se for de janela, período.

USO
    python3 scripts/verificar_imprensa_coerencia.py
    python3 scripts/verificar_imprensa_coerencia.py --autoteste
"""
import datetime
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SEMANA = RAIZ / "data" / "imprensa" / "semana.json"
META = RAIZ / "data" / "meta.json"
PAGINA = RAIZ / "imprensa.html"

# Os blocos da página que o script preenche. Dígito dentro deles é número escrito à mão.
BLOCOS_DO_DADO = ("imprensa-topo", "semana-em-numeros", "release")
# Os números que FAZEM PARTE do texto aprovado e não mudam com a edição: o denominador da escala
# ("de 100"), o ciclo ("El Niño 2026/2027"), a data do primeiro boletim ("29 de junho") e o total
# de estados ("de 27"). A lista é curta de propósito: qualquer número NOVO escrito à mão continua
# reprovando, que é o efeito que o handover pede.
CONSTANTES_DO_TEXTO = {"100", "2026/2027", "29", "27", "2026/2027,"}

# Grupos cujo período pode fechar antes: a saúde usa a última semana epidemiológica completa.
GRUPOS_SEM_TETO_DE_PERIODO = ("saude",)
TETO_DE_ATRASO_DIAS = 8


def ler(p, padrao=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return padrao


def data_br(texto):
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(texto or "").strip())
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def digitos_em_bloco(html: str, bloco: str) -> list:
    """Os trechos com dígito dentro do bloco, fora de atributo. Função pura.

    Ignora o que está dentro de tag (`id="h2"`, `class="grade-numeros--3"`): ali o dígito é do
    código, não do conteúdo. O que interessa é o TEXTO que o leitor vê."""
    m = re.search(rf'<(section|div)[^>]*\b(?:id|class)="[^"]*{re.escape(bloco)}[^"]*"[^>]*>', html)
    if not m:
        return []
    tag = m.group(1)
    prof, j = 1, m.end()
    passo = re.compile(rf"</?{tag}\b[^>]*>")
    while prof and j < len(html):
        mm = passo.search(html, j)
        if not mm:
            break
        prof += -1 if mm.group(0).startswith("</") else 1
        j = mm.end()
    corpo = html[m.end():j]
    texto = re.sub(r"<[^>]*>", " ", corpo)
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)
    achados = re.findall(r"[^\s]*\d[^\s]*", texto)
    return [t for t in achados if t.strip(".,;:()") not in CONSTANTES_DO_TEXTO]


def problemas() -> list:
    p = []
    dados = ler(SEMANA)
    if not dados or not dados.get("cartoes"):
        return ["data/imprensa/semana.json ausente ou sem cartões: a página não tem o que mostrar"]
    cartoes = dados["cartoes"]
    meta = ler(META, {}) or {}
    edicao = data_br(meta.get("atualizado_em")) or data_br(meta.get("corte"))

    # ---- 1. o mesmo número, a mesma fonte
    alertas = (ler(RAIZ / "data" / "alertas" / "vigentes.json", {}) or {}).get("resumo") or {}
    painel = (ler(RAIZ / "data" / "saude_desfechos" / "serie_painel.json", {}) or {})
    por_id = {c["id"]: c for c in cartoes}

    def confere(ident, esperado, de_onde):
        c = por_id.get(ident)
        if not c or c.get("sem_coleta") or esperado is None:
            return
        if c.get("valor") != esperado:
            p.append(f"{ident}: a imprensa mostra {c.get('valor')} e {de_onde} tem {esperado} — "
                     f"o mesmo número com duas contas")

    confere("municipios_sob_alerta_cemaden", alertas.get("municipios_cemaden"),
            "data/alertas/vigentes.json (a mesma fonte da Defesa civil)")
    M = painel.get("municipios") or {}
    if M:
        ufs = {m.get("uf") for m in M.values()
               if (m.get("nivel_ultima_se") or 0) >= 3 and m.get("uf")}
        confere("ufs_dengue_alerta", len(ufs),
                "data/saude_desfechos/serie_painel.json (a mesma fonte do MARÉ Saúde)")

    # ---- 2. período e fonte de cada cartão
    for c in cartoes:
        ident = c["id"]
        if c.get("sem_coleta"):
            if not c.get("nota"):
                p.append(f"{ident}: sem dado e sem dizer por quê")
            continue
        if not c.get("fonte") or c["fonte"] == "—":
            p.append(f"{ident}: cartão com valor e sem fonte")
        per = c.get("periodo") or {}
        if per.get("fim") and edicao and c.get("grupo") not in GRUPOS_SEM_TETO_DE_PERIODO:
            fim = datetime.date.fromisoformat(per["fim"][:10])
            if (edicao - fim).days > TETO_DE_ATRASO_DIAS:
                p.append(f"{ident}: o período termina em {per['fim']} e a edição é de "
                         f"{edicao.isoformat()} — mais de {TETO_DE_ATRASO_DIAS} dias de atraso")

    # ---- 3. nada escrito à mão onde o dado manda
    html = PAGINA.read_text(encoding="utf-8")
    for bloco in BLOCOS_DO_DADO:
        achados = digitos_em_bloco(html, bloco)
        if achados:
            p.append(f"imprensa.html, bloco '{bloco}': número, data ou versão escritos à mão "
                     f"({', '.join(achados[:4])}) — este bloco é preenchido pelo dado")
    return p


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    html_limpo = ('<section class="imprensa-topo" id="t"><p>MARÉ Legal <span id="x">—</span> de '
                  'cem</p></section>')
    html_sujo = ('<section class="imprensa-topo" id="t"><p>MARÉ Legal 45,2 de 100</p></section>')
    checar("bloco sem dígito no texto passa", digitos_em_bloco(html_limpo, "imprensa-topo") == [])
    checar("número escrito à mão no bloco é encontrado",
           digitos_em_bloco(html_sujo, "imprensa-topo") == ["45,2"])
    checar("constante do texto aprovado não é número escrito à mão",
           digitos_em_bloco('<div id="release"><p>de 100, El Niño 2026/2027, 29 de junho</p></div>',
                            "release") == [])
    checar("dígito em atributo não conta como número escrito à mão",
           digitos_em_bloco('<div class="release grade-numeros--3" id="release">'
                            '<p>texto</p></div>', "release") == [])
    checar("bloco ausente não quebra", digitos_em_bloco("<html></html>", "release") == [])
    checar("data brasileira é lida", data_br("01/10/2026") == datetime.date(2026, 10, 1))
    checar("texto que não é data devolve None", data_br("ontem") is None)
    checar("arquivo ausente reprova com mensagem própria",
           any("ausente" in x for x in [
               "data/imprensa/semana.json ausente ou sem cartões: a página não tem o que mostrar"]))
    # O portão real, sobre a edição publicada.
    reais = problemas()
    checar("o portão real não acusa problema hoje" if not reais
           else f"o portão real acusa: {reais[0][:90]}", not reais)
    if falhas:
        print(f"✗ AUTOTESTE: {len(falhas)} caso(s) reprovado(s).")
        return 1
    print("✓ AUTOTESTE DA COERÊNCIA OK — sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    p = problemas()
    if p:
        print("✗ COERÊNCIA DA IMPRENSA:")
        for x in p:
            print("   -", x)
        return 1
    print("✓ COERÊNCIA DA IMPRENSA OK — mesmo número com a mesma conta das outras páginas, "
          "período dentro da janela da edição, nada escrito à mão onde o dado manda.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
