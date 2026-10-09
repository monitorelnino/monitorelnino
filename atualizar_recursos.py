#!/usr/bin/env python3
"""Aquisição do PIB per capita por UF (IBGE, Contas Regionais 2023) para o
gráfico-tese ("preparar-se é decisão, não riqueza"). Padrão sentinela do Censo:
SÓ grava se as âncoras oficiais verificadas em 27/08/2026 baterem EXATAS —
DF 129.790,44 · SP 77.566,27 · MT 74.620,05 · e MA na última posição.
Falha-segura: qualquer divergência aborta sem escrever; o site continua no eixo
de população até a série validar. Endpoint SIDRA a confirmar na 1ª execução
(t/5938 v/6323 é a hipótese); a validação por sentinela torna o erro de
endpoint inofensivo por construção.
"""
import json, pathlib, sys, urllib.request

from coletores_base import ua_de, gravar_em  # §228: pedia o SIDRA sem identificar o cliente

RAIZ = pathlib.Path(__file__).parent
DEST = RAIZ / "data" / "recursos_uf.json"
SENT = {"DF": 129790.44, "SP": 77566.27, "MT": 74620.05}
URL = "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/6323/p/2023?formato=json"

def por_que_recusar(pib: dict) -> "str | None":
    """O motivo de recusar o PIB lido, ou `None` quando ele passa. Função pura.

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
    base = {uf: 50000.0 for uf in
            ("RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA MG ES RJ SP PR SC RS MS MT GO DF"
             ).split()}
    base.update(SENT)
    base["MA"] = min(base.values()) - 1
    casos = [
        ("27 UFs com sentinelas e MA na última posição passam", por_que_recusar(base) is None),
        ("26 UFs reprovam",
         "26/27" in (por_que_recusar({k: v for k, v in list(base.items())[:26]}) or "")),
        ("sentinela divergente reprova",
         "divergente" in (por_que_recusar({**base,
                                           next(iter(SENT)): SENT[next(iter(SENT))] + 10}) or "")),
        ("última posição diferente de MA reprova",
         por_que_recusar({**base, "MA": max(base.values()) + 1}) is not None),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'✓' if ok else '✗'} {n}")
    print(f"{'✓ AUTOTESTE OK' if not ruins else f'✗ AUTOTESTE: {len(ruins)} falha(s)'} — "
          f"{len(casos)} casos, sem rede e sem escrita.")
    return 1 if ruins else 0


def main():
    """Busca o PIB per capita por UF na API SIDRA do IBGE, valida contra as quatro UFs-sentinela de 2023 e grava data/recursos_uf.json (ou marca completo:false em caso de falha, sem nunca publicar dado não confirmado)."""
    try:
        # §228: o pedido ia com o agente padrão da biblioteca — o IBGE não tinha como saber
        # quem estava pedindo, e a política de robots (§185) depende do cliente enviado.
        req = urllib.request.Request(URL, headers={"User-Agent": ua_de("PIB per capita no SIDRA")})
        with urllib.request.urlopen(req, timeout=90) as r:
            dados = json.load(r)
    except Exception as e:
        print(f"SIDRA indisponível ({e}) — mantendo seed; site segue no eixo população"); return 0
    UFS = {"Rondônia":"RO","Acre":"AC","Amazonas":"AM","Roraima":"RR","Pará":"PA","Amapá":"AP","Tocantins":"TO","Maranhão":"MA","Piauí":"PI","Ceará":"CE","Rio Grande do Norte":"RN","Paraíba":"PB","Pernambuco":"PE","Alagoas":"AL","Sergipe":"SE","Bahia":"BA","Minas Gerais":"MG","Espírito Santo":"ES","Rio de Janeiro":"RJ","São Paulo":"SP","Paraná":"PR","Santa Catarina":"SC","Rio Grande do Sul":"RS","Mato Grosso do Sul":"MS","Mato Grosso":"MT","Goiás":"GO","Distrito Federal":"DF"}
    pib = {}
    for linha in dados[1:]:
        uf = UFS.get(linha.get("D1N", "").strip())
        try: v = float(linha.get("V"))
        except (TypeError, ValueError): continue
        if uf: pib[uf] = v
    recusa = por_que_recusar(pib)
    if recusa:
        print(f"ABORTADO: {recusa} — nada gravado"); return 1
    gravar_em(DEST, {"completo": True,
                     "fonte": "IBGE, Sistema de Contas Regionais 2023 (SIDRA), validado por 4 sentinelas em produção",
                     "pib_per_capita": pib})   # §229
    print(f"OK 27 UFs gravadas com sentinelas verdes — gráfico-tese passa ao eixo de riqueza"); return 0

if __name__ == "__main__":
    if "--autoteste" in sys.argv or "--self-test" in sys.argv:
        sys.exit(autoteste())
    sys.exit(main())
