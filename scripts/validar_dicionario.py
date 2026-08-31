#!/usr/bin/env python3
"""Valida data/dicionario_busca.json e expõe get_sinalizadores_resposta() como
fonte única de verdade do portão de natureza (verificar_consistencia.py).

Criado em 29/08/2026 a resposta à pergunta "o dicionário está correto?": até
esta correção, o portão de natureza usava uma regex solta
(`re.compile(r"emergênci|calamidade")`) desconectada do dicionário documentado
em METODOLOGIA §4.1.1(a) — duas fontes de verdade divergentes é exatamente o
tipo de furo que este script fecha.

O QUE "CORRETO" SIGNIFICA AQUI (três testes, não um):
  1. Estrutura: todo termo tem origem registrada (regra do §4.1.1a); nenhum
     grupo vazio; sinalizadores_automaticos é subconjunto de atos_resposta.
  2. Precisão: cada termo em sinalizadores_automaticos é testado contra os
     3 casos ex-ante REAIS do banco que mais se pareceriam com resposta
     (AM/AC/MS — a própria classe de erro da revisão de 29/08/2026) e NÃO
     deve disparar; e contra os 2 casos de resposta REAIS confirmados
     (AC/Decreto 11.932, PE/Decreto 60.960) e DEVE disparar. Isto é teste de
     regressão sobre um erro que já aconteceu uma vez.
  3. Variantes: toda busca roda com/sem acento e com/sem hífen (regra do
     §4.1.1a) — gerar_variantes() implementa isso e é testado.

Uso: python3 scripts/validar_dicionario.py           (roda os 3 testes)
     python3 scripts/validar_dicionario.py --self-test (idêntico; nome usado
                                                        pelas outras rotinas)
Importável: from validar_dicionario import get_sinalizadores_resposta, gerar_variantes
"""
import json
import pathlib
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).parent.parent
CAMINHO = RAIZ / "data" / "dicionario_busca.json"

# Casos de regressão reais (METODOLOGIA §16) — o texto real dos cards no dia da
# revisão. Servem de gabarito: qualquer alteração no dicionário roda contra
# eles automaticamente.
CASOS_NAO_DEVEM_DISPARAR = {
    "AM (ex-ante, sustentado)": "Estado de Emergência Climática e Ambiental preventivo (Decreto nº 54.274, DOE 01/06/2026) + Operação Amazonas+Verde",
    "AC (ex-ante, base corrigida)": "Gabinete de Crise Hídrica (Decreto nº 11.899, DOE 12/06/2026; sucede a estrutura do Decreto 11.504/2024)",
    "MS (ex-ante, sustentado)": "Decreto de emergência ambiental PREVENTIVO (DOE 03/06/2026, base alerta Cemtec) — ex-ante pelo objeto; CICOE",
}
CASOS_DEVEM_DISPARAR = {
    "AC (registro de resposta)": "Decreto nº 11.932 (03/08/2026), situação de emergência por estiagem — ato de resposta (rito SINPDEC; base da Portaria federal nº 2.659): registro de transparência, não pontua.",
    "PE (registro de resposta)": "Decreto nº 60.960 (DOE 30/06/2026), Situação de Emergência em 75 municípios por desastre de estiagem (COBRADE 1.4.1.1.0; reconhecimento federal pela Portaria nº 2.203, 03/07/2026) — ato de resposta: registro de transparência, não pontua.",
}


def _sem_acento(s):
    """Remove diacríticos preservando a base ASCII (regra de variantes do §4.1.1a)."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def gerar_variantes(termo):
    """Devolve o conjunto {original, sem acento} × {com hífen, sem hífen, com espaço}."""
    base = {termo, _sem_acento(termo)}
    variantes = set()
    for b in base:
        variantes.add(b)
        variantes.add(b.replace("-", " "))
        variantes.add(b.replace(" ", "-"))
    return variantes


def carregar():
    """Carrega e valida estruturalmente o dicionário; levanta AssertionError descrevendo o furo."""
    d = json.load(open(CAMINHO, encoding="utf-8"))
    assert "grupos" in d and d["grupos"], "dicionário sem grupos"
    todos_termos = {}
    for nome_grupo, grupo in d["grupos"].items():
        assert grupo.get("termos"), f"grupo '{nome_grupo}' sem termos"
        for t in grupo["termos"]:
            assert t.get("termo"), f"termo sem campo 'termo' em '{nome_grupo}'"
            assert t.get("origem"), f"termo '{t.get('termo')}' em '{nome_grupo}' sem origem registrada (regra §4.1.1a)"
            todos_termos.setdefault(t["termo"].lower(), []).append(nome_grupo)
    sinal = d["grupos"]["atos_resposta"].get("sinalizadores_automaticos", {}).get("termos", [])
    assert sinal, "sinalizadores_automaticos ausente ou vazio em atos_resposta"
    termos_resposta = {t["termo"].lower() for t in d["grupos"]["atos_resposta"]["termos"]}
    for s in sinal:
        assert s.lower() in termos_resposta, f"sinalizador automático '{s}' não está listado em atos_resposta.termos"
    return d, todos_termos


def get_sinalizadores_resposta():
    """API pública: devolve a lista de sinalizadores automáticos de resposta, já validada."""
    d, _ = carregar()
    return d["grupos"]["atos_resposta"]["sinalizadores_automaticos"]["termos"]


def _contem_sinalizador(texto, sinalizadores):
    """Testa se algum sinalizador (ou variante) ocorre no texto, case-insensitive."""
    t = texto.lower()
    return any(v.lower() in t for s in sinalizadores for v in gerar_variantes(s))


def self_test():
    """Roda os três testes de correção: estrutura, precisão (regressão) e variantes."""
    d, todos_termos = carregar()
    sinal = get_sinalizadores_resposta()
    print(f"✓ estrutura: {sum(len(g['termos']) for g in d['grupos'].values())} termos em {len(d['grupos'])} grupos, "
          f"todos com origem registrada; {len(sinal)} sinalizadores automáticos")

    falhas = []
    for nome, texto in CASOS_NAO_DEVEM_DISPARAR.items():
        if _contem_sinalizador(texto, sinal):
            falhas.append(f"FALSO POSITIVO: '{nome}' disparou sinalizador de resposta indevidamente")
    for nome, texto in CASOS_DEVEM_DISPARAR.items():
        if not _contem_sinalizador(texto, sinal):
            falhas.append(f"FALSO NEGATIVO: '{nome}' deveria disparar sinalizador de resposta e não disparou")
    if falhas:
        for f in falhas:
            print("✗", f)
        raise AssertionError(f"{len(falhas)} caso(s) de regressão falharam — ver CASOS_* no topo do script")
    print(f"✓ precisão: {len(CASOS_NAO_DEVEM_DISPARAR)} caso(s) ex-ante não dispararam e "
          f"{len(CASOS_DEVEM_DISPARAR)} caso(s) de resposta dispararam (regressão sobre o erro real de AC/PE)")

    v = gerar_variantes("plano de contingência")
    assert "plano de contingencia" in v and "plano-de-contingência" in v, "gerar_variantes não cobre acento/hífen"
    print(f"✓ variantes: gerar_variantes cobre acento e hífen (ex.: {sorted(v)[:2]}…)")

    dup = {t: gs for t, gs in todos_termos.items() if len(set(gs)) > 1}
    if dup:
        print(f"⚠ termos presentes em mais de um grupo (pode ser intencional): {dup}")

    print("✓ TODOS OS TESTES PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
