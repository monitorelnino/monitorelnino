#!/usr/bin/env python3
"""Autoteste do leitor da página de consulta do DOU (§209, 24/09/2026), sem rede.

POR QUE ESTE ARQUIVO EXISTE. O DOU trocou o transporte do resultado da busca: ele vinha num
`<input ... value="{json}">` e passou a vir num `<script type="application/json">`. Dois
coletores tinham, cada um, a cópia do regex do `<input>` e passaram a devolver **lista vazia**
para toda consulta, calados. A guarda que existia testava `"jsonArray" in texto` — e essa
string continua na página, no script e no JS ao lado —, de modo que a guarda passava e o zero
virava "consultamos e não há". Medido em 24/09: a consulta de reconhecimentos tinha 132
resultados reais no ciclo e o coletor lia 0.

O que estes testes travam é a lição, não o regex: **ausência de estrutura levanta**, nunca
devolve zero; o trecho devolvido pela busca é excerto e não serve de prova; e uma janela que
a página não entrega inteira volta declarada, porque recorte não se apresenta como varredura.
"""
import json
import pathlib
import sys
from datetime import date

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import (parse_busca_dou, total_declarado_dou, varrer_busca_dou,  # noqa: E402
                            FormatoDoDOUMudou, rodar_autoteste)

ID = "_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"


def pagina(itens, total=None, forma="script"):
    """Monta uma página de consulta como o DOU a serve — nas duas formas conhecidas."""
    corpo = json.dumps({"jsonArray": itens})
    if forma == "script":
        html = f'<script id="{ID}" type="application/json">{corpo}</script>'
    else:
        import html as _h
        html = f'<input id="{ID}" type="hidden" value="{_h.escape(corpo, quote=True)}">'
    if total is not None:
        html += f"<p>{total} resultados</p>"
    return html


ITEM = {"title": "<span class='highlight'>PORTARIA</span> Nº 3.175, DE 23 DE SETEMBRO DE 2026",
        "urlTitle": "portaria-n-3.175-de-23-de-setembro-de-2026-733736080", "pubDate": "24/09/2026",
        "content": "resolve: Art. 1º Reconhecer ... a situação de emergência nas áreas descritas no",
        "hierarchyStr": "Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil"}


def t_le_a_forma_de_hoje():
    r = parse_busca_dou(pagina([ITEM]))
    return (len(r) == 1 and r[0]["titulo"] == "PORTARIA Nº 3.175, DE 23 DE SETEMBRO DE 2026"
            and r[0]["url"].endswith("733736080") and r[0]["data"] == "24/09/2026")


def t_le_a_forma_antiga():
    """A evidência preservada até 23/09/2026 está na forma antiga; o leitor tem de continuar
    lendo o que já guardamos, senão a reauditoria de um dia antigo daria vazio."""
    return len(parse_busca_dou(pagina([ITEM], forma="input"))) == 1


def t_sem_estrutura_levanta():
    """O defeito de 24/09 em uma linha: página que responde e não traz resultados NÃO é
    consulta bem-sucedida. Devolver [] aqui é o que transformou 132 atos em 'não há'."""
    for p in ("<html>nada</html>", "", "<p>jsonArray aparece no texto e não é resultado</p>"):
        try:
            parse_busca_dou(p)
            return False
        except FormatoDoDOUMudou:
            pass
    return True


def t_estrutura_ilegivel_levanta():
    return _levanta(f'<script id="{ID}" type="application/json">{{isso não é json</script>')


def t_estrutura_sem_a_chave_levanta():
    return _levanta(f'<script id="{ID}" type="application/json">{{"outraCoisa":[]}}</script>')


def _levanta(p):
    try:
        parse_busca_dou(p)
        return False
    except FormatoDoDOUMudou:
        return True


def t_lista_vazia_com_estrutura_e_resultado():
    """Com a estrutura presente e o array vazio, zero É resposta: procuramos e não há."""
    return parse_busca_dou(pagina([], total=0)) == []


def t_total_declarado():
    return (total_declarado_dou("<p>132 resultados</p>") == 132
            and total_declarado_dou("<p>1.132 resultados</p>") == 1132
            and total_declarado_dou("<p>1 resultado</p>") == 1
            and total_declarado_dou("<p>sem contagem</p>") is None)


def t_janela_cabe_nao_estreita():
    """Total declarado igual ao lido: uma consulta só, sem partir a janela."""
    chamadas = []

    def falsa(u):
        chamadas.append(u)
        return pagina([ITEM], total=1).encode()

    itens, faltando = varrer_busca_dou("x", date(2026, 6, 29), date(2026, 9, 24), buscar_fn=falsa, _relogio=lambda _: None)
    return len(chamadas) == 1 and len(itens) == 1 and faltando == []


def t_janela_nao_cabe_e_estreitada():
    """Total maior que o entregue: a janela é partida, e o resultado é a união sem repetição.
    O DOU não pagina (`start` é ignorado, medido em 24/09) — estreitar é o único caminho."""
    chamadas = []

    def falsa(u):
        chamadas.append(u)
        if len(chamadas) == 1:
            return pagina([ITEM], total=2).encode()          # 1 entregue, 2 declarados
        outro = {**ITEM, "urlTitle": f"ato-{len(chamadas)}"}
        return pagina([ITEM, outro], total=2).encode()        # metades cabem

    itens, faltando = varrer_busca_dou("x", date(2026, 8, 1), date(2026, 8, 31), buscar_fn=falsa, _relogio=lambda _: None)
    urls = [i["url"] for i in itens]
    return (len(chamadas) == 3 and faltando == []
            and len(urls) == len(set(urls)) and len(urls) == 3)


