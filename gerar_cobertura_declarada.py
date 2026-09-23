#!/usr/bin/env python3
"""Cobertura declarada por UF e por canal (§166, 23/09/2026) — ESTRUTURA, sem texto público.

O PROBLEMA QUE ISTO RESOLVE. Hoje o site afirma "não localizamos até o corte" sem dizer
ONDE se procurou. O caso do painel do AM (§164/§165) mostrou que a frase valia menos do
que parecia: o plano estava publicado, num canal que a varredura textual não alcança. Uma
afirmação de ausência sem escopo declarado é uma afirmação que o leitor não pode auditar.

O QUE ESTE SCRIPT FAZ: deriva, de data/log_buscas.json (o log v2 que todo coletor já
alimenta), quais CANAIS foram verificados em cada UF e quando. Não pergunta nada de novo
aos coletores e não cria um segundo lugar onde a verdade mora — se o log não registrou,
aqui aparece como não verificado, que é a resposta honesta.

O QUE ESTE SCRIPT NÃO FAZ — e por quê:
  • Não escreve texto público. `nota_publica` nasce null DE PROPÓSITO: a redação da nota
    que aparece na ficha de cada estado é decisão da editoria (Patricia), não do robô.
  • Não toca em página nenhuma. A exposição na ficha do estado entra quando a editoria
    escrever a frase; até lá isto é estrutura pronta e inerte.
  • Não reproduz pedido de LAI. O canal `lai` existe no esquema porque é um canal real de
    verificação, mas é alimentado à mão e guarda só data e status — nunca texto ou registro
    de pedido (regra editorial vigente).
  • Não entra na cadeia canônica de derivados enquanto for inerte: regenerar é sob demanda
    (`python3 gerar_cobertura_declarada.py`), para não publicar por inércia o que ainda
    aguarda decisão editorial.

Uso: python3 gerar_cobertura_declarada.py [--saida data/cobertura_declarada_uf.json]
     python3 gerar_cobertura_declarada.py --autoteste
"""
import sys
from collections import defaultdict

from coletores_base import hoje, ler, gravar, rodar_autoteste

SAIDA = "cobertura_declarada_uf.json"

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
       "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Canal do log v2 → classe de canal que o leitor entende. Declarado, não escondido: canal
# do log que não esteja aqui cai em "outro" e aparece no relatório, em vez de sumir.
CLASSES = {
    "DOM": "diario_oficial",
    "DOU": "diario_oficial",
    "site_estadual": "sitio_do_orgao",
    "site_municipal": "sitio_do_orgao",
    "orgao_estadual": "sitio_do_orgao",
    "repositorio_estadual": "sitio_do_orgao",
    "busca_web": "busca_web",
    "motor_de_busca": "busca_web",
    "descobrir_planos": "busca_web",
    "sonda de painéis": "painel",
    "painel AM": "painel",
}

# Ordem estável na saída. `lai` e `portal_transparencia` entram no esquema mesmo sem
# registro no log: um canal que nunca foi verificado precisa aparecer como NÃO verificado —
# é exatamente essa a informação que faltava ao leitor.
CANAIS = ["diario_oficial", "sitio_do_orgao", "painel", "portal_transparencia",
          "busca_web", "lai", "outro"]

# Um canal só "cobre" a UF se a execução chegou a olhar. Erro de acesso e fonte suspensa
# contam como TENTATIVA, nunca como verificação — senão a nota de rodapé mentiria de novo,
# só que com mais detalhe.
DECISOES_QUE_VERIFICAM = {"registro", "pista", "nada localizado", "coberto_sem_mencao",
                          "com_excerto", "sem_cobertura_qd",
                          # §184: a sonda de UF que consultou a fonte e não achou OLHOU — é o oposto
                          # de tentativa frustrada. Fica aqui pela mesma razão que "nada localizado".
                          "consultado sem achado"}


def classe_do_canal(canal: str) -> str:
    return CLASSES.get(canal, "outro")


def verificou(decisao: str) -> bool:
    d = (decisao or "").strip()
    return any(d == v or d.startswith(v) for v in DECISOES_QUE_VERIFICAM)


def derivar(execucoes: list) -> dict:
    """log v2 → {uf: {canal: {ultima_verificacao, execucoes, verificacoes, ultima_tentativa}}}."""
    acc = defaultdict(lambda: defaultdict(lambda: {
        "ultima_verificacao": None, "ultima_tentativa": None,
        "execucoes": 0, "verificacoes": 0, "canais_do_log": set()}))
    for e in execucoes:
        uf = e.get("uf")
        if uf not in UFS:
            continue                       # execução nacional ou sem UF: não vira cobertura de UF
        canal = classe_do_canal(e.get("canal"))
        c = acc[uf][canal]
        c["execucoes"] += 1
        c["canais_do_log"].add(e.get("canal"))
        data = e.get("data")
        if data and (c["ultima_tentativa"] or "") < data:
            c["ultima_tentativa"] = data
        if verificou(e.get("decisao")):
            c["verificacoes"] += 1
            if data and (c["ultima_verificacao"] or "") < data:
                c["ultima_verificacao"] = data

    saida = {}
    for uf in UFS:
        por_canal = {}
        for canal in CANAIS:
            c = acc[uf].get(canal)
            if not c:
                por_canal[canal] = {"verificado": False, "ultima_verificacao": None,
                                    "ultima_tentativa": None, "execucoes": 0,
                                    "verificacoes": 0, "canais_do_log": []}
            else:
                por_canal[canal] = {
                    "verificado": c["verificacoes"] > 0,
                    "ultima_verificacao": c["ultima_verificacao"],
                    "ultima_tentativa": c["ultima_tentativa"],
                    "execucoes": c["execucoes"],
                    "verificacoes": c["verificacoes"],
                    "canais_do_log": sorted(x for x in c["canais_do_log"] if x)}
        saida[uf] = {"canais": por_canal,
                     "n_canais_verificados": sum(1 for v in por_canal.values() if v["verificado"])}
    return saida


