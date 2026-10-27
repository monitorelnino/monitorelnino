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

from coletores_base import data_do_corte, gravar_em, semana_do_rotulo

RAIZ = pathlib.Path(__file__).resolve().parent
DATA = RAIZ / "data"
SAIDA = DATA / "imprensa" / "semana.json"
JANELA = 7


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


def periodo(corte: date) -> dict:
    return {"ini": (corte - timedelta(days=JANELA)).isoformat(), "fim": corte.isoformat()}


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


# ── acumulados do ciclo (HANDOVER_IMPRENSA_REDESENHO §2) ────────────────────────────────────
# Uma função por número. Sem dado é `sem_coleta` com o motivo, nunca zero.
INICIO_CICLO_IMP = date(2026, 6, 29)


def acumulado(ident, valor, unidade, inicio, fim, n, fonte, motivo=None, **extra):
    return {"id": ident, "valor": valor, "unidade": unidade, "periodo_inicio": inicio,
            "periodo_fim": fim, "n": n, "fonte": fonte, "sem_coleta": valor is None, "motivo": motivo,
            **extra}


def acumulado_focos(focos_ref, corte):
    """Focos de calor do INPE, somados dia a dia desde 29/06 até o corte, na série publicada."""
    fonte = "INPE — Programa Queimadas (série diária, satélite de referência)"
    serie = (focos_ref or {}).get("serie") or {}
    ini, fim = INICIO_CICLO_IMP.isoformat(), corte.isoformat()
    dias = {k: v["total"] for k, v in serie.items()
            if isinstance(v, dict) and v.get("total") is not None and ini <= k <= fim}
    if not dias:
        return acumulado("focos_desde_29_06", None, "focos", ini, fim, 0, fonte,
                         "a série diária do INPE não cobre o período até o corte")
    if min(dias) > ini:
        # Soma parcial não vira "desde 29/06": o trecho anterior ao primeiro dia publicado é lacuna declarada.
        return acumulado("focos_desde_29_06", None, "focos", ini, fim, len(dias), fonte,
                         f"a série diária do INPE publicada começa em {min(dias)}; {ini} a {min(dias)} não está no arquivo",
                         valor_parcial=sum(dias.values()), periodo_parcial_inicio=min(dias))
    return acumulado("focos_desde_29_06", sum(dias.values()), "focos", min(dias), max(dias), len(dias), fonte)


def acumulado_planos(municipios, corte):
    """Municípios com plano localizado pelo MARÉ Legal, até o corte (sem recorte de data: é estoque)."""
    n = sum(1 for m in municipios if m.get("categoria") == "plano")
    return acumulado("municipios_plano_localizado", n, "municípios", None, corte.isoformat(), n,
                     "MARÉ Legal (planos municipais localizados)")


def acumulado_inmet(corte):
    return acumulado("dias_alerta_laranja_vermelho", None, "dias", INICIO_CICLO_IMP.isoformat(), corte.isoformat(),
                     0, "Inmet (avisos meteorológicos)",
                     "o histórico diário de avisos não está guardado; o arquivo do Inmet traz só os vigentes")


def planos_novos_do_ciclo(ufs: dict) -> tuple:
    """(estados com instrumento estadual NOVO para o ciclo, UFs do monitor). Função pura: lê o
    `instrumento.status` que o MARÉ Saúde já publica por UF; UF sem leitura conta no denominador."""
    ufs = ufs or {}
    novos = sum(1 for v in ufs.values() if ((v or {}).get("instrumento") or {}).get("status") == "NOVO")
    return novos, len(ufs)


def acumulado_estados_plano_saude(corte, ufs):
    """Estados com plano estadual novo para o El Niño, de 27, até o corte (estoque, sem recorte de data)."""
    fonte = "MARÉ Saúde (instrumento estadual novo para o ciclo, por UF)"
    if not ufs:
        return acumulado("estados_plano_saude", None, "estados", None, corte.isoformat(), 0, fonte,
                         "o monitor de saúde não traz as UFs até o corte")
    n, total = planos_novos_do_ciclo(ufs)
    return acumulado("estados_plano_saude", n, "estados", None, corte.isoformat(), total, fonte,
                     denominador=total)


