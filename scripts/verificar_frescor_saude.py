#!/usr/bin/env python3
"""Portão de frescor da página de Saúde: 9 dias por fonte (HANDOVER_SAUDE_10-10-2026, item 1.6).

Medido em 10/10/2026: `saude_sinais.json` com `gerado_em` 26/09, InfoDengue e painel de calor de
25/09, duas fontes "a_verificar" havia semanas — e nenhum portão vermelho. O coletor tinha parado
(F40) e a página seguia mostrando o dado sem dizer que ele envelhecera.

O que o portão cobra, por fonte:

- **coletada** (`status: coletado`): `consultado_em` com no máximo 9 dias (uma semana de cadência
  mais dois de folga, a mesma régua do Financiamento e da Defesa civil);
- **reuso** (`status: reuso`): passa — o arquivo de origem tem o próprio portão;
- **lacuna declarada** (`status: lacuna`): passa se trouxer `motivo` — ausência dita, com razão;
- **qualquer outro estado** (`a_verificar`, `aguardando_primeira_coleta`, vazio): reprova. "A
  verificar" não é estado de fonte exibida; é pendência, e pendência não vai ao ar sem prazo.

E por arquivo de série de desfechos: o carimbo `gerado_em` com no máximo 9 dias.

Na publicação, o portão não barra (regra de 06/10: só integridade, segredo, vocabulário, runtime e
tamanho barram); no PR, bloqueia. Função pura sobre os carimbos: não coleta, não escreve, não vai à
rede.

Uso:
    python3 scripts/verificar_frescor_saude.py
    python3 scripts/verificar_frescor_saude.py --json
    python3 scripts/verificar_frescor_saude.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LIMITE_DIAS = 9
SINAIS = "saude_sinais.json"
# Séries de desfechos que a página desenha, cada uma com o elo que a escreve.
SERIES = (
    "saude_desfechos/serie_uf.json",            # noturno_saude (coletar_desfechos_saude.py)
    "saude_desfechos/chik_serie_uf.json",       # noturno_saude (… --doenca chikungunya)
    "saude_desfechos/dengue_sinan_serie.json",  # semanal_sinais_e_links (coletar_arboviroses_sinan.py)
    "saude_desfechos/chik_sinan_serie.json",    # idem
    "saude_desfechos/srag_serie.json",          # semanal_sinais_e_links (coletar_srag_gripe.py)
)
ESTADOS_OK = ("coletado", "reuso", "lacuna")


def _data(bruto):
    if not isinstance(bruto, str):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(bruto[:10], fmt).date()
        except ValueError:
            continue
    return None


def problemas(sinais: dict, series: dict, hoje: dt.date, limite: int = LIMITE_DIAS) -> list:
    """As falhas de frescor. Função pura: `series` é {nome: conteúdo ou None}."""
    ruins = []
    if sinais is None:
        return [f"{SINAIS}: não existe"]
    for nome, f in sorted(((sinais or {}).get("fontes") or {}).items()):
        st = str((f or {}).get("status") or "")
        if st not in ESTADOS_OK:
            ruins.append(f"{SINAIS} · {nome}: estado `{st or 'vazio'}` — coletar ou declarar lacuna "
                         "com motivo; \"a verificar\" não é estado de fonte exibida")
            continue
        if st == "lacuna" and not str(f.get("motivo") or "").strip():
            ruins.append(f"{SINAIS} · {nome}: lacuna sem `motivo`")
        if st == "coletado":
            # A idade que importa é a do DADO, não a da tentativa: o coletor carimba
            # `consultado_em` mesmo quando a fonte falha e o dado exibido continua o anterior.
            d = _data(f.get("ultima_coleta_ok"))
            if d is None and not f.get("ultima_tentativa_falhou"):
                d = _data(f.get("consultado_em"))
            if d is None:
                ruins.append(f"{SINAIS} · {nome}: coletada sem data da última coleta bem-sucedida")
            elif (hoje - d).days > limite:
                ruins.append(f"{SINAIS} · {nome}: {(hoje - d).days} dias desde {d.isoformat()} "
                             f"(limite {limite})")
    for nome, conteudo in sorted((series or {}).items()):
        if conteudo is None:
            ruins.append(f"{nome}: não existe")
            continue
        d = _data((conteudo or {}).get("gerado_em"))
        if d is None:
            ruins.append(f"{nome}: sem `gerado_em` legível")
        elif (hoje - d).days > limite:
            ruins.append(f"{nome}: {(hoje - d).days} dias desde {d.isoformat()} (limite {limite})")
    return ruins


def _autoteste() -> int:
    falhas, casos = [], []

    def ok(nome, cond):
        casos.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    hoje = dt.date(2026, 10, 11)
    bom = {"fontes": {"infodengue": {"status": "coletado", "consultado_em": "10/10/2026"},
                      "inpe_focos": {"status": "reuso"},
                      "sisagua": {"status": "lacuna", "motivo": "sem coletor automático"}}}
    serie_ok = {"s.json": {"gerado_em": "02/10/2026"}}
    ok("fontes em dia, reuso e lacuna com motivo passam", problemas(bom, serie_ok, hoje) == [])
    velho = {"fontes": {"infodengue": {"status": "coletado", "consultado_em": "25/09/2026"}}}
    ok("coletada há 16 dias reprova (o caso de 10/10)",
       any("16 dias" in p for p in problemas(velho, {}, hoje)))
    falhou = {"fontes": {"x": {"status": "coletado", "consultado_em": "11/10/2026",
                               "ultima_tentativa_falhou": "11/10/2026", "ultima_coleta_ok": "25/09/2026"}}}
    ok("tentativa de hoje que falhou não rejuvenesce o dado de 25/09",
       any("16 dias" in p for p in problemas(falhou, {}, hoje)))
    ok("falhou e sem data de coleta boa reprova", len(problemas(
        {"fontes": {"x": {"status": "coletado", "consultado_em": "11/10/2026",
                          "ultima_tentativa_falhou": "11/10/2026"}}}, {}, hoje)) == 1)
    ok("no limite de 9 dias passa",
       problemas({"fontes": {"x": {"status": "coletado", "consultado_em": "02/10/2026"}}}, {}, hoje) == [])
    ok("`a_verificar` reprova", any("a_verificar" in p for p in problemas(
        {"fontes": {"x": {"status": "a_verificar"}}}, {}, hoje)))
    ok("`aguardando_primeira_coleta` reprova", len(problemas(
        {"fontes": {"x": {"status": "aguardando_primeira_coleta"}}}, {}, hoje)) == 1)
    ok("lacuna sem motivo reprova", any("sem `motivo`" in p for p in problemas(
        {"fontes": {"x": {"status": "lacuna"}}}, {}, hoje)))
    ok("série velha reprova; série ausente reprova",
       len(problemas(bom, {"a.json": {"gerado_em": "24/09/2026"}, "b.json": None}, hoje)) == 2)
    ok("arquivo de sinais ausente reprova", problemas(None, {}, hoje) == [f"{SINAIS}: não existe"])
    import dis
    nomes = set()
    for n, obj in list(globals().items()):
        if n != "_autoteste" and getattr(obj, "__code__", None) is not None:
            nomes |= {i.argval for i in dis.get_instructions(obj.__code__) if isinstance(i.argval, str)}
    ok("trava estrutural: o portão não escreve", not ({"write_text", "write_bytes", "gravar"} & nomes))
    print(f"✗ AUTOTESTE: {len(falhas)} falha(s)" if falhas
          else f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede e sem leitura de data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    def ler(rel):
        p = RAIZ / "data" / rel
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        except ValueError:
            return None

    sys.path.insert(0, str(RAIZ))
    from coletores_base import hoje_editorial
    hoje = hoje_editorial()
    ruins = problemas(ler(SINAIS), {n: ler(n) for n in SERIES}, hoje)
    if "--json" in sys.argv:
        print(json.dumps({"hoje": hoje.isoformat(), "limite_dias": LIMITE_DIAS, "problemas": ruins},
                         ensure_ascii=False, indent=1))
        return 1 if ruins else 0
    if ruins:
        print(f"✗ FRESCOR DA SAÚDE: {len(ruins)} problema(s) (limite {LIMITE_DIAS} dias):")
        for r in ruins:
            print("   - " + r)
        return 1
    print(f"✓ FRESCOR DA SAÚDE OK — fontes de {SINAIS} em dia ou com lacuna declarada, e "
          f"{len(SERIES)} série(s) de desfechos dentro de {LIMITE_DIAS} dias.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
