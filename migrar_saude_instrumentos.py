#!/usr/bin/env python3
"""Migração de data/saude_uf.json: campo único `doc` por UF → `instrumentos: []`,
mesmo padrão de data/estados.json (defesa civil), pedida no handover do ponto cego
de saúde (18/09/2026, §3.2).

Achado ao investigar antes de escrever: defesa civil NÃO tem uma função "escolher o
melhor entre N instrumentos" para reaproveitar — o campo de topo de cada UF em
estados.json sempre espelha, 1 para 1, o item de tipo `instrumento_operacional`
(confirmado nas 27 UFs). É um mapeamento fixo entre dois papéis paralelos
(estrutura de coordenação × instrumento operacional), não uma escolha entre vários.
Saúde é diferente: três tipos formam uma ESCALA de força (um documento específico do
ciclo é mais forte que um plano recorrente de arboviroses, que é mais forte que só uma
estrutura de coordenação sem documento operacional) — por isso `melhor_instrumento()`
abaixo é lógica nova, não uma reutilização.

Regra de ouro (handover): nenhuma nota muda só pela migração. Para o dado de hoje,
cada UF tem no máximo um documento real — o item migrado é sempre o único candidato,
então `melhor_instrumento()` devolve exatamente o que já estava no campo de topo.
"""
import json
import sys
from pathlib import Path
from coletores_base import gravar_em  # noqa: E402  (§229: escrita atômica de data/)

RAIZ = Path(__file__).resolve().parent
CAMINHO = RAIZ / "data" / "saude_uf.json"

# ordem de força, do mais fraco ao mais forte — usada por melhor_instrumento()
ORDEM_TIPO = ["estrutura_coordenacao", "recorrente_arboviroses", "especifico_ciclo"]
ORDEM_STATUS = ["NAO_VERIFICADO", "LAC", "ELAB", "VIG", "READ", "NOVO"]

CAMPOS_INSTRUMENTO = ["status", "orgao", "doc", "numero", "data", "url", "hash_evidencia",
                      "natureza_doc", "justificativa_ex_ante"]
CAMPOS_UF = ["risco_sanitario_projetado", "consist", "data_verificacao", "log_ref"]


def classificar_tipo(registro: dict) -> str:
    """Classifica o tipo do instrumento migrado a partir do texto e do status já julgados
    manualmente (bateria de 05/09/2026) — nunca reclassifica o julgamento em si, só nomeia
    o tipo que ele já representa."""
    status = registro.get("status")
    doc = (registro.get("doc") or "")
    if status == "NAO_VERIFICADO" or not doc:
        return "especifico_ciclo"  # nenhum instrumento conhecido ainda; é o tipo que a
        # próxima verificação prioriza encontrar primeiro — não inventa um documento
    if "el niño" in doc.lower() or "el nino" in doc.lower():
        return "especifico_ciclo"
    return "recorrente_arboviroses"


def melhor_instrumento(instrumentos: list) -> dict | None:
    """Escolhe o instrumento que deve alimentar o campo de topo (e o índice): primeiro por
    tipo (ORDEM_TIPO, mais forte vence), depois por status (ORDEM_STATUS) como desempate
    dentro do mesmo tipo, depois pela data mais recente como último desempate."""
    if not instrumentos:
        return None
    def chave(i):
        tipo_i = ORDEM_TIPO.index(i.get("tipo")) if i.get("tipo") in ORDEM_TIPO else -1
        status_i = ORDEM_STATUS.index(i.get("status")) if i.get("status") in ORDEM_STATUS else -1
        return (tipo_i, status_i, i.get("data") or "")
    return max(instrumentos, key=chave)


def migrar(dado: dict) -> tuple[dict, list]:
    """Devolve (dado migrado, lista de avisos). Não muta o dado de entrada."""
    avisos = []
    saida = json.loads(json.dumps(dado))  # cópia profunda
    for uf, registro in saida["uf"].items():
        item = {c: registro.get(c) for c in CAMPOS_INSTRUMENTO}
        item["tipo"] = classificar_tipo(registro)
        instrumentos = [item]

        novo = {c: registro.get(c) for c in CAMPOS_UF}
        novo["instrumentos"] = instrumentos
        melhor = melhor_instrumento(instrumentos)
        for c in CAMPOS_INSTRUMENTO:
            novo[c] = melhor.get(c) if melhor else None

        # confere que a migração não mudou nada que o índice lê
        for campo in ("status", "doc", "data"):
            if novo.get(campo) != registro.get(campo):
                avisos.append(f"{uf}: campo '{campo}' mudou na migração ({registro.get(campo)!r} → {novo.get(campo)!r})")
        saida["uf"][uf] = novo
    return saida, avisos


def main() -> int:
    dado = json.loads(CAMINHO.read_text(encoding="utf-8"))
    if any("instrumentos" in r for r in dado["uf"].values()):
        print("✗ já migrado — data/saude_uf.json já tem 'instrumentos' em pelo menos uma UF.")
        return 1
    migrado, avisos = migrar(dado)
    if avisos:
        print(f"✗ MIGRAÇÃO: {len(avisos)} campo(s) mudariam de valor — corrija antes de gravar:")
        for a in avisos:
            print("  -", a)
        return 1
    gravar_em(CAMINHO, migrado)   # §229
    print(f"✓ migrado — {len(migrado['uf'])} UFs, nenhum valor de topo mudou.")
    return 0


def autoteste() -> int:
    falhas = []
    def checar(nome, cond):
        if not cond:
            falhas.append(nome)

    # classificar_tipo
    checar("tipo: sem doc vira especifico_ciclo (nada inventado)", classificar_tipo({"status": "NAO_VERIFICADO", "doc": None}) == "especifico_ciclo")
    checar("tipo: menção a El Niño vira especifico_ciclo", classificar_tipo({"status": "NOVO", "doc": "Plano... cenários do El Niño 2026/2027"}) == "especifico_ciclo")
    checar("tipo: arbovirose sem El Niño vira recorrente_arboviroses", classificar_tipo({"status": "VIG", "doc": "Plano Estadual de Contingência das Arboviroses Urbanas"}) == "recorrente_arboviroses")

    # melhor_instrumento
    checar("melhor: especifico_ciclo vence recorrente mesmo com status mais fraco",
           melhor_instrumento([{"tipo": "recorrente_arboviroses", "status": "VIG", "data": "05/2025"},
                                {"tipo": "especifico_ciclo", "status": "ELAB", "data": "08/2026"}])["tipo"] == "especifico_ciclo")
    checar("melhor: dentro do mesmo tipo, status mais forte vence",
           melhor_instrumento([{"tipo": "recorrente_arboviroses", "status": "ELAB", "data": "01/2025"},
                                {"tipo": "recorrente_arboviroses", "status": "VIG", "data": "01/2024"}])["status"] == "VIG")
    checar("melhor: lista vazia devolve None", melhor_instrumento([]) is None)

    # migração não muda nada (regra de ouro do handover) — roda contra o dado real
    dado = json.loads(CAMINHO.read_text(encoding="utf-8"))
    if "instrumentos" not in next(iter(dado["uf"].values())):
        _, avisos = migrar(dado)
        checar("migração do dado real: nenhum valor de topo muda", avisos == [])
    else:
        checar("migração do dado real: já migrado, pulando (rode antes de aplicar migrar_saude_instrumentos.py)", True)

    if falhas:
        print(f"✗ {len(falhas)} falha(s):")
        for f in falhas:
            print("  -", f)
        return 1
    print("✓ AUTOTESTE OK — classificação, escolha do melhor instrumento e migração sem regressão.")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
