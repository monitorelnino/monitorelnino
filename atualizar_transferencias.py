#!/usr/bin/env python3
"""
atualizar_transferencias.py
============================
Consulta a API pública do Portal da Transparência (api.portaldatransparencia.gov.br)
para os municípios cadastrados em data/municipios.json e atualiza data/transferencias.json
com os valores efetivamente transferidos (convênios / transferências voluntárias) que
mencionem defesa civil / desastres / emergência / estiagem / seca / El Niño.

COMO OBTER A CHAVE DE API (gratuita):
  1. Acesse https://portaldatransparencia.gov.br/api-de-dados
  2. Clique em "Solicitar cadastro" (cadastro por e-mail)
  3. A chave chega por e-mail; exporte-a como variável de ambiente:
       export PORTAL_TRANSPARENCIA_API_KEY="sua_chave_aqui"

LIMITES DE REQUISIÇÃO (documentados pelo Portal):
  - 06:00–23:59 → até 400 requisições/minuto
  - 00:00–05:59 → até 700 requisições/minuto
  Este script já inclui um limitador conservador (padrão: 60 req/min) para uso
  responsável mesmo com muitos municípios cadastrados.

O QUE ESTE SCRIPT FAZ (e o que NÃO faz):
  - Consulta os endpoints documentados de CONVÊNIOS e TRANSFERÊNCIAS VOLUNTÁRIAS,
    filtrando por código IBGE de cada município do banco.
  - Filtra os resultados por palavras-chave (defesa civil, desastre, emergência,
    calamidade, estiagem, seca, enchente, El Niño) para reduzir ruído.
  - Grava um relatório bruto (data/transferencias_api_raw.json) com TUDO que a API
    retornou, para auditoria — nunca decide sozinho o que "conta" como recurso do
    El Niño; isso fica para revisão humana antes de entrar em transferencias.json.
  - NÃO publica automaticamente no transferencias.json final — gera um arquivo de
    revisão (transferencias_revisar.json) que você aprova manualmente. Isso é
    proposital: a mesma regra de "nunca inventar/presumir" vale para automação.

ANTES DE RODAR EM ESCALA:
  - Confirme os nomes exatos dos parâmetros no Swagger oficial:
    https://api.portaldatransparencia.gov.br/swagger-ui/index.html
    (os endpoints abaixo seguem o padrão documentado publicamente em ago/2026;
    a API do governo pode alterar nomes de parâmetros sem aviso.)
  - Teste primeiro com --limite 5 para validar antes de rodar os 5.570 municípios.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

# 26/09/2026 (§226): este script era o único do pipeline que pedia rede sem passar pelo
# `coletores_base` — `requests` direto, sem espera, sem lacuna declarada e sem escrita atômica.
# As três coisas vêm daqui agora, em vez de uma quarta cópia de cada regra.
from coletores_base import esperas_para, registrar_lacuna, gravar, ua_de

API_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
ENDPOINTS = {
    "convenios": "/convenios",
    "transferencias_voluntarias": "/transferencias-voluntarias",
}

PALAVRAS_CHAVE = [
    "defesa civil", "desastre", "emergência", "emergencia", "calamidade",
    "estiagem", "seca", "enchente", "inundação", "inundacao",
    "incêndio florestal", "incendio florestal", "el niño", "el nino",
]

DATA_DIR = Path(__file__).parent / "data"


def get_api_key() -> str:
    """Lê PORTAL_TRANSPARENCIA_API_KEY do ambiente; devolve None (nunca string vazia) se ausente, para que o chamador decida pular a etapa com aviso."""
    key = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY")
    if not key:
        sys.exit(
            "Erro: defina a variável de ambiente PORTAL_TRANSPARENCIA_API_KEY.\n"
            "Cadastro gratuito em https://portaldatransparencia.gov.br/api-de-dados"
        )
    return key


class RateLimiter:
    """Limitador simples de requisições por minuto (padrão conservador: 60/min)."""

    def __init__(self, max_por_minuto: int = 60):
        """Inicializa o limitador de taxa com o intervalo mínimo entre requisições consecutivas."""
        self.intervalo = 60.0 / max_por_minuto
        self.ultima = 0.0

    def esperar(self):
        """Bloqueia até que o intervalo mínimo desde a última requisição tenha decorrido."""
        agora = time.time()
        delta = agora - self.ultima
        if delta < self.intervalo:
            time.sleep(self.intervalo - delta)
        self.ultima = time.time()


def consultar_endpoint(endpoint: str, params: dict, api_key: str, limiter: RateLimiter,
                       max_paginas: int = 5, pedir_fn=None, dormir=None, lacuna_fn=None):
    """Pagina um endpoint da API e retorna a lista completa de resultados.

    26/09/2026 (§226) — três defeitos corrigidos de uma vez, todos da mesma família:

    1. **Erro transitório virava ausência de repasse.** Qualquer código diferente de 200 e 429
       imprimia um aviso e abandonava o município. Em 26/09/2026 o endpoint de convênios devolveu
       `HTTP 504` na sonda de credenciais — gateway, não recusa —, e com o código antigo aquele
       município entraria no arquivo como "nada encontrado". Agora 5xx e 429 esperam o que a
       política compartilhada de `coletores_base` manda esperar, e só depois desistem.

    2. **O 429 repetia para sempre.** `continue` sem consumir tentativa: com um limite de taxa
       persistente, o laço nunca terminava. Agora a espera é contada, e acaba.

    3. **Desistir era silencioso.** Um `print` não é rastro: não entra no log de buscas nem na
       contagem de lacunas, e o município ficava indistinguível de um que não tem convênio. Agora
       desistir DECLARA a lacuna, com o código HTTP e o município — zero e ausência de dado são
       coisas distintas, e esta função confundia as duas.

    `pedir_fn`, `dormir` e `lacuna_fn` existem para o autoteste provar as três coisas sem rede."""
    # §228: o cabeçalho levava a chave e NÃO levava o cliente — o Portal recebia um pedido
    # autenticado de agente anônimo.
    pedir = pedir_fn or (lambda url: requests.get(
        url, headers={"chave-api-dados": api_key, "User-Agent": ua_de("transferências do Portal")},
        timeout=30))
    _dormir = dormir or time.sleep
    _lacuna = lacuna_fn or registrar_lacuna
    resultados = []
    pagina = 1
    while pagina <= max_paginas:
        q = dict(params, pagina=pagina)
        url = f"{API_BASE}{endpoint}?{urlencode(q)}"
        restantes = None
        resp = None
        while True:
            limiter.esperar()
            resp = pedir(url)
            if resp.status_code == 200:
                break
            if restantes is None:
                restantes = list(esperas_para(resp.status_code))
            if not restantes:
                break
            espera = restantes.pop(0)
            print(f"  [{resp.status_code}] {endpoint}: a fonte pediu tempo — esperando {espera}s", flush=True)
            _dormir(espera)
        if resp.status_code != 200:
            # Lacuna DECLARADA, não aviso: o município não fica indistinguível de um sem convênio.
            _lacuna(f"Portal da Transparência ({endpoint})",
                    f"HTTP {resp.status_code} após as esperas — município IBGE "
                    f"{params.get('codigoIBGE')}, ano {params.get('ano')}",
                    strings=[url])
            break
        dados = resp.json()
        if not dados:
            break
        resultados.extend(dados)
        if len(dados) < params.get("itens", 20):
            break
        pagina += 1
    return resultados


def bate_palavra_chave(registro: dict) -> bool:
    """Confere se o texto de um repasse do Portal da Transparência menciona termos de defesa civil/El Niño, para filtrar ruído de outras transferências municipais."""
    texto = json.dumps(registro, ensure_ascii=False).lower()
    return any(p in texto for p in PALAVRAS_CHAVE)


def main():
    """Consulta a API do Portal da Transparência por UF, aplica o filtro de palavra-chave e grava data/transferencias.json com controle de taxa de requisição."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limite", type=int, default=None, help="Limitar a N municípios (para teste)")
    ap.add_argument("--ano", type=int, default=2026, help="Ano de referência (padrão: 2026)")
    ap.add_argument("--req-por-minuto", type=int, default=60, help="Limite de requisições/min (padrão: 60, conservador)")
    args = ap.parse_args()

    api_key = get_api_key()
    limiter = RateLimiter(args.req_por_minuto)

    municipios = json.load(open(DATA_DIR / "municipios.json", encoding="utf-8"))
    codigos = sorted({(m["nome"], m["uf"]) for m in municipios})
    if args.limite:
        codigos = codigos[: args.limite]

    # o dataset municipios.json não traz código IBGE — carregar do arquivo de referência
    # (gerado a partir do IBGE; ver README da Fase de dados). Ajuste o caminho se necessário.
    ref_path = DATA_DIR / "municipios_ibge_referencia.json"
    if not ref_path.exists():
        sys.exit(
            f"Erro: não encontrei {ref_path}.\n"
            "Gere esse arquivo de referência (nome, uf, codigo_ibge) a partir da base "
            "IBGE usada no projeto antes de rodar este script."
        )
    ref = {(r["nome"], r["uf"]): r["codigo_ibge"] for r in json.load(open(ref_path, encoding="utf-8"))}

    bruto = []
    revisar = []
    total = len(codigos)
    for i, (nome, uf) in enumerate(codigos, 1):
        codigo_ibge = ref.get((nome, uf))
        if not codigo_ibge:
            print(f"[{i}/{total}] {nome}/{uf}: código IBGE não encontrado na referência — pulando")
            continue
        print(f"[{i}/{total}] {nome}/{uf} (IBGE {codigo_ibge})...")
        for chave_ep, path_ep in ENDPOINTS.items():
            params = {"codigoIBGE": codigo_ibge, "ano": args.ano, "itens": 20}
            achados = consultar_endpoint(path_ep, params, api_key, limiter)
            for a in achados:
                a["_endpoint"] = chave_ep
                a["_municipio"] = nome
                a["_uf"] = uf
                bruto.append(a)
                if bate_palavra_chave(a):
                    revisar.append(a)

    # §226: escrita ATÔMICA, como no resto do projeto. Estes dois arquivos ainda escreviam direto
    # no destino — a corrupção de 21/09/2026 (JSON truncado por processo interrompido no meio de
    # uma gravação) podia acontecer aqui do mesmo jeito, e este script roda depois de milhares de
    # requisições, que é exatamente quando uma Action é cancelada por tempo.
    gravar("transferencias_api_raw.json", bruto)
    gravar("transferencias_revisar.json", revisar)

    print(f"\nConcluído. {len(bruto)} registros brutos salvos em data/transferencias_api_raw.json")
    print(f"{len(revisar)} registros relevantes (palavras-chave) salvos em data/transferencias_revisar.json")
    print("\nPRÓXIMO PASSO (manual, obrigatório):")
    print("  Revise data/transferencias_revisar.json e só então incorpore as linhas")
    print("  aprovadas em data/transferencias.json e/ou data/municipios.json,")
    print("  seguindo o vocabulário controlado e as regras de fonte do README.")


