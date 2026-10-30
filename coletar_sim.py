#!/usr/bin/env python3
"""Óbitos por causa básica, UF e mês: SIM (Declaração de Óbito), arquivos DO do DATASUS.

Faixa E2 (HANDOVER_SUS_DESFECHOS_16-10-2026, camada C). Peso zero, como todo o MARÉ Saúde: conta óbitos
registrados; não atribui nenhum ao El Niño. Complementa `coletar_obitos.py` (Registro Civil, sem causa).

O QUE A SÉRIE CONTA
-------------------
Óbitos não fetais por mês de OCORRÊNCIA (`DTOBITO`) e causa básica (`CAUSABAS`), nos grupos de CID-10 de
`coletar_sih.GRUPOS` (os mesmos das internações; ver `GRUPOS_SIM`). Um arquivo por UF e ano: o consolidado
(`SIM/CID10/DORES`) onde existe, o preliminar (`SIM/PRELIM/DORES`) nos anos seguintes. O ano preliminar só
tem meses até o último com registro; o que vem depois não foi publicado e fica fora (ausência, nunca zero).
Os `N_PARCIAIS` meses mais recentes são `parcial`: o registro de óbito chega com atraso (medida a conferir).

TERRITÓRIO. A UF é a do NOME do arquivo (`DO<UF><ANO>`). Se isso é a UF de ocorrência ou de residência não
foi verificado: `--sondar` mede a parcela de registros cujo `CODMUNOCOR` e cujo `CODMUNRES` começam pelo
código da UF do arquivo, e a lacuna do arquivo comum diz que o território é o do arquivo.

LEITURA. Arquivo pequeno (27 UFs × ~8 anos). Lê o que ainda não foi lido ou, no ano preliminar, mudou de
tamanho no FTP. Leitor `.dbc`, FTP e ritmo são os de `coletar_datasus_dbc.py` e `coletar_sih.py`, importados.

USO
  python3 coletar_sim.py --autoteste
  python3 coletar_sim.py --sondar          # só mede e imprime; não grava nada
  python3 coletar_sim.py [--orcamento S]   # lê o FTP por até S segundos e grava os arquivos comuns
"""
import datetime
import pathlib
import re
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

DIR_FINAL = "/dissemin/publicos/SIM/CID10/DORES"
DIR_PRELIM = "/dissemin/publicos/SIM/PRELIM/DORES"
CAMPOS = ("DTOBITO", "CAUSABAS", "CODMUNOCOR", "CODMUNRES")
RE_DO = re.compile(r"^DO([A-Z]{2})(\d{4})\.DBC$", re.I)
ANO_INICIAL = 2019
ORCAMENTO_S = 1500
N_PARCIAIS = 2        # meses mais recentes marcados `parcial` (atraso do registro: não verificado)
PARADA_APOS = 5       # falhas seguidas: a fonte caiu, a rodada para
GRUPOS_SIM = ("respiratorias", "cardio", "renal", "desidratacao", "fumaca", "calor")
TOTAL = "obitos_sim_total"
ROTULOS = {
    "respiratorias": "Óbitos por doenças respiratórias agudas (CID-10 J00 a J22)",
    "cardio": "Óbitos por doença isquêmica do coração e cerebrovascular (CID-10 I20 a I25 e I60 a I64)",
    "renal": "Óbitos por insuficiência renal (CID-10 N17 a N19)",
    "desidratacao": "Óbitos por desidratação (CID-10 E86)",
    "fumaca": "Óbitos por efeito tóxico de gases, fumaças e vapores (CID-10 T59)",
    "calor": "Óbitos por exposição ao calor natural excessivo (CID-10 X30, causa externa)",
}
CRITERIO = "causa-externa-x30"   # muda quando muda o que um grupo conta: força a releitura de todos os arquivos
DESFECHOS = {TOTAL: "Óbitos por todas as causas (SIM, por mês de ocorrência)",
             **{f"obitos_{g}": r for g, r in ROTULOS.items()}}


# ============================================================================================
# Funções puras
# ============================================================================================
def arquivos(listagem_final: dict, listagem_prelim: dict) -> dict:
    """{(UF, ano): (caminho, tamanho, preliminar)} de 2019 em diante: consolidado onde houver, preliminar
    nos demais anos. `listagem_*` é {nome: bytes}. Função pura."""
    out = {}
    for lista, dir_, prelim in ((listagem_prelim, DIR_PRELIM, True), (listagem_final, DIR_FINAL, False)):
        for nome, tam in lista.items():
            m = RE_DO.match(nome.strip())
            if m and int(m.group(2)) >= ANO_INICIAL and m.group(1).upper() != "BR":
                out[(m.group(1).upper(), int(m.group(2)))] = (f"{dir_}/{nome}", tam, prelim)
    return out


