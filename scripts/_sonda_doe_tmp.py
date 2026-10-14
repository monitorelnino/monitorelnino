"""Sonda temporária (ramo diag): domínio oficial municipal e busca WordPress, amostra de 40."""
import sys, json, re, unicodedata, urllib.parse, random
sys.path.insert(0, ".")
from coletores_base import buscar, referencia_ibge, ler
import coletar_diarios_municipais as cdm
def slug(n):
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", n)
por, _ = referencia_ibge()
ordem = cdm.ordem_prioridade(por, ler("cadastro_prioritarios.json", {}) or {}, ler("populacao_censo2022.json", {}) or {})
random.seed(14); amostra = ordem[:20] + random.sample(ordem[20:], 20)
tot = {"dominio": 0, "wp": 0, "pdf_plano": 0}
for c in amostra:
    r = por[c]; s, uf = slug(r["nome"]), r["uf"].lower()
    achou = None
    for d in (f"www.{s}.{uf}.gov.br", f"{s}.{uf}.gov.br", f"www.prefeitura{s}.{uf}.gov.br", f"prefeitura{s}.{uf}.gov.br", f"pm{s}.{uf}.gov.br"):
        try:
            b = buscar(f"https://{d}/", timeout=15); achou = (d, len(b)); break
        except Exception as e:
            ultimo = f"{type(e).__name__}"
    linha = {"mun": f"{r['nome']}/{r['uf']}", "dominio": achou[0] if achou else None}
    if achou:
        tot["dominio"] += 1
        try:
            j = json.loads(buscar(f"https://{achou[0]}/wp-json/wp/v2/media?search={urllib.parse.quote('plano de contingência')}&mime_type=application/pdf&per_page=10", timeout=20))
            if isinstance(j, list):
                tot["wp"] += 1; linha["wp"] = len(j)
                pdfs = [x.get("source_url") for x in j if "conting" in (x.get("source_url") or "").lower() + str((x.get("title") or {}).get("rendered") or "").lower()]
                if pdfs: tot["pdf_plano"] += 1; linha["pdfs"] = pdfs[:3]
        except Exception as e:
            linha["wp_erro"] = type(e).__name__
    print(json.dumps(linha, ensure_ascii=False))
print("TOTAL", json.dumps(tot), "de", len(amostra))
