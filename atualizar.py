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
  7b. verificar_runtime_mapas.js — mapas-e-graficos.html roda em navegador simulado
  7c. verificar_runtime_sinais.js — sinais-de-risco.html roda em navegador simulado
     (obrigatória; falha bloqueia; página própria desde 31/08/2026)
  8. data/meta.json — carimbo de atualização (e novo corte, se a etapa 3 alterou dados)

Quando o passo 2 gerar propostas: revise data/instrumentos_revisar.json, apague o que
não deve entrar, e rode `python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json`
— esse script mescla a revisão aprovada, recalcula o índice e roda os três portões.

Uso: python atualizar.py
"""
import datetime, hashlib, json, os, pathlib, subprocess, sys

RAIZ = pathlib.Path(__file__).parent

def rodar(cmd, obrigatorio=False, env_extra=None):
    """Executa um subprocesso do pipeline; se obrigatorio=True, aborta o processo com o mesmo código de saída em caso de falha."""
    print(f"\n=== {' '.join(cmd)} ===")
    env = {**os.environ, **(env_extra or {})}
    r = subprocess.run(cmd, cwd=RAIZ, env=env)
    if r.returncode != 0 and obrigatorio:
        print(f"[erro] etapa obrigatória falhou: {' '.join(cmd)}")
        sys.exit(r.returncode)
    return r.returncode == 0

def hash_arquivo(p):
    """SHA-256 do conteúdo do arquivo (string vazia se ainda não existir), usado para detectar se a etapa de transferências mudou os dados."""
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ""

def main():
    """Executa as oito etapas do pipeline canônico em ordem, na sequência declarada no docstring do módulo."""
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    transf = RAIZ / "data" / "transferencias.json"
    antes = hash_arquivo(transf)

    # v2.2.4 (E4/§13): cadência ANTES de qualquer coleta — em dia não publicável nada muda.
    intensivo = os.environ.get("INTENSIVO_ATE", "")
    dia_semana = datetime.date.today().weekday()  # 0 = segunda
    em_intensivo = bool(intensivo) and datetime.date.today().isoformat() <= intensivo
    if not em_intensivo and dia_semana != 0:
        print("[cadência] fora da semana intensiva e não é segunda-feira: execução diária encerra sem coletar nem comitar.")
        return 0

    rodar([sys.executable, "atualizar_boletins.py"])

    # Sinais oficiais de risco (01/09/2026, METODOLOGIA §23): coleta as três camadas
    # para sinais-de-risco.html. NÃO é bloqueante e NÃO toca no índice — fonte fora do
    # ar permanece como lacuna declarada na página, nunca como valor estimado.
    rodar([sys.executable, "coletar_sinais_risco.py"])

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
        # fora do intensivo (segunda-feira semanal) usa o lote 1 — os lotes seguintes são pós-defeso (§13)
        if em_intensivo:
            faltam = (datetime.date.fromisoformat(intensivo) - datetime.date.today()).days
            lote = str(max(1, 7 - faltam))
        else:
            lote = "1"
    rodar([sys.executable, "coletar_diarios_municipais.py", "--lote", lote, "--tamanho", os.environ.get("TAMANHO_LOTE", "150")])
    rodar([sys.executable, "recalcular_mare.py", "--simular-declarado-nacional"])  # anexo público; não altera indice.json
    rodar([sys.executable, "preservar_evidencias.py"])                 # idempotente; §3.8

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

    if os.environ.get("PORTAL_TRANSPARENCIA_API_KEY"):
        rodar([sys.executable, "atualizar_transferencias.py"])
    else:
        print("\n[aviso] PORTAL_TRANSPARENCIA_API_KEY ausente — etapa de transferências pulada.")
        print("        Cadastre a chave gratuita em https://portaldatransparencia.gov.br/api-de-dados")

    # Artefatos derivados (31/08/2026): função pura dos dados desta rodada; gerados ANTES dos
    # portões, que os conferem (selos × índice; feeds válidos; dados abertos × banco).
    rodar([sys.executable, "gerar_selos.py"], obrigatorio=True)
    rodar([sys.executable, "gerar_feeds.py", "--data", hoje], obrigatorio=True)
    rodar([sys.executable, "gerar_dados_abertos.py"], obrigatorio=True)

    rodar(["node", "scripts/verificar_estrutura.js"], obrigatorio=True)

    rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)
    rodar([sys.executable, "verificar_sinais.py"], obrigatorio=True)
    rodar([sys.executable, "verificar_evidencias.py"], obrigatorio=True)   # aviso até 09/09, bloqueante depois
    rodar([sys.executable, "recalcular_mare.py", "--check"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_mapas.js"], obrigatorio=True)
    rodar(["node", "scripts/verificar_runtime_sinais.js"], obrigatorio=True)

    meta_p = RAIZ / "data" / "meta.json"
    meta = json.load(open(meta_p, encoding="utf-8"))
    meta["atualizado_em"] = hoje
    if hash_arquivo(transf) != antes:
        meta["corte"] = hoje
        print(f"\nTransferências alteradas → corte dos dados atualizado para {hoje}.")
    json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✓ Atualização concluída ({hoje}). Corte vigente: {meta['corte']}.")

if __name__ == "__main__":
    main()
