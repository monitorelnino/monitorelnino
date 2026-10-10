#!/usr/bin/env python3
"""
medir_revocacao_das_consultas.py
================================
Mede a revocação de cada string do conjunto de consultas da camada 4, para que a adoção do
conjunto mínimo seja decidida por medição e não por intuição.

Handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`, PR 1 item 4: "Rodar as 8 strings
sobre os 30 municípios da amostra manual (auditoria do funil, item D) e sobre 30 municípios com
plano já registrado; reportar revocação por string; adotar o conjunto mínimo que recupere o
máximo."

Duas populações, com verdades diferentes:

  **registrados** — 30 municípios sorteados entre os que já têm `plano` em `municipios.json`.
  A verdade aqui é forte: o documento existe e está preservado. Se uma string não recupera o
  município, ela perdeu um caso conhecido. É desta população que sai a revocação por string.

  **amostra_manual** — os 30 municípios da amostra do item D (semente 42). A verdade depende de
  leitura humana, que ainda não aconteceu. Aqui o script mede apenas o que cada string TROUXE
  (resultado bruto e candidato aprovado pela peneira), sem chamar isso de revocação. Vira
  revocação quando a coluna humana do item D estiver preenchida.

O script precisa do SearXNG de pé (`http://127.0.0.1:8080`), que é efêmero: sobe dentro do job
da Action. Sem ele, o script diz que não mediu — nunca inventa número.

Saída: `notas/preprint/funil/REVOCACAO_CONSULTAS_<data>.md` no repositório privado quando o
caminho existir; sempre imprime a tabela na saída padrão.

USO
  python3 scripts/medir_revocacao_das_consultas.py --autoteste
  python3 scripts/medir_revocacao_das_consultas.py --n 30
  python3 scripts/medir_revocacao_das_consultas.py --n 30 --saida /caminho/REVOCACAO.md
"""
import json
import pathlib
import random
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

SEMENTE = 42   # a mesma do item D, para que as duas medições falem da mesma amostra
ESPACO_ENTRE_CONSULTAS = 5.0   # PR 1c item 6: instância dedicada, sem pressa — 5 s entre consultas
ALVO_DE_REVOCACAO = 0.95       # conjunto mínimo aceitável: recupera >= 95% do que o leque recupera


def sortear_registrados(municipios: list, n: int, semente: int = SEMENTE) -> list:
    """Os municípios com plano registrado, sorteados de forma reprodutível.

    Ordena por código IBGE ANTES de sortear: a ordem do arquivo muda a cada rodada, e sem a
    ordenação a mesma semente devolveria amostras diferentes em dias diferentes."""
    com_plano = sorted((m for m in municipios if m.get("categoria") == "plano"),
                       key=lambda m: str(m.get("codigo_ibge") or m.get("ibge") or ""))
    r = random.Random(semente)
    return r.sample(com_plano, min(n, len(com_plano)))


def medir(municipios: list, buscar, relevante, consultas_de, pausa=None) -> dict:
    """Roda cada string sobre cada município e conta o que ela recuperou.

    `buscar(query)` devolve o dicionário do SearXNG ou levanta — a injeção existe para que o
    autoteste rode sem rede. Devolve contagens por id de string e o total de municípios em que
    ALGUMA string recuperou candidato (revocação do conjunto)."""
    por_string = {}
    recuperados_por_alguma = 0
    sem_resposta = 0
    for m in municipios:
        nome = m.get("nome") or m.get("municipio")
        uf = m.get("uf")
        achou_alguma = False
        brutos_no_municipio = 0
        for ident, query in consultas_de(nome, uf):
            alvo = por_string.setdefault(ident, {"brutos": 0, "candidatos": 0, "municipios_com_candidato": 0,
                                                 "consultas": 0, "falhas": 0})
            alvo["consultas"] += 1
            if pausa:
                pausa(ESPACO_ENTRE_CONSULTAS)
            try:
                dados = buscar(query)
            except Exception:  # noqa: BLE001 — falha de uma string não invalida as outras
                alvo["falhas"] += 1
                continue
            crus = dados.get("results") or []
            brutos_no_municipio += len(crus)
            alvo["brutos"] += len(crus)
            candidatos = [r for r in crus if relevante(r, nome)]
            alvo["candidatos"] += len(candidatos)
            if candidatos:
                alvo["municipios_com_candidato"] += 1
                achou_alguma = True
        if achou_alguma:
            recuperados_por_alguma += 1
        elif brutos_no_municipio == 0:
            sem_resposta += 1
    return {"n_municipios": len(municipios), "por_string": por_string,
            "municipios_recuperados_pelo_conjunto": recuperados_por_alguma,
            "municipios_sem_resposta_do_motor": sem_resposta}


def tabela(resultado: dict, titulo: str) -> str:
    n = resultado["n_municipios"] or 1
    linhas = [f"### {titulo}", "",
              f"{resultado['n_municipios']} município(s); o conjunto inteiro recuperou candidato em "
              f"{resultado['municipios_recuperados_pelo_conjunto']} "
              f"({100 * resultado['municipios_recuperados_pelo_conjunto'] / n:.0f}%); "
              f"{resultado['municipios_sem_resposta_do_motor']} sem nenhuma resposta do motor.", "",
              "| string | municípios com candidato | revocação | resultados brutos | candidatos | falhas |",
              "|---|---:|---:|---:|---:|---:|"]
    ordenado = sorted(resultado["por_string"].items(),
                      key=lambda kv: -kv[1]["municipios_com_candidato"])
    for ident, c in ordenado:
        linhas.append(f"| `{ident}` | {c['municipios_com_candidato']} | "
                      f"{100 * c['municipios_com_candidato'] / n:.0f}% | {c['brutos']} | "
                      f"{c['candidatos']} | {c['falhas']} |")
    return "\n".join(linhas)


