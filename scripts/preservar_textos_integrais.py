#!/usr/bin/env python3
"""Completa evidências de diário municipal que só têm o excerto da API com o TEXTO INTEGRAL.

Para cada pista de origem querido_diario em data/pistas_imprensa.json cujo hash tem
evidencias/<hash>.json (resposta da API, com txt_url) mas não evidencias/<hash>.txt,
baixa o texto integral da edição e grava ao lado, via preservar_texto_integral().

Não decide nada e não toca em pista, registro ou nota: só completa evidência já
preservada, para que o julgamento humano (rotina de pistas) leia o documento inteiro
offline. Idempotente; best-effort (falha de rede vira aviso, nunca erro fatal).

Uso:  python3 scripts/preservar_textos_integrais.py [--n 0]
      --n limita quantos downloads nesta execução (0 = todos os pendentes).
Feito para rodar no GitHub Actions (rede aberta); localmente funciona se a rede alcançar
data.queridodiario.ok.org.br.
"""
import argparse, json, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import EVID, preservar_texto_integral  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="máximo de downloads nesta execução (0 = todos)")
    a = ap.parse_args()

    pistas = json.load(open(RAIZ / "data" / "pistas_imprensa.json", encoding="utf-8"))["pistas"]
    pendentes, vistos = [], set()
    for p in pistas:
        h = p.get("hash_evidencia")
        if not h or h in vistos or p.get("origem") != "querido_diario":
            continue
        vistos.add(h)
        if (EVID / f"{h}.txt").exists():
            continue
        pendentes.append(h)

    print(f"{len(vistos)} evidência(s) de diário na fila · {len(pendentes)} sem texto integral")
    ok = falha = sem_json = 0
    for i, h in enumerate(pendentes, 1):
        if a.n and i > a.n:
            print(f"limite --n {a.n} atingido; {len(pendentes) - a.n} ficam para a próxima execução")
            break
        cam = EVID / f"{h}.json"
        if not cam.exists():
            print(f"  - {h[:12]}…: sem .json no disco (evidência nunca preservada) — fora do alcance deste script")
            sem_json += 1
            continue
        try:
            dados = json.load(open(cam, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {h[:12]}…: .json ilegível ({type(e).__name__})")
            falha += 1
            continue
        r = preservar_texto_integral(h, dados.get("gazettes", []), "preservar_textos_integrais")
        if r:
            print(f"  ✓ {h[:12]}… → {r}")
            ok += 1
        else:
            print(f"  ✗ {h[:12]}…: nenhum txt_url alcançável nesta execução")
            falha += 1
        time.sleep(1.0)  # cortesia com a API pública do Querido Diário

    print(f"concluído: {ok} completada(s), {falha} sem texto nesta execução, {sem_json} sem evidência-base")
    return 0  # best-effort por desenho: pendência não é erro; a régua de prova continua no julgamento


if __name__ == "__main__":
    sys.exit(main())
