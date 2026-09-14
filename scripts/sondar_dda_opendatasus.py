#!/usr/bin/env python3
"""Sonda pontual (14/09/2026): item 1 do §5 das instruções — Doenças Diarreicas
Agudas (DDA). O catálogo (`data/saude_desfechos/catalogo.json`, id `dda`) aponta
"OpenDataSUS (Sivep-DDA: agregado semanal por município)" como fonte aberta, mas
a fonte NUNCA foi aberta pelo projeto. Regra da casa: abrir a fonte primeiro,
ver o formato real, só então escrever coletor.

O que esta sonda faz (só mede, não coleta nem grava nada em data/):
  1. consulta a API CKAN do OpenDataSUS (package_search) por termos ligados a
     DDA e, de carona, leptospirose (item 2 do §5, mesma API, custo zero);
  2. para cada dataset encontrado, lista os recursos (nome, formato, URL,
     última modificação, tamanho);
  3. para os recursos CSV, lê só o começo (Range: bytes=0-8191) e mostra o
     cabeçalho e as 3 primeiras linhas — o suficiente para saber grão
     (município? UF? semana?), colunas e separador, sem baixar arquivos
     grandes.

Roda do runner do Actions (rede real; `opendatasus.saude.gov.br` é bloqueado
no sandbox de edição — 403 host_not_allowed, medido em 14/09/2026).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
# 14/09/2026 (2ª rodada): opendatasus.saude.gov.br redireciona para o portal novo dadosabertos.saude.gov.br
# (Next.js, busca só por JS). Pelos caminhos de imagem do portal, o CKAN de bastidor é ckan-dadosabertos.saude.gov.br,
# e há uma "API de Dados Abertos" em apidadosabertos.saude.gov.br. Testa os candidatos em ordem e usa o primeiro que
# devolver JSON de CKAN; registra o que cada um respondeu.
BASES = ["https://ckan-dadosabertos.saude.gov.br", "https://dadosabertos.saude.gov.br", "https://opendatasus.saude.gov.br"]
BASE = BASES[0]
API_NOVA = "https://apidadosabertos.saude.gov.br"
TERMOS = [
    ("sinan", "sinan"),
    ("dda", "diarreica"),
    ("dda", "diarréicas"),
    ("dda", "sivep-dda"),
    ("dda", "DDA"),
    ("lepto", "leptospirose"),
]
CABECALHO_BYTES = 8191


def _get(url: str, timeout: int = 40, cabecalhos: dict | None = None) -> dict:
    h = {"User-Agent": UA}
    if cabecalhos:
        h.update(cabecalhos)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            corpo = resp.read()
            return {
                "status": resp.status,
                "tipo": resp.headers.get("Content-Type", ""),
                "tamanho_declarado": resp.headers.get("Content-Length") or resp.headers.get("Content-Range"),
                "_corpo": corpo,
            }
    except urllib.error.HTTPError as e:
        return {"erro": "HTTPError", "status": e.code, "motivo": str(e)}
    except urllib.error.URLError as e:
        return {"erro": "URLError", "motivo": str(e.reason)}
    except Exception as e:  # noqa: BLE001 — sonda: qualquer falha é resultado a registrar
        return {"erro": type(e).__name__, "motivo": str(e)}


def buscar_pacotes(termo: str) -> list[dict]:
    url = f"{BASE}/api/3/action/package_search?" + urllib.parse.urlencode({"q": termo, "rows": 20})
    r = _get(url)
    if "erro" in r:
        print(f"   !! package_search({termo!r}): {r}")
        return []
    try:
        dados = json.loads(r["_corpo"])
    except json.JSONDecodeError:
        print(f"   !! package_search({termo!r}): resposta não é JSON — início: {r['_corpo'][:200]!r}")
        return []
    if not dados.get("success"):
        print(f"   !! package_search({termo!r}): success=false — {dados.get('error')}")
        return []
    return dados["result"].get("results", [])


def espiar_csv(url: str) -> None:
    r = _get(url, cabecalhos={"Range": f"bytes=0-{CABECALHO_BYTES}"})
    if "erro" in r:
        print(f"        !! não consegui ler o começo: {r}")
        return
    texto = r["_corpo"].decode("utf-8", "replace")
    if texto.startswith("\ufeff"):
        texto = texto[1:]
    linhas = texto.splitlines()
    print(f"        status={r['status']} tipo={r['tipo']!r} range={r['tamanho_declarado']!r}")
    if not linhas:
        print("        (corpo vazio)")
        return
    cab = linhas[0]
    sep = max([";", ",", "\t", "|"], key=cab.count)
    print(f"        separador provável: {sep!r} · {cab.count(sep) + 1} coluna(s)")
    print(f"        cabeçalho: {cab[:600]}")
    for ln in linhas[1:4]:
        print(f"        linha: {ln[:400]}")


def main() -> int:
    print("=== SONDA DDA / LEPTOSPIROSE — OpenDataSUS (CKAN) — 14/09/2026 ===")
    print("Nada é coletado nem gravado; só medição do que a fonte devolve de verdade.\n")

    # 0. qual host responde como CKAN de verdade (JSON com "success")?
    global BASE
    escolhido = None
    for b in BASES:
        r = _get(f"{b}/api/3/action/site_read")
        resumo = {k: v for k, v in r.items() if k != "_corpo"}
        corpo = r.get("_corpo", b"")
        eh_json = corpo[:1] == b"{"
        print(f"-- {b}/api/3/action/site_read → {resumo} · JSON={eh_json}")
        if eh_json and not escolhido:
            escolhido = b
    for u in (f"{API_NOVA}/", f"{API_NOVA}/docs", f"{API_NOVA}/openapi.json", f"{API_NOVA}/swagger.json"):
        r = _get(u, timeout=30)
        print(f"-- {u} → {({k: v for k, v in r.items() if k != '_corpo'})} · início={r.get('_corpo', b'')[:160]!r}")
    if not escolhido:
        print("!! Nenhum host respondeu como CKAN; nada a sondar além disto.")
        return 1
    BASE = escolhido
    print(f"\n→ CKAN escolhido: {BASE}")

    vistos: dict[str, dict] = {}
    for tema, termo in TERMOS:
        print(f"\n-- busca [{tema}] q={termo!r}")
        for p in buscar_pacotes(termo):
            nome = p.get("name")
            if nome in vistos:
                print(f"   (já visto) {nome}")
                continue
            vistos[nome] = p
            org = (p.get("organization") or {}).get("title")
            print(f"   • {nome} — {p.get('title')!r} · org={org!r} · modificado={p.get('metadata_modified')}")
            print(f"     recursos: {len(p.get('resources', []))}")

    if not vistos:
        print("\n!! Nenhum dataset encontrado para nenhum termo — verificar se a busca precisa de outro vocabulário.")
        return 1

    print("\n=== RECURSOS DOS DATASETS ENCONTRADOS ===")
    for nome, p in vistos.items():
        print(f"\n## {nome} — {p.get('title')}")
        for res in p.get("resources", []):
            fmt = (res.get("format") or "").upper()
            print(f"   - [{fmt or '?'}] {res.get('name')!r}")
            print(f"     url={res.get('url')}")
            print(f"     modificado={res.get('last_modified')} · criado={res.get('created')} · tamanho={res.get('size')}")
            if fmt in {"CSV", "TXT"} or str(res.get("url", "")).lower().endswith((".csv", ".csv.gz", ".txt")):
                if str(res.get("url", "")).lower().endswith(".gz"):
                    print("        (comprimido .gz — o cabeçalho não é legível em texto; um coletor terá de descompactar)")
                else:
                    espiar_csv(res["url"])

    print("\n→ sonda concluída (só leitura).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
