#!/usr/bin/env python3
"""Portão de frescor dos dados do Financiamento: 9 dias por arquivo (handover de 02/10/2026).

A página do Financiamento mostra dinheiro do ciclo, e dinheiro do ciclo envelhece: um arquivo
parado há três semanas publica um número que já não é o número. A editoria fechou o limite em
**9 dias** por arquivo — uma semana de cadência mais dois dias de folga —, e vermelho **bloqueia a
publicação**.

A distinção que este portão faz, e que é o motivo de ele existir:

- **Saída de coletor** é medida pelo relógio. Nove dias sem coletar é falha, e a falha aparece.
- **Arquivo de curadoria** — o modelo das rotas, a lista de compromissos verificados em fonte
  primária, a estrutura do diagrama — não tem coletor por decisão de método: ele é escrito a partir
  de documento lido, e revisado quando o documento muda. Medir curadoria pelo relógio produz
  vermelho permanente que ninguém consegue apagar, e vermelho que não se apaga deixa de ser sinal.
  Curadoria é medida por **declaração**: o arquivo diz `curadoria: true` e traz `revisado_em`.

Em 02/10/2026 esta distinção não existia, e quatro arquivos apareciam como "parados em 06/09" —
sem que houvesse coletor nenhum para rodar. Declarar o que é curado é o que torna o atraso dos
outros legível.

Uso:
    python3 scripts/verificar_frescor_financiamento.py            # portão
    python3 scripts/verificar_frescor_financiamento.py --json     # para outro programa ler
    python3 scripts/verificar_frescor_financiamento.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LIMITE_DIAS = 9
# Os arquivos que a página do Financiamento lê. Saída de coletor; o limite de 9 dias vale para
# todos. Arquivo mensal entra na semana em que o mês é publicado, e por isso o limite é do ARQUIVO,
# não do mês que ele descreve.
DE_COLETOR = (
    "financiamento/mps_2026.json",
    "financiamento/serie_nacional.json",
    "financiamento/por_uf.json",
    "financiamento/programas_faf_2026.json",
    "financiamento/municipios/transferencias_uniao.json",
    "financiamento/municipios/despesa_182.json",
    "resposta/recursos_liberados.json",
    "financiamento/semana.json",
    "financiamento/contadores_uf.json",
)
# Curadoria: sem coletor por decisão de método. Exige `curadoria: true` e `revisado_em`.
DE_CURADORIA = (
    "financiamento/rotas.json",
    "financiamento/rotas_preventivas.json",
    "financiamento/compromissos_federais.json",
    "financiamento/emendas.json",
    "financiamento/preventivo_setores.json",
)
CAMPOS_DE_DATA = ("gerado_em", "atualizado_em", "corte", "revisado_em")


def data_do_arquivo(d: dict):
    """A data mais recente que o arquivo declara, em ISO. Função pura; `None` sem carimbo."""
    datas = []
    for campo in CAMPOS_DE_DATA:
        bruto = (d or {}).get(campo)
        if not isinstance(bruto, str):
            continue
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                datas.append(dt.datetime.strptime(bruto[:10], fmt).date())
                break
            except ValueError:
                continue
    return max(datas).isoformat() if datas else None


def atraso(data_iso: str, hoje_iso: str):
    """Dias entre a data do arquivo e hoje. Função pura; `None` sem data."""
    if not data_iso or not hoje_iso:
        return None
    return (dt.date.fromisoformat(hoje_iso) - dt.date.fromisoformat(data_iso)).days


def problemas(arquivos: dict, hoje_iso: str, limite: int = LIMITE_DIAS) -> list:
    """As falhas de frescor. Função pura: `arquivos` é {nome: (conteúdo, é_curadoria)}.

    Curadoria sem `curadoria: true` e sem `revisado_em` é falha de **declaração**, não de relógio —
    e a mensagem diz isso, porque a correção é outra: declarar, não coletar.
    """
    ruins = []
    for nome, (conteudo, curado) in sorted(arquivos.items()):
        if conteudo is None:
            ruins.append(f"{nome}: não existe")
            continue
        data = data_do_arquivo(conteudo)
        if curado:
            if not conteudo.get("curadoria"):
                ruins.append(f"{nome}: é de curadoria e não declara `curadoria: true` — sem a "
                             "declaração, o atraso dele some no meio dos coletores")
            if not conteudo.get("revisado_em"):
                ruins.append(f"{nome}: é de curadoria e não traz `revisado_em` — curadoria se "
                             "mede por revisão declarada, não por relógio")
            continue
        if not data:
            ruins.append(f"{nome}: sem carimbo de data legível")
            continue
        d = atraso(data, hoje_iso)
        if d is not None and d > limite:
            ruins.append(f"{nome}: {d} dias desde {data} (limite {limite})")
    return ruins


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("lê a data em formato brasileiro", data_do_arquivo({"gerado_em": "02/10/2026"}) == "2026-10-02")
    ok("lê a data em ISO", data_do_arquivo({"atualizado_em": "2026-10-02"}) == "2026-10-02")
    ok("entre dois carimbos, fica o mais recente",
       data_do_arquivo({"corte": "01/09/2026", "gerado_em": "02/10/2026"}) == "2026-10-02")
    ok("sem carimbo devolve None", data_do_arquivo({"x": 1}) is None)
    ok("carimbo ilegível não quebra", data_do_arquivo({"gerado_em": "ontem"}) is None)

    ok("atraso em dias", atraso("2026-09-23", "2026-10-02") == 9)
    ok("sem data, sem atraso", atraso(None, "2026-10-02") is None)

    hoje = "2026-10-02"
    ok("coletor no limite passa",
       problemas({"a.json": ({"gerado_em": "23/09/2026"}, False)}, hoje) == [])
    ok("coletor um dia além do limite reprova",
       len(problemas({"a.json": ({"gerado_em": "22/09/2026"}, False)}, hoje)) == 1)
    ok("coletor sem carimbo reprova",
       any("sem carimbo" in p for p in problemas({"a.json": ({}, False)}, hoje)))
    ok("arquivo ausente reprova",
       any("não existe" in p for p in problemas({"a.json": (None, False)}, hoje)))

    curado_ok = {"curadoria": True, "revisado_em": "06/09/2026"}
    ok("curadoria declarada passa, mesmo velha",
       problemas({"c.json": (curado_ok, True)}, hoje) == [])
    ok("curadoria sem declaração reprova por declaração, não por relógio",
       any("não declara" in p for p in problemas({"c.json": ({"corte": "06/09/2026"}, True)}, hoje)))
    ok("curadoria sem revisão declarada reprova",
       any("revisado_em" in p for p in problemas({"c.json": ({"curadoria": True}, True)}, hoje)))

    ok("as duas listas não se sobrepõem", not (set(DE_COLETOR) & set(DE_CURADORIA)))
    # Trava estrutural pelo bytecode: nenhuma função deste portão chama escrita. Olhar o texto do
    # próprio arquivo não serve, porque esta linha cita os nomes que ela proíbe.
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
          else "✓ AUTOTESTE OK — 16 casos, sem rede e sem leitura de data/.")
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
    hoje = hoje_editorial().isoformat()
    arquivos = {n: (ler(n), False) for n in DE_COLETOR}
    arquivos.update({n: (ler(n), True) for n in DE_CURADORIA})
    ruins = problemas(arquivos, hoje)

    if "--json" in sys.argv:
        print(json.dumps({"hoje": hoje, "limite_dias": LIMITE_DIAS, "problemas": ruins,
                          "arquivos": {n: data_do_arquivo(c or {}) for n, (c, _) in arquivos.items()}},
                         ensure_ascii=False, indent=1))
        return 1 if ruins else 0

    if ruins:
        print(f"✗ FRESCOR DO FINANCIAMENTO: {len(ruins)} problema(s) (limite {LIMITE_DIAS} dias):")
        for r in ruins:
            print("   - " + r)
        return 1
    print(f"✓ FRESCOR DO FINANCIAMENTO OK — {len(DE_COLETOR)} arquivo(s) de coletor dentro de "
          f"{LIMITE_DIAS} dias e {len(DE_CURADORIA)} de curadoria com revisão declarada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
