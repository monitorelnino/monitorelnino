#!/usr/bin/env python3
"""Sonda pontual (14/09/2026), 2ª etapa do item 1 do §5 — DDA.

Resultado da 1ª etapa (sondar_dda_opendatasus.py, relatório
2026-09-14_101822_dda_opendatasus.txt): o OpenDataSUS deixou de ser CKAN
(`/api/3/...` devolve HTML de um portal Next.js) e, pelo que se acha por fora,
NÃO hospeda o Sivep-DDA — o catálogo dizia "OpenDataSUS (Sivep-DDA)" sem prova.

O que existe de fato: a resposta do Ministério da Saúde a um pedido LAI
(processo 25072.030308202612) redistribuída no Zenodo por Raphael Saldanha
(Fiocruz / Observatório de Clima e Saúde), CC BY 4.0, com MD5 publicado,
codebook e manifesto. Depósito 2025-2026 (preliminar, "atualizado
mensalmente"): DOI 10.5281/zenodo.20752301. Grão declarado: agregado SEMANAL
por MUNICÍPIO — o mesmo do painel amostral de dengue.

Esta sonda só mede (nada em data/): resolve a versão mais recente pela API
do Zenodo, baixa o CSV de 2026 e o codebook, confere o MD5 contra o
publicado, e mostra colunas, primeiras linhas, faixa de semanas e quantos
dos municípios do painel aparecem. Com isso o coletor é escrito com prova.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
RECORD_ID = "20752301"
API = f"https://zenodo.org/api/records/{RECORD_ID}"
QUERO = ("sivep_dda_2026_csv.zip", "sivep_dda_metadata_csv.zip")
RAIZ = Path(__file__).resolve().parent.parent


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def municipios_do_painel() -> set[str]:
    """Códigos IBGE (7 dígitos) dos municípios que o painel de dengue acompanha."""
    for cand in ("data/saude_desfechos/serie_painel.json", "data/saude_desfechos/completude.json"):
        p = RAIZ / cand
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cods: set[str] = set()

        def _walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(k, str) and k.isdigit() and len(k) == 7:
                        cods.add(k)
                    _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)

        _walk(d)
        if cods:
            print(f"   (municípios do painel lidos de {cand}: {len(cods)})")
            return cods
    print("   (não achei os códigos do painel — a comparação por município fica de fora)")
    return set()


def main() -> int:
    print("=== SONDA DDA — Zenodo (Sivep-DDA via LAI, Saldanha/Fiocruz) — 14/09/2026 ===")
    print("Nada é gravado em data/; só leitura e medição.\n")
    try:
        rec = json.loads(_get(API))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"!! API do Zenodo não respondeu como JSON: {e}")
        return 1
    print(f"-- registro {RECORD_ID}: {rec.get('metadata', {}).get('title')!r}")
    print(f"   publicado={rec.get('metadata', {}).get('publication_date')} · versão={rec.get('metadata', {}).get('version')}")
    print(f"   licença={rec.get('metadata', {}).get('license', {}).get('id')} · latest={rec.get('links', {}).get('latest')}")
    if rec.get("links", {}).get("latest_html") and rec["links"]["latest_html"].rstrip("/").split("/")[-1] != RECORD_ID:
        print(f"   !! existe versão mais nova: {rec['links']['latest_html']} — o coletor deve seguir 'latest'")
    arquivos = {f["key"]: f for f in rec.get("files", [])}
    print(f"   arquivos ({len(arquivos)}): {sorted(arquivos)}")

    for nome in QUERO:
        f = arquivos.get(nome)
        if not f:
            print(f"\n!! {nome} não está no registro")
            continue
        url = f["links"]["self"]
        md5_pub = (f.get("checksum") or "").replace("md5:", "")
        print(f"\n## {nome} · {f.get('size')} bytes · md5 publicado={md5_pub}")
        try:
            corpo = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"   !! download falhou: {e}")
            continue
        md5 = hashlib.md5(corpo).hexdigest()
        print(f"   md5 calculado={md5} → {'OK' if md5 == md5_pub else '!! DIFERENTE'}")
        try:
            z = zipfile.ZipFile(io.BytesIO(corpo))
        except zipfile.BadZipFile:
            print("   !! não é zip")
            continue
        for zi in z.infolist():
            print(f"   - {zi.filename} ({zi.file_size} bytes)")
            if not zi.filename.lower().endswith((".csv", ".txt", ".md")):
                continue
            texto = z.read(zi).decode("utf-8", "replace")
            if "metadata" in nome:
                print("     --- conteúdo (até 4000 chars) ---")
                print("     " + texto[:4000].replace("\n", "\n     "))
                continue
            linhas = texto.splitlines()
            cab = linhas[0] if linhas else ""
            sep = max([",", ";", "\t", "|"], key=cab.count)
            print(f"     separador={sep!r} · colunas={cab.count(sep) + 1} · linhas={len(linhas) - 1}")
            print(f"     cabeçalho: {cab}")
            for ln in linhas[1:4]:
                print(f"     linha: {ln[:300]}")
            # métricas por coluna candidata (semana/ano/município) sem adivinhar nome: mostra os
            # valores distintos das colunas de baixa cardinalidade e a cardinalidade das demais
            rd = csv.DictReader(io.StringIO(texto), delimiter=sep)
            cols = rd.fieldnames or []
            dist: dict[str, set] = {c: set() for c in cols}
            n = 0
            for row in rd:
                n += 1
                for c in cols:
                    if len(dist[c]) <= 60:
                        dist[c].add(row.get(c, ""))
            print(f"     registros lidos: {n}")
            for c in cols:
                v = dist[c]
                if len(v) <= 60:
                    print(f"     · {c}: {len(v)} valor(es) → {sorted(v, key=str)[:60]}")
                else:
                    print(f"     · {c}: >60 valores distintos")
            painel = municipios_do_painel()
            if painel:
                for c in cols:
                    if len(dist[c]) > 60:
                        rd2 = csv.DictReader(io.StringIO(texto), delimiter=sep)
                        vals = {row.get(c, "") for row in rd2}
                        inter = painel & vals
                        inter6 = {p[:6] for p in painel} & vals
                        if inter or inter6:
                            print(f"     · coluna {c!r} bate com o painel: 7 dígitos={len(inter)} · 6 dígitos={len(inter6)} de {len(painel)}")
    print("\n→ sonda concluída (só leitura).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
