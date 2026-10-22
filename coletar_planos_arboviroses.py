#!/usr/bin/env python3
"""Planos municipais de contingência de arboviroses (dengue, chikungunya, zika) nos diários oficiais.

Ordem da editoria, 22/10/2026 (HANDOVER_SAUDE_V06 §5, prioridade máxima): coletar e preservar o plano de
cada município, registrar a fonte e a base, capitais e maiores primeiro. Peso zero: o arquivo não entra
na nota da Saúde.

ROTA (a que roda em qualquer executor, sem credencial): o texto integral dos diários municipais no
Querido Diário, uma busca por município e termo. A função de consulta, a preservação por hash e a pista
são as de `consultar_querido_diario.py`; esta peça só decide QUEM consultar, O QUE vale como menção e
QUAL estatuto o município recebe. Páginas de prefeitura e de secretaria estadual não têm rota de máquina
comum: ficam como rota futura, sem endereço inventado.

ESTATUTO (vocabulário da casa, nunca zero):
  menção localizada em diário oficial · não localizado até o corte · não verificado.
`menção` não é `plano lido`: o excerto cita o plano, o documento ainda não foi aberto pelo juiz.
Município sem cobertura no acervo ou consulta que falhou é `não verificado`, nunca `não localizado`.

TRAVAS (as mesmas de `descobrir_planos.py`):
  1. ESTRUTURAL: escreve só `data/planos_arboviroses.json` e a fila `data/pistas_arboviroses.json`
     (esta pela porta `scripts/pistas.py`); nunca estados.json, saude_uf.json, municipios.json,
     indice.json nem monitor_saude.json.
  2. DE CAMPO: toda pista nasce com `documento_oficial_confirmado: null` e `promovivel: false`.
  3. DE PROCESSO: a saída vai à fila própria, que nenhum juiz do índice lê; nada vai ao banco.

Uso: python3 coletar_planos_arboviroses.py [--orcamento SEG] [--limite N]
     python3 coletar_planos_arboviroses.py --autoteste        (offline, não escreve em data/)
"""
import json
import sys
import time
import urllib.error

import consultar_querido_diario as qd
from coletores_base import RAIZ, ler, gravar, hoje_editorial, normalizar_nome, rodar_autoteste

ARQUIVO = "planos_arboviroses.json"
FILA = "pistas_arboviroses.json"
JANELA_DESDE = "2024-01-01"   # plano de contingência vale por temporada; a anterior ainda orienta
CONSULTAS = ('"plano de contingência" dengue', '"plano de contingência" arboviroses',
             '"plano de contingência" chikungunya')
ASSUNTOS = ("DENGUE", "ARBOVIR", "CHIKUNGUNYA", "ZIKA")
MENCAO, NAO_LOCALIZADO, NAO_VERIFICADO = (
    "menção localizada em diário oficial", "não localizado até o corte", "não verificado")
RECUSAS_REAIS = (401, 403, 429, 451)   # bloqueio de acesso se respeita: a rodada para
PASSOS_ENTRE_SALVAMENTOS = 10


class Recusa(Exception):
    """A fonte recusou o acesso (401/403/429/451): a rodada termina, sem insistir."""


def ordem_de_busca(ref: list, populacao: dict, casos: dict) -> list:
    """Capitais, depois alternando o mais populoso e o de mais casos estimados na última semana lida,
    sem repetir. Função pura; devolve [(ibge, nome, uf)]."""
    por_ibge = {f"{m['codigo_ibge']:07d}": (f"{m['codigo_ibge']:07d}", m["nome"], m["uf"]) for m in ref}
    capitais = [i for i, (_, n, u) in por_ibge.items() if qd.CAPITAIS.get(n) == u]
    por_pop = sorted(por_ibge, key=lambda i: (-populacao.get(i, 0), i))
    por_casos = sorted((i for i in por_ibge if casos.get(i)), key=lambda i: (-casos[i], i))
    ordem, vistos = [], set()
    for i in capitais + [x for par in zip(por_pop, por_casos + por_pop) for x in par] + por_pop:
        if i not in vistos:
            vistos.add(i)
            ordem.append(por_ibge[i])
    return ordem