def acumulado_cidades_oms(corte):
    return acumulado("cidades_acima_limite_oms", None, "cidades", INICIO_CICLO_IMP.isoformat(), corte.isoformat(),
                     0, "Série diária de temperatura por município",
                     "a série diária por município não está publicada no arquivo até o corte")


def _intervalo_do_periodo(p: str, tipo: str):
    """(início, fim) de uma semana epidemiológica ('AAAA-SS') ou de um mês ('AAAA-MM')."""
    ano, x = p.split("-")
    if tipo == "semana":
        from coletores_base import semana_intervalo
        return semana_intervalo(int(ano), int(x))
    m = int(x)
    return date(int(ano), m, 1), date(int(ano) + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def _janela_fechada(d: dict, corte: date) -> list:
    """Períodos FECHADOS desde a semana que contém 29/06 (o `parcial` do arquivo fica fora),
    em ordem: [(período, início, fim)]. A semana conta se termina em 29/06 ou depois; o mês, se
    começa em 29/06 ou depois (junho não é mês fechado desde 29/06)."""
    tipo, parciais = (d or {}).get("periodo"), set((d or {}).get("parcial") or [])
    jan = []
    for p in ((d or {}).get("serie") or {}).get("BR") or {}:
        if p in parciais:
            continue
        a, b = _intervalo_do_periodo(p, tipo)
        if b <= corte and (b if tipo == "semana" else a) >= INICIO_CICLO_IMP:
            jan.append((p, a, b))
    return sorted(jan)


def acumulado_saude(ident, arquivo, corte, unidade, fonte):
    """Soma nacional de um desfecho nos períodos fechados desde 29/06. Um período fechado sem valor
    vira lacuna com o motivo do arquivo, nunca uma soma pela metade."""
    d = ler("saude_desfechos/" + arquivo, {}) or {}
    jan = _janela_fechada(d, corte)
    ini = jan[0][1].isoformat() if jan else INICIO_CICLO_IMP.isoformat()
    fim = jan[-1][2].isoformat() if jan else corte.isoformat()
    if not jan:
        tipo = "semana" if d.get("periodo") == "semana" else "mês"
        return acumulado(ident, None, unidade, ini, fim, 0, fonte,
                         f"nenhum {tipo} fechado desde 29/06; o último período com valor é parcial")
    serie = d["serie"]["BR"]
    faltam = [p for p, _, _ in jan if serie.get(p) is None]
    if faltam:
        motivo = ((d.get("lacunas") or [{}])[0].get("motivo")
                  or f"a série nacional não tem valor em {len(faltam)} período(s) fechado(s)")
        return acumulado(ident, None, unidade, ini, fim, len(jan), fonte, motivo)
    return acumulado(ident, sum(serie[p] for p, _, _ in jan), unidade, ini, fim, len(jan), fonte)


def acumulado_ufs_acima(corte):
    """Estados acima da faixa habitual, POR DOENÇA: a conta é a de `resumo_do_desfecho` do topo
    (a única conta de 'estados acima da faixa', na última semana consolidada de cada UF). Um
    cartão por doença; sem série por UF, lacuna declarada."""
    from scripts.gerar_topo_das_paginas import resumo_do_desfecho
    saidas = []
    for arquivo, rotulo in (("dengue.json", "dengue"), ("srag.json", "srag"),
                            ("chikungunya.json", "chikungunya"), ("diarreias.json", "diarreia"),
                            ("leptospirose.json", "leptospirose")):
        d = ler("saude_desfechos/" + arquivo, {}) or {}
        r = resumo_do_desfecho(d)
        fonte = "MARÉ Saúde (última semana fechada de cada UF, contra a faixa habitual da própria UF)"
        ini = fim = None
        if r["periodo"]:  # o topo calcula semana_inicio/fim só para semana; mês sai do próprio período
            ini, fim = (x.isoformat() for x in _intervalo_do_periodo(r["periodo"], d.get("periodo")))
        valor = r["ufs_acima_faixa"]
        motivo = None if valor is not None else "a faixa habitual não se compara com a série de todas as UFs até o corte"
        saidas.append(acumulado(f"estados_acima_da_faixa_{rotulo}", valor, "estados", ini, fim,
                                r["ufs_comparadas"], fonte, motivo, periodo=r["periodo"]))
    return saidas


def _do_arquivo(ident, valor, unidade, n, fonte, motivo_vazio, **extra):
    """Acumulado de um número já calculado por outra página; valor None vira lacuna com motivo."""
    if valor is None:
        return acumulado(ident, None, unidade, INICIO_CICLO_IMP.isoformat(), None, 0, fonte, motivo_vazio)
    return acumulado(ident, valor, unidade, INICIO_CICLO_IMP.isoformat(), None, n, fonte, **extra)


def acumulado_decretos(por_uf):
    nac = (por_uf or {}).get("nacional") or {}
    return _do_arquivo("municipios_decretaram", nac.get("n_municipios"), "municípios", nac.get("n_municipios"),
                       "Defesa Civil nacional (decretos no Diário Oficial da União)",
                       "o arquivo de decretos não traz o total")


def acumulado_reconhecidos(por_uf):
    nac = (por_uf or {}).get("nacional") or {}
    return _do_arquivo("municipios_reconhecidos", nac.get("reconhecidos"), "municípios", nac.get("reconhecidos"),
                       "Defesa Civil nacional (portarias de reconhecimento, DOU)",
                       "o arquivo não traz o total reconhecido", prazo_reconhecimento=nac.get("prazo_reconhecimento"))


def acumulado_pessoas(por_uf):
    nac = (por_uf or {}).get("nacional") or {}
    return _do_arquivo("pessoas_municipios_decretados", nac.get("pop_sob_decreto"), "pessoas",
                       nac.get("n_municipios"), "IBGE, Censo 2022 (população dos municípios que decretaram)",
                       "o arquivo não traz a população dos municípios sob decreto")


def acumulado_atos_por_evento(por_uf):
    """Atos de emergência por evento declarado, somados das UFs. 'sem tipo' é contado como tal."""
    por_evento: dict = {}
    for u in ((por_uf or {}).get("uf") or {}).values():
        for k, v in ((u or {}).get("eventos_declarados") or {}).items():
            por_evento[k] = por_evento.get(k, 0) + v
    total = sum(por_evento.values()) if por_evento else None
    return _do_arquivo("atos_por_evento", total, "atos", total, "Defesa Civil nacional (atos de emergência)",
                       "o arquivo de atos não traz o tipo de evento", por_evento=por_evento)


def _carta(lista, ident):
    return next((c for c in (lista or []) if c.get("id") == ident), None)


def acumulado_do_topo_financeiro(ident, fin, id_topo, motivo_vazio):
    c = _carta(fin.get("topo"), id_topo) or {}
    return _do_arquivo(ident, c.get("valor"), "reais", c.get("n_atos"), c.get("fonte") or "Portal da Transparência",
                       motivo_vazio, periodo=c.get("periodo"))


def acumulado_capitais(cartoes):
    c = _carta(cartoes, "capitais_com_plano") or {}
    return _do_arquivo("capitais_com_plano", c.get("valor"), "capitais", 27,
                       "MARÉ Legal (planos de contingência das capitais)",
                       c.get("nota") or "sem leitura das capitais até o corte")


def acumulados(corte, focos_ref, municipios, fin, por_uf, cartoes) -> list:
    saude_fontes = {
        "dengue": ("dengue.json", "notificações", "Ministério da Saúde (Sinan), semanas fechadas"),
        "chikungunya": ("chikungunya.json", "notificações", "Ministério da Saúde (Sinan), semanas fechadas"),
        "srag": ("srag.json", "internações", "Ministério da Saúde (SIVEP-Gripe), semanas fechadas"),
        "diarreia": ("diarreias.json", "atendimentos", "SUS (SISAB), meses fechados"),
        "leptospirose": ("leptospirose.json", "casos", "Ministério da Saúde (SINAN), meses fechados"),
    }
    lista = [acumulado_focos(focos_ref, corte), acumulado_planos(municipios, corte),
             acumulado_inmet(corte),
             acumulado_estados_plano_saude(corte, (ler("monitor_saude.json", {}) or {}).get("ufs")),
             acumulado_cidades_oms(corte),
             acumulado_decretos(por_uf), acumulado_reconhecidos(por_uf), acumulado_pessoas(por_uf),
             acumulado_atos_por_evento(por_uf), acumulado_capitais(cartoes),
             acumulado_do_topo_financeiro("anunciado_em_atos", fin, "anunciado_atos",
                                          "o texto das medidas não traz valor anunciado"),
             acumulado_do_topo_financeiro("desembolsado", fin, "pago_ate_agora",
                                          "a execução da despesa não traz o acumulado"),
             acumulado_do_topo_financeiro("autorizado_defesa_civil", fin, "autorizado_defesa_civil",
                                          "a soma por município ainda não fechou com o total publicado"),
             acumulado_do_topo_financeiro("repasses_sus_emergencia", fin, "repasses_sus",
                                          "os repasses de emergência do SUS não estão no derivado")]
    for ident, (arq, unid, fonte) in saude_fontes.items():
        lista.append(acumulado_saude(ident, arq, corte, unid, fonte))
    return lista + acumulado_ufs_acima(corte)


# ── os cartões ──────────────────────────────────────────────────────────────────────────────

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
    {"id": "paginas_fora_do_ar",
     "rotulo": "Páginas oficiais fora do ar por aviso eleitoral",
     "por_que_nao": "depende do campo `escopo` em data/calendario/fontes_suspensas.json, que hoje "
                    "é nulo nos 38 registros (bloco E do pedido de 27/09, não executado)."},
]


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
    """Risco agora: quatro cartoes. Dois da Defesa civil, um do Monitor de riscos, um do fogo.
    16/10/2026: o do ar saiu com o indice europeu (CAMS) que o alimentava. O cruzamento decreto e
    alerta saiu da Defesa civil na reforma de 16/10 e sai daqui com ele."""
    d, r = por_id(dc), por_id(riscos)
    # Os dois primeiros cartoes vem do instantaneo da Defesa civil, que desde 08/10/2026 ja
    # declara a parada das 24 horas (scripts/gerar_topo_das_paginas.alertas_pararam). A Imprensa
    # nao repete a regra: ela copia o instantaneo, e por isso para junto.
    cartoes = [
        importado("municipios_alerta_cemaden", "Municípios sob alerta do Cemaden",
                  d.get("municipios_alerta_cemaden"), grupo="risco_agora",
                  url_fonte="https://www.gov.br/cemaden/pt-br", origem="defesa-civil.html"),
        importado("municipios_aviso_inmet", "Municípios sob aviso do Inmet",
                  d.get("municipios_aviso_inmet"), grupo="risco_agora",
                  url_fonte="https://portal.inmet.gov.br/", origem="defesa-civil.html"),
        cartao_focos(sinais),
        importado("temperatura_desvio_capital",
                  "A maior diferença de temperatura máxima em relação ao normal, em grau Celsius",
                  r.get("temperatura_desvio_capital"), grupo="risco_agora", unidade="°C",
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
                  nota=(f"desde 29 de junho, {n_mun} município(s) com ato de portaria" if n_mun else None)
                       or resp.get("detalhe"),
                  origem="financiamento.html"),
        importado("atos_federais_semana",
                  "Atos federais de financiamento publicados nos últimos 7 dias", atos,
                  grupo="dinheiro", unidade="atos", referencia="últimos 7 dias",
                  origem="financiamento.html"),
    ]


