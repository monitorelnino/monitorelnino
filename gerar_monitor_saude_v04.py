#!/usr/bin/env python3
"""
gerar_monitor_saude_v04.py — o MARÉ Saúde v0.4, calculado EM PARALELO
======================================================================
Bloco B do handover do MARÉ Saúde (editoria, 01/10/2026). A v0.4 foi aprovada e a troca foi
autorizada; este arquivo é o que a calcula, e ele roda **ao lado** da v0.3 em vez de substituí-la,
por uma razão de fato que a execução descobriu e que está medida abaixo.

O QUE MUDA DA v0.3 PARA A v0.4
------------------------------
1. **Instrumento na escala de razão declarada**, a mesma da v3.1 do Legal: NOVO 100 · READ 70 ·
   recorrente que cobre o risco e tem revisão datada em 2026 (`VIG_REVISADO`) 55 · recorrente que
   cobre sem revisão (`VIG`) 30 · em elaboração 20 · plano de outro risco (`VIG_OUTRO_RISCO`) 0 ·
   nada 0. Cada degrau é uma afirmação sobre o documento, não um lugar numa fila.
2. **Coordenação na saúde** passa a ser componente: sala de situação ou centro de operações de
   emergência criado para o ciclo 100 · reativado 65 · permanente, sem ato do ciclo 45 ·
   anunciado 35 · nada 0. É o que de fato opera a resposta, e não estava no índice.
3. **O tempo sai da nota** e passa a indicador publicado à parte (dias desde o Boletim nº 1),
   pela mesma razão do C27: publicar cedo é atributo de conduta, não do arcabouço.

Um terço para cada um dos três.

POR QUE EM PARALELO, E NÃO NO LUGAR
-----------------------------------
A v0.4 exige a coordenação, e a coordenação **não tem verificação em nenhum dos 27 estados**:
`data/saude_uf.json` nunca teve esse campo, porque o componente nasceu hoje. Trocar agora deixaria
duas saídas possíveis, e as duas são proibidas: somar um terço de zero (afirmar que o estado não
tem sala de situação porque ninguém procurou) ou publicar a página sem número (apagar o índice que
já existe). A regra do projeto é a primeira que ele tem — lacuna não é zero —, e por isso a v0.3
continua no ar enquanto a bateria de saúde estadual (`coletar_saude_estadual.py`, duas das suas oito
consultas são `sala de situação` e `centro de operações`) não trouxer os documentos.

Este arquivo grava `data/monitor_saude_v04.json`, que a página NÃO lê. Ele existe para que a troca
seja um ajuste de leitura quando a coordenação estiver verificada, e para que a comparação esteja
publicada antes, não depois.

ROBUSTEZ
--------
Monte Carlo de 10 mil sorteios Dirichlet(1,1,1) com semente 42 — a mesma do índice principal, para
que as duas auditorias sejam comparáveis — e sensibilidade de ±15 pontos por degrau da escala do
instrumento, que é o que o handover pede. Peso zero no MARÉ: nada aqui entra em `indice.json`.

USO
  python gerar_monitor_saude_v04.py --autoteste
  python gerar_monitor_saude_v04.py --comparar     # v0.3 × v0.4, sem gravar
  python gerar_monitor_saude_v04.py --write
"""
import json
import pathlib
import sys

import numpy as np

import gerar_monitor_saude as v03
from coletores_base import gravar, ler

RAIZ = pathlib.Path(__file__).resolve().parent
SAIDA = "monitor_saude_v04.json"
SEMENTE = 42
SORTEIOS = 10000
PASSO_SENSIBILIDADE = 15


