#!/usr/bin/env python3
"""
coletar_s2id.py
===============
Reconhecimentos FEDERAIS de situação de emergência/calamidade (portarias da
SEDEC/MIDR publicadas no DOU; base S2iD), do ciclo 2026/2027.
ESTATUTO (doc de redesenho §3.2, §4): atos de RESPOSTA — peso zero, sempre.
Alimentam `data/atos_resposta.json` (camada própria, fonte "DOU" ou "S2iD"),
o livro de fontes consultadas (nível "nacional" para TODOS os municípios quando
a fonte de abrangência nacional é consultada com sucesso) e o fato binário
`decreto_reconhecido`.

Endpoints (§15 — "a verificar"):
  - S2iD (s2id.mi.gov.br): sem API pública confirmada em 02/09/2026 →
    status `a_verificar`; nada é coletado dele até a confirmação.
  - DOU (in.gov.br/consulta): busca textual por "reconhece a situação de
    emergência" no período; o resultado vem num JSON embutido no HTML.
    Parser provado por fixture (--autoteste); a primeira coleta real é da Action.

USO
  python coletar_s2id.py --autoteste
  python coletar_s2id.py --desde 2026-06-29        # coleta (precisa de rede)
"""
import html as _html, json, re, sys, urllib.parse
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            ler, gravar, rodar_autoteste, eh_suspensao_defeso, sha256)

