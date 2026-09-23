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


def _consulta_minima_pela_pista(h: str):
    """Monta a menor consulta possível à API do QD a partir das pistas que carregam o hash:
    territory_ids=<ibge> na data exata da edição. Devolve os bytes da resposta, ou None."""
    try:
        pistas = json.load(open(_RAIZ / "data" / "pistas_imprensa.json", encoding="utf-8"))["pistas"]
        alvo = next((p for p in pistas if p.get("hash_evidencia") == h and p.get("ibge") and p.get("data")), None)
        if not alvo:
            return None
        d, m_, a_ = alvo["data"].split("/")
        dia = f"{a_}-{m_}-{d}"
        for base in ("https://queridodiario.ok.org.br/api/gazettes",
                     "https://api.queridodiario.ok.org.br/gazettes"):
            u = f"{base}?territory_ids={str(alvo['ibge']).zfill(7)}&published_since={dia}&published_until={dia}&size=10"
            try:
                return buscar(u, timeout=60)
            except Exception:  # noqa: BLE001
                time.sleep(2)
        return None
    except Exception:  # noqa: BLE001
        return None


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
        # Fallback final (10/09/2026, 2ª rodada): a consulta original pode ter expirado ou
        # mudado de contrato; a EDIÇÃO é estável. Reconstrói uma consulta mínima pela
        # própria pista (IBGE + data) e busca só aquele dia.
        bruto = _consulta_minima_pela_pista(h)
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


def fila_do_indice(idx: dict, raiz=None) -> list:
    """§176 (23/09/2026): hashes que o ÍNDICE diz ter texto integral preservado e não têm arquivo.

    A fila desta rotina sempre saiu de `data/pistas_imprensa.json`, com `origem == querido_diario`.
    Evidência preservada por `coletar_diarios_municipais.py` que não gerou pista ficava fora de
    alcance: quatro itens tinham `texto_integral` no índice desde 12/09/2026 apontando para um
    `.txt` que nunca entrou no commit da rodada, e nada os procurava nem os acusava."""
    raiz = raiz or RAIZ
    return [h for h, it in (idx.get("itens") or {}).items()
            if it.get("texto_integral") and not (raiz / it["texto_integral"]).exists()]


def selar_hashes(idx: dict, raiz=None) -> tuple:
    """§176: sela `texto_integral_hash` de quem foi preservado antes desta regra. Muda `idx` em
    memória e devolve (selados, divergentes) — quem chama grava.

    Preenche só quando o hash está AUSENTE. Divergência entre o arquivo em disco e um hash já
    registrado não é reselada em silêncio: seria apagar o registro de que o arquivo mudou. Volta
    na lista de divergentes, e o portão 6 bloqueia até alguém dizer o que aconteceu (a redação de
    dados pessoais, que é a mudança legítima conhecida, recalcula o hash na própria rotina —
    scripts/remediar_cpf_evidencias.py)."""
    raiz = raiz or RAIZ
    selados, divergentes = [], []
    for h, item in (idx.get("itens") or {}).items():
        ti = item.get("texto_integral")
        if not ti:
            continue
        arq = raiz / ti
        if not arq.exists():
            continue
        real = sha256(arq.read_bytes())
        registrado = item.get("texto_integral_hash")
        if registrado == real:
            continue
        if registrado:
            divergentes.append(f"{h[:12]}… registrado {registrado[:10]}… ≠ disco {real[:10]}… ({ti})")
        else:
            item["texto_integral_hash"] = real
            selados.append(f"{h[:12]}… {real[:10]}… ({ti})")
    return selados, divergentes


def autoteste() -> int:
    """Testes negativos permanentes das duas regras novas do §176."""
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory() as d:
        raiz = Path(d); (raiz / "evidencias").mkdir()
        (raiz / "evidencias" / "aa.txt").write_text("edição inteira", encoding="utf-8", newline="\n")
        h_real = sha256((raiz / "evidencias" / "aa.txt").read_bytes())
        idx = {"itens": {
            "a" * 64: {"texto_integral": "evidencias/aa.txt"},                                  # sem hash → sela
            "b" * 64: {"texto_integral": "evidencias/bb.txt"},                                  # arquivo ausente → fila
            "c" * 64: {"texto_integral": "evidencias/aa.txt", "texto_integral_hash": "0" * 64},  # divergente → acusa
            "d" * 64: {"texto_integral": "evidencias/aa.txt", "texto_integral_hash": h_real},    # em ordem → silêncio
            "e" * 64: {"arquivo": "evidencias/aa.json"},                                        # sem texto integral
        }}
        fila = fila_do_indice(idx, raiz)
        if fila != ["b" * 64]:
            falhas.append(f"fila_do_indice devolveu {[x[:4] for x in fila]}, esperado só o de arquivo ausente")
        selados, divergentes = selar_hashes(idx, raiz)
        if len(selados) != 1 or idx["itens"]["a" * 64].get("texto_integral_hash") != h_real:
            falhas.append(f"selar_hashes não selou o hash ausente: {selados}")
        if len(divergentes) != 1:
            falhas.append(f"selar_hashes não acusou a divergência: {divergentes}")
        if idx["itens"]["c" * 64]["texto_integral_hash"] != "0" * 64:
            falhas.append("selar_hashes reselou um hash divergente em silêncio — isso apaga o registro da mudança")
        if selar_hashes(idx, raiz)[0]:
            falhas.append("selar_hashes não é idempotente")
    if falhas:
        print("✗ AUTOTESTE (texto integral):"); [print("   ", f) for f in falhas]; return 1
    print("✓ AUTOTESTE OK — fila pelo índice, hash ausente selado, divergência acusada e não reselada.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="máximo de downloads nesta execução (0 = todos)")
    ap.add_argument("--autoteste", action="store_true", help="testes negativos das regras do §176")
    a = ap.parse_args()
    if a.autoteste:
        return autoteste()


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

    # §176: quem o índice diz ter texto integral preservado e não tem arquivo em disco entra na
    # mesma fila, venha de pista ou não — foi assim que quatro itens de 12/09/2026 ficaram órfãos.
    idx = ler("evidencias.json", {"itens": {}})
    do_indice = [h for h in fila_do_indice(idx) if h not in pendentes]
    pendentes += do_indice

    print(f"{len(vistos)} evidência(s) de diário na fila · {len(pendentes)} sem texto integral"
          f" ({len(do_indice)} vindo(s) do índice, sem pista)")
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

    # §176: sela o hash do texto integral de quem foi preservado antes desta regra.
    idx = ler("evidencias.json", {"itens": {}})
    selados, divergentes = selar_hashes(idx)
    if selados:
        gravar("evidencias.json", idx)
        print(f"{len(selados)} hash(es) de texto integral selado(s):")
        for s in selados[:8]:
            print("   ", s)
        if len(selados) > 8:
            print(f"    … e mais {len(selados) - 8}")
    for dv in divergentes:
        print(f"  ⚠ texto integral divergente do hash registrado: {dv}")

    print(f"concluído: {ok} completada(s), {falha} sem texto nesta execução, {sem_json} sem evidência-base")
    return 0  # best-effort por desenho: pendência não é erro; a régua de prova continua no julgamento


if __name__ == "__main__":
    sys.exit(main())
