#!/usr/bin/env python3
"""Gatilho de reverificação por marco federal, handover ponto cego saúde (18/09/2026, §3.5) —
o item de menor prioridade do handover, mas o que evita a PRÓXIMA defasagem de duas semanas
(o caso Bahia só foi notado porque a imprensa noticiou; nada no sistema perguntava "algo
mudou desde a última verificação?" depois de um marco federal como aquele).

MECANISMO: o Ministério da Saúde publica notícias em gov.br/saude (Plone) sob
/pt-br/assuntos/noticias-ms/<ano>/<mes>/<slug> — Plone expõe RSS padrão em
"<pasta>/RSS" para qualquer pasta do site. Este coletor lê esse feed, filtra por palavras-chave
de marco relevante (assembleia do Conass, coletiva de imprensa, oficina, El Niño, clima e
saúde), e compara contra data/marcos_federais_saude.json (marcos já processados, por URL).

Quando um marco NOVO é achado: todas as 27 UFs de data/saude_uf.json recebem
`requer_reverificacao: true` e `motivo_reverificacao: "marco federal de dd/mm — <título>"`.
Esses dois campos nunca alimentam o índice nem aparecem em nenhum artefato público — são
sinalizadores internos, lidos direto de saude_uf.json (arquivo de dados do pipeline, não
servido ao público), até a rotina semanal (Pista A) confirmar ou atualizar cada UF e limpar
a flag manualmente. Verificado por self-test que gerar_monitor_saude.py (e qualquer outro
gerador de artefato público) nunca propaga esses dois campos.

Uso: python3 detectar_marcos_federais.py    (rotina real)
     python3 detectar_marcos_federais.py --self-test   (offline)
"""
import json
import re
import sys
import time
import urllib.request

from coletores_base import RAIZ, UA, ler, gravar

FEED_URL = "https://www.gov.br/saude/pt-br/assuntos/noticias-ms/RSS"
PALAVRAS_MARCO = [
    "el niño", "el nino", "conass", "coletiva", "assembleia", "oficina",
    "clima e saúde", "emergências climáticas", "adaptasus",
]