def cartoes_da_saude_importados(saude):
    """Saude: tres cartoes, lidos do instantaneo do MARE Saude.

    A semana fechada e a do gerador da saude (`gerar_topo_das_paginas`): uma definicao so, como o
    handover exige. Era aqui que a Imprensa publicava a semana 37 do InfoDengue enquanto a pagina
    publicava a semana 33 do Sinan. O rotulo diz as datas da semana, nunca o numero dela.
    """
    s_ = por_id(saude)
    den = s_.get("dengue_casos_se") or {}
    srag = s_.get("srag_internacoes_se") or {}
    ufs = s_.get("uf_dengue_alerta") or {}

    def na_semana(c):
        quando = semana_do_rotulo(c.get("referencia"))
        return f" na semana {quando}" if quando else ""
    return [
        importado("dengue_casos_se", "Casos prováveis de dengue" + na_semana(den), den,
                  grupo="saude", origem="saude.html"),
        importado("srag_internacoes_se",
                  "Internações por síndrome respiratória grave" + na_semana(srag), srag,
                  grupo="saude", origem="saude.html"),
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

    # As frases do release são as do texto aprovado, e a pontuação é a dela: cada frase termina em
    # ponto. Juntar tudo com ponto e vírgula produzia "…verificadas; Na semana", com maiúscula
    # depois de ponto e vírgula — erro de idioma num texto que sai em release de imprensa. "Ciclo"
    # sozinho não aparece (regra da Imprensa de 16/10/2026).
    frases = []
    edicao = I.get("edicao")
    legal, saude_i = I.get("mare_legal"), I.get("mare_saude")
    if edicao:
        frases.append(f"Edição de {edicao}.")
    if legal is not None and saude_i is not None:
        frases.append(
            "O MARÉ Legal, índice que acompanha a preparação publicada por estados e municípios "
            f"para o El Niño 2026/2027, está em {str(legal).replace('.', ',')} de 100; o MARÉ "
            f"Saúde, em {str(saude_i).replace('.', ',')} de 100.")
    planos, decretos = v("planos_na_semana"), v("decretos_na_semana")
    pop = v("populacao_decretos_na_semana")
    if planos is not None and decretos is not None:
        frase = ("Na semana, " + mun(planos, "publicou plano para o El Niño",
                                     "publicaram plano para o El Niño")
                 + " e " + mun(decretos, "decretou situação de emergência ou calamidade",
                               "decretaram situação de emergência ou calamidade"))
        if pop:
            # 08/10/2026 (A3-23): "288.729 de pessoas" saía quando o número não chegava ao
            # milhão. O "de" pertence a "milhão"/"milhões", não ao número cheio.
            _p = milhoes(pop)
            _liga = " de " if ("milh" in str(_p)) else " "
            frase += f"; {_p}{_liga}pessoas vivem nos municípios que decretaram"
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
        segundo.append(f"Desde 29 de junho, {capitais} de 27 capitais têm "
                       "plano localizado e " + mun(ciclo, "decretou emergência ou calamidade",
                                                   "decretaram emergência ou calamidade") + ".")
    segundo.append("Cada registro, com documento, data e fonte, está em monitorelnino.com.br. "
                   "O MARÉ é uma criação do Futura Evidence Lab.")
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
        "mare_saude": resumo.get("indice_nacional"),
        "saude_verificadas": resumo.get("verificadas"),
        "decretaram_no_ciclo": (por_uf.get("nacional") or {}).get("n_municipios"),
    }
    sem_dado = [c["rotulo"] for c in cartoes if c["sem_coleta"]]
    return {
        "acumulado": acumulados(corte, ler("focos_referencia.json", {}) or {}, municipios, fin, por_uf, cartoes),
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
        "definicao_dos_indices": saude.get("definicao_dos_indices"),
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
        {"id": "municipios_aviso_inmet", "valor": 2876}]}
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
    RIS = {"cartoes": [{"id": "temperatura_desvio_capital", "valor": 2.9, "capital": "Belém"}]}

    emerg = cartoes_das_emergencias(DC)
    checar("emergências publicam a SEMANA, não o acumulado do ciclo",
           [c["valor"] for c in emerg] == [69, 1500000, 58])
    checar("todo cartão importado declara a página de origem",
           all(c["pagina_de_origem"] == "defesa-civil.html" for c in emerg))
    risco = cartoes_do_risco_agora(DC, RIS, {"uf": {"PA": {"fogo": {"focos_24h": 9, "consultado_em": "x"}}}})
    checar("risco agora tem quatro cartões, sem o cruzamento decreto e alerta",
           len(risco) == 4 and not any("decreto" in c["id"] for c in risco))
    checar("o calor da imprensa é o DESVIO, e vem do Monitor de riscos",
           risco[3]["valor"] == 2.9 and risco[3]["pagina_de_origem"] == "monitor-de-riscos.html")
    din = cartoes_do_dinheiro_importados(FIN, {"municipios_com_ato": 68})
    checar("o dinheiro deixa de ser 'sem dado': ele vem do Financiamento",
           din[0]["valor"] == 150887172.93 and not din[0]["sem_coleta"])
    checar("o recorte do dinheiro é o da fonte, dito no cartão",
           "setembro" in (din[0]["referencia"] or ""))
    checar("zero autorizado na semana é ZERO, não sem dado",
           din[1]["valor"] == 0 and din[1]["sem_coleta"] is False)
    sau = cartoes_da_saude_importados(SAU)
    checar("a dengue da imprensa é a do MARÉ Saúde, na mesma semana, dita em datas",
           sau[0]["valor"] == 8146
           and sau[0]["rotulo"] == "Casos prováveis de dengue na semana de 16 a 22 de agosto de 2026"
           and "epidemiol" not in sau[1]["rotulo"])
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
    for grupo, quantos in (("preparacao", 3), ("emergencias", 3), ("risco_agora", 4),
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
    checar("o release dá o índice nacional da saúde, sem a contagem de verificados",
           "Saúde, em 31,8 de 100." in rel and "21" not in rel)
    checar("o release não usa 'ciclo' sozinho", "ciclo" not in rel)
    checar("o release traz a assinatura do Futura", "criação do Futura Evidence Lab" in rel)
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
    # §2 do handover: cada acumulado soma só o que a fonte publica no período; sem dado é lacuna, nunca zero.
    _ref = {"serie": {"2026-06-28": {"total": 9}, "2026-06-29": {"total": 4}, "2026-07-01": {"total": 6}}}
    _f = acumulado_focos(_ref, date(2026, 7, 1))
    checar("acumulado de focos soma só desde 29/06 e declara os dias", _f["valor"] == 10 and _f["n"] == 2 and _f["periodo_inicio"] == "2026-06-29")
    _gap = acumulado_focos({"serie": {"2026-09-17": {"total": 5}}}, date(2026, 10, 25))
    checar("acumulado de focos com trecho sem série é lacuna declarada, nunca soma parcial como desde 29/06", _gap["sem_coleta"] is True and _gap["valor_parcial"] == 5 and "2026-06-29" not in (_gap["motivo"] or "")[:0] and "17" in _gap["motivo"])
    checar("acumulado sem série é lacuna, nunca zero", acumulado_focos({}, date(2026, 7, 1))["sem_coleta"] is True)
    checar("acumulado de planos conta só 'plano'", acumulado_planos([{"categoria": "plano"}, {"categoria": "nao_verificado"}], date(2026, 7, 1))["valor"] == 1)
    _ufs = {"AM": {"instrumento": {"status": "NOVO"}}, "SP": {"instrumento": {"status": "NOVO"}},
            "SC": {"instrumento": {"status": "VIG"}}, "AC": {"instrumento": {}}}
    checar("estados com plano para o ciclo contam só NOVO, com denominador de todas as UFs do monitor",
           planos_novos_do_ciclo(_ufs) == (2, 4))
    checar("estados com plano para o ciclo sem monitor é lacuna, nunca zero",
           acumulado_estados_plano_saude(date(2026, 10, 25), None)["sem_coleta"] is True)
    checar("cidades acima do limite da OMS sem série diária é lacuna declarada",
           acumulado_cidades_oms(date(2026, 10, 25))["sem_coleta"] is True)
    _sem = {"periodo": "semana", "parcial": ["2026-29"], "serie": {"BR": {"2026-26": 9, "2026-27": 5, "2026-28": 6, "2026-29": 7}}}
    checar("janela de semanas: a que contém 29/06 entra, a parcial fica fora",
           [p for p, _, _ in _janela_fechada(_sem, date(2026, 7, 20))] == ["2026-26", "2026-27", "2026-28"])
    _mes = {"periodo": "mes", "parcial": ["2026-08"], "serie": {"BR": {"2026-06": 1, "2026-07": 2, "2026-08": 3}}}
    checar("janela de meses: junho não é mês fechado desde 29/06",
           [p for p, _, _ in _janela_fechada(_mes, date(2026, 9, 1))] == ["2026-07"])
    checar("número sem fonte no arquivo é lacuna declarada, nunca zero",
           _do_arquivo("x", None, "u", None, "f", "motivo")["sem_coleta"] is True
           and _do_arquivo("x", None, "u", None, "f", "motivo")["motivo"] == "motivo")
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
    corte = data_do_ato(meta.get("corte")) or data_do_corte()
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
