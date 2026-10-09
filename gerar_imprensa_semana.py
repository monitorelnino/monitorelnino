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


# -- cartoes IMPORTADOS das paginas de origem (handover de 02/10/2026, item 1) ----------------
# A Imprensa nao recalcula mais nada que outra pagina ja publica. Cada numero abaixo e LIDO do
# instantaneo que o gerador da pagina de origem escreve:
#
#   data/financiamento/semana.json        · Financiamento   (gerar_financiamento_semana.py)
#   data/saude_desfechos/topo_saude.json  · MARE Saude      (scripts/gerar_topo_das_paginas.py)
#   data/resposta/topo_defesa_civil.json  · Defesa civil    (idem)
#   data/topo_monitor_riscos.json          · Monitor de riscos (idem)
#
# Por que: em 02/10/2026 a Imprensa dizia "sem dado" no dinheiro com dado publicado no
# Financiamento, e 482 casos de dengue na semana 37 (InfoDengue) onde o MARE Saude dizia 8.146 na
# semana 33 (Sinan). Duas definicoes do mesmo numero, uma em cada pagina, e nada obrigando as duas
# a concordarem. Agora ha uma definicao e um lugar; a Imprensa le.

FONTE_LEITOR = {
    "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)": "Portal da Transparência",
    "Portal da Transparência, Transferências de Recursos (dados abertos)": "Portal da Transparência",
    "Portarias da SEDEC no Diário Oficial da União": "Defesa Civil nacional, no Diário Oficial da União",
    "Atos federais lidos pelo MARÉ": "atos federais lidos pelo MARÉ",
}


def _reais(v):
    """R$ com separador de milhar brasileiro. Funcao pura."""
    if v is None:
        return None
    inteiro = f"{round(float(v)):,}".replace(",", ".")
    return "R$ " + inteiro


def importado(ident, rotulo, fonte_card, *, grupo, valor=None, referencia=None, variacao=None,
              fonte=None, url_fonte=None, nota=None, unidade=None, origem=None):
    """Um cartao cujo valor veio pronto da pagina de origem. Funcao pura.

    `fonte_card` e o cartao do instantaneo; `origem` e a pagina que o publica — ela entra no
    registro porque o portao de coerencia confere numero contra pagina, e sem dizer qual pagina
    o portao nao sabe onde conferir.
    """
    c = fonte_card or {}
    sem = bool(c.get("sem_coleta")) if valor is None else False
    v = c.get("valor") if valor is None else valor
    if v is None:
        sem = True
    var = variacao if valor is None else None
    if variacao is not None:
        var = variacao
    if valor is not None and variacao is None:
        var = None
    elif valor is None and variacao is None:
        var = c.get("variacao")
    return {
        "id": ident, "grupo": grupo, "rotulo": rotulo,
        "valor": None if sem else v,
        "unidade": unidade,
        "sem_coleta": sem,
        "periodo": None,
        "referencia": referencia if referencia is not None else c.get("referencia"),
        "fonte": fonte or FONTE_LEITOR.get(c.get("fonte"), c.get("fonte")) or "—",
        "url_fonte": url_fonte or c.get("url_fonte"),
        "consultado_em": c.get("referencia"),
        # `valor` passado é OVERRIDE: nesse caso o cartão publica outro recorte do mesmo cartão de
        # origem (a contagem da SEMANA, e não o acumulado do ciclo), e a variação do instantâneo
        # NÃO se aplica a ele — ela é a variação do acumulado, que aqui já é o próprio valor.
        # Publicar a mesma conta como valor e como variação diria duas vezes a mesma coisa, e o
        # portão da imprensa cobra que variação feche com o par — que aqui não existe.
        "primeira_medicao": var is None,
        "valor_semana_anterior": None,
        "variacao": var,
        "nota": nota if nota is not None else c.get("nota"),
        "secundaria": None,
        "lista": c.get("lista") or [],
        "pagina_de_origem": origem,
    }


def por_id(instantaneo):
    """{id: cartao} do instantaneo. Funcao pura."""
    return {c.get("id"): c for c in (instantaneo or {}).get("cartoes") or []}


