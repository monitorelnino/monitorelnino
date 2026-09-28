#!/usr/bin/env python3
"""Busca dirigida do documento primário, antes de recusar por Etapa 0.

Bloco das 17:20 de 28/09/2026 (decisão da central). Na primeira passada real do juiz, **176 de
250** recusas foram `sem_documento_primario`: a pista aponta a notícia, e a notícia não é o ato.
Dos 171 com URL, 34 eram Instagram, 4 Facebook, o resto portais de imprensa. O juiz está certo em
recusar — o que faltava era **procurar o ato** antes de encerrar.

AS TRÊS ROTAS, NESTA ORDEM
--------------------------
1. **Querido Diário**, pelo território e pelo número/data do ato extraídos da pista.
2. **Sítio oficial do município**, pelos domínios já conhecidos (`data/dominios_oficiais.json` e os
   padrões de fonte provável oficial), procurando o título do ato.
3. **Cascata da busca web**, com string específica do ato — `"{município}" "{tipo} nº {número}"` e
   `"{município}" "{nome do plano}"` —, sob o **mesmo ritmo e o mesmo disjuntor** da rodada.

Achou → o juiz segue das etapas 1 a 7 sobre o documento encontrado. Não achou → a recusa fica, com
`busca_dirigida` dizendo quais fontes foram tentadas e quando, e a pista entra na fila de
reprocessamento que o noturno revisita a cada 7 dias: **o ato pode ser publicado depois da
notícia**, e é justamente esse o caso que uma recusa definitiva perderia.

O QUE ESTE ARQUIVO NÃO FAZ
--------------------------
Não promove, não classifica, não decide categoria e não escreve no banco. Ele devolve candidato a
documento primário; quem julga é o juiz, com as mesmas etapas de sempre.

USO
  python3 scripts/busca_dirigida_do_ato.py --autoteste
  python3 scripts/busca_dirigida_do_ato.py --relatorio        # o que seria procurado, sem rede
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

FILA = RAIZ / "data" / "fila_reprocessamento.json"
DIAS_ENTRE_REVISITAS = 7

# Tipos de ato que valem como documento primário, na forma em que aparecem numa notícia.
RE_ATO = re.compile(
    r"\b(decreto|portaria|lei(?:\s+complementar)?|resolu[çc][ãa]o|instru[çc][ãa]o\s+normativa)\b"
    r"[^\n\d]{0,30}?(?:n[ºo°.]?\s*)?([\d][\d.\-/]{0,12}\d|\d)", re.I)
RE_DATA = re.compile(r"\b([0-3]?\d)[/\-\s]?(?:de\s+)?([0-1]?\d|[a-zç]{4,9})[/\-\s]?(?:de\s+)?(20\d\2)\b", re.I)
RE_NOME_DO_PLANO = re.compile(
    r"(plano\s+(?:municipal\s+|estadual\s+)?(?:de\s+)?"
    r"(?:conting[êe]ncia|a[çc][ãa]o|enfrentamento|prote[çc][ãa]o\s+e\s+defesa\s+civil)"
    # 28/09/2026: o rabo era de até quatro palavras e produzia consulta que não casa nada —
    # "Plano de contingência preventivo estruturado pela Secretaria" é frase de jornalista,
    # não nome de ato. Duas palavras bastam para distinguir "Plano de Contingência Municipal"
    # de "Plano de Contingência", e a precisão vem do nome do município entre aspas.
    r"(?:\s+(?!preventivo|estruturado|elaborado|apresentado|criado)[a-zà-ú]+){0,2})", re.I)


def identificadores(pista: dict) -> dict:
    """O que a própria pista já diz sobre o ato: tipo e número, nome do plano, território.

    Sem inventar nada: o que não estiver escrito volta como None. Identificador ausente não é
    problema — ele apenas tira uma das rotas, e as outras seguem."""
    texto = " ".join(str(pista.get(k) or "") for k in ("titulo", "trecho", "query", "documento"))
    ato = RE_ATO.search(texto)
    plano = RE_NOME_DO_PLANO.search(texto)
    return {
        "tipo": ato.group(1).lower() if ato else None,
        "numero": ato.group(2) if ato else None,
        "nome_do_plano": " ".join(plano.group(1).split()) if plano else None,
        "municipio": pista.get("municipio") or _municipio_do_alvo(pista.get("alvo")),
        "uf": pista.get("uf") or _uf_do_alvo(pista.get("alvo")),
        "ibge": pista.get("ibge"),
        "data_publicacao": pista.get("data_publicacao") or pista.get("data"),
    }


def _partes_do_alvo(alvo):
    return [x.strip() for x in str(alvo or "").split("/") if x.strip()]


def _municipio_do_alvo(alvo):
    p = _partes_do_alvo(alvo)
    return p[-2] if len(p) >= 2 and len(p[-1]) == 2 and p[-1].isalpha() else None


def _uf_do_alvo(alvo):
    p = _partes_do_alvo(alvo)
    return p[-1].upper() if p and len(p[-1]) == 2 and p[-1].isalpha() else None


def consultas_dirigidas(ident: dict) -> list:
    """As strings da rota 3, na ordem de especificidade. Lista vazia quando não há o que procurar.

    Específico primeiro: número de ato é a string que separa um documento de mil notícias sobre
    ele. O nome do plano vem depois, porque casa com matéria jornalística com facilidade."""
    mun, uf = ident.get("municipio"), ident.get("uf")
    if not mun:
        return []
    lugar = f'"{mun}"' + (f" {uf}" if uf else "")
    consultas = []
    if ident.get("tipo") and ident.get("numero"):
        consultas.append(f'{lugar} "{ident["tipo"]} nº {ident["numero"]}"')
    if ident.get("nome_do_plano"):
        consultas.append(f'{lugar} "{ident["nome_do_plano"]}"')
    return consultas


def deve_revisitar(entrada: dict, hoje) -> bool:
    """A fila de reprocessamento devolve a pista a cada 7 dias — o ato pode sair depois da notícia."""
    ultima = str(entrada.get("ultima_busca_em") or "")
    if not ultima:
        return True
    import datetime
    try:
        d = datetime.date.fromisoformat(ultima[:10])
    except ValueError:
        return True
    return (hoje - d).days >= DIAS_ENTRE_REVISITAS


def registrar_busca(pista: dict, fontes_tentadas: list, hoje, achou_url=None) -> dict:
    """Escreve na pista o que foi tentado. Recusa que não diz onde procurou não é conferível."""
    registro = {"em": hoje.isoformat(), "fontes": list(fontes_tentadas),
                "encontrou": achou_url or None}
    pista.setdefault("busca_dirigida", []).append(registro)
    pista["ultima_busca_em"] = hoje.isoformat()
    return registro


def autoteste() -> int:
    import datetime
    casos = []
    d = datetime.date

    p = {"titulo": "Prefeitura publica Decreto nº 1.482 que institui o Plano de Contingência",
         "alvo": "D-municipio-prioritario/Bonito/MS", "data_publicacao": "14/07/2026"}
    i = identificadores(p)
    casos.append(("extrai tipo e número do ato", (i["tipo"], i["numero"]) == ("decreto", "1.482")))
    casos.append(("extrai o nome do plano", i["nome_do_plano"].lower().startswith("plano de conting")))
    casos.append(("extrai município e UF do alvo", (i["municipio"], i["uf"]) == ("Bonito", "MS")))

    vazio = identificadores({"titulo": "Chuva alaga bairro na capital"})
    casos.append(("sem ato no texto, não inventa número",
                  vazio["tipo"] is None and vazio["numero"] is None))
    casos.append(("sem alvo, não inventa município", vazio["municipio"] is None))

    c = consultas_dirigidas(i)
    casos.append(("a consulta mais específica é a do número do ato",
                  c[0] == '"Bonito" MS "decreto nº 1.482"'))
    casos.append(("o nome do plano vira a segunda consulta", "Plano de Contingência" in c[1]))
    casos.append(("sem município não há consulta dirigida", consultas_dirigidas(vazio) == []))
    casos.append(("só com município, sem ato nem plano, não há o que procurar",
                  consultas_dirigidas({"municipio": "Bonito", "uf": "MS"}) == []))

    casos.append(("pista nunca buscada é revisitada", deve_revisitar({}, d(2026, 9, 28))))
    casos.append(("pista buscada ontem NÃO é revisitada",
                  not deve_revisitar({"ultima_busca_em": "2026-09-27"}, d(2026, 9, 28))))
    casos.append(("pista buscada há 7 dias é revisitada",
                  deve_revisitar({"ultima_busca_em": "2026-09-21"}, d(2026, 9, 28))))
    casos.append(("data ilegível não trava a fila",
                  deve_revisitar({"ultima_busca_em": "ontem"}, d(2026, 9, 28))))

    alvo = {}
    r = registrar_busca(alvo, ["querido_diario", "sitio_oficial"], d(2026, 9, 28))
    casos.append(("a busca registra as fontes tentadas", r["fontes"] == ["querido_diario", "sitio_oficial"]))
    casos.append(("busca sem achado registra encontrou=None", r["encontrou"] is None))
    registrar_busca(alvo, ["busca_web"], d(2026, 10, 5), achou_url="https://x.gov.br/d.pdf")
    casos.append(("o histórico de buscas cresce, não substitui", len(alvo["busca_dirigida"]) == 2))
    casos.append(("o achado fica registrado com a URL",
                  alvo["busca_dirigida"][-1]["encontrou"].endswith("d.pdf")))
    casos.append(("a data da última busca acompanha", alvo["ultima_busca_em"] == "2026-10-05"))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def relatorio() -> int:
    """O que seria procurado, sobre as recusas já gravadas. Não toca a rede."""
    import collections
    reg = json.loads((RAIZ / "data" / "promocoes_automaticas.json").read_text(encoding="utf-8"))
    fila = {p["id"]: p for p in json.loads(
        (RAIZ / "data" / "pistas_imprensa.json").read_text(encoding="utf-8")).get("pistas", [])
        if p.get("id")}
    alvo = [v for v in reg.get("decisoes", [])
            if v.get("motivo") in ("sem_documento_primario", "citacao_incompleta")
            and not v.get("superada_por")]
    c = collections.Counter()
    exemplos = []
    for v in alvo:
        ident = identificadores({**fila.get(v.get("pista_id"), {}),
                                 "municipio": v.get("municipio"), "uf": v.get("uf")})
        consultas = consultas_dirigidas(ident)
        c["com_numero_de_ato" if ident["numero"] else "sem_numero_de_ato"] += 1
        c["com_nome_de_plano" if ident["nome_do_plano"] else "sem_nome_de_plano"] += 1
        c["com_consulta_dirigida" if consultas else "sem_consulta_dirigida"] += 1
        if consultas and len(exemplos) < 5:
            exemplos.append((v.get("municipio"), v.get("uf"), consultas[0]))
    print(f"{len(alvo)} recusa(s) de Etapa 0/citação elegíveis à busca dirigida")
    for k, n in sorted(c.items()):
        print(f"  {k}: {n}")
    for m, uf, q in exemplos:
        print(f"  exemplo: {m}/{uf} -> {q}")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--relatorio" in sys.argv:
        return relatorio()
    print(__doc__.strip().splitlines()[0])
    print("use --autoteste ou --relatorio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
