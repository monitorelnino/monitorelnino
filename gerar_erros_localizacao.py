#!/usr/bin/env python3
"""Gera `data/erros_localizacao.json` — o registro de erros de LOCALIZAÇÃO da descoberta.

POR QUE ESTE ARQUIVO EXISTE (27/09/2026, §251)
==============================================
Decisão da editoria, pedido §I de 27/09 (repositório privado `robo-registro`): o Claude Code não
aprende entre sessões — só o que está em arquivo persiste. Cada correção aplicada apenas como
correção deixa o sistema tão cego quanto antes para o próximo caso. Este registro transforma
correção em REGRA, e a regra é medida: `achados_novos_pela_regra` é a medida de aprendizado e vai
ao relatório de cada rodada. Regra que roda duas semanas com zero achados novos é REVISTA, não
apagada.

PROIBIDO, e é o ponto do pedido: inserir à mão o documento de um caso para fechá-lo. Fechar o caso
sem que a descoberta o ache sozinha deixa o próximo Espírito Santo escapar igual. Sinal de
violação: fixture verde sem coletor novo no repositório.

POR QUE GERADOR E NÃO JSON À MÃO
================================
`data/**.json` é território de arquivo derivado neste projeto, e há hook que bloqueia edição
direta (`.claude/hooks/bloquear_derivados.py`). A regra é alterar a fonte e regenerar. A fonte é
este arquivo; o precedente é o dicionário `ESTADOS` de `recalcular_mare.py`, que o próprio
workflow chama de "a fonte de verdade real do cálculo". E é melhor assim: o registro precisa ser
regenerado a cada rodada, quando a contagem de achados por regra muda.

Uso:
    python3 gerar_erros_localizacao.py            # grava data/erros_localizacao.json
    python3 gerar_erros_localizacao.py --autoteste # prova os invariantes, sem rede
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
SAIDA = RAIZ / "data" / "erros_localizacao.json"

GOVERNANCA = (
    "Registro de erros de LOCALIZAÇÃO da descoberta automática. Criado em 27/09/2026 por decisão "
    "da editoria (pedido §I de 27/09, repositório privado). RAZÃO DE EXISTIR: o Claude Code não "
    "aprende entre sessões — só o que está em arquivo persiste. Cada correção aplicada apenas "
    "como correção deixa o sistema tão cego quanto antes para o próximo caso. Este arquivo "
    "transforma correção em regra, e a regra é medida: `achados_novos_pela_regra` é a medida de "
    "aprendizado, e vai ao relatório de cada rodada. Regra que roda duas semanas com zero achados "
    "novos é REVISTA, não apagada. PROIBIDO: inserir à mão o documento de um caso para fechá-lo. "
    "Fechar o caso sem que a descoberta o ache sozinha deixa o próximo Espírito Santo escapar "
    "igual. Sinal de violação: fixture verde sem coletor novo no repositório. Derivado de "
    "gerar_erros_localizacao.py — não se edita à mão."
)

CLASSES_DE_CAUSA = {
    "vocabulario":
        "O termo pelo qual o documento se chama não estava no dicionário de busca. Regra: buscar "
        "por RADICAL (calor, contingênc, adapta, sala de situação), não por frase exata.",
    "caminho":
        "O documento estava em caminho que a descoberta não enumera (/media/, /uploads/AAAA/, "
        "seção de navegação). Regra: enumerar wp-json media, /media/, /uploads/AAAA/ e as seções "
        "planos · publicações · vigilância · biblioteca · documentos.",
    "canal_oficial_nao_coberto":
        "A evidência estava em agência oficial de notícias do governo estadual, que é comunicação "
        "oficial e não imprensa. Regra: adaptador próprio para as 27 agências, sustentando ELAB e "
        "a classe 'declarado, não documentado'. Nunca pontua sozinha.",
    "regra_de_reavaliacao":
        "A reavaliação de sítio suspenso decidiu por evidência truncada. Regra: <title>, <h1> e "
        "meta refresh de página de aviso são texto declarativo; evidência truncada nunca decide; "
        "recoletar antes de reclassificar.",
    "nomenclatura_nova_do_ciclo":
        "O ciclo criou nome novo para o instrumento. Regra: manter a classe no dicionário para os "
        "próximos.",
}

# Premissa do pedido que a medição desmentiu. Fica registrada porque premissa errada em pedido é
# erro de localização como qualquer outro — e o §249 do mesmo dia mostrou o custo de repetir a
# afirmação de um documento sem medir.
CORRECAO_DE_PREMISSA = {
    "data": "2026-09-27",
    "o_que_o_pedido_afirmava":
        "Causa 2 (caminho): 'construir descobrir_planos.py (§11 de 06/09, NUNCA IMPLEMENTADO)'.",
    "o_que_a_medicao_mostrou":
        "descobrir_planos.py EXISTE (26.468 bytes) e já consulta wp-json/wp/v2/posts e "
        "wp/v2/media?mime_type=application/pdf, com --uf e --setor. Não é construir, é consertar.",
    "a_causa_real_medida":
        "TERMOS_BUSCA['saude'] tem três termos, e descobrir_planos.py:194 usa "
        "`TERMOS_BUSCA[setor][:2]` — SÓ OS DOIS PRIMEIROS. O terceiro ('plano de contingência "
        "arboviroses') já é código morto hoje. Acrescentar os termos do bloco D ao fim da lista "
        "não mudaria nada, e o relatório diria 'dicionário ampliado' com o coletor sem usar um "
        "único termo novo.",
    "por_que_isto_esta_registrado":
        "Seguir o pedido à letra produziria exatamente a falsa implementação que este registro "
        "existe para impedir.",
}

CASOS = [
    {
        "id": "EL-2026-09-27-01",
        "data": "2026-09-27",
        "uf": "ES",
        "setor": "saude",
        "o_que_era": "Plano de Contingência para Calor Extremo, SESA/ES, 2026",
        "onde_estava": "https://saude.es.gov.br/media/plano-de-contingencia-calor-extremo-sesa-2026-2.pdf",
        "como_foi_achado": "busca web dirigida + leitura direta do sítio (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["vocabulario", "caminho"],
        "regra_derivada":
            "Buscar por radical 'calor' e 'contingênc' no wp-json media do domínio de saúde, e "
            "enumerar /media/*.pdf quando a seção de planos não linka o arquivo. A causa operativa "
            "medida é ANTERIOR a isso: o laço usa só os dois primeiros termos de TERMOS_BUSCA, "
            "então nenhum termo novo entra em uso sem consertar o corte.",
        "fixture": "https://saude.es.gov.br/media/plano-de-contingencia-calor-extremo-sesa-2026-2.pdf",
        "tipo_de_fixture": "descoberta",
        "mecanismo_esperado": "descobrir_planos.py --uf ES --setor saude",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
    {
        "id": "EL-2026-09-27-02",
        "data": "2026-09-27",
        "uf": "PA",
        "setor": "saude",
        "o_que_era": "Plano AdaptaSUS-UF do Pará (processo 2026/2294762, jun/2026)",
        "onde_estava": "http://www.saude.pa.gov.br/wp-content/uploads/2026/06/PLANO-ADAPTASUS-1.pdf",
        "como_foi_achado": "busca web dirigida (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["vocabulario", "caminho"],
        "regra_derivada":
            "Radical 'adapta' no dicionário de saúde, com camada `adaptacao` (não pontua, §31 "
            "v0.2). Enumerar wp-content/uploads/AAAA/MM/.",
        "fixture": "http://www.saude.pa.gov.br/wp-content/uploads/2026/06/PLANO-ADAPTASUS-1.pdf",
        "tipo_de_fixture": "descoberta",
        "mecanismo_esperado": "descobrir_planos.py --uf PA --setor saude",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
    {
        "id": "EL-2026-09-27-03",
        "data": "2026-09-27",
        "uf": "MA",
        "setor": "saude",
        "o_que_era":
            "Página 'Planos da VE' da SES-MA e o Plano de Contingência do Setor Saúde para "
            "Desastres Naturais no Maranhão",
        "onde_estava": "https://www.saude.ma.gov.br/planos-da-ve/",
        "como_foi_achado": "leitura direta do sítio (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["caminho", "vocabulario"],
        "regra_derivada":
            "Varrer as seções de navegação chamadas planos · publicações · vigilância · "
            "biblioteca · documentos, e listar os PDFs que elas linkam. Radical 'contingênc' e "
            "'desastre' no dicionário.",
        "fixture": "https://www.saude.ma.gov.br/planos-da-ve/",
        "tipo_de_fixture": "descoberta",
        "mecanismo_esperado":
            "descobrir_planos.py --uf MA --setor saude (varredura de seção de navegação, ainda "
            "não construída)",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
    {
        "id": "EL-2026-09-27-04",
        "data": "2026-09-27",
        "uf": "AC",
        "setor": "saude",
        "o_que_era":
            "Oficina Sesacre + OPAS + MS, 10–12/06/2026, para elaboração conjunta de plano de "
            "contingência para eventos de calor extremo",
        "onde_estava":
            "https://agencia.ac.gov.br/acre-fortalece-estrategias-de-saude-publica-para-"
            "enfrentamento-de-eventos-de-calor-extremo/",
        "como_foi_achado":
            "busca web dirigida em agência oficial de notícias (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["canal_oficial_nao_coberto"],
        "regra_derivada":
            "Agência oficial de notícias de governo estadual é comunicação OFICIAL, não imprensa. "
            "Adaptador próprio com a lista das 27, sustentando status ELAB e a classe 'declarado, "
            "não documentado'. Nunca pontua sozinha.",
        "fixture":
            "https://agencia.ac.gov.br/acre-fortalece-estrategias-de-saude-publica-para-"
            "enfrentamento-de-eventos-de-calor-extremo/",
        "tipo_de_fixture": "descoberta",
        "mecanismo_esperado": "adaptador de agências oficiais estaduais (não construído)",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
    {
        "id": "EL-2026-09-27-05",
        "data": "2026-09-27",
        "uf": "MT",
        "setor": "saude",
        "o_que_era":
            "Sala de Situação em Saúde para o El Niño 2026-2027, SES-MT, e 40 municípios "
            "prioritários (13/08/2026)",
        "onde_estava": None,
        "lacuna_declarada":
            "O pedido §I nomeia esta fixture como 'MT notícia da Sala de Situação (pista oficial)' "
            "SEM URL, e o bloco B a credita a 'fonte SES-MT via imprensa'. Não há endereço para "
            "testar, e endereço não se inventa. O caso fica ABERTO até a editoria fornecer a URL, "
            "ou até o adaptador de agências / o monitor de imprensa de saúde localizá-la por conta "
            "própria — e nesse segundo caso a URL achada passa a ser a fixture.",
        "como_foi_achado": "SES-MT via imprensa (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["canal_oficial_nao_coberto", "vocabulario"],
        "regra_derivada":
            "Radical 'sala de situação' no dicionário de saúde; adaptador de agências oficiais "
            "estaduais; monitor de imprensa de saúde (pedido de 18/09, não construído). Ato a "
            "localizar no DOE-MT por 'Sala de Situação em Saúde'.",
        "fixture": None,
        "tipo_de_fixture": "descoberta",
        "mecanismo_esperado":
            "adaptador de agências oficiais + monitor de imprensa de saúde (nenhum construído)",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
    {
        "id": "EL-2026-09-27-06",
        "data": "2026-09-27",
        "uf": "SE",
        "setor": "defesa_civil",
        "o_que_era":
            "Sítio da Defesa Civil de Sergipe classificado como suspenso quando está no ar; só a "
            "aba de notícias está desativada pelo defeso",
        "onde_estava": "https://defesacivil.se.gov.br/",
        "como_foi_achado": "leitura direta do sítio (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["regra_de_reavaliacao"],
        "regra_derivada":
            "<title>, <h1> e meta refresh de página de aviso são texto DECLARATIVO, não prova de "
            "indisponibilidade do sítio. Evidência truncada nunca decide. Recoletar antes de "
            "reclassificar. O escopo da suspensão é campo próprio: `noticias` não é `sitio`.",
        "fixture": "https://defesacivil.se.gov.br/",
        "tipo_de_fixture": "reavaliacao",
        "esperado": {"suspensa": False, "escopo": "noticias"},
        "estado_medido_em_27_09": {"suspensa": True, "escopo": None},
        "mecanismo_esperado":
            "regra de reavaliação de fontes suspensas (a corrigir) + campo `escopo`, que hoje não "
            "existe em nenhum dos 38 registros de data/calendario/fontes_suspensas.json",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
    {
        "id": "EL-2026-09-27-07",
        "data": "2026-09-27",
        "uf": "TO",
        "setor": "defesa_civil",
        "o_que_era":
            "Executivo estadual do Tocantins inteiro fora do ar desde 04/07/2026, e o sítio da "
            "Defesa Civil estava classificado como NÃO suspenso",
        "onde_estava": "https://defesacivil.to.gov.br/",
        "como_foi_achado":
            "leitura direta + Diário do Tocantins 07/07/2026 (Claude do chat, 27/09/2026)",
        "classe_de_causa": ["regra_de_reavaliacao"],
        "regra_derivada":
            "A mesma regra, no sentido inverso: título 'Aviso de Suspensão' mais meta refresh é "
            "declaração de indisponibilidade e vale para o escopo declarado — aqui "
            "`governo_estadual`, não só um sítio.",
        "fixture": "https://defesacivil.to.gov.br/",
        "tipo_de_fixture": "reavaliacao",
        "esperado": {"suspensa": True, "escopo": "governo_estadual"},
        "estado_medido_em_27_09": {"suspensa": False, "escopo": None},
        "mecanismo_esperado": "regra de reavaliação de fontes suspensas (a corrigir) + campo `escopo`",
        "regra_implementada": "nao",
        "generalizada_em": None,
        "achados_novos_pela_regra": None,
    },
]


def montar() -> dict:
    """O registro inteiro, pronto para gravar."""
    return {
        "_governanca": GOVERNANCA,
        "criado_em": "2026-09-27",
        "fonte_do_pedido":
            "notas/PEDIDO_claude_code_incorporar_verificacoes_27-09-2026.md "
            "(repositório privado robo-registro)",
        "classes_de_causa": CLASSES_DE_CAUSA,
        "correcao_de_premissa_do_pedido": CORRECAO_DE_PREMISSA,
        "casos": CASOS,
    }


def autoteste() -> int:
    """Invariantes do registro, sem rede."""
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    r = montar()
    casos = r["casos"]

    checar("sete casos, um por achado de 27/09", len(casos) == 7)
    checar("nenhum id repetido", len({c["id"] for c in casos}) == 7)

    obrigatorios = ("id", "data", "uf", "setor", "o_que_era", "onde_estava", "como_foi_achado",
                    "classe_de_causa", "regra_derivada", "fixture", "regra_implementada",
                    "generalizada_em", "achados_novos_pela_regra")
    checar("todo caso tem os campos do §I",
           all(all(k in c for k in obrigatorios) for c in casos))

    checar("toda classe_de_causa citada existe no dicionário de classes",
           all(cl in r["classes_de_causa"] for c in casos for cl in c["classe_de_causa"]))

    # A trava do pedido: nenhum caso pode nascer fechado. Fixture verde sem coletor novo é o
    # sinal de violação, e `regra_implementada` começa em "nao" para todos.
    checar("nenhum caso nasce com regra implementada",
           all(c["regra_implementada"] == "nao" for c in casos))
    checar("nenhum caso nasce generalizado",
           all(c["generalizada_em"] is None for c in casos))

    # Caso sem fixture tem de declarar a lacuna, nunca inventar URL.
    sem_fixture = [c for c in casos if not c["fixture"]]
    checar("caso sem fixture declara a lacuna em vez de inventar URL",
           all(c.get("lacuna_declarada") for c in sem_fixture))
    checar("exatamente um caso sem fixture, o do MT",
           [c["uf"] for c in sem_fixture] == ["MT"])

    # Fixture de reavaliação precisa dizer o esperado E o medido, senão não é teste.
    reav = [c for c in casos if c.get("tipo_de_fixture") == "reavaliacao"]
    checar("fixture de reavaliação declara esperado e medido",
           all(c.get("esperado") and "estado_medido_em_27_09" in c for c in reav))
    checar("o esperado difere do medido nas duas de reavaliação — senão não haveria erro",
           all(c["esperado"] != c["estado_medido_em_27_09"] for c in reav))

    checar("a premissa desmentida do pedido está registrada",
           "NUNCA IMPLEMENTADO" in r["correcao_de_premissa_do_pedido"]["o_que_o_pedido_afirmava"])

    if falhas:
        print(f"\n✗ REGISTRO DE ERROS: {len(falhas)} falha(s).")
        return 1
    print("\n✓ REGISTRO DE ERROS OK — sete casos, nenhum nasce fechado, lacuna declarada.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(montar(), ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8", newline="\n")
    print(f"→ {SAIDA.relative_to(RAIZ)} gravado ({len(CASOS)} caso(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