def cartoes_das_emergencias(dc):
    """Emergencias: tres cartoes da SEMANA, lidos do instantaneo da Defesa civil."""
    d = por_id(dc)
    dec = d.get("municipios_decretaram") or {}
    pop = d.get("populacao_sob_decreto") or {}
    rec = d.get("reconhecidos_pelo_governo_federal") or {}
    return [
        importado("decretos_na_semana",
                  "Municípios que decretaram emergência ou calamidade na semana", dec,
                  grupo="emergencias", valor=dec.get("variacao"), referencia="últimos 7 dias",
                  nota="pela data do decreto", origem="defesa-civil.html"),
        importado("populacao_decretos_na_semana",
                  "Pessoas que vivem nos municípios que decretaram na semana", pop,
                  grupo="emergencias", valor=pop.get("variacao"), referencia="últimos 7 dias",
                  unidade="pessoas", nota="Censo 2022, pelos municípios que entraram na semana",
                  origem="defesa-civil.html"),
        importado("reconhecimentos_na_semana",
                  "Municípios que tiveram a emergência reconhecida pelo governo federal na semana",
                  rec, grupo="emergencias", valor=rec.get("variacao"), referencia="últimos 7 dias",
                  nota="pela data da portaria", origem="defesa-civil.html"),
    ]


def cartoes_do_risco_agora(dc, riscos, sinais):
    """Risco agora: seis cartoes. Tres da Defesa civil, dois do Monitor de riscos, um do fogo."""
    d, r = por_id(dc), por_id(riscos)
    # Os tres primeiros cartoes vem do instantaneo da Defesa civil, que desde 08/10/2026 ja
    # declara a parada das 24 horas (scripts/gerar_topo_das_paginas.alertas_pararam). A Imprensa
    # nao repete a regra: ela copia o instantaneo, e por isso para junto.
    cartoes = [
        importado("municipios_alerta_cemaden", "Municípios sob alerta do Cemaden",
                  d.get("municipios_alerta_cemaden"), grupo="risco_agora",
                  url_fonte="https://www.gov.br/cemaden/pt-br", origem="defesa-civil.html"),
        importado("municipios_aviso_inmet", "Municípios sob aviso do Inmet",
                  d.get("municipios_aviso_inmet"), grupo="risco_agora",
                  url_fonte="https://portal.inmet.gov.br/", origem="defesa-civil.html"),
        importado("decreto_e_alerta_ao_mesmo_tempo",
                  "Municípios com decreto de emergência e alerta ao mesmo tempo",
                  d.get("decreto_e_alerta_ao_mesmo_tempo"), grupo="risco_agora",
                  origem="defesa-civil.html"),
        cartao_focos(sinais),
        importado("temperatura_desvio_capital",
                  "A maior diferença de temperatura máxima em relação ao normal, em grau Celsius",
                  r.get("temperatura_desvio_capital"), grupo="risco_agora", unidade="°C",
                  origem="monitor-de-riscos.html"),
        importado("capitais_ar_ruim_ou_pior", "Capitais com o ar na faixa ruim ou acima dela",
                  r.get("capitais_ar_ruim_ou_pior"), grupo="risco_agora",
                  origem="monitor-de-riscos.html"),
    ]
    return cartoes


def cartoes_do_dinheiro_importados(fin, recursos):
    """Dinheiro: tres cartoes, lidos do instantaneo do Financiamento.

    O recorte e o que a FONTE permite, e o instantaneo ja o traz: mes fechado onde a fonte publica
    por mes, sete dias onde o ato tem data. A Imprensa nao reaperta o recorte — apertar aqui seria
    publicar um numero que a pagina de origem nao publica.
    """
    f = por_id(fin)
    pago = f.get("pago_periodo_mp") or {}
    resp = f.get("resposta_liberado_semana") or {}
    atos = f.get("atos_federais_semana") or {}
    n_mun = (recursos or {}).get("municipios_com_ato")
    janela = ((recursos or {}).get("janela_lida") or {})
    return [
        importado("desembolsado_no_mes",
                  "Em recursos oriundos das medidas federais do El Niño, desembolsados no "
                  + (pago.get("periodo") or "mês fechado"), pago, grupo="dinheiro",
                  unidade="reais", referencia=pago.get("periodo"), origem="financiamento.html"),
        importado("resposta_autorizado_semana",
                  "Autorizados pela defesa civil federal nos últimos 7 dias", resp,
                  grupo="dinheiro", unidade="reais", referencia="últimos 7 dias",
                  nota=(f"para {n_mun} município(s) com ato no ciclo" if n_mun else None)
                       or resp.get("detalhe"),
                  origem="financiamento.html"),
        importado("atos_federais_semana",
                  "Atos federais de financiamento publicados nos últimos 7 dias", atos,
                  grupo="dinheiro", unidade="atos", referencia="últimos 7 dias",
                  origem="financiamento.html"),
    ]


