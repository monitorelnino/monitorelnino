#!/usr/bin/env python3
"""Portão — quem publica dado repõe o domínio no modo que `data/publicacao.json` declara.

Criado em 20/09/2026 (§120), quando o domínio passou sete horas servindo a cortina "Em atualização"
no lugar do site completo. Desde 14/10/2026 (decisão 2 da editoria) a rodada semanal não publica
cortina nem repõe o domínio: ela é um elo como os outros, e quem repõe é o publicador
(`publicar_dados.yml`, por `workflow_run` depois do commit). Este portão cobra do publicador:
o passo de reposição existe, lê a declaração em vez de fixar um modo, e tira a credencial de segredo.

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
        if "data/publicacao.json" not in trecho:
            falhas.append("o passo de reposição não lê data/publicacao.json — o modo do domínio "
                          "ficaria codificado no workflow em vez de declarado pela editoria")
        if "PREVIA_BASIC_AUTH" not in trecho:
            falhas.append("o passo de reposição não usa o segredo PREVIA_BASIC_AUTH")
        if re.search(r"Basic-Auth:\s*[A-Za-z0-9]", trecho):
            falhas.append("credencial literal de Basic-Auth no workflow — ela precisa vir "
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
