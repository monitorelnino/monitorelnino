#!/usr/bin/env python3
"""Cálculo canônico do índice MARÉ v3.0 — Monitor El Niño Brasil.

v3.0 (04/09/2026, decisão editorial; Metodologia §30): o componente estadual passa a ser
a média de DOIS sub-elementos com peso igual — ESTRUTURA DE COORDENAÇÃO (comitê, gabinete,
sala de situação, COE criados ou ativados para o ciclo) e INSTRUMENTO OPERACIONAL (plano,
protocolo, decreto preventivo). Cada um usa a escada ESTADO_SCORE. A cobertura municipal ganha
a categoria `estrutura` (comitê/gabinete municipal nomeado para o ciclo, ou COMPDEC ativada por
ato datado — nunca a COMPDEC genérica), crédito 0,45 = paridade com plano_elaboracao.

Reproduz integralmente os 27 valores publicados em data/indice.json a partir de
data/municipios.json, data/percentual_uf.json, data/municipios_ibge_referencia.json
e data/populacao_censo2022.json (Censo 2022 validado por atualizar_populacao.py).

Fórmula (Metodologia §5, §5.2.1 e §12.4.2-3; reestruturação populacional 27/08/2026;
régua de antecipação formalizada — teste do objeto — em 27/08/2026, sem mudança numérica):
  • 3 componentes, pesos iguais (1/3): instrumento estadual, cobertura populacional, antecipação.
  • Cobertura populacional = Σ(população_município × crédito_da_categoria) ÷ população_UF × 100 (teto 100)
      crédito (CRED_POP, escala do antigo componente capital generalizada):
        plano 1,0 · plano_antigo 0,6 · plano_elaboracao 0,45 · coberto_estadual 0,3 · nao_localizado 0
        decreto: 0 (Correção B) · nao_el_nino: 0 — desvio DELIBERADO do §12.4.2 (que herdaria 0,1):
        o vocabulário OBRIGATÓRIO manda "NUNCA conta como preparação p/ El Niño"; generalizar o 0,1
        da capital dava ao AP 2,6 pontos de cobertura por emergência sanitária (achado na simulação
        de 27/08/2026). Regra de hierarquia: vocabulário > escala derivada.
      agregado sem lista nominal (RO 38 planos): excedente × população municipal MEDIANA da UF × crédito
      camada declarada sem lista nominal (desconto de 50% sobre o crédito), mesmo estimador de mediana:
        excedente_declarado_plano × mediana × 0,5 + declarado_antigo × mediana × 0,3
      município pós-Censo (Boa Esperança do Norte/MT, instalado 2025): população 0 sob a safra
        censitária — seus habitantes estão contidos nos municípios-mãe; jamais imputar.
  • O status da capital permanece verificado e exibido EDITORIALMENTE (card de detalhe);
    aritmeticamente a capital vale sua fração populacional real, como qualquer município (§12.4.2).
  • Agregação: linear (manchete) + geométrica com piso 5 (tooltip).
  • Sensibilidade: Monte Carlo 10.000 × Dirichlet(1,1,1), semente 42; intervalo de posições p5–p95.

Uso:
  python recalcular_mare.py --check   # compara com data/indice.json; falha se divergir (padrão)
  python recalcular_mare.py --write   # regrava data/indice.json
"""
import json, re, pathlib, sys

from coletores_base import gravar_em  # §229: escrita atômica de data/
import numpy as np

RAIZ = pathlib.Path(__file__).parent
# 24/09/2026 (§200): plano_antigo passa de 0,7 a 1,0 aqui também. Este dicionário serve a duas
# coisas: como CONJUNTO de pertinência no motor (`k in PESO_DOC`, onde os valores não entram na
# conta) e como PESO de verdade em analise_sensibilidade.py, no cálculo de `teto_ativo` — a
# checagem de quais UFs estourariam o teto de 100%. Deixar 0,7 aqui depois que o §196 levou o
# crédito real a 1,0 fazia a checagem de teto subestimar, e deixava no código um número que
# contradizia a regra vigente: a próxima sessão leria 0,7 e concluiria que plano anterior vale
# menos. Vale igual, e agora está escrito igual nos dois lugares.
PESO_DOC = {"plano": 1.0, "plano_antigo": 1.0,
            # §202: a escada municipal. Os pesos aqui acompanham CRED_POP — este dicionário
            # também serve de peso no cálculo de teto_ativo (ver §200).
            "plano_novo": 1.0, "plano_readaptado": 0.65, "plano_recorrente": 0.45}  # Correção B (26/08/2026): "decreto" removido —
# não é purga pontual de dado, é regra estrutural. Sem isto, um decreto novo achado pela busca
# automática de segunda-feira (ou por contribuição de leitor) voltaria a pontuar 0,4 por registro,
# desfazendo a Correção B sozinho a cada atualização. `k in PESO_DOC` nas linhas abaixo já basta
# para excluir decreto de w, doc_n e do excedente agregado — nenhuma outra mudança necessária.
ESTADO_SCORE = {"NOVO": 100, "READ": 65, "VIG": 45, "ELAB": 35, "LAC": 0}
# Crédito populacional por categoria (v2.2). Origem: escala do componente capital
# da v2.1 (÷100), generalizada pelo §12.4.2 — com o desvio documentado de
# nao_el_nino (0, não 0,1; ver docstring). decreto ausente por regra estrutural
# (Correção B): `CRED_POP.get(cat, 0.0)` já o exclui sem lista de exceções.
# 24/09/2026 (§196, decisão editorial que emenda o C6): plano vigente de ciclo anterior passa a
# contar INTEGRAL. A régua deixa de perguntar QUANDO o plano foi publicado e passa a perguntar se ele
# EXISTE e se está vigente — plano vigente é plano vigente. O tipo (novo do ciclo, readaptado,
# vigente-recorrente) continua distinguido no banco e à vista no site, como descrição, e deixa de ser
# desconto. Efeito medido antes de aplicar, e declarado no CHANGELOG.
# ESCADA MUNICIPAL (§202, 24/09/2026, decisão da editoria que emenda o C6). Até aqui o município
# tinha "plano" e pronto: um instrumento feito para o El Niño valia o mesmo que uma operação de verão
# que roda todo ano. A escada dos ESTADOS já distinguia — NOVO 100 · READ 65 · VIG 45 (§30) —, e esta
# entrada leva a mesma régua ao município, nas mesmas proporções.
#
#   plano_novo        1.00  instrumento criado PARA o ciclo / dedicado ao El Niño
#   plano_readaptado  0.65  instrumento preexistente reativado ou readaptado para o ciclo, por ato datado
#   plano_recorrente  0.45  rotina sazonal que roda todo ano com ou sem El Niño (plano de verão, operação chuva)
#
# DUAS DECISÕES DE DESENHO, declaradas porque mudam o que o número significa:
#
# 1. `plano` continua valendo 1,00 e passa a significar "localizado, TIPO NÃO DETERMINADO". Não se
#    desconta município porque NÓS ainda não lemos o documento dele: ausência de verificação nunca é
#    ausência de documento (v2.2.4, §2.1), e lacuna nossa não vira nota deles. O tipo se resolve
#    lendo, um a um, e cada reclassificação é R7.
# 2. `plano_antigo` FICA em 1,00. O §196, de hoje, decidiu que plano vigente de ciclo anterior conta
#    integral; sob a escada ele cairia para 0,45, que é o oposto. Reverter uma decisão da editoria por
#    reinterpretação seria trocar o juízo dela pelo meu. Ele só se move com o documento na mão
#    mostrando que é rotina recorrente — e aí vira `plano_recorrente`, com a prova junto.
#
# CONSEQUÊNCIA, dita antes de acontecer: aplicar esta escada tende a BAIXAR o índice conforme os
# documentos forem lidos, não a subir. É o resultado correto — operação de verão anual não é resposta
# ao El Niño —, e ele chega aos poucos, na velocidade da leitura.
CRED_POP = {"plano": 1.0, "plano_antigo": 1.0,
            "plano_novo": 1.0, "plano_readaptado": 0.65, "plano_recorrente": 0.45, "plano_elaboracao": 0.45,
            # v3.0: estrutura de coordenação nomeada para o ciclo — compromisso formal sem instrumento
            # operacional; paridade declarada com plano_elaboracao (§30). O crédito é o MAIOR, nunca a soma.
            "estrutura": 0.45,
            "coberto_estadual": 0.3, "nao_el_nino": 0.0, "nao_localizado": 0.0,
            # v2.2.4 (§2.1): ausência de verificação ≠ ausência de documento; mesmo crédito 0.0
            "nao_verificado": 0.0}
