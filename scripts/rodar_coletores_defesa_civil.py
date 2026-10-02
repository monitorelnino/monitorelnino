#!/usr/bin/env python3
"""Roda os coletores da Defesa civil e registra cada tentativa no painel, com a cadência declarada.

Item 6 do handover de 02/10/2026. O problema que isto resolve: a página lê nove arquivos de oito
coletores diferentes, cada um com a sua cadência, e **falha de coleta não aparecia** — a série
ficava parada e a página continuava igual, o que é pior do que a falha, porque não se distingue de
dado que não mudou. O portão de frescor (`scripts/verificar_frescor_defesa_civil.py`) mede o atraso
depois do fato; este runner registra a TENTATIVA: o que rodou, quando, com que resultado e com que
cadência declarada.

A cadência vive aqui, declarada por coletor, e não espalhada em comentário de cada arquivo:

- **semanal** — decretos, reconhecimentos, recursos de resposta e as três listas federais de risco.
- **a cada publicação** — avisos do Inmet e alertas do Cemaden. São informação de *agora*; o portão
  de frescor deles é de 24 horas, e a página declara "sem atualização desde…" se passar disso.

Uso:
    python3 scripts/rodar_coletores_defesa_civil.py              # roda todos
    python3 scripts/rodar_coletores_defesa_civil.py --agora      # só os de cadência "a cada publicação"
    python3 scripts/rodar_coletores_defesa_civil.py --listar
    python3 scripts/rodar_coletores_defesa_civil.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# (coletor, argumentos, cadência declarada, arquivos que ele alimenta na página)
COLETORES = (
    ("coletar_sinais_risco.py", [], "a cada publicação", ["alertas/vigentes.json"]),
    ("coletar_s2id.py", [], "semanal", ["atos_resposta.json"]),
    ("coletar_recursos_resposta.py", [], "semanal", ["resposta/recursos_liberados.json"]),
    ("coletar_cadastro_prioritarios.py", [], "semanal", ["cadastro_prioritarios_federal.json"]),
    ("coletar_semiarido_sudene.py", [], "semanal", ["enquadramento_federal.json"]),
    ("coletar_prioritarios_mma.py", [], "semanal", ["enquadramento_federal.json"]),
    ("gerar_resposta.py", [], "semanal", ["resposta/municipios_decretados.json",
                                          "resposta/por_uf.json",
                                          "resposta/serie_semanal.json"]),
)
CADENCIA_DE_AGORA = "a cada publicação"


def selecionar(argv) -> list:
    """Os coletores a rodar. Função pura."""
    if "--agora" in argv:
        return [c for c in COLETORES if c[2] == CADENCIA_DE_AGORA]
    return list(COLETORES)


def linha_do_painel(coletor: str, cadencia: str, alimenta: list, codigo: int,
                    segundos: float, cauda: str) -> dict:
    """A linha que vai para o painel. Função pura — é ela que o autoteste exercita.

    `ok` é o veredito, e `motivo` existe só quando há o que dizer: linha de painel que sempre traz
    um campo de erro vazio ensina a ignorar o campo de erro.
    """
    linha = {"coletor": coletor, "cadencia_declarada": cadencia, "alimenta": list(alimenta),
             "ok": codigo == 0, "codigo": codigo, "segundos": round(segundos, 1),
             "pagina": "defesa-civil.html"}
    if codigo != 0:
        linha["motivo"] = (cauda or "").strip()[-400:] or "sem saída"
    return linha


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("--agora seleciona só os de agora",
       [c[0] for c in selecionar(["--agora"])] == ["coletar_sinais_risco.py"])
    ok("sem argumento roda todos", len(selecionar([])) == len(COLETORES))
    boa = linha_do_painel("x.py", "semanal", ["a.json"], 0, 1.23, "")
    ok("linha de sucesso diz ok", boa["ok"] and boa["codigo"] == 0)
    ok("linha de sucesso não traz motivo", "motivo" not in boa)
    ok("linha de sucesso declara a cadência", boa["cadencia_declarada"] == "semanal")
    ruim = linha_do_painel("x.py", "semanal", ["a.json"], 1, 2.0, "Traceback: erro")
    ok("linha de falha diz não ok", ruim["ok"] is False)
    ok("linha de falha traz o motivo", "erro" in ruim["motivo"])
    ok("falha sem saída diz 'sem saída'",
       linha_do_painel("x.py", "semanal", [], 1, 0.0, "")["motivo"] == "sem saída")
    ok("toda entrada declara cadência", all(c[2] for c in COLETORES))
    ok("toda entrada declara o que alimenta", all(c[3] for c in COLETORES))
    ok("todo coletor existe no repositório", all((RAIZ / c[0]).exists() for c in COLETORES))
    ok("os alertas são os únicos de cadência 'a cada publicação'",
       [c[0] for c in COLETORES if c[2] == CADENCIA_DE_AGORA] == ["coletar_sinais_risco.py"])
    ok("o gerador vem por último (ele depende dos coletores)",
       COLETORES[-1][0] == "gerar_resposta.py")

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 13 casos, sem rede e sem escrita em data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    alvos = selecionar(sys.argv)
    if "--listar" in sys.argv:
        for c, _a, cad, alim in alvos:
            print(f"{c:36s} {cad:22s} {', '.join(alim)}")
        return 0

    sys.path.insert(0, str(RAIZ))
    from coletores_base import registrar_tentativa_coletor

    falhou = []
    for coletor, args, cadencia, alimenta in alvos:
        print(f"→ {coletor} ({cadencia})")
        t0 = time.time()
        r = subprocess.run([sys.executable, coletor] + args, cwd=str(RAIZ),
                           capture_output=True, text=True)
        linha = linha_do_painel(coletor, cadencia, alimenta, r.returncode,
                               time.time() - t0, (r.stderr or r.stdout or ""))
        registrar_tentativa_coletor(coletor, linha)
        if r.returncode != 0:
            falhou.append(coletor)
            print("   ✗ " + linha.get("motivo", "")[:200])
        else:
            print(f"   ✓ {linha['segundos']}s")

    if falhou:
        print(f"✗ {len(falhou)} coletor(es) da Defesa civil falharam: {', '.join(falhou)}")
        return 1
    print(f"✓ {len(alvos)} coletor(es) da Defesa civil rodaram, com a tentativa registrada no painel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
