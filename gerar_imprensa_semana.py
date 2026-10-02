#!/usr/bin/env python3
"""Gera `data/imprensa/semana.json` — os cartões "Esta semana em números" da página Imprensa.

POR QUE ESTE ARQUIVO EXISTE (27/09/2026, §253)
==============================================
Handover da editoria de 27/09: os big numbers da Imprensa devem mostrar MUDANÇAS RECENTES, coisas
que um jornalista extrai para notícia. O número sozinho não é notícia; o NOME é — por isso cada
cartão carrega a lista.

REGRAS QUE VALEM PARA TODO CARTÃO (do handover, e são as do projeto):
  · número lido do dado, NUNCA digitado (portão de paridade);
  · período explícito no cartão ("de dd/mm a dd/mm");
  · fonte e "consultado em";
  · ZERO só quando a coleta rodou. Sem coleta → "sem coleta". Ausência não é zero;
  · sem edição anterior → "primeira medição", nunca variação inventada;
  · rótulo descreve (variável, período, unidade), sem adjetivo — voz de docs/VOZ_EDITORIAL.md;
  · peso zero nos índices: nada daqui é lido por recalcular_mare.py nem gerar_monitor_saude.py.

DUAS DATAS NO MESMO CAMPO, E FOI ISSO QUE QUASE ME FEZ PUBLICAR UMA LACUNA FALSA
===============================================================================
`data/atos_resposta.json` (e o CSV que dele deriva) guarda a data do ato em DOIS formatos:
740 em `dd/mm/aaaa` e 71 em ISO `aaaa-mm-dd`, estas últimas vindas dos diários consorciados.

Em 27/09, um parser que aceitava só `dd/mm/aaaa` me fez medir "71 decretos sem data legível" e
quase registrar isso no CHANGELOG como fato. A editoria corrigiu: os decretos TÊM data. O defeito
era do parser. `data_do_ato()` aceita os dois, e `verificar_imprensa.py` vigia a deriva — porque
quem escrever um leitor com um formato só perde 71 linhas caladamente, e `dados-abertos/` é
consumido por terceiros.

Normalizar o formato PUBLICADO é decisão da editoria, não daqui: mudaria o CSV para quem já o lê.

Uso:
    python3 gerar_imprensa_semana.py                 # grava data/imprensa/semana.json
    python3 gerar_imprensa_semana.py --autoteste     # prova as regras, sem rede
"""
import csv
import io
import json
import pathlib
import sys
from datetime import date, datetime, timedelta

from coletores_base import gravar_em, hoje_editorial

RAIZ = pathlib.Path(__file__).resolve().parent
DATA = RAIZ / "data"
SAIDA = DATA / "imprensa" / "semana.json"
JANELA = 7
JANELA_SECUNDARIA = 14

# Acima deste valor a escala europeia sai da faixa "bom/razoável". A banda é DA FONTE (EAQI), não
# nossa — o cartão cita a escala e não adjetiva.
EAQI_LIMIAR = 40


def data_do_ato(valor) -> date | None:
    """A data do ato, aceitando os DOIS formatos que o dado guarda. None só se não houver data.

    27/09/2026: existir em dois formatos é defeito do dado, e vai ao CHANGELOG — mas ler só um
    deles é defeito do leitor, e apaga 71 atos sem aviso.
    """
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def ler(nome: str, padrao=None):
    caminho = DATA / nome
    if not caminho.exists():
        return padrao
    return json.loads(caminho.read_text(encoding="utf-8"))


def ler_atos() -> list[dict]:
    caminho = RAIZ / "dados-abertos" / "atos_resposta.csv"
    if not caminho.exists():
        return []
    with io.open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def periodo(corte: date) -> dict:
    return {"ini": (corte - timedelta(days=JANELA)).isoformat(), "fim": corte.isoformat()}


def na_janela(itens, corte: date, dias: int = JANELA, desloca: int = 0):
    """Os itens cuja DATA DO ATO cai na janela de `dias` que termina em `corte - desloca`.

    `desloca=JANELA` dá a semana ANTERIOR, que é a base da variação. A data é sempre a do ato, e
    nunca a da localização pelo MARÉ — a regra do handover, e a que separa "publicou" de
    "encontramos"."""
    fim = corte - timedelta(days=desloca)
    ini = fim - timedelta(days=dias)
    return [x for x in itens if (d := data_do_ato(x.get("data"))) and ini < d <= fim]


def variacao_de(valor, anterior):
    """(valor_semana_anterior, variacao). Função pura.

    `anterior=None` significa "não há par comparável" — e aí a variação é `None`, nunca zero:
    "não mudou" e "não sei quanto mudou" são afirmações diferentes. A variação é a diferença
    absoluta, e não um percentual: com base pequena, percentual engana (de 1 para 2 é "+100%").
    """
    if anterior is None or valor is None:
        return None, None
    return anterior, valor - anterior


def cartao(ident, rotulo, valor, fonte, consultado_em, *, per=None, lista=None,
           sem_coleta=False, nota=None, secundaria=None, grupo=None, url_fonte=None,
           anterior=None):
    """Um cartão. `valor=None` com `sem_coleta=True` é 'sem coleta' — nunca zero.

    01/10/2026 (handover da imprensa dinâmica): todo cartão passa a declarar o GRUPO em que aparece
    na página, o endereço da fonte e, quando há par comparável, o valor da semana anterior e a
    variação. Sem par, os dois campos ficam nulos e `primeira_medicao` segue verdadeiro."""
    ant, var = variacao_de(None if sem_coleta else valor, anterior)
    return {
        "id": ident,
        "grupo": grupo,
        "rotulo": rotulo,
        "valor": None if sem_coleta else valor,
        "sem_coleta": bool(sem_coleta),
        "periodo": per,
        "fonte": fonte,
        "url_fonte": url_fonte,
        "consultado_em": consultado_em,
        "primeira_medicao": ant is None,
        "valor_semana_anterior": ant,
        "variacao": var,
        "nota": nota,
        "secundaria": secundaria,
        "lista": lista or [],
    }