AGREGADOS = {"RO": (38, "plano")}  # Correção B (26/08/2026): agregados tipo decreto (PB, RN) excluídos do índice — atos de resposta, nunca ex-ante
CAPITAIS = {"Rio Branco":"AC","Maceió":"AL","Manaus":"AM","Macapá":"AP","Salvador":"BA","Fortaleza":"CE",
 "Brasília":"DF","Vitória":"ES","Goiânia":"GO","São Luís":"MA","Cuiabá":"MT","Campo Grande":"MS",
 "Belo Horizonte":"MG","Belém":"PA","João Pessoa":"PB","Curitiba":"PR","Recife":"PE","Teresina":"PI",
 "Rio de Janeiro":"RJ","Natal":"RN","Porto Alegre":"RS","Porto Velho":"RO","Boa Vista":"RR",
 "Florianópolis":"SC","São Paulo":"SP","Aracaju":"SE","Palmas":"TO"}

# (status do INSTRUMENTO OPERACIONAL, antecipação, confiança) — insumos de julgamento da verificação,
# datados no banco de registros; régua de antecipação na Metodologia §5.2.
# v3.0: o status aqui é o do instrumento operacional (plano/protocolo/decreto preventivo); a
# estrutura de coordenação está em ESTRUTURA, abaixo. Componente estadual = média dos dois.
ESTADOS = {
 "AC":("ELAB",100,"Alta"),  "AL":("ELAB",30,"Média"),   "AM":("NOVO",100,"Média"),
 "AP":("VIG",40,"Média"),    "BA":("ELAB",20,"Média"), "CE":("VIG",40,"Média"),
 "DF":("VIG",40,"Média"),   "ES":("VIG",30,"Baixa"),  "GO":("NOVO",30,"Média"),
 "MA":("READ",100,"Média"),"MG":("VIG",20,"Baixa"),  "MS":("READ",100,"Média"),
 "MT":("NOVO",100,"Média"),"PA":("READ",30,"Alta"),   "PB":("LAC",10,"Alta"),
 "PE":("ELAB",20,"Média"), "PI":("VIG",40,"Média"),  "PR":("NOVO",100,"Alta"),
 "RJ":("VIG",30,"Baixa"),  "RN":("LAC",10,"Alta"),   "RO":("READ",40,"Alta"),
 "RR":("VIG",40,"Alta"),   "RS":("READ",100,"Alta"), "SC":("NOVO",100,"Alta"),
 "SE":("NOVO",30,"Média"),   "SP":("VIG",40,"Baixa"),  "TO":("READ",40,"Média"),
}

# v3.0 — ESTRUTURA DE COORDENAÇÃO por UF (§30), julgada pela FUNÇÃO do ato, não pelo nome:
#   NOVO = órgão/instância criado para o ciclo por ato do Executivo (comitê, gabinete, sala de situação),
#          OU plano do ciclo que institui níveis de mobilização e responsáveis (SC);
#   READ = estrutura permanente ativada/re-instituída/designada para o ciclo por ato datado;
#   VIG  = ativação recorrente anual (plano de verão/operação sazonal que mobiliza o sistema todo ano);
#   LAC  = nenhum ato do ciclo toca a estrutura (estrutura permanente sem ato = 0, como a COMPDEC genérica).
# Fontes e datas de cada julgamento: data/estados.json (campo estrutura) e log_buscas (04/09/2026).
ESTRUTURA = {
 "AC":"READ","AL":"NOVO","AM":"READ","AP":"LAC","BA":"LAC","CE":"LAC","DF":"READ","ES":"VIG","GO":"NOVO",
 "MA":"VIG","MG":"VIG","MS":"READ","MT":"NOVO","PA":"READ","PB":"LAC","PE":"LAC","PI":"LAC","PR":"READ",
 "RJ":"VIG","RN":"LAC","RO":"VIG","RR":"VIG","RS":"READ","SC":"NOVO","SE":"NOVO","SP":"VIG","TO":"VIG",
}
# ---------------------------------------------------------------------------------------------
# v3.1 (30/09/2026, decisão da editoria) — a régua do INSTRUMENTO, sem componente temporal
# ---------------------------------------------------------------------------------------------
# O que muda, e por quê (razões aprovadas pela editoria; entram na METODOLOGIA):
#
# 1. O TEMPO SAI DA NOTA. A régua de antecipação (§5.2.1) deixa de ser componente e vira indicador
#    publicado à parte. Publicar cedo não é atributo do arcabouço — a lei exige plano existente e
#    atualizado, não antecedência; é atributo de conduta, e como tal se reporta, não se pontua. O
#    corte de 30 dias e a âncora nacional única eram convenções não sustentáveis (a janela real
#    difere por região, limitação já registrada em E5d), e a correlação 0,56 entre "estadual" e
#    "antecipação" (E4) mostrava dupla contagem.
# 2. TRÊS COMPONENTES, um terço cada, sem sobreposição: instrumento operacional estadual (escala
#    abaixo), estrutura de coordenação (ESTADO_SCORE, como está) e cobertura populacional (como
#    está). A estrutura sai de dentro do componente estadual, onde desde 04/09 entrava como metade,
#    e passa a valer por si.
# 3. ESCALA DO INSTRUMENTO com espaçamento por razão declarada — não é espaçamento igual nem
#    elicitação; a editoria escolheu entre as três em 30/09/2026 e declarou a razão de cada degrau.
#
# O degrau de um recorrente depende de duas coisas que estão no banco, não de opinião:
#   • CONSIST (data/consist.json), que diz se o instrumento cobre o risco projetado do ciclo;
#   • "atualizado", definição operacional: revisão, reedição ou ato de ativação com data em 2026.
INSTRUMENTO_SCORE_V31 = {
    "NOVO": 100,          # plano feito para o El Niño — referência
    "READ": 70,           # readaptado para o ciclo: atualizar é quase equivalente a fazer novo;
                          # a diferença é de especificidade, não de conduta
    "VIG_ATUALIZADO": 55, # recorrente que cobre o risco E tem revisão/ativação datada em 2026
    "VIG": 30,            # recorrente que cobre (ou é neutro), sem revisão datada em 2026 —
                          # o salto grande é entre plano vivo e plano parado
    "ELAB": 20,           # anúncio sem instrumento
    "VIG_NAO_COBRE": 0,   # plano para OUTRO risco não é preparação para este ciclo (caso MG)
    "LAC": 0,
}