def excerto_vale(excerto: str) -> bool:
    """O excerto fala de plano de contingência E de arbovirose. Função pura."""
    t = normalizar_nome(excerto or "")
    return "CONTINGE" in t and any(a in t for a in ASSUNTOS)


def gazeta_vale(g: dict) -> bool:
    return any(excerto_vale(e) for e in (g.get("excerpts") or []))


def registro_do_municipio(cobertura, achados: list, motivo: str, hoje: str) -> dict:
    """O registro do município na rodada. `cobertura`: True, False (acervo sem o município) ou None
    (consulta falhou). Função pura."""
    if cobertura is not True:
        estatuto = NAO_VERIFICADO
        motivo = motivo or "município sem cobertura no acervo de diários"
    else:
        estatuto = MENCAO if achados else NAO_LOCALIZADO
        motivo = ""
    return {"estatuto": estatuto, "consultado_em": hoje, "janela_desde": JANELA_DESDE,
            "rota": "querido_diario", "motivo": motivo, "achados": achados}


def achado_da_gazeta(g: dict, termo: str, hash_evidencia) -> dict:
    return {"url": g.get("url") or g.get("txt_url"), "data_publicacao": g.get("date"),
            "edicao": g.get("edition"), "consulta": termo,
            "trecho": " ".join(str((g.get("excerpts") or [""])[0]).split())[:500],
            "hash_evidencia": hash_evidencia}


def pista_do_achado(g: dict, nome: str, uf: str, ibge: str, termo: str, hash_evidencia, hoje: str):
    """A pista que vai à porta única, ou None. Trava de campo: nasce não confirmada e não promovível."""
    p = qd.pista_da_gazeta(g, nome, uf, ibge, termo, hash_evidencia, hoje)
    if p:
        p.update({"tipo": "plano", "assunto": "arboviroses", "nivel": "B",
                  "documento_oficial_confirmado": None, "promovivel": False})
    return p


def consultar(ibge: str, nome: str, uf: str, hoje: str, obter=None, dormir=time.sleep, preservar=None):
    """Consulta um município. Devolve (registro, pistas). `obter`/`preservar` são injetáveis."""
    obter = obter or qd._get
    preservar = preservar or qd._preservar_achado
    achados, pistas, vistos = [], [], set()
    try:
        base = obter({"territory_ids": ibge, "size": 1})
        dormir(1.1)
        if not base.get("total_gazettes"):
            return registro_do_municipio(False, [], "", hoje), []
        for termo in CONSULTAS:
            r = obter({"territory_ids": ibge, "querystring": termo, "published_since": JANELA_DESDE,
                       "size": 5, "excerpt_size": 300, "number_of_excerpts": 1})
            dormir(1.1)
            for g in r.get("gazettes", []):
                url = g.get("url") or g.get("txt_url")
                if not url or url in vistos or not gazeta_vale(g):
                    continue
                vistos.add(url)
                h = preservar(g)
                achados.append(achado_da_gazeta(g, termo, h))
                pistas.append(pista_do_achado(g, nome, uf, ibge, termo, h, hoje))
        return registro_do_municipio(True, achados, "", hoje), [p for p in pistas if p]
    except urllib.error.HTTPError as e:
        if e.code in RECUSAS_REAIS:
            raise Recusa(f"HTTP {e.code}") from e
        return _incompleta(achados, pistas, f"HTTP {e.code}", hoje)
    except Exception as e:  # noqa: BLE001 — falha de rede é lacuna declarada, nunca "não localizado"
        return _incompleta(achados, pistas, type(e).__name__, hoje)