def sem_dado(ident, rotulo, grupo, motivo, fonte=None, url_fonte=None):
    """Cartão de indicador que a coleta de hoje não alcança. NUNCA zero.

    O handover é explícito: "indicador sem fonte coletada = cartão com 'sem dado nesta edição',
    nunca zero". Zero diria que não houve pagamento, que nenhum estado mudou de faixa ou que não
    houve internação — três afirmações que o dado não sustenta."""
    return cartao(ident, rotulo, None, fonte or "—", None, sem_coleta=True, nota=motivo,
                  grupo=grupo)


# ── os cartões ──────────────────────────────────────────────────────────────────────────────

def cartao_decretos(atos, corte):
    """1 · Municípios que entraram em emergência no período."""
    decretos = [a for a in atos if "reconhecimento" not in (a.get("causa") or "").lower()]
    def na_janela(dias):
        limite = corte - timedelta(days=dias)
        return [a for a in decretos if (d := data_do_ato(a.get("data"))) and limite < d <= corte]
    j7, j14 = na_janela(JANELA), na_janela(JANELA_SECUNDARIA)
    lista = [{"uf": a["uf"], "municipio": a["municipio"],
              "data": data_do_ato(a["data"]).isoformat(), "causa": a.get("causa"),
              "documento": a.get("decreto"), "url": a.get("url")}
             for a in sorted(j7, key=lambda x: (data_do_ato(x["data"]), x["uf"], x["municipio"]),
                             reverse=True)]
    return cartao(
        "decretos_no_periodo",
        "Municípios que decretaram emergência ou calamidade no período",
        len(j7), "Diários oficiais e diários consorciados (via MARÉ)",
        None, per=periodo(corte), lista=lista,
        secundaria={"rotulo": f"em {JANELA_SECUNDARIA} dias", "valor": len(j14)} if j14 else None)


def cartao_reconhecimentos(atos, corte):
    """2 · Reconhecidos pelo governo federal no período.

    O handover marca este cartão como "a construir", porque o adaptador do S2iD guardaria só o
    total. Medido em 27/09: `atos_resposta.csv` tem data em TODOS os 653 reconhecimentos. O cartão
    é calculável hoje, e a premissa do handover está desmentida no CHANGELOG.
    """
    rec = [a for a in atos if "reconhecimento" in (a.get("causa") or "").lower()]
    limite = corte - timedelta(days=JANELA)
    na = [a for a in rec if (d := data_do_ato(a.get("data"))) and limite < d <= corte]
    lista = [{"uf": a["uf"], "municipio": a["municipio"],
              "data": data_do_ato(a["data"]).isoformat(),
              "documento": a.get("decreto"), "url": a.get("url")}
             for a in sorted(na, key=lambda x: (data_do_ato(x["data"]), x["uf"]), reverse=True)]
    return cartao("reconhecimentos_no_periodo",
                  "Municípios reconhecidos pelo governo federal no período",
                  len(na), "Portarias SEDEC/MIDR publicadas no DOU", None,
                  per=periodo(corte), lista=lista)


def cartao_planos(municipios, corte):
    """3 · Planos municipais com data de ato no período."""
    limite = corte - timedelta(days=JANELA)
    na = [m for m in municipios
          if (m.get("categoria") == "plano"
              and (d := data_do_ato(m.get("data"))) and limite < d <= corte)]
    lista = [{"uf": m["uf"], "municipio": m["nome"], "data": data_do_ato(m["data"]).isoformat(),
              "documento": m.get("documento"), "url": m.get("url")}
             for m in sorted(na, key=lambda x: (data_do_ato(x["data"]), x["uf"]), reverse=True)]
    return cartao("planos_no_periodo", "Planos municipais com data de ato no período",
                  len(na), "Diários oficiais municipais e sítios das prefeituras (via MARÉ)",
                  None, per=periodo(corte), lista=lista,
                  nota=("a data é a do ato, não a da localização pelo MARÉ; plano antigo "
                        "localizado agora não aparece aqui"))


def cartao_focos(sinais):
    """4 · Focos de calor nas últimas 24 horas."""
    ufs = (sinais or {}).get("uf") or {}
    linhas = [(uf, (u.get("fogo") or {})) for uf, u in ufs.items()]
    com_dado = [(uf, f) for uf, f in linhas if f.get("focos_24h") is not None]
    if not com_dado:
        return cartao("focos_24h", "Focos de calor detectados nas últimas 24 horas", None,
                      "Programa Queimadas (INPE)", None, sem_coleta=True)
    total = sum(f["focos_24h"] for _, f in com_dado)
    consultado = next((f.get("consultado_em") for _, f in com_dado if f.get("consultado_em")), None)
    documento = next((f.get("documento") for _, f in com_dado if f.get("documento")), None)
    lista = [{"uf": uf, "valor": f["focos_24h"]}
             for uf, f in sorted(com_dado, key=lambda x: -x[1]["focos_24h"]) if f["focos_24h"]]
    return cartao("focos_24h", "Focos de calor detectados nas últimas 24 horas", total,
                  "Programa Queimadas (INPE)", consultado, lista=lista, nota=documento)