# "Atualizado" por UF: o documento e a data que sustentam o julgamento, lidos de data/estados.json
# em 30/09/2026 e registrados aqui porque a régua tem de ser auditável sem reler o banco inteiro.
# Só entram UFs VIG — nas outras a pergunta não se coloca.
#
# Um recorrente sem ato datado em 2026 NÃO é rebaixado por suspeita: ele cai no degrau 30, que é o
# degrau do "plano parado", e a razão fica escrita. Quando o ato aparecer, sobe.
VIG_ATUALIZADO_EM_2026 = {
    "DF": "Decreto nº 48.599/2026, DODF de 15/05/2026 — ativa o PPCIF contra incêndios florestais",
    "PI": "Antecipação de ações (PAA/PAS/Garantia-Safra), instrumento datado de 2026",
}
# Registrado por simetria: as VIG sem ato datado em 2026, com o que o banco traz no lugar.
VIG_SEM_REVISAO_2026 = {
    "AP": "PPCDAP com vigência atualizada para 2026–2030, mas sem ato de revisão datado em 2026; "
          "comitê de estiagem é de 2024",
    "CE": "Monitoramento + Comitê de Segurança Hídrica, registrados como recorrentes, sem data",
    "ES": "Plano de verão/chuvas, ciclo anual, sem data",
    "MG": "Plano de verão/chuvas, ciclo anual, sem data — e CONSIST=DIFERE",
    "RJ": "Plano de verão/chuvas, ciclo anual, sem data",
    "RR": "Operação Verão Sem Fogo, ciclo nov–abr, sem data. O Gabinete Integrado noticiado em "
          "02/09/2026 é pista sem ato localizado, e é de estrutura, não de instrumento",
    "SP": "Plano de verão/chuvas, ciclo anual, sem data",
}
# CONSIST que reprovam um recorrente: o instrumento trata de outro risco.
CONSIST_NAO_COBRE = ("DIFERE",)

# Boletim nº 1 do ciclo — âncora do INDICADOR de antecedência (não mais do componente).
BOLETIM_1 = "29/06/2026"


def _consist():
    """{uf: categoria} de data/consist.json. Vazio se o arquivo não existe."""
    p = RAIZ / "data" / "consist.json"
    if not p.exists():
        return {}
    d = json.load(open(p, encoding="utf-8"))
    d = d.get("ufs", d)
    return {u: (v or {}).get("cat") for u, v in d.items() if isinstance(v, dict)}


def degrau_do_instrumento(uf: str, status: str, consist: dict) -> str:
    """O degrau da escala v3.1 para o instrumento operacional da UF. Função pura.

    Só os recorrentes (VIG) dependem de CONSIST e de revisão datada; os outros degraus são o
    próprio status. Um VIG que não cobre o risco do ciclo vale 0 — decisão da editoria."""
    if status != "VIG":
        return status
    if consist.get(uf) in CONSIST_NAO_COBRE:
        return "VIG_NAO_COBRE"
    return "VIG_ATUALIZADO" if uf in VIG_ATUALIZADO_EM_2026 else "VIG"


def score_instrumento_v31(uf: str, consist: dict) -> int:
    """Pontos do instrumento operacional na v3.1. Função pura."""
    return INSTRUMENTO_SCORE_V31[degrau_do_instrumento(uf, ESTADOS[uf][0], consist)]


def dias_apos_boletim_1(data_do_ato: str, boletim: str = BOLETIM_1):
    """Dias entre o Boletim nº 1 e o primeiro ato datado da UF; negativo se anterior. Função pura.

    Devolve None quando não há data COMPLETA — mês solto ("08/2026"), "Recorrente", intervalo ou
    travessão não viram número. Lacuna declarada é melhor do que dia inventado: a diferença entre
    "publicou em agosto" e "publicou em 28/08" é exatamente o que este indicador mede."""
    import datetime
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", str(data_do_ato or "").strip())
    if not m:
        return None
    b = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", boletim)
    try:
        ato = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        ref = datetime.date(int(b.group(3)), int(b.group(2)), int(b.group(1)))
    except ValueError:
        return None
    return (ato - ref).days


def _datas_dos_atos():
    """{uf: data do instrumento operacional} lida de data/estados.json. Vazio se não existir."""
    p = RAIZ / "data" / "estados.json"
    if not p.exists():
        return {}
    fora = {}
    for u in json.load(open(p, encoding="utf-8")).get("ufs", []):
        instr = [i for i in (u.get("instrumentos") or [])
                 if i.get("tipo") == "instrumento_operacional"]
        fora[u["uf"]] = (instr[0].get("data") if instr else None) or u.get("data")
    return fora


PESO_ESTRUTURA = 0.5   # v3.0: peso igual entre estrutura e instrumento operacional (padrão da casa; sensibilidade 30/70–50/50 sem troca de faixa, §30)


def score_estado(uf: str) -> float:
    """Componente estadual v3.0 = média ponderada (PESO_ESTRUTURA) de estrutura e instrumento operacional."""
    st = ESTADOS[uf][0]
    return PESO_ESTRUTURA * ESTADO_SCORE[ESTRUTURA[uf]] + (1 - PESO_ESTRUTURA) * ESTADO_SCORE[st]


def excedente_agregado(uf, c):
    """Excesso do agregado estadual sobre o que já está contado individualmente
    (mesma regra usada nos dois lugares: score de cobertura E percentual_uf —
    fonte única, para as duas contagens nunca mais poderem divergir). 'c' é a
    contagem por categoria de um único UF. Devolve (tipo_do_agregado, excedente)
    ou (None, 0) se a UF não tem agregado.

    Correção B (26/08/2026, achada pelo teste de estresse formal da Metodologia
    §12.1 — "27 UFs decretando simultaneamente devem deslocar o MARÉ em exatamente
    zero décimos"): a subtração cruzada de 'decreto' contra um agregado tipo
    'plano' (caso de RO) fazia sentido ANTES da Correção B, quando evitava dupla
    contagem de um município com decreto individual E aggregate plano. Como
    decreto não pontua mais nada, esse termo cruzado só reduzia o crédito do
    agregado sem motivo — um decreto novo em QUALQUER município de RO diminuía
    o score de RO, mesmo sem o decreto em si valer ponto algum. Removido.
    """
    if uf not in AGREGADOS:
        return None, 0
    tot_ag, tipo = AGREGADOS[uf]
    ja = c.get(tipo, 0)
    return tipo, max(tot_ag - ja, 0)


