"""Fila de teste da central (26/11/2026): os documentos de plano achados pela ponte nos sites de prefeitura de SP
que recusavam o robô de fora do país viram pista pela porta única (`scripts/pistas.gravar_lote`). Some do PR de dado."""
import json, pathlib, sys, urllib.parse as u
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
from pistas import gravar_lote
d = json.loads((RAIZ / "filas_teste" / "sp_docs.json").read_text(encoding="utf-8"))
pistas = [{"url": x["url"], "tipo": "plano", "alvo": x["ibge"], "nivel": "B", "data": "2026-11-26",
           "titulo": x.get("titulo") or "documento de plano no site da prefeitura (ponte no Brasil)",
           "origem": "descoberta"} for x in d]
print(gravar_lote(pistas, origem="descoberta"))
(RAIZ / "filas_teste" / "sp_urls.txt").write_text("\n".join(x["url"] for x in d) + "\n", encoding="utf-8")