def cartao_avisos(sinais):
    """5 · Avisos meteorológicos em vigor, por grau."""
    ufs = (sinais or {}).get("uf") or {}
    com_dado = [(uf, u.get("avisos_inmet") or {}) for uf, u in ufs.items()]
    com_dado = [(uf, a) for uf, a in com_dado if a.get("total") is not None]
    if not com_dado:
        return cartao("avisos_inmet", "Avisos meteorológicos em vigor", None,
                      "INMET", None, sem_coleta=True)
    total = sum(a["total"] for _, a in com_dado)
    graus = {}
    for _, a in com_dado:
        for grau, n in (a.get("graus") or {}).items():
            graus[grau] = graus.get(grau, 0) + n
    consultado = next((a.get("consultado_em") for _, a in com_dado if a.get("consultado_em")), None)
    lista = [{"uf": uf, "valor": a["total"], "graus": a.get("graus") or {}}
             for uf, a in sorted(com_dado, key=lambda x: -x[1]["total"]) if a["total"]]
    return cartao("avisos_inmet", "Avisos meteorológicos em vigor", total,
                  "INMET — avisos ativos no momento da consulta", consultado, lista=lista,
                  secundaria={"rotulo": "por grau", "valor": graus} if graus else None)


def cartao_alertas(sinais):
    """5b · Alertas do CEMADEN em vigor, por nível."""
    ufs = (sinais or {}).get("uf") or {}
    com_dado = [(uf, u.get("alertas_cemaden") or {}) for uf, u in ufs.items()]
    com_dado = [(uf, a) for uf, a in com_dado if a.get("total") is not None]
    if not com_dado:
        return cartao("alertas_cemaden", "Alertas do CEMADEN em vigor", None,
                      "CEMADEN", None, sem_coleta=True)
    total = sum(a["total"] for _, a in com_dado)
    niveis = {}
    for _, a in com_dado:
        for nivel, n in (a.get("niveis") or {}).items():
            niveis[nivel] = niveis.get(nivel, 0) + n
    consultado = next((a.get("consultado_em") for _, a in com_dado if a.get("consultado_em")), None)
    lista = [{"uf": uf, "valor": a["total"], "municipios": (a.get("municipios") or [])[:20]}
             for uf, a in sorted(com_dado, key=lambda x: -x[1]["total"]) if a["total"]]
    return cartao("alertas_cemaden", "Alertas do CEMADEN em vigor", total,
                  "CEMADEN — alertas vigentes", consultado, lista=lista,
                  secundaria={"rotulo": "por nível", "valor": niveis} if niveis else None)


def cartao_temperatura(sinais):
    """9 · Maior máxima prevista entre as capitais.

    O handover pede `tmax_amanha`. O dado guarda `tmax` com a `data` a que se refere — o cartão
    diz a data que está no dado, nunca "amanhã" sem base.
    """
    ufs = (sinais or {}).get("uf") or {}
    com_dado = [(uf, u.get("temperatura") or {}) for uf, u in ufs.items()]
    com_dado = [(uf, t) for uf, t in com_dado if t.get("tmax") is not None]
    if not com_dado:
        return cartao("temperatura_maxima", "Maior máxima prevista entre as capitais", None,
                      "INMET", None, sem_coleta=True)
    ordenado = sorted(com_dado, key=lambda x: -x[1]["tmax"])
    uf, t = ordenado[0]
    lista = [{"uf": u, "capital": tt.get("capital"), "valor": tt["tmax"], "data": tt.get("data")}
             for u, tt in ordenado[:5]]
    return cartao("temperatura_maxima",
                  "Maior máxima prevista entre as capitais, em grau Celsius",
                  t["tmax"], t.get("publicado_por") or "INMET — previsão para as capitais",
                  t.get("data"), lista=lista,
                  nota=f"{t.get('capital')} ({uf}), previsão para {t.get('data')}; "
                       f"critério: {t.get('criterio')}")


def cartao_qualidade_ar(sinais):
    """10 · Capitais com índice de qualidade do ar acima da faixa boa/razoável.

    O handover pede PM2,5. A editoria removeu o PM2,5 do site em 27/09 (§244 trocou por ÍNDICE),
    então o cartão usa o índice — que é o que interessa a quem lê, e vem pronto da fonte.
    """
    ufs = (sinais or {}).get("uf") or {}
    linhas = []
    for uf, u in ufs.items():
        ind = ((u.get("qualidade_ar") or {}).get("indice") or {})
        if ind.get("valor") is not None:
            linhas.append((uf, ind))
    if not linhas:
        return cartao("qualidade_ar_indice",
                      "Capitais com índice de qualidade do ar acima da faixa boa ou razoável",
                      None, "Copernicus CAMS via Open-Meteo", None, sem_coleta=True)
    acima = [(uf, i) for uf, i in linhas if i["valor"] > EAQI_LIMIAR]
    escala = linhas[0][1].get("escala")
    publicado = linhas[0][1].get("publicado_por")
    lista = [{"uf": uf, "valor": i["valor"], "hora": i.get("hora")}
             for uf, i in sorted(acima, key=lambda x: -x[1]["valor"])]
    return cartao("qualidade_ar_indice",
                  f"Capitais com índice {escala} acima de {EAQI_LIMIAR}",
                  len(acima), publicado or "Copernicus CAMS via Open-Meteo",
                  linhas[0][1].get("hora"), lista=lista,
                  nota=(f"escala {escala}, faixas da própria fonte; {len(linhas)} capital(is) com "
                        f"leitura; critério: {linhas[0][1].get('criterio')}"))


# ── cartões que o handover pede e que NÃO são calculáveis hoje ──────────────────────────────