def derivar_percentual_uf(cnt, totais, pct_existente):
    """Deriva total/com_ato/n_plano/n_decreto/pct de cada UF a partir da MESMA
    contagem por categoria ('cnt') usada no cálculo do score de cobertura —
    incluindo o mesmo desconto de sobreposição dos agregados estaduais, para
    que as duas métricas nunca possam divergir uma da outra. Preserva campos de
    levantamento externo (declarado_plano, declarado_antigo, fonte_declarada),
    que vêm de auditorias de TCEs/órgãos estaduais e não são deriváveis daqui.
    Fecha a lacuna que exigia sincronizar percentual_uf.json à mão a cada
    mudança em municipios.json (achada e corrigida em 26/08/2026)."""
    novo = {}
    for uf, total in totais.items():
        c = cnt.get(uf, {})
        n_plano = c.get("plano", 0) + c.get("plano_antigo", 0)
        n_decreto = c.get("decreto", 0)
        tipo_agr, excedente = excedente_agregado(uf, c)
        if tipo_agr == "plano":
            n_plano += excedente
        elif tipo_agr == "decreto":
            n_decreto += excedente
        com_ato = n_plano + n_decreto
        entrada = {"total": total, "com_ato": com_ato,
                   "pct": round(100 * com_ato / total, 2) if total else 0.0,
                   "n_plano": n_plano, "n_decreto": n_decreto}
        antiga = pct_existente.get(uf, {})
        for chave in ("declarado_plano", "declarado_antigo", "fonte_declarada"):
            if chave in antiga:
                entrada[chave] = antiga[chave]
        novo[uf] = entrada
    return novo


def _declarado_nacional_uf():
    """Nº de municípios por UF que DECLARAM plano de contingência (MUNIC 'sim' ou ICM
    variável 8 'sim') em data/declarado_nacional.json. Vazio se o arquivo não existe."""
    p = RAIZ / "data" / "declarado_nacional.json"
    if not p.exists(): return {}
    d = json.load(open(p, encoding="utf-8")).get("municipios", {})
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    uf_por = {str(r["codigo_ibge"]).zfill(7): r["uf"] for r in ref}
    n = {}
    for cod, v in d.items():
        if v.get("munic_plano_contingencia") == "sim" or v.get("icm_var8_plano_contingencia") == "sim":
            uf = uf_por.get(cod)
            if uf: n[uf] = n.get(uf, 0) + 1
    return n

def cobertura_de_uf(uf, c, wpop_uf, mediana, pop_total, dp_tce, da_tce, nacional,
                    n_municipios=None, desconto_plano=0.5):
    """O componente de COBERTURA POPULACIONAL de uma UF. Função pura, e a única.

    08/10/2026 (A3-05). Esta conta existia em dois lugares: aqui, dentro de `calcular`, e copiada
    em `analise_sensibilidade.cobertura`, que alimenta o PDF público "Documentação do Índice". A
    cópia divergiu: ignorava a camada declarada nacional (MUNIC/ICM, ativa desde 21/09) e aplicava
    0,3 ao plano desatualizado onde o motor aplica 0,5. O PDF publicava, por isso, uma tabela de
    camadas que o motor não produz — DF 100/0/0 contra 37/0/63 do motor — e um efeito de variante
    que era artefato da divergência, não resultado.

    Os descontos são parâmetro porque o teste de sensibilidade existe para variá-los; o padrão é o
    do motor, e quem não passa nada recebe exatamente o que o índice publica.
    """
    w = float(wpop_uf)
    tipo_agr, excedente = excedente_agregado(uf, c)
    if tipo_agr:
        w += excedente * mediana * CRED_POP[tipo_agr]
    # Decisão D2 (A3-02, 08/10/2026): UM TERMO SÓ, com dois tetos. Os dois contadores do tribunal
    # de contas somam entre si — plano e plano desatualizado são municípios diferentes —, o
    # resultado é COMPARADO, nunca somado, com o levantamento nacional (MUNIC/ICM), e o total nunca
    # passa do número de municípios da UF. Do que sobra, desconta-se tudo o que já tem crédito
    # próprio em `CRED_POP` — antes a subtração usava só `PESO_DOC` e deixava `estrutura` e
    # `coberto_estadual` de fora, de modo que o mesmo município era creditado duas vezes.
    teto = n_municipios if n_municipios else float("inf")
    declarado = min(max((dp_tce or 0) + (da_tce or 0), nacional or 0), teto)
    doc_n = sum(v for k, v in c.items() if CRED_POP.get(k, 0.0) > 0)
    if declarado:
        w += max(declarado - doc_n, 0) * mediana * (CRED_POP["plano"] * desconto_plano)
    return min(100.0, 100.0 * w / pop_total), {"documentado": doc_n, "declarado": declarado,
                                               "declarado_antigo": da_tce or 0}