class _RespostaFalsa:
    """O mínimo que `consultar_endpoint` usa de uma resposta do `requests`."""

    def __init__(self, status, corpo=None):
        self.status_code, self._corpo = status, corpo if corpo is not None else []
        self.text = "" if corpo is None else str(corpo)

    def json(self):
        return self._corpo


def _limitador_mudo():
    class _L:
        def esperar(self):
            pass
    return _L()


def autoteste() -> int:
    """26/09/2026 (§226): este coletor estava no pipeline SEM autoteste e sem portão — o único
    assim entre os que pedem rede. Os quatro testes abaixo travam justamente os defeitos que o
    §226 corrigiu, porque é para lá que o código volta se alguém "simplificar" a função."""
    from coletores_base import rodar_autoteste

    def t1():
        """504 transitório: espera, repete, e ENTREGA. Nada de município perdido por gateway."""
        respostas = [_RespostaFalsa(504), _RespostaFalsa(504), _RespostaFalsa(200, [{"a": 1}])]
        esperas, lacunas = [], []
        r = consultar_endpoint("/convenios", {"codigoIBGE": "3106200", "ano": 2026, "itens": 20},
                               "k", _limitador_mudo(), pedir_fn=lambda u: respostas.pop(0),
                               dormir=esperas.append, lacuna_fn=lambda *a, **k: lacunas.append(a))
        return r == [{"a": 1}] and esperas == [5, 15] and not lacunas

    def t2():
        """504 persistente: desiste DECLARANDO a lacuna, com o código e o município. Sem lacuna,
        o município ficaria indistinguível de um que não tem convênio."""
        esperas, lacunas = [], []
        r = consultar_endpoint("/convenios", {"codigoIBGE": "3106200", "ano": 2026, "itens": 20},
                               "k", _limitador_mudo(), pedir_fn=lambda u: _RespostaFalsa(504),
                               dormir=esperas.append,
                               lacuna_fn=lambda *a, **k: lacunas.append((a, k)))
        return (r == [] and esperas == [5, 15] and len(lacunas) == 1
                and "504" in lacunas[0][0][1] and "3106200" in lacunas[0][0][1])

    def t3():
        """429 termina. A versão anterior dava `continue` sem consumir tentativa: laço infinito
        diante de um limite de taxa persistente."""
        esperas, lacunas = [], []
        pedidos = []

        def pedir(u):
            pedidos.append(u)
            if len(pedidos) > 20:
                raise AssertionError("laço infinito no 429")
            return _RespostaFalsa(429)

        consultar_endpoint("/convenios", {"codigoIBGE": "1", "ano": 2026, "itens": 20}, "k",
                           _limitador_mudo(), pedir_fn=pedir, dormir=esperas.append,
                           lacuna_fn=lambda *a, **k: lacunas.append(a))
        return esperas == [30] and len(pedidos) == 2 and len(lacunas) == 1

    def t4():
        """Negativo: 404 não repete e não dorme. Consulta errada não melhora com repetição, e
        repetir dobraria a carga sobre uma API pública."""
        pedidos, esperas, lacunas = [], [], []
        consultar_endpoint("/convenios", {"codigoIBGE": "1", "ano": 2026, "itens": 20}, "k",
                           _limitador_mudo(),
                           pedir_fn=lambda u: (pedidos.append(u), _RespostaFalsa(404))[1],
                           dormir=esperas.append, lacuna_fn=lambda *a, **k: lacunas.append(a))
        return len(pedidos) == 1 and not esperas and len(lacunas) == 1

    def t5():
        """A palavra-chave continua filtrando: convênio de defesa civil entra na fila de revisão,
        convênio de pavimentação não. A fila é humana (R7) — este coletor nunca publica sozinho."""
        return (bate_palavra_chave({"objeto": "Apoio à DEFESA CIVIL municipal na estiagem"})
                and not bate_palavra_chave({"objeto": "Pavimentação asfáltica de vias urbanas"}))

    return rodar_autoteste({
        "504 transitório: espera, repete e entrega (município não se perde)": t1,
        "504 persistente: desiste DECLARANDO a lacuna com código e município": t2,
        "429 termina — a versão anterior era laço infinito": t3,
        "negativo: 404 não repete e não dorme": t4,
        "palavra-chave filtra o que vai à revisão humana": t5,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    main()