NAO_CALCULAVEIS = [
    {"id": "planos_localizados_no_periodo",
     "rotulo": "Planos localizados pelo MARÉ nesta edição",
     "por_que_nao": "o campo `localizado_em` não existe em nenhum registro (medido: 0 de 267 em "
                    "data/municipios.json). Sem ele, a data de localização seria a do ato."},
    {"id": "mudancas_de_categoria",
     "rotulo": "Estados que mudaram de categoria nesta edição",
     "por_que_nao": "não existe fotografia da edição anterior (`data/edicao_anterior/`). Sem o par, "
                    "o diff seria inventado."},
    {"id": "dengue_no_periodo",
     "rotulo": "Municípios que entraram em alerta de dengue no período",
     "por_que_nao": "o handover marca como calculável, mas a medição desmente: `dengue_capitais` "
                    "tem 27 CAPITAIS com uma única semana epidemiológica corrente, e "
                    "`serie_capitais` é série agregada das 27, não nível por município por SE. "
                    "Sem o nível da SE anterior, a passagem para laranja/vermelho seria inventada."},
    {"id": "paginas_fora_do_ar",
     "rotulo": "Páginas oficiais fora do ar por aviso eleitoral",
     "por_que_nao": "depende do campo `escopo` em data/calendario/fontes_suspensas.json, que hoje "
                    "é nulo nos 38 registros (bloco E do pedido de 27/09, não executado)."},
]


# ── cartões novos do handover de 01/10/2026 ─────────────────────────────────────────────────

def cartao_populacao_decretos(atos, municipios, corte):
    """Emergências · quanta gente vive nos municípios que decretaram no período.

    A população vem de `data/populacao_censo2022.json`, a MESMA fonte que `gerar_resposta.py` usa
    para a página de Defesa civil — o handover exige que o mesmo número não tenha duas origens.

    O pareamento é por código do IBGE, e o código vem do nome e da UF pela referência do IBGE,
    porque `atos_resposta` não guarda código. Município que não casa entra na contagem de
    municípios (cartão acima) e **não** na de pessoas, e a nota diz quantos ficaram fora: somar
    zero habitante por falta de pareamento seria subnotificar com cara de medida — foi o que a
    primeira versão deste cartão fez, com 37 municípios no período e "0 pessoas" na tela.
    """
    pop = ler("populacao_censo2022.json", {}) or {}
    ref = ler("municipios_ibge_referencia.json", []) or []
    ref = ref if isinstance(ref, list) else list(ref.values())
    codigo = {(r["uf"], str(r["nome"]).strip().lower()): str(r["codigo_ibge"]).zfill(7)
              for r in ref if r.get("uf") and r.get("nome")}
    decretos = [a for a in atos if "reconhecimento" not in (a.get("causa") or "").lower()]

    def soma(desloca):
        total, sem = 0, 0
        for a in na_janela(decretos, corte, desloca=desloca):
            cod = str(a.get("ibge") or "").zfill(7)
            if cod == "0000000":
                cod = codigo.get((a.get("uf"), str(a.get("municipio") or "").strip().lower()), "")
            valor = pop.get(cod) if cod else None
            if valor in (None, ""):
                sem += 1
                continue
            try:
                total += int(float(valor))
            except (TypeError, ValueError):
                sem += 1
        return total, sem

    atual, sem_pareamento = soma(0)
    anterior, _ = soma(JANELA)
    return cartao("populacao_decretos_no_periodo",
                  "Pessoas que vivem nos municípios que decretaram no período",
                  atual, "Censo 2022 (IBGE) sobre os decretos lidos pelo MARÉ", None,
                  per=periodo(corte), grupo="emergencias",
                  url_fonte="https://censo2022.ibge.gov.br/", anterior=anterior,
                  nota=(f"{sem_pareamento} município(s) do período sem código do IBGE pareado "
                        f"ficaram fora desta soma" if sem_pareamento else None))


def cartao_capitais_com_plano(municipios):
    """Preparação · capitais com plano localizado, de 27. Nenhum nome digitado aqui.

    02/10/2026: este cartão era lacuna declarada porque `municipios.json` não marca capital e a
    única lista que se tinha achado (`normais_capitais.json`, do Inmet) cobre 24 das 27 — faltam
    MS, RJ e RO, que não têm normal climatológica publicada. A referência das 27 **já existia no
    repositório**: `CAPITAL_IBGE`, pelo código IBGE, em `coletar_siconfi_182.py`, com uma segunda
    cópia em `coletar_sinais_risco.py` que o autoteste daquele coletor compara com esta — duas
    cópias que se conferem valem mais do que uma cópia nova aqui. O nome do município continua
    vindo do arquivo de referência do IBGE, e o código é a chave.
    """
    try:
        from coletar_siconfi_182 import CAPITAL_IBGE
    except Exception:  # noqa: BLE001
        return sem_dado("capitais_com_plano", "Capitais com plano localizado", "preparacao",
                        "a referência das 27 capitais por código IBGE não pôde ser lida")
    ref = ler("municipios_ibge_referencia.json", []) or []
    ref = ref if isinstance(ref, list) else list(ref.values())
    nome_do_codigo, codigo_do_nome = {}, {}
    for r in ref:
        cod = str(r.get("codigo_ibge") or "").zfill(7)
        nome_do_codigo[cod] = (r.get("uf"), r.get("nome"))
        codigo_do_nome[(r.get("uf"), str(r.get("nome") or "").strip().lower())] = cod
    capitais = {c for c in (str(x).zfill(7) for x in CAPITAL_IBGE) if c in nome_do_codigo}
    if len(capitais) != 27:
        return sem_dado("capitais_com_plano", "Capitais com plano localizado", "preparacao",
                        f"a referência do IBGE casou {len(capitais)} das 27 capitais: o cartão "
                        "não publica denominador que não seja 27")
    # O banco de municípios é por (UF, nome): a chave de ligação é o código, pela referência.
    com = []
    for m in municipios:
        if m.get("categoria") != "plano":
            continue
        cod = codigo_do_nome.get((m.get("uf"), str(m.get("nome") or "").strip().lower()))
        if cod in capitais:
            com.append(m)
    return cartao("capitais_com_plano", "Capitais com plano localizado", len(com),
                  "Diários oficiais municipais e sítios das prefeituras (via MARÉ)", None,
                  grupo="preparacao", nota="de 27 capitais",
                  lista=[{"uf": m["uf"], "municipio": m["nome"], "documento": m.get("documento"),
                          "url": m.get("url")} for m in sorted(com, key=lambda x: x["uf"])])


