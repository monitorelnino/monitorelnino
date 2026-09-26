#!/usr/bin/env python3
"""Orquestrador de atualização do Monitor El Niño Brasil.

Etapas:
  1. atualizar_boletins.py  — vigia de novos boletins do Painel El Niño (rede tolerante a falha)
  2. atualizar_instrumentos_estaduais.py — Camada 1 do Protocolo de Busca v2 (Metodologia
     §4.1.1): verifica repositórios estaduais estruturados por município novo/atualizado.
     NUNCA escreve na base; só gera data/instrumentos_revisar.json para aprovação humana
     (rede tolerante a falha — um repositório fora do ar não interrompe a atualização).
  3. atualizar_transferencias.py — transferências municipais via API do Portal da Transparência
     (requer a variável de ambiente PORTAL_TRANSPARENCIA_API_KEY; sem ela, a etapa é pulada com aviso)
  4. verificar_estrutura.js — árvore HTML das páginas (obrigatória; falha bloqueia)
  5. verificar_consistencia.py — invariantes dos dados (obrigatória; falha bloqueia)
  6. recalcular_mare.py --check — índice bate com os dados (obrigatória; falha bloqueia)
  7. verificar_runtime.js — site roda em navegador simulado (obrigatória; falha bloqueia)
  7b. verificar_runtime_mapas.js — defesa-civil.html roda em navegador simulado
  7c. verificar_runtime_sinais.js — monitor-de-riscos.html roda em navegador simulado
     (obrigatória; falha bloqueia; página própria desde 31/08/2026)
  8. data/meta.json — carimbo de atualização (e novo corte, se a etapa 3 alterou dados)
  9. preencher_fallback_estatico.py — medidor de resposta e datas de corte no HTML estático
     (sem JavaScript) de index.html, saude.html e financiamento.html (16/09/2026)

Nota (17/09/2026): coletar_sinais_risco.py (ONI, avisos do INMET, focos do INPE, alertas do
CEMADEN) roda TODO DIA, incondicional — está fora do portão de cadência semanal do índice
(peso zero, nunca pontua; sempre foi independente do índice, só não tinha frequência própria).

Quando o passo 2 gerar propostas: revise data/instrumentos_revisar.json, apague o que
não deve entrar, e rode `python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json`
— esse script mescla a revisão aprovada, recalcula o índice e roda os três portões.

Uso: python atualizar.py
"""
import datetime, hashlib, json, os, pathlib, subprocess, sys
from zoneinfo import ZoneInfo

RAIZ = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------------
# Cadência semanal de publicação — dia único de verdade para toda a rotina.
#
# 20/09/2026 (decisão da editoria): a publicação semanal passa de SEGUNDA para
# DOMINGO, 0h de Brasília (cron `0 3 * * 0` = domingo 03h UTC). A rodada leva
# 75–105 min e agora cabe inteira dentro do domingo, sem cruzar a meia-noite.
# Duas armadilhas resolvidas aqui:
#
#  1. FUSO. O runner do GitHub roda em UTC, e a meia-noite de Brasília é 03h
#     em UTC do mesmo dia. Usar datetime.date.today() (UTC) para a data da
#     edição ou para o dia da semana desalinha o que o site promete do que ele
#     executa — ver §118, quando a cadência de sábado 22h40 carimbava domingo.
#     A cadência é, por isso, ancorada em America/Sao_Paulo — o fuso do leitor,
#     do texto público e da redação —, não no fuso do runner.
#  2. DUPLICIDADE. O cron diário das 09h UTC também cai no dia de publicação
#     (06h de Brasília, com a rodada semanal já encerrada). Sem guarda, o
#     domingo teria DUAS rodadas completas. `ja_publicou_hoje()` encerra a segunda.
#
# Ao alterar o dia aqui, altere também: o cron do workflow, o texto público
# (obrigado.html, pesquisadores.html) e a documentação. O portão
# scripts/testar_cadencia_publicacao.py bloqueia se algum deles divergir — o dia
# é compromisso declarado ao leitor, não detalhe interno.
# ---------------------------------------------------------------------------
FUSO_EDITORIAL = ZoneInfo("America/Sao_Paulo")
DIA_PUBLICACAO = 6            # weekday(): 0 = segunda … 5 = sábado, 6 = domingo
NOME_DIA_PUBLICACAO = "domingo"


