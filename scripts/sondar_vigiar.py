#!/usr/bin/env python3
"""Sonda do Painel VIGIAR (MS/SVSA/CNIE), 26/10/2026: só mede, não grava em data/.

Mede, do runner do Actions (rede real): status e tamanho da página oficial; robots.txt do host
(Crawl-delay e Disallow para o caminho); presença de referência a Power BI (`powerbi`,
`querydata`, `public/reports`) no HTML e nos scripts linkados; e uma consulta GET ao endpoint de
relatório público (sem credencial). Cliente identificado. Recusa (401/403/429/451) é registrada
como recusa, nunca contornada.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
PAGINA = ("https://www.gov.br/saude/pt-br/composicao/svsa/cnie/"
          "painel-de-poluicao-atmosferica-e-saude-humana")


def pedir(url: str, metodo: str = "GET", corpo: bytes | None = None, limite: int = 2_000_000):
    req = urllib.request.Request(url, data=corpo, method=metodo, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            dados = r.read(limite)
            return r.status, dict(r.headers), dados
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read(4000)
    except Exception as e:  # rede, TLS, DNS
        return None, {}, repr(e).encode()[:300]


def sondar_modelo(rel: str) -> None:
    """GET `modelsAndExploration` do relatório público (o pedido que o navegador faz ao abrir a vista).

    Só mede: imprime id do modelo, seções e, por visual, o tipo e as entidades/propriedades da consulta
    (`prototypeQuery`). Sem POST. O token `r=` é o JSON {k: chave do recurso, t: tenant, c: cluster}.
    """
    import base64
    import json
    tok = rel.split("r=", 1)[1]
    try:
        info = json.loads(base64.b64decode(tok + "=" * (-len(tok) % 4)))
    except Exception as e:
        print("  TOKEN ilegível:", repr(e)[:120])
        return
    print("  token chaves:", sorted(info.keys()), "c=", info.get("c"))
    chave = info.get("k")
    for host in ("wabi-brazil-south-b-primary-redirect.analysis.windows.net",):
        url = f"https://{host}/public/reports/{chave}/modelsAndExploration?preferReadOnlySession=true"
        req = urllib.request.Request(url, headers={"User-Agent": UA, "X-PowerBI-ResourceKey": chave,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                dados = r.read(8_000_000)
                st = r.status
        except urllib.error.HTTPError as e:
            print(f"MODELS status={e.code} corpo={e.read(300)!r}")
            continue
        except Exception as e:
            print("MODELS erro", repr(e)[:200])
            continue
        print(f"MODELS status={st} bytes={len(dados)}")
        try:
            j = json.loads(dados)
        except Exception as e:
            print("  MODELS não é JSON:", repr(e)[:100], dados[:200])
            continue
        print("  chaves:", sorted(j.keys()))
        for m in j.get("models", [])[:5]:
            print("  modelo:", {k: m.get(k) for k in ("id", "dbName", "displayName")})
        expl = j.get("exploration") or {}
        print("  exploration chaves:", sorted(expl.keys()))
        cfg = expl.get("report") or expl
        secoes = cfg.get("sections") or []
        print("  seções:", len(secoes))
        for sec in secoes[:12]:
            print("   seção", sec.get("displayName") or sec.get("name"), "visuais:", len(sec.get("visualContainers", [])))
            for vc in sec.get("visualContainers", [])[:40]:
                try:
                    c = json.loads(vc.get("config") or "{}")
                except Exception:
                    continue
                sv = c.get("singleVisual") or {}
                pq = sv.get("prototypeQuery") or {}
                tabs = {f.get("Name"): f.get("Entity") for f in pq.get("From", [])}
                sel = [s.get("Name") for s in pq.get("Select", [])][:12]
                print("     ", sv.get("visualType"), tabs, sel)


def main() -> int:
    st, h, corpo = pedir(PAGINA)
    print(f"PAGINA status={st} bytes={len(corpo)} ctype={h.get('Content-Type')}")
    texto = corpo.decode("utf-8", "replace") if corpo else ""
    for chave in ("powerbi", "querydata", "public/reports", "app.powerbi.com", "Última atualização", "Dados até"):
        print(f"  ref {chave!r}: {texto.count(chave)}")
    scripts = re.findall(r'src="([^"]+\.js[^"]*)"', texto)[:12]
    links = sorted(set(re.findall(r'https?://[^"\'\s<>]*(?:powerbi|querydata|public/reports)[^"\'\s<>]*', texto)))[:10]
    print("  scripts:", len(scripts), "links_powerbi:", links)

    host = urllib.parse.urlsplit(PAGINA)
    st, h, rb = pedir(f"{host.scheme}://{host.netloc}/robots.txt")
    print(f"ROBOTS {host.netloc} status={st} bytes={len(rb)}")
    if st == 200:
        linhas = rb.decode("utf-8", "replace").splitlines()
        for ln in linhas:
            if re.match(r"(?i)\s*(crawl-delay|disallow|user-agent)", ln) and len(ln) < 160:
                print("   ", ln.strip())

    for url in ("https://dadosabertos.saude.gov.br/robots.txt",):
        st, _, rb = pedir(url)
        print(f"ROBOTS {url} status={st} crawl_delay={'crawl-delay' in rb.decode('utf-8','replace').lower() if st==200 else '-'}")

    rel = None
    m = re.search(r"https://app\.powerbi\.com/view\?r=([A-Za-z0-9_\-=]+)", texto)
    if m:
        rel = m.group(0)
        st, _, vista = pedir(rel, limite=3_000_000)
        vt = vista.decode("utf-8", "replace") if vista else ""
        print(f"POWERBI_VIEW status={st} bytes={len(vista)}")
        clusters = sorted(set(re.findall(r"https://[a-z0-9.\-]+\.analysis\.windows\.net", vt)))[:5]
        print("  clusters:", clusters)
        for chave in ("clusterUrl", "reportId", "modelId", "resourceKey", "exploration", "publicReport"):
            i = vt.find(chave)
            if i >= 0:
                print(f"  {chave} @{i}: {vt[max(0, i - 40):i + 160]!r}")
        for b in sorted(set(re.findall(r"/public/reports/[A-Za-z0-9\-/]+", vt)))[:5]:
            print("  rota:", b)
        sondar_modelo(rel)
    else:
        print("POWERBI_VIEW sem link app.powerbi.com/view na página")
    return 0


if __name__ == "__main__":
    sys.exit(main())
