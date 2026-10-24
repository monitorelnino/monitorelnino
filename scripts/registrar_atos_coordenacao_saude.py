#!/usr/bin/env python3
"""Registra na fila de saúde os atos de coordenação já lidos em domínio oficial (config/atos_coordenacao_saude.json).

Só entra pela porta única (`pistas.gravar_lote`); crédito é do juiz (`julgar_saude.py`). Uso:
    python3 scripts/registrar_atos_coordenacao_saude.py [--autoteste]
"""
import json, pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
FILA = "pistas_imprensa_saude.json"
ORIGEM = "busca_web"


def pistas_dos_atos(atos: list) -> list:
    """Função pura: um ato lido vira uma pista no molde da fila de saúde, nunca promovível."""
    return [{"alvo": f"funil-saude/{a['uf']}", "uf": a["uf"], "consulta": "coordenacao_" + a["funcao"],
             "titulo": f"{a['ato']} ({a['uf']}, {a['funcao']})", "url": a["url"], "trecho": a["trecho"],
             "data": a["data"], "nivel": "A", "tipo": "estrutura", "oficial": True,
             "documento_oficial_confirmado": None, "promovivel": False,
             "status": "pendente_confirmacao_documento"} for a in atos]


def autoteste() -> int:
    src = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert not any(f in src.split("def autoteste")[0] for f in ("saude_uf.json", "monitor_saude.json", "estados.json", "municipios.json", "indice.json")), "trava estrutural"
    ps = pistas_dos_atos([{"uf": "ES", "funcao": "F1", "ato": "X", "url": "https://a.gov.br/x", "trecho": "t", "data": "2026-01-20"}])
    assert ps[0]["documento_oficial_confirmado"] is None and ps[0]["promovivel"] is False, "trava de campo"
    print("autoteste ok (offline, sem escrita em data/)")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from scripts.pistas import gravar_lote
    atos = json.loads((RAIZ / "config" / "atos_coordenacao_saude.json").read_text(encoding="utf-8"))["atos"]
    r = gravar_lote(pistas_dos_atos(atos), origem=ORIGEM, nome_da_fila=FILA)
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