FONTES = {
    "s2id": {"nome": "S2iD — Sistema Integrado de Informações sobre Desastres", "url": None,
             "status": "a_verificar", "nota": "sem API pública confirmada (§15)"},
    "dou": {"nome": "DOU — portarias SEDEC de reconhecimento",
            "url": "https://www.in.gov.br/consulta/-/buscar/dou?q={q}&s=do1&exactDate=personalizado&sortType=0&publishFrom={de}&publishTo={ate}",
            "status": "parser_provado_por_fixture"},
}
COBRADE_CICLO = ("1.4.1", "1.4.2", "1.3.2", "1.3.1", "1.2.1", "1.2.2", "1.2.3", "2.4.1", "2.4.2")
PADRAO_TITULO = re.compile(r"PORTARIA\s+(?:SEDEC/MIDR\s+)?N[ºo°]\s*([\d\.]+),?\s+DE\s+(\d{1,2})\s+DE\s+([A-ZÇ]+)\s+DE\s+(\d{4})", re.I)
MESES = {m: i + 1 for i, m in enumerate("janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())}
PADRAO_MUN = re.compile(r"Munic[íi]pio de ([^\-–,;\.]+?)\s*-\s*([A-Z]{2})", re.I)


def parse_dou_html(texto: str) -> list:
    """Extrai a lista de resultados do JSON embutido na página de consulta do DOU.
    Devolve dicts {titulo, url, data, conteudo}. Função pura."""
    m = re.search(r'id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"[^>]*value="([^"]*)"', texto)
    if not m:
        return []
    bruto = _html.unescape(m.group(1))
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        return []
    out = []
    for it in dados.get("jsonArray", []):
        out.append({"titulo": it.get("title", ""), "url": "https://www.in.gov.br/web/dou/-/" + it.get("urlTitle", ""),
                    "data": it.get("pubDate", ""), "conteudo": it.get("content", "")})
    return out


def extrair_reconhecimentos(resultados: list) -> list:
    """De cada portaria, extrai (número, data, município, UF). Só entra o que tem
    número E data E município — citação completa como condição de entrada (§3.3)."""
    saida = []
    for r in resultados:
        t = PADRAO_TITULO.search(r["titulo"] or "")
        if not t:
            continue
        numero, dia, mes, ano = t.groups()
        try:
            data_iso = date(int(ano), MESES[mes.lower()], int(dia)).strftime("%d/%m/%Y")
        except (KeyError, ValueError):
            continue
        for nome, uf in PADRAO_MUN.findall(r["conteudo"] or ""):
            saida.append({"portaria": f"Portaria SEDEC/MIDR nº {numero}", "data": data_iso,
                          "municipio": nome.strip(), "uf": uf.upper(), "url": r["url"]})
    return saida


def coletar(desde: str, ate: str) -> int:
    por_cod, por_nome = referencia_ibge()
    # S2iD: lacuna declarada enquanto o endpoint não for confirmado
    registrar_lacuna(FONTES["s2id"]["nome"], FONTES["s2id"]["nota"], canal="DOU", camada=1)
    q = urllib.parse.quote('"reconhece a situação de emergência"')
    de = date.fromisoformat(desde).strftime("%d-%m-%Y"); at = date.fromisoformat(ate).strftime("%d-%m-%Y")
    url = FONTES["dou"]["url"].format(q=q, de=de, ate=at)
    try:
        bruto = buscar(url)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(FONTES["dou"]["nome"], f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[url])
        return 0
    texto = bruto.decode("utf-8", "replace")
    h = preservar_evidencia(bruto, url, "html", "coletar_s2id")
    if eh_suspensao_defeso(texto) and "jsonArray" not in texto:
        registrar_lacuna(FONTES["dou"]["nome"], "página com aviso de período eleitoral", canal="DOU",
                         camada=1, strings=[url], suspensa=True, hash_evidencia=h)
        return 0
    if "jsonArray" not in texto:
        # 03/09/2026 (achado da 1ª atualização real): a página veio sem a estrutura de resultados —
        # NÃO é consulta bem-sucedida; ninguém sobe de nível por uma leitura vazia.
        registrar_lacuna(FONTES["dou"]["nome"], "página sem a estrutura de resultados (jsonArray ausente) — parser/endpoint a verificar",
                         canal="DOU", camada=1, strings=[url], hash_evidencia=h)
        return 0
    itens = extrair_reconhecimentos(parse_dou_html(texto))
    atos = ler("atos_resposta.json")
    vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    novos = 0
    for it in itens:
        cod = por_nome.get((it["municipio"], it["uf"]))
        if not cod:
            log_busca("DOU", 1, [url], "pista", resultados=f"município não casou com IBGE: {it['municipio']}/{it['uf']}",
                      uf=it["uf"], nivel="nacional", hash_evidencia=h)
            continue
        ref = por_cod[cod]
        chave = (ref["nome"], it["uf"], it["data"], "reconhecimento federal")
        if chave in vistos:
            continue
        atos["eventos"].append({"nome": ref["nome"], "uf": it["uf"], "ibge": cod, "data": it["data"],
                                "causa": "reconhecimento federal", "decreto": it["portaria"],
                                "data_reconhecimento": it["data"], "portaria": it["portaria"],
                                "fonte": "DOU (portaria SEDEC/MIDR)", "url": it["url"],
                                "lat": ref["lat"], "lon": ref["lon"], "canal": "DOU",
                                "hash_evidencia": h})
        marcar_fato_municipal(cod, "decreto_reconhecido", True)
        vistos.add(chave); novos += 1
    gravar("atos_resposta.json", atos)
    # fonte de abrangência nacional consultada com sucesso ⇒ nível "nacional" para todos
    marcar_fonte_consultada(list(por_cod), "DOU/SEDEC reconhecimentos", "nacional",
                            resultado=f"{len(itens)} reconhecimento(s) no período")
    log_busca("DOU", 1, [url], "registro" if novos else "pista", resultados=f"{len(itens)} itens, {novos} novos",
              nivel="nacional", n_resultados=len(itens), hash_evidencia=h)
    print(f"DOU: {len(itens)} reconhecimento(s) lidos, {novos} novo(s) em atos_resposta.json")
    return 0


FIXTURE_HTML = ('<input id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="hidden" value="'
                + _html.escape(json.dumps({"jsonArray": [
                    {"title": "PORTARIA SEDEC/MIDR Nº 2.659, DE 28 DE AGOSTO DE 2026", "urlTitle": "portaria-2659",
                     "pubDate": "29/08/2026", "content": "Reconhece a situação de emergência no Município de Blumenau - SC, afetado por chuvas intensas (COBRADE 1.3.2.1.4)."},
                    {"title": "AVISO DE LICITAÇÃO", "urlTitle": "x", "pubDate": "29/08/2026", "content": "nada"}]}), quote=True)
                + '"></input>')


def autoteste() -> int:
    def t1():
        r = parse_dou_html(FIXTURE_HTML); return len(r) == 2 and r[0]["url"].endswith("portaria-2659")
    def t2():
        e = extrair_reconhecimentos(parse_dou_html(FIXTURE_HTML))
        return len(e) == 1 and e[0]["municipio"] == "Blumenau" and e[0]["uf"] == "SC" and e[0]["data"] == "28/08/2026"
    def t3():  # negativo: sem número de portaria → não entra
        e = extrair_reconhecimentos([{"titulo": "PORTARIA SEM NUMERO", "url": "", "data": "", "conteudo": "Município de X - SC"}])
        return e == []
    def t4():  # negativo: HTML sem o JSON embutido → lista vazia, nunca exceção
        return parse_dou_html("<html>vazio</html>") == []
    def t5():
        return eh_suspensao_defeso("Conteúdo suspenso em razão do período eleitoral") and not eh_suspensao_defeso("normal")
    return rodar_autoteste({"parser do DOU lê o JSON embutido": t1, "extrai portaria+data+município": t2,
                            "negativo: sem número não entra": t3, "negativo: HTML sem JSON": t4,
                            "heurística de suspensão por defeso": t5})


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else "2026-06-29"
    sys.exit(coletar(desde, date.today().isoformat()))