def componentes_por_uf(su: dict, cob: dict) -> dict:
    """{UF: {...}} com os três componentes da v0.4 e o indicador de tempo. Função pura.

    `prontidao` é None quando instrumento ou coordenação não foram verificados — e o motivo fica
    escrito no próprio registro, porque "sem número" sem motivo é indistinguível de erro."""
    from migrar_saude_instrumentos import melhor_instrumento
    saida = {}
    for uf in v03.UFS:
        u = (su.get("uf") or {}).get(uf, {})
        melhor = melhor_instrumento(u.get("instrumentos") or []) or u
        camada = u.get("camada") or "ciclo"
        degrau = v03.instrumento_v04(melhor.get("status"), melhor.get("doc") or "",
                                     melhor.get("data") or "", u.get("consist"))
        coord = (u.get("coordenacao") or {}).get("status") or "NAO_VERIFICADO"
        cobertura = (cob.get(uf) or {}).get("cobertura", 0.0)
        total, pi, pk, pc = v03.prontidao_v04(degrau, coord, cobertura, camada)
        faltam = []
        if degrau not in v03.INSTRUMENTO_SCORE_V04:
            faltam.append("instrumento estadual não verificado")
        if coord not in v03.COORDENACAO_SCORE_V04:
            faltam.append("coordenação em saúde não verificada")
        if camada == "adaptacao":
            faltam.append("instrumento é plano de adaptação decenal, que não é do ciclo")
        saida[uf] = {
            "prontidao": total, "faixa": v03.faixa(total),
            "instrumento": {"degrau": degrau, "pontos": pi, "doc": melhor.get("doc"),
                            "data": melhor.get("data"), "url": melhor.get("url")},
            "coordenacao": {"degrau": coord, "pontos": pk,
                            "doc": (u.get("coordenacao") or {}).get("doc"),
                            "data": (u.get("coordenacao") or {}).get("data"),
                            "url": (u.get("coordenacao") or {}).get("url")},
            "cobertura": {"pontos": pc, "cobertura_pct": cobertura,
                          "planos_lidos": (cob.get(uf) or {}).get("planos_lidos"),
                          "planos_sem_leitura": (cob.get(uf) or {}).get("planos_sem_leitura")},
            # INDICADOR, não componente: não entra na nota.
            "dias_apos_boletim_1": v03.dias_apos_boletim_1(melhor.get("data") or ""),
            "sem_numero_porque": faltam or None,
        }
    return saida


def robustez(comp: dict) -> dict:
    """Monte Carlo e sensibilidade sobre as UFs que TÊM número. Determinística pela semente.

    Sem UF com número, devolve a lacuna declarada em vez de um dicionário de zeros: uma auditoria
    de robustez sobre conjunto vazio não é uma auditoria com resultado zero."""
    com_numero = [uf for uf, v in comp.items() if v["prontidao"] is not None]
    if not com_numero:
        return {"ufs_com_numero": 0,
                "motivo": ("auditoria não executada: nenhuma UF tem os três componentes "
                           "verificados — a coordenação em saúde nasceu na v0.4 e ainda não foi "
                           "coletada em nenhum estado"),
                "monte_carlo": None, "sensibilidade": None}
    X = np.array([[comp[uf]["instrumento"]["pontos"], comp[uf]["coordenacao"]["pontos"],
                   comp[uf]["cobertura"]["pontos"]] for uf in com_numero], float)
    rng = np.random.default_rng(SEMENTE)
    W = rng.dirichlet(np.ones(3), size=SORTEIOS)
    S = X @ W.T
    mc = {uf: {"mediana": round(float(np.median(S[i])), 1),
               "p05": round(float(np.percentile(S[i], 5)), 1),
               "p95": round(float(np.percentile(S[i], 95)), 1)}
          for i, uf in enumerate(com_numero)}
    # Sensibilidade: ±15 em CADA degrau da escala do instrumento, um por vez, e quantas UFs mudam
    # de faixa. É o teste que o handover pede, e o que ele mede é se a faixa publicada depende de
    # um degrau escolhido — se depender, o degrau é frágil e isso tem de estar publicado.
    sens = {}
    for degrau, base in v03.INSTRUMENTO_SCORE_V04.items():
        for sinal in (-PASSO_SENSIBILIDADE, PASSO_SENSIBILIDADE):
            escala = dict(v03.INSTRUMENTO_SCORE_V04)
            escala[degrau] = max(0, min(100, base + sinal))
            mudam = []
            for uf in com_numero:
                c = comp[uf]
                novo = (escala.get(c["instrumento"]["degrau"], 0) + c["coordenacao"]["pontos"]
                        + c["cobertura"]["pontos"]) / 3.0
                if v03.faixa(round(novo, 1)) != c["faixa"]:
                    mudam.append(uf)
            sens[f"{degrau}{sinal:+d}"] = {"ufs_que_mudam_de_faixa": mudam, "n": len(mudam)}
    return {"ufs_com_numero": len(com_numero), "monte_carlo": mc, "sensibilidade": sens,
            "metodo": (f"Monte Carlo {SORTEIOS} sorteios Dirichlet(1,1,1) semente {SEMENTE} — a mesma "
                       f"do índice principal, para que as duas auditorias sejam comparáveis; "
                       f"sensibilidade de ±{PASSO_SENSIBILIDADE} pontos por degrau do instrumento")}