def cartao_mudaram_faixa():
    """Preparação · estados que mudaram de faixa entre a edição anterior e esta.

    02/10/2026: o cartão era lacuna porque faltava a série — `historico_mudancas.json` está vazio,
    e sem faixa por data não há como dizer quem mudou **nem** dizer que ninguém mudou. Agora
    `scripts/registrar_faixas.py` escreve `data/historico_faixas.json` a cada edição, e o cartão lê
    de lá. Enquanto a série tiver uma edição só, ele continua declarando — com o motivo certo.

    Entrar ou sair de "não verificado" não conta: isso é mudança de COBERTURA, não de faixa, e
    somar as duas coisas inflaria o número com estados que ninguém tinha medido ainda.
    """
    from scripts.registrar_faixas import mudaram
    hist = ler("historico_faixas.json", {}) or {}
    m = mudaram(hist, "legal")
    ms = mudaram(hist, "saude")
    if m["mudaram"] is None:
        n_edicoes = len((hist.get("edicoes") or []))
        return sem_dado("ufs_mudaram_faixa", "Estados que mudaram de faixa no período", "preparacao",
                        f"a série de faixas por edição tem {n_edicoes} edição(ões), e a comparação "
                        "pede duas: ela começa na próxima edição")
    lista = list(m["mudaram"]) + [x for x in (ms["mudaram"] or []) if x not in m["mudaram"]]
    de, ate = m["de_ate"]
    return cartao("ufs_mudaram_faixa", "Estados que mudaram de faixa no período", len(lista),
                  "MARÉ, sobre os documentos lidos em cada estado", None, grupo="preparacao",
                  nota=f"entre as edições de {de} e {ate}, nos dois índices",
                  lista=[{"uf": x["uf"], "de": x["de"], "para": x["para"]} for x in lista])


def cartao_municipios_sob_alerta():
    """Risco agora · municípios sob alerta do Cemaden, na MESMA unidade da Defesa civil.

    O cartão antigo contava AVISOS; a Defesa civil conta MUNICÍPIOS. Dois números para a mesma
    coisa em páginas vizinhas é o defeito nomeado no item 0 do handover, e a correção é ler o mesmo
    arquivo que ela lê."""
    al = ler("alertas/vigentes.json", {}) or {}
    res = al.get("resumo") or {}
    if not res:
        return sem_dado("municipios_sob_alerta_cemaden", "Municípios sob alerta do Cemaden",
                        "risco_agora",
                        "o arquivo de alertas vigentes não foi coletado nesta edição")
    return cartao("municipios_sob_alerta_cemaden", "Municípios sob alerta do Cemaden",
                  res.get("municipios_cemaden"), "Cemaden (alertas vigentes)", al.get("gerado_em"),
                  grupo="risco_agora", url_fonte="https://www.gov.br/cemaden/pt-br",
                  nota="mesma consulta e mesma unidade da página Defesa civil")


def cartao_dengue_semana():
    """Saúde · casos de dengue na última semana epidemiológica com dado, nos acompanhados."""
    serie = ler("saude_desfechos/serie_uf.json", {}) or {}
    uf = serie.get("uf") or {}
    if not uf:
        return sem_dado("dengue_casos_se", "Casos de dengue notificados na semana epidemiológica",
                        "saude", "a série por estado não foi coletada nesta edição")
    semanas = sorted({se for v in uf.values() for se, d in v.items()
                      if isinstance(d, dict) and d.get("casos") is not None})
    if not semanas:
        return sem_dado("dengue_casos_se", "Casos de dengue notificados na semana epidemiológica",
                        "saude", "a série por estado não traz casos notificados nesta edição")
    ultima = semanas[-1]
    anterior_se = semanas[-2] if len(semanas) > 1 else None

    def soma(se):
        if not se:
            return None
        return int(sum((v.get(se) or {}).get("casos") or 0 for v in uf.values()))

    return cartao("dengue_casos_se",
                  f"Casos de dengue notificados na semana epidemiológica {ultima.split('-')[-1]}",
                  soma(ultima), "InfoDengue (Fiocruz/FGV), municípios acompanhados pelo MARÉ",
                  serie.get("gerado_em"), grupo="saude", url_fonte="https://info.dengue.mat.br/",
                  anterior=soma(anterior_se),
                  nota=("as últimas semanas são parciais e sobem com as notificações atrasadas; "
                        "este número não indica relação com o El Niño"))


