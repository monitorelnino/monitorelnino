"""Sonda descartável: por que o DOU e o MIDR não respondem ao coletor de reconhecimentos. Nada grava."""
import re, sys, urllib.request
sys.path.insert(0, ".")
from coletores_base import buscar
urls = [
 "https://www.in.gov.br/consulta/-/buscar/dou?q=%22reconhece+a+situa%C3%A7%C3%A3o+de+emerg%C3%AAncia%22&s=do1&exactDate=personalizado&sortType=0&publishFrom=20-11-2026&publishTo=27-11-2026",
 "https://www.in.gov.br/consulta/-/buscar/dou?q=%22calamidade+p%C3%BAblica%22&s=do1&exactDate=dia",
 "https://www.in.gov.br/leiturajornal?data=24-11-2026&secao=do1",
 "https://www.gov.br/mdr/pt-br/noticias-midr/RSS",
 "https://www.gov.br/mdr/pt-br/noticias-midr",
 "https://www.gov.br/mdr/pt-br/assuntos/noticias",
 "https://agenciagov.ebc.com.br/noticias/defesa-civil",
]
for u in urls:
    try:
        b = buscar(u, timeout=60, origem="coletar_s2id")
        t = b.decode("utf-8", "replace")
        print("==", u[:110], "OK", len(b))
        print("   títulos:", re.findall(r"<title>(.{0,120})</title>", t)[:3])
        print("   reconhec:", [m[:140] for m in re.findall(r"[^<>]{0,60}[Rr]econhec[^<>]{0,80}", t)][:5])
        print("   amostra links:", re.findall(r'href="([^"]*noticia[^"]*)"', t)[:5])
    except Exception as e:
        print("==", u[:110], "FALHA", type(e).__name__, str(e)[:200])