def hoje_editorial():
    """Data de hoje no fuso da redação (America/Sao_Paulo), não no fuso do runner."""
    return datetime.datetime.now(FUSO_EDITORIAL).date()


def ja_publicou_hoje():
    """True se data/meta.json já registra atualização na data editorial de hoje.

    Guarda contra rodada completa duplicada no mesmo dia: o cron diário e o cron
    semanal caem ambos no dia de publicação, e sem isto a cadeia inteira (75–105 min)
    rodaria duas vezes, gerando dois commits para a mesma edição.
    """
    try:
        meta = json.loads((RAIZ / "data" / "meta.json").read_text(encoding="utf-8"))
        return meta.get("atualizado_em", "") == hoje_editorial().strftime("%d/%m/%Y")
    except Exception:  # noqa: BLE001 — meta ilegível nunca bloqueia a rodada
        return False

# TETO DE TEMPO POR ETAPA (23/09/2026). Achado real: a rodada diária de 23/09 ficou 45+ min
# num passo que, fora do dia de publicação, só executa dois scripts antes de encerrar na
# trava de cadência — e um deles não toca a rede. O `subprocess.run` não tinha timeout, o
# passo do workflow não tinha `timeout-minutes`, e o job herda o padrão de 6 HORAS do
# GitHub. Somado à trava de concorrência (`cancel-in-progress: false`), uma única fonte
# pendurada segurava a fila de atualização o dia inteiro, sem nada reprovar.
#
# O teto por etapa é a correção certa, não o teto do job: uma fonte lenta mata a etapa dela
# e a rodada segue — que é exatamente a disciplina que o pipeline já declara ("nenhum
# coletor é bloqueante; fonte fora do ar é lacuna declarada"). Sem isso, a única saída era
# matar a rodada inteira e perder também o que já tinha coletado.
TETO_ETAPA_S = 45 * 60          # etapas pesadas do dia de publicação
TETO_ETAPA_DIARIA_S = 15 * 60   # coletores que rodam todo dia e nunca pontuam


def rodar(cmd, obrigatorio=False, env_extra=None, teto_s=TETO_ETAPA_S):
    """Executa um subprocesso do pipeline; se obrigatorio=True, aborta o processo com o mesmo código de saída em caso de falha."""
    # 21/09/2026 (§124): flush obrigatório. Fora de um terminal, o stdout do Python é
    # bufferizado em blocos, mas os subprocessos escrevem direto no descritor. Sem o flush,
    # os cabeçalhos "=== etapa ===" saíam todos juntos no fim da rodada, enquanto a saída de
    # cada coletor saía na hora — o relatório ficava com os cabeçalhos separados do que cada
    # etapa imprimiu, e era impossível atribuir uma falha à etapa que a produziu. Foi assim
    # que "[aviso] iri_plume: ..." passou despercebido rodada após rodada.
    print(f"\n=== {' '.join(cmd)} ===", flush=True)
    env = {**os.environ, **(env_extra or {})}
    try:
        codigo = subprocess.run(cmd, cwd=RAIZ, env=env, timeout=teto_s).returncode
    except subprocess.TimeoutExpired:
        # O filho é morto; netos que ele tenha deixado podem sobreviver até o fim do job.
        # Ainda assim a rodada volta a andar, que é o ponto.
        codigo = 124
        print(f"[aviso] etapa estourou o teto de {teto_s // 60} min e foi encerrada: "
              f"{' '.join(cmd)} — tratada como fonte fora do ar (lacuna declarada), "
              f"a rodada continua", flush=True)
    sys.stdout.flush()
    if codigo != 0 and obrigatorio:
        print(f"[erro] etapa obrigatória falhou: {' '.join(cmd)}", flush=True)
        sys.exit(codigo)
    if codigo != 0:
        print(f"[aviso] etapa não obrigatória falhou (código {codigo}): {' '.join(cmd)}", flush=True)
    return codigo == 0