def _incompleta(achados: list, pistas: list, erro: str, hoje: str):
    """Consulta interrompida: o que já foi preservado fica (menção real); sem achado, `não verificado`."""
    if achados:
        reg = registro_do_municipio(True, achados, "", hoje)
        reg["motivo"] = f"consulta incompleta: {erro}"
        return reg, [p for p in pistas if p]
    return registro_do_municipio(None, [], f"consulta falhou: {erro}", hoje), []


def casos_recentes() -> dict:
    """{ibge: casos estimados de dengue na última semana lida}, de `data/saude_municipio/<UF>.json`."""
    saida = {}
    for uf in sorted({m["uf"] for m in json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json",
                                                      encoding="utf-8"))}):
        doc = ler(f"saude_municipio/{uf}.json", {}) or {}
        for ibge, m in (doc.get("municipios") or {}).items():
            c = (m.get("dengue") or {}).get("casos_estimados")
            if isinstance(c, (int, float)):
                saida[ibge] = c
    return saida


def rodar(orcamento: int, limite: int) -> int:
    from scripts.pistas import gravar_lote
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    ordem = ordem_de_busca(ref, ler("populacao_censo2022.json", {}), casos_recentes())
    doc = ler(ARQUIVO, {}) or {}
    doc.setdefault("municipios", {})
    hoje = hoje_editorial().isoformat()
    fatia, doc["cursor"] = qd.fatia_do_cursor(ordem, int(doc.get("cursor") or 0), limite)
    inicio, feitos, novas, parou = time.monotonic(), 0, [], ""
    for ibge, nome, uf in fatia:
        if time.monotonic() - inicio > orcamento:
            parou = "orçamento de tempo"
            break
        try:
            doc["municipios"][ibge], pistas = consultar(ibge, nome, uf, hoje)
        except Recusa as e:
            parou = f"recusa real da fonte ({e}); respeitada"
            break
        doc["municipios"][ibge].update({"nome": nome, "uf": uf})
        novas += pistas
        feitos += 1
        if feitos % PASSOS_ENTRE_SALVAMENTOS == 0:
            gravar(ARQUIVO, doc)
    if parou:   # o cursor só avança até onde a rodada chegou
        doc["cursor"] = (int(doc["cursor"]) - len(fatia) + feitos) % len(ordem)
    doc["execucao"] = {"data": hoje, "consultados": feitos, "paradas": parou or None,
                       "estatutos": _contagem(doc["municipios"])}
    gravar(ARQUIVO, doc)
    balanco = gravar_lote(novas, origem="querido_diario", nome_da_fila=FILA, ler_fn=ler, gravar_fn=gravar)
    print(f"{feitos} município(s) consultado(s); estatutos {doc['execucao']['estatutos']}; "
          f"fila: {balanco['gravadas']} gravada(s), {balanco['recusadas']} recusada(s)"
          + (f"; parou: {parou}" if parou else ""))
    return 0


def _contagem(municipios: dict) -> dict:
    c = {}
    for m in municipios.values():
        c[m["estatuto"]] = c.get(m["estatuto"], 0) + 1
    return c