def comparar(su: dict, cob: dict, comp: dict) -> dict:
    """A comparação v0.3 × v0.4, componente a componente. Função pura.

    Compara o que HÁ para comparar: o componente do instrumento, que existe nas duas versões. O
    índice inteiro não se compara hoje, porque a v0.4 não tem número em UF nenhuma — e dizer isso é
    a comparação honesta, não a sua ausência."""
    from migrar_saude_instrumentos import melhor_instrumento
    linhas, muda = [], 0
    soma3 = soma4 = n = 0
    for uf in v03.UFS:
        u = (su.get("uf") or {}).get(uf, {})
        melhor = melhor_instrumento(u.get("instrumentos") or []) or u
        st = melhor.get("status")
        if st not in v03.PONTOS_STATUS:
            continue
        p3 = v03.PONTOS_STATUS[st]
        degrau = comp[uf]["instrumento"]["degrau"]
        p4 = v03.INSTRUMENTO_SCORE_V04.get(degrau)
        if p4 is None:
            continue
        n += 1; soma3 += p3; soma4 += p4
        if p3 != p4:
            muda += 1
            linhas.append({"uf": uf, "status_v03": st, "pontos_v03": p3,
                           "degrau_v04": degrau, "pontos_v04": p4})
    return {
        "ufs_com_instrumento_verificado": n,
        "ufs_que_mudam_de_pontuacao_do_instrumento": muda,
        "media_do_componente_instrumento": {"v0_3": round(soma3 / n, 1) if n else None,
                                            "v0_4": round(soma4 / n, 1) if n else None},
        "por_uf": linhas,
        "indice_inteiro": ("não comparável hoje: a v0.4 não produz número em nenhuma UF, porque a "
                           "coordenação em saúde nasceu nesta versão e ainda não foi verificada em "
                           "nenhum estado"),
        "ufs_com_numero_na_v04": sum(1 for v in comp.values() if v["prontidao"] is not None),
        "ufs_com_coordenacao_verificada": sum(
            1 for uf in v03.UFS
            if ((su.get("uf") or {}).get(uf, {}).get("coordenacao") or {}).get("status")
            in v03.COORDENACAO_SCORE_V04),
    }


