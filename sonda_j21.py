"""Sonda (não grava em data/): o que muda nos documentos recusados por título quando o cabeçalho corrido conta (J21)."""
import json, sys
import coletores_base as c
from scripts.sondar_documento import texto_de
import juiz
ps = json.load(open("data/pistas_imprensa.json"))["pistas"]
vistos = {}
for p in ps:
    if (p.get("juiz") or {}).get("motivo") == "titulo_nao_e_plano":
        vistos.setdefault(str(p.get("url_final") or p.get("url")), p)
print("ALVOS", len(vistos), flush=True)
for url, p in sorted(vistos.items()):
    try:
        t = texto_de(c.buscar(url, timeout=60, origem="medição da proposta J21"))[1]
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:80], url[-90:], flush=True); continue
    nome, uf = p.get("municipio") or "", p.get("uf") or ""
    if not nome:
        from scripts.municipio_do_dominio import municipio_de
        d = municipio_de(url, camara=True) or {}; nome, uf = d.get("nome", ""), d.get("uf", "")
    a = juiz.julgar(t, nome, uf, ibge=p.get("ibge") or p.get("alvo"), url=url)
    b = juiz.julgar(t, nome, uf, ibge=p.get("ibge") or p.get("alvo"), url=url, propostas=("J21",))
    cab = [l.strip() for l in t.splitlines() if len(l.strip()) <= 80 and juiz.RE_TITULO_DE_PLANO.match(l.strip())]
    print("J21", "MUDA" if (a.get("promove"), a.get("motivo")) != (b.get("promove"), b.get("motivo")) else "igual", "|", nome, uf, "|",
          a.get("motivo"), "→", ("promove " + str(b.get("categoria")) + " " + str(b.get("data"))) if b.get("promove") else b.get("motivo"),
          "| cabeçalhos:", len(cab), repr(cab[0][:60]) if cab else "", "| início:", repr(" ".join(t[:120].split())), "|", url[-80:], flush=True)