def cartao_srag_semana():
    """Saúde · internações por síndrome respiratória grave na última semana epidemiológica.

    A forma do arquivo é `serie: {UF: {"2026-37": n}}` — foi assim que o SIVEP-Gripe chegou em
    02/10/2026, e não como a lista que eu havia suposto antes de ele existir. O cartão soma o país
    por semana, usa a última semana do ano corrente e compara com a anterior.

    As últimas semanas são PARCIAIS, e quantas são é o próprio arquivo que diz (`se_incompletas`):
    notificação e resultado laboratorial chegam depois. A nota declara isso — sem ela, a queda do
    fim da série seria lida como melhora."""
    srag = ler("saude_desfechos/srag_serie.json", None)
    rotulo = "Internações por síndrome respiratória grave na semana epidemiológica"
    if not srag or not srag.get("serie"):
        return sem_dado("srag_internacoes_se", rotulo, "saude",
                        "a série do SIVEP-Gripe ainda não foi coletada até o corte",
                        fonte="SIVEP-Gripe (Ministério da Saúde)")
    ano = str(srag.get("ano_corrente") or hoje_editorial().year)
    total = {}
    for semanas in srag["serie"].values():
        if not isinstance(semanas, dict):
            continue
        for se, n in semanas.items():
            if str(se).startswith(ano) and isinstance(n, (int, float)):
                total[se] = total.get(se, 0) + n
    if not total:
        return sem_dado("srag_internacoes_se", rotulo, "saude",
                        f"a série não traz semanas de {ano} até o corte",
                        fonte="SIVEP-Gripe (Ministério da Saúde)")
    semanas = sorted(total)
    ultima = semanas[-1]
    anterior = total[semanas[-2]] if len(semanas) > 1 else None
    incompletas = srag.get("se_incompletas")
    nota = ("as últimas semanas são parciais e sobem com as notificações atrasadas"
            + (f" (a fonte declara {incompletas} semana(s) incompleta(s))" if incompletas else "")
            + "; este número não indica relação com o El Niño")
    return cartao("srag_internacoes_se", f"{rotulo} {ultima.split('-')[-1]}",
                  int(total[ultima]), "SIVEP-Gripe (Ministério da Saúde)", srag.get("gerado_em"),
                  grupo="saude", url_fonte=srag.get("fonte"),
                  anterior=None if anterior is None else int(anterior), nota=nota)


def cartao_ufs_dengue_alerta():
    """Saúde · estados com dengue em nível de alerta, pelo InfoDengue.

    A régua é da fonte (níveis 3 e 4). A agregação por estado é NOSSA, e a nota diz qual é — sem
    ela, o leitor entenderia que o InfoDengue publica um nível por estado, e ele não publica."""
    painel = ler("saude_desfechos/serie_painel.json", {}) or {}
    M = painel.get("municipios") or {}
    if not M:
        return sem_dado("ufs_dengue_alerta", "Estados com dengue em nível de alerta", "saude",
                        "o painel municipal não foi coletado nesta edição")
    ufs = sorted({m.get("uf") for m in M.values()
                  if (m.get("nivel_ultima_se") or 0) >= 3 and m.get("uf")})
    return cartao("ufs_dengue_alerta", "Estados com dengue em nível de alerta", len(ufs),
                  "InfoDengue (Fiocruz/FGV)", painel.get("gerado_em"), grupo="saude",
                  url_fonte="https://info.dengue.mat.br/", lista=[{"uf": u} for u in ufs],
                  nota=("nível de alerta calculado pelo InfoDengue a partir das notificações; o "
                        "estado entra quando ao menos um município acompanhado está em nível 3 "
                        "ou 4"))


def cartoes_do_dinheiro(corte):
    """Dinheiro · os três do handover, e o que cada um pode dizer hoje.

    Nenhum deles vira zero. Os dois primeiros não são calculáveis por semana, e o motivo é da
    FONTE: as medidas federais publicam empenhado e pago em agregados sem data de pagamento, e o
    Portal da Transparência publica transferência a município por MÊS — medido em 01/10/2026."""
    atos = (ler("financiamento/compromissos_federais.json", {}) or {}).get("itens") or []
    tres = [
        sem_dado("pago_na_semana",
                 "Desembolsado no período em recursos oriundos das medidas federais do El Niño",
                 "dinheiro",
                 "as medidas federais publicam empenhado e pago em agregados sem data de "
                 "pagamento: não há como recortar sete dias sem inventar a data",
                 fonte="Portal da Transparência e atos federais"),
        sem_dado("transferido_na_semana", "Transferido pela União a municípios no período",
                 "dinheiro",
                 "o Portal da Transparência publica a transferência a município por MÊS: a "
                 "fonte entrega o mês, e não a semana",
                 fonte="Portal da Transparência (transferências)",
                 url_fonte="https://portaldatransparencia.gov.br/download-de-dados/transferencias"),
    ]
    if not atos:
        tres.append(sem_dado("atos_federais_no_periodo",
                             "Novos atos federais de financiamento no período", "dinheiro",
                             "o arquivo de compromissos federais não foi coletado nesta edição"))
        return tres
    na = na_janela(atos, corte)
    tres.append(cartao("atos_federais_no_periodo",
                       "Novos atos federais de financiamento no período", len(na),
                       "Atos federais lidos pelo MARÉ", None, per=periodo(corte), grupo="dinheiro",
                       anterior=len(na_janela(atos, corte, desloca=JANELA)),
                       lista=[{"documento": a.get("instrumento"), "nome": a.get("nome"),
                               "url": a.get("url")} for a in na]))
    return tres


