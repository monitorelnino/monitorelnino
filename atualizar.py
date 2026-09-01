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

    rodar([sys.executable, "atualizar_boletins.py"])

    # Sinais oficiais de risco (01/09/2026, METODOLOGIA §23): coleta as três camadas
    # para sinais-de-risco.html. NÃO é bloqueante e NÃO toca no índice — fonte fora do
    # ar permanece como lacuna declarada na página, nunca como valor estimado.
    rodar([sys.executable, "coletar_sinais_risco.py"])

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
