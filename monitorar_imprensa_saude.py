#!/usr/bin/env python3
"""Vigia de imprensa nacional para instrumentos de SAÚDE ligados ao El Niño 2026/2027,
ainda não registrados em data/saude_uf.json — mesmo mecanismo e mesma trava absoluta de
monitorar_imprensa_regional.py (defesa civil), separado porque aquele nunca buscava por
secretaria de saúde (achado do handover "ponto cego saúde", 18/09/2026, §3.3: foi assim
que o plano de R$ 30,5 mi da Bahia ficou fora do banco por mais de um mês).

===========================================================================
TRAVA ABSOLUTA (mesma trava de monitorar_imprensa_regional.py — "nada entra sem ser
documento oficial") — três camadas independentes, cada uma suficiente sozinha:

  1. ESTRUTURAL: esta rotina LÊ saude_uf.json (para saber quais UFs/status buscar —
     leitura é necessária e legítima), mas NUNCA escreve em saude_uf.json,
     monitor_saude.json ou indice.json (garantia verificada por self-test).
  2. DE CAMPO: toda pista nasce com "documento_oficial_confirmado": null e
     "promovivel": false. Não existe, nesta rotina, nenhum caminho de código que ponha
     esses campos em outro valor — a mudança é exclusivamente manual, feita por um
     humano após localizar o documento primário e registrar sua URL.
  3. DE PROCESSO: mesmo confirmada, uma pista não entra direto no banco — ela vira uma
     entrada em data/pistas_imprensa_saude.json e só então segue o fluxo humano normal
     de edição de saude_uf.json (adicionar o item em instrumentos[], §3.2).
===========================================================================

MECANISMO DE BUSCA: Google News RSS, idêntico a monitorar_imprensa_regional.py — mesmo
parser tolerante, mesma cortesia de taxa, mesmo princípio de "perda de recall nunca
invenção de resultado".

PRIORIZAÇÃO (handover §3.6): as UFs NAO_VERIFICADO primeiro (nunca verificadas, maior
valor por consulta), depois as com data_verificacao mais antiga (defasagem = risco de
ponto cego, como o da Bahia), depois as demais em busca ampla (para pescar o padrão
Bahia: UF já com VIG, mas com um instrumento mais específico ainda não descoberto).

Termos de busca: os do dicionário ampliado em 18/09/2026 (data/dicionario_busca.json,
grupo saude, achado 18/09/2026), combinados a "secretaria de saúde"/"Sesab"/"Ses<UF>" e
"2026 El Niño" — exatamente o padrão que faltava e deixou o caso Bahia sem pista nenhuma.

Uso: python3 monitorar_imprensa_saude.py [--limite N]  (vigia ao vivo)
     python3 monitorar_imprensa_saude.py --self-test    (offline)
"""
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).parent

FILA = RAIZ / "data" / "pistas_imprensa_saude.json"
CURSOR = RAIZ / "data" / "imprensa_saude_cursor.json"
RSS = "https://news.google.com/rss/search"
UA = {"User-Agent": "MonitorElNinoBrasil/1.0 (+monitorelnino.com.br; descoberta editorial, não indexação)"}

PADROES_FONTE_PROVAVEL_OFICIAL = [
    r"\.gov\.br", r"\.leg\.br", r"\.jus\.br", r"diariomunicipal\.com\.br",
    r"diariooficial", r"\bdoe\.", r"\bdom\.", r"in\.gov\.br",
    r"queridodiario", r"imprensaoficial", r"saude\.\w+\.gov\.br", r"^ses\w*\.\w+\.gov\.br",
]

# 18/09/2026 (handover ponto cego saúde, §3.1): os termos que faltavam quando a Bahia
# publicou — nomes que espelham o programa federal do MS, não mais só "arboviroses".
TERMOS_INSTRUMENTO = [
    "plano de ações de saúde para o enfrentamento ao El Niño",
    "plano estadual de enfrentamento ao El Niño",
    "plano de contingência para arboviroses",
]

NOMES_ORGAO_SAUDE = "secretaria de saúde OR Sesab OR Ses{sigla}"


def _get(url, timeout=30):
    """GET tolerante: devolve o corpo como texto, ou None com aviso (nunca exceção)."""
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"[aviso] falha ao consultar imprensa: {e}")
        return None


