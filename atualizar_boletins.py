#!/usr/bin/env python3
"""Vigia de boletins do Painel El Niño 2026-2027.
Consulta as páginas oficiais (CEMADEN e INPE), detecta o número de boletim mais
recente mencionado e compara com data/boletins.json. Falha de rede não interrompe
o pipeline (aviso e saída 0); um boletim novo atualiza o registro e sinaliza no log.
"""
import json, re, sys, urllib.request

PAGINAS = [
    "https://www.gov.br/cemaden/pt-br",
    "https://www.gov.br/inpe/pt-br/assuntos/ultimas-noticias",
]
REGISTRO = "data/boletins.json"

def maior_boletim(html: str) -> int:
    """Extrai do HTML o maior número de boletim mencionado, testando dois padrões de menção (texto 'Boletim nº N' e slug 'PainelElNinoN')."""
    numeros = [int(n) for n in re.findall(r"[Bb]oletim\s*(?:n[ºo°.]?\s*)?(\d{1,2})\b", html)]
    extra = [int(n) for n in re.findall(r"PainelElNino(\d{1,2})", html)]
    return max(numeros + extra, default=0)

def main() -> int:
    """Consulta as páginas oficiais, compara com o último boletim registrado e atualiza data/boletins.json se houver boletim mais recente."""
    try:
        atual = json.load(open(REGISTRO, encoding="utf-8"))
    except FileNotFoundError:
        atual = {"ultimo_boletim": 2}
    detectado = 0
    for url in PAGINAS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MonitorElNinoBrasil/1.0"})
            html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
            detectado = max(detectado, maior_boletim(html))
        except Exception as e:
            print(f"[aviso] não foi possível consultar {url}: {e}")
    if detectado > atual.get("ultimo_boletim", 0):
        print(f"[NOVO BOLETIM] nº {detectado} detectado (registro anterior: nº {atual['ultimo_boletim']}).")
        print("  → Revisar o painel 'Risco projetado × instrumento estadual' e a timeline contra o novo boletim.")
        atual["ultimo_boletim"] = detectado
        json.dump(atual, open(REGISTRO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    else:
        print(f"Nenhum boletim novo (último conhecido: nº {atual.get('ultimo_boletim')}).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
