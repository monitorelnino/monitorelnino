#!/usr/bin/env python3
"""Caderno de leitura das pistas pendentes (não decide nada; só formata para julgamento humano).

Por padrão as pistas C10 (rebaixamento) ficam de fora — rotina de julgamento §5: nunca
misturar com o lote do diário. Para julgá-las, rodar em separado com --origem "rebaixamento C10".
Achados com o mesmo hash_evidencia (o mesmo documento relogado em dias diferentes pela
varredura) aparecem uma única vez, com as datas repetidas anotadas.

Uso:  python3 scripts/caderno_de_pistas.py [--origem querido_diario|imprensa|agencia_oficial|"rebaixamento C10"] [--uf SP] [--n 15]
Saída: caderno_de_pistas_<AAAA-MM-DD>.md na raiz (não versionado; é material de trabalho).
"""
import argparse, datetime, json, os, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PISTAS = RAIZ / "data" / "pistas_imprensa.json"
REF = RAIZ / "data" / "municipios_ibge_referencia.json"
MUN = RAIZ / "data" / "municipios.json"
EVID = RAIZ / "evidencias"
ORDEM = {"candidato_forte": 0, "indefinido": 1, "falso_positivo_provavel": 2}
TERMOS = ["plano de contingência", "situação de emergência", "estado de calamidade",
          "estiagem", "seca", "El Niño", "defesa civil", "comitê"]


def julgada(p):
    """Pista já decidida por humano ou aplicada automaticamente — fica fora do caderno."""
    return bool(p.get("julgamento_humano")) or str(p.get("status", "")).startswith(
        ("aplicada", "descartada", "revertida"))


def deduplicar(pistas):
    """Pistas com o mesmo hash_evidencia são o mesmo achado relogado em dias diferentes
    pela varredura — mantém uma só, a de registrado_em mais antigo, e guarda as datas
    repetidas em '_duplicatas' para aviso no caderno."""
    por_hash, sem_hash = {}, []
    for x in pistas:
        h = x.get("hash_evidencia")
        if h:
            por_hash.setdefault(h, []).append(x)
        else:
            sem_hash.append(x)
    saida = list(sem_hash)
    for grupo in por_hash.values():
        grupo.sort(key=lambda x: x.get("registrado_em") or "")
        principal = dict(grupo[0])
        if len(grupo) > 1:
            principal["_duplicatas"] = [g.get("registrado_em") for g in grupo[1:]]
        saida.append(principal)
    return saida


def destacar(trecho):
    """Marca os termos vigiados em **negrito**, para o olho achar o motivo do achado."""
    for t in TERMOS:
        trecho = re.sub(f"({re.escape(t)})", r"**\1**", trecho, flags=re.I)
    return " ".join(trecho.split())


def linha_evidencia(ev, disco):
    """Mostra o que existe de verdade no disco para este hash — nunca assume extensão.
    Prioridade: .txt (texto integral) > qualquer captura (.json/.html) > nada."""
    arqs = sorted(disco.get(ev, []))
    if not ev or not arqs:
        return "**não preservada** — preservar antes de promover"
    if f"{ev}.txt" in arqs:
        return f"`evidencias/{ev}.txt` (texto integral — dá para ler o documento inteiro offline)"
    return (f"`evidencias/{arqs[0]}` — **só excerto/captura; texto integral pendente** "
            f"(Action \u201cPreservar textos integrais das evidências\u201d)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origem", default=None,
                    help='querido_diario | imprensa | agencia_oficial | "rebaixamento C10" '
                         '(só entra se pedido explicitamente) | vazio = todas menos C10')
    ap.add_argument("--uf", default=None)
    ap.add_argument("--n", type=int, default=15, help="tamanho do lote (padrão 15)")
    a = ap.parse_args()

    fila = deduplicar(json.load(open(PISTAS, encoding="utf-8"))["pistas"])
    ref = {str(x["codigo_ibge"]).zfill(7): x for x in json.load(open(REF, encoding="utf-8"))}
    jah = {(m["nome"], m["uf"]): m for m in json.load(open(MUN, encoding="utf-8"))}
    disco = {}
    if EVID.exists():
        for f in os.listdir(EVID):
            disco.setdefault(f.split(".")[0], []).append(f)

    p = [x for x in fila if not julgada(x)]
    if a.origem:
        p = [x for x in p if x.get("origem") == a.origem]
    else:
        # Rotina de julgamento §5: pistas C10 nunca entram misturadas — só com --origem explícito.
        p = [x for x in p if x.get("origem") != "rebaixamento C10"]
    if a.uf:
        p = [x for x in p if x.get("uf") == a.uf]
    p.sort(key=lambda x: (ORDEM.get(x.get("triagem"), 3), x.get("uf") or "", x.get("municipio") or ""))
    lote, restantes = p[:a.n], max(0, len(p) - a.n)

    hoje = datetime.date.today().isoformat()
    L = [f"# Caderno de pistas — {hoje}", "",
         f"{len(lote)} pista(s) neste lote · {restantes} ainda na fila depois deste.", "",
         "Responda cada bloco com **uma palavra**: `registro`, `resposta`, `descartar`, "
         "`pista` ou `buscar`. Em caso de dúvida, `pista` é sempre a resposta certa.", ""]

    for i, x in enumerate(lote, 1):
        cod = str(x.get("ibge") or "").zfill(7)
        geo = ref.get(cod, {})
        existe = (x.get("municipio"), x.get("uf")) in jah
        ev = x.get("hash_evidencia") or ""
        L += [f"## {i}. {x.get('municipio')} / {x.get('uf')} · {x.get('data') or 's/ data'}",
              f"- **Triagem do robô:** {x.get('triagem', '—')} · autoridade: {x.get('autoridade', '—')}"
              f" · objeto: {x.get('objeto', '—')} · destino sugerido: {x.get('destino', '—')}",
              f"- **Trecho:** {destacar(x.get('trecho', '') or '(sem trecho)')}",
              f"- **Diário:** {x.get('url', '—')}",
              f"- **Evidência local:** {linha_evidencia(ev, disco)}",
              f"- **Na base hoje:** " + (f"já existe como `{jah[(x['municipio'], x['uf'])]['categoria']}`"
                                        if existe else "não consta (entraria como `novo`)"),
              f"- **Coordenadas:** {geo.get('lat', '?')}, {geo.get('lon', '?')}"]
        if x.get("_duplicatas"):
            L.append(f"- **Repetida na varredura:** mesma evidência também registrada em "
                     f"{', '.join(x['_duplicatas'])} — mostrada uma única vez aqui; a decisão "
                     f"vale para todas as cópias.")
        L += ["", "**Decisão:** ", "", "---", ""]

    saida = RAIZ / f"caderno_de_pistas_{hoje}.md"
    saida.write_text("\n".join(L), encoding="utf-8")
    print(f"{saida} · {len(lote)} pista(s) no lote · {restantes} na fila")


if __name__ == "__main__":
    main()
