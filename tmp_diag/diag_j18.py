"""Diagnóstico de uma rodada (ramo coleta-dia, nunca mesclado): de onde vem o ano 2012 dos PLANCONs do RS."""
import json, re, sys, pathlib
RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
from rejulgar_decisoes_do_juiz import buscar_18
from juiz import ano_do_plano, RE_GATILHO_CICLO, RE_ANO_OU_CICLO
d = json.loads((RAIZ / "data/paralelo_juiz18.json").read_text())["decisoes"]
alvo = ("Nova Pádua", "Mormaço", "Bossoroca", "Tubarão", "Picada Café", "Palmeira das Missões", "Rio dos Índios")
urls = {}
for v in d:
    if v.get("promove") and v.get("municipio") in alvo:
        urls.setdefault(v["municipio"], v["url"])
ler, _ = buscar_18()
for m, u in urls.items():
    t = ler(u) or ""
    print("=====", m, len(t), "ano_do_plano", ano_do_plano(t, 2026))
    g = RE_GATILHO_CICLO.search(t); a = RE_ANO_OU_CICLO.search(t)
    print("gatilho", repr(t[max(0, g.start()-60):g.end()+20]) if g else None)
    print("RE_ANO_OU_CICLO", repr(t[max(0, a.start()-80):a.end()+20]) if a else None)
    for x in re.finditer(r"\b(?:19|20)\d{2}\b", t[:3000]):
        print("  ano", x.group(0), x.start(), repr(t[max(0, x.start()-80):x.end()+15]))