def construir() -> dict:
    lg = ler("log_buscas.json") or {"execucoes": []}
    ufs = derivar(lg.get("execucoes", []))
    return {
        "_governanca": (
            "Cobertura declarada por UF e por canal (§166, 23/09/2026). DERIVADO de "
            "data/log_buscas.json — não editar à mão; rode gerar_cobertura_declarada.py. "
            "Serve para que 'não localizamos até o corte' passe a ter escopo explícito: o "
            "leitor vê em que canais se procurou e quando. Canal com verificado=false NUNCA "
            "pode ser apresentado como ausência de plano. O canal 'lai' guarda só data e "
            "status, jamais texto ou registro de pedido (regra editorial). ESTRUTURA INERTE: "
            "nenhuma página lê este arquivo até a editoria escrever a nota pública."),
        "gerado_em": hoje(),
        "fonte": "data/log_buscas.json (log v2)",
        # Em branco de propósito: a frase que vai à ficha do estado é da editoria.
        "nota_publica": None,
        "canais": CANAIS,
        "ufs": ufs,
    }


def autoteste() -> int:
    LOG = [
        {"uf": "AM", "canal": "DOM", "data": "2026-09-01", "decisao": "coberto_sem_mencao"},
        {"uf": "AM", "canal": "DOM", "data": "2026-09-20", "decisao": "erro"},
        {"uf": "AM", "canal": "painel AM", "data": "2026-09-23", "decisao": "pista"},
        {"uf": "BA", "canal": "busca_web", "data": "2026-09-10", "decisao": "registro"},
        {"uf": None, "canal": "DOU", "data": "2026-09-11", "decisao": "registro"},
    ]

    def t_erro_nao_conta_como_verificacao():
        """A regra que impede a nota de rodapé de repetir o erro que ela corrige: tentativa
        que falhou é tentativa, não verificação."""
        c = derivar(LOG)["AM"]["canais"]["diario_oficial"]
        return (c["verificado"] is True and c["ultima_verificacao"] == "2026-09-01"
                and c["ultima_tentativa"] == "2026-09-20" and c["execucoes"] == 2)

    def t_so_erro_nao_verifica():
        c = derivar([{"uf": "AC", "canal": "DOM", "data": "2026-09-01", "decisao": "erro"}])
        a = c["AC"]["canais"]["diario_oficial"]
        return a["verificado"] is False and a["ultima_verificacao"] is None and a["execucoes"] == 1

    def t_canal_nunca_visto_aparece_como_nao_verificado():
        """O ponto de Tarefa C: canal ausente tem de APARECER como não verificado, em vez
        de sumir do relatório."""
        c = derivar(LOG)["AM"]["canais"]
        return (set(c) == set(CANAIS) and c["lai"]["verificado"] is False
                and c["portal_transparencia"]["execucoes"] == 0)

    def t_painel_entra_como_canal_proprio():
        return derivar(LOG)["AM"]["canais"]["painel"]["verificado"] is True

    def t_execucao_sem_uf_nao_vira_cobertura():
        return all(u["canais"]["diario_oficial"]["execucoes"] == 0
                   for k, u in derivar(LOG).items() if k not in ("AM",))

    def t_todas_as_27_ufs_saem():
        d = derivar(LOG)
        return len(d) == 27 and "AM" in d and "DF" in d

    def t_canal_desconhecido_cai_em_outro():
        d = derivar([{"uf": "TO", "canal": "canal_novo_qualquer", "data": "2026-09-01",
                      "decisao": "pista"}])
        c = d["TO"]["canais"]["outro"]
        return c["verificado"] is True and c["canais_do_log"] == ["canal_novo_qualquer"]

    def t_nota_publica_nasce_em_branco():
        """Contrato com a editoria: o robô monta a estrutura e NÃO escreve a frase."""
        return construir()["nota_publica"] is None

    return rodar_autoteste({
        "erro é tentativa, não verificação": t_erro_nao_conta_como_verificacao,
        "canal só com erro fica não verificado": t_so_erro_nao_verifica,
        "canal nunca visto aparece como não verificado": t_canal_nunca_visto_aparece_como_nao_verificado,
        "painel é canal próprio na cobertura": t_painel_entra_como_canal_proprio,
        "execução sem UF não vira cobertura de UF": t_execucao_sem_uf_nao_vira_cobertura,
        "saem as 27 UFs, sempre": t_todas_as_27_ufs_saem,
        "canal desconhecido cai em 'outro' (não some)": t_canal_desconhecido_cai_em_outro,
        "nota pública nasce em branco (é da editoria)": t_nota_publica_nasce_em_branco,
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    d = construir()
    gravar(SAIDA, d)
    print(f"Cobertura declarada por canal — data/{SAIDA} (derivado de {d['fonte']}).\n")
    print(f"{'UF':4} {'canais':>7}  detalhe")
    for uf, v in d["ufs"].items():
        vistos = [c for c, x in v["canais"].items() if x["verificado"]]
        print(f"{uf:4} {v['n_canais_verificados']:>3}/{len(CANAIS):<3}  "
              + (", ".join(vistos) if vistos else "— nenhum canal verificado —"))
    nunca = [uf for uf, v in d["ufs"].items() if v["n_canais_verificados"] == 0]
    print(f"\nUFs sem nenhum canal verificado: {len(nunca)}"
          + (f" ({', '.join(nunca)})" if nunca else ""))
    print("nota_publica segue null: a redação da nota na ficha do estado é da editoria.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
