#!/usr/bin/env python3
"""
atualizar_contador_cortina.py
==============================
Publica um contador OPERACIONAL (quantos municípios já foram consultados na
varredura dos diários oficiais municipais, sobre quantos no total) no ramo
`publico` — a cortina "Em atualização" que fica no domínio público enquanto
o site completo está em prévia. Nunca afirma existência ou inexistência de
plano; nunca escreve dado do índice. Fonte única: data/verificacao_resumo.json
(campo `varredura_diarios`, já calculado por recalcular_mare.py).

Roda como parte de atualizar.py, DEPOIS do commit na `main`, e só se algo
mudou. Clona o `publico` à parte (histórico independente de propósito — não
é um branch de trabalho do site) e faz um commit simples, sem PR: o ramo
`publico` não tem os portões do site (é só uma página estática) e sua única
regra é não deletar / não force-push (garantida pelo ruleset do GitHub, não
por este script).
"""
import json, subprocess, sys, os
from pathlib import Path
from datetime import datetime, timezone

RAIZ = Path(__file__).resolve().parent.parent


def numeros_da_varredura() -> dict | None:
    p = RAIZ / "data" / "verificacao_resumo.json"
    if not p.exists():
        return None
    vd = json.loads(p.read_text(encoding="utf-8")).get("varredura_diarios")
    if not vd or not vd.get("consultados"):
        return None
    return {"consultados": vd["consultados"], "total": vd["total"]}


def hora_brasilia_texto() -> str:
    # Sem dependência de tzdata no runner: Brasília = UTC-3 o ano todo (sem horário de verão desde 2019).
    return (datetime.now(timezone.utc).astimezone(
        timezone.utc).replace(tzinfo=None)).strftime("%Hh%M, %d/%m/%Y") + " (UTC)"


def houve_mudanca(anterior: dict, dado: dict) -> bool:
    """Só publica de novo se os números mudaram (evita commit vazio no ramo publico a cada rodada sem progresso novo)."""
    return anterior.get("consultados") != dado["consultados"] or anterior.get("total") != dado["total"]


def autoteste() -> int:
    sys.path.insert(0, str(RAIZ))  # coletores_base.py vive na raiz do repo, este script em scripts/
    from coletores_base import rodar_autoteste  # reaproveita o runner de autotestes do projeto

    def t1():  # números ausentes → None, nunca exceção
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            global RAIZ
            antigo = RAIZ
            RAIZ = Path(d)
            try:
                return numeros_da_varredura() is None
            finally:
                RAIZ = antigo

    def t2():  # dedup: mesmos números não republica; números diferentes republicam
        a = {"consultados": 688, "total": 5571}
        return (not houve_mudanca(a, {"consultados": 688, "total": 5571})
                and houve_mudanca(a, {"consultados": 1200, "total": 5571}))

    def t3():  # formato da hora: dia e mês com 2 dígitos
        import re
        return bool(re.match(r"^\d{2}h\d{2}, \d{2}/\d{2}/\d{4} \(UTC\)$", hora_brasilia_texto()))

    return rodar_autoteste({"sem arquivo de verificação: não quebra": t1,
                            "dedup: só publica se os números mudaram": t2,
                            "formato de hora previsível": t3})


def main() -> int:
    numeros = numeros_da_varredura()
    if numeros is None:
        print("contador da cortina: sem números de varredura ainda — nada a publicar")
        return 0
    token = os.environ.get("ROBO_DEPLOY_KEY_SSH_DIR")  # caminho da chave já configurada pelo chamador
    if not token:
        print("::error::ROBO_DEPLOY_KEY_SSH_DIR não definido — contador da cortina não publicado")
        return 1
    repo = os.environ.get("GITHUB_REPOSITORY", "monitorelnino/monitorelnino")
    tmp = Path("/tmp/publico_cortina")
    subprocess.run(["rm", "-rf", str(tmp)], check=True)
    env_ssh = {"GIT_SSH_COMMAND": f"ssh -i {token} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"}
    subprocess.run(["git", "clone", "-q", "--branch", "publico", "--depth", "1",
                     f"git@github.com:{repo}.git", str(tmp)], check=True, env={**os.environ, **env_ssh})
    destino = tmp / "progresso.json"
    dado = {
        "_governanca": ("Contador operacional da varredura dos diários municipais (Querido Diário), "
                        "publicado no domínio para acompanhamento durante a semana intensiva. Não afirma "
                        "existência ou inexistência de plano; consultar não é verificar. Gerado por "
                        "scripts/atualizar_contador_cortina.py a cada rodada do robô."),
        "consultados": numeros["consultados"],
        "total": numeros["total"],
        "atualizado_em": hora_brasilia_texto(),
    }
    anterior = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    if not houve_mudanca(anterior, numeros):
        print("contador da cortina: sem mudança nos números — não publica de novo")
        return 0
    destino.write_text(json.dumps(dado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp), "config", "user.name", "monitor-el-nino-bot"], check=True)
    subprocess.run(["git", "-C", str(tmp), "config", "user.email", "bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "-C", str(tmp), "add", "progresso.json"], check=True)
    subprocess.run(["git", "-C", str(tmp), "commit", "-q", "-m",
                     f"Contador: {dado['consultados']}/{dado['total']} municípios consultados ({dado['atualizado_em']})"],
                    check=True)
    subprocess.run(["git", "-C", str(tmp), "push", "-q", "origin", "HEAD:publico"], check=True, env={**os.environ, **env_ssh})
    print(f"contador da cortina publicado: {dado['consultados']}/{dado['total']}")
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    sys.exit(main())