def texto_pronto(cartoes: list[dict]) -> str:
    """Uma frase por cartão com valor. Cláusula de valor zero ou sem coleta é OMITIDA."""
    por_id = {c["id"]: c for c in cartoes}
    partes = []

    def v(ident):
        c = por_id.get(ident)
        if not c or c["sem_coleta"] or not c["valor"]:
            return None
        return c

    c = v("decretos_no_periodo")
    if c:
        ufs = sorted({x["uf"] for x in c["lista"]})[:3]
        ini = datetime.fromisoformat(c["periodo"]["ini"]).strftime("%d/%m")
        fim = datetime.fromisoformat(c["periodo"]["fim"]).strftime("%d/%m")
        partes.append(f"Entre {ini} e {fim}, {c['valor']} municípios decretaram emergência ou "
                      f"calamidade ({', '.join(ufs)})")
    c = v("reconhecimentos_no_periodo")
    if c:
        partes.append(f"{c['valor']} municípios foram reconhecidos pelo governo federal")
    c = v("planos_no_periodo")
    if c:
        partes.append(f"{c['valor']} planos municipais têm ato no período")
    c = v("focos_24h")
    if c:
        top = c["lista"][0]["uf"] if c["lista"] else None
        partes.append(f"o INPE detectou {c['valor']} focos de calor nas últimas 24 horas"
                      + (f" ({top})" if top else ""))
    c = v("avisos_inmet")
    if c:
        partes.append(f"{c['valor']} avisos meteorológicos do INMET estão em vigor")
    c = v("alertas_cemaden")
    if c:
        partes.append(f"{c['valor']} alertas do CEMADEN estão em vigor")
    c = v("temperatura_maxima")
    if c and c["lista"]:
        # Vírgula decimal: o texto é público e em português. "39.0 °C" é erro de idioma.
        graus = f"{c['valor']:.1f}".replace(".", ",")
        partes.append(f"a maior máxima prevista entre as capitais é de {graus} °C em "
                      f"{c['lista'][0]['capital']}")
    c = v("qualidade_ar_indice")
    if c:
        partes.append(f"{c['valor']} capitais estão com índice de qualidade do ar acima de "
                      f"{EAQI_LIMIAR}")
    return ("; ".join(partes) + ".") if partes else ""


def montar(corte: date) -> dict:
    atos = ler_atos()
    municipios = ler("municipios.json", []) or []
    sinais = ler("sinais_risco.json", {}) or {}

    # A ordem é a dos grupos aprovados em 01/10/2026: preparação, emergências, risco agora,
    # dinheiro, saúde. Cada cartão carrega o seu grupo, e a página não reordena nada.
    #
    # Saem daqui dois cartões antigos: "avisos meteorológicos em vigor" (contava AVISOS onde a
    # Defesa civil conta MUNICÍPIOS — item 0 do handover) e "alertas do CEMADEN em vigor", pela
    # mesma razão. No lugar entra `cartao_municipios_sob_alerta`, que lê o arquivo que ela lê.
    cartoes = [
        cartao_planos(municipios, corte),
        cartao_mudaram_faixa(),
        cartao_capitais_com_plano(municipios),
        cartao_decretos(atos, corte),
        cartao_populacao_decretos(atos, municipios, corte),
        cartao_reconhecimentos(atos, corte),
        cartao_municipios_sob_alerta(),
        cartao_focos(sinais),
        cartao_temperatura(sinais),
        cartao_qualidade_ar(sinais),
        *cartoes_do_dinheiro(corte),
        cartao_dengue_semana(),
        cartao_srag_semana(),
        cartao_ufs_dengue_alerta(),
    ]
    # Grupo e endereço da fonte dos cartões que já existiam. Entram por mapa, e não por argumento
    # na chamada: `cartao()` é posicional, e um `grupo=` no meio quebraria as cinco de uma vez.
    GRUPO_DOS_ANTIGOS = {"planos_no_periodo": "preparacao",
                         "decretos_no_periodo": "emergencias",
                         "reconhecimentos_no_periodo": "emergencias",
                         "focos_24h": "risco_agora",
                         "temperatura_maxima": "risco_agora",
                         "qualidade_ar_indice": "risco_agora"}
    URL_DOS_ANTIGOS = {"focos_24h": "https://terrabrasilis.dpi.inpe.br/queimadas/portal/",
                       "reconhecimentos_no_periodo": "https://www.gov.br/mdr/pt-br"}
    for c in cartoes:
        if c.get("grupo") is None:
            c["grupo"] = GRUPO_DOS_ANTIGOS.get(c["id"])
        if c.get("url_fonte") is None:
            c["url_fonte"] = URL_DOS_ANTIGOS.get(c["id"])
    assert all(c.get("grupo") for c in cartoes), "cartão sem grupo não tem onde aparecer na página"
    return {
        "_governanca":
            "Cartões 'Esta semana em números' da página Imprensa (handover da editoria de "
            "27/09/2026, §253). Peso ZERO nos índices: nada aqui é lido por recalcular_mare.py "
            "nem por gerar_monitor_saude.py. Todo número vem do dado; texto fixo nunca contém "
            "número. Zero só quando a coleta rodou — sem coleta é `sem_coleta: true`, e ausência "
            "não é zero. Sem fotografia da edição anterior, `primeira_medicao: true` e "
            "`variacao: null`: variação sem par seria inventada. Derivado de "
            "gerar_imprensa_semana.py — não se edita à mão.",
        "gerado_em": corte.isoformat(),
        "janela_dias": JANELA,
        "cartoes": cartoes,
        "nao_calculaveis": NAO_CALCULAVEIS,
        "texto_pronto": texto_pronto(cartoes),
    }


# ── autoteste ───────────────────────────────────────────────────────────────────────────────

