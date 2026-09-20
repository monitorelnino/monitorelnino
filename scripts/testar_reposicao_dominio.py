#!/usr/bin/env python3
"""Portão — a rodada semanal precisa terminar restaurando o modo do domínio.

Criado em 20/09/2026 (§120), depois de o domínio passar sete horas servindo a
cortina "Em atualização" no lugar do site completo, sem que nada tivesse falhado.

O defeito é estrutural e não se anuncia. O ramo `publico` carrega um workflow
próprio, `publicar_dominio.yml`, que dispara A CADA PUSH naquele ramo e faz deploy
de PRODUÇÃO. A rodada semanal empurra o contador da cortina para lá no fim da
execução. Logo, toda rodada republicava a cortina por cima do site completo e
derrubava o modo senha — silenciosamente, com a Action verde do começo ao fim,
porque do ponto de vista dela nada deu errado.

`data/publicacao.json` declara qual estado o domínio deve ter (`dominio`):
  "cortina" — página de rosto do ramo publico
  "senha"   — site completo atrás de Basic-Auth, noindex
  "aberto"  — lançamento

Este portão verifica que `atualizar.yml` tem um passo final que lê essa declaração
e repõe o domínio quando ele estiver em "senha"; que esse passo roda DEPOIS do
push da cortina (senão os dois deploys correm e o vencedor é sorteio); e que ele
espera o deploy da cortina assentar antes de publicar por cima.

Uso: python3 scripts/testar_reposicao_dominio.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WF = RAIZ / ".github" / "workflows" / "atualizar.yml"
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
        print("✗ .github/workflows/atualizar.yml não existe")
        return 1
    wf = WF.read_text(encoding="utf-8")

    # 2. Existe o passo de reposição, e ele consulta a declaração em vez de
    #    assumir um modo fixo.
    if "Repor o site completo no domínio" not in wf:
        falhas.append("atualizar.yml não tem o passo de reposição do domínio — a rodada "
                      "terminaria deixando a cortina por cima do site completo")
    if "data/publicacao.json" not in wf:
        falhas.append("o passo de reposição não lê data/publicacao.json — o modo do domínio "
                      "ficaria codificado no workflow em vez de declarado pela editoria")

    # 3. A ordem: reposição depois do push da cortina.
    i_cortina = wf.find("Atualizar contador da cortina")
    i_repor = wf.find("Repor o site completo no domínio")
    if i_cortina != -1 and i_repor != -1 and i_repor < i_cortina:
        falhas.append("o passo de reposição vem ANTES do push da cortina — a cortina seria "
                      "publicada por último e o domínio voltaria a perder o modo senha")

    # 4. A espera: sem ela os dois deploys correm.
    if i_repor != -1:
        trecho = wf[i_repor:]
        if not re.search(r"sleep\s+(\d+)", trecho):
            falhas.append("o passo de reposição não espera o deploy da cortina assentar "
                          "(sem `sleep`, os dois deploys de produção correm entre si)")
        else:
            segundos = int(re.search(r"sleep\s+(\d+)", trecho).group(1))
            if segundos < 60:
                falhas.append(f"a espera antes de repor o domínio é de {segundos}s — curta "
                              f"demais para o deploy da cortina (~1 min) assentar")

    # 5. A senha nunca pode estar no repositório: vem de segredo.
    if i_repor != -1:
        trecho = wf[i_repor:]
        if "PREVIA_BASIC_AUTH" not in trecho:
            falhas.append("o passo de reposição não usa o segredo PREVIA_BASIC_AUTH")
        if re.search(r"Basic-Auth:\s*[A-Za-z0-9]", trecho):
            falhas.append("credencial literal de Basic-Auth no workflow — ela precisa vir "
                          "do segredo, o repositório é público")

    if falhas:
        for f in falhas:
            print(f"✗ {f}")
        return 1

    print(f"✓ reposição do domínio: publicacao.json declara {modo!r}; atualizar.yml repõe o "
          f"site depois do push da cortina, com espera, e tira a credencial de segredo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