def a_ler(todos: dict, lidos: dict) -> list:
    """[(uf, ano)] a baixar, do ano mais recente ao mais antigo: o que nunca foi lido e o que mudou de
    tamanho desde a leitura (`lidos` = {caminho: bytes}). Função pura."""
    return sorted((k for k, (cam, tam, _p) in todos.items() if lidos.get(cam) != tam),
                  key=lambda k: (k[1], k[0]), reverse=True)


def grupos_da_causa(cid) -> list:
    """Grupos do SIM para a causa básica. Capítulo XIX (T00 a T98) não pode ser causa básica: o calor é a causa
    externa X30, não o T67 das internações. Função pura."""
    from coletar_sih import grupo_do_cid
    g = [x for x in grupo_do_cid(cid) if x in GRUPOS_SIM and x != "calor"]
    return g + ["calor"] if (cid or "").strip().upper().replace(".", "").startswith("X30") else g


def agregar(registros, uf: str, ano: int, preliminar: bool) -> dict:
    """{'total'|grupo: {'AAAA-MM': n}} de um arquivo DO de `uf` e `ano`. Função pura.

    Só conta data do próprio ano do arquivo. No arquivo consolidado os 12 meses existem; no preliminar, só
    os meses até o último com registro: depois dele o mês não foi publicado, não é zero."""
    cont = {}
    for r in registros:
        d = str(r.get("DTOBITO") or "").strip()
        if not (len(d) == 8 and d.isdigit() and int(d[4:]) == ano and 1 <= int(d[2:4]) <= 12):
            continue
        chave = f"{ano:04d}-{d[2:4]}"
        for g in ["total"] + grupos_da_causa(r.get("CAUSABAS")):
            cont.setdefault(g, {})
            cont[g][chave] = cont[g].get(chave, 0) + 1
    meses = sorted(cont.get("total", {}))
    if not meses:
        return {}
    ate = 12 if not preliminar else int(meses[-1][5:])
    todos = [f"{ano:04d}-{m:02d}" for m in range(1, ate + 1)]
    return {g: {p: cont.get(g, {}).get(p, 0) for p in todos} for g in ["total", *GRUPOS_SIM]}


def alinhamento(registros, uf: str, codigo_uf: str) -> dict:
    """Parcela dos registros cujo município de ocorrência e de residência começam pelo código da UF do
    arquivo (medição de território; `--sondar`). Função pura."""
    n = occ = res = 0
    for r in registros:
        n += 1
        occ += str(r.get("CODMUNOCOR") or "").startswith(codigo_uf)
        res += str(r.get("CODMUNRES") or "").startswith(codigo_uf)
    return {"n": n, "ocorrencia": round(occ / n, 4) if n else None, "residencia": round(res / n, 4) if n else None}