def t_dia_unico_que_nao_cabe_volta_declarado():
    """Um dia só que ainda estoura a página não pode ser apresentado como varredura: volta
    em `janelas_incompletas` para o coletor declarar a leitura parcial."""
    def falsa(u):
        return pagina([ITEM], total=61).encode()

    itens, faltando = varrer_busca_dou("x", date(2026, 8, 3), date(2026, 8, 3), buscar_fn=falsa, _relogio=lambda _: None)
    return (len(faltando) == 1 and faltando[0]["total"] == 61 and faltando[0]["lidos"] == 1
            and faltando[0]["de"] == "2026-08-03")


def t_data_vai_em_dia_mes_ano():
    """Medido em 24/09: com aaaa-mm-dd a página responde 200 e devolve OUTRA janela (3
    resultados no lugar de 132). Formato errado aqui não dá erro — dá número menor."""
    vistas = []

    def falsa(u):
        vistas.append(u)
        return pagina([], total=0).encode()

    varrer_busca_dou("x", date(2026, 6, 29), date(2026, 9, 24), buscar_fn=falsa, _relogio=lambda _: None)
    return "publishFrom=29-06-2026" in vistas[0] and "publishTo=24-09-2026" in vistas[0]


def t_ritmo_de_dois_segundos_entre_consultas():
    """§11: uma requisição a cada 2 s por domínio. Estreitar a janela multiplica as chamadas ao
    MESMO host — quem varre vai mais devagar, não mais rápido. A primeira não espera."""
    esperas, chamadas = [], []

    def falsa(u):
        chamadas.append(u)
        return pagina([ITEM], total=(2 if len(chamadas) == 1 else 1)).encode()

    varrer_busca_dou("x", date(2026, 8, 1), date(2026, 8, 31), buscar_fn=falsa,
                     _relogio=esperas.append)
    return len(chamadas) == 3 and esperas == [2.0, 2.0]


def t_pagina_cheia_sem_total_declarado_nao_passa_por_completa():
    """A contagem pode mudar de forma. Página cheia (50) sem total declarado não pode ser lida
    como 'é tudo' — trata-se como janela que não coube."""
    chamadas = []

    def falsa(u):
        chamadas.append(u)
        return pagina([{**ITEM, "urlTitle": f"a{i}"} for i in range(50)]).encode()   # sem total

    itens, faltando = varrer_busca_dou("x", date(2026, 8, 3), date(2026, 8, 3), buscar_fn=falsa,
                                       _relogio=lambda _: None)
    return len(chamadas) == 1 and len(faltando) == 1


def t_orgao_vem_da_fonte():
    """O órgão é o que a busca declara, não o que o título sugere: é por ele que um coletor
    decide quais atos vale a pena abrir, sem adivinhar."""
    r = parse_busca_dou(pagina([ITEM]))[0]
    return r["orgao"].endswith("Secretaria Nacional de Proteção e Defesa Civil")


def t_trecho_vem_sem_marcacao_e_nao_e_o_ato():
    """O termo vem embrulhado em <span class='highlight'>; e o trecho é excerto, não prova."""
    r = parse_busca_dou(pagina([ITEM]))[0]
    return "<span" not in r["trecho"] and "highlight" not in r["titulo"] and r["trecho"].startswith("resolve:")


if __name__ == "__main__":
    sys.exit(rodar_autoteste({
        "lê a forma de hoje (<script type=application/json>)": t_le_a_forma_de_hoje,
        "lê a forma antiga (<input value>), que é a da evidência preservada": t_le_a_forma_antiga,
        "§209 página sem a estrutura de resultados levanta, não devolve zero": t_sem_estrutura_levanta,
        "estrutura ilegível levanta": t_estrutura_ilegivel_levanta,
        "estrutura sem a chave de resultados levanta": t_estrutura_sem_a_chave_levanta,
        "com a estrutura presente, lista vazia é resposta e não lacuna": t_lista_vazia_com_estrutura_e_resultado,
        "total declarado pela página é lido (e ausente vira None)": t_total_declarado,
        "janela que cabe é lida numa consulta só": t_janela_cabe_nao_estreita,
        "janela que não cabe é estreitada, e a união não repete": t_janela_nao_cabe_e_estreitada,
        "dia único que não cabe volta declarado como leitura parcial": t_dia_unico_que_nao_cabe_volta_declarado,
        "a data vai em dd-mm-aaaa (o outro formato muda a janela em silêncio)": t_data_vai_em_dia_mes_ano,
        "§11 ritmo de 2 s entre consultas ao mesmo host (a primeira não espera)": t_ritmo_de_dois_segundos_entre_consultas,
        "página cheia sem total declarado não passa por leitura completa": t_pagina_cheia_sem_total_declarado_nao_passa_por_completa,
        "o órgão vem declarado pela fonte, não adivinhado do título": t_orgao_vem_da_fonte,
        "o trecho volta sem marcação, e é excerto — não é o ato": t_trecho_vem_sem_marcacao_e_nao_e_o_ato,
    }))