def cartoes_da_saude_importados(saude):
    """Saude: tres cartoes, lidos do instantaneo do MARE Saude.

    A semana epidemiologica fechada e a do gerador da saude — uma definicao so, como o handover
    exige. Era aqui que a Imprensa publicava a semana 37 do InfoDengue enquanto a pagina publicava
    a semana 33 do Sinan.
    """
    s_ = por_id(saude)
    den = s_.get("dengue_casos_se") or {}
    srag = s_.get("srag_internacoes_se") or {}
    ufs = s_.get("uf_dengue_alerta") or {}
    se = lambda c: (str(c.get("referencia") or "").split("-")[-1] or "—")
    return [
        importado("dengue_casos_se",
                  f"Casos prováveis de dengue na semana epidemiológica {se(den)}", den,
                  grupo="saude", origem="saude.html"),
        importado("srag_internacoes_se",
                  "Internações por síndrome respiratória grave na semana epidemiológica "
                  + se(srag), srag, grupo="saude", origem="saude.html"),
        importado("ufs_dengue_alerta", "Estados com dengue em nível de alerta", ufs,
                  grupo="saude", origem="saude.html"),
    ]


def texto_pronto(cartoes: list[dict], indices: dict = None) -> str:
    """O release da edicao, no texto aprovado em 02/10/2026.

    Tres regras, e as tres sao do handover: **frase sem dado e omitida**; a concordancia segue o
    numero (0 vira "nenhum municipio publicou", 1 vira singular); populacao vem arredondada. Zero
    escrito por extenso existe porque "0 municipios publicaram plano" se le como falha de sistema,
    e "nenhum municipio publicou plano" se le como o fato que e.
    """
    d = {c["id"]: c for c in cartoes}
    I = indices or {}

    def v(ident):
        c = d.get(ident)
        if not c or c.get("sem_coleta") or c.get("valor") is None:
            return None
        return c["valor"]

    def milhoes(n):
        if n is None:
            return None
        if n >= 1e6:
            x = round(n / 1e6, 1)
            return f"{x:.1f}".replace(".", ",") + (" milhão" if x < 2 else " milhões")
        return f"{int(n):,}".replace(",", ".")

    def mun(n, verbo_sing, verbo_plur):
        if n == 0:
            return "nenhum município " + verbo_sing
        if n == 1:
            return "1 município " + verbo_sing
        return f"{n} municípios " + verbo_plur

    # As frases do release são as do texto aprovado, e a pontuação é a dele: o parágrafo do ciclo
    # começa com "Desde o início do ciclo". Juntar tudo com ponto e vírgula produzia "…verificadas;
    # Na semana", com maiúscula depois de ponto e vírgula — erro de idioma num texto que sai em
    # release de imprensa.
    frases = []
    edicao = I.get("edicao")
    legal, saude_i = I.get("mare_legal"), I.get("mare_saude")
    verificadas = I.get("saude_verificadas")
    if edicao:
        frases.append(f"Edição de {edicao}.")
    if legal is not None and saude_i is not None:
        media = ("" if (verificadas or 0) >= 27 or not verificadas
                 else f", média dos {verificadas} estados verificados")
        frases.append(
            "O MARÉ Legal, índice que acompanha a preparação publicada por estados e municípios "
            f"para o El Niño 2026/2027, está em {str(legal).replace('.', ',')} de 100; o MARÉ "
            f"Saúde, em {str(saude_i).replace('.', ',')} de 100{media}.")
    planos, decretos = v("planos_na_semana"), v("decretos_na_semana")
    pop = v("populacao_decretos_na_semana")
    if planos is not None and decretos is not None:
        frase = ("Na semana, " + mun(planos, "publicou plano para o ciclo",
                                     "publicaram plano para o ciclo")
                 + " e " + mun(decretos, "decretou situação de emergência ou calamidade",
                               "decretaram situação de emergência ou calamidade"))
        if pop:
            frase += f"; {milhoes(pop)} de pessoas vivem nos municípios que decretaram"
        frases.append(frase + ".")
    faixas = v("mudaram_faixa")
    if faixas is not None:
        frases.append(("Nenhum estado mudou de faixa." if faixas == 0
                       else ("1 estado mudou de faixa." if faixas == 1
                             else f"{faixas} estados mudaram de faixa.")))
    primeiro = " ".join(frases)

    segundo = []
    capitais = v("capitais_com_plano")
    ciclo = I.get("decretaram_no_ciclo")
    if capitais is not None and ciclo is not None:
        segundo.append(f"Desde o início do ciclo, em 29 de junho, {capitais} de 27 capitais têm "
                       "plano localizado e " + mun(ciclo, "decretou emergência ou calamidade",
                                                   "decretaram emergência ou calamidade") + ".")
    segundo.append("Cada registro, com documento, data e fonte, está em monitorelnino.com.br. "
                   "O MARÉ é uma criação da Futura Evidence Lab.")
    return (primeiro + chr(10)*2 + " ".join(segundo)).strip()