def _get(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001 — tolerante por design (ver docstring)
        print(f"[aviso] falha ao consultar o feed do MS: {e}")
        return None


def extrair_itens_rss(xml):
    """Extrai (titulo, link, data) de um feed RSS — mesmo parser tolerante por regex já
    usado em monitorar_imprensa_saude.py, reaproveitado aqui em vez de reescrito."""
    itens = []
    for bloco in re.findall(r"<item>(.*?)</item>", xml or "", re.S):
        titulo = re.search(r"<title>(.*?)</title>", bloco, re.S)
        link = re.search(r"<link>(.*?)</link>", bloco, re.S)
        data = re.search(r"<pubDate>(.*?)</pubDate>", bloco, re.S)
        if not (titulo and link):
            continue
        t = re.sub(r"<!\[CDATA\[|\]\]>", "", titulo.group(1)).strip()
        itens.append({"titulo": t, "url": link.group(1).strip(),
                       "data_publicacao": (data.group(1).strip() if data else "")})
    return itens


def eh_marco_relevante(item: dict) -> bool:
    t = item["titulo"].lower()
    return any(p in t for p in PALAVRAS_MARCO)


def carregar_conhecidos():
    return ler("marcos_federais_saude.json", {"_governanca": (
        "Marcos federais já processados pelo gatilho de reverificação (handover ponto cego "
        "saúde, §3.5). Cada URL aqui já disparou (ou foi semeada como histórica, sem disparar) "
        "requer_reverificacao nas 27 UFs — não processar de novo."), "marcos": []})


def marcar_todas_ufs(motivo: str):
    """Marca as 27 UFs com requer_reverificacao — nunca decide qual UF precisa, todas
    recebem a flag por igual; a rotina semanal (humana) é quem confirma ou limpa cada uma."""
    su = ler("saude_uf.json", {})
    for uf, registro in su.get("uf", {}).items():
        registro["requer_reverificacao"] = True
        registro["motivo_reverificacao"] = motivo
    gravar("saude_uf.json", su)
    return len(su.get("uf", {}))


def rodar(semear_sem_marcar: list[str] | None = None) -> int:
    """`semear_sem_marcar`: URLs de marcos já conhecidos (achados nesta mesma sessão de
    trabalho, já reverificados manualmente) — entram como processados SEM marcar as UFs,
    para o gatilho não repetir um trabalho que a resserragem manual de 18/09/2026 já fez."""
    conhecidos = carregar_conhecidos()
    urls_conhecidas = {m["url"] for m in conhecidos["marcos"]}

    if semear_sem_marcar:
        novos_semeados = 0
        for url in semear_sem_marcar:
            if url not in urls_conhecidas:
                conhecidos["marcos"].append({"url": url, "processado_em": time.strftime("%Y-%m-%d"),
                                              "marcou_ufs": False, "motivo": "semeado — já reverificado manualmente em 18/09/2026"})
                urls_conhecidas.add(url)
                novos_semeados += 1
        if novos_semeados:
            gravar("marcos_federais_saude.json", conhecidos)
            print(f"{novos_semeados} marco(s) semeado(s) sem marcar UFs (já reverificados manualmente).")
        return 0

    xml = _get(FEED_URL)
    if not xml:
        print("Feed do MS indisponível nesta execução — nada processado (tolerante a falha).")
        return 0

    itens = [i for i in extrair_itens_rss(xml) if eh_marco_relevante(i)]
    novos = [i for i in itens if i["url"] not in urls_conhecidas]

    if not novos:
        print(f"Nenhum marco novo (feed com {len(itens)} item(ns) relevante(s), todos já conhecidos).")
        return 0

    for item in novos:
        data_curta = re.search(r"(\d{1,2}) (\w+) (\d{4})", item["data_publicacao"] or "")
        motivo = f"marco federal — {item['titulo'][:120]}"
        n = marcar_todas_ufs(motivo)
        conhecidos["marcos"].append({"url": item["url"], "titulo": item["titulo"],
                                      "processado_em": time.strftime("%Y-%m-%d"),
                                      "marcou_ufs": True, "motivo": motivo})
        print(f"[MARCO NOVO] {item['titulo'][:100]} — {n} UFs marcadas com requer_reverificacao=true")

    gravar("marcos_federais_saude.json", conhecidos)
    return 0


def self_test() -> int:
    falhas = []
    def checar(nome, cond):
        if not cond:
            falhas.append(nome)

    fx = """<rss><channel>
    <item><title><![CDATA[Ministério da Saúde apresenta plano na 7ª Assembleia do Conass]]></title>
    <link>https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/agosto/exemplo</link>
    <pubDate>27 Aug 2026</pubDate></item>
    <item><title><![CDATA[Ministério lança campanha de vacinação infantil]]></title>
    <link>https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/agosto/vacinacao</link>
    <pubDate>20 Aug 2026</pubDate></item>
    </channel></rss>"""
    itens = extrair_itens_rss(fx)
    checar("parser RSS extrai os 2 itens do fixture", len(itens) == 2)
    checar("filtro de marco: Conass é relevante", eh_marco_relevante(itens[0]))
    checar("filtro de marco: vacinação infantil não é relevante", not eh_marco_relevante(itens[1]))

    fonte = (RAIZ / "detectar_marcos_federais.py").read_text(encoding="utf-8")
    for proibido in ["monitor_saude.json", "indice.json"]:
        for _ in re.finditer(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
            falhas.append(f"TRAVA VIOLADA: escreve em {proibido}")
        for _ in re.finditer(r'gravar\("' + re.escape(proibido), fonte):
            falhas.append(f"TRAVA VIOLADA: gravar() em {proibido}")
    checar("garantia estrutural: nunca escreve em artefato público (índice/monitor)", not any("VIOLADA" in f for f in falhas))

    gms = (RAIZ / "gerar_monitor_saude.py").read_text(encoding="utf-8")
    checar("gerar_monitor_saude.py nunca propaga requer_reverificacao ao output público",
           "requer_reverificacao" not in gms and "motivo_reverificacao" not in gms)

    if falhas:
        print(f"✗ {len(falhas)} falha(s):")
        for f in falhas:
            print("  -", f)
        return 1
    print("✓ AUTOTESTE OK — parser, filtro de relevância e trava estrutural (nunca vaza ao público).")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(rodar())
