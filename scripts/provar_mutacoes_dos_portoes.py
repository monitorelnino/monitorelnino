#!/usr/bin/env python3
"""Prova que a suíte de portões ainda pega cada defeito do registro (item 3 e 6 do HANDOVER_CONSOLIDACAO).

POR QUE EXISTE. Fundir ou remover um portão só é seguro se a regressão que ele pegava continua
pega. Cada mutação de `scripts/mutacoes_dos_portoes.json` é aplicada no arquivo, os comandos de
`portoes.yml` que casam com `pegam` rodam, e ao menos um tem de reprovar. Trecho sem comando
correspondente no workflow é cobertura perdida (reprova antes de rodar). O arquivo é sempre
restaurado byte a byte. Uso: provar_mutacoes_dos_portoes.py [--id ID] [--so-casar].
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import portoes_locais  # noqa: E402


def comandos_que_casam(pegam, comandos):
    achados = {p: [c for c in comandos if p in c] for p in pegam}
    return achados, [p for p, c in achados.items() if not c]


def aplicar(m, texto):
    if "anexar" in m:
        return texto + m["anexar"]
    antigo, novo = m["trocar"]
    if antigo not in texto:
        raise ValueError(f"âncora ausente em {m['arquivo']}")
    return texto.replace(antigo, novo, 1)


def provar(m, comandos):
    arq = RAIZ / m["arquivo"]
    original = arq.read_bytes()
    try:
        arq.write_text(aplicar(m, original.decode()), encoding="utf-8", newline="")
        return [c for c in comandos if any(p in c for p in m["pegam"])
                and subprocess.run(c, shell=True, cwd=RAIZ, capture_output=True).returncode != 0]
    finally:
        arq.write_bytes(original)


def main(argv):
    todas = json.loads((RAIZ / "scripts" / "mutacoes_dos_portoes.json").read_text())["mutacoes"]
    so = argv[argv.index("--id") + 1] if "--id" in argv else None
    comandos = [c for _, c, _ in portoes_locais.comandos_do_workflow()]
    falhas = []
    for m in todas:
        if so and m["id"] != so:
            continue
        _, orfaos = comandos_que_casam(m["pegam"], comandos)
        if orfaos:
            falhas.append(f"{m['id']}: nenhum comando do portoes.yml casa {orfaos}")
            continue
        if "--so-casar" in argv:
            continue
        mortos = provar(m, comandos)
        print(f"{'✓' if mortos else '✗'} {m['id']}: reprovam {len(mortos)}", flush=True)
        if not mortos:
            falhas.append(f"{m['id']}: nenhum portão pegou a mutação")
    print("MUTAÇÕES: " + ("; ".join(falhas) if falhas else "todas pegas"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
