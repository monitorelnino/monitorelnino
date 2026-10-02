#!/usr/bin/env python3
"""Síndrome gripal pela fonte primária — e-SUS Notifica, no Portal de Dados Abertos do SUS.

Bloco de 01/10/2026 (23h20 UTC, editoria): síndrome gripal não tinha coletor em nenhuma rotina.
Este é o coletor. Ele acompanha o `coletar_srag_sivep.py`, que cobre a síndrome respiratória
**grave** (hospitalizada): a gripal é a notificação leve, e as duas juntas são o que o painel de
saúde chama de doenças respiratórias.

O ESTADO DA FONTE, MEDIDO EM 01/10/2026 — E POR QUE NADA FOI PUBLICADO
----------------------------------------------------------------------
O portal declara duas rotas para o e-SUS Notifica, e **as duas recusam acesso automatizado**:

1. `API OpenSearch` (`notifica-prd-es.saude.gov.br/desc-esus-notifica-estado-*/_search`) devolve
   **HTTP 401** ao cliente do projeto, com e sem o `_count`. 401 é recusa de acesso, e recusa se
   respeita, sempre — não se contorna com credencial achada em documento, e o repositório é
   público: senha não entra aqui (`CLAUDE.md`, seção de segurança).
2. Os **CSV por UF e lote**, cujos endereços o próprio portal publica dentro da descrição de cada
   recurso (`s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SGL/<ano>/uf=<UF>/lote=<n>/...csv`),
   devolvem **HTTP 403**.

Além disso, o conjunto por ano para a **síndrome gripal** existe de 2020 a 2024: não há conjunto de
2025 nem de 2026. Ou seja, mesmo que o acesso abrisse, o ciclo 2026/2027 não tem série aberta nesta
fonte até o corte.

Por isso este coletor **não publica série**: ele consulta, mede e declara a lacuna, com o código de
cada recusa e a lista de anos que a fonte oferece. É a regra do projeto: ausência é lacuna
declarada, com fonte, e nunca "não existe". Se a fonte abrir — o acesso volta, ou o Ministério
publica o ano corrente —, o mesmo coletor passa a agregar sem mudança de rota: a descoberta dos
conjuntos e dos arquivos já está escrita e testada aqui.

MICRODADO NÃO SE GUARDA
-----------------------
Quando houver o que ler, cada arquivo é lido em fluxo, agregado por UF × semana epidemiológica e
descartado — mesma regra do SRAG. O que se guarda é a contagem.

USO
  python3 coletar_sg_esus.py --autoteste
  python3 coletar_sg_esus.py --relatorio     # o que a fonte oferece, sem baixar microdado
  python3 coletar_sg_esus.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from coletores_base import (buscar, gravar, hoje_editorial, ler, log_busca,  # noqa: E402
                            preservar_evidencia, registrar_lacuna, rodar_autoteste)

BUSCA = "https://dadosabertos.saude.gov.br/dataset?q=gripal"
CONJUNTO = "https://dadosabertos.saude.gov.br/dataset/{slug}"
SAIDA = "saude_desfechos/sindrome_gripal_serie.json"
ORIGEM = "coletar_sg_esus"

# O nome do conjunto por ano, como o portal o publica. O ano sai do próprio nome: nada de montar
# slug por analogia e pedir um ano que a fonte não tem.
RE_CONJUNTO_ANO = re.compile(r"^notificacoes-de-sindrome-gripal-leve-(20\d\d)$")
# Os endereços dos CSV vivem DENTRO da descrição de cada recurso, em markdown. Medido em
# 01/10/2026: o campo `url` do recurso vem vazio, e o link está no `description`.
RE_LINK_MD = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
RE_UF_NO_CAMINHO = re.compile(r"/uf=([A-Z]{2})/")
RE_NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

RESSALVA = ("O Monitor não atribui casos ao El Niño. Síndrome gripal é a notificação de caso leve "
            "no e-SUS Notifica (Ministério da Saúde); casos graves ficam na série de SRAG, do "
            "SIVEP-Gripe. As últimas semanas são parciais e sobem com as notificações atrasadas.")


# =============================================================================================
# Leitura do que o portal declara — funções puras sobre o corpo da página
# =============================================================================================
def payload_do_portal(html: str) -> dict:
    """O JSON que a própria página carrega (`__NEXT_DATA__`). Função pura.

    Levanta `ValueError` quando o bloco não está lá: é mudança de contrato da fonte, e não ausência
    de dado. Os dois não podem virar a mesma coisa."""
    m = RE_NEXT.search(html or "")
    if not m:
        raise ValueError("a página não traz o bloco __NEXT_DATA__: formato da fonte mudou")
    return json.loads(m.group(1))


def conjuntos_por_ano(payload: dict) -> dict:
    """{ano: slug} dos conjuntos de síndrome gripal que a fonte oferece. Função pura."""
    pacotes = ((payload or {}).get("props") or {}).get("pageProps", {}).get("packages") or []
    saida = {}
    for p in pacotes:
        m = RE_CONJUNTO_ANO.match(str(p.get("name") or ""))
        if m:
            saida[int(m.group(1))] = p["name"]
    return dict(sorted(saida.items()))


def arquivos_do_conjunto(payload: dict) -> list:
    """[{uf, url}] dos CSV que o conjunto declara. Função pura.

    O endereço vem da descrição do recurso, que é onde a fonte o publica; a UF vem do CAMINHO do
    arquivo, não do nome do recurso — o nome é texto livre ("Dados AC - 20/12") e o caminho é
    estrutura (`/uf=AC/`)."""
    pp = ((payload or {}).get("props") or {}).get("pageProps") or {}
    pacote = pp.get("package") or pp
    saida, vistos = [], set()
    for r in pacote.get("resources") or []:
        if (r.get("format") or "").upper() != "CSV":
            continue
        for _rotulo, url in RE_LINK_MD.findall(r.get("description") or ""):
            if not url.lower().endswith(".csv") or url in vistos:
                continue
            uf = RE_UF_NO_CAMINHO.search(url)
            vistos.add(url)
            saida.append({"uf": uf.group(1) if uf else None, "url": url})
    return saida


def api_declarada(payload: dict) -> str:
    """O endereço da API que o conjunto declara, ou "". Função pura."""
    pp = ((payload or {}).get("props") or {}).get("pageProps") or {}
    pacote = pp.get("package") or pp
    for r in pacote.get("resources") or []:
        if (r.get("format") or "").upper() == "API" and (r.get("url") or ""):
            return r["url"]
    return ""


def decidir(anos: dict, ano_do_ciclo: int, api_respondeu: bool, csv_respondeu: bool) -> str:
    """A decisão da rodada. Função pura.

    Nenhuma combinação produz "série publicada" sem leitura: `fonte_bloqueada` quando as rotas
    recusam, `ano_do_ciclo_ausente` quando a fonte não oferece o ano, e só com rota aberta E ano
    presente é que há o que agregar."""
    if not anos:
        return "formato_da_fonte_mudou"
    if not (api_respondeu or csv_respondeu):
        return "fonte_bloqueada"
    if ano_do_ciclo not in anos:
        return "ano_do_ciclo_ausente"
    return "agregar"


DECISAO_NO_LOG = {"fonte_bloqueada": "erro",
                  "ano_do_ciclo_ausente": "consultado sem achado",
                  "formato_da_fonte_mudou": "erro",
                  "agregar": "registro"}


# =============================================================================================
# A rodada
# =============================================================================================
def sondar(buscar_fn=None) -> dict:
    """Consulta a fonte e devolve o que ela oferece e o que ela recusa. Não grava nada."""
    _buscar = buscar_fn or buscar
    bruto = _buscar(BUSCA, timeout=90, origem=ORIGEM)
    html = bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto
    anos = conjuntos_por_ano(payload_do_portal(html))
    estado = {"anos_oferecidos": sorted(anos), "api": "", "api_erro": "", "csv_erro": "",
              "csv_exemplo": "", "arquivos_no_ano_mais_recente": 0}
    if not anos:
        return estado
    recente = max(anos)
    bruto = _buscar(CONJUNTO.format(slug=anos[recente]), timeout=90, origem=ORIGEM)
    pagina = bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto
    payload = payload_do_portal(pagina)
    arquivos = arquivos_do_conjunto(payload)
    estado["arquivos_no_ano_mais_recente"] = len(arquivos)
    estado["api"] = api_declarada(payload)
    if not estado["api"]:
        # Medido em 01/10/2026: o conjunto por ANO não declara a API — ela vive num conjunto
        # próprio ("API OpenSearch"). Sem esta segunda leitura, a lacuna diria "API não declarada"
        # quando a verdade é outra e pior: ela existe e responde 401.
        try:
            bruto = _buscar(CONJUNTO.format(slug="notificacoes-de-sindrome-gripal-api-opensearch"),
                            timeout=90, origem=ORIGEM)
            pag = bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto
            estado["api"] = api_declarada(payload_do_portal(pag))
        except Exception as e:  # noqa: BLE001
            estado["api_erro"] = f"conjunto da API não lido: {type(e).__name__}: {e}"
    # As duas rotas, uma a uma, com o código que cada uma devolve. Recusa se mede, não se supõe.
    if estado["api"]:
        try:
            _buscar(estado["api"].replace("_search", "_count"), timeout=60, origem=ORIGEM)
        except Exception as e:  # noqa: BLE001
            estado["api_erro"] = f"{type(e).__name__}: {e}"
    if arquivos:
        estado["csv_exemplo"] = arquivos[0]["url"]
        try:
            _buscar(arquivos[0]["url"], timeout=90, origem=ORIGEM)
        except Exception as e:  # noqa: BLE001
            estado["csv_erro"] = f"{type(e).__name__}: {e}"
    return estado


def registrar_tentativa_sg(dados: dict, agora: str = None, escrever: bool = True) -> dict:
    """Mesma porta do SRAG (item 5, 02/10/2026): cada tentativa aparece no painel.

    Aqui nao ha arquivo grande para retomar — a fonte recusa com 401 e 403, e recusa se respeita.
    O que o painel resolve e o outro lado do mesmo problema: lacuna publicada em junho e lacuna
    medida hoje sao indistinguiveis na pagina, e a linha do painel diz qual e qual.
    """
    from coletores_base import registrar_tentativa_coletor
    return registrar_tentativa_coletor("coletar_sg_esus", dados, agora=agora, escrever=escrever)


def coletar() -> dict:
    estado = sondar()
    anos = {a: a for a in estado["anos_oferecidos"]}
    ano_do_ciclo = hoje_editorial().year
    decisao = decidir(anos, ano_do_ciclo,
                      api_respondeu=bool(estado["api"]) and not estado["api_erro"],
                      csv_respondeu=bool(estado["csv_exemplo"]) and not estado["csv_erro"])
    corpo = json.dumps({"fonte": BUSCA, "medido_em": hoje_editorial().isoformat(),
                        "estado_da_fonte": estado, "decisao": decisao},
                       ensure_ascii=False, indent=1).encode("utf-8")
    h = preservar_evidencia(corpo, BUSCA, "json", ORIGEM)

    if decisao != "agregar":
        motivo = {
            "fonte_bloqueada": (f"e-SUS Notifica recusa acesso automatizado nas duas rotas que o "
                                f"portal declara — API: {estado['api_erro'] or 'não declarada'}; "
                                f"CSV: {estado['csv_erro'] or 'não declarado'}"),
            "ano_do_ciclo_ausente": (f"a fonte oferece {estado['anos_oferecidos']} e não o ano do "
                                     f"ciclo ({ano_do_ciclo})"),
            "formato_da_fonte_mudou": "a busca do portal não devolveu nenhum conjunto por ano",
        }[decisao]
        registrar_tentativa_sg({"resultado": "lacuna", "motivo": motivo[:180]})
        registrar_lacuna("sindrome_gripal", motivo, canal="repositorio_nacional", camada=1,
                         nivel="nacional", strings=[BUSCA], hash_evidencia=h)
        # A lacuna é PUBLICÁVEL: a página precisa dizer ao leitor que procuramos e não obtivemos.
        gravar(SAIDA, {"_governanca": __doc__.strip().splitlines()[0],
                       "ressalva": RESSALVA,
                       "fonte": BUSCA,
                       "sistema": "e-SUS Notifica (Ministério da Saúde)",
                       "serie": [],
                       "lacuna": motivo,
                       "anos_oferecidos": estado["anos_oferecidos"],
                       "medido_em": hoje_editorial().strftime("%d/%m/%Y"),
                       "hash_evidencia": h})
    log_busca("repositorio_nacional", 1, [BUSCA], DECISAO_NO_LOG[decisao], nivel="nacional",
              n_resultados=len(estado["anos_oferecidos"]),
              resultados=f"sindrome_gripal: decisão {decisao} · anos {estado['anos_oferecidos']} · "
                         f"api {estado['api_erro'] or 'ok'} · csv {estado['csv_erro'] or 'ok'}",
              hash_evidencia=h)
    return {"decisao": decisao, **estado}


# =============================================================================================
# Autoteste — offline, sem rede e sem escrever em data/
# =============================================================================================
def fonte_do_coletor() -> str:
    """O código OPERACIONAL deste arquivo, como texto — tudo o que vem antes do autoteste."""
    texto = pathlib.Path(__file__).read_text(encoding="utf-8")
    corte = texto.find("def autoteste")
    return texto[:corte] if corte > 0 else texto


BANCO_PROIBIDO = ("estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json")

# Recorte REAL do portal, 01/10/2026 (encurtado; a estrutura é a que veio).
FIXTURE_BUSCA = ('<html><script id="__NEXT_DATA__" type="application/json">' + json.dumps({
    "props": {"pageProps": {"numberOfPackages": 11, "packages": [
        {"name": "notificacoes-de-sindrome-gripal-leve-2024"},
        {"name": "notificacoes-de-sindrome-gripal-leve-2020"},
        {"name": "notificacoes-de-sindrome-gripal-api-opensearch"},
        {"name": "srag-2019-a-2026"},
    ]}}}, ensure_ascii=False) + "</script></html>")

FIXTURE_CONJUNTO = ('<html><script id="__NEXT_DATA__" type="application/json">' + json.dumps({
    "props": {"pageProps": {"package": {"resources": [
        {"format": "PDF", "name": "Dicionário de Dados", "url": "https://x/d.pdf",
         "description": ""},
        {"format": "API", "name": "Opensearch API",
         "url": "https://notifica-prd-es.saude.gov.br/desc-esus-notifica-estado-*/_search",
         "description": ""},
        {"format": "CSV", "name": "Dados AC - 20/12", "url": "",
         "description": "# **Lista de dados UF AC**\n- [UF-AC - Lote 1]("
                        "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SGL/2024/uf=AC/"
                        "lote=1/part-00000.c000.csv)\n"},
        {"format": "CSV", "name": "Dados AL - 20/12", "url": "",
         "description": "- [UF-AL - Lote 1](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"
                        "SGL/2024/uf=AL/lote=1/part-00001.c000.csv)\n"},
    ]}}}}, ensure_ascii=False) + "</script></html>")


def autoteste() -> int:
    anos = conjuntos_por_ano(payload_do_portal(FIXTURE_BUSCA))
    arquivos = arquivos_do_conjunto(payload_do_portal(FIXTURE_CONJUNTO))
    casos = {
        "o conjunto por ano sai do nome que a fonte publica":
            lambda: anos == {2020: "notificacoes-de-sindrome-gripal-leve-2020",
                             2024: "notificacoes-de-sindrome-gripal-leve-2024"},
        "conjunto que não é de ano não entra (API, SRAG)":
            lambda: all(isinstance(a, int) for a in anos),
        "o endereço do CSV vem da descrição, porque o campo url vem vazio":
            lambda: [a["url"] for a in arquivos] == [
                "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SGL/2024/uf=AC/lote=1/"
                "part-00000.c000.csv",
                "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SGL/2024/uf=AL/lote=1/"
                "part-00001.c000.csv"],
        "a UF vem do caminho do arquivo, não do nome do recurso":
            lambda: [a["uf"] for a in arquivos] == ["AC", "AL"],
        "PDF não entra como arquivo de dado":
            lambda: all(a["url"].endswith(".csv") for a in arquivos),
        "a API declarada é lida do recurso":
            lambda: api_declarada(payload_do_portal(FIXTURE_CONJUNTO)).endswith("/_search"),
        "página sem o bloco da fonte LEVANTA, em vez de devolver vazio":
            lambda: _levanta(lambda: payload_do_portal("<html>nada</html>"), ValueError),
        # A trava central: recusa nas duas rotas nunca produz série.
        "as duas rotas recusando é fonte bloqueada":
            lambda: decidir({2024: "x"}, 2026, False, False) == "fonte_bloqueada",
        "fonte bloqueada entra no log como erro, nunca como 'consultado sem achado'":
            lambda: DECISAO_NO_LOG["fonte_bloqueada"] == "erro",
        "ano do ciclo ausente é consulta sem achado, e não erro da fonte":
            lambda: (decidir({2024: "x"}, 2026, True, True) == "ano_do_ciclo_ausente"
                     and DECISAO_NO_LOG["ano_do_ciclo_ausente"] == "consultado sem achado"),
        "com rota aberta e ano presente, agrega":
            lambda: decidir({2026: "x"}, 2026, False, True) == "agregar",
        "nenhum conjunto é mudança de formato, não ausência":
            lambda: decidir({}, 2026, True, True) == "formato_da_fonte_mudou",
        "uma rota aberta basta para não ser bloqueio":
            lambda: decidir({2026: "x"}, 2026, True, False) == "agregar",
        # TRAVA ESTRUTURAL: o coletor não pode ganhar escrita no banco numa edição futura.
        "o fonte não grava em nenhum arquivo do banco":
            lambda: not any(f'gravar("{nome}' in fonte_do_coletor() for nome in BANCO_PROIBIDO),
        "a lista proibida é a canônica do projeto, com os cinco arquivos":
            lambda: set(BANCO_PROIBIDO) == {"estados.json", "saude_uf.json", "municipios.json",
                                            "indice.json", "monitor_saude.json"},
        "o fonte grava só na própria série":
            lambda: sorted(set(re.findall(r"gravar\((SAIDA|\"[^\"]+\")", fonte_do_coletor()))) == ["SAIDA"],
        # A ressalva é obrigatória: o leitor não pode receber série de doença sem ela.
        "a ressalva diz que o Monitor não atribui casos ao El Niño":
            lambda: "não atribui casos ao El Niño" in RESSALVA,
        "a ressalva distingue gripal de grave":
            lambda: "SRAG" in RESSALVA and "leve" in RESSALVA,
        # Item 5 do contrato de layout: cada tentativa aparece no painel, com o motivo — lacuna
        # publicada em junho e lacuna medida hoje são indistinguíveis na página sem isto.
        "a tentativa entra no painel de saúde dos coletores, com o motivo":
            lambda: (registrar_tentativa_sg({"resultado": "lacuna", "motivo": "API 401"},
                                            agora="2026-10-02", escrever=False)
                     ["tentativas"][-1]["motivo"] == "API 401"),
        "o painel sabe não escrever, e é por isso que o autoteste pode exercitá-lo":
            lambda: "escrever" in __import__("inspect").signature(registrar_tentativa_sg).parameters,
    }
    return rodar_autoteste(casos)


def _levanta(fn, excecao) -> bool:
    try:
        fn()
    except excecao:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--relatorio" in sys.argv:
        estado = sondar()
        print(json.dumps(estado, ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(coletar(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
