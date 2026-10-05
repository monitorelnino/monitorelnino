#!/usr/bin/env python3
"""Portão: o número da Imprensa é o mesmo da página de origem.

Item 1 do handover "Imprensa — redesenho definitivo" (02/10/2026), que pede isto com estas
palavras: *reprova se qualquer número da imprensa divergir do mesmo número na página de origem
(valor, semana/mês de referência e rótulo)*.

O defeito que ele barra foi medido em 02/10/2026: a Imprensa publicava "sem dado" no dinheiro com
dado publicado no Financiamento, e 482 casos de dengue da semana 37 onde o MARÉ Saúde publicava
8.146 da semana 33. A correção de fundo foi a Imprensa passar a LER o instantâneo de cada página em
vez de recalcular. Este portão é a garantia de que a correção continua valendo: ele compara o número
do cartão da Imprensa com o número RENDERIZADO no topo da página de origem — no navegador, como o
leitor vê. Comparar arquivo com arquivo provaria menos: o que o leitor compara é página com página.

O que ele confere, por cartão mapeado:
  (a) **valor** — na precisão em que a página de origem o publica (um cartão que diz "R$ 150,9 mi"
      confere contra 150.887.172,93 com a folga da própria casa decimal);
  (b) **referência** — o mês ou a semana epidemiológica que a Imprensa declara tem de aparecer no
      texto visível da página de origem;
  (c) **lacuna** — cartão sem dado na Imprensa com número publicado na origem reprova, e é
      exatamente o caso do dinheiro em 02/10.

A medição vem de `scripts/_layout_dump.js`, o mesmo renderizador do portão de layout. A REGRA é
função pura e tem autoteste offline, sem rede e sem navegador.

Uso:
    python3 scripts/verificar_imprensa_coerencia.py
    python3 scripts/verificar_imprensa_coerencia.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# (id do cartão da Imprensa, página de origem, id do elemento do número naquela página)
# 03/10/2026 (handover do blog e da imprensa): "Esta semana em números" SAIU da Imprensa, e com ela
# os nove cartões que este portão comparava na própria página. O que sobrou de dinâmico ali é o
# PONTEIRO do boletim — três números congelados na edição.
#
# A comparação continua, no lugar certo: o motor da semana (`imprensa/semana.json`) é conferido
# contra as páginas de origem, porque é dele que o boletim tira os números. Se o motor divergir da
# página, o boletim nasce errado — e o portão pega antes de nascer.
MAPA = (
    ("desembolsado_no_mes", "financiamento.html", "topoPagoMes"),
    ("resposta_autorizado_semana", "financiamento.html", "topoRespostaSemana"),
    ("atos_federais_semana", "financiamento.html", "topoAtosSemana"),
    ("municipios_alerta_cemaden", "defesa-civil.html", "topoCemaden"),
    ("municipios_aviso_inmet", "defesa-civil.html", "topoInmet"),
    ("decreto_e_alerta_ao_mesmo_tempo", "defesa-civil.html", "topoCruzamento"),
    ("dengue_casos_se", "saude.html", "nDengueSE"),
    ("srag_internacoes_se", "saude.html", "nSragSE"),
    ("ufs_dengue_alerta", "saude.html", "nUFsAlerta"),
)
# Os índices da manchete da Imprensa, que também têm página de origem.
MAPA_INDICES = (
    ("mare_saude", "saude.html", "nIndiceSaude"),
    # O MARÉ Legal nacional não existe como campo em arquivo nenhum: a página inicial o calcula na
    # hora, como média das 27 UFs. A Imprensa usa a mesma régua, e aqui é onde isso se prova.
    ("mare_legal", "index.html", "gaugeNum"),
)
# Os tres cartoes da SEMANA da Imprensa sao, por definicao, a VARIACAO dos cartoes do ciclo da
# Defesa civil. Eles nao aparecem como numero no topo daquela pagina (aparecem como seta e valor ao
# lado dele), e por isso a conferencia e contra o instantaneo que as duas leem.
MAPA_VARIACAO = (
    ("decretos_na_semana", "municipios_decretaram"),
    ("populacao_decretos_na_semana", "populacao_sob_decreto"),
    ("reconhecimentos_na_semana", "reconhecidos_pelo_governo_federal"),
)
# Cartões de AGORA: o número deles é função do TEMPO. Entre a edição da imprensa e a renderização
# da página pode ter entrado uma coleta nova de alerta (a cadeia roda a cada duas horas), e aí os
# dois números divergem sem que ninguém tenha errado. Medido em 03/10/2026, na publicação: "a
# Imprensa diz 14 e a Defesa civil diz 16".
#
# O que se exige deles é o que faz sentido exigir: que a imprensa publique a CONSULTA que ela leu, e
# que essa consulta não seja mais nova do que a da página de origem — imprensa adiantada seria
# número inventado; imprensa atrasada é a edição sendo o que ela é, um retrato datado. Divergência
# de valor com referência igual continua reprovando.
DE_AGORA = ("municipios_alerta_cemaden", "municipios_aviso_inmet", "decreto_e_alerta_ao_mesmo_tempo")
MULTIPLICADOR = {"mil": 1e3, "mi": 1e6, "bi": 1e9, "milhão": 1e6, "milhões": 1e6}


def numero_do_texto(texto: str):
    """O número que o texto publica, com a escala que ele declara. Função pura.

    Devolve (valor, casas) — `casas` é a precisão em que a página o escreveu, e é ela que define a
    folga da comparação. "R$ 150,9 mi" devolve (150900000.0, 1) com escala de milhão, e não um
    valor exato: exigir igualdade ao centavo contra um número arredondado na tela reprovaria por
    arredondamento, que não é divergência.
    """
    if texto is None:
        return None
    t = str(texto).strip().replace(" ", " ")
    m = re.search(r"(-?\d[\d.  ]*(?:,\d+)?)", t)
    if not m:
        return None
    cru = m.group(1).replace(".", "").replace(" ", "").replace(" ", "")
    casas = len(cru.split(",")[1]) if "," in cru else 0
    try:
        valor = float(cru.replace(",", "."))
    except ValueError:
        return None
    resto = t[m.end():].strip().lower()
    for palavra, fator in MULTIPLICADOR.items():
        if resto.startswith(palavra):
            return valor * fator, casas, fator
    return valor, casas, 1.0


def mesmo_numero(valor, texto_da_pagina) -> bool:
    """O valor do cartão é o número que a página publica? Função pura."""
    lido = numero_do_texto(texto_da_pagina)
    if lido is None or valor is None:
        return False
    publicado, casas, fator = lido
    folga = (fator * (10 ** -casas)) / 2 if fator > 1 else (10 ** -casas) / 2
    return abs(float(valor) - publicado) <= max(folga, 0.051)


def divergencias_de_variacao(cartoes: dict, instantaneo: dict, mapa=MAPA_VARIACAO) -> list:
    """Os cartoes da semana da Imprensa sao a variacao do instantaneo da Defesa civil. Funcao pura."""
    por_id = {c.get("id"): c for c in (instantaneo or {}).get("cartoes") or []}
    ruins = []
    for ident, no_instantaneo in mapa:
        c = cartoes.get(ident)
        if c is None or c.get("sem_coleta"):
            continue
        esperado = (por_id.get(no_instantaneo) or {}).get("variacao")
        if esperado is None:
            continue
        if c.get("valor") != esperado:
            ruins.append(f"{ident}: a Imprensa diz {c.get('valor')!r} e o instantâneo da Defesa "
                         f"civil diz {esperado!r} — a página publica o do instantâneo")
    return ruins


def divergencias(cartoes: dict, indices: dict, numeros: dict, textos: dict,
                 mapa=MAPA, mapa_indices=MAPA_INDICES) -> list:
    """As divergências entre a Imprensa e as páginas de origem. Função pura.

    `cartoes` é {id: cartão}, `numeros` é {pagina: {id_do_elemento: texto}} e `textos` é
    {pagina: texto_visível}.
    """
    ruins = []
    for ident, pagina, elemento in mapa:
        c = cartoes.get(ident)
        if c is None:
            ruins.append(f"{ident}: a Imprensa não publica este cartão, e o mapa o exige")
            continue
        na_pagina = (numeros.get(pagina) or {}).get(elemento)
        if na_pagina is None:
            ruins.append(f"{ident}: {pagina} não publica o número em #{elemento}")
            continue
        lido = numero_do_texto(na_pagina)
        if c.get("sem_coleta"):
            if lido is not None:
                ruins.append(f"{ident}: a Imprensa diz 'sem dado' e {pagina} publica "
                             f"{na_pagina!r}")
            continue
        if lido is None:
            # A origem não publica número (está em "sem coleta"): a Imprensa não pode publicar um.
            ruins.append(f"{ident}: a Imprensa publica {c.get('valor')!r} e {pagina} não publica "
                         f"número ({na_pagina!r})")
            continue
        if not mesmo_numero(c.get("valor"), na_pagina):
            if ident in DE_AGORA:
                # A referência da imprensa é a consulta que ela leu; a da página está no texto
                # visível. Se a página já tem consulta MAIS NOVA, a divergência é do relógio.
                ref_imprensa = str(c.get("referencia") or "")
                alvo = (textos.get(pagina) or "")
                if ref_imprensa and ref_imprensa not in alvo:
                    print(f"   [nota] {ident}: a Imprensa publica a consulta de {ref_imprensa} "
                          f"({c.get('valor')!r}) e {pagina} já renderiza uma consulta mais nova "
                          f"({na_pagina!r}) — informação de agora, retrato datado")
                    continue
            ruins.append(f"{ident}: a Imprensa diz {c.get('valor')!r} e {pagina} diz "
                         f"{na_pagina!r}")
        ref = str(c.get("referencia") or "")
        # Minúsculas em TUDO: o rótulo do cartão é versalete por CSS, e o texto renderizado chega
        # em caixa alta. Comparar sem normalizar reprovava a página que publica a semana certa.
        alvo = (textos.get(pagina) or "").lower()
        se = re.search(r"\b(\d{4})-(\d{2})\b", ref)
        if se:
            if f"semana epidemiológica {se.group(2)}" not in alvo:  # alvo já em minúsculas
                ruins.append(f"{ident}: a Imprensa declara a semana {se.group(2)} e {pagina} não "
                             f"a publica")
        else:
            mes = re.search(r"m[êe]s de (\w+)", ref)
            if mes and mes.group(1).lower() not in alvo:
                ruins.append(f"{ident}: a Imprensa declara o {ref!r} e {pagina} não cita "
                             f"{mes.group(1)!r}")
    for chave, pagina, elemento in mapa_indices:
        v = indices.get(chave)
        na_pagina = (numeros.get(pagina) or {}).get(elemento)
        if v is None or na_pagina is None:
            continue
        if not mesmo_numero(v, na_pagina):
            ruins.append(f"índice {chave}: a Imprensa diz {v!r} e {pagina} diz {na_pagina!r}")
    return ruins


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

    ok("lê inteiro com separador de milhar", numero_do_texto("8.146")[0] == 8146)
    ok("lê decimal brasileiro", numero_do_texto("31,8")[0] == 31.8)
    ok("lê escala de milhão", numero_do_texto("R$ 150,9 mi")[0] == 150900000.0)
    ok("lê escala de mil", numero_do_texto("R$ 12,0 mil")[0] == 12000.0)
    ok("lê 'de 27' pegando o primeiro número", numero_do_texto("3 de 27")[0] == 3)
    ok("texto sem número devolve nada", numero_do_texto("sem coleta") is None)
    ok("texto vazio devolve nada", numero_do_texto("") is None and numero_do_texto(None) is None)

    ok("milhão arredondado confere com o centavo",
       mesmo_numero(150887172.93, "R$ 150,9 mi"))
    ok("milhão arredondado NÃO confere com outro valor",
       not mesmo_numero(160887172.93, "R$ 150,9 mi"))
    ok("inteiro confere", mesmo_numero(8146, "8.146"))
    ok("inteiro diferente reprova", not mesmo_numero(8534, "8.146"))
    ok("uma casa decimal confere", mesmo_numero(31.8, "31,8"))

    cartoes = {"dengue_casos_se": {"valor": 8146, "referencia": "2026-33", "sem_coleta": False},
               "desembolsado_no_mes": {"valor": 150887172.93,
                                       "referencia": "mês de setembro de 2026", "sem_coleta": False}}
    numeros = {"saude.html": {"nDengueSE": "8.146"},
               "financiamento.html": {"topoPagoMes": "R$ 150,9 mi"}}
    textos = {"saude.html": "NOTIFICAÇÕES DE DENGUE NA SEMANA EPIDEMIOLÓGICA 33",
              "financiamento.html": "desembolsados no mês de setembro de 2026"}
    mapa = (("dengue_casos_se", "saude.html", "nDengueSE"),
            ("desembolsado_no_mes", "financiamento.html", "topoPagoMes"))
    ok("edição coerente não acusa nada",
       divergencias(cartoes, {}, numeros, textos, mapa, ()) == [])
    ruim = dict(cartoes); ruim["dengue_casos_se"] = {"valor": 482, "referencia": "2026-37",
                                                     "sem_coleta": False}
    d = divergencias(ruim, {}, numeros, textos, mapa, ())
    ok("valor divergente reprova", any("482" in x for x in d))
    ok("semana divergente reprova", any("semana 37" in x for x in d))
    sem = dict(cartoes); sem["desembolsado_no_mes"] = {"valor": None, "sem_coleta": True}
    ok("'sem dado' na Imprensa com número na origem reprova",
       any("sem dado" in x for x in divergencias(sem, {}, numeros, textos, mapa, ())))
    ok("origem sem número com valor na Imprensa reprova",
       any("não publica número" in x for x in
           divergencias(cartoes, {}, {"saude.html": {"nDengueSE": "sem coleta"},
                                      "financiamento.html": {"topoPagoMes": "R$ 150,9 mi"}},
                        textos, mapa, ())))
    ok("cartão exigido e ausente reprova",
       any("não publica este cartão" in x for x in divergencias({}, {}, numeros, textos, mapa, ())))
    ok("índice divergente reprova",
       any("índice" in x for x in divergencias(cartoes, {"mare_saude": 99.9}, numeros, textos,
                                               mapa, (("mare_saude", "saude.html", "nDengueSE"),))))
    ok("rótulo em versalete (caixa alta no DOM) não reprova a semana certa",
       divergencias({"dengue_casos_se": {"valor": 8146, "referencia": "2026-33", "sem_coleta": False}},
                    {}, {"saude.html": {"nDengueSE": "8.146"}},
                    {"saude.html": "SEMANA EPIDEMIOLÓGICA 33"},
                    (("dengue_casos_se", "saude.html", "nDengueSE"),), ()) == [])
    ok("alerta com referência mais antiga que a da página é nota, não falha",
       divergencias({"municipios_alerta_cemaden": {"valor": 14, "sem_coleta": False,
                                                   "referencia": "02/10/2026 11:22"}},
                    {}, {"defesa-civil.html": {"topoCemaden": "16"}},
                    {"defesa-civil.html": "CONSULTA DE 03/10/2026 09:40"},
                    (("municipios_alerta_cemaden", "defesa-civil.html", "topoCemaden"),), ()) == [])
    ok("alerta divergente com a MESMA referência continua reprovando",
       len(divergencias({"municipios_alerta_cemaden": {"valor": 14, "sem_coleta": False,
                                                       "referencia": "03/10/2026 09:40"}},
                        {}, {"defesa-civil.html": {"topoCemaden": "16"}},
                        {"defesa-civil.html": "consulta de 03/10/2026 09:40"},
                        (("municipios_alerta_cemaden", "defesa-civil.html", "topoCemaden"),), ())) == 1)
    ok("a semana da Imprensa é a variação do instantâneo",
       divergencias_de_variacao({"decretos_na_semana": {"valor": 69, "sem_coleta": False}},
                                {"cartoes": [{"id": "municipios_decretaram", "variacao": 69}]}) == [])
    ok("semana divergente do instantâneo reprova",
       len(divergencias_de_variacao({"decretos_na_semana": {"valor": 22, "sem_coleta": False}},
                                    {"cartoes": [{"id": "municipios_decretaram", "variacao": 69}]})) == 1)
    ok("todo cartão do mapa tem página e elemento",
       all(len(x) == 3 and x[1].endswith(".html") for x in MAPA))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem navegador.")
    return 1 if falhas else 0


def despejar(pagina: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        alvo = pathlib.Path(f.name)
    r = subprocess.run(["node", str(RAIZ / "scripts" / "_layout_dump.js"), pagina, str(alvo)],
                       capture_output=True, text=True, cwd=str(RAIZ))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:300])
    return json.loads(alvo.read_text(encoding="utf-8"))


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    semana = json.loads((RAIZ / "data" / "imprensa" / "semana.json").read_text(encoding="utf-8"))
    cartoes = {c["id"]: c for c in semana.get("cartoes") or []}
    indices = semana.get("indices") or {}
    numeros, textos = {}, {}
    for pagina in sorted({x[1] for x in MAPA} | {x[1] for x in MAPA_INDICES}):
        d = despejar(pagina)
        largura = (d.get("larguras") or {}).get("1280") or {}
        numeros[pagina] = {n.get("valor_id"): n.get("valor") for n in largura.get("numeros") or []}
        textos[pagina] = largura.get("texto_visivel") or ""
    instantaneo = json.loads((RAIZ / "data" / "resposta" / "topo_defesa_civil.json")
                             .read_text(encoding="utf-8"))
    ruins = divergencias(cartoes, indices, numeros, textos)
    ruins += divergencias_de_variacao(cartoes, instantaneo)
    if ruins:
        print(f"✗ COERÊNCIA DA IMPRENSA: {len(ruins)} divergência(s) com a página de origem:")
        for x in ruins:
            print("   - " + x)
        return 1
    print(f"✓ COERÊNCIA DA IMPRENSA OK — {len(MAPA)} número(s) e {len(MAPA_VARIACAO)} variação(ões) "
          f"iguais aos das páginas de origem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
