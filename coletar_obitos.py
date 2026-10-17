#!/usr/bin/env python3
"""Óbitos registrados por UF e mês, na estrutura comum de desfechos (faixa E2, 17/10/2026).

Grava `data/saude_desfechos/obitos.json` pela forma comum (`desfechos_sus.montar` e
`gravar_desfecho`): série desde jan/2019, por 100 mil, faixa habitual, cortes do mapa congelados,
último valor e mês corrente parcial. A leitura da fonte é a de `coletar_obitos_registro_civil.py`
(`API`, `meses`, `serie_de`, importados): este arquivo não fala com a fonte de outro jeito, só pede
mais meses. O arquivo antigo (`obitos_registro_civil.json`), que a página lê hoje, não muda.

O QUE A SÉRIE É
---------------
Registros de óbito lavrados em cartório no mês, por UF, como o Portal da Transparência do Registro
Civil agrega. Não é óbito ocorrido no mês nem óbito por causa (o SIM é a fonte de causa, com meses
de defasagem). O painel por causa saiu do portal (sondagem de 17/10/2026: HTTP 500 nos endereços
antigos; o código do portal não os chama mais): lacuna declarada.

INCREMENTAL
-----------
Registro lavrado num mês não muda depois: mês fechado já lido não é pedido de novo, salvo os três
mais recentes (o corrente sobe ao longo dos dias). Na primeira rodada são 94 pedidos; depois, três.
Mês que a fonte não respondeu fica `null` (lacuna), nunca zero.

USO
  python3 coletar_obitos.py --autoteste
  python3 coletar_obitos.py --sondar      # só mede e imprime; não grava série
  python3 coletar_obitos.py               # coleta e grava o arquivo comum
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from coletar_obitos_registro_civil import API, meses, serie_de  # noqa: E402

DESFECHO = "obitos"
INICIO = datetime.date(2019, 1, 1)
REPEDIR = 3  # meses mais recentes pedidos de novo a cada rodada
RC_BASE = "https://transparencia.registrocivil.org.br"
FONTE = {"sistema": "Portal da Transparência do Registro Civil (ARPEN/CNJ)", "url": RC_BASE + "/",
         "conta": "registros de óbito lavrados no mês, sem causa"}


def janelas(hoje: datetime.date) -> list:
    """Janelas mensais de jan/2019 até o mês de `hoje`, pela função do coletor existente. Pura."""
    n = (hoje.year - INICIO.year) * 12 + hoje.month - INICIO.month + 1
    return meses(hoje, n) if n > 0 else []


def a_pedir(todas: list, anterior: dict) -> list:
    """Janelas a pedir: as que o arquivo anterior não tem completas (27 UFs) e as `REPEDIR` últimas."""
    serie = (anterior or {}).get("serie") or {}
    ufs = [u for u in serie if u != "BR"]
    feitos = {p for p in {p for u in ufs for p in serie[u]}
              if len(ufs) == 27 and all(serie[u].get(p) is not None for u in ufs)}
    ultimas = todas[-REPEDIR:]
    return [j for j in todas if j in ultimas or f"{j[0].year}-{j[0].month:02d}" not in feitos]


def unir(anterior: dict, novos: dict, todas: list, ufs) -> dict:
    """Série completa {UF: {AAAA-MM: n | None}}: o novo vence o anterior; o que faltar é None. Pura."""
    velho = (anterior or {}).get("serie") or {}
    chaves = [f"{i.year}-{i.month:02d}" for i, _f in todas]
    return {uf: {p: novos.get(uf, {}).get(p, velho.get(uf, {}).get(p)) for p in chaves} for uf in ufs}


def coletar(buscar_fn=None, ler_fn=None, gravar_fn=None, hoje: datetime.date = None) -> bool:
    """Pede o que falta, monta o arquivo comum e grava. Sem nenhuma resposta, nada é regravado."""
    import desfechos_sus as ds
    from coletores_base import buscar, gravar, hoje_editorial, ler
    buscar_fn = buscar_fn or buscar; ler_fn = ler_fn or ler; gravar_fn = gravar_fn or gravar
    hoje = hoje or hoje_editorial()
    anterior = ler_fn(ds.caminho(DESFECHO))
    todas = janelas(hoje)
    respostas, falhas = {}, []
    for ini, fim in a_pedir(todas, anterior):
        try:
            respostas[(ini, fim)] = json.loads(buscar_fn(f"{API}?start_date={ini}&end_date={fim}", timeout=60))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{ini:%Y-%m}: {type(e).__name__}")
    novos = {uf: s for uf, s in serie_de(respostas).items() if uf != "BR"}
    if not novos:
        print(f"óbitos: nenhum mês respondido ({len(falhas)} falha(s)); o arquivo anterior fica")
        return False
    ufs = sorted(set(ds.uf_por_codigo(ler_fn).values()) | set(novos))
    serie = unir(anterior, novos, todas, ufs)
    sem_valor = sorted({p for s in serie.values() for p, v in s.items() if v is None})
    lacunas = ([f"meses sem resposta da fonte nesta rodada: {', '.join(falhas)}"] if falhas else []) + \
              ([f"meses sem valor: {', '.join(sem_valor)}"] if sem_valor else []) + \
              ["óbito por causa: o painel por causa não está mais no portal (sondagem de 17/10/2026)"]
    obj = ds.montar(desfecho=DESFECHO, rotulo="Óbitos registrados em cartório", unidade="óbitos registrados",
                    periodo="mes", territorio="UF, como o Portal da Transparência do Registro Civil agrega",
                    serie=serie, fonte=FONTE, cadencia="diária; o mês corrente cresce ao longo dos dias",
                    coletado_em=hoje.isoformat(), n_parciais=1, populacao=ds.populacao_por_uf(ler_fn),
                    anterior=anterior, lacunas=lacunas)
    ok = ds.gravar_desfecho(obj, gravar_fn=gravar_fn)
    print(f"óbitos: {len(respostas)} mês(es) pedidos e respondidos, {len(falhas)} falha(s); "
          f"{len(serie)} UFs, {len(todas)} meses; gravado: {ok}")
    return ok


def sondar() -> int:
    """Só mede e imprime: a API responde para jan/2019 e para o mês passado?"""
    from coletores_base import buscar, hoje_editorial
    hoje = hoje_editorial()
    print(f"== Registro Civil · {RC_BASE} · {hoje}")
    for ini, fim in (janelas(hoje)[0], janelas(hoje)[-2]):
        try:
            s = serie_de({(ini, fim): json.loads(buscar(f"{API}?start_date={ini}&end_date={fim}", timeout=60))})
            print(f"  {ini:%Y-%m}: BR {s.get('BR')} · UFs {len(s) - 1}")
        except Exception as e:  # noqa: BLE001
            print(f"  {ini:%Y-%m}: falhou ({type(e).__name__}: {str(e)[:120]})")
    return 0


# ============================================================================================
# Autoteste (sem rede, sem escrita: ler, gravar e buscar são falsos)
# ============================================================================================
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()


def _falsos(anterior=None, falhar=()):
    gravados, pedidos = {}, []

    def ler_fn(c):
        if c == "municipios_ibge_referencia.json":
            return [{"codigo_ibge": f"{i + 11}00000", "uf": u} for i, u in enumerate(UFS)]
        if c == "populacao_censo2022.json":
            return {f"{i + 11}00000": 100000 for i in range(27)}
        return anterior if c == "saude_desfechos/obitos.json" else None

    def gravar_fn(c, obj, **_kw):
        gravados[c] = obj

    def buscar_fn(url, timeout=60):
        pedidos.append(url)
        if any(f in url for f in falhar):
            raise OSError("fora do ar")
        return json.dumps({"data": [{"name": u, "total": 10} for u in UFS]}).encode()
    return ler_fn, gravar_fn, buscar_fn, gravados, pedidos


def _t_primeira_rodada():
    ler_fn, gravar_fn, buscar_fn, g, pedidos = _falsos()
    ok = coletar(buscar_fn, ler_fn, gravar_fn, hoje=datetime.date(2026, 10, 17))
    o = g.get("saude_desfechos/obitos.json")
    return (ok and len(pedidos) == 94 and o["serie"]["AC"]["2019-01"] == 10 and o["serie"]["BR"]["2026-10"] == 270
            and o["parcial"] == ["2026-10"] and o["por_100mil"]["AC"]["2026-01"] == 10.0)


def _t_incremental():
    ler_fn, gravar_fn, buscar_fn, g, _p = _falsos()
    coletar(buscar_fn, ler_fn, gravar_fn, hoje=datetime.date(2026, 10, 17))
    ler2, gravar2, buscar2, g2, pedidos2 = _falsos(anterior=g["saude_desfechos/obitos.json"])
    coletar(buscar2, ler2, gravar2, hoje=datetime.date(2026, 10, 18))
    return len(pedidos2) == REPEDIR and g2["saude_desfechos/obitos.json"]["cortes_mapa"] == \
        g["saude_desfechos/obitos.json"]["cortes_mapa"]


def _t_falha_vira_lacuna_nao_zero():
    ler_fn, gravar_fn, buscar_fn, g, _p = _falsos(falhar=("start_date=2020-03-01",))
    coletar(buscar_fn, ler_fn, gravar_fn, hoje=datetime.date(2026, 10, 17))
    o = g["saude_desfechos/obitos.json"]
    return o["serie"]["AC"]["2020-03"] is None and o["serie"]["BR"]["2020-03"] is None and \
        any("2020-03" in l for l in o["lacunas"])


def _t_falha_total_nao_regrava():
    ler_fn, gravar_fn, buscar_fn, g, _p = _falsos(falhar=("start_date",))
    return coletar(buscar_fn, ler_fn, gravar_fn, hoje=datetime.date(2026, 10, 17)) is False and not g


def _t_mes_repedido_e_incompleto():
    todas = janelas(datetime.date(2026, 10, 17))
    ant = {"serie": {u: {f"{i.year}-{i.month:02d}": 1 for i, _f in todas} for u in UFS}}
    ant["serie"]["SP"]["2021-05"] = None
    pedir = [f"{i:%Y-%m}" for i, _f in a_pedir(todas, ant)]
    return pedir == ["2021-05", "2026-08", "2026-09", "2026-10"]


def _t_trava_estrutural():
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8").split("# =====")[0]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json\"", "indice.json", "monitor_saude.json",
                 "obitos_registro_civil.json\"")
    return not any(p in fonte for p in proibidos) and "gravar" not in fonte.split("def sondar")[1]


TESTES = {
    "primeira rodada: 94 meses desde jan/2019, BR = soma das 27, mês corrente parcial, taxa": _t_primeira_rodada,
    "segunda rodada pede só os 3 últimos meses e mantém os cortes congelados": _t_incremental,
    "mês que falhou fica null (lacuna declarada), nunca zero": _t_falha_vira_lacuna_nao_zero,
    "nenhuma resposta: nada regravado": _t_falha_total_nao_regrava,
    "mês incompleto no anterior é pedido de novo": _t_mes_repedido_e_incompleto,
    "trava estrutural: não escreve no índice nem no arquivo da página atual; sondagem não grava":
        _t_trava_estrutural,
}


def main() -> int:
    if "--autoteste" in sys.argv:
        from coletores_base import rodar_autoteste
        return rodar_autoteste(TESTES)
    if "--sondar" in sys.argv:
        return sondar()
    coletar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