def calcular(versao="v3.1"):
    """Motor do índice: lê data/*.json, calcula os três componentes por estado, agrega com elemento
    geométrico e piso, e devolve o dicionário completo que vira data/indice.json.

    `versao` existe para a v3.0 continuar calculável depois da troca — a comparação v3.0 × v3.1 é
    registro público, e registro que não se pode refazer não é registro. Ninguém grava v3.0 em
    `data/`: quem pede v3.0 está comparando."""
    import statistics
    if versao not in ("v3.0", "v3.1"):
        raise SystemExit(f"✗ versão desconhecida: {versao}")
    tab = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    pct_arquivo = json.load(open(RAIZ / "data" / "percentual_uf.json", encoding="utf-8"))
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    pop = json.load(open(RAIZ / "data" / "populacao_censo2022.json", encoding="utf-8"))
    totais, pop_uf, pops_uf, cod_por = {}, {}, {}, {}
    for m in ref:
        totais[m["uf"]] = totais.get(m["uf"], 0) + 1
        p = pop.get(f"{m['codigo_ibge']:07d}", 0)  # 0 apenas p/ município pós-Censo (docstring)
        pop_uf[m["uf"]] = pop_uf.get(m["uf"], 0) + p
        if p:
            pops_uf.setdefault(m["uf"], []).append(p)
        cod_por[(m["nome"], m["uf"])] = f"{m['codigo_ibge']:07d}"
    mediana_uf = {u: statistics.median(v) for u, v in pops_uf.items()}

    cnt, cap_cat, wpop = {}, {}, {}
    for r in tab:
        cnt.setdefault(r["uf"], {}).setdefault(r["categoria"], 0)
        cnt[r["uf"]][r["categoria"]] += 1
        if r["nome"] in CAPITAIS and CAPITAIS[r["nome"]] == r["uf"]:
            cap_cat[r["uf"]] = r["categoria"]
        chave = (r["nome"], r["uf"])
        if chave not in cod_por:
            raise SystemExit(f"✗ registro sem casamento na malha IBGE: {chave} — "
                             "grafia deve ser a oficial (convenção do banco)")
        wpop[r["uf"]] = wpop.get(r["uf"], 0.0) + pop.get(cod_por[chave], 0) * CRED_POP.get(r["categoria"], 0.0)

    pct = derivar_percentual_uf(cnt, totais, pct_arquivo)

    ufs = sorted(ESTADOS)
    consist = _consist()
    datas_dos_atos = _datas_dos_atos()
    comp = []
    for uf in ufs:
        c = cnt.get(uf, {})
        w = wpop.get(uf, 0.0)
        # O excedente agregado entra dentro de `cobertura_de_uf`, com o resto da conta.
        # C5/§3.9: camada declarada nacional (MUNIC/ICM) ativada permanentemente em 21/09/2026,
        # por decisão editorial explícita. 08/10/2026 (A3-05): a conta mora em
        # `cobertura_de_uf`, uma só, porque a cópia que alimentava o PDF público divergiu dela.
        cobertura, _camadas = cobertura_de_uf(
            uf, c, w, mediana_uf[uf], pop_uf[uf],
            pct[uf].get("declarado_plano", 0) or 0, pct[uf].get("declarado_antigo", 0) or 0,
            _declarado_nacional_uf().get(uf, 0), totais.get(uf, 0) or 0)
        st, ant, conf = ESTADOS[uf]
        if versao == "v3.1":
            # Três componentes sem sobreposição: instrumento, estrutura e cobertura. A estrutura
            # deixa de ser metade do componente estadual e passa a valer um terço por si.
            comp.append([score_instrumento_v31(uf, consist), ESTADO_SCORE[ESTRUTURA[uf]],
                         round(cobertura, 1)])
        else:
            comp.append([score_estado(uf), round(cobertura, 1), ant])

    X = np.array(comp, float)
    lin = X.mean(axis=1)
    geo = np.exp(np.log(np.maximum(X, 5.0)).mean(axis=1))
    rng = np.random.default_rng(42)
    W = rng.dirichlet(np.ones(3), size=10000)
    S = X @ W.T
    order = (-S).argsort(axis=0)
    ranks = np.empty_like(order)
    for j in range(S.shape[1]):
        ranks[order[:, j], j] = np.arange(1, len(ufs) + 1)

    saida, robustez = {}, {}
    for i, uf in enumerate(ufs):
        st, ant, conf = ESTADOS[uf]
        if versao == "v3.1":
            data_ato = datas_dos_atos.get(uf)
            saida[uf] = {
                # Os três componentes da v3.1, nomeados pelo que são. `estado` sai: na v3.0 ele
                # era a média de estrutura e instrumento, e manter o nome com outro significado
                # seria pior do que trocá-lo.
                "instrumento": round(float(X[i, 0]), 1),
                "estrutura": round(float(X[i, 1]), 1),
                "cobertura_pop": round(float(X[i, 2]), 1),
                "total": round(float(lin[i]), 1), "total_geo": round(float(geo[i]), 1),
                "confianca": conf, "status_estadual": st,
                "estrutura_status": ESTRUTURA[uf], "estado_estrutura": ESTADO_SCORE[ESTRUTURA[uf]],
                "operacional_status": st, "estado_operacional": round(float(X[i, 0]), 1),
                "degrau_instrumento": degrau_do_instrumento(uf, st, consist),
                "consist": consist.get(uf),
                # INDICADOR, não componente: não entra na nota. None quando não há data completa —
                # mês solto e "Recorrente" não viram dia.
                "dias_apos_boletim_1": dias_apos_boletim_1(data_ato),
                "data_primeiro_ato": data_ato,
                "metodo": ("v3.1 — 3 componentes, pesos iguais (1/3), sem sobreposição: INSTRUMENTO "
                           "OPERACIONAL na escala de razão declarada (NOVO 100 · READ 70 · "
                           "recorrente que cobre e tem revisão/ativação datada em 2026 55 · "
                           "recorrente que cobre sem revisão 30 · em elaboração 20 · recorrente que "
                           "NÃO cobre o risco do ciclo 0 · nada localizado 0), ESTRUTURA DE "
                           "COORDENAÇÃO (§30) e COBERTURA POPULACIONAL (Censo 2022; §5 e §12.4.2-3). "
                           "O tempo saiu da nota: a antecedência é indicador à parte "
                           "(`dias_apos_boletim_1`, contado do Boletim nº 1 de 29/06/2026), porque a "
                           "lei exige plano existente e atualizado, não antecedência. Linear + "
                           "geométrico piso 5. Sem ranking ordinal público (§13); Monte Carlo 10k "
                           "Dirichlet(1,1,1) seed 42 em data/robustez_mc.json."),
            }
        else:
            saida[uf] = {
                "estado": round(float(X[i, 0]), 1), "cobertura_pop": round(float(X[i, 1]), 1),
                "antecipacao": int(ant),
                "total": round(float(lin[i]), 1), "total_geo": round(float(geo[i]), 1),
                "confianca": conf, "status_estadual": st,
                "estrutura_status": ESTRUTURA[uf], "estado_estrutura": ESTADO_SCORE[ESTRUTURA[uf]],
                "operacional_status": st, "estado_operacional": ESTADO_SCORE[st],
                "metodo": "v3.0 — 3 componentes, pesos iguais (1/3): instrumento estadual = média (1/2, 1/2) de ESTRUTURA DE COORDENAÇÃO e INSTRUMENTO OPERACIONAL (Metodologia §30, decisão de 04/09/2026), cobertura populacional (Censo 2022; crédito por categoria, inclusive `estrutura` 0,45; agregados e declarada via mediana; §5 e §12.4.2-3), antecipação (régua e teste do objeto: §5.2.1); linear + geométrico piso 5. Sem ranking ordinal público (§13); Monte Carlo 10k Dirichlet(1,1,1) seed 42 em data/robustez_mc.json.",
            }
        # Decisão de 29/08/2026 (Metodologia §13): o rank ordinal deixa de ser
        # produto público por UF — a resolução do instrumento não sustenta
        # comparação ordinal fina (12 pares de UFs a <2 pontos; amplitude
        # mediana p5–p95 de 7 posições). O Monte Carlo permanece integralmente
        # computado e selado AQUI, como evidência de robustez, com o intervalo
        # sempre publicado junto do rank mediano (recomendação da auditoria de
        # 29/08/2026, §6) — nunca o ordinal isolado.
        robustez[uf] = {
            "rank_mediano": int(np.median(ranks[i])),
            "rank_p5": int(np.percentile(ranks[i], 5)),
            "rank_p95": int(np.percentile(ranks[i], 95)),
        }
        robustez[uf]["amplitude"] = robustez[uf]["rank_p95"] - robustez[uf]["rank_p5"]
    robustez["_parametros"] = {"metodo": "Monte Carlo 10.000 sorteios de pesos Dirichlet(1,1,1), semente 42",
                               "uso": "evidência de robustez (anexo metodológico); não é produto público por UF",
                               "decisao": "Metodologia §13, 29/08/2026"}
    # 21/09/2026 (achado real, Portão 17): a média nacional usava lin.mean() — média dos valores
    # CRUS, antes do arredondamento de cada UF a 1 casa decimal — enquanto verificar_consistencia.py
    # (e qualquer leitor somando os 27 números da tabela pública) calcula a média dos valores JÁ
    # ARREDONDADOS. As duas contas podem divergir por erro de arredondamento acumulado; ficaram
    # coincidentemente iguais a sessão inteira porque a nota nunca mudou de verdade — a primeira
    # mudança real (ativação da camada declarada, §137) expôs a divergência (45.1 vs 45.2).
    # Corrigido para a fonte mais defensável: a média dos números que o site publica por UF, para
    # que somar a tabela pública e dividir por 27 dê exatamente o número do medidor principal.
    media_publicada = round(sum(v["total"] for v in saida.values()) / len(saida), 1)
    return saida, media_publicada, pct, robustez