def montar() -> dict:
    su = ler("saude_uf.json", {}) or {}
    from recalcular_mare import CRED_POP
    cob = v03.cobertura_sanitaria(
        ler("municipios.json", []) or [], ler("municipios_ibge_referencia.json", []) or [],
        ler("populacao_censo2022.json", {}) or {},
        (ler("saude_no_plano_auto.json", {}) or {}).get("itens") or {},
        (ler("saude_no_plano.json", {}) or {}).get("leituras") or [], CRED_POP)
    comp = componentes_por_uf(su, cob)
    return {
        "_governanca": (
            "MARÉ Saúde v0.4, calculado EM PARALELO e NÃO publicado (01/10/2026). A página lê "
            "data/monitor_saude.json, que é a v0.3. A v0.4 foi aprovada pela editoria e a troca foi "
            "autorizada; ela espera a verificação do componente de COORDENAÇÃO EM SAÚDE, que nasceu "
            "nesta versão e não existe em nenhum dos 27 estados. Trocar antes disso exigiria somar "
            "um terço de zero — afirmar que o estado não tem sala de situação porque ninguém "
            "procurou — ou apagar o índice da página. Peso zero no MARÉ: nunca lido por "
            "recalcular_mare.py nem por gerar_monitor_saude.py."),
        "versao": v03.VERSAO_V04,
        "gerado_em": v03._hoje().strftime("%d/%m/%Y"),
        "corte": su.get("corte"),
        "metodo": {
            "pesos": dict(v03.PESOS_V04),
            "instrumento": dict(v03.INSTRUMENTO_SCORE_V04),
            "coordenacao": dict(v03.COORDENACAO_SCORE_V04),
            "cobertura": "igual à v0.3: população em município cujo plano localizado trata a saúde",
            "tempo": ("fora do índice; publicado à parte como `dias_apos_boletim_1`, negativo "
                      "quando o ato é anterior ao Boletim nº 1"),
            "faixas": {"estágio inicial": "0–25", "em construção": "25–50",
                       "consolidado": "50–70", "avançado": "70–100"},
        },
        "uf": comp,
        "comparacao_v03_v04": comparar(su, cob, comp),
        "robustez": robustez(comp),
    }


