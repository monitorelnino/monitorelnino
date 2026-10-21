#!/usr/bin/env python3
"""Portão — quem publica dado repõe o domínio no modo que `data/publicacao.json` declara.

Criado em 20/09/2026 (§120), quando o domínio passou sete horas servindo a cortina "Em atualização"
no lugar do site completo. Desde 14/10/2026 (decisão 2 da editoria) a rodada semanal não publica
cortina nem repõe o domínio: ela é um elo como os outros, e quem repõe é o publicador
(`publicar_dados.yml`, por `workflow_run` depois do commit). Este portão cobra do publicador:
o passo de reposição existe e chama o script único, que lê a declaração em vez de fixar um modo e tira a credencial de segredo.

`data/publicacao.json` declara qual estado o domínio deve ter (`dominio`):
  "cortina" · "senha" (site completo atrás de Basic-Auth, noindex) · "aberto" (lançamento)

Uso: python3 scripts/testar_reposicao_dominio.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WF = RAIZ / ".github" / "workflows" / "publicar_dados.yml"
PASSO = "Repor o site no domínio, atrás de senha"
PUBLICACAO = RAIZ / "data" / "publicacao.json"

MODOS_VALIDOS = {"cortina", "senha", "aberto"}


def main() -> int:
    falhas = []

    # 1. A declaração existe e é um modo conhecido.
    if not PUBLICACAO.exists():
        print("✗ data/publicacao.json não existe — é ele que declara o modo do domínio")
        return 1
    modo = json.loads(PUBLICACAO.read_text(encoding="utf-8")).get("dominio", "")
    if modo not in MODOS_VALIDOS:
        falhas.append(f"data/publicacao.json · dominio = {modo!r} não é um modo conhecido "
                      f"({', '.join(sorted(MODOS_VALIDOS))})")

    if not WF.exists():
        print(f"✗ {WF.relative_to(RAIZ)} não existe")
        return 1
    wf = WF.read_text(encoding="utf-8")
    i_repor = wf.find(PASSO)
    if i_repor == -1:
        falhas.append(f"{WF.name} não tem o passo \"{PASSO}\" — o dado novo não chegaria ao domínio")
    else:
        fim = wf.find("\n      - name:", i_repor)
        trecho = wf[i_repor:fim if fim != -1 else len(wf)]
        if "scripts/repor_dominio.sh" not in trecho:
            falhas.append("o passo de reposição não chama scripts/repor_dominio.sh — o deploy do domínio é UM só")
        if "PREVIA_BASIC_AUTH" not in trecho:
            falhas.append("o passo de reposição não repassa o segredo PREVIA_BASIC_AUTH")
    # 21/10/2026: o domínio segue a `main` porque o publicador espera o workflow de portões pelo NOME;
    # se o nome mudar ou o gatilho sair, a dependência quebra calada (domínio parado de 07 a 20/10).
    bloco = wf.split("workflow_run:", 1)[-1].split("concurrency:", 1)[0]
    nome = next((n for n in re.findall(r'^\s*- "([^"]+)"', bloco, re.M) if n.startswith("Portões")), None)
    if nome is None:
        falhas.append("publicar_dados.yml não espera o workflow de portões — merge não republicaria o domínio")
    else:
        pr = [f for f in (RAIZ / ".github" / "workflows").glob("*.yml")
              if re.search(rf"^name:\s*{re.escape(nome)}\s*$", f.read_text(encoding="utf-8"), re.M)]
        if not pr or "pull_request" not in pr[0].read_text(encoding="utf-8"):
            falhas.append(f"o publicador espera \"{nome}\", mas nenhum workflow com esse nome dispara em pull_request")
    sh = (RAIZ / "scripts" / "repor_dominio.sh").read_text(encoding="utf-8")
    if "data/publicacao.json" not in sh:
        falhas.append("repor_dominio.sh não lê data/publicacao.json — o modo do domínio ficaria "
                      "codificado em vez de declarado pela editoria")
    if re.search(r"Basic-Auth:\s*[A-Za-z0-9]", sh):
        falhas.append("credencial literal de Basic-Auth em repor_dominio.sh — ela precisa vir "
                      "do segredo, o repositório é público")
    if falhas:
        for f in falhas:
            print(f"✗ {f}")
        return 1

    print(f"✓ reposição do domínio: publicacao.json declara {modo!r}; o publicador repõe o "
          f"domínio lendo a declaração, com a credencial de segredo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