# ============================================================================================
# Coleta
# ============================================================================================
def coletar(listar=None, baixar=None, ler_fn=None, gravar_fn=None, hoje=None, decodificar=None,
            orcamento_s: int = ORCAMENTO_S, relogio=None, pausa: float = None) -> bool:
    """Lê o que falta no FTP e grava os arquivos comuns. Sem nenhum arquivo lido, nada é regravado."""
    import desfechos_sus as ds
    from coletar_datasus_dbc import PAUSA, baixar_ftp, ler_dbc, listar_ftp
    from coletar_sih import espacar
    from coletores_base import gravar, hoje_editorial, ler
    listar = listar or listar_ftp; baixar = baixar or baixar_ftp; decodificar = decodificar or ler_dbc
    ler_fn = ler_fn or ler; gravar_fn = gravar_fn or gravar; relogio = relogio or time.monotonic
    hoje = hoje or hoje_editorial()
    baixar = espacar(baixar, PAUSA if pausa is None else pausa)
    ant = {d: ds.ler_desfecho(d, ler_fn) for d in DESFECHOS}
    # Um arquivo só está lido quando TODOS os desfechos existem: arquivo comum novo força a releitura.
    lidos = (dict(ant[TOTAL]["fonte"].get("arquivos_lidos", {}))
             if all(ant.values()) and ant[TOTAL]["fonte"].get("criterio_versao") == CRITERIO else {})
    todos = arquivos(dict(listar(DIR_FINAL)), dict(listar(DIR_PRELIM)))
    fila = a_ler(todos, lidos)
    novos = {g: {} for g in ["total", *GRUPOS_SIM]}
    falhas, seguidas, feitos, inicio = [], 0, {}, relogio()
    for uf, ano in fila:
        if relogio() - inicio > orcamento_s or seguidas >= PARADA_APOS:
            break
        cam, tam, prelim = todos[(uf, ano)]
        try:
            _desc, linhas = decodificar(baixar(cam), CAMPOS)
            ag = agregar(linhas, uf, ano, prelim)
            if not ag:
                raise ValueError("arquivo sem registro do ano")
            for g, s in ag.items():
                novos[g].setdefault(uf, {}).update(s)
            feitos[cam] = tam; seguidas = 0
            novos.setdefault("_anos", set()).add((uf, ano))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{cam.rsplit('/', 1)[1]}: {type(e).__name__}"); seguidas += 1
    if not feitos:
        print(f"SIM: nenhum arquivo lido ({len(fila)} na fila, {len(falhas)} falha(s)); os arquivos anteriores ficam")
        return False
    anos_lidos = novos.pop("_anos")
    pendentes = [k for k in fila if todos[k][0] not in feitos]
    lacunas = ([f"{len(pendentes)} arquivo(s) de UF e ano ainda não lidos; a leitura segue nas próximas rodadas"]
               if pendentes else []) + \
              ([f"falha de leitura nesta rodada: {', '.join(falhas[:5])}" + (" e outras" if len(falhas) > 5 else "")]
               if falhas else []) + \
              ["território: a UF é a do nome do arquivo (DO<UF><ano>); se é a de ocorrência ou a de residência não foi verificado",
               f"os {N_PARCIAIS} meses mais recentes são parciais: o registro do óbito chega com atraso (extensão do atraso não verificada)"]
    fonte = {"sistema": "SIM, Declaração de Óbito, Ministério da Saúde, microdados no FTP do DATASUS",
             "url": f"ftp://ftp.datasus.gov.br{DIR_PRELIM}/",
             "criterio": "óbitos não fetais; causa básica (CAUSABAS); consolidado (CID10/DORES) onde existe, preliminar nos anos seguintes",
             "data_do_periodo": "mês de ocorrência (DTOBITO)", "uf": "UF do nome do arquivo",
             "criterio_versao": CRITERIO, "arquivos_lidos": {**lidos, **feitos}}
    ufs = sorted(ds.uf_por_codigo(ler_fn).values())
    populacao = ds.populacao_por_uf(ler_fn)
    ok = True
    for desfecho, rotulo in DESFECHOS.items():
        g = "total" if desfecho == TOTAL else desfecho[len("obitos_"):]
        velho = (ant[desfecho] or {}).get("serie", {})
        serie = {}
        for uf in ufs:
            antigo = {p: v for p, v in velho.get(uf, {}).items() if (uf, int(p[:4])) not in anos_lidos}
            serie[uf] = {**antigo, **novos[g].get(uf, {})}
        completa = not pendentes and not any("ainda não lidos" in x for x in (ant[desfecho] or {}).get("lacunas", []))
        obj = ds.montar(desfecho=desfecho, rotulo=rotulo, unidade="óbitos", periodo="mes",
                        territorio="UF do arquivo", serie={u: s for u, s in serie.items() if s}, fonte=fonte,
                        cadencia="mensal; o preliminar do ano corrente cresce a cada atualização do DATASUS",
                        coletado_em=hoje.isoformat(), anos_preliminares=[hoje.year - 1, hoje.year],
                        n_parciais=N_PARCIAIS, populacao=populacao,
                        anterior=ant[desfecho] if completa else None, lacunas=lacunas)
        ok = ds.gravar_desfecho(obj, gravar_fn=gravar_fn) and ok
    print(f"SIM: {len(feitos)} arquivo(s) lido(s), {len(falhas)} falha(s), {len(pendentes)} por ler; gravado: {ok}")
    return ok