def hash_arquivo(p):
    """SHA-256 do conteúdo do arquivo (string vazia se ainda não existir), usado para detectar se a etapa de transferências mudou os dados."""
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ""

def main():
    """Executa as oito etapas do pipeline canônico em ordem, na sequência declarada no docstring do módulo."""
    # Data da EDIÇÃO, fixada aqui no início da rodada e no fuso da redação.
    # Duas razões, ambas descobertas na primeira rodada de sábado (20/09/2026):
    #  · Fuso: datetime.date.today() é UTC no runner. A rodada de sábado 22h40 de
    #    Brasília começa às 01h40 de DOMINGO em UTC, e carimbava `atualizado_em`
    #    com domingo — o site prometendo sábado e datando domingo toda semana.
    #  · Meia-noite: a rodada leva 75–105 min e sempre cruza a virada do dia. A data
    #    é fixada no início, então a edição inteira leva a data do dia em que foi
    #    publicada, não a do minuto em que a última etapa terminou.
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    transf = RAIZ / "data" / "transferencias.json"
    antes = hash_arquivo(transf)

    # v2.2.4 (E4/§13): cadência ANTES de qualquer coleta — em dia não publicável nada muda.
    intensivo = os.environ.get("INTENSIVO_ATE", "")
    intensivo_de = os.environ.get("INTENSIVO_DE", "") or intensivo  # sem início declarado, vale só o fim
    hoje_iso = hoje_editorial().isoformat()
    dia_semana = hoje_editorial().weekday()  # no fuso da redação, nunca no do runner (ver topo)
    em_intensivo = bool(intensivo) and intensivo_de <= hoje_iso <= intensivo
    if os.environ.get("ENSAIO"):
        print("[ensaio] execução de ensaio: tudo roda como no dia da semana intensiva; NADA será comitado nem publicado.")
        em_intensivo = True

    # RODADA COMPLETA SOB DEMANDA (23/09/2026, pedido da editoria). Diferente do ensaio:
    # roda tudo E comita, fora do dia de publicação. Existe porque a alternativa era mexer
    # nas variáveis INTENSIVO_DE/INTENSIVO_ATE do repositório, que valem também para os três
    # crons — uma edição fora de hora viraria uma semana inteira de rodadas completas, e
    # ninguém lembraria de desfazer.
    #
    # É destrava DECLARADA, não atalho: sai no log, exige disparo manual com o botão, e a
    # edição publicada leva a data de HOJE. Isso é consequência editorial real — a cadência
    # semanal é compromisso público (obrigado.html, pesquisadores.html dizem ao leitor
    # quando o banco muda), e uma edição fora do dia declarado é decisão da editoria,
    # tomada a cada disparo, nunca herdada de uma configuração esquecida.
    if os.environ.get("FORCAR_RODADA_COMPLETA"):
        print(f"[cadência] RODADA COMPLETA SOB DEMANDA: hoje é "
              f"{hoje_editorial():%d/%m/%Y} e o dia de publicação declarado é "
              f"{NOME_DIA_PUBLICACAO}. Rodando tudo e comitando por pedido explícito da "
              f"editoria; a edição levará a data de hoje.")
        em_intensivo = True

    # Sinais oficiais de risco (01/09/2026, METODOLOGIA §23): coleta as três camadas
    # para monitor-de-riscos.html. NÃO é bloqueante e NÃO toca no índice — fonte fora do
    # ar permanece como lacuna declarada na página, nunca como valor estimado.
    # 17/09/2026 (achado ao checar a frequência da página, pedido da editoria): esta coleta é
    # independente do índice desde a origem (peso zero, nunca pontua) — mas vivia PRESA à mesma
    # cadência semanal do índice, então "o que está acontecendo agora" só se atualizava às
    # segundas. Sinais como ONI, avisos do INMET e focos do INPE mudam todo dia na fonte; a
    # chamada sai daqui de dentro do portão semanal e roda incondicionalmente, todo dia.
    rodar([sys.executable, "coletar_sinais_risco.py"], teto_s=TETO_ETAPA_DIARIA_S)

    # 18/09/2026 (rotina diária, portão 12 vermelho na main): gerar_monitor_saude.py copia
    # sinais.uf[UF].fogo.focos_24h de data/sinais_risco.json para data/monitor_saude.json
    # (campo "focos_24h" de cada UF, §31). Como a chamada acima passou a rodar todo dia
    # (17/09/2026) mas esta continuava só no bloco semanal, abaixo do "return" de cadência,
    # o derivado ficava um a seis dias atrás do sinal bruto em qualquer dia que não fosse
    # segunda — mesma classe de bug do carimbo `gerado_em` de 10/09/2026 (derivado não
    # regravado quando a fonte muda). Regenerar aqui, todo dia, mantém o derivado
    # sincronizado com o sinal que ele copia; a chamada do bloco semanal (mais abaixo)
    # continua — é idempotente sobre os mesmos dados quando nada mudou.
    rodar([sys.executable, "gerar_monitor_saude.py"], teto_s=TETO_ETAPA_DIARIA_S)

    if not em_intensivo and dia_semana != DIA_PUBLICACAO:
        print(f"[cadência] fora da semana intensiva e não é {NOME_DIA_PUBLICACAO} "
              f"(hoje é {hoje_editorial():%d/%m/%Y} no fuso da redação): "
              f"execução diária encerra sem coletar nem comitar.")
        return 0

    # Guarda contra rodada completa duplicada no mesmo dia editorial (ver topo):
    # o cron diário e o cron semanal caem ambos no dia de publicação.
    if not em_intensivo and not os.environ.get("ENSAIO") and ja_publicou_hoje():
        print(f"[cadência] a edição de {hoje_editorial():%d/%m/%Y} já foi publicada nesta "
              f"data (data/meta.json); execução encerra sem recoletar nem comitar.")
        return 0

    rodar([sys.executable, "atualizar_boletins.py"])

    # v2.2.4 (PR-C, doc de redesenho §4): coletores da Pista A. Nenhum é bloqueante e
    # nenhum toca a nota: escrevem atos de resposta (peso zero), pistas e o livro de
    # fontes consultadas. Fonte fora do ar ou não confirmada = lacuna declarada no log.
    # Lotes da semana intensiva (§13) controlados por INTENSIVO_ATE (variável de repositório):
    rodar([sys.executable, "coletar_s2id.py"])
    rodar([sys.executable, "coletar_declarado_nacional.py"])
    rodar([sys.executable, "coletar_doe.py"])                       # 27 UFs; sem adaptador = lacuna
    lote = os.environ.get("LOTE_DIARIOS") or ""
    if not lote:
        # lote rotativo: 1 no primeiro dia da semana intensiva, subindo até o último dia (D1..D7);
        # fora do intensivo (rodada semanal de sábado) usa o lote 1 — os lotes seguintes são pós-defeso (§13)
        if em_intensivo:
            # no fuso da redação, como hoje_iso e o portão de cadência: em UTC a rodada
            # noturna cairia no dia seguinte e adiantaria o lote em um.
            decorridos = (hoje_editorial() - datetime.date.fromisoformat(intensivo_de)).days
            lote = str(max(1, min(7, decorridos + 1)))  # D0 = lote 1 … D6+ = lote 7
        else:
            lote = "1"
    if em_intensivo and os.environ.get("FINALIZAR_VARREDURA_HOJE") == "1":
        # 03/09/2026: pedido editorial pontual — encerrar a varredura integral HOJE, numa rodada só,
        # em vez de seguir o ritmo por dias restantes. Ativado só pelo input manual do workflow.
        rodar([sys.executable, "coletar_diarios_municipais.py", "--pendentes-desde", intensivo_de,
               "--ate", intensivo, "--tamanho", os.environ.get("TAMANHO_LOTE", "150"), "--tudo"])
    elif em_intensivo and not os.environ.get("LOTE_DIARIOS"):
        # 03/09/2026 (decisão editorial): varredura INTEGRAL — todos os 5.571 municípios até INTENSIVO_ATE.
        # Cada dia consulta os próximos ainda não consultados na janela; o tamanho é recalculado a cada
        # rodada para caber nos dias que restam (mínimo TAMANHO_LOTE). Consulta não é verificação (§4.1.2).
        rodar([sys.executable, "coletar_diarios_municipais.py", "--pendentes-desde", intensivo_de, "--ate", intensivo,
               "--tamanho", os.environ.get("TAMANHO_LOTE", "150")])
    else:
        rodar([sys.executable, "coletar_diarios_municipais.py", "--lote", lote, "--tamanho", os.environ.get("TAMANHO_LOTE", "150")])
    # 21/09/2026: recalcular_mare.py --simular-declarado-nacional foi removido — a camada
    # declarada nacional (MUNIC/ICM) agora é parte permanente do cálculo padrão (calcular()),
    # ativada por decisão editorial explícita. O --write mais adiante no pipeline já cobre isso;
    # nenhuma chamada separada é mais necessária aqui.
    # 25/09/2026 (§217/§223): o canal dos diários CONSORCIADOS entra na rotina. Ele estava
    # escrito desde 22/09 e fora do pipeline porque a fonte bloqueava; destravado, é o único
    # caminho para a maioria dos 5.041 municípios sem diário indexado no Querido Diário.
    # A janela é CURTA de propósito: a rotina roda todo dia e só precisa do que é novo. Uma
    # edição consorciada é um PDF de vários MB e leva cerca de dois minutos — varrer o ciclo
    # inteiro leva horas e é trabalho de rodada dedicada, não de cadência diária.
    rodar([sys.executable, "coletar_diarios_consorciados.py", "--desde",
           (hoje_editorial() - datetime.timedelta(days=8)).isoformat(),
           "--ate", hoje_editorial().isoformat()])
    rodar([sys.executable, "preservar_evidencias.py"])                 # idempotente; §3.8
    rodar([sys.executable, "preservar_evidencias.py", "--reconferir"])  # §3.8-bis: rebaixa e compara o hash; alteração vira evento
    rodar([sys.executable, "coletar_saude.py"])                         # §9: camada observada (InfoDengue); peso zero
    rodar([sys.executable, "coletar_desfechos_saude.py"])               # 07/09/2026 (§8): desfechos — InfoDengue 2019–2026 para o painel; peso zero
    rodar([sys.executable, "coletar_desfechos_saude.py", "--doenca", "chikungunya"])   # 14/09/2026: mesmo coletor, disease=chikungunya → chik_*.json; peso zero
    rodar([sys.executable, "coletar_srag_gripe.py"])                      # 09/09/2026 (§36): SRAG/SG nacional e por UF, InfoGripe; peso zero
    rodar([sys.executable, "coletar_dda.py"])                             # 14/09/2026 (§39): DDA nacional e por UF, Sivep-DDA via LAI (Zenodo); peso zero
    rodar([sys.executable, "coletar_boletim_ms_dengue.py"])           # 10/09/2026 (§36): dengue por município, boletim semanal da SES-MS; peso zero
    rodar([sys.executable, "coletar_boletim_df_arboviroses.py"])      # 10/09/2026 (§36): arboviroses por Região de Saúde, informe semanal da SES-DF; peso zero
    rodar([sys.executable, "coletar_boletim_pe_arboviroses.py"])      # 10/09/2026 (§36): arboviroses, TOTAIS ESTADUAIS, informe semanal do CIEVS-PE (tabela municipal é imagem); peso zero
    rodar([sys.executable, "coletar_boletim_pb_arboviroses.py"])      # 10/09/2026 (§36): arboviroses por Região de Saúde, boletim numerado da SES-PB; peso zero
    rodar([sys.executable, "preservar_evidencias.py", "--ler", "--limite", "40"])   # 07/09/2026 (§10.1): texto por página dos PDFs de planos
    rodar([sys.executable, "classificar_saude_no_plano.py"])            # 07/09/2026 (§10.1): leitura automática de saúde no plano → fila R7
    rodar([sys.executable, "gerar_monitor_saude.py"])                   # 05/09/2026: Monitor Saúde v0.1 (§31), derivado da camada de saúde; peso zero
    rodar([sys.executable, "gerar_resposta.py"])                        # 06/09/2026 (v3.1 §3): contador de resposta; peso zero (verificar_resposta.py)
    rodar([sys.executable, "gerar_prioritarios.py"])                    # 15/09/2026: municípios prioritários (aproximação populacional), fonte única do mapa e da busca
    rodar([sys.executable, "gerar_contadores_financiamento.py"])       # 06/09/2026 (v3.1 §11): quatro contadores por UF; peso zero
    rodar([sys.executable, "coletar_financiamento.py"])                 # §7.8: Portal (chave), rotas; peso zero
    rodar([sys.executable, "coletar_transferegov.py"])                  # 04/09/2026: transferências sem chave (TransfereGov dados abertos); r5 na série
    rodar([sys.executable, "coletar_execucao_mps.py"])                  # 05/09/2026: execução das ações das MPs 1.367/1.384 (arquivos mensais abertos)

    rodar([sys.executable, "verificar_contribuicoes.py"])

    revisar_p = RAIZ / "data" / "instrumentos_revisar.json"
    if revisar_p.exists(): revisar_p.unlink()  # descarta proposta não aplicada de rodada anterior
    # Etapa não-bloqueante por design (um repositório estadual fora do ar não deve
    # impedir a atualização), mas o retorno != 0 significa VERIFICAÇÃO INCOMPLETA —
    # nunca 'sem novidades'. O aviso abaixo torna isso visível no log da Action.
    if not rodar([sys.executable, "atualizar_instrumentos_estaduais.py"]):
        print("\n[aviso] a varredura de repositórios estaduais ficou INCOMPLETA (ver mensagens acima).")
        print("        Os dados publicados seguem válidos, mas esta rodada não confirma ausência de novidades.")
    if revisar_p.exists():
        print(f"\n[aviso] {revisar_p.relative_to(RAIZ)} tem proposta(s) pendente(s) de revisão humana.")
        print("        Revise o arquivo e rode: python3 aplicar_revisao.py --arquivo", revisar_p.relative_to(RAIZ))

    # 03/09/2026 (achado do ensaio): coletores legados que rodavam DEPOIS dos portões, no workflow,
    # passam para cá — antes dos derivados e dos portões (nunca mais dado gravado sem portão).
    # PR-N0 §1.1 (06/09/2026): o varredor em LOTE (territory_ids com vírgulas) produziu 8.165 zeros uniformes em 03/09;
    # suspenso até o diagnóstico de resultado conhecido concluir. O coletar_diarios_municipais.py (um território por vez)
    # é o canal DOM vigente e grava as três decisões do §1.2.
    # rodar([sys.executable, "consultar_querido_diario.py"]); rodar([sys.executable, "consultar_querido_diario.py", "--descobrir-termos"])
    rodar([sys.executable, "atualizar_recursos.py"]); rodar([sys.executable, "verificar_vigencia.py"]); rodar([sys.executable, "analisar_decretos.py"])
    if os.environ.get("PORTAL_TRANSPARENCIA_API_KEY"):
        rodar([sys.executable, "atualizar_transferencias.py"])
    else:
        print("\n[aviso] PORTAL_TRANSPARENCIA_API_KEY ausente — etapa de transferências pulada.")
        print("        Cadastre a chave gratuita em https://portaldatransparencia.gov.br/api-de-dados")

    # 03/09/2026 (achado do ensaio): TODO derivado é regravado DEPOIS de todos os coletores e
    # ANTES dos portões — índice, percentuais, robustez, selos, verificação municipal e resumo,
    # fallback do medidor (recalcular --write); depois as fichas do painel (dependem da
    # verificação), feeds e dados abertos. Relógio fixado no corte (determinismo dos PDFs).
    corte = json.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("corte", "")
    try:
        dd, mm, aa = corte.split("/"); epoch = str(int(datetime.datetime(int(aa), int(mm), int(dd), tzinfo=datetime.timezone.utc).timestamp()))
    except Exception:
        epoch = None
    rodar([sys.executable, "recalcular_mare.py", "--write"], obrigatorio=True, env_extra=({"SOURCE_DATE_EPOCH": epoch} if epoch else None))
    rodar([sys.executable, "gerar_painel.py", "--fichas"], obrigatorio=True)   # §10-bis: reverificação semanal das fichas
    # Artefatos derivados (31/08/2026): função pura dos dados desta rodada; gerados ANTES dos
    # portões, que os conferem (selos × índice; feeds válidos; dados abertos × banco).
    rodar([sys.executable, "gerar_selos.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_feeds.py", "--data", hoje], obrigatorio=True)
    rodar([sys.executable, "gerar_dados_abertos.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_blog.py"], obrigatorio=True)   # 22/09/2026: páginas dos textos, índice e feed do Blog do MARÉ (função pura de blog/posts/*.md)

    rodar(["node", "scripts/verificar_estrutura.js"], obrigatorio=True)

    rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)
    rodar([sys.executable, "verificar_sinais.py"], obrigatorio=True)
    rodar([sys.executable, "verificar_saude.py"], obrigatorio=True)        # §9.6: peso zero provado
    rodar([sys.executable, "verificar_financiamento.py"], obrigatorio=True) # §7.8: peso zero, E10, estresse
    rodar([sys.executable, "verificar_painel.py"], obrigatorio=True)         # §10-bis: lista imutável, fichas, paridade
    rodar([sys.executable, "verificar_evidencias.py"], obrigatorio=True)   # aviso até 09/09, bloqueante depois
    rodar([sys.executable, "recalcular_mare.py", "--check"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_mapas.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_sinais.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_saude.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_financiamento.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_acessibilidade.js"], obrigatorio=True)   # v2.3: a11y + responsividade
    rodar(["node", "scripts/verificar_vocabulario_publico.js"], obrigatorio=True)  # 03/09: sem jargão interno no texto visível
    rodar(["bash", "scripts/verificar_derivados.sh", "--idempotencia"], obrigatorio=True)         # AUD-04: derivados reproduzíveis em árvore limpa

    meta_p = RAIZ / "data" / "meta.json"
    meta = json.load(open(meta_p, encoding="utf-8"))
    meta["atualizado_em"] = hoje
    if hash_arquivo(transf) != antes:
        meta["corte"] = hoje
        print(f"\nTransferências alteradas → corte dos dados atualizado para {hoje}.")
    json.dump(meta, open(meta_p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    # 10/09/2026 (causa-raiz do portão 12 vermelho na main após cada rodada): os três geradores
    # abaixo carimbam `gerado_em` com o `atualizado_em` de data/meta.json (data determinística),
    # mas rodaram ANTES deste carimbo e ficavam um dia atrás. Reexecutá-los aqui é idempotente
    # (função pura dos dados desta rodada, provada por verificar_derivados.sh --idempotencia);
    # só o carimbo muda. O manifesto é selado depois, no workflow, após os PDFs.
    rodar([sys.executable, "gerar_monitor_saude.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_resposta.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_prioritarios.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_contadores_financiamento.py"], obrigatorio=True)
    # 16/09/2026 (handover urgente): o medidor de resposta e as datas de corte ficavam "—" no HTML
    # estático (sem JavaScript) de index.html, saude.html e financiamento.html. Roda por último,
    # depois que meta.json e os quatro geradores acima já têm os dados finais desta rodada.
    rodar([sys.executable, "preencher_fallback_estatico.py"], obrigatorio=True)
    print(f"\n✓ Atualização concluída ({hoje}). Corte vigente: {meta['corte']}.")

if __name__ == "__main__":
    main()
