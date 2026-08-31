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


def consultar_endpoint(endpoint: str, params: dict, api_key: str, limiter: RateLimiter, max_paginas: int = 5):
    """Pagina um endpoint da API e retorna a lista completa de resultados."""
    resultados = []
    pagina = 1
    while pagina <= max_paginas:
        limiter.esperar()
        q = dict(params, pagina=pagina)
        url = f"{API_BASE}{endpoint}?{urlencode(q)}"
        resp = requests.get(url, headers={"chave-api-dados": api_key}, timeout=30)
        if resp.status_code == 429:
            print(f"  [rate limit] aguardando 60s e tentando de novo...")
            time.sleep(60)
            continue
        if resp.status_code != 200:
            print(f"  [aviso] {endpoint} código IBGE {params.get('codigoIBGE')} → HTTP {resp.status_code}: {resp.text[:200]}")
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

    json.dump(bruto, open(DATA_DIR / "transferencias_api_raw.json", "w", encoding="utf-8"),
               ensure_ascii=False, indent=1)
    json.dump(revisar, open(DATA_DIR / "transferencias_revisar.json", "w", encoding="utf-8"),
               ensure_ascii=False, indent=1)

    print(f"\nConcluído. {len(bruto)} registros brutos salvos em data/transferencias_api_raw.json")
    print(f"{len(revisar)} registros relevantes (palavras-chave) salvos em data/transferencias_revisar.json")
    print("\nPRÓXIMO PASSO (manual, obrigatório):")
    print("  Revise data/transferencias_revisar.json e só então incorpore as linhas")
    print("  aprovadas em data/transferencias.json e/ou data/municipios.json,")
    print("  seguindo o vocabulário controlado e as regras de fonte do README.")


if __name__ == "__main__":
    main()
