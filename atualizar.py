#!/usr/bin/env python3
"""Orquestrador de atualização do Monitor El Niño Brasil.

Etapas:
  1. atualizar_boletins.py  — vigia de novos boletins do Painel El Niño (rede tolerante a falha)
  2. atualizar_instrumentos_estaduais.py — Camada 1 do Protocolo de Busca v2 (Metodologia
     §4.1.1): verifica repositórios estaduais estruturados por município novo/atualizado.
     NUNCA escreve na base; o que lista vira pista (porta única) e o juiz lê o documento
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

Nota (08/11/2026): coletar_sinais_risco.py roda todo dia no elo `noturno_sinais.yml`, não aqui.

Uso: python atualizar.py
"""
import datetime, hashlib, json, os, pathlib, subprocess, sys

RAIZ = pathlib.Path(__file__).parent

# Cadência semanal: publicação no domingo, no fuso da redação (America/Sao_Paulo), nunca no UTC
# do runner. A vez, o `.feito` e o "devido quando" do elo impedem a segunda rodada. Mudou o dia:
# mudar também o cron, o texto público e a documentação (`scripts/testar_cadencia_publicacao.py`).
# O fuso vem de coletores_base: uma definição só.
from coletores_base import FUSO_EDITORIAL, hoje_editorial, gravar_em  # noqa: E402,F401
DIA_PUBLICACAO = 6            # weekday(): 0 = segunda … 5 = sábado, 6 = domingo
NOME_DIA_PUBLICACAO = "domingo"


# Teto por etapa: fonte lenta mata só a sua etapa (lacuna declarada) e a rodada segue.
TETO_ETAPA_S = 45 * 60          # etapas pesadas do dia de publicação
TETO_ETAPA_DIARIA_S = 15 * 60   # coletores que rodam todo dia e nunca pontuam


