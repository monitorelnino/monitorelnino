#!/usr/bin/env python3
"""
preservar_evidencias.py (v2.2.4, §3.8)
======================================
Para cada registro PONTUÁVEL de data/municipios.json com URL e sem
`hash_evidencia`, baixa o documento, guarda em evidencias/<sha256>.<ext> (ou só
o hash + Wayback se > 5 MB), indexa em data/evidencias.json e grava o hash no
registro. Idempotente: quem já tem hash é pulado. Falha de rede = lacuna
declarada (o portão verificar_evidencias.py cobra depois). É a ÚNICA edição
programática permitida em municipios.json fora de aplicar_revisao.py, porque
não altera nenhum campo de julgamento — só acrescenta prova.
"""
import mimetypes, sys
from coletores_base import buscar, preservar_evidencia, ler, gravar, registrar_lacuna

PONT = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}


def main(limite: int = 200) -> int:
    mun = ler("municipios.json"); feitos = pulados = falhas = 0
    for m in mun:
        if m.get("categoria") not in PONT or not str(m.get("url", "")).startswith("http"):
            continue
        if m.get("hash_evidencia"):
            pulados += 1; continue
        if feitos + falhas >= limite:
            break
        try:
            bruto = buscar(m["url"], timeout=45)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"evidência {m['nome']}/{m['uf']}", f"{type(e).__name__}", canal=m.get("canal") or "DOM",
                             camada=2, uf=m["uf"], municipio=m["nome"], strings=[m["url"]]); falhas += 1
            continue
        ext = (mimetypes.guess_extension(("application/pdf" if bruto[:4] == b"%PDF" else "text/html")) or ".bin").lstrip(".")
        m["hash_evidencia"] = preservar_evidencia(bruto, m["url"], ext, "preservar_evidencias")
        feitos += 1
    gravar("municipios.json", mun)
    print(f"evidências: {feitos} preservada(s), {pulados} já tinham hash, {falhas} falha(s) de rede (lacunas no log)")
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 200))