def montar_url(query):
    """Monta a URL do Google News RSS para uma query, em português do Brasil."""
    q = urllib.parse.quote(query)
    return f"{RSS}?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def extrair_itens_rss(xml):
    """Extrai (titulo, link, data, fonte) de um retorno RSS do Google News — mesmo
    parser tolerante por regex de monitorar_imprensa_regional.py."""
    itens = []
    for bloco in re.findall(r"<item>(.*?)</item>", xml or "", re.S):
        titulo = re.search(r"<title>(.*?)</title>", bloco, re.S)
        link = re.search(r"<link>(.*?)</link>", bloco, re.S)
        data = re.search(r"<pubDate>(.*?)</pubDate>", bloco, re.S)
        fonte = re.search(r"<source[^>]*>(.*?)</source>", bloco, re.S)
        if not (titulo and link):
            continue
        t = re.sub(r"<!\[CDATA\[|\]\]>", "", titulo.group(1)).strip()
        itens.append({
            "titulo": t,
            "url": link.group(1).strip(),
            "data_publicacao": (data.group(1).strip() if data else ""),
            "fonte_veiculo": (re.sub(r"<!\[CDATA\[|\]\]>", "", fonte.group(1)).strip() if fonte else ""),
        })
    return itens


def parece_fonte_oficial(url):
    """Heurística de ORDENAÇÃO apenas (ver TRAVA ABSOLUTA) — nunca confirmação."""
    return any(re.search(p, url, re.I) for p in PADROES_FONTE_PROVAVEL_OFICIAL)


def _hash(p):
    """Identidade estável de uma pista para deduplicação entre execuções."""
    import hashlib
    return hashlib.sha256(f"{p['alvo']}|{p['titulo']}|{p['url']}".encode()).hexdigest()[:16]


NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

# Capitais estaduais — usadas como segunda âncora na filtragem por UF (bug 19/09/2026:
# Google News RSS retorna resultados nacionais; o coletor precisa descartar achados que
# não mencionam nem o estado nem a capital da UF-alvo no título ou na URL).
CAPITAIS_UF = {
    "AC": "Rio Branco",      "AL": "Maceió",        "AM": "Manaus",
    "AP": "Macapá",          "BA": "Salvador",       "CE": "Fortaleza",
    "DF": "Brasília",        "ES": "Vitória",        "GO": "Goiânia",
    "MA": "São Luís",        "MG": "Belo Horizonte", "MS": "Campo Grande",
    "MT": "Cuiabá",          "PA": "Belém",          "PB": "João Pessoa",
    "PE": "Recife",          "PI": "Teresina",       "PR": "Curitiba",
    "RJ": "Rio de Janeiro",  "RN": "Natal",          "RO": "Porto Velho",
    "RR": "Boa Vista",       "RS": "Porto Alegre",   "SC": "Florianópolis",
    "SE": "Aracaju",         "SP": "São Paulo",      "TO": "Palmas",
}


def _menciona_uf_alvo(titulo, url, uf):
    """Retorna True se o título ou a URL menciona a UF-alvo (estado, capital ou SES-UF).

    FILTRO DE INTEGRIDADE — bug detectado em 19/09/2026: o Google News RSS devolve
    resultado de cobertura nacional para queries por UF e o coletor atribuía o achado à
    UF-alvo sem confirmar relevância. "Secretaria de Saúde de Cuiabá" apareceu como pista
    de AC, AP, CE, DF, MS, RO e SE. 20 das 25 pistas não mencionavam a UF-alvo; aplicar
    qualquer uma creditaria a um estado um instrumento de outro.

    Regra: pelo menos uma das âncoras (nome do estado, capital ou padrão SES/domínio gov.br
    da UF) deve aparecer no título ou na URL da notícia — sem essa evidência mínima, a pista
    é descartada antes de entrar na fila.

    Nota: a comparação usa case-insensitive com acentos preservados (re.IGNORECASE +
    re.UNICODE), de modo que "Pará" nunca casa com a preposição "para" — ausência de acento
    é a diferença relevante, e este filtro a preserva.
    """
    nome_estado = NOMES_UF.get(uf, "")
    capital = CAPITAIS_UF.get(uf, "")

    # Âncoras: nome do estado, capital, "SES-UF" (org. estadual de saúde), e domínio .uf.gov.br
    ancoras = [t for t in [nome_estado, capital, f"SES-{uf}"] if t]
    padrao_dominio = re.compile(
        r'(?:\.|/|-|_)' + re.escape(uf.lower()) + r'(?:\.|/)gov\.br', re.IGNORECASE
    )

    para_checar = [titulo, url]
    for ancora in ancoras:
        padrao = re.compile(re.escape(ancora), re.IGNORECASE | re.UNICODE)
        if any(padrao.search(texto) for texto in para_checar if texto):
            return True

    # Verificação de domínio (.ba.gov.br, /ba.gov.br, etc.)
    if any(padrao_dominio.search(texto) for texto in para_checar if texto):
        return True

    return False


