#!/usr/bin/env python3
"""
monitorar_atos_resposta.py
=============================
Vigia de imprensa nacional por NOVOS decretos de situação de emergência ou
calamidade pública — atos de RESPOSTA, que nunca pontuam no índice MARÉ
(Correção B), mas alimentam o mapa "Cidades que decretaram emergência"
(data/atos_resposta.json), criado em 31/08/2026 a pedido de Patricia depois
do temporal de granizo em Santa Catarina.

DIFERENÇA DELIBERADA em relação a monitorar_imprensa_regional.py: aquela
rotina busca instrumentos EX-ANTE, priorizada pelas UFs que mais precisam
(LAC primeiro) — faz sentido, porque o que se busca é ligado ao status de
preparação de cada UF. Atos de resposta são o oposto: um evento climático
pode acontecer em QUALQUER UF, independente do quanto ela já está preparada
— por isso esta rotina varre as 27 UFs em rodízio simples, sem priorização,
usando o vocabulário de RESPOSTA do dicionário (não o de instrumento).

MESMA TRAVA ABSOLUTA das outras rotinas de descoberta (nenhuma pista entra
direto no banco): esta rotina só GERA pistas, na MESMA fila que
monitorar_imprensa_regional.py usa (data/pistas_imprensa.json) — reaproveita
a função registrar() de lá, então a mesma deduplicação e os mesmos campos de
trava (documento_oficial_confirmado, promovivel) se aplicam. O julgamento
(classificador_natureza.py, via julgar_e_aplicar_descobertas.py) decide se
cada pista é resposta (vai para o mapa) ou, por engano de busca, alguma coisa
ex-ante (vai para o caminho normal) — a rotina de busca não pré-julga nada.

Uso:
  python3 monitorar_atos_resposta.py                 # roda o rodízio (rede aberta)
  python3 monitorar_atos_resposta.py --limite 10      # tamanho do lote desta execução
  python3 monitorar_atos_resposta.py --self-test       # valida offline, sem rede
"""
import json
import sys
import time
from pathlib import Path

from monitorar_imprensa_regional import (
    _get, montar_url, extrair_itens_rss, parece_fonte_oficial,
    carregar_fila, registrar, FILA,
)

RAIZ = Path(__file__).parent
CURSOR_RESPOSTA = RAIZ / "data" / "resposta_cursor.json"

TERMOS_RESPOSTA_BUSCA = ["situação de emergência", "estado de calamidade pública", "decreto emergência"]

TODAS_UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
             "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]


def montar_universo_resposta(estados_json):
    """Um alvo por UF (rodízio simples, sem priorização — ver docstring do módulo).
    O nome do estado (não só a sigla) melhora a precisão da busca por notícia local."""
    nomes = {u["uf"]: u["nome"] for u in estados_json["ufs"]}
    return [("resposta", uf, [f'"{t}" {nomes.get(uf, uf)} 2026' for t in TERMOS_RESPOSTA_BUSCA])
            for uf in TODAS_UFS]


def carregar_cursor(total):
    """Posição do rodízio — arquivo PRÓPRIO desta rotina (resposta_cursor.json),
    para não interferir no cursor de monitorar_imprensa_regional.py."""
    if CURSOR_RESPOSTA.exists():
        try:
            return json.load(open(CURSOR_RESPOSTA, encoding="utf-8")).get("posicao", 0) % total
        except Exception:
            return 0
    return 0


def salvar_cursor(posicao, total):
    """Grava a posição do rodízio para a próxima execução continuar de onde parou."""
    json.dump({"posicao": posicao, "tamanho_universo": total},
               open(CURSOR_RESPOSTA, "w", encoding="utf-8"))


def main():
    """CLI: consome o cursor próprio, busca o próximo lote de UFs e registra pistas
    de resposta na MESMA fila de monitorar_imprensa_regional.py."""
    if "--self-test" in sys.argv:
        return self_test()

    limite = 10
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])

    estados = json.load(open(RAIZ / "data" / "estados.json", encoding="utf-8"))
    universo = montar_universo_resposta(estados)
    pos = carregar_cursor(len(universo))
    fila = carregar_fila()
    total_novas = 0

    for i in range(limite):
        idx = (pos + i) % len(universo)
        rotulo, uf, queries = universo[idx]
        for q in queries:
            xml = _get(montar_url(q))
            if not xml:
                continue
            itens = [{"alvo": f"{rotulo}/{uf}", "query": q, **it} for it in extrair_itens_rss(xml)]
            novas = registrar(fila, itens)
            total_novas += len(novas)
            time.sleep(1.0)  # mesma cortesia de taxa do resto do pipeline

    salvar_cursor((pos + limite) % len(universo), len(universo))
    json.dump(fila, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Universo de busca (atos de resposta): {len(universo)} UFs; "
          f"{limite} consultadas nesta execução (posição {pos}→{(pos+limite) % len(universo)}).")
    if total_novas:
        print(f"[PISTAS NOVAS] {total_novas} para julgamento automático "
              f"(julgar_e_aplicar_descobertas.py) ou triagem humana:")
        for p in fila["pistas"][-total_novas:]:
            marca = " [parece oficial]" if p["fonte_provavel_oficial"] else ""
            print(f"  · [{p['alvo']}]{marca} {p['titulo'][:100]}")
    else:
        print(f"Nenhuma pista inédita (fila com {len(fila['pistas'])} itens acumulados).")
    return 0


def self_test():
    """Valida offline: universo tem as 27 UFs, cursor isolado do de imprensa, e a
    reutilização de registrar()/carregar_fila() continua funcionando (dedup incluída)."""
    estados = json.load(open(RAIZ / "data" / "estados.json", encoding="utf-8"))
    universo = montar_universo_resposta(estados)
    assert len(universo) == 27, f"esperava 27 UFs, achei {len(universo)}"
    assert {u for _, u, _ in universo} == set(TODAS_UFS)
    print("✓ self-test OK — universo cobre as 27 UFs, sem priorização")

    assert CURSOR_RESPOSTA != RAIZ / "data" / "imprensa_cursor.json", \
        "cursor de resposta não pode ser o mesmo arquivo do cursor de imprensa"
    print("✓ self-test OK — cursor isolado do de monitorar_imprensa_regional.py")

    fila_teste = {"_governanca": "teste", "pistas": []}
    item = {"alvo": "resposta/SC", "query": "teste", "titulo": "Cidade decreta emergência",
            "url": "https://exemplo.gov.br/x", "data_publicacao": "", "fonte_veiculo": ""}
    novas1 = registrar(fila_teste, [item])
    novas2 = registrar(fila_teste, [item])  # mesma pista de novo
    assert len(novas1) == 1 and len(novas2) == 0, "deduplicação deveria rejeitar a segunda vez"
    assert fila_teste["pistas"][0]["documento_oficial_confirmado"] is None
    assert fila_teste["pistas"][0]["promovivel"] is False
    print("✓ self-test OK — reaproveitamento de registrar()/dedup/trava funciona igual ao de imprensa")


if __name__ == "__main__":
    sys.exit(main())
