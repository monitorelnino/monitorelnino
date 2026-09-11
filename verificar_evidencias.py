#!/usr/bin/env python3
"""
verificar_evidencias.py — portão 6 (v2.2.4, §3.8 / §6)
======================================================
Todo registro PONTUÁVEL com URL precisa de evidência preservada
(`hash_evidencia` presente em `data/evidencias.json`, com arquivo em
`evidencias/` ou snapshot no Wayback). Regime declarado:
  - até 14/09/2026: AVISO — lista o que falta, sai 0 (prazo original 09/09, adiado em 08/09/2026 com errata:
    69 registros do ES não tinham cópia por falha do nosso próprio cliente HTTP — IRI com "ê" cru no caminho,
    corrigida em coletores_base.url_ascii; a primeira rodada do robô com a correção é segunda 14/09);
  - a partir de 15/09/2026: BLOQUEANTE — sai 1 se faltar.
Também confere a integridade dos arquivos preservados (sha256 do arquivo = chave).
"""
import hashlib, json, pathlib, sys
from datetime import date

RAIZ = pathlib.Path(__file__).parent
PONT = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}
BLOQUEIA_A_PARTIR = date(2026, 9, 15)


def checar_cliente_http() -> list:
    """Teste negativo permanente (08/09/2026): toda URL pontuável tem de sair de coletores_base.url_ascii em ASCII puro,
    idêntica quando já estava codificada. Foi um "ê" cru em 69 URLs do ES que deixou 69 registros sem evidência."""
    sys.path.insert(0, str(RAIZ))
    from coletores_base import url_ascii
    erros = []
    exemplo = "https://defesacivil.es.gov.br/Media/DefesaCivil/Plano%20de%20Contingência%20atualizado/2026/%C3%81GUA.pdf"
    if url_ascii(exemplo) != "https://defesacivil.es.gov.br/Media/DefesaCivil/Plano%20de%20Conting%C3%AAncia%20atualizado/2026/%C3%81GUA.pdf":
        erros.append("url_ascii não codifica caractere cru no caminho")
    ja = "https://x.org/a%20b?c=1&d=%C3%81#f"
    if url_ascii(ja) != ja: erros.append("url_ascii altera URL já codificada")
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    for m in mun:
        u = str(m.get("url", ""))
        if u.startswith("http") and not url_ascii(u).isascii(): erros.append(f"URL não ASCII após url_ascii: {u[:70]}")
    return erros


def main() -> int:
    e = checar_cliente_http()
    if e:
        print("✗ EVIDÊNCIAS: cliente HTTP:"); [print("   ", x) for x in e]; return 1
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    p_idx = RAIZ / "data" / "evidencias.json"
    idx = json.load(open(p_idx, encoding="utf-8")) if p_idx.exists() else {"itens": {}}
    itens = idx.get("itens", {})
    faltam, corrompidos = [], []
    for m in mun:
        if m.get("categoria") in PONT and str(m.get("url", "")).startswith("http"):
            h = m.get("hash_evidencia")
            if not h or h not in itens or not (itens[h].get("arquivo") or itens[h].get("wayback")):
                faltam.append(f"{m['nome']}/{m['uf']}")
    for h, it in itens.items():
        arq = it.get("arquivo")
        if arq:
            p = RAIZ / arq
            if not p.exists():
                corrompidos.append(f"{h[:12]}… arquivo ausente ({arq})")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
                corrompidos.append(f"{h[:12]}… conteúdo não bate com o hash ({arq})")
    # 11/09/2026 (achado do ensaio): teste negativo permanente. Um item cuja `arquivo` é um .txt e cuja URL de origem
    # é um .pdf tem a chave = sha256 do TEXTO, não do binário. Sem a marca `texto_manual`, `preservar_evidencias --ler`
    # o elege como alvo, reextrai o PDF e regrava evidencias/<h>.txt sob o mesmo nome — o conteúdo deixa de bater com a
    # chave e este portão fica vermelho na rodada (foi o que derrubou o job em 10/09 21h e o ensaio de 11/09).
    for h, it in itens.items():
        arq = str(it.get("arquivo") or "")
        if arq.endswith(".txt") and str(it.get("url", "")).lower().split("?")[0].endswith(".pdf") and not it.get("texto_manual"):
            corrompidos.append(f"{h[:12]}… evidência de texto com URL .pdf sem `texto_manual: true` — seria sobrescrita por preservar_evidencias --ler ({arq})")
    if corrompidos:
        print("✗ EVIDÊNCIAS: integridade violada:"); [print("   ", c) for c in corrompidos]; return 1
    total = sum(1 for m in mun if m.get("categoria") in PONT and str(m.get("url", "")).startswith("http"))
    if faltam:
        regime = "BLOQUEANTE" if date.today() >= BLOQUEIA_A_PARTIR else "aviso (bloqueante a partir de 15/09/2026)"
        print(f"{'✗' if regime == 'BLOQUEANTE' else '⚠'} EVIDÊNCIAS: {len(faltam)} de {total} registro(s) pontuável(is) com URL sem evidência preservada — {regime}")
        for f in faltam[:8]: print("   ", f)
        if len(faltam) > 8: print(f"    … e mais {len(faltam) - 8}")
        return 1 if regime == "BLOQUEANTE" else 0
    print(f"✓ EVIDÊNCIAS OK — {total} registro(s) pontuável(is) com URL, todos com evidência preservada; {len(itens)} item(ns) íntegro(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