def sondar() -> int:
    from coletar_datasus_dbc import baixar_ftp, ler_dbc, listar_ftp
    from coletores_base import hoje_editorial
    print(f"== SIM · FTP {DIR_FINAL} e {DIR_PRELIM} · {hoje_editorial()}")
    try:
        todos = arquivos(dict(listar_ftp(DIR_FINAL)), dict(listar_ftp(DIR_PRELIM)))
    except Exception as e:  # noqa: BLE001
        print(f"FTP: falhou ({type(e).__name__}: {e})")
        return 0
    anos = sorted({a for _u, a in todos})
    print(f"arquivos: {len(todos)} · anos {anos[0]}–{anos[-1]}" if anos else "arquivos: 0")
    for a in anos:
        n = [k for k in todos if k[1] == a]
        print(f"  {a}: {len(n)} UFs · {'preliminar' if todos[n[0]][2] else 'consolidado'}")
    if not anos:
        return 0
    for uf, cod in (("AP", "16"), ("AC", "12")):
        k = (uf, anos[-1])
        if k not in todos:
            continue
        cam, tam, prelim = todos[k]
        dbc = baixar_ftp(cam)
        _d, linhas = ler_dbc(dbc, CAMPOS)
        regs = list(linhas)
        ag = agregar(regs, uf, k[1], prelim)
        print(f"{uf} {k[1]}: {len(regs)} registros · {tam} bytes · alinhamento {alinhamento(regs, uf, cod)}")
        print(f"  total por mês: {ag.get('total')}")
    return 0


