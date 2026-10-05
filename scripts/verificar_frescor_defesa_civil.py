#!/usr/bin/env python3
"""Portão de frescor dos dados da Defesa civil (handover de 02/10/2026, item 6).

Duas réguas, e a razão de serem duas é de segurança, não de método:

- **Cadência semanal, limite de 9 dias** — decretos, reconhecimentos, tipos de evento, recursos de
  resposta e as três listas federais de risco. Uma semana de cadência mais dois dias de folga.
- **Aviso e alerta: limite de 24 HORAS.** Eles são informação de *agora*, que a população pode usar
  para se proteger. Um retrato de três dias atrás mostrado como "em vigor" não é apenas velho: é
  enganoso, e aqui enganoso pode machucar. Por isso o limite é de horas, e por isso a página tem o
  comportamento de reserva correspondente — passando das 24 horas ela declara "sem atualização
  desde {data e hora}" em vez de desenhar alerta nenhum. O portão existe para que a declaração seja
  exceção visível, e não o estado normal da página.

O portão é função pura sobre os carimbos: ele não coleta, não escreve e não acessa rede. Tem
autoteste offline.

Uso:
    python3 scripts/verificar_frescor_defesa_civil.py            # portão
    python3 scripts/verificar_frescor_defesa_civil.py --json     # para outro programa ler
    python3 scripts/verificar_frescor_defesa_civil.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LIMITE_DIAS = 9
LIMITE_HORAS_ALERTA = 24

# Cadência semanal (decisão da editoria, 02/10/2026). O limite é do ARQUIVO, não do fato que ele
# descreve: lista federal publicada em 2024 e coletada ontem está fresca.
SEMANAIS = (
    "resposta/municipios_decretados.json",
    "resposta/por_uf.json",
    "resposta/serie_semanal.json",
    "resposta/recursos_liberados.json",
    "atos_resposta.json",
    "cadastro_prioritarios_federal.json",
    "enquadramento_federal.json",
)
# Informação de AGORA: medida em horas.
DE_AGORA = ("alertas/vigentes.json",)

CAMPOS_DE_DATA = ("gerado_em", "atualizado_em", "coletado_em", "corte")


def marca_do_arquivo(d: dict):
    """O carimbo mais recente que o arquivo declara, como (ISO, hora_ou_None). Função pura."""
    melhor = None
    for campo in CAMPOS_DE_DATA:
        bruto = (d or {}).get(campo)
        if not isinstance(bruto, str):
            continue
        iso, hora = None, None
        try:
            iso = dt.datetime.strptime(bruto[:10], "%d/%m/%Y").date().isoformat()
        except ValueError:
            try:
                iso = dt.datetime.strptime(bruto[:10], "%Y-%m-%d").date().isoformat()
            except ValueError:
                continue
        resto = bruto[10:].strip()
        if len(resto) >= 5 and resto[2] == ":":
            hora = resto[:5]
        if melhor is None or (iso, hora or "") > (melhor[0], melhor[1] or ""):
            melhor = (iso, hora)
    return melhor


def horas_desde(marca, agora: str):
    """Horas entre o carimbo e `agora` ("AAAA-MM-DD HH:MM"). Função pura; None sem carimbo.

    Carimbo sem hora conta como o FIM do dia declarado: supor meia-noite reprovaria um arquivo
    gravado às 23h por engano de leitura, e supor o fim do dia erra sempre para o lado de quem
    coletou — que é o lado que o portão não precisa punir.
    """
    if not marca or not agora:
        return None
    iso, hora = marca
    quando = dt.datetime.fromisoformat(iso + " " + (hora or "23:59"))
    return (dt.datetime.fromisoformat(agora) - quando).total_seconds() / 3600.0


def problemas(arquivos: dict, agora: str, limite_dias: int = LIMITE_DIAS,
              limite_horas: int = LIMITE_HORAS_ALERTA) -> list:
    """As falhas de frescor. Função pura: `arquivos` é {nome: (conteúdo, é_de_agora)}."""
    ruins = []
    for nome, (conteudo, de_agora) in sorted(arquivos.items()):
        if conteudo is None:
            ruins.append(f"{nome}: não existe")
            continue
        marca = marca_do_arquivo(conteudo)
        if not marca:
            ruins.append(f"{nome}: sem carimbo de data legível")
            continue
        h = horas_desde(marca, agora)
        if h is None:
            continue
        if de_agora:
            if h > limite_horas:
                ruins.append(f"{nome}: {h:.0f} horas desde {marca[0]} {marca[1] or ''}".rstrip()
                             + f" (limite {limite_horas} h — é informação de agora)")
        elif h / 24.0 > limite_dias:
            ruins.append(f"{nome}: {h / 24.0:.0f} dias desde {marca[0]} (limite {limite_dias})")
    return ruins


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("lê data brasileira com hora",
       marca_do_arquivo({"gerado_em": "02/10/2026 11:22"}) == ("2026-10-02", "11:22"))
    ok("lê data brasileira sem hora",
       marca_do_arquivo({"gerado_em": "02/10/2026"}) == ("2026-10-02", None))
    ok("lê data ISO", marca_do_arquivo({"coletado_em": "2026-09-30"}) == ("2026-09-30", None))
    ok("entre dois carimbos fica o mais recente",
       marca_do_arquivo({"corte": "01/09/2026", "gerado_em": "02/10/2026"}) == ("2026-10-02", None))
    ok("carimbo ilegível devolve None", marca_do_arquivo({"gerado_em": "ontem"}) is None)
    ok("sem carimbo devolve None", marca_do_arquivo({"x": 1}) is None)

    agora = "2026-10-02 12:00"
    ok("hora conta em horas", round(horas_desde(("2026-10-02", "11:00"), agora)) == 1)
    ok("dia sem hora conta do fim do dia",
       round(horas_desde(("2026-10-01", None), agora)) == 12)

    ok("alerta de hoje passa",
       problemas({"alertas/vigentes.json": ({"gerado_em": "02/10/2026 11:22"}, True)}, agora) == [])
    ok("alerta de anteontem reprova pelas 24 horas",
       any("é informação de agora" in p for p in
           problemas({"alertas/vigentes.json": ({"gerado_em": "30/09/2026 11:00"}, True)}, agora)))
    ok("semanal no limite passa",
       problemas({"a.json": ({"gerado_em": "23/09/2026"}, False)}, agora) == [])
    ok("semanal além do limite reprova",
       len(problemas({"a.json": ({"gerado_em": "20/09/2026"}, False)}, agora)) == 1)
    ok("semanal sem carimbo reprova",
       any("sem carimbo" in p for p in problemas({"a.json": ({}, False)}, agora)))
    ok("arquivo ausente reprova",
       any("não existe" in p for p in problemas({"a.json": (None, False)}, agora)))
    ok("as duas listas não se sobrepõem", not (set(SEMANAIS) & set(DE_AGORA)))
    ok("o alerta tem limite menor que o semanal", LIMITE_HORAS_ALERTA / 24 < LIMITE_DIAS)

    # Trava estrutural pelo bytecode: nenhuma função deste portão escreve. Olhar o texto do próprio
    # arquivo não serve, porque esta linha cita os nomes que ela proíbe.
    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj == "_autoteste":
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o portão não escreve nada",
       not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem leitura de data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    def ler(rel):
        p = RAIZ / "data" / rel
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return None

    sys.path.insert(0, str(RAIZ))
    from coletores_base import hoje_editorial
    agora = hoje_editorial().isoformat() + " " + dt.datetime.now().strftime("%H:%M")
    arquivos = {n: (ler(n), False) for n in SEMANAIS}
    arquivos.update({n: (ler(n), True) for n in DE_AGORA})
    ruins = problemas(arquivos, agora)

    if "--json" in sys.argv:
        print(json.dumps({"agora": agora, "limite_dias": LIMITE_DIAS,
                          "limite_horas_alerta": LIMITE_HORAS_ALERTA, "problemas": ruins,
                          "arquivos": {n: marca_do_arquivo(c or {}) for n, (c, _) in arquivos.items()}},
                         ensure_ascii=False, indent=1))
        return 1 if ruins else 0

    if ruins:
        print(f"✗ FRESCOR DA DEFESA CIVIL: {len(ruins)} problema(s):")
        for r in ruins:
            print("   - " + r)
        return 1
    print(f"✓ FRESCOR DA DEFESA CIVIL OK — {len(SEMANAIS)} arquivo(s) semanal(is) dentro de "
          f"{LIMITE_DIAS} dias e {len(DE_AGORA)} de agora dentro de {LIMITE_HORAS_ALERTA} h.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
