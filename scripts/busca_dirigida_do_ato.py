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
    # 09/10/2026 (lote 2.5, A1-16 e A1-24): busca sem rota nenhuma não é busca. 3.534 de 3.939
    # registros tinham `fontes: []` — e o contador que o prazo lê (`tentativas_de_busca_dirigida`)
    # nunca era escrito, de modo que a regra "duas tentativas" estava morta. Agora só se registra o
    # que foi tentado, e cada tentativa real conta.
    if not fontes_tentadas:
        return None
    registro = {"em": hoje.isoformat(), "fontes": list(fontes_tentadas),
                "encontrou": achou_url or None}
    pista.setdefault("busca_dirigida", []).append(registro)
    pista["ultima_busca_em"] = hoje.isoformat()
    pista["tentativas_de_busca_dirigida"] = int(pista.get("tentativas_de_busca_dirigida") or 0) + 1
    return registro


def ibge_de(nome, uf, referencia=None):
    """Código IBGE por nome e UF, da referência oficial. None quando não consta — nunca inventa."""
    if not nome or not uf:
        return None
    if referencia is None:
        referencia = json.loads(
            (RAIZ / "data" / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))
    m = next((r for r in referencia
              if r.get("nome") == nome and str(r.get("uf", "")).upper() == str(uf).upper()), None)
    return str(m["codigo_ibge"]).zfill(7) if m else None


def parece_fonte_oficial(url, padroes=None) -> bool:
    """A mesma peneira da Etapa 0 — a busca dirigida não pode devolver o que o juiz recusaria."""
    if padroes is None:
        from juiz import PADROES_FONTE_PROVAVEL_OFICIAL as padroes
    u = str(url or "").lower()
    return bool(u) and any(pad in u for pad in padroes)


# 09/10/2026 (lote 2.5, A1-24): a home do portal não é o ato. Candidato precisa de caminho e de
# sinal de documento — PDF, ou termo de ato/plano no endereço ou no título do resultado.
RE_SINAL_DE_DOCUMENTO = re.compile(
    r"\.pdf\b|plano|conting|decreto|portaria|resolu|lei[-_/ ]|diario|di%c3%a1rio|diário|edicao|edição",
    re.I)


def tem_sinal_de_documento(url, titulo="") -> bool:
    from urllib.parse import urlsplit
    caminho = urlsplit(str(url or "")).path.strip("/")
    if not caminho:
        return False
    return bool(RE_SINAL_DE_DOCUMENTO.search(f"{url} {titulo or ''}"))


def candidato_dos_resultados(resultados, padroes=None):
    """A primeira URL de fonte provável oficial COM sinal de documento. Resultado de busca não é
    prova: é endereço — e a raiz de um portal não é endereço de ato."""
    for r in resultados or []:
        url = r.get("url") if isinstance(r, dict) else r
        titulo = (r.get("titulo") or r.get("title") or "") if isinstance(r, dict) else ""
        if parece_fonte_oficial(url, padroes) and tem_sinal_de_documento(url, titulo):
            return url
    return None


