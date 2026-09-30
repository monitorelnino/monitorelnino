#!/usr/bin/env python3
"""Portão — o contador da varredura precisa classificar POSITIVAMENTE, e bater com o log.

Criado em 20/09/2026 (§121). Até ali `recalcular_mare.py` contava como "sem menção" o
município cujo resultado começasse com a string `"sem edições"` — string que
`coletar_diarios_municipais.py` nunca gravou. Efeito: nenhum município caía em
`sem_mencao`, `com_mencao` igualava `consultados`, e o número publicado na cortina do
domínio afirmava que **3.180 municípios tinham menção a El Niño** quando eram **153**.
A Action ficava verde: nada falhava, a conta só media outra coisa.

REESCRITO EM 28/09/2026 (§280), PORQUE ESTE PORTÃO PASSOU VERDE SOBRE O MESMO DEFEITO
-------------------------------------------------------------------------------------
O §121 trocou os prefixos errados pelos certos e manteve a definição por EXCLUSÃO:
`com_mencao` era tudo o que não começasse por um de três prefixos. Este portão conferia
a assinatura do defeito antigo (`com_mencao == consultados`) em vez da propriedade, e
por isso não viu quando `sem_edicao_no_periodo` — decisão criada pelo §194 — passou a
entrar na conta pública de menções: 347 publicados contra 260 reais.

O portão agora faz três coisas diferentes disso:

1. Recomputa os cinco estados por conta própria, a partir de `fontes_consultadas.json`,
   e exige que o resumo publicado concorde. Dois códigos independentes, um número.
2. Reconcilia `com_mencao` contra o **log**, que é outro arquivo e outra origem: todo
   município contado como tendo menção precisa ter `com_excerto` ou `registro` no canal
   DOM. Menção que o log não viu é menção inventada.
3. Recusa definição por exclusão no código-fonte. Ela não erra uma vez: erra a cada
   decisão nova que alguém criar.

Os cinco estados são distintos e não podem ser colapsados:

  sem_cobertura_qd      o município NÃO tem diário indexado — não há o que ler
  sem_edicao_no_periodo indexado, nenhuma edição DENTRO da janela — não houve o que ler
  coberto_sem_mencao    indexado e lido; nenhum excerto com os termos
  com_mencao            a consulta com os termos devolveu edição (log: com_excerto/registro)
  cobertura_indefinida  teste de cobertura falhou, OU string desconhecida

A distinção que mais importa é entre "não houve o que ler" e "leu e não achou". Somar os
dois faria o site afirmar ausência de plano onde há apenas ausência de fonte — o que
§4.1.2 proíbe, e o que destrói a credibilidade de um índice cuja promessa é nunca dizer
"não existe" quando só sabe "não localizamos".

Uso: python3 scripts/testar_contador_varredura.py
     python3 scripts/testar_contador_varredura.py --autoteste
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / "recalcular_mare.py"
RESUMO = RAIZ / "data" / "verificacao_resumo.json"
FONTES = RAIZ / "data" / "fontes_consultadas.json"
COBERTURA = RAIZ / "data" / "cobertura_qd.json"
FQD = "Querido Diário (diário municipal)"

CAMPOS = ["consultados", "total", "com_mencao", "coberto_sem_mencao", "sem_edicao_no_periodo",
          "sem_cobertura_qd", "cobertura_indefinida", "indexados", "sem_mencao"]

# A contagem que o coletor grava SÓ no ramo em que a consulta com os termos devolveu edição.
RE_CONTAGEM = re.compile(r"^\d+ decreto\(s\), \d+ pista\(s\)$")


def estado(marcas) -> str:
    """Os cinco estados, classificados positivamente. Cópia deliberadamente independente da de
    recalcular_mare.py: o portão vale porque são dois códigos, não um chamando o outro."""
    if any(RE_CONTAGEM.match(m) or m.startswith("com_excerto") for m in marcas):
        return "com_mencao"
    if any(m.startswith("coberto_sem_mencao") for m in marcas):
        return "coberto_sem_mencao"
    if any(m.startswith("sem_edicao_no_periodo") for m in marcas):
        return "sem_edicao_no_periodo"
    if any(m.startswith("sem_cobertura_qd") for m in marcas):
        return "sem_cobertura_qd"
    return "cobertura_indefinida"


def falhas_de_codigo(codigo: str) -> list:
    """O código não pode voltar à string fantasma nem à definição por exclusão."""
    p = []
    if "sem edições" in codigo:
        p.append('recalcular_mare.py voltou a classificar por "sem edições" — prefixo que o '
                 'coletor nunca grava; a conta mediria outra coisa em silêncio (§121)')
    if re.search(r"not m\.startswith", codigo):
        p.append("recalcular_mare.py voltou a definir menção por EXCLUSÃO (`not m.startswith`): "
                 "toda decisão nova que alguém criar entra na conta pública de menções sem "
                 "ninguém notar, que foi o defeito do §280")
    # Comparação LITERAL, não regex: em recalcular_mare.py a contagem é um literal de expressão
    # regular (`decreto\(s\)`, com barra), e procurá-lo como regex não casaria com ele mesmo.
    for marca in ("decreto", "pista", "sem_edicao_no_periodo", "coberto_sem_mencao"):
        if marca not in codigo:
            p.append(f"recalcular_mare.py não usa mais {marca!r} na classificação")
    return p


def falhas_de_aritmetica(v: dict) -> list:
    """As classes precisam existir, somar os consultados e repartir os indexados."""
    faltando = [c for c in CAMPOS if c not in v]
    if faltando:
        return [f"varredura_diarios sem os campos {faltando} — as classes precisam ser "
                f"publicáveis separadamente"]
    p = []
    soma = (v["com_mencao"] + v["coberto_sem_mencao"] + v["sem_edicao_no_periodo"]
            + v["sem_cobertura_qd"] + v["cobertura_indefinida"])
    # 29/09/2026: as classes somam o TOTAL, não os consultados. Município sem diário indexado nunca
    # foi consultado e não tem linha de log — mas tem estado, e o estado é `sem_cobertura_qd`, dito
    # por `data/cobertura_qd.json`. Conferir contra `consultados` fazia este teste e o portão de
    # paridade (§256) exigirem coisas incompatíveis: um pedia 5.021, o outro 5.041. `consultados`
    # segue verificado abaixo, como o que é: quantos têm linha de log.
    if soma != v["total"]:
        p.append(f"as classes somam {soma} mas o total é {v['total']} — algum "
                 f"município está fora de classificação ou contado duas vezes")
    if v["sem_mencao"] != v["coberto_sem_mencao"]:
        p.append(f"sem_mencao ({v['sem_mencao']}) difere de coberto_sem_mencao "
                 f"({v['coberto_sem_mencao']}) — 'sem menção' só vale para diário efetivamente "
                 f"lido; incluir não indexado ou sem edição na janela afirma ausência de plano "
                 f"onde há ausência de fonte (§4.1.2)")
    esperado = v["com_mencao"] + v["coberto_sem_mencao"] + v["sem_edicao_no_periodo"]
    if v["indexados"] != esperado:
        p.append(f"indexados ({v['indexados']}) deve ser com_mencao + coberto_sem_mencao + "
                 f"sem_edicao_no_periodo = {esperado}: diário indexado sem edição na janela "
                 f"continua indexado")
    if v["consultados"] and v["com_mencao"] == v["consultados"]:
        p.append("com_mencao == consultados: assinatura do defeito de §121 (todo município "
                 "consultado contado como tendo menção)")
    return p


def falhas_de_paridade(recontado: dict, v: dict) -> list:
    """O resumo publicado tem de concordar com a recontagem independente deste portão."""
    p = []
    for classe, n in sorted(recontado.items()):
        if v.get(classe) != n:
            p.append(f"{classe}: este portão reconta {n} e verificacao_resumo.json declara "
                     f"{v.get(classe)} — os dois códigos discordam sobre o mesmo dado")
    return p


def falhas_de_reconciliacao(com_mencao: set, positivos_no_log: set) -> list:
    """Menção que o log não viu é menção inventada. O contrário é tolerado: o log é histórico e
    o estado é o da última janela, então um município pode ter tido excerto antes e não agora."""
    fantasmas = sorted(com_mencao - positivos_no_log)
    if fantasmas:
        return [f"{len(fantasmas)} município(s) contados em com_mencao sem nenhuma execução "
                f"`com_excerto` nem `registro` no canal DOM do log — exemplos: "
                f"{', '.join(fantasmas[:5])}"]
    return []


def autoteste() -> int:
    casos = []
    casos.append(("contagem com zero e zero é menção (houve excerto, não houve ato)",
                  estado(["0 decreto(s), 0 pista(s)"]) == "com_mencao"))
    casos.append(("sem edição na janela NÃO é menção",
                  estado(["sem_edicao_no_periodo: diário indexado, nenhuma edição"])
                  == "sem_edicao_no_periodo"))
    casos.append(("string desconhecida cai em indefinida, nunca em menção",
                  estado(["decisao_que_alguem_inventar_amanha: qualquer coisa"])
                  == "cobertura_indefinida"))
    casos.append(("leitura efetiva vence ausência de edição",
                  estado(["sem_edicao_no_periodo: x", "coberto_sem_mencao: y"])
                  == "coberto_sem_mencao"))
    casos.append(("não indexado continua não indexado",
                  estado(["sem_cobertura_qd: diário não indexado"]) == "sem_cobertura_qd"))
    casos.append(("teste de cobertura falhado é indefinido",
                  estado(["cobertura a confirmar (teste de cobertura falhou)"])
                  == "cobertura_indefinida"))

    # O defeito do §280, encenado: a definição por exclusão vista sobre as strings reais.
    reais = ["sem_cobertura_qd: x", "0 decreto(s), 0 pista(s)", "coberto_sem_mencao: x",
             "sem_edicao_no_periodo: x", "cobertura a confirmar (teste de cobertura falhou)"]
    por_exclusao = [m for m in reais
                    if not m.startswith(("sem_cobertura_qd", "coberto_sem_mencao",
                                         "cobertura a confirmar"))]
    casos.append(("a definição por exclusão de fato engolia sem_edicao_no_periodo",
                  any(m.startswith("sem_edicao_no_periodo") for m in por_exclusao)))
    casos.append(("o portão recusa definição por exclusão no código",
                  any("EXCLUS" in f for f in falhas_de_codigo(
                      'if any(not m.startswith(("sem_cobertura_qd",)) for m in marcas):'))))
    casos.append(("o portão recusa a string fantasma do §121",
                  any("sem edições" in f for f in falhas_de_codigo('if "sem edições" in m:'))))

    # As classes somam o TOTAL. Os 100 consultados são os que têm linha de log; os 5.471 restantes
    # não têm diário indexado e entram em `sem_cobertura_qd` pela cobertura.
    bom = {"consultados": 100, "total": 5571, "com_mencao": 10, "coberto_sem_mencao": 20,
           "sem_edicao_no_periodo": 5, "sem_cobertura_qd": 5535, "cobertura_indefinida": 1,
           "indexados": 35, "sem_mencao": 20}
    casos.append(("estado coerente passa", falhas_de_aritmetica(bom) == []))
    casos.append(("classe faltando reprova",
                  falhas_de_aritmetica({k: n for k, n in bom.items()
                                        if k != "sem_edicao_no_periodo"}) != []))
    casos.append(("indexados sem sem_edicao_no_periodo reprova",
                  any("indexados" in f for f in falhas_de_aritmetica({**bom, "indexados": 30}))))
    casos.append(("sem_mencao absorvendo sem edição reprova",
                  any("sem_mencao" in f for f in falhas_de_aritmetica({**bom, "sem_mencao": 25}))))
    casos.append(("classes que não somam o total reprovam",
                  any("somam" in f for f in falhas_de_aritmetica({**bom, "total": 5572}))))
    casos.append(("recontagem divergente reprova",
                  falhas_de_paridade({"com_mencao": 11}, bom) != []))
    casos.append(("recontagem igual passa", falhas_de_paridade({"com_mencao": 10}, bom) == []))
    casos.append(("menção que o log não viu reprova",
                  falhas_de_reconciliacao({"3205002"}, set()) != []))
    casos.append(("excerto no log sem menção no estado é tolerado (o log é histórico)",
                  falhas_de_reconciliacao(set(), {"3205002"}) == []))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    falhas = []
    fonte = FONTE.read_text(encoding="utf-8")
    # Só o CÓDIGO conta: o comentário que documenta o defeito cita a string fantasma e a
    # definição antiga de propósito, e o portão não pode cair por causa da própria explicação.
    codigo = "\n".join(l.split("#", 1)[0] for l in fonte.splitlines())
    falhas += falhas_de_codigo(codigo)

    if not RESUMO.exists():
        print("X data/verificacao_resumo.json não existe")
        return 1
    v = json.loads(RESUMO.read_text(encoding="utf-8")).get("varredura_diarios") or {}
    if not v:
        print("X verificacao_resumo.json sem varredura_diarios")
        return 1
    falhas += falhas_de_aritmetica(v)

    # Recontagem independente, a partir do dado bruto.
    fc = json.loads(FONTES.read_text(encoding="utf-8"))
    fc = fc.get("municipios") or fc
    recontado, com_mencao, vistos_no_log = {}, set(), set()
    cob = {}
    if COBERTURA.exists():
        cob = (json.loads(COBERTURA.read_text(encoding="utf-8")) or {}).get("municipios") or {}
    for cod, m in fc.items():
        fs = [f for f in (m.get("fontes") or []) if f.get("fonte") == FQD]
        if not fs:
            continue
        e = estado([str(f.get("resultado", "")) for f in fs])
        # 30/09/2026: marca de log ILEGÍVEL não vence a sondagem do acervo. Quando o log não diz
        # nada legível e a cobertura sabe que não há diário, o município é `sem_cobertura_qd`. A
        # regra é a mesma do produtor, mas lida da FONTE (o arquivo de cobertura), não copiada do
        # código dele — é isso que mantém esta recontagem independente.
        if e == "cobertura_indefinida":
            r = cob.get(str(cod).zfill(7)) if cob else None
            val = r.get("cobertura_qd") if isinstance(r, dict) else r
            if val is False:
                e = "sem_cobertura_qd"
        recontado[e] = recontado.get(e, 0) + 1
        vistos_no_log.add(str(cod).zfill(7))
        if e == "com_mencao":
            com_mencao.add(str(cod).zfill(7))
    consultados = sum(recontado.values())
    if consultados != v["consultados"]:
        falhas.append(f"consultados: este portão conta {consultados} municípios com linha de log do "
                      f"Querido Diário e verificacao_resumo.json declara {v['consultados']}")
    # Os não consultados entram pela cobertura, que é o único arquivo que sabe deles — e a
    # recontagem os soma aqui, de forma independente do produtor, para o total fechar.
    cob = {}
    if COBERTURA.exists():
        cob = (json.loads(COBERTURA.read_text(encoding="utf-8")) or {}).get("municipios") or {}
    for cod, r in cob.items():
        if str(cod).zfill(7) in vistos_no_log:
            continue
        val = r.get("cobertura_qd") if isinstance(r, dict) else r
        e = "sem_cobertura_qd" if val is False else "cobertura_indefinida"
        recontado[e] = recontado.get(e, 0) + 1
    recontado["consultados"] = consultados
    falhas += falhas_de_paridade(recontado, v)

    # Reconciliação contra o log, que é outro arquivo e outra origem.
    sys.path.insert(0, str(RAIZ))
    from coletores_base import ler_log
    positivos = set()
    for e in ler_log().get("execucoes", []):
        if e.get("canal") != "DOM":
            continue
        if str(e.get("decisao") or "").split(":")[0] in ("com_excerto", "registro"):
            cod = str(e.get("ibge") or "").zfill(7)
            if cod and cod != "0000000":
                positivos.add(cod)
    falhas += falhas_de_reconciliacao(com_mencao, positivos)

    if falhas:
        for f in falhas:
            print(f"X {f}")
        return 1

    print(f"OK contador da varredura: {v['total']} municípios = {v['com_mencao']} com menção "
          f"+ {v['coberto_sem_mencao']} lidos sem menção + {v['sem_edicao_no_periodo']} sem edição "
          f"na janela + {v['sem_cobertura_qd']} sem diário indexado + {v['cobertura_indefinida']} "
          f"indefinidos. Recontagem independente concorda; as {len(com_mencao)} menções têm "
          f"execução com_excerto ou registro no log. Não indexado e sem edição não são sem menção.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
