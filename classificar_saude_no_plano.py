#!/usr/bin/env python3
"""
classificar_saude_no_plano.py — leitura automática de como o plano trata a saúde (§10.1, peça 2; 07/09/2026)
==============================================================================================================
Mesmo desenho do classificador_natureza.py: regras por degrau, sempre com PÁGINA citada. Degraus automáticos:
  1 orgao_listado  — Secretaria de Saúde / SAMU aparecem só em lista de órgãos
  2 resposta       — SAMU, abrigo, atendimento, inspeção sanitária, remoção em TAREFAS
  3 vigilancia_pos — vigilância epidemiológica/ambiental pós-desastre, Vigidesastres
  5 riscos_do_ciclo — onda de calor, fumaça/qualidade do ar, El Niño / ciclo 2026-27 nomeados
Degrau 4 (prevencao_epidemiologica) NUNCA é automático — só na fila, por leitura humana.
Saída: saude_no_plano_auto (maior degrau atingido), pagina_citada, termos, publicada como "leitura automática";
entra na fila R7 (data/saude_no_plano_revisar.json). Peso zero; nunca lida pelo motor.
  python classificar_saude_no_plano.py --autoteste
"""
import json, re, sys, unicodedata
from datetime import date
from pathlib import Path
from coletores_base import ler, gravar, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
ROTULO = {0: "ausente", 1: "orgao_listado", 2: "resposta", 3: "vigilancia_pos", 4: "prevencao_epidemiologica", 5: "riscos_do_ciclo"}

def _plano(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")

REGRAS = {
    1: [r"secretaria (municipal |estadual )?de saude", r"\bsamu\b", r"vigilancia (em )?saude"],
    2: [r"\bsamu\b[^.]{0,120}(atendimento|acionamento|remocao|resgate|socorro)", r"(atendimento|remocao|socorro|inspecao sanitaria|assistencia)[^.]{0,80}(abrigo|desabrigad|feridos|vitimas)",
        r"inspecao sanitaria", r"(equipe|equipes) de saude[^.]{0,80}(abrigo|resposta|atendimento)"],
    3: [r"vigil(a|â)ncia (epidemiologica|ambiental)[^.]{0,120}(pos[- ]desastre|apos o desastre|desastre)", r"vigidesastres", r"acompanhamento epidemiologico[^.]{0,80}(pos|apos)"],
    5: [r"onda(s)? de calor", r"fumaca", r"qualidade do ar", r"\bel ni[nñ]o\b", r"ciclo (do )?el ni[nñ]o"],   # 07/09: "2026/2027" sozinho é rótulo de temporada, não risco do ciclo (falso positivo em Afonso Cláudio)
}
_RX = {d: [re.compile(p) for p in pats] for d, pats in REGRAS.items()}


def classificar(paginas: list) -> dict:
    """Função pura. paginas = [texto_pagina_1, ...]. Devolve {degrau, rotulo, pagina_citada, termos: {degrau: [(pagina, termo)]}}.
    O degrau é o maior atingido entre 1, 2, 3, 5 (4 nunca aqui); 0 se nenhuma menção."""
    termos = {}
    for i, txt in enumerate(paginas, start=1):
        t = _plano(txt)
        for d, rxs in _RX.items():
            for rx in rxs:
                m = rx.search(t)
                if m:
                    termos.setdefault(d, []).append((i, m.group(0)[:60]))
    if not termos:
        return {"degrau": 0, "rotulo": ROTULO[0], "pagina_citada": None, "termos": {}}
    d = max(termos)
    return {"degrau": d, "rotulo": ROTULO[d], "pagina_citada": termos[d][0][0], "termos": {str(k): v[:5] for k, v in termos.items()}}


def rodar() -> int:
    idx = ler("evidencias.json", {"itens": {}}); itens = idx.get("itens") or {}
    saida = ler("saude_no_plano_auto.json", {"_governanca": "Leitura AUTOMÁTICA de como o plano trata a saúde (§10.1): degraus 1/2/3/5 por regra com página citada; degrau 4 nunca automático. Publicada como 'leitura automática'; vira saude_no_plano (confirmada) só pela fila R7 com revisado_por e data. Peso zero; nunca lida pelo motor.", "itens": {}}) or {}
    fila = ler("saude_no_plano_revisar.json", {"_governanca": "Fila R7 (§10.1): pré-classificações automáticas de saude_no_plano aguardando confirmação humana na sessão semanal, a partir do texto já extraído.", "fila": []}) or {}
    n = 0
    for h, it in itens.items():
        ta = it.get("texto_arquivo")
        if not ta or h in (saida.get("itens") or {}):
            continue
        p = RAIZ / ta
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        paginas = [b.split("\n", 1)[1] if "\n" in b else "" for b in re.split(r"\n=== página \d+ ===\n", txt)[1:]] or [txt]
        c = classificar(paginas)
        saida.setdefault("itens", {})[h] = {**c, "url": it.get("url"), "texto_hash": it.get("texto_hash"), "paginas": len(paginas), "classificado_em": date.today().strftime("%d/%m/%Y"), "status": "leitura automática"}
        # divergência com leitura humana já confirmada (mesmo documento): fica marcada para a sessão semanal, nunca resolvida pela máquina
        conf = next((l for l in (ler("saude_no_plano.json", {}) or {}).get("leituras", []) if l.get("hash") and h.startswith(l["hash"])), None)
        div = ({"confirmada": conf.get("categoria"), "automatica": c["degrau"]} if conf and conf.get("categoria") != c["degrau"] else None)
        fila.setdefault("fila", []).append({"hash": h, "url": it.get("url"), "degrau_auto": c["degrau"], "rotulo_auto": c["rotulo"], "pagina_citada": c["pagina_citada"], "entrou_em": date.today().strftime("%d/%m/%Y"), "status": "aguardando revisão", "divergencia": div})
        n += 1
    gravar("saude_no_plano_auto.json", saida); gravar("saude_no_plano_revisar.json", fila)
    print(f"saude_no_plano (auto): {n} documento(s) classificado(s) nesta rodada; {len(fila.get('fila', []))} na fila R7")
    return 0


def autoteste() -> int:
    def t1(): return classificar(["Art. 1º Fica instituído o plano.", "Compõem o sistema: Secretaria de Saúde, SAMU, Defesa Civil."])["degrau"] == 1
    def t2(): c = classificar(["A Vigilância em Saúde fará a inspeção sanitária dos abrigos e o SAMU o atendimento das vítimas."]); return c["degrau"] == 2 and c["pagina_citada"] == 1
    def t3(): c = classificar(["x", "Vigidesastres acompanha a vigilância epidemiológica pós-desastre."]); return c["degrau"] == 3 and c["pagina_citada"] == 2
    def t4(): return classificar(["Cenário do El Niño 2026-2027: ondas de calor e fumaça de queimadas."])["degrau"] == 5 and classificar(["Plano de Contingência 2026/2027."])["degrau"] == 0
    def t5(): return classificar(["Nada sobre o tema."])["degrau"] == 0 and 4 not in REGRAS   # degrau 4 nunca automático
    def t6(): c = classificar(["Secretaria de Saúde na lista.", "Vigidesastres."]); return c["degrau"] == 3 and "1" in c["termos"] and "3" in c["termos"]
    return rodar_autoteste({"1 órgão listado": t1, "2 resposta com página": t2, "3 vigilância pós": t3, "5 riscos do ciclo": t4, "0 ausente e 4 nunca automático": t5, "maior degrau, termos por degrau": t6})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else rodar())
