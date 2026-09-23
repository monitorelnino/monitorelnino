#!/usr/bin/env python3
"""PreToolUse: impede que segredo entre em contexto ou em commit (§167, 23/09/2026).

O QUE PROTEGE, E O QUE NÃO PRECISA PROTEGER. Este repositório é público e NÃO guarda
arquivo de token: os segredos da operação (ROBO_TOKEN, ROBO_DEPLOY_KEY, NETLIFY_AUTH_TOKEN,
PORTAL_TRANSPARENCIA_API_KEY, PREVIA_BASIC_AUTH) vivem como GitHub Actions secrets, fora da
árvore. Proteger um arquivo que não existe daria falsa sensação de segurança.

O que existe e merece porta: `.env` preenchido (o `.env.example` é público e passa), chaves
`*.pem`/`*.key`, e as credenciais do próprio Claude e do gh no diretório do usuário — que
estão fora do repositório mas ao alcance das ferramentas.

Bloqueia em duas frentes:
  1. LEITURA — Read/Edit/Write num caminho de segredo;
  2. SHELL — comando que leia (cat/head/less/grep) ou versione (`git add`) um desses
     caminhos, porque ler por Bash contorna o bloqueio de Read.

Fecha com `permissionDecision: deny`, que é recusa dura: não vira pergunta ao usuário.
"""
import json
import re
import sys

# Caminhos de segredo. `.env.example` é deliberadamente ausente da lista: é público, faz
# parte da documentação de instalação, e bloqueá-lo só atrapalharia.
PADROES = [
    r"(^|/)\.env$", r"(^|/)\.env\.(?!example)[\w.-]+$",
    r"\.pem$", r"\.key$", r"(^|/)id_rsa\b", r"(^|/)id_ed25519\b",
    r"\.claude/\.credentials\.json$",
    r"(^|/)\.config/gh(/|$)", r"(^|/)\.gitconfig$",
    r"(^|/)\.netrc$", r"(^|/)\.npmrc$", r"(^|/)\.pypirc$",
]
RE = [re.compile(p) for p in PADROES]

# Verbos de shell que fariam o conteúdo chegar ao contexto, ou o arquivo ao índice do git.
RE_SHELL = re.compile(
    r"\b(cat|bat|head|tail|less|more|strings|xxd|od|grep|rg|awk|sed|cp|scp|base64)\b"
    r"|\bgit\s+add\b", re.IGNORECASE)


# Heredoc e mensagem de -m são TEXTO, não operando. Achado ao escrever este hook: ele
# bloqueou o commit que o introduzia, porque a mensagem citava ".env" ao explicar a regra.
# Um caminho de segredo dentro de texto livre não abre arquivo nenhum; recusar ali só
# impediria de escrever sobre o assunto — e um controle que atrapalha sem proteger acaba
# desligado, que é o pior desfecho possível.
RE_HEREDOC = re.compile(r"<<-?\s*'?(\w+)'?\n.*?\n\1", re.DOTALL)
RE_MENSAGEM = re.compile(r"""(-m|--message)\s+('([^']*)'|"([^"]*)")""")


def sem_texto_livre(cmd: str) -> str:
    """Remove corpos de heredoc e valores de -m/--message antes de procurar operandos."""
    cmd = RE_HEREDOC.sub(" ", cmd)
    return RE_MENSAGEM.sub(" ", cmd)


def e_segredo(caminho: str) -> bool:
    return any(r.search(caminho or "") for r in RE)


def recusar(motivo: str):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": motivo}}, ensure_ascii=False))
    sys.exit(0)


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — hook nunca derruba a sessão
        return 0
    ferramenta = ev.get("tool_name", "")
    entrada = ev.get("tool_input") or {}

    if ferramenta in ("Read", "Edit", "Write", "NotebookEdit"):
        alvo = entrada.get("file_path") or entrada.get("notebook_path") or ""
        if e_segredo(alvo):
            recusar(f"{alvo} é caminho de segredo: não entra em contexto nem em commit. "
                    "Os segredos da operação vivem como GitHub Actions secrets, fora da árvore.")

    if ferramenta == "Bash":
        cmd = sem_texto_livre(entrada.get("command", "") or "")
        if RE_SHELL.search(cmd):
            # Só recusa se o comando de fato menciona um caminho de segredo — um `git add`
            # comum ou um `grep` em código não pode ser bloqueado por precaução.
            for token in re.findall(r"[\w./~-]+", cmd):
                if e_segredo(token):
                    recusar(f"o comando toca {token}, que é caminho de segredo. "
                            "Leitura e versionamento de segredo ficam bloqueados por hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