def autoteste() -> int:
    """Offline: nada de rede, nada de escrita em `data/` (a consulta e a preservação são falsas)."""
    sys.path.insert(0, str(RAIZ))
    from scripts.pistas import normalizar, motivo_de_recusa
    ref = [{"nome": "Alfa", "uf": "AA", "codigo_ibge": 1100001}, {"nome": "Beta", "uf": "AA", "codigo_ibge": 1100002},
           {"nome": "Gama", "uf": "AA", "codigo_ibge": 1100003}, {"nome": "Recife", "uf": "PE", "codigo_ibge": 2611606}]
    g = {"url": "https://x.org/a.pdf", "date": "2026-03-10", "edition": "10",
         "excerpts": ["Aprova o Plano de Contingência da Dengue, Chikungunya e Zika do município"]}
    sem_assunto = {"url": "https://x.org/b.pdf", "excerpts": ["Plano de contingência de defesa civil"]}

    def falso(com, sem=None):
        def obter(params):
            if "querystring" not in params:
                return {"total_gazettes": 7 if com is not False else 0}
            return {"gazettes": com or []}
        return obter

    def cons(com, **kw):
        return consultar("1100001", "Alfa", "AA", "2026-10-22", obter=falso(com), dormir=lambda s: None,
                         preservar=lambda gz: "h" * 64, **kw)

    reg, pistas = cons([g, sem_assunto])
    reg0, _ = cons([])
    n = {"i": 0}

    def meio(params):
        n["i"] += 1
        if n["i"] == 3:
            raise TimeoutError("t")
        return falso([g])(params)
    parcial, pp = consultar("1100001", "Alfa", "AA", "2026-10-22", obter=meio, dormir=lambda s: None,
                            preservar=lambda gz: "h" * 64)
    regs, _ = cons(False)
    err, _ = consultar("1100001", "Alfa", "AA", "2026-10-22", dormir=lambda s: None,
                       obter=lambda p: (_ for _ in ()).throw(TimeoutError("t")))

    def recusa():
        try:
            consultar("1100001", "Alfa", "AA", "2026-10-22", dormir=lambda s: None,
                      obter=lambda p: (_ for _ in ()).throw(urllib.error.HTTPError("u", 429, "x", {}, None)))
        except Recusa:
            return True
        return False

    ordem = ordem_de_busca(ref, {"1100003": 90, "1100002": 10, "1100001": 5}, {"1100002": 50})
    fonte = open(__file__, encoding="utf-8").read().split("def autoteste")[0].split('"""', 2)[2]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json")
    escritas = [l for l in fonte.splitlines() if "gravar" in l and "import" not in l]
    return rodar_autoteste({
        "excerto com plano e arbovirose vale; defesa civil sozinha não": lambda: excerto_vale(g["excerpts"][0]) and not excerto_vale(sem_assunto["excerpts"][0]),
        "menção em diário vira estatuto de menção, com hash": lambda: reg["estatuto"] == MENCAO and reg["achados"][0]["hash_evidencia"] == "h" * 64 and len(reg["achados"]) == 1,
        "excerto sem arbovirose não conta como achado": lambda: len(reg["achados"]) == 1,
        "coberto e sem menção é 'não localizado até o corte'": lambda: reg0["estatuto"] == NAO_LOCALIZADO and reg0["motivo"] == "",
        "sem cobertura é 'não verificado', nunca 'não localizado'": lambda: regs["estatuto"] == NAO_VERIFICADO and "cobertura" in regs["motivo"],
        "falha no meio não joga fora o que já foi preservado": lambda: parcial["estatuto"] == MENCAO and "incompleta" in parcial["motivo"] and len(pp) == 1,
        "consulta que falha é 'não verificado' com o erro": lambda: err["estatuto"] == NAO_VERIFICADO and "TimeoutError" in err["motivo"],
        "429 para a rodada (recusa real, sem insistir)": recusa,
        "trava de campo: pista não confirmada e não promovível": lambda: pistas[0]["documento_oficial_confirmado"] is None and pistas[0]["promovivel"] is False,
        "a pista passa na porta única como plano": lambda: motivo_de_recusa(normalizar(pistas[0], "querido_diario"), []) == "" and pistas[0]["tipo"] == "plano",
        "ordem: capital primeiro, depois alterna população e casos": lambda: [o[0] for o in ordem] == ["2611606", "1100003", "1100002", "1100001"],
        "ordem não repete município": lambda: len({o[0] for o in ordem}) == len(ordem) == 4,
        "trava estrutural: o fonte não cita arquivo do banco": lambda: not any(p in fonte for p in proibidos),
        "trava estrutural: só duas escritas, no arquivo e na fila": lambda: all(("ARQUIVO" in l or "gravar_lote" in l or "pistas.py" in l) for l in escritas),
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    arg = lambda nome, padrao: int(sys.argv[sys.argv.index(nome) + 1]) if nome in sys.argv else padrao
    return rodar(arg("--orcamento", 1500), arg("--limite", 400))


if __name__ == "__main__":
    sys.exit(main())
