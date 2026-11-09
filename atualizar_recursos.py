#!/usr/bin/env python3
"""Aquisição do PIB per capita por UF (IBGE, Sistema de Contas Regionais) para a capacidade fiscal
de `data/financiamento/por_uf.json`. Padrão sentinela do Censo: só grava se as âncoras oficiais
verificadas em 27/08/2026 baterem — DF 129.790,44 · SP 77.566,27 · MT 74.620,05 (2023) · MA na
última posição. Qualquer divergência aborta sem escrever.

09/11/2026 — causa raiz de dez domingos sem dado, provada por sonda no Actions: a consulta pedia a
variável 6323 na tabela 5938 do SIDRA e o IBGE respondia 400 "variável inexistente na tabela"; o
script engolia a recusa e saía 0 ("mantendo seed"), e a rodada semanal nunca ficou vermelha. A tabela
5938 não tem per capita em nível de UF. O per capita passa a ser construído com as duas séries que o
IBGE publica nela e na tabela 6579: PIB a preços correntes (v/37, mil reais) ÷ população residente
estimada do mesmo ano (v/9324, pessoas) — é a construção do próprio IBGE, e as sentinelas provam
isso: no ano delas (2023) o quociente tem de reproduzir o valor oficial ao centavo (tolerância 0,5).
Validado o método no ano das sentinelas, publica-se o último ano disponível com a mesma construção,
declarando os dois anos. Recusa da fonte é erro (exit 1), nunca "ok".
"""
import json, pathlib, sys, urllib.request

from coletores_base import ua_de, gravar_em, ler, gravar  # §228: pedia o SIDRA sem identificar o cliente

RAIZ = pathlib.Path(__file__).parent
DEST = RAIZ / "data" / "recursos_uf.json"
ANO_SENTINELAS = "2023"
SENT = {"DF": 129790.44, "SP": 77566.27, "MT": 74620.05}
URL_PIB = "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/37/p/{ano}?formato=json"     # mil reais
URL_POP = "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/{ano}?formato=json"   # pessoas
UFS = {"Rondônia": "RO", "Acre": "AC", "Amazonas": "AM", "Roraima": "RR", "Pará": "PA", "Amapá": "AP", "Tocantins": "TO",
       "Maranhão": "MA", "Piauí": "PI", "Ceará": "CE", "Rio Grande do Norte": "RN", "Paraíba": "PB", "Pernambuco": "PE",
       "Alagoas": "AL", "Sergipe": "SE", "Bahia": "BA", "Minas Gerais": "MG", "Espírito Santo": "ES", "Rio de Janeiro": "RJ",
       "São Paulo": "SP", "Paraná": "PR", "Santa Catarina": "SC", "Rio Grande do Sul": "RS", "Mato Grosso do Sul": "MS",
       "Mato Grosso": "MT", "Goiás": "GO", "Distrito Federal": "DF"}


def por_uf(dados) -> dict:
    """Linhas do SIDRA → {sigla: valor}. Pula o cabeçalho e valores não numéricos ("...", "-"). Função pura."""
    out = {}
    for linha in (dados or [])[1:]:
        uf = UFS.get(str(linha.get("D1N", "")).strip())
        try:
            v = float(linha.get("V"))
        except (TypeError, ValueError):
            continue
        if uf:
            out[uf] = v
    return out


def per_capita(pib_mil_reais: dict, populacao: dict) -> dict:
    """PIB (mil reais) ÷ população (pessoas), em reais com centavos, só para as UFs presentes nos dois. Função pura."""
    return {uf: round(pib_mil_reais[uf] * 1000.0 / populacao[uf], 2)
            for uf in pib_mil_reais if uf in populacao and populacao[uf] > 0}


def por_que_recusar(pib: dict) -> "str | None":
    """O motivo de recusar o PIB per capita lido, ou `None` quando ele passa. Função pura.

    08/10/2026 (A6-26): a validação morava dentro de `main`, depois da chamada de rede, e
    `--autoteste` era IGNORADO — o script ia ao SIDRA e GRAVAVA. Autoteste que depende da rede
    não é autoteste; a trava que importa é esta, e agora ela se exerce offline.
    """
    if len(pib) != 27:
        return f"{len(pib)}/27 UFs"
    for uf, esperado in SENT.items():
        if uf not in pib:
            return f"sentinela {uf} ausente"
        if abs(pib[uf] - esperado) > 0.5:
            return f"sentinela {uf} divergente ({pib[uf]} ≠ {esperado})"
    if min(pib, key=pib.get) != "MA":
        return "última posição não é MA"
    return None


