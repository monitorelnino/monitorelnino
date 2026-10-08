#!/usr/bin/env python3
"""Auditoria de robustez do índice MARÉ v2.1 — bateria reproduzível.

Executa, sobre os dados publicados em data/, as análises de sensibilidade
recomendadas pelo Handbook OCDE/JRC e pela revisão de literatura v2.1→v2.2:
agregação (linear × geométrica), piso da geométrica, descontos da camada
declarada, esquemas de ponderação (PCA e knockouts), contribuição efetiva à
variância, correlações entre componentes, decomposição da cobertura populacional
por camada, teto de risco de sobreposição da declarada-desatualizada,
convergência e estabilidade de semente do Monte Carlo, e verificações de borda
(teto min(100), régua de antecipação, denominadores IBGE).

Primeira execução: auditoria pré-publicação de 27/08/2026. Os resultados
alimentam o PDF de documentação do índice (gerar_pdf_indice.py), que computa
tudo AO VIVO a partir desta bateria — o PDF não contém número digitado à mão.

Uso:
  python3 analise_sensibilidade.py            # relatório no terminal
  (importado por gerar_pdf_indice.py)         # dicionário de resultados
"""
import json, pathlib, importlib.util
import numpy as np

RAIZ = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location("rm", RAIZ / "recalcular_mare.py")
rm = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rm)


def _spearman(a, b):
    """Coeficiente de correlação de postos de Spearman entre duas listas de mesmo tamanho, sem dependência externa além de numpy."""
    ra = np.argsort(np.argsort(-np.asarray(a, float)))
    rb = np.argsort(np.argsort(-np.asarray(b, float)))
    return float(np.corrcoef(ra, rb)[0, 1])


def _ranks(ufs, tot):
    """Converte uma lista de valores em postos (ranks), com médias para empates, insumo do cálculo de Spearman."""
    ordem = sorted(range(len(ufs)), key=lambda i: -tot[i])
    return {ufs[i]: r for r, i in enumerate(ordem, 1)}


def _shifts(rk, ref, ufs):
    """Conta quantas posições do ranking mudam ao comparar dois orderings do mesmo conjunto de estados."""
    s = [abs(rk[u] - ref[u]) for u in ufs]
    piores = sorted(((abs(rk[u] - ref[u]), u) for u in ufs), reverse=True)[:3]
    return {"mediana": int(np.median(s)), "max": int(max(s)), "piores": piores}