def _recomputar_verificacao_em_memoria():
    """v2.2.4 (§3.3): data/verificacao_municipal.json é ARTEFATO DERIVADO de
    municipios.json + log_buscas.json + municipios_ibge_referencia.json —
    regravado por quem regrava a origem (lição §10 da transferência: 'artefato
    derivado precisa ser regravado por quem regrava a origem'). O nível de
    verificação só sobe com log estruturado; nada é imputado."""
    import re as _re
    PONT = {"plano","plano_antigo","plano_elaboracao","estrutura","coberto_estadual","decreto","nao_el_nino"}
    with open(RAIZ / "data" / "municipios.json", encoding="utf-8") as f: mun = json.load(f)
    from coletores_base import ler_log
    lg = ler_log()   # item 4: log em JSONL mensal, concatenado pela porta única
    with open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8") as f: ref = json.load(f)
    completos = set()
    for e in lg.get("execucoes", []):
        if e.get("nivel") == "municipal_completo" and str(e.get("decisao","")).strip().lower().startswith("nada localizado") and e.get("municipio") and e.get("uf"):
            completos.add((e["municipio"], e["uf"]))
    niveis_log = {}
    for e in lg.get("execucoes", []):
        if e.get("municipio") and e.get("uf") and e.get("nivel") in ("nacional","estadual","municipal_completo"):
            ordem = {"nacional":1,"estadual":2,"municipal_completo":3}
            ch=(e["municipio"],e["uf"])
            if ordem[e["nivel"]] > ordem.get(niveis_log.get(ch,""),0): niveis_log[ch]=e["nivel"]
    por = {(m["nome"], m["uf"]): m for m in mun}
    # v2.2.4 (PR-C): livro de fontes consultadas dos coletores (nível, datas, fatos binários)
    _lp = RAIZ / "data" / "fontes_consultadas.json"
    livro = (json.load(open(_lp, encoding="utf-8")).get("municipios", {}) if _lp.exists() else {})
    ordem = {"nao_verificado": 0, "nacional": 1, "estadual": 2, "municipal_completo": 3}
    out = []
    for r in ref:
        ch = (r["nome"], r["uf"]); reg = por.get(ch)
        cod7 = str(r["codigo_ibge"]).zfill(7)
        lv = livro.get(cod7, {})
        n_log = niveis_log.get(ch, "nao_verificado"); n_livro = lv.get("nivel_verificacao", "nao_verificado")
        # "municipal_completo" só pelo log (bateria inteira logada por município), nunca pelo livro
        if n_livro == "municipal_completo": n_livro = "estadual"
        nivel = n_log if ordem[n_log] >= ordem[n_livro] else n_livro
        out.append({"ibge": str(r["codigo_ibge"]), "nome": r["nome"], "uf": r["uf"],
            "nivel_verificacao": nivel,
            "ultima_verificacao": lv.get("ultima_verificacao"),
            "fontes_consultadas": sorted({f["fonte"] for f in lv.get("fontes", [])}),
            "decreto_reconhecido": lv.get("decreto_reconhecido"), "decreto_homologado": lv.get("decreto_homologado"),
            "plano_declarado_munic": lv.get("plano_declarado_munic"), "plano_declarado_icm": lv.get("plano_declarado_icm"),
            "plano_localizado": (reg["categoria"] if reg and reg["categoria"] in PONT else None)})
    return out