def montar(corte: date) -> dict:
    """Os cinco grupos aprovados, na ordem aprovada.

    Quase todo cartao e IMPORTADO da pagina de origem (item 1 do handover de 02/10/2026). Os que a
    Imprensa ainda calcula sao os tres da PREPARACAO, porque eles nao existem no topo de nenhuma
    pagina: "planos publicados na semana" e janela de sete dias sobre o banco municipal, "estados
    que mudaram de faixa" sai do historico de faixas, e "capitais com plano" e um recorte proprio
    da Imprensa. Nenhum deles duplica numero publicado em outro lugar.
    """
    municipios = ler("municipios.json", []) or []
    sinais = ler("sinais_risco.json", {}) or {}
    fin = ler("financiamento/semana.json", {}) or {}
    dc = ler("resposta/topo_defesa_civil.json", {}) or {}
    saude = ler("saude_desfechos/topo_saude.json", {}) or {}
    riscos = ler("topo_monitor_riscos.json", {}) or {}
    recursos = ler("resposta/recursos_liberados.json", {}) or {}
    mare = ler("indice.json", {}) or {}
    monitor_saude = ler("monitor_saude.json", {}) or {}
    por_uf = ler("resposta/por_uf.json", {}) or {}

    planos = cartao_planos(municipios, corte)
    planos["id"] = "planos_na_semana"
    planos["rotulo"] = "Planos publicados na semana, pela data do ato"
    faixas = cartao_mudaram_faixa()
    faixas["id"] = "mudaram_faixa"
    faixas["rotulo"] = "Estados que mudaram de faixa no MARÉ Legal ou no MARÉ Saúde"
    capitais = cartao_capitais_com_plano(municipios)
    capitais["id"] = "capitais_com_plano"
    # O rótulo do handover é "{n} de 27 capitais com plano localizado": o número grande é o `n`, e o
    # "de 27" entra no rótulo, que é onde o denominador se lê sem competir com o valor.
    capitais["rotulo"] = "de 27 capitais com plano localizado"

    cartoes = [planos, faixas, capitais]
    cartoes += cartoes_das_emergencias(dc)
    cartoes += cartoes_do_risco_agora(dc, riscos, sinais)
    cartoes += cartoes_do_dinheiro_importados(fin, recursos)
    cartoes += cartoes_da_saude_importados(saude)

    GRUPO_DOS_PROPRIOS = {"planos_na_semana": "preparacao", "mudaram_faixa": "preparacao",
                          "capitais_com_plano": "preparacao", "focos_24h": "risco_agora"}
    URL_DOS_PROPRIOS = {"focos_24h": "https://terrabrasilis.dpi.inpe.br/queimadas/portal/"}
    for c in cartoes:
        if c.get("grupo") is None:
            c["grupo"] = GRUPO_DOS_PROPRIOS.get(c["id"])
        if c.get("url_fonte") is None:
            c["url_fonte"] = URL_DOS_PROPRIOS.get(c["id"])
        c.setdefault("pagina_de_origem", None)
        c.setdefault("referencia", None)
        c.setdefault("unidade", None)
    assert all(c.get("grupo") for c in cartoes), "cartão sem grupo não tem onde aparecer na página"

    resumo = (monitor_saude.get("resumo") or {})
    indices = {
        "edicao": corte.strftime("%d/%m/%Y"),
        # O MARÉ Legal nacional é a MÉDIA DAS 27 UFs do `total` de `indice.json` — a mesma conta
        # que a barra da página inicial faz (assets/js/index.js). Ele não existe como campo no
        # arquivo: a inicial o calcula na hora, e a Imprensa passa a usar a mesma régua.
        "mare_legal": (round(sum((v or {}).get("total") or 0 for v in mare.values()) / 27, 1)
                       if isinstance(mare, dict) and len(mare) >= 27 else None),
        "mare_saude": resumo.get("media_das_verificadas"),
        "saude_verificadas": resumo.get("verificadas"),
        "decretaram_no_ciclo": (por_uf.get("nacional") or {}).get("n_municipios"),
    }
    sem_dado = [c["rotulo"] for c in cartoes if c["sem_coleta"]]
    return {
        "_governanca":
            "Cartões 'Esta semana em números' da página Imprensa. Peso ZERO nos índices. "
            "02/10/2026 (handover do redesenho): a Imprensa NÃO recalcula número que outra página "
            "publica — ela lê o instantâneo do topo de cada página (Financiamento, MARÉ Saúde, "
            "Defesa civil, Monitor de riscos), e cada cartão declara a sua `pagina_de_origem`. "
            "Zero só quando a coleta rodou; sem coleta é `sem_coleta: true`, o cartão SAI da grade "
            "e o rótulo entra na linha 'Sem dado nesta edição'. Derivado de "
            "gerar_imprensa_semana.py — não se edita à mão.",
        "gerado_em": corte.isoformat(),
        "janela_dias": JANELA,
        "indices": indices,
        "cartoes": cartoes,
        "sem_dado_nesta_edicao": sem_dado,
        "nao_calculaveis": NAO_CALCULAVEIS,
        "texto_pronto": texto_pronto(cartoes, indices),
    }


