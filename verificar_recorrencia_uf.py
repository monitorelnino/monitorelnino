#!/usr/bin/env python3
"""
verificar_recorrencia_uf.py
=============================
Compara um decreto ESTADUAL candidato contra o histórico da mesma UF
(data/decretos_historico_uf.json) para detectar se é, na prática, o mesmo
instrumento reeditado ano a ano (achado do Decreto 48.599/2026 do DF —
idêntico, em espírito, aos decretos de 2016/2021/2023/2025 — ver METODOLOGIA
§18 addendum) — em vez de um instrumento genuinamente novo do ciclo.

ESCOPO DELIBERADO: só decretos ESTADUAIS (27 UFs, universo pequeno, custo de
manter e comparar histórico é baixo). NÃO se aplica a municípios (5.571
linhas — decisão explícita de Patricia, 31/08/2026, por serem problemas de
escala diferente).

Isto é um módulo DIFERENTE de classificador_natureza.py: aquele lê um único
texto e decide ex-ante/resposta; este compara um texto contra um HISTÓRICO
para decidir se é novo ou reciclado. Um decreto pode ser claramente ex-ante
(classificador_natureza diria EX_ANTE) e AINDA ASSIM ser recorrente (este
módulo aplicaria antecipação reduzida) — são eixos independentes.

USO:
    from verificar_recorrencia_uf import checar_recorrencia, registrar_no_historico
    recorrente, similaridade, entrada_parecida = checar_recorrencia("DF", texto_resumo)
"""
import argparse
import difflib
import json
from pathlib import Path

RAIZ = Path(__file__).parent
HISTORICO_PATH = RAIZ / "data" / "decretos_historico_uf.json"
LIMIAR_PADRAO = 0.55  # abaixo disso, similaridade insuficiente para acusar reedição

# Régua de antecipação por cobertura do risco projetado, já declarada em
# METODOLOGIA §18 addendum (aplicada hoje manualmente a DF/SP/RJ/ES/MG).
REGUA_ANTECIPACAO_RECORRENTE = {"COBRE": 40, "NEUTRO": 30, "DIFERE": 20}


def carregar_historico():
    """Lê o histórico completo (todas as UFs) do disco, ou um esqueleto vazio se o
    arquivo ainda não existir."""
    if not HISTORICO_PATH.exists():
        return {"UF": {}}
    return json.load(open(HISTORICO_PATH, encoding="utf-8"))


def salvar_historico(historico):
    """Grava o histórico completo de volta em disco (indentado, para diff legível)."""
    json.dump(historico, open(HISTORICO_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def checar_recorrencia(uf, texto_novo, limiar=LIMIAR_PADRAO):
    """Retorna (é_recorrente: bool, similaridade_máxima: float, entrada_mais_parecida: dict|None)."""
    historico = carregar_historico()
    entradas = historico.get("UF", {}).get(uf, [])
    if not entradas:
        return False, 0.0, None
    texto_novo_norm = texto_novo.lower()
    melhor = max(entradas, key=lambda h: difflib.SequenceMatcher(
        None, h["resumo"].lower(), texto_novo_norm).ratio())
    sim = difflib.SequenceMatcher(None, melhor["resumo"].lower(), texto_novo_norm).ratio()
    return sim >= limiar, sim, melhor


def registrar_no_historico(uf, ano, numero, tema, resumo, origem):
    """Adiciona uma entrada ao histórico (recorrente ou não — todo decreto processado
    entra, para servir de comparação em ciclos futuros). Idempotente por (uf, ano, numero)."""
    historico = carregar_historico()
    entradas = historico.setdefault("UF", {}).setdefault(uf, [])
    if any(e["ano"] == ano and e["numero"] == numero for e in entradas):
        return False  # já registrado
    entradas.append({"ano": ano, "numero": numero, "tema": tema, "resumo": resumo, "origem": origem})
    salvar_historico(historico)
    return True


def self_test():
    """Roda os 4 cenários de calibração do verificador de recorrência: DF (recorrente
    de verdade), Acre (controle — cita antecessor mas é genuinamente novo), UF sem
    histórico ainda, e idempotência do registro."""
    # Teste 1: DF 2026 deve bater com o histórico (é o achado real de hoje)
    texto_df = ("estado de emergência ambiental no Distrito Federal entre abril e dezembro de "
                "2026, para prevenir e minimizar incêndios florestais no âmbito do PPCIF")
    recorrente, sim, match = checar_recorrencia("DF", texto_df)
    assert recorrente, f"DF deveria ser detectado como recorrente (sim={sim:.2f})"
    assert sim >= LIMIAR_PADRAO
    print(f"✓ self-test OK — DF 2026 detectado como recorrente ({sim:.0%} de semelhança com {match['ano']})")

    # Teste 2 (controle/falso-positivo): AC muda substancialmente — NÃO deve bater
    texto_ac = ("institui o Gabinete de Crise Hídrica do Acre, com competências ampliadas de "
                "coordenação intersetorial e orçamento próprio dedicado, sucedendo e ampliando "
                "a estrutura informal de 2024")
    recorrente2, sim2, match2 = checar_recorrencia("AC", texto_ac)
    assert not recorrente2, f"AC NÃO deveria ser recorrente (falso positivo, sim={sim2:.2f})"
    print(f"✓ self-test OK — AC (controle, texto genuinamente diferente) NÃO confundido com recorrência ({sim2:.0%})")

    # Teste 3: UF sem histórico ainda
    recorrente3, sim3, match3 = checar_recorrencia("SE", "cria comitê de monitoramento")
    assert not recorrente3 and match3 is None
    print("✓ self-test OK — UF sem histórico não é classificada como recorrente (correto: sem dado, sem acusação)")

    # Teste 4: registrar_no_historico é idempotente
    import tempfile, os
    global HISTORICO_PATH
    original = HISTORICO_PATH
    with tempfile.TemporaryDirectory() as tmp:
        HISTORICO_PATH = Path(tmp) / "hist_teste.json"
        salvar_historico({"UF": {}})
        r1 = registrar_no_historico("XX", 2026, "1", "teste", "resumo teste", "self-test")
        r2 = registrar_no_historico("XX", 2026, "1", "teste", "resumo teste", "self-test")
        assert r1 is True and r2 is False, "registro duplicado deveria ser rejeitado (idempotência)"
    HISTORICO_PATH = original
    print("✓ self-test OK — registrar_no_historico é idempotente (não duplica)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