def _resumo_verificacao(out):
    """Resumo derivado para o site (data/verificacao_resumo.json): contagens por
    nível e por UF, mapa compacto ibge→nível apenas para níveis acima do padrão,
    nº de fontes suspensas pelo defeso na última rodada do log e tamanho da fila
    de citação incompleta. Fonte única: verificacao_municipal.json."""
    tot = {}
    por_uf = {}
    acima = {}
    for v in out:
        n = v["nivel_verificacao"]; tot[n] = tot.get(n, 0) + 1
        d_uf = por_uf.setdefault(v["uf"], {}); d_uf[n] = d_uf.get(n, 0) + 1
        if n != "nao_verificado": acima[v["ibge"]] = n
    try:
        from coletores_base import ler_log
        lg = ler_log()   # item 4
        datas = [e["data"] for e in lg.get("execucoes", []) if e.get("data")]
        ult = max(datas) if datas else None
        suspensas = sum(1 for e in lg.get("execucoes", []) if e.get("data") == ult and e.get("fonte_suspensa_defeso"))
    except Exception:
        ult, suspensas = None, 0
    try:
        fila = len(json.load(open(RAIZ / "data" / "citacao_incompleta.json", encoding="utf-8")).get("fila", []))
    except Exception:
        fila = None
    try:
        # 03/09/2026: o registro de LAI vive no repositório PRIVADO (nunca no site); aqui só
        # entra a lista de UFs cuja verificação estadual depende de resposta — sem contagens.
        _lp = RAIZ / "data" / "ufs_dependentes_de_lai.json"
        _lai = json.load(open(_lp, encoding="utf-8")) if _lp.exists() else {"ufs": []}
        lai = {"ufs_dependentes": sorted(_lai.get("ufs", []))}
        raise StopIteration
        _lai = json.load(open(RAIZ / "data" / "lai_pedidos.json", encoding="utf-8")).get("pedidos", [])
        lai = {"total": len(_lai), "a_enviar": sum(1 for p in _lai if p.get("status") == "a_enviar"),
               "enviados_sem_resposta": sum(1 for p in _lai if p.get("status") == "enviado" and not p.get("data_resposta")),
               "respondidos": sum(1 for p in _lai if p.get("data_resposta")),
               "ufs_dependentes": sorted({p["uf"] for p in _lai if p.get("tipo") == "defesa_civil" and not p.get("data_resposta") and p["uf"] != "BR"})}
    except StopIteration:
        pass
    except Exception:
        lai = None
    try:
        # 03/09/2026: progresso da varredura integral dos diários municipais (Querido Diário).
        # Consulta NÃO é verificação (§4.1.2): o número diz quantos municípios já foram consultados
        # nessa fonte, quantos tiveram menção e quantos não — nunca quantos "têm" ou "não têm" plano.
        _fc = json.load(open(RAIZ / "data" / "fontes_consultadas.json", encoding="utf-8")).get("municipios", {})
        _FQD = "Querido Diário (diário municipal)"
        _qd = {c: [f for f in m.get("fontes", []) if f.get("fonte") == _FQD] for c, m in _fc.items()}
        _qd = {c: f for c, f in _qd.items() if f}
        _datas = sorted({f["data"] for fs in _qd.values() for f in fs if f.get("data")})
        # 20/09/2026 (§121): classificação pelos prefixos REAIS que coletar_diarios_municipais.py
        # grava. Até aqui a conta procurava resultados começando com "sem edições", string que
        # nunca existiu: nenhum município caía em sem_mencao, com_mencao igualava consultados, e
        # a cortina pública afirmava que 3.180 municípios tinham menção a El Niño quando eram 153.
        #
        # 28/09/2026 (§280): a classificação passa a ser POSITIVA, e este é o conserto do defeito
        # que o §121 deixou pela metade. Ele trocou os prefixos errados pelos certos e manteve a
        # definição por EXCLUSÃO: `com_mencao` era tudo o que não começasse por um de três
        # prefixos. Definição por exclusão não erra uma vez — erra a cada decisão nova que alguém
        # criar. Foi o que aconteceu com `sem_edicao_no_periodo`, criada pelo §194: 87 registros de
        # "diário indexado, nenhuma edição na janela" entraram na conta pública de menções, e o
        # número publicado caiu de 347 para 260 quando a definição virou positiva. É a terceira
        # lista de que essa decisão ficou de fora (as duas primeiras estão no comentário do
        # coletor, linha 108).
        #
        # Os cinco estados são distintos e não podem ser colapsados:
        #   sem_cobertura_qd      — o município NÃO tem diário indexado; nada foi ou pode ser lido
        #   sem_edicao_no_periodo — indexado, nenhuma edição DENTRO da janela; não houve o que ler
        #   coberto_sem_mencao    — indexado e lido; nenhum excerto com os termos
        #   com_mencao            — a consulta COM OS TERMOS devolveu edição. É a contagem
        #                           `N decreto(s), M pista(s)`, que o coletor grava só nesse ramo,
        #                           e vale também com zero e zero: houve excerto com os termos, não
        #                           houve ato classificado. No log é `com_excerto` ou `registro`.
        #   cobertura_indefinida  — o teste de cobertura falhou, OU a string é desconhecida por
        #                           este código. String desconhecida NUNCA vira menção: cair no
        #                           balde indefinido subdeclara, cair em `com_mencao` afirma.
        # "Não indexado" não é "sem menção", e "sem edição na janela" também não: nos dois casos
        # não há o que ler, e tratar isso como leitura negativa afirma ausência onde só há ausência
        # de fonte (§4.1.2). A ordem dos testes é deliberada — leitura efetiva vence ausência de
        # edição, porque o município que teve o diário lido numa janela e nenhuma edição em outra
        # foi, de fato, lido.
        _RE_CONTAGEM_QD = re.compile(r"^\d+ decreto\(s\), \d+ pista\(s\)$")

        def _classificar(fs):
            marcas = [str(f.get("resultado", "")) for f in fs]
            if any(_RE_CONTAGEM_QD.match(m) or m.startswith("com_excerto") for m in marcas):
                return "com_mencao"
            if any(m.startswith("coberto_sem_mencao") for m in marcas):
                return "coberto_sem_mencao"
            if any(m.startswith("sem_edicao_no_periodo") for m in marcas):
                return "sem_edicao_no_periodo"
            if any(m.startswith("sem_cobertura_qd") for m in marcas):
                return "sem_cobertura_qd"
            return "cobertura_indefinida"

        _estado = {c: _classificar(fs) for c, fs in _qd.items()}

        # 29/09/2026: o log não fala de TODOS os municípios. Vinte deles não têm diário indexado no
        # Querido Diário e, justamente por isso, nunca foram consultados — não há linha de log a
        # classificar. O estado deles não é indefinido: `data/cobertura_qd.json` diz `false`, e
        # `false` é `sem_cobertura_qd`. Sem este preenchimento, o resumo contava 5.021 e o arquivo
        # de cobertura 5.041, e o portão de paridade (§256) reprovava a `main` por comparar
        # universos diferentes: o dos consultados contra o dos existentes. `consultados` continua
        # sendo o número de quem tem linha de log, que é outra pergunta e segue respondida.
        _cob_qd = {}
        _p_cob = RAIZ / "data" / "cobertura_qd.json"
        if _p_cob.exists():
            _cob_qd = (json.loads(_p_cob.read_text(encoding="utf-8")) or {}).get("municipios") or {}
        # 30/09/2026: quando o log é ILEGÍVEL (`cobertura_indefinida`) e a cobertura SABE a
        # resposta, vale a cobertura. Marca de log que ninguém consegue ler não é prova de nada;
        # a sondagem do acervo é. O caminho inverso não vale: cobertura `true` com log ilegível
        # significa "indexado e não lido", que não é `sem_cobertura_qd` e segue indefinido.
        for _v in out:
            _c = str(_v["ibge"]).zfill(7)
            if _estado.get(_c) == "cobertura_indefinida":
                _r = _cob_qd.get(_c)
                _val = _r.get("cobertura_qd") if isinstance(_r, dict) else _r
                if _val is False:
                    _estado[_c] = "sem_cobertura_qd"
            if _c in _estado:
                continue
            _r = _cob_qd.get(_c)
            _val = _r.get("cobertura_qd") if isinstance(_r, dict) else _r
            _estado[_c] = "sem_cobertura_qd" if _val is False else "cobertura_indefinida"

        _com_mencao = sum(1 for e in _estado.values() if e == "com_mencao")
        _coberto_sem_mencao = sum(1 for e in _estado.values() if e == "coberto_sem_mencao")
        _sem_edicao = sum(1 for e in _estado.values() if e == "sem_edicao_no_periodo")
        _sem_cobertura = sum(1 for e in _estado.values() if e == "sem_cobertura_qd")
        _indefinido = sum(1 for e in _estado.values() if e == "cobertura_indefinida")
        _uf_de = {str(v["ibge"]).zfill(7): v["uf"] for v in out}; _por_uf_qd = {}
        for c in _qd: _u = _uf_de.get(str(c).zfill(7)); _por_uf_qd[_u] = _por_uf_qd.get(_u, 0) + 1
        varredura = {"fonte": _FQD, "consultados": len(_qd), "total": len(out), "com_mencao": _com_mencao,
                     "coberto_sem_mencao": _coberto_sem_mencao,
                     "sem_edicao_no_periodo": _sem_edicao, "sem_cobertura_qd": _sem_cobertura,
                     "cobertura_indefinida": _indefinido,
                     # sem_mencao = lidos e sem excerto. NÃO inclui os não indexados nem os sem
                     # edição na janela: nos dois casos não há leitura, e somá-los afirmaria
                     # ausência de plano onde só há ausência de fonte.
                     "sem_mencao": _coberto_sem_mencao,
                     "indexados": _com_mencao + _coberto_sem_mencao + _sem_edicao,
                     "desde": (_datas[0] if _datas else None), "ultima": (_datas[-1] if _datas else None),
                     "por_uf": _por_uf_qd}   # 07/09/2026: diário consultado por UF (face do cartão)
    except Exception:
        varredura = None
    resumo = {"gerado_de": "verificacao_municipal.json", "total_municipios": len(out), "lai": lai,
              "totais_por_nivel": tot, "por_uf": por_uf, "niveis_acima_do_padrao": acima,
              "ultima_rodada_log": ult, "fontes_suspensas_defeso_ultima_rodada": suspensas,
              "fila_citacao_incompleta": fila, "varredura_diarios": varredura}
    gravar_em(RAIZ / "data" / "verificacao_resumo.json", resumo)   # §229
    return resumo

