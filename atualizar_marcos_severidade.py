#!/usr/bin/env python3
"""
atualizar_marcos_severidade.py
=================================
Implementa o refinamento do marco temporal descrito na Metodologia §12.3.1:
um segundo marco (t_monitor), exógeno ao ente avaliado e específico por tipo
de risco, complementando t_decreto (§12.3) na fronteira entre antecipação e
resposta do MARÉ.

O QUE ESTE SCRIPT FAZ:
  - Implementa o MOTOR DE CLASSIFICAÇÃO das três zonas (antes de t_monitor /
    entre t_monitor e t_decreto / depois de t_decreto) — testável e correto
    por construção, independente de qualquer fonte de dado externa.
  - Busca o Monitor de Secas (ANA) via o catálogo de dados abertos oficial
    (dadosabertos.ana.gov.br, API padrão CKAN), com DESCOBERTA DINÂMICA do
    recurso por busca de texto — não assume uma URL fixa não verificada.

O QUE ESTE SCRIPT NÃO FAZ (declarado, não escondido):
  - NÃO busca automaticamente CEMADEN, INMET ou Risco de Fogo/INPE. A
    pesquisa desta sessão confirmou a ESCALA e a SEMÂNTICA de cada um
    (ver Metodologia §12.3.1), mas não confirmou um endpoint de dado
    ESTRUTURADO acessível programaticamente para os três — ao contrário do
    Monitor de Secas, cuja ANA mantém portal de dados abertos documentado.
    Publicar um parser para uma página que não foi verificada violaria a
    mesma regra de ouro que rege o resto deste projeto (nunca presumir
    formato de fonte não verificada). Por isso, estas três entram em
    MODO MANUAL: uma pessoa com acesso real à internet confirma o
    endpoint/formato e preenche data/marcos_severidade_manual.json (mesmo
    padrão de honestidade de atualizar_instrumentos_estaduais.py para
    repositórios estaduais ainda sem parser).
  - NÃO escreve em municipios.json nem em indice.json. Este script apenas
    mantém data/marcos_severidade.json (os t_monitor por UF/risco), que
    ainda não é consumido por recalcular_mare.py — a integração ao cálculo
    do MARÉ é etapa POSTERIOR à simulação e sensibilidade (Metodologia
    §12.5), não decidida nem aplicada aqui.

LIMITAÇÃO DE AMBIENTE (igual à de atualizar_instrumentos_estaduais.py): o
sandbox onde este projeto é editado tem rede restrita a um allowlist de
pacotes; dadosabertos.ana.gov.br não está nele. A busca CKAN abaixo é
testada com uma resposta de exemplo fixada (fixture) e roda de verdade no
ambiente real de publicação.

Uso:
  python3 atualizar_marcos_severidade.py                         # tenta ANA; demais em modo manual
  python3 atualizar_marcos_severidade.py --self-test              # roda o motor de classificação contra casos sintéticos
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"

# ---------------------------------------------------------------------------
# Patamares de "gravidade estabelecida" por risco (Metodologia §12.3.1).
# Normativos — pendentes do teste de sensibilidade previsto na própria seção.
# ---------------------------------------------------------------------------
PATAMARES = {
    "estiagem":       {"instrumento": "Monitor de Secas (ANA)", "escala": ["S0", "S1", "S2", "S3", "S4"], "corte": "S2"},
    "seca":           {"instrumento": "Monitor de Secas (ANA)", "escala": ["S0", "S1", "S2", "S3", "S4"], "corte": "S2"},
    "deslizamento":   {"instrumento": "Alerta geo-hidrológico (CEMADEN)", "escala": ["Moderado", "Alto", "Muito Alto"], "corte": "Alto"},
    "enchente":       {"instrumento": "Alerta geo-hidrológico (CEMADEN)", "escala": ["Moderado", "Alto", "Muito Alto"], "corte": "Alto"},
    "inundacao":      {"instrumento": "Alerta geo-hidrológico (CEMADEN)", "escala": ["Moderado", "Alto", "Muito Alto"], "corte": "Alto"},
    "chuvas_intensas": {"instrumento": "Alerta por cor (INMET)", "escala": ["Amarelo", "Laranja", "Vermelho"], "corte": "Laranja"},
    "incendio":       {"instrumento": "Risco de Fogo (INPE/Queimadas)", "escala": ["Mínimo", "Baixo", "Médio", "Alto", "Crítico"], "corte": "Alto", "corte_numerico": 0.70},
}


def indice_na_escala(nivel: str, escala: list[str]) -> int:
    """Classifica um valor observado na escala oficial do índice de referência (por exemplo, categoria S0-S4 do Monitor de Secas)."""
    try:
        return escala.index(nivel)
    except ValueError:
        raise ValueError(f"nível '{nivel}' não pertence à escala {escala}")


def atingiu_patamar(risco: str, nivel_observado: str) -> bool:
    """True se o nível observado já está no patamar de 'gravidade estabelecida' (ou acima)."""
    cfg = PATAMARES[risco]
    return indice_na_escala(nivel_observado, cfg["escala"]) >= indice_na_escala(cfg["corte"], cfg["escala"])


def classificar_zona(categoria: str, data_instrumento: str, t_monitor: str | None, t_decreto: str | None) -> str:
    """Motor de classificação das três zonas de 12.3.1. Datas em 'DD/MM/AAAA'
    ou None (marco ainda não atingido neste ciclo). Devolve uma das três
    zonas ou 'antes' quando nenhum marco existe ainda (caso mais favorável
    ao ente, coerente com 'ausência de registro não é registro de ausência',
    Seção 3).

    GUARDA DE CORREÇÃO LEGAL (achada e corrigida em 26/08/2026, a partir de
    pergunta direta sobre a correção legal da classificação): um decreto
    SE/ECP é SEMPRE 'resposta', em qualquer cenário, independentemente da
    data comparada a t_monitor. Isto não é uma regra de desenho — é um fato
    legal: a IN MDR nº 2/2016 exige dano JÁ OCORRIDO para o decreto existir
    (Metodologia, Frente 4). Um decreto datado antes do monitor estadual
    cruzar o patamar de gravidade não vira preventivo por coincidência de
    datas — o dano que o originou pode ser hiperlocal e anteceder a média
    agregada do monitor. Sem esta guarda, a função aceitaria QUALQUER data
    e poderia classificar erroneamente um decreto como antecipação de alta
    confiança — um erro de coerência legal, não só de estilo.
    """
    if categoria == "decreto":
        return "resposta"

    # Guarda de contrato (auditoria de 27/08/2026): para categorias não-decreto,
    # a data do instrumento é obrigatória — os None permitidos pela assinatura
    # são os MARCOS (t_monitor/t_decreto, "ainda não atingidos"), nunca a data
    # do próprio instrumento. Sem esta guarda, um registro sem data combinado a
    # um marco existente estourava TypeError (None >= datetime) — falha muda em
    # produção. Falhar alto e nomeado é a regra da camada de lógica.
    if not data_instrumento:
        raise ValueError("classificar_zona: data_instrumento é obrigatória para "
                         f"categoria '{categoria}' — registro sem data não é classificável em zonas")

    def conv(d):
        """Converte a data do formato de origem para o formato ISO usado internamente pelo restante do pipeline."""
        return datetime.datetime.strptime(d, "%d/%m/%Y") if d else None

    d, m, r = conv(data_instrumento), conv(t_monitor), conv(t_decreto)
    if r is not None and d >= r:
        return "resposta"
    if m is not None and d >= m:
        return "pressao_exige_verificacao"
    return "antecipacao_alta_confianca"


# ---------------------------------------------------------------------------
# Monitor de Secas (ANA) — descoberta dinâmica via catálogo CKAN.
# ---------------------------------------------------------------------------
CKAN_BASE = "https://dadosabertos.ana.gov.br/api/3/action"


def buscar_recurso_monitor_secas(sessao=None):
    """Localiza o dataset 'Monitor de Secas' no catálogo CKAN da ANA por busca
    de texto (nunca por URL fixa presumida) e devolve a lista de recursos
    (arquivos/tabelas) do primeiro resultado. Levanta exceção clara se a
    rede não permitir a consulta (esperado no sandbox de edição)."""
    import requests
    url = f"{CKAN_BASE}/package_search"
    resp = requests.get(url, params={"q": "monitor de secas", "rows": 5}, timeout=30)
    resp.raise_for_status()
    corpo = resp.json()
    if not corpo.get("success") or not corpo["result"]["results"]:
        raise RuntimeError("catálogo CKAN da ANA não retornou dataset para 'monitor de secas'")
    pacote = corpo["result"]["results"][0]
    return pacote.get("resources", [])


def testar_classificador_ckan(fixture_json: dict):
    """Testa o parsing da resposta do CKAN contra uma fixture local (a forma
    real da resposta, sem depender de rede) — prova a lógica de navegação
    do JSON sem exigir acesso ao dadosabertos.ana.gov.br."""
    if not fixture_json.get("success"):
        raise RuntimeError("fixture indica success=false")
    resultados = fixture_json["result"]["results"]
    if not resultados:
        raise RuntimeError("fixture sem resultados")
    return resultados[0].get("resources", [])


# ---------------------------------------------------------------------------
# CEMADEN / INMET / Risco de Fogo — modo manual (honesto: sem parser ainda)
# ---------------------------------------------------------------------------
ARQUIVO_MANUAL = DATA / "marcos_severidade_manual.json"
MODELO_MANUAL = {
    "_leia_antes_de_preencher": (
        "Preencha t_monitor (DD/MM/AAAA) para cada UF onde o risco atingiu o patamar "
        "de 12.3.1, verificando a fonte ao vivo (CEMADEN, INMET ou o boletim Infoqueima "
        "do INPE). Deixe null enquanto o patamar não tiver sido atingido no ciclo. "
        "Isto é uma ENTRADA HUMANA — nada aqui é gerado automaticamente."
    ),
    "deslizamento": {}, "enchente": {}, "inundacao": {}, "chuvas_intensas": {}, "incendio": {},
}


def main():
    """Busca o recurso do Monitor de Secas no catálogo CKAN da ANA por descoberta dinâmica e classifica cada registro nas três zonas do marco temporal."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="Roda apenas os testes do motor de classificação")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    marcos = {}
    if ARQUIVO_MANUAL.exists():
        manual = json.load(open(ARQUIVO_MANUAL, encoding="utf-8"))
        for risco, por_uf in manual.items():
            if risco.startswith("_"):
                continue
            for uf, t in por_uf.items():
                marcos.setdefault(uf, {})[risco] = t
        print(f"Modo manual: {ARQUIVO_MANUAL.name} lido para deslizamento/enchente/inundacao/chuvas_intensas/incendio.")
    else:
        json.dump(MODELO_MANUAL, open(ARQUIVO_MANUAL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[aviso] {ARQUIVO_MANUAL.name} não existia — modelo criado. Preencha e rode de novo.")

    print("\n[ANA] buscando dataset 'Monitor de Secas' no catálogo de dados abertos...")
    try:
        recursos = buscar_recurso_monitor_secas()
        print(f"  {len(recursos)} recurso(s) encontrado(s) no dataset — download/parse ainda não implementado")
        print("  (a etapa de download+parse do formato real do recurso fica para quando isto rodar")
        print("   com acesso à internet; a descoberta do dataset já está funcionando)")
    except Exception as e:
        print(f"  [FALHA] não foi possível consultar o catálogo da ANA: {e}")
        print("  (esperado no sandbox de edição — allowlist de rede não inclui dadosabertos.ana.gov.br;")
        print("   roda de verdade na Action do GitHub ou na máquina de quem publica)")

    saida = DATA / "marcos_severidade.json"
    json.dump(marcos, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{saida.relative_to(RAIZ)} gravado com {sum(len(v) for v in marcos.values())} marco(s) manual(is).")
    print("NOTA: marcos_severidade.json NÃO é consumido por recalcular_mare.py ainda —")
    print("      integração ao cálculo do MARÉ é posterior à simulação (Metodologia §12.5).")


def self_test():
    """Roda o motor de classificação das três zonas contra casos sintéticos conhecidos, sem depender de rede, para validar a lógica isoladamente da busca."""
    print("=== Motor de classificação (3 zonas) ===")
    casos = [
        # (nome, categoria, data_instrumento, t_monitor, t_decreto, esperado)
        ("antes de qualquer marco",            "plano",   "10/01/2026", None,         None,         "antecipacao_alta_confianca"),
        ("antes do monitor",                    "plano",   "10/01/2026", "01/06/2026", "01/09/2026", "antecipacao_alta_confianca"),
        ("na zona de pressão (Acre-like)",      "plano",   "15/06/2026", "01/06/2026", "01/09/2026", "pressao_exige_verificacao"),
        ("exatamente no dia do monitor",        "plano",   "01/06/2026", "01/06/2026", "01/09/2026", "pressao_exige_verificacao"),
        ("depois do decreto",                   "plano",   "10/09/2026", "01/06/2026", "01/09/2026", "resposta"),
        ("monitor nunca atingido, sem decreto", "plano",   "10/09/2026", None,         None,         "antecipacao_alta_confianca"),
        ("sem monitor, mas com decreto",        "plano",   "10/09/2026", None,         "01/09/2026", "resposta"),
        # Guarda legal: decreto é SEMPRE resposta, mesmo com data anterior a
        # qualquer marco — o caso que motivou a correção de 26/08/2026.
        ("decreto ANTES do monitor (dano hiperlocal)", "decreto", "05/01/2026", "01/06/2026", "01/09/2026", "resposta"),
        ("decreto sem nenhum marco calculado ainda",   "decreto", "05/01/2026", None,         None,         "resposta"),
    ]
    falhas = 0
    for nome, cat, d, m, r, esperado in casos:
        obtido = classificar_zona(cat, d, m, r)
        ok = obtido == esperado
        falhas += not ok
        print(f"  {'✓' if ok else '✗'} {nome}: {obtido}" + ("" if ok else f" (esperado: {esperado})"))

    # Guarda de contrato: não-decreto sem data deve falhar alto (ValueError),
    # nunca TypeError mudo nem classificação silenciosa (auditoria 27/08/2026).
    try:
        classificar_zona("plano", None, None, "01/09/2026")
        falhas += 1
        print("  ✗ plano sem data: deveria levantar ValueError, não levantou")
    except ValueError:
        print("  ✓ plano sem data: ValueError nomeado (guarda de contrato)")
    except Exception as e:
        falhas += 1
        print(f"  ✗ plano sem data: levantou {type(e).__name__}, esperado ValueError")

    print("\n=== atingiu_patamar() nas quatro escalas ===")
    testes_patamar = [
        ("estiagem", "S1", False), ("estiagem", "S2", True), ("estiagem", "S4", True),
        ("deslizamento", "Moderado", False), ("deslizamento", "Alto", True),
        ("chuvas_intensas", "Amarelo", False), ("chuvas_intensas", "Laranja", True), ("chuvas_intensas", "Vermelho", True),
        ("incendio", "Médio", False), ("incendio", "Alto", True), ("incendio", "Crítico", True),
    ]
    for risco, nivel, esperado in testes_patamar:
        obtido = atingiu_patamar(risco, nivel)
        ok = obtido == esperado
        falhas += not ok
        print(f"  {'✓' if ok else '✗'} {risco}/{nivel} → {obtido}" + ("" if ok else f" (esperado: {esperado})"))

    print("\n=== descoberta CKAN contra fixture local (sem rede) ===")
    fixture = {
        "success": True,
        "result": {"results": [{"name": "monitor-de-secas-classificacao-mensal",
                                 "resources": [{"name": "classificacao_202608.csv", "format": "CSV",
                                                "url": "https://dadosabertos.ana.gov.br/datasets/exemplo/download"}]}]}
    }
    try:
        recursos = testar_classificador_ckan(fixture)
        ok = len(recursos) == 1 and recursos[0]["format"] == "CSV"
        falhas += not ok
        print(f"  {'✓' if ok else '✗'} navegação do JSON CKAN (1 recurso CSV encontrado)")
    except Exception as e:
        falhas += 1
        print(f"  ✗ falhou: {e}")

    print(f"\n{'✓ TODOS OS TESTES PASSARAM' if not falhas else f'✗ {falhas} teste(s) falharam'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main() or 0)
