#!/usr/bin/env python3
"""Óbitos registrados em cartório, por UF e MÊS — Portal da Transparência do Registro Civil.

Item 5 do bloco "fontes primárias" (decisão da central, 29/09/2026), perna do **preliminar
rápido**. A decisão pede duas pernas para óbitos: o Registro Civil como sinal rápido e o SIM como
consolidação. Esta é a primeira.

O QUE ESTA SÉRIE É, E O QUE ELA NÃO É
-------------------------------------
É a contagem de **registros de óbito lavrados em cartório**, por UF, no período pedido. Ela chega em
dias — por isso serve de sinal precoce — e **não traz causa**. Não é o SIM: o Sistema de Informações
sobre Mortalidade tem causa básica codificada e é a fonte de mortalidade do país, com defasagem de
meses. Uma não substitui a outra, e usar esta para falar de causa seria erro grave.

Também não é "óbitos ocorridos": é **óbitos registrados** na janela. Um óbito de dezembro registrado
em janeiro conta em janeiro. Para leitura de excesso isso importa, e está dito no arquivo.

A GRANULARIDADE É MENSAL, E ISSO FOI MEDIDO
-------------------------------------------
A primeira versão deste coletor pediu semanas e escreveu uma série semanal. Os números saíram
errados de um jeito que só a conferência pegou: semanas diferentes do mesmo mês devolviam o
**mesmo** total, e 96.348 óbitos numa semana é cerca de três vezes o que o país registra. A medição
explicou — qualquer intervalo dentro de agosto devolve agosto inteiro (123.642), e um intervalo de
15/08 a 15/09 devolve a soma dos dois meses (219.990). **A API agrega por mês**, e o parâmetro de
data escolhe quais meses entram, não o recorte.

Então a série é mensal, com uma consulta por mês. Pedir semana e publicar o número do mês seria
inventar granularidade que a fonte não tem.

PESO ZERO
---------
Como todo o MARÉ Saúde: observação declarada, sem nota, sem faixa, sem atribuição ao El Niño.

USO
  python3 coletar_obitos_registro_civil.py --autoteste
  python3 coletar_obitos_registro_civil.py [--meses 18]
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

API = "https://transparencia.registrocivil.org.br/api/record/death"
SAIDA = "saude_desfechos/obitos_registro_civil.json"
MESES_PADRAO = 18
RESSALVA = ("O Monitor não atribui óbitos ao El Niño. A série conta REGISTROS de óbito lavrados em "
            "cartório por UF, sem causa — é sinal precoce, não mortalidade por causa. A fonte de "
            "mortalidade com causa básica é o SIM, que tem defasagem de meses. Conta óbito "
            "REGISTRADO no mês, não óbito ocorrido nele. A granularidade é MENSAL: é a que a fonte "
            "tem, e o mês corrente está incompleto porque o registro entra ao longo dos dias.")


def chave_mes(d: datetime.date) -> str:
    """'AAAA-MM'. A granularidade da fonte é o mês, e a chave diz isso — série de saúde com chave
    'AAAA-SS' é semanal, e confundir as duas na mesma página seria pedir erro de leitura."""
    return f"{d.year}-{d.month:02d}"


def meses(ate: datetime.date, quantos: int) -> list:
    """[(primeiro_dia, ultimo_dia)] de meses, do mais antigo para o mais novo, incluindo o corrente.

    O mês corrente ENTRA, porque é ele que dá o sinal precoce — mas sai marcado como incompleto:
    registro de cartório chega ao longo dos dias, e ler o mês pela metade como queda seria o erro
    que as séries semanais evitam vazando as últimas semanas."""
    out = []
    ano, mes = ate.year, ate.month
    for _ in range(quantos):
        primeiro = datetime.date(ano, mes, 1)
        ultimo = (datetime.date(ano + (mes == 12), (mes % 12) + 1, 1) - datetime.timedelta(days=1))
        out.append((primeiro, ultimo))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return list(reversed(out))


def serie_de(respostas: dict) -> dict:
    """{'BR'|UF: {'AAAA-MM': total}} a partir de {(ini, fim): resposta_da_api}. Função pura."""
    serie = {}
    for (ini, _fim), resposta in sorted(respostas.items(), key=lambda kv: kv[0][0]):
        chave = chave_mes(ini)
        total_br = 0
        for item in (resposta or {}).get("data", []):
            uf = str(item.get("name") or "").strip().upper()
            if len(uf) != 2 or not uf.isalpha():
                continue
            try:
                n = int(item.get("total") or 0)
            except (TypeError, ValueError):
                continue
            serie.setdefault(uf, {})[chave] = n
            total_br += n
        if total_br:
            serie.setdefault("BR", {})[chave] = total_br
    return serie


def autoteste() -> int:
    casos = []
    d = datetime.date

    casos.append(("a chave é mensal, não semanal", chave_mes(d(2026, 9, 27)) == "2026-09"))
    ms = meses(d(2026, 9, 29), 3)
    casos.append(("três meses, do mais antigo para o mais novo",
                  [chave_mes(i) for i, _f in ms] == ["2026-07", "2026-08", "2026-09"]))
    casos.append(("cada janela vai do dia 1 ao último dia do mês",
                  ms[0] == (d(2026, 7, 1), d(2026, 7, 31))
                  and ms[1] == (d(2026, 8, 1), d(2026, 8, 31))))
    casos.append(("fevereiro fecha no dia certo",
                  meses(d(2026, 2, 10), 1)[0] == (d(2026, 2, 1), d(2026, 2, 28))))
    casos.append(("a virada de ano volta para dezembro",
                  [chave_mes(i) for i, _f in meses(d(2026, 1, 15), 2)] == ["2025-12", "2026-01"]))
    casos.append(("o mês corrente entra — é ele que dá o sinal precoce",
                  chave_mes(ms[-1][0]) == "2026-09"))

    resp = {(d(2026, 8, 1), d(2026, 8, 31)): {"data": [{"name": "AC", "total": 293},
                                                       {"name": "sp", "total": 1000},
                                                       {"name": "XXX", "total": 5},
                                                       {"name": "RJ", "total": "abc"}]}}
    s = serie_de(resp)
    casos.append(("conta por UF no mês", s["AC"]["2026-08"] == 293 and s["SP"]["2026-08"] == 1000))
    casos.append(("o nacional é a soma das UFs válidas", s["BR"]["2026-08"] == 1293))
    casos.append(("nome que não é UF fica de fora", "XXX" not in s))
    casos.append(("total ilegível não vira zero nem entra", "RJ" not in s))
    casos.append(("resposta vazia não cria mês",
                  serie_de({(d(2026, 8, 1), d(2026, 8, 31)): {}}) == {}))
    casos.append(("a ressalva diz que não há causa e que é registro, não ocorrência",
                  "sem causa" in RESSALVA and "REGISTRADO" in RESSALVA))
    casos.append(("a ressalva diz que a granularidade é mensal", "mensal" in RESSALVA.lower()))

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

    from coletores_base import DATA, buscar, gravar_em, hoje_editorial, log_busca, registrar_lacuna

    quantos = MESES_PADRAO
    if "--meses" in sys.argv:
        try:
            quantos = int(sys.argv[sys.argv.index("--meses") + 1])
        except (IndexError, ValueError):
            print("--meses exige um inteiro")
            return 2
        if quantos < 1:
            print("--meses exige inteiro positivo")
            return 2

    hoje = hoje_editorial()
    respostas, falhas = {}, []
    for ini, fim in meses(hoje, quantos):
        url = f"{API}?start_date={ini.isoformat()}&end_date={fim.isoformat()}"
        try:
            respostas[(ini, fim)] = json.loads(buscar(url, timeout=60))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{ini}..{fim}: {type(e).__name__}")

    if falhas:
        registrar_lacuna("Registro Civil (óbitos por UF)", "; ".join(falhas)[:180],
                         canal="DOU", camada=1)
    if not respostas:
        print("óbitos: nenhum mês respondido — lacuna declarada, série não escrita")
        return 0

    serie = serie_de(respostas)
    if not serie:
        registrar_lacuna("Registro Civil (óbitos por UF)",
                         "respostas sem nenhuma UF utilizável", canal="DOU", camada=1)
        print("óbitos: respostas sem UF utilizável — lacuna declarada")
        return 0

    (DATA / "saude_desfechos").mkdir(parents=True, exist_ok=True)
    gravar_em(DATA / SAIDA, {
        "_governanca": ("Óbitos registrados em cartório — nacional e por UF (§36, catálogo). Peso "
                        "zero, sem nota, sem faixa. " + RESSALVA + " O mês corrente aparece e está "
                        "declarado como incompleto em `mes_corrente_incompleto`: lê-lo como queda "
                        "seria o mesmo erro que as séries semanais evitam vazando as últimas SE."),
        "gerado_em": hoje.strftime("%d/%m/%Y"),
        "fonte": "https://transparencia.registrocivil.org.br/",
        "sistema": "Portal da Transparência do Registro Civil (ARPEN/CNJ)",
        "indicador": "obitos_registrados", "conta": "registros_de_obito",
        "granularidade": "mensal", "meses_pedidos": quantos, "meses_obtidos": len(respostas),
        "meses_sem_resposta": falhas, "mes_corrente_incompleto": chave_mes(hoje), "serie": serie})
    log_busca("DOU", 1, [API], "registro", nivel="nacional", n_resultados=len(serie),
              resultados=f"óbitos registrados: {len(serie)} localidade(s), {len(respostas)} mês(es)")
    print(f"óbitos: {len(serie)} localidade(s), {len(respostas)} de {quantos} mês(es); "
          f"última: {max(serie.get('BR', {}), default='—')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