def regravar_verificacao_municipal():
    out = _recomputar_verificacao_em_memoria()
    with open(RAIZ / "data" / "verificacao_municipal.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.write("\n")
    _resumo_verificacao(out)
    return out

def main():
    """Interface de linha de comando: sem flag, recalcula e grava; com --check, recalcula em memória e compara campo a campo contra o data/indice.json publicado (portão 2), sem gravar nada."""
    modo = sys.argv[1] if len(sys.argv) > 1 else "--check"
    novo, media, pct_derivado, robustez = calcular()
    alvo = RAIZ / "data" / "indice.json"
    alvo_pct = RAIZ / "data" / "percentual_uf.json"
    alvo_rob = RAIZ / "data" / "robustez_mc.json"
    if modo == "--write":
        # §229: escrita atômica. O índice é o produto do projeto; um JSON truncado aqui é o site
        # inteiro sem número, e a corrupção de 21/09/2026 provou que a janela existe.
        gravar_em(alvo, novo)
        gravar_em(alvo_pct, pct_derivado)
        gravar_em(alvo_rob, robustez)
        print(f"data/indice.json, data/percentual_uf.json e data/robustez_mc.json regravados · média nacional {media:.1f}")
        # 03/09/2026: o fallback estático do medidor do herói (index.html) é DERIVADO do índice
        _p = RAIZ / "index.html"; _h = _p.read_text(encoding="utf-8"); _m = f"{media:.1f}"; _mbr = _m.replace(".", ",")
        _h2 = re.sub(r'(id="gaugeNum">)[\d,]+(<)', rf"\g<1>{_mbr}\g<2>", _h, count=1)
        _h2 = re.sub(r'data-alvo="[\d.]+" style="--galvo:[\d.]+;"', f'data-alvo="{_m}" style="--galvo:{_m};"', _h2, count=1)
        _h2 = re.sub(r'aria-label="Barra de progresso: MARÉ nacional em [\d,]+ de 100"', f'aria-label="Barra de progresso: MARÉ nacional em {_mbr} de 100"', _h2, count=1)
        if _h2 != _h: _p.write_text(_h2, encoding="utf-8", newline="\n"); print(f"index.html: fallback do medidor regravado ({_mbr})")
        vm = regravar_verificacao_municipal()
        print(f"data/verificacao_municipal.json regravado (derivado) · {len(vm)} municípios")
        # Selos SVG são função pura do índice: quem regrava o índice regrava os selos
        # (31/08/2026 — sem isto, o portão selo×índice revertia toda mudança legítima
        # dentro do julgamento automático).
        import gerar_selos
        gerar_selos.gerar()
        print("selos/ regravados a partir do índice")
        print("(percentual_uf.json agora é DERIVADO de municipios.json a cada --write; campos")
        print(" declarado_plano/declarado_antigo/fonte_declarada de auditorias externas preservados.)")
        return 0
    # v2.2.4: paridade do artefato derivado verificacao_municipal.json
    import tempfile, copy
    vm_disco_path = RAIZ / "data" / "verificacao_municipal.json"
    if vm_disco_path.exists():
        vm_disco = json.load(open(vm_disco_path, encoding="utf-8"))
        vm_novo = _recomputar_verificacao_em_memoria()
        if vm_disco != vm_novo:
            print("✗ VERIFICACAO_MUNICIPAL NÃO REPRODUZIDA — derivado em disco diverge do recomputado (rode --write)")
            return 1
        # resumo também é derivado: conferir contra o recomputado (sem gravar)
        import io, contextlib
        res_path = RAIZ / "data" / "verificacao_resumo.json"
        if res_path.exists():
            res_disco = json.load(open(res_path, encoding="utf-8"))
            _tmp = res_path.read_bytes()
            _resumo_verificacao(vm_novo)          # regrava…
            res_novo = json.load(open(res_path, encoding="utf-8"))
            res_path.write_bytes(_tmp)            # …e restaura o disco (modo --check não grava)
            if res_disco != res_novo:
                print("✗ VERIFICACAO_RESUMO NÃO REPRODUZIDO — derivado em disco diverge do recomputado (rode --write)")
                return 1
        else:
            print("✗ data/verificacao_resumo.json ausente (rode --write)")
            return 1
    else:
        print("✗ data/verificacao_municipal.json ausente (rode --write)")
        return 1
    _h = (RAIZ / "index.html").read_text(encoding="utf-8")
    _mm = re.search(r'data-alvo="([\d.]+)"', _h); _mn = re.search(r'id="gaugeNum">([\d,]+)<', _h)
    if not _mm or abs(float(_mm.group(1)) - round(media, 1)) > 0.05 or not _mn or _mn.group(1) != f"{media:.1f}".replace(".", ","):
        print(f"✗ MEDIDOR DO HERÓI desatualizado no index.html (fallback ≠ média {media:.1f}; rode --write)"); return 1
    atual = json.load(open(alvo, encoding="utf-8"))
    # v3.1 (30/09/2026): os componentes trocaram de nome. `estado` era a média de estrutura e
    # instrumento; `antecipacao` era a régua temporal, que saiu da nota. Conferir campo que não
    # existe mais faria o portão quebrar em vez de reprovar — e quebrar não é reprovar.
    campos = ["instrumento", "estrutura", "cobertura_pop", "total", "total_geo",
              "confianca", "status_estadual", "degrau_instrumento", "dias_apos_boletim_1"]
    rob_atual = json.load(open(alvo_rob, encoding="utf-8")) if alvo_rob.exists() else None
    if rob_atual != robustez:
        print("✗ ROBUSTEZ NÃO REPRODUZIDA — data/robustez_mc.json diverge do recomputado (rode --write)")
        return 1
    div = [(uf, k, atual[uf][k], novo[uf][k]) for uf in novo for k in campos
           if atual.get(uf, {}).get(k) != novo[uf][k]]
    if div:
        print(f"✗ ÍNDICE NÃO REPRODUZIDO — {len(div)} divergência(s):")
        for d in div[:12]:
            print(f"   {d[0]}.{d[1]}: publicado={d[2]} recomputado={d[3]}")
        return 1
    print(f"✓ MARÉ REPRODUZIDO — 27 estados × {len(campos)} campos idênticos (+ robustez_mc.json) · média nacional {media:.1f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