def autoteste() -> int:
    """Autoteste PURO: sem rede, sem escrever nada."""
    base = {uf: 50000.0 for uf in UFS.values()}
    base.update(SENT)
    base["MA"] = min(base.values()) - 1
    sidra = [{"D1N": "Unidade da Federação", "V": "Valor"}, {"D1N": "Rio de Janeiro", "V": "1172871000"},
             {"D1N": "Acre", "V": "..."}, {"D1N": "Lugar Nenhum", "V": "1"}]
    pc = per_capita({"RJ": 1172871000.0, "SP": 1.0}, {"RJ": 16055174.0, "AC": 1.0})
    casos = [
        ("27 UFs com sentinelas e MA na última posição passam", por_que_recusar(base) is None),
        ("26 UFs reprovam",
         "26/27" in (por_que_recusar({k: v for k, v in list(base.items())[:26]}) or "")),
        ("sentinela divergente reprova",
         "divergente" in (por_que_recusar({**base,
                                           next(iter(SENT)): SENT[next(iter(SENT))] + 10}) or "")),
        ("última posição diferente de MA reprova",
         por_que_recusar({**base, "MA": max(base.values()) + 1}) is not None),
        ("linhas do SIDRA: pula cabeçalho, '...' e nome desconhecido", por_uf(sidra) == {"RJ": 1172871000.0}),
        ("per capita = PIB (mil reais) ÷ população, só UF presente nos dois; RJ 2023 reproduz o oficial (R$ 73.052,55) a 3 centavos",
         pc == {"RJ": 73052.52} and abs(pc["RJ"] - 73052.55) <= 0.5),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'✓' if ok else '✗'} {n}")
    print(f"{'✓ AUTOTESTE OK' if not ruins else f'✗ AUTOTESTE: {len(ruins)} falha(s)'} — "
          f"{len(casos)} casos, sem rede e sem escrita.")
    return 1 if ruins else 0


def _sidra(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": ua_de("PIB per capita no SIDRA")})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def _ano_de(dados) -> str:
    return str((dados or [{}, {}])[1].get("D3N", "")) if len(dados or []) > 1 else ""


def main():
    """Lê PIB e população por UF no SIDRA, valida o quociente contra as sentinelas de 2023 e grava data/recursos_uf.json com o último ano disponível; recusa da fonte ou sentinela divergente = erro, nada gravado."""
    try:
        pib_s, pop_s = _sidra(URL_PIB.format(ano=ANO_SENTINELAS)), _sidra(URL_POP.format(ano=ANO_SENTINELAS))
        pib_u, pop_u = _sidra(URL_PIB.format(ano="last")), None
        ano = _ano_de(pib_u)
        pop_u = pop_s if ano == ANO_SENTINELAS else _sidra(URL_POP.format(ano=ano))
    except Exception as e:  # recusa, rede fora, JSON inválido: erro de verdade, sem "ok" mascarado
        print(f"ERRO: SIDRA não respondeu ({e}) — nada gravado"); return 1
    recusa = por_que_recusar(per_capita(por_uf(pib_s), por_uf(pop_s)))
    if recusa:
        print(f"ABORTADO: {recusa} — nada gravado"); return 1
    pc = per_capita(por_uf(pib_u), por_uf(pop_u))
    if len(pc) != 27 or not ano:
        print(f"ABORTADO: último ano ({ano or '?'}) com {len(pc)}/27 UFs — nada gravado"); return 1
    fonte = (f"IBGE, Sistema de Contas Regionais {ano} (SIDRA, tabela 5938) e estimativas de população {ano} (tabela 6579); "
             f"construção validada pelas sentinelas oficiais de {ANO_SENTINELAS}")
    gravar_em(DEST, {"completo": True, "ano": ano, "fonte": fonte,
                     "sentinelas_verificadas_2023": {**SENT, "ultima_posicao": "MA"}, "pib_per_capita": pc})   # §229
    # 09/11/2026: a capacidade fiscal de financiamento/por_uf.json só era copiada daqui por `coletar_financiamento.py
    # --semear`, que nenhuma rodada chama — o campo ficaria nulo para sempre mesmo com o dado em casa. Quem produz o
    # número o leva até onde a página lê.
    puf = ler("financiamento/por_uf.json", {}) or {}
    for uf, v in pc.items():
        puf.setdefault("uf", {}).setdefault(uf, {})["capacidade_fiscal"] = {
            "pib_per_capita": v, "ano": ano, "fonte": fonte, "fonte_original": "data/recursos_uf.json"}
    gravar("financiamento/por_uf.json", puf)
    print(f"OK PIB per capita {ano} gravado para 27 UFs, sentinelas {ANO_SENTINELAS} verdes"); return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv or "--self-test" in sys.argv:
        sys.exit(autoteste())
    sys.exit(main())