def rodar():
    """Executa a bateria completa de análises de sensibilidade (agregação, piso, pesos, Monte Carlo, bordas) sobre os dados publicados e retorna um dicionário de resultados."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    mun = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    pct = json.load(open(RAIZ / "data" / "percentual_uf.json", encoding="utf-8"))
    import statistics
    idx, media, _, _rob = rm.calcular()  # v2.2.3: calcular() passou a devolver também a robustez MC
    ufs = sorted(rm.ESTADOS)
    # v3.1 (30/09/2026): os componentes passaram a ser instrumento operacional, estrutura de
    # coordenação e cobertura populacional. `estado` e `antecipacao` não existem mais no índice —
    # o tempo saiu da nota e virou indicador à parte (`dias_apos_boletim_1`).
    X = np.array([[idx[u]["instrumento"], idx[u]["estrutura"],
                   idx[u]["cobertura_pop"]] for u in ufs], float)
    pop = json.load(open(RAIZ / "data" / "populacao_censo2022.json", encoding="utf-8"))
    totais, pop_uf, pops_uf, cod_por = {}, {}, {}, {}
    for m in ref:
        totais[m["uf"]] = totais.get(m["uf"], 0) + 1
        p = pop.get(f"{m['codigo_ibge']:07d}", 0)
        pop_uf[m["uf"]] = pop_uf.get(m["uf"], 0) + p
        if p:
            pops_uf.setdefault(m["uf"], []).append(p)
        cod_por[(m["nome"], m["uf"])] = f"{m['codigo_ibge']:07d}"
    med = {u: statistics.median(v) for u, v in pops_uf.items()}
    R = {"media": media, "ufs": ufs, "idx": idx}

    # cobertura populacional recomputável com descontos variáveis (mesma cadeia do motor)
    def contagem_e_peso(uf):
        c, w = {}, 0.0
        for r in mun:
            if r["uf"] == uf:
                c[r["categoria"]] = c.get(r["categoria"], 0) + 1
                w += pop.get(cod_por[(r["nome"], r["uf"])], 0) * rm.CRED_POP.get(r["categoria"], 0.0)
        return c, w

    def cobertura(uf, d_plano=0.5, d_antigo=0.5):
        """A cobertura populacional da UF, pela MESMA função do motor.

        08/10/2026 (A3-05): esta função tinha a conta copiada, e a cópia divergiu — ignorava a
        camada declarada nacional (MUNIC/ICM, ativa desde 21/09) e usava 0,3 para o plano
        desatualizado onde o motor usa 0,5. O PDF público saía com uma tabela de camadas que o
        motor não produz e com um "efeito" de variante que era a própria divergência.
        """
        c, w = contagem_e_peso(uf)
        valor, _ = rm.cobertura_de_uf(uf, c, w, med[uf], pop_uf[uf],
                                      pct[uf].get("declarado_plano", 0) or 0,
                                      pct[uf].get("declarado_antigo", 0) or 0,
                                      rm._declarado_nacional_uf().get(uf, 0),
                                      desconto_plano=d_plano, desconto_antigo=d_antigo)
        return valor

    def camadas_da_uf(uf):
        """(documentado, agregado, declarado) em pontos percentuais da população, pelo motor.

        As três camadas saem da mesma conta, por diferença: documentado é o peso dos registros
        lidos; agregado é o que o excedente agregado acrescenta (RO); declarado é o resto, que é
        o que a camada do levantamento acrescenta. Somadas, dão a cobertura publicada.
        """
        c, w = contagem_e_peso(uf)
        total, _ = rm.cobertura_de_uf(uf, c, w, med[uf], pop_uf[uf],
                                      pct[uf].get("declarado_plano", 0) or 0,
                                      pct[uf].get("declarado_antigo", 0) or 0,
                                      rm._declarado_nacional_uf().get(uf, 0))
        com_agregado, _ = rm.cobertura_de_uf(uf, c, w, med[uf], pop_uf[uf], 0, 0, 0)
        doc_pct = min(100.0, 100.0 * w / pop_uf[uf])
        agr = max(0.0, com_agregado - doc_pct)
        dec = max(0.0, total - com_agregado)
        return round(doc_pct, 1), round(agr, 1), round(dec, 1)

    rank_base = _ranks(ufs, X.mean(axis=1))

    # 1. agregação linear × geométrica (piso 5)
    geo5 = np.exp(np.log(np.maximum(X, 5.0)).mean(axis=1))
    R["agregacao"] = {**_shifts(_ranks(ufs, geo5), rank_base, ufs),
                      "spearman": round(_spearman(X.mean(axis=1), geo5), 3)}

    # 2. piso da geométrica (referência: geo piso 5)
    rk5 = _ranks(ufs, geo5)
    R["piso"] = {}
    for piso in (1.0, 2.5, 10.0):
        g = np.exp(np.log(np.maximum(X, piso)).mean(axis=1))
        R["piso"][piso] = _shifts(_ranks(ufs, g), rk5, ufs)

    # 3. descontos da camada declarada (referência: linear base)
    R["descontos"] = {}
    for dp_, da_, nome in ((0.3, 0.3, "0,5 → 0,3"), (0.7, 0.3, "0,5 → 0,7"),
                           (0.5, 0.2, "0,3 → 0,2"), (0.5, 0.4, "0,3 → 0,4")):
        Xv = X.copy()
        for i, u in enumerate(ufs):
            # v3.1: X = [instrumento, estrutura, cobertura]. A coluna 1 é a
            # ESTRUTURA; escrever a cobertura nela media a sensibilidade da
            # camada declarada sobre o componente errado (A3-05).
            Xv[i, 2] = round(cobertura(u, dp_, da_), 1)
        R["descontos"][nome] = _shifts(_ranks(ufs, Xv.mean(axis=1)), rank_base, ufs)

    # 4. esquemas de ponderação: PCA e knockouts
    Z = (X - X.mean(0)) / X.std(0)
    autoval, autovet = np.linalg.eigh(np.cov(Z.T))
    pc1 = autovet[:, -1]; pc1 = pc1 * np.sign(pc1.sum())
    wp = np.abs(pc1) / np.abs(pc1).sum()
    R["pca"] = {"pesos": [round(float(x), 3) for x in wp],
                "var_explicada": round(float(autoval[-1] / autoval.sum()), 2),
                **_shifts(_ranks(ufs, X @ wp), rank_base, ufs),
                "spearman": round(_spearman(X.mean(axis=1), X @ wp), 3)}
    R["knockouts"] = {}
    for k, nome in enumerate(("instrumento", "estrutura", "cobertura_pop")):
        w = np.full(3, 1 / 2); w[k] = 0
        R["knockouts"][nome] = _shifts(_ranks(ufs, X @ w), rank_base, ufs)

    # 5. contribuição efetiva à variância e correlações
    contrib = ((1 / 3) * X.std(0)) ** 2; contrib = contrib / contrib.sum()
    R["contrib_var"] = [round(float(c), 3) for c in contrib]
    R["correl"] = np.corrcoef(X.T).round(2).tolist()
    R["stats_comp"] = [(round(float(X[:, j].mean()), 1), round(float(X[:, j].std()), 1),
                        round(float(X[:, j].min()), 1), round(float(X[:, j].max()), 1))
                       for j in range(3)]

    # 6. decomposição da cobertura populacional por camada (nominal / agregado / declarada)
    # 08/10/2026 (A3-05): a decomposição sai da MESMA conta do motor. A versão anterior aplicava
    # 0,3 ao plano desatualizado (o motor aplica 0,5) e ignorava a camada nacional, e por isso o
    # PDF público dizia "DF 100 % documentado" onde o motor tem 37 % documentado e 63 % declarado.
    # 08/10/2026 (A3-05): a cobertura por UF e a decomposição em valores ABSOLUTOS saem no
    # resultado, para o portão `verificar_camadas_do_pdf.py` poder compará-las com o que o índice
    # publica. Enquanto a conta só existia dentro do relatório, nada a conferia.
    R["cobertura_por_uf"] = {u: round(cobertura(u), 1) for u in ufs}
    R["camadas_absolutas"] = {u: camadas_da_uf(u) for u in ufs}
    R["camadas"] = {}
    for u in ufs:
        doc_pct, agr_pct, dec_pct = camadas_da_uf(u)
        total = doc_pct + agr_pct + dec_pct
        if total > 1e-9:
            R["camadas"][u] = (round(100 * doc_pct / total), round(100 * agr_pct / total),
                               round(100 * dec_pct / total))

    # 7. teto de risco de sobreposição declarada-desatualizada × plano_antigo documentado
    R["sobreposicao"] = {}
    for u in ufs:
        da = pct[u].get("declarado_antigo", 0) or 0
        if da:
            n_pa = sum(1 for r in mun if r["uf"] == u and r["categoria"] == "plano_antigo")
            R["sobreposicao"][u] = {"declarado_antigo": da, "plano_antigo_doc": n_pa,
                                     "teto_pp": round(100 * n_pa * med[u] * 0.3 / pop_uf[u], 2)}

    # 7b. VARIANTE DE 70% — plano sem ato de aprovação localizado (decisão da editoria, 03/10/2026)
    #
    # A decisão foi: sem degrau novo; o plano publicado em domínio oficial conta no degrau da
    # leitura, com a marca na ficha. A editoria pediu, junto, que a análise de incerteza publicasse
    # a variante em que esses planos valessem **70% do degrau** — e quantas unidades mudariam de
    # faixa. É a pergunta certa a fazer de uma decisão de régua: se o crédito fosse menor, o retrato
    # mudaria? A resposta entra na METODOLOGIA, não na nota.
    #
    # O desconto incide sobre o crédito populacional do município marcado, que é por onde o plano
    # entra na nota do estado. `municipios.json` traz a marca desde 03/10/2026.
    from gerar_monitor_saude import faixa as faixa_canonica
    FATOR_SEM_ATO = 0.7
    marcados = {}
    for r in mun:
        if r.get("sem_ato_de_aprovacao"):
            marcados.setdefault(r["uf"], []).append(r)

    def cobertura_com_desconto_sem_ato(uf, fator=FATOR_SEM_ATO):
        """Cobertura populacional da UF com os planos sem ato valendo `fator` do degrau. Pura."""
        c, w = {}, 0.0
        for r in mun:
            if r["uf"] != uf:
                continue
            c[r["categoria"]] = c.get(r["categoria"], 0) + 1
            credito = rm.CRED_POP.get(r["categoria"], 0.0)
            if r.get("sem_ato_de_aprovacao"):
                credito *= fator
            w += pop.get(cod_por[(r["nome"], r["uf"])], 0) * credito
        # 08/10/2026 (A3-05): a variante comparava a base COM a camada nacional contra uma
        # variante SEM ela, e metade do "efeito" publicado era isso. A conta é a mesma do motor.
        valor, _ = rm.cobertura_de_uf(uf, c, w, med[uf], pop_uf[uf],
                                      pct[uf].get("declarado_plano", 0) or 0,
                                      pct[uf].get("declarado_antigo", 0) or 0,
                                      rm._declarado_nacional_uf().get(uf, 0))
        return valor

    Xv = X.copy()
    mudou_de_faixa, antes_depois = [], {}
    for i, u in enumerate(ufs):
        if u in marcados:
            Xv[i, 2] = round(cobertura_com_desconto_sem_ato(u), 1)
    nota_base = X.mean(axis=1)
    nota_var = Xv.mean(axis=1)
    for i, u in enumerate(ufs):
        # A régua da faixa é a canônica de `gerar_monitor_saude.faixa` — uma definição só para os
        # dois índices, que é o que `scripts/registrar_faixas.py` também usa.
        fa, fb = faixa_canonica(float(nota_base[i])), faixa_canonica(float(nota_var[i]))
        if fa != fb:
            mudou_de_faixa.append(u)
        if abs(nota_base[i] - nota_var[i]) > 0.049:
            antes_depois[u] = (round(float(nota_base[i]), 1), round(float(nota_var[i]), 1))
    R["sem_ato_70"] = {
        "fator": FATOR_SEM_ATO,
        "municipios_marcados": sum(len(v) for v in marcados.values()),
        "ufs_com_marcados": sorted(marcados),
        "ufs_que_mudam_de_nota": antes_depois,
        "ufs_que_mudam_de_faixa": mudou_de_faixa,
        "media_base": round(float(nota_base.mean()), 1),
        "media_variante": round(float(nota_var.mean()), 1),
    }

    # 8. Monte Carlo: estabilidade de semente e convergência
    def mc(seed, n):
        """Roda uma rodada do Monte Carlo com a semente informada, para o teste de estabilidade de semente."""
        rng = np.random.default_rng(seed)
        W = rng.dirichlet(np.ones(3), size=n)
        S = X @ W.T
        order = (-S).argsort(axis=0)
        ranks = np.empty_like(order)
        for j in range(S.shape[1]):
            ranks[order[:, j], j] = np.arange(1, len(ufs) + 1)
        return {u: (int(np.percentile(ranks[i], 5)), int(np.percentile(ranks[i], 95)))
                for i, u in enumerate(ufs)}
    b42 = mc(42, 10000)
    R["mc_sementes"] = max(max(abs(mc(s, 10000)[u][0] - b42[u][0]),
                               abs(mc(s, 10000)[u][1] - b42[u][1]))
                           for s in (7, 123, 2026) for u in ufs)
    m100 = mc(42, 100000)
    R["mc_convergencia"] = max(max(abs(m100[u][0] - b42[u][0]), abs(m100[u][1] - b42[u][1]))
                               for u in ufs)

    # 9. bordas: teto min(100), régua de antecipação, denominadores
    R["teto_ativo"] = [u for u in ufs
                       if 100.0 * (lambda c: sum(rm.PESO_DOC[k] * v for k, v in c.items() if k in rm.PESO_DOC))(
                           {r["categoria"]: sum(1 for x in mun if x["uf"] == u and x["categoria"] == r["categoria"])
                            for r in mun if r["uf"] == u}) / totais[u] > 100]
    R["antecip_valores"] = sorted({v[1] for v in rm.ESTADOS.values()})
    R["malha"] = {"linhas": len(ref), "pe_total": totais["PE"]}
    return R


def main():
    """Executa rodar() e imprime o relatório de sensibilidade formatado no terminal."""
    R = rodar()
    print(f"média nacional: {R['media']:.1f}")
    print(f"1. linear×geométrica: mediana {R['agregacao']['mediana']}, máx {R['agregacao']['max']}, Spearman {R['agregacao']['spearman']}")
    for p, v in R["piso"].items():
        print(f"2. piso {p}: mediana {v['mediana']}, máx {v['max']}")
    for n, v in R["descontos"].items():
        print(f"3. desconto {n}: mediana {v['mediana']}, máx {v['max']}")
    print(f"4. PCA {R['pca']['pesos']} (var. {R['pca']['var_explicada']:.0%}): mediana {R['pca']['mediana']}, máx {R['pca']['max']}, Spearman {R['pca']['spearman']}")
    for n, v in R["knockouts"].items():
        print(f"   knockout {n}: mediana {v['mediana']}, máx {v['max']}")
    print(f"5. contribuição efetiva à variância: {['%.0f%%' % (100*c) for c in R['contrib_var']]}")
    print(f"6. camadas da cobertura populacional: {R['camadas']}")
    print(f"7. sobreposição declarada: {R['sobreposicao']}")
    sa = R["sem_ato_70"]
    print(f"7b. variante 70% (plano sem ato): {sa['municipios_marcados']} município(s) marcado(s) "
          f"em {len(sa['ufs_com_marcados'])} UF(s) · média {sa['media_base']} → "
          f"{sa['media_variante']} · muda de faixa: "
          f"{', '.join(sa['ufs_que_mudam_de_faixa']) or 'nenhuma UF'}")
    if sa["ufs_que_mudam_de_nota"]:
        print(f"    notas que mudam: {sa['ufs_que_mudam_de_nota']}")
    print(f"8. MC: sementes ±{R['mc_sementes']} posição · 10k×100k Δ={R['mc_convergencia']}")
    print(f"9. teto ativo: {R['teto_ativo'] or 'nenhum'} · antecipação {R['antecip_valores']} · malha {R['malha']}")


if __name__ == "__main__":
    main()