# ============================================================================================
# Autoteste (sem rede, sem escrita)
# ============================================================================================
def autoteste() -> int:
    from coletar_sih import UFS
    casos = []
    lf = {"DOAC2024.dbc": 10, "DOAC2019.DBC": 10, "DOAC2018.dbc": 10, "DOBR2024.dbc": 10, "LEIAME.txt": 1}
    lp = {"DOAC2024.dbc": 11, "DOAC2025.dbc": 5, "DOAC2026.dbc": 7}
    a = arquivos(lf, lp)
    casos.append(("consolidado vence o preliminar do mesmo ano; BR e anos < 2019 fora",
                  a[("AC", 2024)] == (DIR_FINAL + "/DOAC2024.dbc", 10, False) and a[("AC", 2025)][2]
                  and ("AC", 2018) not in a and not any(u == "BR" for u, _ in a)))
    casos.append(("fila: ano mais recente primeiro; só o não lido ou de tamanho mudado",
                  a_ler(a, {}) [0] == ("AC", 2026)
                  and a_ler(a, {DIR_FINAL + "/DOAC2024.dbc": 10, DIR_FINAL + "/DOAC2019.DBC": 10,
                                DIR_PRELIM + "/DOAC2025.dbc": 5, DIR_PRELIM + "/DOAC2026.dbc": 6}) == [("AC", 2026)]))
    regs = [{"DTOBITO": "15072026", "CAUSABAS": "J189"}, {"DTOBITO": "02072026", "CAUSABAS": "I219"},
            {"DTOBITO": "01082026", "CAUSABAS": "A09"}, {"DTOBITO": "01012025", "CAUSABAS": "J189"},
            {"DTOBITO": "", "CAUSABAS": "J189"}, {"DTOBITO": "32132026", "CAUSABAS": "J189"},
            {"DTOBITO": "10082026", "CAUSABAS": "F200"}, {"DTOBITO": "11082026", "CAUSABAS": "X30"},
            {"DTOBITO": "12082026", "CAUSABAS": "T671"}]
    p = agregar(regs, "AC", 2026, True)
    casos.append(("preliminar: meses só até o último com registro; mês sem caso do grupo é zero medido",
                  sorted(p["total"]) == [f"2026-{m:02d}" for m in range(1, 9)] and p["respiratorias"]["2026-07"] == 1
                  and p["cardio"]["2026-08"] == 0 and p["total"]["2026-03"] == 0))
    casos.append(("data de outro ano, vazia ou impossível não conta", sum(p["total"].values()) == 6))
    casos.append(("calor é a causa básica X30; T67 não é causa básica e não conta",
                  p["calor"]["2026-08"] == 1 and sum(p["calor"].values()) == 1))
    casos.append(("saúde mental e ICSAP não são grupos do SIM", "saude_mental" not in p and "icsap" not in p))
    c = agregar(regs, "AC", 2025, False)
    casos.append(("consolidado: 12 meses, zero medido nos vazios", len(c["total"]) == 12 and c["total"]["2025-01"] == 1
                  and c["total"]["2025-06"] == 0))
    casos.append(("arquivo sem registro do ano devolve vazio", agregar([{"DTOBITO": "01012020", "CAUSABAS": "J18"}], "AC", 2026, True) == {}))
    casos.append(("alinhamento do território", alinhamento([{"CODMUNOCOR": "120040", "CODMUNRES": "130010"}], "AC", "12")
                  == {"n": 1, "ocorrencia": 1.0, "residencia": 0.0}))
    # ---- gravação na forma comum (ler, gravar, listar, baixar e decodificar são falsos)
    gravados, baixados = {}, []

    def fake_ler(c):
        if c == "municipios_ibge_referencia.json":
            return [{"codigo_ibge": f"{i + 11}00000", "uf": u} for i, u in enumerate(UFS)]
        if c == "populacao_censo2022.json":
            return {f"{i + 11}00000": 100000 for i in range(27)}
        return gravados.get(c)

    def fake_gravar(c, obj, **_kw):
        gravados[c] = obj

    def fake_baixar(caminho):
        baixados.append(caminho)
        return caminho

    def fake_decod(dados, campos):
        ano = int(dados[-8:-4])
        if "DOAC2025" in dados:
            raise OSError("fora do ar")
        return None, iter([{"DTOBITO": f"1507{ano}", "CAUSABAS": c} for c in ("J180", "I219", "A09", "E860")])

    fin = {f"DO{u}2024.dbc": 10 for u in UFS}
    pre = {f"DO{u}{y}.dbc": 5 for u in UFS for y in (2025, 2026)}

    def lista(d):
        return list((fin if d == DIR_FINAL else pre).items())

    hoje = datetime.date(2026, 10, 23)
    ok1 = coletar(lista, fake_baixar, fake_ler, fake_gravar, hoje, fake_decod, pausa=0)
    t = gravados.get("saude_desfechos/obitos_sim_total.json", {})
    casos.append(("1ª rodada grava os sete arquivos comuns", ok1 and len(gravados) == 7))
    casos.append(("grupo conta só o seu CID; E86 é desidratação",
                  gravados["saude_desfechos/obitos_respiratorias.json"]["serie"]["SP"]["2026-07"] == 1
                  and gravados["saude_desfechos/obitos_desidratacao.json"]["serie"]["SP"]["2026-07"] == 1
                  and t["serie"]["SP"]["2026-07"] == 4))
    casos.append(("ano que falhou (AC 2025) fica fora, não vira zero; lacuna declarada",
                  not any(p.startswith("2025") for p in t["serie"]["AC"]) and any("DOAC2025" in x for x in t["lacunas"])))
    casos.append(("preliminar não ganha mês depois do último com registro", "2026-08" not in t["serie"]["SP"]
                  and t["serie"]["SP"]["2026-06"] == 0))
    casos.append(("meses recentes marcados parciais; território declarado como o do arquivo",
                  t["parcial"] == ["2026-06", "2026-07"] and t["territorio"] == "UF do arquivo"
                  and any("território" in x for x in t["lacunas"])))
    baixados.clear()
    coletar(lista, fake_baixar, fake_ler, fake_gravar, hoje, fake_decod, pausa=0)
    casos.append(("2ª rodada pede só o que faltou", len(baixados) == 1 and baixados[0].endswith("DOAC2025.dbc")))
    baixados.clear()
    pre = {n: (9 if n.startswith("DOSP2026") else v) for n, v in pre.items()}
    coletar(lista, fake_baixar, fake_ler, fake_gravar, hoje, fake_decod, pausa=0)
    casos.append(("ano preliminar com tamanho novo é relido e substitui o antigo",
                  sum("DOSP2026" in x for x in baixados) == 1))
    gravados.clear(); baixados.clear(); r = iter(range(0, 10 ** 6, 100))
    coletar(lista, fake_baixar, fake_ler, fake_gravar, hoje, fake_decod, orcamento_s=350, relogio=lambda: next(r), pausa=0)
    casos.append(("orçamento acaba: lê o ano mais recente primeiro e declara os pendentes",
                  len(baixados) == 3 and all("2026" in x for x in baixados)
                  and any("ainda não lidos" in x for x in gravados["saude_desfechos/obitos_sim_total.json"]["lacunas"])))
    gravados.clear(); baixados.clear()
    caiu = coletar(lista, fake_baixar, fake_ler, fake_gravar, hoje, lambda d, c: (_ for _ in ()).throw(OSError("fora")), pausa=0)
    casos.append(("fonte fora do ar: nada gravado e a rodada para na 5ª falha seguida",
                  caiu is False and not gravados and len(baixados) == PARADA_APOS))
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json")
    casos.append(("trava estrutural: não escreve nos arquivos do índice", not any(x in fonte for x in proibidos)))
    casos.append(("trava estrutural: a sondagem não grava série", "gravar" not in fonte.split("def sondar")[1]))
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--sondar" in sys.argv:
        return sondar()
    orcamento = int(sys.argv[sys.argv.index("--orcamento") + 1]) if "--orcamento" in sys.argv else ORCAMENTO_S
    return 0 if coletar(orcamento_s=orcamento) else 1


if __name__ == "__main__":
    sys.exit(main())