def rodar(cmd, obrigatorio=False, env_extra=None, teto_s=TETO_ETAPA_S):
    """Executa um subprocesso do pipeline; se obrigatorio=True, aborta o processo com o mesmo código de saída em caso de falha."""
    # flush: o cabeçalho da etapa sai antes da saída do subprocesso.
    print(f"\n=== {' '.join(cmd)} ===", flush=True)
    env = {**os.environ, **(env_extra or {})}
    _inicio = datetime.datetime.now().replace(microsecond=0)
    try:
        codigo = subprocess.run(cmd, cwd=RAIZ, env=env, timeout=teto_s).returncode
    except subprocess.TimeoutExpired:
        # O filho é morto (netos podem sobreviver até o fim do job); a rodada segue.
        codigo = 124
        print(f"[aviso] etapa estourou o teto de {teto_s // 60} min e foi encerrada: "
              f"{' '.join(cmd)} — tratada como fonte fora do ar (lacuna declarada), "
              f"a rodada continua", flush=True)
    sys.stdout.flush()
    # Toda etapa grava a sua linha de saúde; o registro nunca derruba a rodada.
    try:
        from scripts.saude_pipeline import registrar as _registrar_saude
        _nome = next((a for a in cmd if str(a).endswith(".py")), " ".join(map(str, cmd)))
        _registrar_saude(script=_nome, inicio=_inicio.isoformat(),
                         duracao_s=(datetime.datetime.now() - _inicio).total_seconds(),
                         itens=None, status="ok" if codigo == 0 else "erro",
                         erro="" if codigo == 0 else f"código de saída {codigo}")
    except Exception as _e:  # noqa: BLE001
        print(f"[aviso] linha de saúde não registrada para {' '.join(map(str, cmd))}: {_e}",
              flush=True)
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
    # Data da edição: fixada no início da rodada, no fuso da redação.
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    transf = RAIZ / "data" / "transferencias.json"
    antes = hash_arquivo(transf)

    # Cadência antes de qualquer coleta: em dia não publicável nada muda.
    intensivo = os.environ.get("INTENSIVO_ATE", "")
    intensivo_de = os.environ.get("INTENSIVO_DE", "") or intensivo  # sem início declarado, vale só o fim
    hoje_iso = hoje_editorial().isoformat()
    dia_semana = hoje_editorial().weekday()  # no fuso da redação, nunca no do runner (ver topo)
    em_intensivo = bool(intensivo) and intensivo_de <= hoje_iso <= intensivo

    # Sinais de risco: coletados pelo elo `noturno_sinais.yml` (dono único). O derivado que os copia
    # (`monitor_saude.json`) é regravado todo dia; idempotente.
    rodar([sys.executable, "gerar_monitor_saude.py"], teto_s=TETO_ETAPA_DIARIA_S)

    if not em_intensivo and dia_semana != DIA_PUBLICACAO:
        print(f"[cadência] fora da semana intensiva e não é {NOME_DIA_PUBLICACAO} "
              f"(hoje é {hoje_editorial():%d/%m/%Y} no fuso da redação): "
              f"execução diária encerra sem coletar nem comitar.")
        return 0

    rodar([sys.executable, "atualizar_boletins.py"])

    # Coletores da Pista A: nenhum bloqueia nem pontua; fonte fora do ar é lacuna declarada.
    # Lotes da semana intensiva (§13) controlados por INTENSIVO_ATE (variável de repositório).
    rodar([sys.executable, "coletar_s2id.py"])
    rodar([sys.executable, "coletar_declarado_nacional.py"])
    rodar([sys.executable, "coletar_doe.py"])                       # 27 UFs; sem adaptador = lacuna
    lote = os.environ.get("LOTE_DIARIOS") or ""
    if not lote:
        # lote rotativo D1..D7 na semana intensiva (no fuso da redação); fora dela, lote 1.
        if em_intensivo:
            decorridos = (hoje_editorial() - datetime.date.fromisoformat(intensivo_de)).days
            lote = str(max(1, min(7, decorridos + 1)))  # D0 = lote 1 … D6+ = lote 7
        else:
            lote = "1"
    if em_intensivo and not os.environ.get("LOTE_DIARIOS"):
        # Semana intensiva: varredura integral, lote recalculado para caber nos dias que restam.
        rodar([sys.executable, "coletar_diarios_municipais.py", "--pendentes-desde", intensivo_de, "--ate", intensivo,
               "--tamanho", os.environ.get("TAMANHO_LOTE", "150")])
    else:
        rodar([sys.executable, "coletar_diarios_municipais.py", "--lote", lote, "--tamanho", os.environ.get("TAMANHO_LOTE", "150")])
    # Diários consorciados: janela curta (8 dias); varrer o ciclo inteiro é rodada dedicada.
    rodar([sys.executable, "coletar_diarios_consorciados.py", "--desde",
           (hoje_editorial() - datetime.timedelta(days=8)).isoformat(),
           "--ate", hoje_editorial().isoformat()])
    rodar([sys.executable, "preservar_evidencias.py"])                 # idempotente; §3.8
    rodar([sys.executable, "preservar_evidencias.py", "--reconferir"])  # §3.8-bis: rebaixa e compara o hash; alteração vira evento
    rodar([sys.executable, "coletar_srag_gripe.py"])                      # SRAG/SG nacional e por UF, InfoGripe; peso zero
    rodar([sys.executable, "coletar_espin.py"])                       # ESPIN no DOU, vigilância contínua; fila R7
    # SICONFI: com `pendentes` vazio não faz nada; na virada do exercício preenche em lotes.
    rodar([sys.executable, "coletar_siconfi_182.py", "--lote", "300"])  # DCA/SICONFI, retomável por lote
    rodar([sys.executable, "preservar_evidencias.py", "--ler", "--limite", "40"])   # §10.1: texto por página dos PDFs de planos
    rodar([sys.executable, "gerar_resposta.py"])                        # v3.1 §3: contador de resposta; peso zero (verificar_resposta.py)
    rodar([sys.executable, "gerar_prioritarios.py"])                    # municípios prioritários (aproximação populacional), fonte única do mapa e da busca
    rodar([sys.executable, "gerar_contadores_financiamento.py"])       # v3.1 §11: quatro contadores por UF; peso zero
    rodar([sys.executable, "coletar_financiamento.py"])                 # §7.8: Portal (chave), rotas; peso zero
    rodar([sys.executable, "coletar_transferegov.py"])                  # transferências sem chave (TransfereGov dados abertos); r5 na série
    rodar([sys.executable, "coletar_execucao_mps.py"])                  # execução das ações das MPs 1.367/1.384 (arquivos mensais abertos)

    rodar([sys.executable, "verificar_contribuicoes.py"])

    # Não bloqueia, mas retorno != 0 é verificação INCOMPLETA, nunca "sem novidades". O que o
    # repositório lista vira pista na porta única e vai ao juiz (§106).
    if not rodar([sys.executable, "atualizar_instrumentos_estaduais.py", "--pistas"]):
        print("\n[aviso] a varredura de repositórios estaduais ficou INCOMPLETA (ver mensagens acima).")
        print("        Os dados publicados seguem válidos, mas esta rodada não confirma ausência de novidades.")

    # Querido Diário: um território por chamada; toda pista passa pelo juiz.
    rodar([sys.executable, "consultar_querido_diario.py"])
    rodar([sys.executable, "atualizar_recursos.py"]); rodar([sys.executable, "verificar_vigencia.py"]); rodar([sys.executable, "analisar_decretos.py"])
    if os.environ.get("PORTAL_TRANSPARENCIA_API_KEY"):
        rodar([sys.executable, "atualizar_transferencias.py"])
    else:
        print("\n[aviso] PORTAL_TRANSPARENCIA_API_KEY ausente — etapa de transferências pulada.")
        print("        Cadastre a chave gratuita em https://portaldatransparencia.gov.br/api-de-dados")

    # Ordem: coletores → carimbo da rodada (`atualizado_em` e `corte`) → derivados → portões, que
    # conferem o carimbo desta rodada. O relógio dos derivados (SOURCE_DATE_EPOCH) é o do corte de hoje.
    meta_p = RAIZ / "data" / "meta.json"
    meta = json.load(open(meta_p, encoding="utf-8"))
    meta["atualizado_em"] = hoje
    # O corte é a data da última rodada de coleta que alimentou o índice: hoje, mesmo sem novidade.
    meta["corte"] = hoje
    gravar_em(meta_p, meta)

    corte = meta["corte"]
    try:
        dd, mm, aa = corte.split("/"); epoch = str(int(datetime.datetime(int(aa), int(mm), int(dd), tzinfo=datetime.timezone.utc).timestamp()))
    except Exception:
        epoch = None
    rodar([sys.executable, "recalcular_mare.py", "--write"], obrigatorio=True, env_extra=({"SOURCE_DATE_EPOCH": epoch} if epoch else None))
    rodar([sys.executable, "gerar_painel.py", "--fichas"], obrigatorio=True)   # §10-bis: reverificação semanal das fichas
    # Derivados: função pura dos dados desta rodada, gerados antes dos portões que os conferem.
    rodar([sys.executable, "gerar_selos.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_feeds.py", "--data", hoje], obrigatorio=True)
    rodar([sys.executable, "gerar_dados_abertos.py"], obrigatorio=True)

    rodar(["node", "scripts/verificar_estrutura.js"], obrigatorio=True)

    rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)
    rodar([sys.executable, "verificar_sinais.py"], obrigatorio=True)
    rodar([sys.executable, "verificar_saude.py"], obrigatorio=True)        # §9.6: peso zero provado
    rodar([sys.executable, "verificar_financiamento.py"], obrigatorio=True) # §7.8: peso zero, E10, estresse
    rodar([sys.executable, "verificar_painel.py"], obrigatorio=True)         # §10-bis: lista imutável, fichas, paridade
    rodar([sys.executable, "verificar_evidencias.py"], obrigatorio=True)
    rodar([sys.executable, "recalcular_mare.py", "--check"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_mapas.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_sinais.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_saude.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_financiamento.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_acessibilidade.js"], obrigatorio=True)   # v2.3: a11y + responsividade
    rodar(["node", "scripts/verificar_texto_publico.js"], obrigatorio=True)  # sem jargão interno no texto visível
    rodar(["bash", "scripts/verificar_derivados.sh", "--idempotencia"], obrigatorio=True)         # AUD-04: derivados reproduzíveis em árvore limpa

    if hash_arquivo(transf) != antes:
        print("\nTransferências alteradas nesta rodada.")
    # Regravados depois do carimbo (`gerado_em` = `atualizado_em`); idempotentes. O manifesto é
    # selado no workflow, depois dos PDFs.
    rodar([sys.executable, "gerar_monitor_saude.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_resposta.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_prioritarios.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_contadores_financiamento.py"], obrigatorio=True)
    # Fallback estático (sem JavaScript) por último, com os dados finais da rodada.
    rodar([sys.executable, "preencher_fallback_estatico.py"], obrigatorio=True)
    print(f"\n✓ Atualização concluída ({hoje}). Corte vigente: {meta['corte']}.")

if __name__ == "__main__":
    main()
