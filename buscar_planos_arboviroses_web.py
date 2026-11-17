#!/usr/bin/env python3
"""Planos MUNICIPAIS de arboviroses na web aberta, para os municípios que o diário oficial não cobre.

Editoria, 15/11/2026: "procure por planos municipais o máximo que conseguir encontrar". O Querido Diário
cobre poucas centenas de municípios; os demais (mais de 5 mil "não verificados" em
`data/planos_arboviroses.json`) só aparecem pela página da prefeitura ou da secretaria. Esta peça
pergunta ao metabuscador local (SearXNG da própria Action, sem chave) por município, na ordem do
coletor do diário (capitais, alvos de tribunal de contas, mais populosos e de mais casos), e entrega
os candidatos à fila `data/pistas_arboviroses.json` pela porta única, que aplica as regras do Buscador 2
(redirecionador, domínio do ente, uma pista por URL). Quem decide é `julgar_saude_municipal.py`.

TRAVAS: escreve só a fila, pela porta (`scripts/pistas.py`); toda pista nasce com
`documento_oficial_confirmado: null` e `promovivel: false`; nunca estados.json, saude_uf.json,
municipios.json, indice.json nem monitor_saude.json. Recusa da fonte (401/403/429/451) se respeita.

Uso: python3 buscar_planos_arboviroses_web.py [--limite N]   ·   --autoteste
"""
import json
import sys
import time

import coletar_planos_arboviroses as cpa
import monitorar_busca_web as mbw
from coletores_base import RAIZ, hoje_editorial, ler, rodar_autoteste

FILA = cpa.FILA
CONSULTAS = ('"{nome}" {uf} "plano de contingência" arboviroses',
             '"{nome}" {uf} "plano municipal" dengue contingência')
TERMOS = ("conting", "plano")
ASSUNTOS = ("dengue", "arbovir", "chikungunya", "zika")


def candidato(r: dict, nome: str) -> bool:
    """Resultado que nomeia o município, fala de plano e de arbovirose. Função pura, literal."""
    t = " ".join(str(r.get(k) or "") for k in ("title", "url", "content")).lower()
    return nome.lower() in t and all(any(x in t for x in g) for g in (TERMOS, ASSUNTOS))


def pistas_do_municipio(ibge: str, nome: str, uf: str, resultados: list, hoje: str) -> list:
    """Pistas no esquema da fila (a porta normaliza e recusa o resto). Função pura."""
    vistas, saida = set(), []
    for r in resultados:
        url = r.get("url")
        if not url or url in vistas or not candidato(r, nome):
            continue
        vistas.add(url)
        saida.append({"url_final": url, "tipo": "plano", "alvo": ibge, "ibge": ibge, "municipio": nome, "uf": uf,
                      "nivel": "C", "data": hoje, "titulo": str(r.get("title") or "")[:200],
                      "trecho": str(r.get("content") or "")[:500], "assunto": "arboviroses",
                      "documento_oficial_confirmado": None, "promovivel": False})
    return saida


def rodar(limite: int, web=None, gravar_lote=None) -> int:
    if gravar_lote is None:
        from scripts.pistas import gravar_lote
    web = web or mbw.web_do_metabuscador()
    if web is None:
        print("metabuscador sem resposta: nada consultado (lacuna da rodada, não ausência)")
        return 0
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    ordem = cpa.ordem_de_busca(ref, ler("populacao_censo2022.json", {}), cpa.casos_recentes(),
                               tuple((ler(cpa.ARQUIVO_ALVOS, {}) or {}).get("alvos", ())))
    hoje, novas, feitos = hoje_editorial().isoformat(), [], 0
    try:
        for ibge, nome, uf in ordem[:limite]:
            resultados = []
            for q in CONSULTAS:
                try:
                    resultados += (web(q.format(nome=nome, uf=uf)) or {}).get("results") or []
                except Exception as e:  # noqa: BLE001 — consulta que falhou é lacuna, não ausência
                    print(f"  {nome}/{uf}: consulta falhou ({type(e).__name__})")
            novas += pistas_do_municipio(ibge, nome, uf, resultados, hoje)
            feitos += 1
            if feitos % 25 == 0:
                print(f"  {feitos} município(s), {len(novas)} candidato(s)")
    except KeyboardInterrupt:
        print("prazo: gravando o que foi achado")
    r = gravar_lote(novas, origem="busca_web", nome_da_fila=FILA)
    print(f"{feitos} município(s) consultado(s) · {len(novas)} candidato(s) · porta: {r}")
    return 0


def autoteste() -> int:
    res = [{"title": "Plano Municipal de Contingência das Arboviroses 2026 - Prefeitura de Lages",
            "url": "https://www.lages.sc.gov.br/plano-arboviroses-2026.pdf", "content": "dengue, chikungunya e zika"},
           {"title": "Plano de mobilidade de Lages", "url": "https://www.lages.sc.gov.br/mobilidade.pdf", "content": ""},
           {"title": "Plano de contingência da dengue em Joinville", "url": "https://joinville.sc.gov.br/x.pdf",
            "content": "dengue"}]
    gravadas = []
    rodar(1, web=lambda q: {"results": res}, gravar_lote=lambda n, **k: gravadas.extend(n) or {"gravadas": len(n)})
    p = pistas_do_municipio("4209300", "Lages", "SC", res, "2026-11-16")
    import inspect
    fonte = inspect.getsource(sys.modules[__name__])
    return rodar_autoteste({
        "só o resultado que nomeia o município, o plano e a arbovirose vira pista":
            lambda: [x["url_final"] for x in p] == ["https://www.lages.sc.gov.br/plano-arboviroses-2026.pdf"],
        "toda pista nasce não confirmada e não promovível":
            lambda: all(x["documento_oficial_confirmado"] is None and x["promovivel"] is False for x in p),
        "a rodada entrega à porta única, sem importar o gravador de data/": lambda: isinstance(gravadas, list)
            and "gravar" not in fonte.split("from coletores_base import", 1)[1].split("\n", 1)[0],
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    return rodar(int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 300)


if __name__ == "__main__":
    sys.exit(main())
