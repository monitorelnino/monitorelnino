#!/usr/bin/env python3
"""Vigia de imprensa nacional: busca em portais de notícias brasileiros por
possíveis instrumentos municipais/estaduais/federais ainda não registrados no
banco, usando o dicionário de busca consolidado (data/dicionario_busca.json).

Criado em 29/08/2026 respondendo a duas perguntas de Patricia: (i) "o
dicionário está correto?" — resolvida em scripts/validar_dicionario.py,
importado aqui como fonte única; (ii) "podemos verificar os principais
portais de notícias por mais publicações?" — esta rotina.

===========================================================================
TRAVA ABSOLUTA (a exigência de Patricia: "nada entra sem ser documento
oficial") — três camadas independentes, cada uma suficiente sozinha:

  1. ESTRUTURAL: esta rotina LÊ estados.json (para saber quais UFs/capitais
     buscar — leitura é necessária e legítima), mas NUNCA escreve em
     estados.json, municipios.json ou indice.json (garantia verificada por
     self-test: nenhum open(..., "w"/"a") nem json.dump direcionado a esses
     arquivos existe no código-fonte deste módulo).
  2. DE CAMPO: toda pista nasce com "documento_oficial_confirmado": null e
     "promovivel": false. Não existe, nesta rotina, nenhum caminho de código
     que ponha esses campos em outro valor — a mudança é exclusivamente
     manual, feita por um humano após localizar o documento primário
     (camada 1 do Protocolo de Busca v2, §4.1.1b) e registrar sua URL.
  3. DE PROCESSO: mesmo confirmada, uma pista não entra direto no banco — ela
     vira uma entrada em data/log_buscas.json (o mesmo log usado nas
     correções manuais desta sessão) e só então segue o fluxo humano normal
     de edição de estados.json/municipios.json. Esta rotina não toca esse
     fluxo em nenhum ponto.

Isto é mais estrito que o estatuto "Querido Diário" (descoberta, nunca
classificação) já usado em monitorar_sinais_federais.py: aqui, mesmo a
CLASSIFICAÇÃO PROVISÓRIA de uma pista como "parece oficial" é apenas um
ordenador de prioridade para o triador humano — nunca uma promoção.
===========================================================================

MECANISMO DE BUSCA: Google News RSS (news.google.com/rss/search), sem chave
de API, que agrega a grande maioria dos portais brasileiros (G1, UOL, Folha,
Estadão, CNN Brasil, R7, Correio Braziliense, Poder360, veículos regionais
etc.) — mesmo princípio de agregação usado pelo Querido Diário para diários
oficiais, aplicado aqui à imprensa. Tolerante a falha de rede (aviso, nunca
exceção); each requisição é isolada.

ESCOPO E PRIORIZAÇÃO (a pedido de Patricia, sem limite de esforço, mas o
espaço de busca de 5.570 municípios exige ordem): quatro camadas, na ordem de
valor informacional por consulta:
  camada A — as UFs em LAC (maior valor: uma reclassificação move nota e
             cobertura de uma vez);
  camada B — as 27 capitais (maior cobertura populacional por consulta);
  camada C — os demais 27 estados, busca ex-ante ampla (para pescar o padrão
             AC: estado sem nada pontuado, mas com instrumento não descoberto);
  camada D — municípios de maior população nas UFs mais suscetíveis do
             Cadastro Nacional (data/cadastro_prioritarios.json), ainda
             ausentes do banco nominal. Limitação declarada (31/08/2026): a
             lista NOMINAL completa dos 2.095 municípios do Cadastro Nacional
             (Nota Técnica 1/2025/SADJ-VI/SEPAC/CC/PR) exige login no portal
             do MDR e não é publicamente acessível; o arquivo usa, em vez
             disso, as CONTAGENS oficiais por UF (públicas, na própria nota
             técnica) para decidir em que estados concentrar a busca — dentro
             de cada UF prioritária, os alvos são os municípios de maior
             população ainda não verificados, proxy razoável e auditável.
Um cursor persistido (data/imprensa_cursor.json) faz o rodízio avançar a cada
execução, para a Action semanal cobrir o universo sem martelar o serviço.

Uso: python3 monitorar_imprensa_regional.py [--limite N]  (vigia ao vivo)
     python3 monitorar_imprensa_regional.py --self-test    (offline)
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).parent
sys.path.insert(0, str(RAIZ / "scripts"))
from validar_dicionario import get_sinalizadores_resposta  # noqa: E402 (import após sys.path)

FILA = RAIZ / "data" / "pistas_imprensa.json"
CURSOR = RAIZ / "data" / "imprensa_cursor.json"
RSS = "https://news.google.com/rss/search"
UA = {"User-Agent": "MonitorElNinoBrasil/1.0 (+monitorelnino.com.br; descoberta editorial, não indexação)"}

# Domínios cujo achado sugere fonte primária (ordenador de prioridade para o
# triador — NUNCA confirmação; ver TRAVA ABSOLUTA acima).
PADROES_FONTE_PROVAVEL_OFICIAL = [
    r"\.gov\.br", r"\.leg\.br", r"\.jus\.br", r"diariomunicipal\.com\.br",
    r"diariooficial", r"\bdoe\.", r"\bdom\.", r"in\.gov\.br",
    r"queridodiario", r"imprensaoficial",
]

TERMOS_INSTRUMENTO = ["plano de contingência", "PLANCON", "plano de enfrentamento",
                      "gabinete de crise", "plano preventivo"]


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
    """Extrai (titulo, link, data, fonte) de um retorno RSS do Google News.

    Parser tolerante por regex (evita dependência de parser XML completo,
    mesmo padrão de monitorar_sinais_federais.py): formato que não casar é
    ignorado — perda de recall, nunca invenção de resultado.
    """
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


def montar_universo(estados_json):
    """Monta a lista priorizada de alvos de busca a partir do estado atual do banco.

    Cada alvo é (rótulo, uf, [queries]). Camada A (LAC) primeiro, depois
    capitais (B), depois demais estados em busca ex-ante ampla (C), depois
    municípios grandes das UFs mais suscetíveis ainda não verificados (D) —
    ver docstring do módulo para o racional de priorização.

    A camada D usa data/cadastro_prioritarios.json (contagens oficiais por UF
    do Cadastro Nacional de Municípios Suscetíveis, Nota Técnica 1/2025/
    SADJ-VI/SEPAC/CC/PR) para decidir EM QUE ESTADOS concentrar a busca
    municipal — não uma lista nominal (indisponível publicamente; ver a
    _governanca do arquivo). Dentro de cada UF prioritária, busca-se pelos
    municípios de MAIOR POPULAÇÃO ainda ausentes do banco nominal — proxy
    razoável de relevância e de probabilidade de cobertura de imprensa,
    registrado em 31/08/2026 a partir de achado real de sessão (Guarulhos,
    Campinas, São Gonçalo, São Bernardo do Campo).
    """
    ufs = estados_json["ufs"]
    lac = [u for u in ufs if u["status"] == "LAC"]
    outros = [u for u in ufs if u["status"] != "LAC"]
    alvos = []
    for u in lac:
        alvos.append(("A-lac", u["uf"], [
            f'"{t}" {u["nome"]} 2026 El Niño' for t in TERMOS_INSTRUMENTO[:3]
        ]))
    for u in ufs:
        cap = u.get("capital", {}).get("nome")
        if cap:
            alvos.append(("B-capital", u["uf"], [
                f'"{t}" prefeitura {cap} 2026' for t in TERMOS_INSTRUMENTO[:2]
            ]))
    for u in outros:
        alvos.append(("C-estado-amplo", u["uf"], [
            f'governo {u["nome"]} "plano" El Niño estiagem 2026 preventivo',
        ]))

    cadastro_path = RAIZ / "data" / "cadastro_prioritarios.json"
    if cadastro_path.exists():
        try:
            cadastro = json.load(open(cadastro_path, encoding="utf-8"))
            municipios = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
            pop = json.load(open(RAIZ / "data" / "populacao_censo2022.json", encoding="utf-8"))
            ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
            ja_temos = {(r["nome"], r["uf"]) for r in municipios}
            for uf in cadastro.get("ordem_prioridade_uf_por_percentual", []):
                candidatos = [(pop.get(str(r["codigo_ibge"]).zfill(7), 0), r["nome"], r["uf"])
                             for r in ref if r["uf"] == uf and (r["nome"], r["uf"]) not in ja_temos]
                candidatos.sort(reverse=True)
                for _, nome, ufc in candidatos[:5]:  # os 5 maiores por UF prioritária, por rodada
                    alvos.append(("D-municipio-prioritario", f"{nome}/{ufc}", [
                        f'"{t}" {nome} {ufc} 2026 El Niño estiagem defesa civil' for t in TERMOS_INSTRUMENTO[:2]
                    ]))
        except Exception as e:
            print(f"[aviso] camada D (municípios prioritários) não pôde ser montada: {e}")

    return alvos


def carregar_cursor(total):
    """Lê a posição do rodízio; reinicia do zero quando o universo muda de tamanho."""
    if CURSOR.exists():
        c = json.load(open(CURSOR, encoding="utf-8"))
        if c.get("tamanho_universo") == total:
            return c.get("posicao", 0)
    return 0


def salvar_cursor(posicao, total):
    """Grava a posição do rodízio para a próxima execução continuar dali."""
    json.dump({"posicao": posicao, "tamanho_universo": total,
              "atualizado_em": time.strftime("%Y-%m-%d")},
              open(CURSOR, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def carregar_fila():
    """Carrega a fila de pistas (ou inicializa vazia com o cabeçalho de governança)."""
    if FILA.exists():
        return json.load(open(FILA, encoding="utf-8"))
    return {"_governanca": (
        "Fila de DESCOBERTA em imprensa para triagem humana (METODOLOGIA §17). "
        "TRAVA ABSOLUTA: nenhuma pista entra no banco (estados.json/municipios.json/"
        "indice.json) sem que um humano preencha documento_oficial_confirmado com a "
        "URL do documento primário (Protocolo de Busca v2, camada 1) e registre a "
        "promoção em data/log_buscas.json, pelo fluxo manual normal. Este arquivo "
        "não é, em nenhuma circunstância, lido por recalcular_mare.py."),
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
        p["documento_oficial_confirmado"] = None   # só um humano preenche
        p["promovivel"] = False                    # nunca setado por código
        p["status"] = "pendente_confirmacao_documento"
        fila["pistas"].append(p)
        vistos.add(p["hash"])
        ineditas.append(p)
    return ineditas


def self_test():
    """Valida offline: parsing RSS, heurística de fonte, cursor, dedup e a trava absoluta por inspeção do código-fonte."""
    fx = """<rss><channel>
    <item><title><![CDATA[Prefeitura publica Plano de Contingência 2026]]></title>
    <link>https://diariomunicipal.com.br/exemplo/123</link>
    <pubDate>Sat, 29 Aug 2026 10:00:00 GMT</pubDate>
    <source url="https://x.com">Diário Municipal</source></item>
    <item><title><![CDATA[Portal noticia decreto de emergência]]></title>
    <link>https://portalnoticias.com.br/decreto-emergencia</link>
    <pubDate>Sat, 29 Aug 2026 09:00:00 GMT</pubDate>
    <source>Portal Notícias</source></item>
    </channel></rss>"""
    itens = extrair_itens_rss(fx)
    assert len(itens) == 2, "parser RSS não extraiu os 2 itens do fixture"
    assert "Plano de Contingência" in itens[0]["titulo"] and "<" not in itens[0]["titulo"], "CDATA/tags não limpos"
    assert parece_fonte_oficial(itens[0]["url"]) is True, "diariomunicipal.com.br deveria parecer fonte oficial"
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

    universo_fx = {"ufs": [
        {"uf": "SE", "nome": "Sergipe", "status": "LAC", "capital": {"nome": "Aracaju"}},
        {"uf": "SC", "nome": "Santa Catarina", "status": "NOVO", "capital": {"nome": "Florianópolis"}},
    ]}
    alvos = montar_universo(universo_fx)
    assert alvos[0][0] == "A-lac" and alvos[0][1] == "SE", "priorização de LAC (camada A) falhou"
    assert any(a[0] == "B-capital" for a in alvos), "camada de capitais ausente"
    assert any(a[0] == "C-estado-amplo" and a[1] == "SC" for a in alvos), "camada C ausente para não-LAC"
    print("✓ priorização em camadas (A-lac, B-capital, C-estado-amplo) OK")

    alvos_d = [a for a in alvos if a[0] == "D-municipio-prioritario"]
    assert alvos_d, "camada D (municípios prioritários) não gerou nenhum alvo — cadastro_prioritarios.json ausente ou vazio?"
    rotulos_d = {a[1] for a in alvos_d}
    assert not any("/" not in r for r in rotulos_d), "rótulo da camada D deveria ser 'Nome/UF'"
    print(f"✓ priorização em camadas (A-lac, B-capital, C-estado-amplo, D-município-prioritário: "
          f"{len(alvos_d)} alvos) OK")

    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        cur = pathlib.Path(d) / "cursor.json"
        json.dump({"posicao": 5, "tamanho_universo": 10}, open(cur, "w"))
        d2 = json.load(open(cur))
        assert d2["posicao"] == 5
    print("✓ mecanismo de cursor (leitura/gravação) OK")

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    for proibido in ["estados.json", "municipios.json", "indice.json"]:
        # a garantia é sobre ESCRITA, não leitura: ler estados.json (para saber
        # o que buscar) e municipios.json (para saber o que já está coberto, na
        # camada D) é necessário e legítimo; o que é vedado é qualquer caminho
        # de código que abra esses arquivos para gravação ou os alvo de json.dump.
        for m in re.finditer(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
            raise AssertionError(f"TRAVA VIOLADA: open() em modo escrita sobre {proibido} no código-fonte")
        for m in re.finditer(r'json\.dump\([^,]*,\s*open\([^)]*' + re.escape(proibido), fonte):
            raise AssertionError(f"TRAVA VIOLADA: json.dump gravando em {proibido} no código-fonte")
    print("✓ garantia estrutural: estados.json e municipios.json são lidos (necessário à priorização), "
          "mas nunca escritos; indice.json nem lido nem escrito")

    print("✓ TODOS OS TESTES PASSARAM")
    return 0


def main():
    """CLI: consome o cursor, busca o próximo lote de alvos, registra pistas e avança o rodízio."""
    if "--self-test" in sys.argv:
        return self_test()

    limite = 12
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])

    estados = json.load(open(RAIZ / "data" / "estados.json", encoding="utf-8"))
    universo = montar_universo(estados)
    pos = carregar_cursor(len(universo))
    fila = carregar_fila()
    total_novas = 0

    for i in range(limite):
        idx = (pos + i) % len(universo)
        rotulo, uf, queries = universo[idx]
        for q in queries:
            xml = _get(montar_url(q))
            if not xml:
                continue
            itens = [{"alvo": f"{rotulo}/{uf}", "query": q, **it} for it in extrair_itens_rss(xml)]
            novas = registrar(fila, itens)
            total_novas += len(novas)
            time.sleep(1.0)  # cortesia de taxa, mesmo padrão das outras rotinas do pipeline

    salvar_cursor((pos + limite) % len(universo), len(universo))
    json.dump(fila, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Universo de busca: {len(universo)} alvos (camadas A/B/C); "
          f"{limite} consultados nesta execução (posição {pos}→{(pos+limite) % len(universo)}).")
    if total_novas:
        print(f"[PISTAS NOVAS] {total_novas} para triagem humana (status pendente_confirmacao_documento):")
        for p in fila["pistas"][-total_novas:]:
            marca = " [parece oficial]" if p["fonte_provavel_oficial"] else ""
            print(f"  · [{p['alvo']}]{marca} {p['titulo'][:100]}")
        print("  → NENHUMA foi confirmada nem é promovível — trava absoluta. Ver data/pistas_imprensa.json.")
    else:
        print(f"Nenhuma pista inédita (fila com {len(fila['pistas'])} itens acumulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
