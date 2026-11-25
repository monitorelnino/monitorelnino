"""Diagnóstico da auditoria de 25/11/2026 (não vai à main): atos do DOU que autorizam transferência de recursos de
defesa civil, pelas redações "Autoriza a transferência de recursos" (a que o coletor consulta) e "Autoriza o empenho e a
transferência de recursos" (a que ele não consulta). Só leitura: município, UF, valor e ação de cada ato, por redação.
Uso: python3 diag_portarias_recursos.py 2026-04-26 2026-11-23"""
import datetime
import json
import pathlib
import re
import sys

import coletar_recursos_resposta as c
from coletores_base import buscar, varrer_busca_dou

de, ate = (datetime.date.fromisoformat(x) for x in sys.argv[1:3])
CONSULTAS = {
    "transferencia": '"Autoriza a transferência de recursos"',
    "empenho_e_transferencia": '"Autoriza o empenho e a transferência de recursos"',
    "empenho_e_a_transferencia": '"empenho e a transferência de recursos"',
}
RE_MUN_SOLTO = re.compile(r"[Mm]unic[íi]pio de\s+([^,/()]{2,60}?)\s*(?:/|-|–|\()\s*([A-Z]{2})\b")
RE_ESTADO = re.compile(r"\bao Estado d[oae]\s+([A-ZÀ-Ú][^,/()]{2,40})")
RE_VALOR_SOLTO = re.compile(r"R\$\s*([\d.]+,\d{2})")
saida = {"de": de.isoformat(), "ate": ate.isoformat(), "consultas": {}, "atos": [], "falhas": {}}
vistos = {}
for nome, q in CONSULTAS.items():
    try:
        itens, incompletas = varrer_busca_dou(q, de, ate)
    except Exception as e:  # noqa: BLE001
        saida["falhas"][nome] = f"{type(e).__name__}: {str(e)[:200]}"
        print(nome, "FALHA", saida["falhas"][nome], flush=True)
        continue
    saida["consultas"][nome] = {"q": q, "n": len(itens), "incompletas": incompletas, "urls": [it["url"] for it in itens]}
    print(nome, len(itens), "itens;", len(incompletas), "janelas incompletas", flush=True)
    for it in itens:
        vistos.setdefault(it["url"], it)
for n, (url, it) in enumerate(vistos.items(), 1):
    reg = {"url": url, "titulo": it.get("titulo"), "data_pub": it.get("data"), "orgao": it.get("orgao"),
           "trecho": it.get("trecho"),
           "redacao": [k for k, v in saida["consultas"].items() if url in v["urls"]]}
    if not re.search(r"Defesa Civil", (it.get("orgao") or "") + " " + (it.get("trecho") or ""), re.I):
        reg["nao_aberto"] = "órgão e trecho sem 'Defesa Civil'"
        saida["atos"].append(reg)
        continue
    try:
        texto = c.texto_limpo(buscar(url, timeout=90, origem="coletar_recursos_resposta"))
    except Exception as e:  # noqa: BLE001
        reg["erro"] = f"{type(e).__name__}: {str(e)[:160]}"
        saida["atos"].append(reg)
        continue
    reg["lido_pelo_coletor"] = c.ler_ato(texto, url)
    reg["portaria_e_data"] = [str(x) for x in c.portaria_e_data(texto, url)]
    reg["municipios_no_texto"] = [[re.sub(r"\s+", " ", m.group(1)).strip(), m.group(2)] for m in RE_MUN_SOLTO.finditer(texto)][:6]
    reg["estado_no_texto"] = [m.group(1).strip() for m in RE_ESTADO.finditer(texto)][:3]
    reg["valores_no_texto"] = RE_VALOR_SOLTO.findall(texto)[:6]
    reg["acao"] = list(c.acao_de(texto))
    reg["prorrogacao"] = bool(c.RE_PRORROGACAO.search(texto))
    i = texto.find("Art. 1")
    reg["art1"] = texto[i:i + 700] if i >= 0 else None
    j = texto.upper().find("PORTARIA")
    reg["ementa"] = texto[j:j + 420] if j >= 0 else None
    saida["atos"].append(reg)
    if n % 25 == 0:
        print(n, "de", len(vistos), flush=True)
pathlib.Path("data/relatorio_rs").mkdir(exist_ok=True)
json.dump(saida, open(f"data/relatorio_rs/diag_portarias_{de.isoformat()}_{ate.isoformat()}.json", "w"), ensure_ascii=False)
print("gravado:", len(saida["atos"]), "atos", flush=True)