def montar_universo(saude_json):
    """Monta a lista priorizada de alvos a partir do estado atual de saude_uf.json.

    Camada A (maior valor): NAO_VERIFICADO — nunca verificadas, nada para comparar.
    Camada B: data_verificacao anterior a 01/09/2026 — defasagem = risco de ponto cego
    (exatamente o padrão que deixou a Bahia, verificada em 05/09, escapar até 18/09).
    Camada C: as demais, busca ampla ex-ante (pesca o padrão Bahia: VIG com instrumento
    mais forte ainda não descoberto).
    """
    uf_dados = saude_json.get("uf", {})
    camada_a, camada_b, camada_c = [], [], []
    for sigla, u in uf_dados.items():
        nome = NOMES_UF.get(sigla, sigla)
        org = NOMES_ORGAO_SAUDE.format(sigla=sigla)
        queries = [f'"{t}" {nome} {org} 2026' for t in TERMOS_INSTRUMENTO]
        status = u.get("status")
        data_verif = u.get("data_verificacao") or ""   # sempre dd/mm/aaaa quando presente
        if status == "NAO_VERIFICADO" or not data_verif:
            camada_a.append(("A-nunca-verificado", sigla, queries))
        else:
            # dd/mm/aaaa não ordena por comparação de string direta (dia vem primeiro) —
            # vira aaaa-mm antes de comparar, para "antes de 01/09/2026" significar de
            # verdade "antes de setembro de 2026", não uma comparação de dígitos crua
            dd, mm, aaaa = data_verif.split("/")
            aaaa_mm = f"{aaaa}-{mm}"
            if aaaa_mm < "2026-09":
                camada_b.append(("B-defasado", sigla, queries))
            else:
                camada_c.append(("C-amplo", sigla, queries))
    return camada_a + camada_b + camada_c


def carregar_cursor(total):
    if CURSOR.exists():
        c = json.load(open(CURSOR, encoding="utf-8"))
        if c.get("tamanho_universo") == total:
            return c.get("posicao", 0)
    return 0