def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # A lição de 27/09: os DOIS formatos, e nada além deles em silêncio.
    checar("data_do_ato aceita dd/mm/aaaa", data_do_ato("15/09/2026") == date(2026, 9, 15))
    checar("data_do_ato aceita ISO", data_do_ato("2026-09-15") == date(2026, 9, 15))
    checar("data_do_ato devolve None em vazio", data_do_ato("") is None and data_do_ato(None) is None)
    checar("data_do_ato devolve None em lixo", data_do_ato("setembro") is None)

    corte = date(2026, 9, 27)

    # Zero não é sem coleta, e sem coleta não é zero.
    c = cartao_focos({"uf": {}})
    checar("sem fonte nenhuma, o cartão diz sem coleta e valor null",
           c["sem_coleta"] is True and c["valor"] is None)
    c = cartao_focos({"uf": {"AC": {"fogo": {"focos_24h": 0, "consultado_em": "x"}}}})
    checar("coleta que rodou e deu zero é ZERO, não sem coleta",
           c["sem_coleta"] is False and c["valor"] == 0)

    # O cartão de decretos tem de ver o ato em ISO — era o defeito de 27/09.
    atos = [{"uf": "MG", "municipio": "Teófilo Otoni", "data": "2026-09-25",
             "causa": "situação de emergência", "decreto": "Decreto nº 79", "url": "u"},
            # 22/09, não 20/09: a janela de 7 dias até 27/09 cobre 21 a 27, e 20 é o limite
            # exclusivo. A primeira montagem deste teste usou 20/09 e reprovou — o código estava
            # certo, a fixture estava errada.
            {"uf": "SP", "municipio": "X", "data": "22/09/2026",
             "causa": "situação de emergência", "decreto": "d", "url": "u"},
            {"uf": "BA", "municipio": "Y", "data": "24/09/2026",
             "causa": "reconhecimento federal", "decreto": "p", "url": "u"}]
    c = cartao_decretos(atos, corte)
    checar("decreto em ISO entra na contagem", c["valor"] == 2)
    checar("reconhecimento NÃO entra no cartão de decretos",
           all("reconhecimento" not in (x["causa"] or "").lower() for x in c["lista"]))
    r = cartao_reconhecimentos(atos, corte)
    checar("reconhecimento entra no cartão dele", r["valor"] == 1)

    # Variação inventada é proibida enquanto não houver edição anterior.
    CARTOES_DO_TESTE = montar(corte)["cartoes"]
    # 01/10/2026 (handover da imprensa dinâmica): o caso anterior cobrava que NENHUM cartão
    # tivesse variação — regra de 27/09, quando não havia fotografia da edição anterior. Agora a
    # variação é exigida onde há par comparável, e proibida onde não há. Os dois casos abaixo
    # cobram as duas metades dessa regra.
    checar("cartão com par comparável traz valor da semana anterior e variação",
           all((c["valor_semana_anterior"] is not None) == (c["variacao"] is not None)
               for c in CARTOES_DO_TESTE))
    checar("cartão sem par não inventa variação",
           all(c["variacao"] is None for c in CARTOES_DO_TESTE if c["primeira_medicao"]))
    checar("variação é diferença absoluta, e confere com os dois valores",
           all(c["variacao"] == c["valor"] - c["valor_semana_anterior"]
               for c in CARTOES_DO_TESTE if c["variacao"] is not None))
    checar("todo cartão declara o grupo em que aparece na página",
           all(c.get("grupo") in ("preparacao", "emergencias", "risco_agora", "dinheiro",
                                  "saude") for c in CARTOES_DO_TESTE))

    # Período em todo cartão de janela.
    for ident in ("decretos_no_periodo", "reconhecimentos_no_periodo", "planos_no_periodo"):
        cc = next(x for x in montar(corte)["cartoes"] if x["id"] == ident)
        if not cc["periodo"]:
            falhas.append(f"{ident} sem período")
    checar("cartão de janela tem período", not any("sem período" in f for f in falhas))

    # A frase pronta omite cláusula de valor zero — nunca "0 planos foram publicados".
    frase = texto_pronto([cartao("planos_no_periodo", "r", 0, "f", None, per=periodo(corte)),
                          cartao("focos_24h", "r", 5, "f", "x", lista=[{"uf": "PA", "valor": 5}])])
    checar("frase pronta omite cláusula de valor zero", "planos" not in frase and "5 focos" in frase)
    frase2 = texto_pronto([cartao("focos_24h", "r", None, "f", None, sem_coleta=True)])
    checar("frase pronta omite cartão sem coleta", frase2 == "")

    # Os não calculáveis precisam DIZER por quê — senão viram silêncio.
    checar("todo não calculável declara o motivo",
           all(x.get("por_que_nao") for x in NAO_CALCULAVEIS))
    checar("dengue está entre os não calculáveis, contra o que o handover supõe",
           any(x["id"] == "dengue_no_periodo" for x in NAO_CALCULAVEIS))

    if falhas:
        print(f"\n✗ IMPRENSA SEMANA: {len(falhas)} falha(s).")
        return 1
    print("\n✓ IMPRENSA SEMANA OK — dois formatos de data, zero ≠ sem coleta, "
          "sem variação inventada, cláusula zero omitida.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()
    meta = ler("meta.json", {}) or {}
    # O dia de hoje vem do fuso da REDAÇÃO, nunca do runner: o runner é UTC, e entre 21h e
    # meia-noite de Brasília os dois discordam do dia. A janela dos cartões é editorial, não do
    # servidor. Há portão de regressão para isso, e ele me reprovou no CI do PR #407.
    corte = data_do_ato(meta.get("corte")) or hoje_editorial()
    r = montar(corte)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    # §229: JSON de data/ passa pela porta atômica, nunca por write_text direto. Uma auditoria de
    # 26/09 achou trinta e três escritas fora dela — entre elas o log de 24 MB e o banco municipal
    # — e o portão 29 reprova quem repetir. Eu repeti, e o CI do PR #403 me pegou.
    gravar_em(SAIDA, r)
    com_valor = sum(1 for c in r["cartoes"] if not c["sem_coleta"])
    print(f"→ {SAIDA.relative_to(RAIZ)} gravado · {len(r['cartoes'])} cartão(ões), "
          f"{com_valor} com coleta, {len(r['nao_calculaveis'])} não calculável(is) declarado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