COLUNAS_CSV = ("grupo", "rótulo", "valor", "variação", "referência", "fonte", "URL da fonte",
               "data da consulta")


def linhas_da_planilha(semana: dict) -> list:
    """As linhas da planilha da edição. Função pura.

    Cartão sem dado entra na planilha com valor vazio e a razão na coluna da referência: quem baixa
    a planilha precisa ver a lacuna, e não uma linha que simplesmente não existe.
    """
    linhas = []
    for c in (semana or {}).get("cartoes") or []:
        linhas.append({
            "grupo": c.get("grupo"),
            "rótulo": c.get("rotulo"),
            "valor": "" if c.get("sem_coleta") else c.get("valor"),
            "variação": "" if c.get("variacao") is None else c.get("variacao"),
            "referência": c.get("referencia") or ("sem dado nesta edição" if c.get("sem_coleta") else ""),
            "fonte": c.get("fonte"),
            "URL da fonte": c.get("url_fonte") or "",
            "data da consulta": c.get("consultado_em") or "",
        })
    return linhas


def escrever_planilha(semana: dict, destino: pathlib.Path) -> int:
    """Grava a planilha da edição e devolve o número de linhas."""
    linhas = linhas_da_planilha(semana)
    destino.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(COLUNAS_CSV), lineterminator="\n")
    w.writeheader()
    for linha in linhas:
        w.writerow(linha)
    destino.write_text(buf.getvalue(), encoding="utf-8", newline="")
    return len(linhas)


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

    # ── o que o handover de 02/10 exige: importar, nunca recalcular ──────────────────────────
    DC = {"cartoes": [
        {"id": "municipios_decretaram", "valor": 749, "variacao": 69,
         "fonte": "Defesa Civil nacional, no Diário Oficial da União"},
        {"id": "populacao_sob_decreto", "valor": 21547599, "variacao": 1500000},
        {"id": "reconhecidos_pelo_governo_federal", "valor": 670, "variacao": 58},
        {"id": "municipios_alerta_cemaden", "valor": 14, "referencia": "02/10/2026 11:22"},
        {"id": "municipios_aviso_inmet", "valor": 2876},
        {"id": "decreto_e_alerta_ao_mesmo_tempo", "valor": 333}]}
    SAU = {"cartoes": [
        {"id": "dengue_casos_se", "valor": 8146, "referencia": "2026-33",
         "fonte": "Ministério da Saúde (Sinan)"},
        {"id": "srag_internacoes_se", "valor": 4267, "referencia": "2026-35"},
        {"id": "uf_dengue_alerta", "valor": 3}]}
    FIN = {"cartoes": [
        {"id": "pago_periodo_mp", "valor": 150887172.93, "periodo": "mês de setembro de 2026",
         "fonte": "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)"},
        {"id": "resposta_liberado_semana", "valor": 0, "periodo": "últimos 7 dias",
         "detalhe": "nenhuma portaria de resposta publicada nos últimos 7 dias"},
        {"id": "atos_federais_semana", "valor": 0, "periodo": "últimos 7 dias"}]}
    RIS = {"cartoes": [{"id": "temperatura_desvio_capital", "valor": 2.9, "capital": "Belém"},
                       {"id": "capitais_ar_ruim_ou_pior", "valor": 11}]}

    emerg = cartoes_das_emergencias(DC)
    checar("emergências publicam a SEMANA, não o acumulado do ciclo",
           [c["valor"] for c in emerg] == [69, 1500000, 58])
    checar("todo cartão importado declara a página de origem",
           all(c["pagina_de_origem"] == "defesa-civil.html" for c in emerg))
    risco = cartoes_do_risco_agora(DC, RIS, {"uf": {"PA": {"fogo": {"focos_24h": 9, "consultado_em": "x"}}}})
    checar("risco agora tem seis cartões", len(risco) == 6)
    checar("o calor da imprensa é o DESVIO, e vem do Monitor de riscos",
           risco[4]["valor"] == 2.9 and risco[4]["pagina_de_origem"] == "monitor-de-riscos.html")
    din = cartoes_do_dinheiro_importados(FIN, {"municipios_com_ato": 68})
    checar("o dinheiro deixa de ser 'sem dado': ele vem do Financiamento",
           din[0]["valor"] == 150887172.93 and not din[0]["sem_coleta"])
    checar("o recorte do dinheiro é o da fonte, dito no cartão",
           "setembro" in (din[0]["referencia"] or ""))
    checar("zero autorizado na semana é ZERO, não sem dado",
           din[1]["valor"] == 0 and din[1]["sem_coleta"] is False)
    sau = cartoes_da_saude_importados(SAU)
    checar("a dengue da imprensa é a do MARÉ Saúde, na mesma semana",
           sau[0]["valor"] == 8146 and "33" in sau[0]["rotulo"])
    checar("as respiratórias não vêm dobradas", sau[1]["valor"] == 4267)
    checar("cartão sem valor no instantâneo vira sem_coleta, nunca zero",
           cartoes_da_saude_importados({"cartoes": [{"id": "dengue_casos_se", "sem_coleta": True}]})[0]["sem_coleta"] is True)
    checar("fonte em linguagem de leitor",
           din[0]["fonte"] == "Portal da Transparência"
           and sau[0]["fonte"] == "Ministério da Saúde (Sinan)")

    # ── a edição montada ────────────────────────────────────────────────────────────────────
    CARTOES_DO_TESTE = montar(corte)["cartoes"]
    checar("todo cartão declara o grupo em que aparece na página",
           all(c.get("grupo") in ("preparacao", "emergencias", "risco_agora", "dinheiro",
                                  "saude") for c in CARTOES_DO_TESTE))
    checar("os cinco grupos existem na edição",
           {c["grupo"] for c in CARTOES_DO_TESTE} == {"preparacao", "emergencias", "risco_agora",
                                                      "dinheiro", "saude"})
    for grupo, quantos in (("preparacao", 3), ("emergencias", 3), ("risco_agora", 6),
                           ("dinheiro", 3), ("saude", 3)):
        checar(f"o grupo '{grupo}' tem {quantos} cartões",
               sum(1 for c in CARTOES_DO_TESTE if c["grupo"] == grupo) == quantos)
    checar("cartão sem par não inventa variação",
           all(c["variacao"] is None for c in CARTOES_DO_TESTE if c["primeira_medicao"]))
    checar("a edição lista o que ficou sem dado",
           isinstance(montar(corte)["sem_dado_nesta_edicao"], list))

    # ── o release ───────────────────────────────────────────────────────────────────────────
    cs = [{"id": "planos_na_semana", "valor": 0, "sem_coleta": False, "variacao": None},
          {"id": "decretos_na_semana", "valor": 1, "sem_coleta": False, "variacao": None},
          {"id": "populacao_decretos_na_semana", "valor": 1500000, "sem_coleta": False, "variacao": None},
          {"id": "mudaram_faixa", "valor": 2, "sem_coleta": False, "variacao": None},
          {"id": "capitais_com_plano", "valor": 17, "sem_coleta": False, "variacao": None}]
    rel = texto_pronto(cs, {"edicao": "02/10/2026", "mare_legal": 24.4, "mare_saude": 31.8,
                            "saude_verificadas": 21, "decretaram_no_ciclo": 749})
    checar("o release escreve zero por extenso", "nenhum município publicou plano" in rel)
    checar("o release concorda no singular", "1 município decretou" in rel)
    checar("o release arredonda a população", "1,5 milhão" in rel)
    checar("o release diz quantos estados a média da saúde cobre",
           "média dos 21 estados verificados" in rel)
    checar("o release traz a assinatura da Futura", "Futura Evidence Lab" in rel)
    rel_vazio = texto_pronto([{"id": "planos_na_semana", "valor": None, "sem_coleta": True}], {})
    checar("frase sem dado é omitida", "plano" not in rel_vazio)

    # ── a planilha da edição ────────────────────────────────────────────────────────────────
    linhas = linhas_da_planilha({"cartoes": [
        {"id": "x", "grupo": "dinheiro", "rotulo": "R", "valor": 10, "variacao": 2,
         "referencia": "mês de setembro de 2026", "fonte": "F", "url_fonte": "u",
         "consultado_em": "02/10/2026", "sem_coleta": False},
        {"id": "y", "grupo": "saude", "rotulo": "S", "valor": None, "sem_coleta": True,
         "variacao": None, "fonte": "G"}]})
    checar("a planilha tem as oito colunas do handover", list(linhas[0]) == list(COLUNAS_CSV))
    checar("a planilha traz valor e variação", linhas[0]["valor"] == 10 and linhas[0]["variação"] == 2)
    checar("a planilha mostra a lacuna, em vez de omitir a linha",
           linhas[1]["valor"] == "" and linhas[1]["referência"] == "sem dado nesta edição")

    # Os não calculáveis precisam DIZER por quê — senão viram silêncio.
    checar("todo não calculável declara o motivo",
           all(x.get("por_que_nao") for x in NAO_CALCULAVEIS))

    if falhas:
        print(f"\n✗ IMPRENSA SEMANA: {len(falhas)} falha(s).")
        return 1
    print("\n✓ IMPRENSA SEMANA OK — números importados das páginas de origem, cinco grupos "
          "completos, release com concordância e planilha com a lacuna declarada.")
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
    planilha = RAIZ / "dados-abertos" / "imprensa" / f"numeros-{corte.isoformat()}.csv"
    n_linhas = escrever_planilha(r, planilha)
    com_valor = sum(1 for c in r["cartoes"] if not c["sem_coleta"])
    print(f"→ {planilha.relative_to(RAIZ)} gravado · {n_linhas} linha(s).")
    print(f"→ {SAIDA.relative_to(RAIZ)} gravado · {len(r['cartoes'])} cartão(ões), "
          f"{com_valor} com coleta, {len(r['nao_calculaveis'])} não calculável(is) declarado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
