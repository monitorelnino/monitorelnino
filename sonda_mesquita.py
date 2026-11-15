"""Sonda (não grava em data/): a matéria da Prefeitura de Mesquita linka o plano? O que o PDF traz?"""
import hashlib, json, re, sys
import coletores_base as c
from scripts.sondar_documento import texto_de
import juiz

MATERIA = "https://prefeitura.mesquita.rj.gov.br/acoes-preventivas-reduzem-impactos-de-chuvas-fortes-e-vendavais-em-mesquita/"
PDF = "https://transparencia.mesquita.rj.gov.br/ver20240713/tmp/PortalServices/PLANODECONTINGENCIA20252026.pdf"
try:
    h = c.buscar(MATERIA, timeout=40, origem="sonda da indicação de Mesquita").decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="([^"]+)"', h)))
    print("MATÉRIA ok", len(h), "| linka o PDF:", PDF in h, "| links de transparência/pdf:", [l for l in links if "transparencia" in l or l.lower().endswith(".pdf")][:8])
    m = re.search(r"<title>(.*?)</title>", h, re.S); print("MATÉRIA título:", m and m.group(1).strip()[:160])
    d = re.search(r'datetime="([^"]+)"|"datePublished":"([^"]+)"', h); print("MATÉRIA data:", d and (d.group(1) or d.group(2)))
except Exception as e:
    print("MATÉRIA ERRO", type(e).__name__, str(e)[:200])
try:
    b = c.buscar(PDF, timeout=60, origem="sonda da indicação de Mesquita")
except Exception as e:
    print("PDF ERRO", type(e).__name__, str(e)[:200]); sys.exit(0)
print("PDF ok", len(b), "bytes | sha256", hashlib.sha256(b).hexdigest(), "| começa", b[:5])
r = texto_de(b); t = r[0] if isinstance(r, tuple) else r
print("TEXTO", len(t), "caracteres | resto do retorno:", (r[1:] if isinstance(r, tuple) else None))
try:
    from pypdf import PdfReader; import io
    print("PÁGINAS", len(PdfReader(io.BytesIO(b)).pages))
except Exception as e:
    print("PÁGINAS ?", type(e).__name__, e, "| /Count:", re.findall(rb"/Count (\d+)", b)[:3])
print("INÍCIO >>>", re.sub(r"\s+", " ", t[:2200]))
for termo in ("decreto", "portaria", "aprovad", "vigência", "vigencia", "2025/2026", "2025-2026", "2026", "El Niño", "El Nino", "estiagem", "seca", "incêndio", "calor",
              "inundaç", "enxurrada", "alagament", "deslizament", "vendava", "audiência pública", "validação", "Lei 12.608", "Lei nº 12.608"):
    ach = [m.start() for m in re.finditer(re.escape(termo), t, re.I)]
    if ach:
        i = ach[0]; print(f"TERMO {termo!r}: {len(ach)}x | {re.sub(r'\\s+', ' ', t[max(0, i - 110): i + 170])!r}")
    else:
        print(f"TERMO {termo!r}: 0")
for prop in ((), ("J20",)):
    v = juiz.julgar(t, "Mesquita", "RJ", ibge="3302858", url=PDF, propostas=prop)
    print("JUIZ propostas", prop, "→", json.dumps({k: v.get(k) for k in ("promove", "motivo", "categoria", "data", "regra", "sem_ato_de_aprovacao")}, ensure_ascii=False))
    print("   critérios:", json.dumps(v.get("criterios"), ensure_ascii=False)[:1500])