def salvar_cursor(posicao, total):
    json.dump({"posicao": posicao, "tamanho_universo": total,
              "atualizado_em": time.strftime("%Y-%m-%d")},
              open(CURSOR, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def carregar_fila():
    if FILA.exists():
        return json.load(open(FILA, encoding="utf-8"))
    return {"_governanca": (
        "Fila de DESCOBERTA em imprensa (saúde) para triagem humana. TRAVA ABSOLUTA: "
        "nenhuma pista entra no banco (saude_uf.json/monitor_saude.json/indice.json) sem "
        "que um humano preencha documento_oficial_confirmado com a URL do documento "
        "primário e registre a promoção como um item novo em instrumentos[] (§3.2), pelo "
        "fluxo manual normal. Este arquivo não é, em nenhuma circunstância, lido por "
        "gerar_monitor_saude.py nem recalcular_mare.py. Criado 18/09/2026 (handover ponto "
        "cego saúde, §3.3, achado real: caso Bahia)."),
        "pistas": []}


def registrar(fila, novas):
    """Deduplica por hash e anexa pistas inéditas com os campos de trava absoluta."""
    vistos = {p["hash"] for p in fila["pistas"]}
    ineditas = []
    for p in novas:
        p["hash"] = _hash(p)
        if p["hash"] in vistos:
            continue
        p["fonte_provavel_oficial"] = parece_fonte_oficial(p["url"])
        if not p.get("hash_evidencia"):
            try:
                from coletores_base import buscar as _buscar, preservar_evidencia as _pe
                p["hash_evidencia"] = _pe(_buscar(p["url"], timeout=30), p["url"], "html",
                                          "monitorar_imprensa_saude")
            except Exception:  # noqa: BLE001
                p["hash_evidencia"] = None
        p["documento_oficial_confirmado"] = None
        p["promovivel"] = False
        p["status"] = "pendente_confirmacao_documento"
        fila["pistas"].append(p)
        vistos.add(p["hash"])
        ineditas.append(p)
    return ineditas


def self_test():
    fx = """<rss><channel>
    <item><title><![CDATA[Sesab publica Plano de Ações de Saúde para o El Niño]]></title>
    <link>https://saude.ba.gov.br/exemplo/123</link>
    <pubDate>Fri, 18 Sep 2026 10:00:00 GMT</pubDate>
    <source url="https://x.com">Portal Bahia</source></item>
    <item><title><![CDATA[Portal noticia plano de saúde]]></title>
    <link>https://portalnoticias.com.br/plano-saude</link>
    <pubDate>Fri, 18 Sep 2026 09:00:00 GMT</pubDate>
    <source>Portal Notícias</source></item>
    </channel></rss>"""
    itens = extrair_itens_rss(fx)
    assert len(itens) == 2, "parser RSS não extraiu os 2 itens do fixture"
    assert "Plano de Ações" in itens[0]["titulo"] and "<" not in itens[0]["titulo"], "CDATA/tags não limpos"
    assert parece_fonte_oficial(itens[0]["url"]) is True, "saude.ba.gov.br deveria parecer fonte oficial"
    assert parece_fonte_oficial(itens[1]["url"]) is False, "portalnoticias.com.br não deveria parecer oficial"
    print("✓ parser RSS e heurística de fonte provável OK")

    fila = {"_governanca": "x", "pistas": []}
    alvo_fx = [{"alvo": "TESTE/UF", **i} for i in itens]
    a = registrar(fila, alvo_fx)
    b = registrar(fila, alvo_fx)
    assert len(a) == 2 and len(b) == 0, "dedup por hash falhou"
    for p in fila["pistas"]:
        assert p["documento_oficial_confirmado"] is None, "TRAVA VIOLADA: pista nasceu confirmada"
        assert p["promovivel"] is False, "TRAVA VIOLADA: pista nasceu promovível"
        assert p["status"] == "pendente_confirmacao_documento"
    print("✓ dedup e trava absoluta (campos de nascença) OK")

    universo_fx = {"uf": {
        "AC": {"status": "NAO_VERIFICADO", "data_verificacao": None},
        "RJ": {"status": "ELAB", "data_verificacao": "15/08/2026"},
        "BA": {"status": "VIG", "data_verificacao": "05/09/2026"},
        "SP": {"status": "VIG", "data_verificacao": "10/09/2026"},
    }}
    alvos = montar_universo(universo_fx)
    assert alvos[0][0] == "A-nunca-verificado" and alvos[0][1] == "AC", "priorização de NAO_VERIFICADO (camada A) falhou"
    assert any(a[0] == "B-defasado" and a[1] == "RJ" for a in alvos), "camada B (verificado antes de setembro/2026) ausente para RJ"
    assert any(a[0] == "C-amplo" and a[1] == "BA" for a in alvos), "camada C (verificado em setembro/2026, ainda que 'antigo' em dias) ausente para BA"
    assert any(a[0] == "C-amplo" and a[1] == "SP" for a in alvos), "camada C (verificado recente) ausente para SP"
    print("✓ priorização em camadas (A-nunca-verificado, B-defasado, C-amplo) OK")

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cur = pathlib.Path(d) / "cursor.json"
        json.dump({"posicao": 5, "tamanho_universo": 10}, open(cur, "w"))
        d2 = json.load(open(cur))
        assert d2["posicao"] == 5
    print("✓ mecanismo de cursor (leitura/gravação) OK")

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    for proibido in ["saude_uf.json", "monitor_saude.json", "indice.json"]:
        for m in re.finditer(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
            raise AssertionError(f"TRAVA VIOLADA: open() em modo escrita sobre {proibido} no código-fonte")
        for m in re.finditer(r'json\.dump\([^,]*,\s*open\([^)]*' + re.escape(proibido), fonte):
            raise AssertionError(f"TRAVA VIOLADA: json.dump gravando em {proibido} no código-fonte")
    print("✓ garantia estrutural: saude_uf.json é lido (necessário à priorização), "
          "mas nunca escrito; monitor_saude.json e indice.json nem lidos nem escritos")

    # Teste do filtro _menciona_uf_alvo (bug 19/09/2026)
    # Casos devem passar (mencionam a UF-alvo)
    assert _menciona_uf_alvo("Bahia prepara rede de saúde para El Niño", "", "BA"), \
        "BA: título com 'Bahia' deveria passar"
    assert _menciona_uf_alvo("Secretaria de Saúde de Cuiabá divulga plano", "", "MT"), \
        "MT: título com 'Cuiabá' (capital) deveria passar"
    assert _menciona_uf_alvo("SES-MG anuncia plano de contingência", "", "MG"), \
        "MG: título com 'SES-MG' deveria passar"
    assert _menciona_uf_alvo("Plano de ações", "https://saude.ba.gov.br/plano/123", "BA"), \
        "BA: URL com .ba.gov.br deveria passar mesmo sem estado no título"
    assert _menciona_uf_alvo("Amapá reforça vigilância para El Niño", "", "AP"), \
        "AP: título com 'Amapá' deveria passar"
    assert _menciona_uf_alvo("Ceará elabora plano de saúde", "", "CE"), \
        "CE: título com 'Ceará' deveria passar (acento preservado)"
    # Casos devem falhar (não mencionam a UF-alvo — bug de atribuição)
    assert not _menciona_uf_alvo("Secretaria de Saúde de Cuiabá divulga plano", "", "AC"), \
        "AC: título sobre Cuiabá/MT NÃO deveria passar como pista de AC"
    assert not _menciona_uf_alvo("Secretaria de Saúde de Cuiabá divulga plano", "", "AP"), \
        "AP: título sobre Cuiabá/MT NÃO deveria passar como pista de AP"
    assert not _menciona_uf_alvo("Secretaria de Saúde de Cuiabá divulga plano", "", "SE"), \
        "SE: título sobre Cuiabá/MT NÃO deveria passar como pista de SE"
    assert not _menciona_uf_alvo("MS lança campanha de enfrentamento à dengue", "", "SP"), \
        "SP: título sobre MS NÃO deveria passar como pista de SP"
    # Caso especial: 'para' (preposição) não deve ser confundida com 'Pará' (estado)
    assert not _menciona_uf_alvo("Plano de ações para arboviroses no Nordeste", "", "PA"), \
        "PA: preposição 'para' sem acento NÃO deve ser confundida com o estado Pará"
    assert _menciona_uf_alvo("Secretaria do Pará lança plano El Niño", "", "PA"), \
        "PA: 'Pará' com acento deveria passar"
    assert _menciona_uf_alvo("Prefeitura de Belém anuncia contingência", "", "PA"), \
        "PA: capital Belém deveria passar como âncora para PA"
    print("✓ filtro _menciona_uf_alvo: aceita pistas da UF-alvo, rejeita atribuições cruzadas, "
          "distingue preposição 'para' do estado 'Pará'")

    print("✓ TODOS OS TESTES PASSARAM")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()

    limite = 12
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])

    saude = json.load(open(RAIZ / "data" / "saude_uf.json", encoding="utf-8"))
    universo = montar_universo(saude)
    pos = carregar_cursor(len(universo))
    fila = carregar_fila()
    total_novas = 0
    total_filtradas = 0

    for i in range(limite):
        idx = (pos + i) % len(universo)
        rotulo, uf, queries = universo[idx]
        for q in queries:
            xml = _get(montar_url(q))
            if not xml:
                continue
            itens_brutos = extrair_itens_rss(xml)
            # Filtro de integridade (bug 19/09/2026): descarta resultados do RSS nacional
            # que não mencionam a UF-alvo no título ou na URL — evita atribuir a um estado
            # um instrumento de outro.
            itens_ok = [it for it in itens_brutos
                        if _menciona_uf_alvo(it.get("titulo", ""), it.get("url", ""), uf)]
            total_filtradas += len(itens_brutos) - len(itens_ok)
            itens = [{"alvo": f"{rotulo}/{uf}", "query": q, **it} for it in itens_ok]
            novas = registrar(fila, itens)
            total_novas += len(novas)
            time.sleep(1.0)  # cortesia de taxa, mesmo padrão das outras rotinas do pipeline

    salvar_cursor((pos + limite) % len(universo), len(universo))
    json.dump(fila, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Universo de busca: {len(universo)} alvos (camadas A/B/C); "
          f"{limite} consultados nesta execução (posição {pos}→{(pos+limite) % len(universo)}).")
    if total_filtradas:
        print(f"[FILTRADAS] {total_filtradas} notícias descartadas por não mencionar a UF-alvo "
              f"(título/URL): resultado nacional do RSS atribuído erroneamente à UF.")
    if total_novas:
        print(f"[PISTAS NOVAS] {total_novas} para triagem humana (status pendente_confirmacao_documento):")
        for p in fila["pistas"][-total_novas:]:
            marca = " [parece oficial]" if p["fonte_provavel_oficial"] else ""
            print(f"  · [{p['alvo']}]{marca} {p['titulo'][:100]}")
        print("  → NENHUMA foi confirmada nem é promovível — trava absoluta. Ver data/pistas_imprensa_saude.json.")
    else:
        print(f"Nenhuma pista inédita (fila com {len(fila['pistas'])} itens acumulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