def autoteste() -> int:
    from coletores_base import rodar_autoteste
    comp_vazio = {uf: {"prontidao": None} for uf in v03.UFS}
    comp_cheio = {
        "AC": {"prontidao": 70.0, "faixa": "avançado",
               "instrumento": {"degrau": "NOVO", "pontos": 100},
               "coordenacao": {"degrau": "CRIADO_CICLO", "pontos": 100},
               "cobertura": {"pontos": 10.0}},
        "AL": {"prontidao": 30.0, "faixa": "em construção",
               "instrumento": {"degrau": "VIG", "pontos": 30},
               "coordenacao": {"degrau": "PERMANENTE", "pontos": 45},
               "cobertura": {"pontos": 15.0}},
    }
    r_vazio = robustez(comp_vazio)
    r_cheio = robustez(comp_cheio)
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    # Os alvos proibidos são MONTADOS por pedaços, de propósito: escritos inteiros, eles apareceriam
    # no texto que a própria trava procura, e a trava reprovaria por se encontrar — foi o que
    # aconteceu na primeira versão dela no coletor de saúde estadual.
    def grava_em(nome):
        return ("grav" + "ar(\"" + nome) in fonte

    casos = {
        "a escala do instrumento é a da v3.1 do Legal, com o degrau de outro risco em zero":
            lambda: (v03.INSTRUMENTO_SCORE_V04["NOVO"] == 100
                     and v03.INSTRUMENTO_SCORE_V04["READ"] == 70
                     and v03.INSTRUMENTO_SCORE_V04["VIG_REVISADO"] == 55
                     and v03.INSTRUMENTO_SCORE_V04["VIG"] == 30
                     and v03.INSTRUMENTO_SCORE_V04["ELAB"] == 20
                     and v03.INSTRUMENTO_SCORE_V04["VIG_OUTRO_RISCO"] == 0),
        "a escala da coordenação é a aprovada":
            lambda: v03.COORDENACAO_SCORE_V04 == {"CRIADO_CICLO": 100, "REATIVADO_CICLO": 65,
                                                  "PERMANENTE": 45, "ANUNCIADO": 35, "LAC": 0},
        "os três componentes valem um terço cada":
            lambda: (len(v03.PESOS_V04) == 3
                     and all(abs(p - 1 / 3) < 1e-9 for p in v03.PESOS_V04.values())),
        "o tempo não é componente":
            lambda: "antecipacao" not in v03.PESOS_V04 and "tempo" not in v03.PESOS_V04,
        # A trava central da v0.4: sem coordenação verificada NÃO existe número. Somar um terço de
        # zero seria afirmar ausência de sala de situação por ausência de busca.
        "sem coordenação verificada a UF não recebe número":
            lambda: v03.prontidao_v04("NOVO", "NAO_VERIFICADO", 50.0)[0] is None,
        "sem instrumento verificado a UF não recebe número":
            lambda: v03.prontidao_v04("NAO_VERIFICADO", "PERMANENTE", 50.0)[0] is None,
        "coordenação LAC é zero verificado, e produz número":
            lambda: v03.prontidao_v04("NOVO", "LAC", 0.0)[0] == round(100 / 3, 1),
        "plano de adaptação decenal não recebe número":
            lambda: v03.prontidao_v04("NOVO", "CRIADO_CICLO", 50.0, "adaptacao")[0] is None,
        "o degrau VIG se divide pelo que foi verificado":
            lambda: (v03.instrumento_v04("VIG", "Plano 2026/2027", "10/02/2026", "NEUTRO") == "VIG_REVISADO"
                     and v03.instrumento_v04("VIG", "Plano de arboviroses", "05/2025", "NEUTRO") == "VIG"
                     and v03.instrumento_v04("VIG", "Plano hidrológico", "01/2026", "DIFERE") == "VIG_OUTRO_RISCO"),
        "NEUTRO não rebaixa o instrumento":
            lambda: v03.instrumento_v04("VIG", "Plano 2026/2027", "10/02/2026", "NEUTRO") != "VIG_OUTRO_RISCO",
        "NOVO, READ, ELAB e LAC passam direto":
            lambda: all(v03.instrumento_v04(x, "", "", "COBRE") == x
                        for x in ("NOVO", "READ", "ELAB", "LAC")),
        "o indicador de tempo é negativo antes do boletim e nulo sem dia":
            lambda: (v03.dias_apos_boletim_1("08/06/2026") < 0
                     and v03.dias_apos_boletim_1("03/2026") is None
                     and v03.dias_apos_boletim_1("") is None),
        # Robustez sobre conjunto vazio é lacuna declarada, não resultado zero.
        "robustez sem UF com número declara a lacuna":
            lambda: (r_vazio["ufs_com_numero"] == 0 and r_vazio["monte_carlo"] is None
                     and "não executada" in r_vazio["motivo"]),
        "robustez com UF roda Monte Carlo e sensibilidade":
            lambda: (r_cheio["ufs_com_numero"] == 2 and set(r_cheio["monte_carlo"]) == {"AC", "AL"}
                     and all(k in r_cheio["sensibilidade"] for k in ("NOVO+15", "NOVO-15", "VIG+15"))),
        "a semente é a mesma do índice principal, e o Monte Carlo reproduz":
            lambda: (SEMENTE == 42
                     and robustez(comp_cheio)["monte_carlo"] == r_cheio["monte_carlo"]),
        "a sensibilidade cobre os dois sinais de cada degrau":
            lambda: len(r_cheio["sensibilidade"]) == 2 * len(v03.INSTRUMENTO_SCORE_V04),
        # TRAVA ESTRUTURAL: este arquivo não pode ganhar, numa edição futura, uma escrita no índice
        # publicado nem no arquivo que a página lê.
        "o fonte grava só pela constante de saída":
            lambda: ("grav" + "ar(SAIDA") in fonte and not grava_em("monitor_saude.json"),
        "o fonte não escreve no índice nem na camada estadual":
            lambda: not any(grava_em(n) for n in ("indice", "saude_uf", "estados", "municipios")),
        "a constante de saída é o arquivo paralelo, que a página não lê":
            lambda: SAIDA == "monitor_saude_v04.json",
    }
    return rodar_autoteste(casos)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    dados = montar()
    if "--comparar" in args:
        c = dados["comparacao_v03_v04"]
        print(json.dumps(c, ensure_ascii=False, indent=1))
        print(f"\nrobustez: {dados['robustez']['ufs_com_numero']} UF(s) com número")
        return 0
    if "--write" in args:
        gravar(SAIDA, dados)
        c = dados["comparacao_v03_v04"]
        print(f"data/{SAIDA} gravado · v0.4 em paralelo, não publicada · "
              f"{c['ufs_com_numero_na_v04']} UF(s) com número · "
              f"componente instrumento {c['media_do_componente_instrumento']['v0_3']} → "
              f"{c['media_do_componente_instrumento']['v0_4']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
