#!/usr/bin/env python3
"""Portão de frescor dos dados exibidos — Financiamento, Defesa civil e Saúde num só medidor.

16/10/2026 (consolidação item 6): `verificar_frescor_financiamento.py`, `verificar_frescor_defesa_civil.py`
e `verificar_frescor_saude.py` liam o mesmo carimbo com três leitores e três relógios. Aqui há UM leitor
de carimbo, UM relógio e três FAMÍLIAS declaradas; cada regra e cada caso de autoteste dos três vieram
juntos. Vermelho bloqueia a publicação.

AS REGRAS (editoria, 02/10/2026; saúde 10/10/2026)
- **Saída de coletor** envelhece pelo relógio: **9 dias** por arquivo (uma semana de cadência + dois de
  folga). O limite é do ARQUIVO, não do fato: lista federal de 2024 coletada ontem está fresca.
- **Curadoria** (rotas, compromissos, emendas, setores) não tem coletor por decisão de método e se
  mede por DECLARAÇÃO: `curadoria: true` e `revisado_em`. Medir curadoria pelo relógio produz vermelho
  permanente, e vermelho que não se apaga deixa de ser sinal.
- **Informação de agora** (alertas vigentes) mede-se em **horas**: 24 h. Carimbo sem hora conta como o
  FIM do dia declarado — supor meia-noite reprovaria um arquivo gravado às 23h.
- **Saúde:** toda fonte de `saude_sinais.json` está `coletado`, `reuso` ou `lacuna` (com `motivo`);
  "a verificar" não é estado de fonte exibida. A idade que importa é a do DADO (`ultima_coleta_ok`), não
  a da tentativa: o coletor carimba `consultado_em` mesmo quando a fonte falha.

Uso:
    python3 scripts/verificar_frescor.py              # o autoteste roda antes da conferência
    python3 scripts/verificar_frescor.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LIMITE_DIAS = 9
LIMITE_HORAS_ALERTA = 24
CAMPOS_DE_DATA = ("gerado_em", "atualizado_em", "coletado_em", "corte", "revisado_em")
ESTADOS_OK = ("coletado", "reuso", "lacuna")
SINAIS = "saude_sinais.json"

# {nome do arquivo em data/: regime}. Regimes: coletor (dias) · curadoria (declaração) · agora (horas)
# · sinais (estado por fonte) · serie (gerado_em em dias). Arquivo mensal entra na semana em que o mês
# é publicado, e por isso o limite é do arquivo, não do mês que ele descreve.
FAMILIAS = {
    "FINANCIAMENTO": {
        "financiamento/mps_2026.json": "coletor", "financiamento/serie_nacional.json": "coletor",
        "financiamento/por_uf.json": "coletor", "financiamento/programas_faf_2026.json": "coletor",
        "financiamento/municipios/transferencias_uniao.json": "coletor",
        "financiamento/fns_2026.json": "coletor",          # 11/10/2026: repasses do FNS (coletar_fns.py)
        "financiamento/municipios/despesa_182.json": "coletor", "resposta/recursos_liberados.json": "coletor",
        "financiamento/semana.json": "coletor", "financiamento/contadores_uf.json": "coletor",
        "financiamento/rotas.json": "curadoria", "financiamento/rotas_preventivas.json": "curadoria",
        "financiamento/compromissos_federais.json": "curadoria", "financiamento/emendas.json": "curadoria",
        "financiamento/preventivo_setores.json": "curadoria",
    },
    "DEFESA CIVIL": {
        "resposta/municipios_decretados.json": "coletor", "resposta/por_uf.json": "coletor",
        "resposta/serie_semanal.json": "coletor", "resposta/recursos_liberados.json": "coletor",
        "atos_resposta.json": "coletor", "cadastro_prioritarios_federal.json": "coletor",
        "enquadramento_federal.json": "coletor",
        "alertas/vigentes.json": "agora",
    },
    "SAÚDE": {
        SINAIS: "sinais",
        "saude_desfechos/serie_uf.json": "serie",            # noturno_saude (coletar_desfechos_saude.py)
        "saude_desfechos/chik_serie_uf.json": "serie",       # noturno_saude (… --doenca chikungunya)
        "saude_desfechos/dengue_sinan_serie.json": "serie",  # semanal_sinais_e_links (coletar_arboviroses_sinan.py)
        "saude_desfechos/chik_sinan_serie.json": "serie",    # idem
        "saude_desfechos/srag_serie.json": "serie",          # semanal_sinais_e_links (coletar_srag_gripe.py)
    },
}


def _data(bruto):
    """dd/mm/aaaa ou aaaa-mm-dd → date; None se ilegível. Função pura."""
    if not isinstance(bruto, str):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(bruto[:10], fmt).date()
        except ValueError:
            continue
    return None


def marca_do_arquivo(d: dict, campos=CAMPOS_DE_DATA):
    """O carimbo mais recente que o arquivo declara, como (ISO, hora_ou_None). Função pura."""
    melhor = None
    for campo in campos:
        bruto = (d or {}).get(campo)
        data = _data(bruto)
        if data is None:
            continue
        resto = bruto[10:].strip()
        hora = resto[:5] if len(resto) >= 5 and resto[2] == ":" else None
        if melhor is None or (data.isoformat(), hora or "") > (melhor[0], melhor[1] or ""):
            melhor = (data.isoformat(), hora)
    return melhor


def horas_desde(marca, agora: str):
    """Horas entre o carimbo e `agora` ("AAAA-MM-DD HH:MM"). Função pura; None sem carimbo.
    Carimbo sem hora conta como o FIM do dia declarado."""
    if not marca or not agora:
        return None
    quando = dt.datetime.fromisoformat(marca[0] + " " + (marca[1] or "23:59"))
    return (dt.datetime.fromisoformat(agora) - quando).total_seconds() / 3600.0


def dias_desde(data: dt.date, agora: str):
    return (dt.date.fromisoformat(agora[:10]) - data).days


def problemas(arquivos: dict, agora: str, limite: int = LIMITE_DIAS,
              limite_horas: int = LIMITE_HORAS_ALERTA) -> list:
    """As falhas de frescor. Função pura: `arquivos` é {nome: (conteúdo ou None, regime)};
    `agora` é "AAAA-MM-DD" ou "AAAA-MM-DD HH:MM"."""
    ruins = []
    for nome, (c, regime) in sorted(arquivos.items()):
        if c is None:
            ruins.append(f"{nome}: não existe")
            continue
        if regime == "curadoria":
            if not c.get("curadoria"):
                ruins.append(f"{nome}: é de curadoria e não declara `curadoria: true` — sem a "
                             "declaração, o atraso dele some no meio dos coletores")
            if not c.get("revisado_em"):
                ruins.append(f"{nome}: é de curadoria e não traz `revisado_em` — curadoria se "
                             "mede por revisão declarada, não por relógio")
            continue
        if regime == "sinais":
            for fonte, f in sorted((c.get("fontes") or {}).items()):
                st = str((f or {}).get("status") or "")
                if st not in ESTADOS_OK:
                    ruins.append(f"{nome} · {fonte}: estado `{st or 'vazio'}` — coletar ou declarar lacuna "
                                 "com motivo; \"a verificar\" não é estado de fonte exibida")
                    continue
                if st == "lacuna" and not str(f.get("motivo") or "").strip():
                    ruins.append(f"{nome} · {fonte}: lacuna sem `motivo`")
                if st == "coletado":
                    d = _data(f.get("ultima_coleta_ok"))
                    if d is None and not f.get("ultima_tentativa_falhou"):
                        d = _data(f.get("consultado_em"))
                    if d is None:
                        ruins.append(f"{nome} · {fonte}: coletada sem data da última coleta bem-sucedida")
                    elif dias_desde(d, agora) > limite:
                        ruins.append(f"{nome} · {fonte}: {dias_desde(d, agora)} dias desde {d.isoformat()} "
                                     f"(limite {limite})")
            continue
        marca = marca_do_arquivo(c, ("gerado_em",) if regime == "serie" else CAMPOS_DE_DATA)
        if not marca:
            ruins.append(f"{nome}: sem `gerado_em` legível" if regime == "serie"
                         else f"{nome}: sem carimbo de data legível")
            continue
        if regime == "agora":
            h = horas_desde(marca, agora if len(agora) > 10 else agora + " 23:59")
            if h > limite_horas:
                ruins.append(f"{nome}: {h:.0f} horas desde {marca[0]} {marca[1] or ''}".rstrip()
                             + f" (limite {limite_horas} h — é informação de agora)")
            continue
        d = dias_desde(dt.date.fromisoformat(marca[0]), agora)
        if d > limite:
            ruins.append(f"{nome}: {d} dias desde {marca[0]} (limite {limite})")
    return ruins


def _autoteste() -> int:
    falhas, casos = [], []

    def ok(nome, cond):
        casos.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # o leitor de carimbo
    ok("lê data brasileira com hora", marca_do_arquivo({"gerado_em": "02/10/2026 11:22"}) == ("2026-10-02", "11:22"))
    ok("lê data brasileira sem hora", marca_do_arquivo({"gerado_em": "02/10/2026"}) == ("2026-10-02", None))
    ok("lê data ISO", marca_do_arquivo({"coletado_em": "2026-09-30"}) == ("2026-09-30", None))
    ok("entre dois carimbos fica o mais recente",
       marca_do_arquivo({"corte": "01/09/2026", "gerado_em": "02/10/2026"}) == ("2026-10-02", None))
    ok("carimbo ilegível devolve None", marca_do_arquivo({"gerado_em": "ontem"}) is None)
    ok("sem carimbo devolve None", marca_do_arquivo({"x": 1}) is None)
    agora = "2026-10-02 12:00"
    ok("hora conta em horas", round(horas_desde(("2026-10-02", "11:00"), agora)) == 1)
    ok("dia sem hora conta do fim do dia", round(horas_desde(("2026-10-01", None), agora)) == 12)
    ok("sem carimbo, sem horas", horas_desde(None, agora) is None)
    ok("atraso em dias", dias_desde(dt.date(2026, 9, 23), "2026-10-02") == 9)
    # coletor (dias) e curadoria (declaração)
    hoje = "2026-10-02"
    ok("coletor no limite passa", problemas({"a.json": ({"gerado_em": "23/09/2026"}, "coletor")}, hoje) == [])
    ok("coletor um dia além do limite reprova",
       len(problemas({"a.json": ({"gerado_em": "22/09/2026"}, "coletor")}, hoje)) == 1)
    ok("coletor sem carimbo reprova", any("sem carimbo" in p for p in problemas({"a.json": ({}, "coletor")}, hoje)))
    ok("arquivo ausente reprova", any("não existe" in p for p in problemas({"a.json": (None, "coletor")}, hoje)))
    ok("curadoria declarada passa, mesmo velha",
       problemas({"c.json": ({"curadoria": True, "revisado_em": "06/09/2026"}, "curadoria")}, hoje) == [])
    ok("curadoria sem declaração reprova por declaração, não por relógio",
       any("não declara" in p for p in problemas({"c.json": ({"corte": "06/09/2026"}, "curadoria")}, hoje)))
    ok("curadoria sem revisão declarada reprova",
       any("revisado_em" in p for p in problemas({"c.json": ({"curadoria": True}, "curadoria")}, hoje)))
    # agora (horas) e semanal com relógio de hora
    ok("alerta de hoje passa", problemas({"alertas/vigentes.json": ({"gerado_em": "02/10/2026 11:22"}, "agora")}, agora) == [])
    ok("alerta de anteontem reprova pelas 24 horas", any("é informação de agora" in p for p in
       problemas({"alertas/vigentes.json": ({"gerado_em": "30/09/2026 11:00"}, "agora")}, agora)))
    ok("semanal no limite passa", problemas({"a.json": ({"gerado_em": "23/09/2026"}, "coletor")}, agora) == [])
    ok("semanal além do limite reprova", len(problemas({"a.json": ({"gerado_em": "20/09/2026"}, "coletor")}, agora)) == 1)
    ok("o alerta tem limite menor que o semanal", LIMITE_HORAS_ALERTA / 24 < LIMITE_DIAS)
    # saúde: estado por fonte e séries
    h11 = "2026-10-11"
    bom = {"fontes": {"infodengue": {"status": "coletado", "consultado_em": "10/10/2026"},
                      "inpe_focos": {"status": "reuso"},
                      "sisagua": {"status": "lacuna", "motivo": "sem coletor automático"}}}
    ok("fontes em dia, reuso e lacuna com motivo passam; série em dia passa",
       problemas({SINAIS: (bom, "sinais"), "s.json": ({"gerado_em": "02/10/2026"}, "serie")}, h11) == [])
    ok("coletada há 16 dias reprova (o caso de 10/10)", any("16 dias" in p for p in problemas(
       {SINAIS: ({"fontes": {"infodengue": {"status": "coletado", "consultado_em": "25/09/2026"}}}, "sinais")}, h11)))
    ok("tentativa de hoje que falhou não rejuvenesce o dado de 25/09", any("16 dias" in p for p in problemas(
       {SINAIS: ({"fontes": {"x": {"status": "coletado", "consultado_em": "11/10/2026",
                                   "ultima_tentativa_falhou": "11/10/2026", "ultima_coleta_ok": "25/09/2026"}}}, "sinais")}, h11)))
    ok("falhou e sem data de coleta boa reprova", len(problemas(
       {SINAIS: ({"fontes": {"x": {"status": "coletado", "consultado_em": "11/10/2026",
                                   "ultima_tentativa_falhou": "11/10/2026"}}}, "sinais")}, h11)) == 1)
    ok("no limite de 9 dias passa", problemas(
       {SINAIS: ({"fontes": {"x": {"status": "coletado", "consultado_em": "02/10/2026"}}}, "sinais")}, h11) == [])
    ok("`a_verificar` e `aguardando_primeira_coleta` reprovam",
       any("a_verificar" in p for p in problemas({SINAIS: ({"fontes": {"x": {"status": "a_verificar"}}}, "sinais")}, h11))
       and len(problemas({SINAIS: ({"fontes": {"x": {"status": "aguardando_primeira_coleta"}}}, "sinais")}, h11)) == 1)
    ok("lacuna sem motivo reprova", any("sem `motivo`" in p for p in problemas(
       {SINAIS: ({"fontes": {"x": {"status": "lacuna"}}}, "sinais")}, h11)))
    ok("série velha reprova; série ausente reprova; série sem gerado_em reprova",
       len(problemas({"a.json": ({"gerado_em": "24/09/2026"}, "serie"), "b.json": (None, "serie"),
                      "c.json": ({"corte": "10/10/2026"}, "serie")}, h11)) == 3)
    ok("arquivo de sinais ausente reprova", problemas({SINAIS: (None, "sinais")}, h11) == [f"{SINAIS}: não existe"])
    ok("cada arquivo tem um regime só", all(len(f) == len(set(f)) for f in FAMILIAS.values()))
    import dis
    nomes = set()
    for n, obj in list(globals().items()):
        if n != "_autoteste" and getattr(obj, "__code__", None) is not None:
            nomes |= {i.argval for i in dis.get_instructions(obj.__code__) if isinstance(i.argval, str)}
    ok("trava estrutural: o portão não escreve", not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))
    print(f"✗ AUTOTESTE: {len(falhas)} falha(s)" if falhas
          else f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede e sem leitura de data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    if _autoteste() != 0:
        return 1

    def ler(rel):
        p = RAIZ / "data" / rel
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        except ValueError:
            return None

    sys.path.insert(0, str(RAIZ))
    from coletores_base import FUSO_EDITORIAL
    agora = dt.datetime.now(FUSO_EDITORIAL).strftime("%Y-%m-%d %H:%M")
    total = 0
    for familia, arquivos in FAMILIAS.items():
        ruins = problemas({n: (ler(n), r) for n, r in arquivos.items()}, agora)
        total += len(ruins)
        if ruins:
            print(f"✗ FRESCOR — {familia}: {len(ruins)} problema(s):")
            for r in ruins:
                print("   - " + r)
        else:
            print(f"  ✓ {familia}: {len(arquivos)} arquivo(s) em dia")
    if total:
        print(f"✗ FRESCOR: {total} problema(s) (limite {LIMITE_DIAS} dias; {LIMITE_HORAS_ALERTA} h para alerta).")
        return 1
    print(f"✓ FRESCOR OK — {sum(len(a) for a in FAMILIAS.values())} arquivo(s) em três famílias: coletor dentro de "
          f"{LIMITE_DIAS} dias, curadoria com revisão declarada, alerta dentro de {LIMITE_HORAS_ALERTA} h, "
          "fontes de saúde coletadas, em reuso ou com lacuna declarada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
