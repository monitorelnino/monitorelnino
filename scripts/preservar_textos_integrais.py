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
from coletores_base import RAIZ as _RAIZ, buscar, ler, gravar, hoje, sha256  # noqa: E402


def _recuperar_pela_url(h: str):
    """Evidência indexada mas sem arquivo no disco (ex.: cópia perdida antes do commit da
    rodada, caso Serra/ES de 03/09/2026): re-busca a URL original do índice.
    - sha256 idêntico ao hash → restaura o .json (é o mesmo conteúdo) e baixa o .txt.
    - sha256 diferente (janela da API trouxe edições novas) → NUNCA grava .json sob o hash
      antigo (seria atestar identidade que não existe); grava só o .txt das edições atuais,
      com nota de divergência no índice — o texto do diário em si é estável e é o que se lê.
    Best-effort: qualquer falha devolve None e a pendência continua declarada."""
    idx = ler("evidencias.json", {"itens": {}})
    item = idx.get("itens", {}).get(h) or {}
    url = item.get("url") or ""
    if not url:
        return None
    # 10/09/2026: a API do QD atende em dois hosts equivalentes; tenta ambos, com retry —
    # a primeira rodada da recuperação falhou numa única tentativa sem fallback.
    alternativa = (url.replace("https://queridodiario.ok.org.br/api/", "https://api.queridodiario.ok.org.br/")
                   if "queridodiario.ok.org.br/api/" in url
                   else url.replace("https://api.queridodiario.ok.org.br/", "https://queridodiario.ok.org.br/api/"))
    bruto = None
    for tentativa, u in enumerate([url, url, alternativa, alternativa], 1):
        try:
            bruto = buscar(u, timeout=60)
            break
        except Exception:  # noqa: BLE001
            time.sleep(3 * tentativa)
    if bruto is None:
        return None
    try:
        dados = json.loads(bruto.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return None
    identico = sha256(bruto) == h
    if identico:
        EVID.mkdir(exist_ok=True)
        (EVID / f"{h}.json").write_bytes(bruto)
        item["arquivo"] = f"evidencias/{h}.json"
        item["nota"] = (item.get("nota") or "") + f" | re-preservada em {hoje()} (sha256 idêntico)"
    else:
        item["nota"] = (item.get("nota") or "") + (f" | {hoje()}: resposta atual da API difere do hash "
                                                   "original (janela trouxe edições novas); .json não "
                                                   "restaurado — texto integral preservado a partir da "
                                                   "resposta atual, com URLs de origem no arquivo")
    idx["itens"][h] = item
    gravar("evidencias.json", idx)
    r = preservar_texto_integral(h, dados.get("gazettes", []), "preservar_textos_integrais/recuperacao")
    return ("restaurada (.json + .txt)" if identico and r else
            ".txt preservado (com nota de divergência)" if r else
            ".json restaurado, sem txt_url alcançável" if identico else None)


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
            r = _recuperar_pela_url(h)
            print(f"  {'✓' if r else '-'} {h[:12]}…: evidência-base ausente — {r or 'irrecuperável pela URL indexada'}")
            if r:
                ok += 1
            else:
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
