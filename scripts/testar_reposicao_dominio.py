#!/usr/bin/env python3
"""Portão — a rodada semanal precisa terminar restaurando o modo do domínio.

Criado em 20/09/2026 (§120), depois de o domínio passar sete horas servindo a
cortina "Em atualização" no lugar do site completo, sem que nada tivesse falhado.

Defeito original (§120): dois deploys de produção competindo — o ramo `publico`
tinha um workflow próprio disparando a CADA PUSH nele, correndo em paralelo com
o passo final que repunha o site completo. Resolvido primeiro com um `sleep`
torcendo pela ordem (frágil: exposto de novo em 21/09/2026, §133, quando um
disparo urgente falhou). Corrigido de vez em 21/09/2026 (§134): o passo
"Colocar 'em atualização' no domínio" publica a cortina de forma EXPLÍCITA e
SEQUENCIAL logo no início do job, direto por este workflow — sem depender do
gatilho do ramo `publico`. Não há mais dois deploys concorrentes para esperar.

`data/publicacao.json` declara qual estado o domínio deve ter (`dominio`):
  "cortina" — página de rosto do ramo publico ("Em atualização")
  "senha"   — site completo atrás de Basic-Auth, noindex
  "aberto"  — lançamento

Este portão verifica que `atualizar.yml` tem: um passo INICIAL que publica a
cortina "em atualização" direto no domínio (não via push no ramo publico); um
passo FINAL que lê a declaração de `data/publicacao.json` e repõe o domínio
quando ele estiver em "senha"; que o passo final roda DEPOIS do inicial e com
`if: always()` (repõe mesmo se algo no meio do job falhar).

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
    wf_completo = WF.read_text(encoding="utf-8")
    # 21/09/2026 (achado real): o job `repor_dominio_manual` (disparo urgente e independente,
    # fora da rodada semanal) tem um passo com o MESMO nome "Repor o site completo no domínio".
    # Buscar a primeira ocorrência no arquivo inteiro pega esse passo — que vem ANTES do job
    # `atualizar:` no arquivo — e acusa ordem errada mesmo quando a ordem DENTRO do job real
    # está correta. Escopo restrito ao corpo do job `atualizar:`.
    i_job = wf_completo.find("\n  atualizar:")
    if i_job == -1:
        print("✗ job `atualizar:` não encontrado em atualizar.yml")
        return 1
    wf = wf_completo[i_job:]

    # 2. Existe o passo de reposição, e ele consulta a declaração em vez de
    #    assumir um modo fixo.
    if "Repor o site completo no domínio" not in wf:
        falhas.append("atualizar.yml não tem o passo de reposição do domínio — a rodada "
                      "terminaria deixando a cortina por cima do site completo")
    if "data/publicacao.json" not in wf:
        falhas.append("o passo de reposição não lê data/publicacao.json — o modo do domínio "
                      "ficaria codificado no workflow em vez de declarado pela editoria")

    # 3. Existe o passo inicial que publica a cortina direto, sem depender do gatilho do ramo publico.
    i_inicio = wf.find("Colocar \"em atualização\" no domínio")
    if i_inicio == -1:
        falhas.append("atualizar.yml não tem o passo inicial que publica a cortina 'em atualização' "
                      "direto no domínio — sem ele, o domínio mostra o estado anterior (site completo "
                      "ou dado desatualizado) durante toda a rodada, não uma cortina")

    # 4. A ordem: passo inicial vem ANTES do passo final de reposição.
    i_repor = wf.find("Repor o site completo no domínio")
    if i_inicio != -1 and i_repor != -1 and i_repor < i_inicio:
        falhas.append("o passo de reposição final vem ANTES do passo que publica a cortina de "
                      "início — a cortina seria publicada por último e o domínio perderia o modo senha")

    # 5. O passo final roda com if: always() — repõe mesmo se algo no meio do job falhar.
    #    Delimitado pelo próximo passo (não por uma janela fixa de caracteres — frágil a
    #    mudanças no tamanho do comentário do próprio passo).
    if i_repor != -1:
        i_proximo_passo = wf.find("\n      - name:", i_repor)
        trecho_do_passo = wf[i_repor:i_proximo_passo if i_proximo_passo != -1 else len(wf)]
        if "if: always()" not in trecho_do_passo:
            falhas.append("o passo de reposição final não tem `if: always()` — uma falha em "
                          "qualquer passo anterior do job deixaria o domínio sem ser reposto")

    # 6. A senha nunca pode estar no repositório: vem de segredo.
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

    print(f"✓ reposição do domínio: publicacao.json declara {modo!r}; atualizar.yml publica a "
          f"cortina 'em atualização' no início e repõe o site no fim, sem depender de corrida "
          f"entre dois deploys, e tira a credencial de segredo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