def procurar(ident: dict, consultar_qd=None, buscar_web=None, esperar=None) -> tuple:
    """(url_candidata, fontes_tentadas). Três rotas, na ordem, parando na primeira que achar.

    As funções de rede entram por parâmetro: é o que permite ao autoteste exercitar as três rotas
    sem tocar a rede e sem instância de metabuscador. `esperar` é o ritmo da rodada — o mesmo de
    `monitorar_busca_web`, porque a busca dirigida some no mesmo limite de taxa que qualquer outra.
    """
    tentadas = []

    # Rota 1 — Querido Diário, pelo território. Só quando o código IBGE é conhecido: sem ele não há
    # território a consultar, e chutar o código consultaria o diário de outro município.
    ibge = ident.get("ibge") or ibge_de(ident.get("municipio"), ident.get("uf"))
    if ibge and consultar_qd:
        tentadas.append("querido_diario")
        if esperar:
            esperar()
        url = consultar_qd(ibge, ident)
        if url:
            return url, tentadas

    consultas = consultas_dirigidas(ident)
    if not consultas or not buscar_web:
        return None, tentadas

    # Rota 2 — sítio oficial, restringindo a busca ao domínio público. `site:gov.br` é o que se pode
    # afirmar sem conhecer o domínio do município: a lista de domínios oficiais cobre os estados,
    # não os 5.571 municípios, e inventar `prefeitura<nome>.<uf>.gov.br` erraria na maioria.
    tentadas.append("sitio_oficial")
    if esperar:
        esperar()
    url = candidato_dos_resultados(buscar_web(f"site:gov.br {consultas[0]}"))
    if url:
        return url, tentadas

    # Rota 3 — cascata aberta, string por string, parando na primeira que devolver fonte oficial.
    tentadas.append("busca_web")
    for consulta in consultas:
        if esperar:
            esperar()
        url = candidato_dos_resultados(buscar_web(consulta))
        if url:
            return url, tentadas
    return None, tentadas


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

    # As três rotas, sem rede: as funções entram por parâmetro.
    REF = [{"nome": "Bonito", "uf": "MS", "codigo_ibge": 5002209, "lat": 0, "lon": 0}]
    casos.append(("acha o código IBGE por nome e UF", ibge_de("Bonito", "MS", REF) == "5002209"))
    casos.append(("município fora da referência não inventa código",
                  ibge_de("Cidade Que Não Existe", "MS", REF) is None))
    casos.append(("sem UF não há código", ibge_de("Bonito", None, REF) is None))

    PAD = (".gov.br", "queridodiario.ok.org.br")
    casos.append(("fonte oficial é reconhecida",
                  parece_fonte_oficial("https://bonito.ms.gov.br/d.pdf", PAD)))
    casos.append(("portal de notícia não é fonte oficial",
                  not parece_fonte_oficial("https://g1.globo.com/x", PAD)))
    casos.append(("rede social não é fonte oficial",
                  not parece_fonte_oficial("https://www.instagram.com/p/abc", PAD)))
    casos.append(("url vazia não passa", not parece_fonte_oficial(None, PAD)))
    casos.append(("dos resultados sai a primeira fonte oficial, não a primeira qualquer",
                  candidato_dos_resultados([{"url": "https://g1.globo.com/a"},
                                            {"url": "https://bonito.ms.gov.br/b.pdf"}], PAD)
                  == "https://bonito.ms.gov.br/b.pdf"))
    casos.append(("resultado sem nenhuma fonte oficial devolve None",
                  candidato_dos_resultados([{"url": "https://g1.globo.com/a"}], PAD) is None))
    # 09/10/2026 (lote 2.5, A1-24)
    casos.append(("a home do portal não é candidato",
                  candidato_dos_resultados([{"url": "https://x.sp.gov.br/"}], PAD) is None))
    casos.append(("página oficial sem sinal de documento não é candidato",
                  candidato_dos_resultados([{"url": "https://x.sp.gov.br/noticias/festa"}], PAD) is None))
    casos.append(("plano no endereço é candidato",
                  candidato_dos_resultados([{"url": "https://x.sp.gov.br/defesa/plano-2026"}], PAD)
                  == "https://x.sp.gov.br/defesa/plano-2026"))
    sem_rota = {}
    casos.append(("busca sem rota nenhuma não é registrada",
                  registrar_busca(sem_rota, [], d(2026, 10, 9)) is None and "busca_dirigida" not in sem_rota))
    conta = {}
    registrar_busca(conta, ["sitio_oficial"], d(2026, 10, 8))
    registrar_busca(conta, ["busca_web"], d(2026, 10, 9))
    casos.append(("cada busca real conta no contador do prazo",
                  conta.get("tentativas_de_busca_dirigida") == 2))

    ident = {"municipio": "Bonito", "uf": "MS", "ibge": "5002209", "tipo": "decreto",
             "numero": "1.482", "nome_do_plano": "Plano de Contingência"}
    url, fontes = procurar(ident, consultar_qd=lambda i, d: "https://bonito.ms.gov.br/qd.pdf",
                           buscar_web=lambda q: [])
    casos.append(("rota 1 acha e para ali", url.endswith("qd.pdf") and fontes == ["querido_diario"]))

    url, fontes = procurar(ident, consultar_qd=lambda i, d: None,
                           buscar_web=lambda q: ([{"url": "https://bonito.ms.gov.br/s.pdf"}]
                                                 if q.startswith("site:") else []))
    casos.append(("rota 2 entra quando a 1 não acha",
                  url.endswith("s.pdf") and fontes == ["querido_diario", "sitio_oficial"]))

    vistas = []
    def _web(q):
        vistas.append(q)
        return [{"url": "https://bonito.ms.gov.br/w.pdf"}] if not q.startswith("site:") else []
    url, fontes = procurar(ident, consultar_qd=lambda i, d: None, buscar_web=_web)
    casos.append(("rota 3 entra por último",
                  url.endswith("w.pdf") and fontes[-1] == "busca_web"))
    casos.append(("a rota 3 usa a consulta mais específica primeiro",
                  vistas[-1].startswith('"Bonito" MS "decreto')))

    url, fontes = procurar(ident, consultar_qd=lambda i, d: None, buscar_web=lambda q: [])
    casos.append(("nada achado devolve None e as três rotas tentadas",
                  url is None and fontes == ["querido_diario", "sitio_oficial", "busca_web"]))

    url, fontes = procurar({"municipio": "Cidade Que Não Existe", "uf": "ZZ", "ibge": None,
                            "nome_do_plano": "Plano de Contingência"},
                           consultar_qd=lambda i, d: "x", buscar_web=lambda q: [])
    casos.append(("município fora da referência: a rota do diário não é tentada",
                  "querido_diario" not in fontes))

    ritmo = []
    procurar(ident, consultar_qd=lambda i, d: None, buscar_web=lambda q: [],
             esperar=lambda: ritmo.append(1))
    casos.append(("toda consulta passa pelo ritmo da rodada", len(ritmo) >= 3))

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
