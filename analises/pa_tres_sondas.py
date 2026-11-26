"""Sonda descartável (relatório do Marajó): quais camadas públicas o TerraBrasilis serve para DETER e área queimada. Nada grava."""
import re, sys
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from coletores_base import buscar
for ws in ("deter-amz", "queimadas", "prodes-legal-amz", "ows"):
    u = f"https://terrabrasilis.dpi.inpe.br/geoserver/{ws}/ows?service=WFS&version=2.0.0&request=GetCapabilities" if ws != "ows" else \
        "https://terrabrasilis.dpi.inpe.br/geoserver/ows?service=WFS&version=2.0.0&request=GetCapabilities"
    try:
        t = buscar(u, timeout=120, origem="coletar_sinais_risco").decode("utf-8", "replace")
        nomes = re.findall(r"<(?:wfs:)?Name>([^<]+)</(?:wfs:)?Name>", t)
        print("==", ws, len(nomes)); print("\n".join(n for n in nomes if ws != "ows" or re.search(r"(?i)queim|aq|burn|fire|deter|fogo|cicatr", n))[:4000])
    except Exception as e:
        print("==", ws, "FALHA", type(e).__name__, str(e)[:200])
for tn in ("deter-amz:deter_amz", "deter-amz:deter_public"):
    try:
        t = buscar(f"https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/ows?service=WFS&version=2.0.0&request=DescribeFeatureType&typeNames={tn}", timeout=120, origem="coletar_sinais_risco").decode("utf-8","replace")
        print("== DESC", tn); print("\n".join(re.findall(r'name="([^"]+)"[^>]*type="([^"]+)"', t) and [f"{a} {b}" for a,b in re.findall(r'name="([^"]+)"[^>]*type="([^"]+)"', t)]))
    except Exception as e:
        print("== DESC", tn, "FALHA", type(e).__name__, str(e)[:200])