def autoteste() -> int:
    """Offline: motor de mentira, verdade conhecida por construção."""
    from monitorar_busca_web import consultas_de_medicao as consultas_de, relevante
    casos = []

    municipios = [{"nome": "Bonito", "uf": "MS", "codigo_ibge": "5002209", "categoria": "plano"},
                  {"nome": "Cuiabá", "uf": "MT", "codigo_ibge": "5103403", "categoria": "plano"}]

    # motor que só responde à string do PLANCON, e só para Bonito
    def buscar_parcial(query):
        if "PLANCON" in query and "Bonito" in query:
            return {"results": [{"title": "PLANCON Bonito 2026", "url": "https://bonito.ms.gov.br/plancon",
                                 "content": "Plano de Contingência de Bonito"}]}
        return {"results": []}

    r = medir(municipios, buscar_parcial, relevante, consultas_de)
    casos.append(("conta município recuperado pelo conjunto", r["municipios_recuperados_pelo_conjunto"] == 1))
    casos.append(("atribui o achado à string certa",
                  r["por_string"]["plancon_sigla"]["municipios_com_candidato"] == 1))
    casos.append(("string que não achou fica com zero",
                  r["por_string"]["periodo_chuvoso"]["municipios_com_candidato"] == 0))
    casos.append(("município sem nenhuma resposta é contado à parte",
                  r["por_string"]["plancon_sigla"]["consultas"] == 2 and r["municipios_sem_resposta_do_motor"] == 1))

    # motor que levanta: falha por string, não invalida a medição
    def buscar_quebrado(query):
        raise ConnectionError("instância não subiu")

    r2 = medir(municipios, buscar_quebrado, relevante, consultas_de)
    casos.append(("falha de rede é contada como falha, não como ausência",
                  all(c["falhas"] == 2 and c["brutos"] == 0 for c in r2["por_string"].values())))
    casos.append(("nenhum município recuperado quando o motor está fora",
                  r2["municipios_recuperados_pelo_conjunto"] == 0))

    # sorteio reprodutível e indiferente à ordem do arquivo
    base = [{"codigo_ibge": f"{i:07d}", "categoria": "plano", "nome": f"M{i}", "uf": "SP"} for i in range(1, 60)]
    a = [m["codigo_ibge"] for m in sortear_registrados(base, 10)]
    b = [m["codigo_ibge"] for m in sortear_registrados(list(reversed(base)), 10)]
    casos.append(("sorteio reprodutível e indiferente à ordem do arquivo", a == b))
    casos.append(("sorteio só pega quem tem plano",
                  all(m["categoria"] == "plano" for m in sortear_registrados(
                      base + [{"codigo_ibge": "9999999", "categoria": "decreto", "nome": "X", "uf": "SP"}], 60))))

    # a tabela não inventa linha
    texto = tabela(r, "teste")
    casos.append(("a tabela traz uma linha por string", texto.count("| `") == len(r["por_string"])))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import ler, hoje_editorial
    # 27/09/2026 (PR 1c item 6): a medição usa o LEQUE COMPLETO, que saiu da rodada. A rodada roda
    # três strings em cascata; aqui rodam as nove, com 5 s entre consultas, em job próprio e
    # instância dedicada — é isso que torna a medição possível sem queimar o limite de taxa.
    from monitorar_busca_web import buscar_searxng, consultas_de_medicao as consultas_de, relevante

    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 30

    # o motor está de pé? uma consulta de prova, antes de qualquer medição
    try:
        buscar_searxng("teste", timeout=10)
    except Exception as e:  # noqa: BLE001
        print(f"✗ SearXNG não respondeu ({type(e).__name__}): a medição NÃO foi feita.")
        print("  A instância é efêmera e sobe dentro do job da Action. Rode lá, ou suba o contêiner local.")
        return 1

    registrados = sortear_registrados((ler("municipios.json") or {}).get("municipios", []), n)
    print(f"medindo {len(registrados)} município(s) com plano registrado × {len(consultas_de('x', 'SP'))} strings")
    r_reg = medir(registrados, buscar_searxng, relevante, consultas_de, pausa=time.sleep)

    partes = [f"# Revocação por string da camada 4 · {hoje_editorial().strftime('%d/%m/%Y')}", "",
              "Medição pedida no PR 1 item 4 do handover do juiz automático. A verdade da população",
              "`registrados` é o documento já preservado; a revocação abaixo é sobre ela.", "",
              tabela(r_reg, "População: municípios com plano já registrado")]

    amostra = RAIZ.parent / "robo-registro" / "notas" / "preprint" / "funil" / "AMOSTRA_MANUAL_D.json"
    if amostra.exists():
        alvo = json.loads(amostra.read_text(encoding="utf-8")).get("municipios", [])
        print(f"medindo {len(alvo)} município(s) da amostra manual do item D")
        r_am = medir(alvo, buscar_searxng, relevante, consultas_de, pausa=time.sleep)
        partes += ["", tabela(r_am, "População: amostra manual do item D (sem coluna de gabarito ainda)"),
                   "", "A coluna de gabarito do item D ainda não foi preenchida: os números acima dizem o que cada",
                   "string TROUXE, não o que ela deixou de achar."]
    else:
        partes += ["", "A amostra do item D não foi encontrada; medida apenas a população de registrados."]

    texto = "\n".join(partes) + "\n"
    print()
    print(texto)
    if "--saida" in sys.argv:
        destino = pathlib.Path(sys.argv[sys.argv.index("--saida") + 1])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8", newline="\n")
        print(f"gravado em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
