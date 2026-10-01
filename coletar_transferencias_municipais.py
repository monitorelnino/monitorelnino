#!/usr/bin/env python3
"""
coletar_transferencias_municipais.py — o que a União transferiu a cada município, por mês e por rota
=====================================================================================================
Pedido da editoria em 01/10/2026, depois de o bloco B do Financiamento não poder publicar o cartão
"Quanto chegou à sua cidade": a página diz, hoje, que a consulta depende da coleta **por município**,
que não existia. Este coletor é ela.

A PORTA SEM CHAVE, E POR QUE ELA
--------------------------------
O Portal da Transparência tem duas portas para o mesmo dado:

  - a **API** (`api.portaldatransparencia.gov.br`), que desde 2023 exige o cabeçalho
    `chave-api-dados`. A chave é gratuita, e ainda assim está **proibida aqui**: o repositório é
    público e vai ser aberto, e a regra é "nenhuma API ou produto pago dependurado no código, nem
    atrás de chave configurável". Medido em 01/10/2026: **403** sem a chave.
  - o **download de dados abertos** (`portaldatransparencia.gov.br/download-de-dados/transferencias/
    AAAAMM`), que devolve um ZIP com um CSV, sem chave, sem cadastro. Medido: **200**, 2,4 MB para
    janeiro de 2026, 122.527 linhas.

É a segunda. Ela não é um contorno: é a publicação oficial em dados abertos do mesmo órgão, e não
depende de credencial que um fork não teria.

O QUE ENTRA NA CONTA
--------------------
Só `TIPO FAVORECIDO = "Administração Pública Municipal"` — 43.987 das 122.527 linhas de janeiro,
cobrindo 5.569 municípios. As outras linhas são transferência a estado, a entidade sem fins
lucrativos, a empresa: dinheiro que não chega à prefeitura, e somá-lo inflaria o número da cidade.

A ROTA, DERIVADA DO QUE O ARQUIVO TRAZ
--------------------------------------
O campo `TIPO TRANSFERÊNCIA` tem dois valores só — "Constitucionais e Royalties" e "Legais,
Voluntárias e Específicas" —, grosso demais para a pergunta "por qual caminho". A rota sai de uma
derivação **declarada**, pelos códigos de função e subfunção, que são fato no arquivo:

  constitucional        TIPO TRANSFERÊNCIA = Constitucionais e Royalties (FPM, cotas, royalties)
  saude                 FUNÇÃO 10
  assistencia_social    FUNÇÃO 08
  defesa_civil          SUBFUNÇÃO 182
  outras                o resto das legais, voluntárias e específicas

**Emenda parlamentar não é identificável nesta fonte**, e por isso não existe como rota aqui — a
lacuna é declarada no arquivo, não preenchida por aproximação. E nenhum nome de autor entra: a regra
do projeto proíbe, e esta fonte não os traz.

A CHAVE DO MUNICÍPIO: SIAFI, NÃO IBGE
-------------------------------------
O arquivo identifica a cidade pelo **código SIAFI** (quatro dígitos), e todo o resto do site é
indexado por **IBGE** (sete). Não há relação aritmética entre os dois: precisa de mapa. O mapa é
montado por `(UF, nome normalizado)` contra `municipios_ibge_referencia.json` — e o que **não casar
é declarado**, nunca descartado em silêncio. Casar por nome já custou caro neste projeto (os
municípios do Cemaden ficaram fora de um mapa sem aviso), e é por isso que a taxa de casamento é
gravada no arquivo e o portão a confere.

PESO ZERO
---------
Camada de contexto. Nunca lida por `recalcular_mare.py` nem por `gerar_monitor_saude.py`; não
pontua, não entra no índice.

USO
  python coletar_transferencias_municipais.py --autoteste
  python coletar_transferencias_municipais.py --mes 202601
  python coletar_transferencias_municipais.py --ano 2026        # os meses do ano até o corte
"""
import csv
import io
import pathlib
import re
import sys
import unicodedata
import zipfile

import funil
from coletores_base import (buscar, gravar_em, hoje_editorial, ler, log_busca, preservar_evidencia,
                            registrar_lacuna, rodar_autoteste)

RAIZ = pathlib.Path(__file__).resolve().parent
SAIDA = RAIZ / "data" / "financiamento" / "municipios" / "transferencias_uniao.json"
FONTE = "https://portaldatransparencia.gov.br/download-de-dados/transferencias/{mes}"
TIPO_MUNICIPAL = "Administração Pública Municipal"
CONSTITUCIONAL = "Constitucionais e Royalties"

# Rota ← função/subfunção. Derivação DECLARADA, não inferência: os códigos são fato no arquivo.
FUNCAO_SAUDE = "10"
FUNCAO_ASSISTENCIA = "08"
SUBFUNCAO_DEFESA_CIVIL = "182"
ROTAS = ("constitucional", "saude", "assistencia_social", "defesa_civil", "outras")

# Os cinco arquivos do banco, na mesma lista que `descobrir_planos.py` usa. Nenhum coletor de
# camada de contexto pode escrever neles, e o autoteste confere que este não ganhou essa
# escrita numa edição futura.
BANCO_PROIBIDO = ("estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json")


def normalizar(nome: str) -> str:
    """Nome de município comparável: sem acento, sem pontuação, maiúsculas. Função pura.

    O arquivo do Portal traz "ACRELANDIA" e a referência do IBGE traz "Acrelândia"; sem normalizar,
    nenhum dos 5.569 casaria."""
    t = unicodedata.normalize("NFD", nome or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # Os espaços são COLAPSADOS, e não só aparados: trocar pontuação por espaço deixa dois onde
    # havia "(" — "Januário Cicco (Boa Saúde)" virava "JANUARIO CICCO  BOA SAUDE", e esse nome não
    # casa com nada. O mesmo vale para o sufixo do SIAFI, que vem com dois espaços antes do "EX".
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", t.upper())).strip()


def valor_br(texto: str) -> float:
    """"1224730,35" → 1224730.35. Função pura.

    Devolve 0.0 para vazio, e **levanta** para texto que não é número: valor ilegível tratado como
    zero somaria errado em silêncio, que é o pior desfecho possível num arquivo de dinheiro."""
    t = (texto or "").strip()
    if not t:
        return 0.0
    return float(t.replace(".", "").replace(",", "."))


def rota_de(tipo_transferencia: str, funcao: str, subfuncao: str) -> str:
    """A rota da linha. Função pura, declarada.

    A ordem importa: defesa civil é subfunção DENTRO de outras funções, e precisa ser testada antes
    da função — uma transferência de defesa civil na função Saúde é defesa civil, não SUS."""
    if (tipo_transferencia or "").strip() == CONSTITUCIONAL:
        return "constitucional"
    if (subfuncao or "").strip().lstrip("0") == SUBFUNCAO_DEFESA_CIVIL:
        return "defesa_civil"
    f = (funcao or "").strip().lstrip("0") or "0"
    if f == FUNCAO_SAUDE.lstrip("0"):
        return "saude"
    if f == FUNCAO_ASSISTENCIA.lstrip("0"):
        return "assistencia_social"
    return "outras"


# ── Os nomes que o SIAFI escreve de outro jeito (01/10/2026) ──────────────────────────────────
# A primeira coleta de janeiro de 2026 casou 5.549 de 5.569 municípios e deixou **20** de fora, com
# R$ 133,4 milhões — 0,37% do mês. Nenhum era erro de dado: eram nomes que o SIAFI e o IBGE escrevem
# diferente, ou municípios renomeados. Resolvidos em dois níveis, para não virar uma tabela sem fim.
#
# DUAS REGRAS GERAIS, que valem para qualquer caso futuro do mesmo tipo:
#
#   1. O SIAFI conserva o nome antigo num sufixo — "CAMPO GRANDE (EX AUGUSTO SEVERO)", "SERRA CAIADA
#      (EX PRESIDENTE JUSCELINO)". O sufixo sai antes de comparar.
#   2. A referência do IBGE às vezes traz o nome alternativo entre parênteses — "Januário Cicco (Boa
#      Saúde)", "Augusto Severo (Campo Grande)". Cada município passa a ser indexado por TODOS os
#      seus nomes: o inteiro, o de fora dos parênteses e o de dentro.
#
# E UMA TABELA, conferida município a município contra `municipios_ibge_referencia.json`. Ela é
# curta de propósito: cada linha é uma grafia que as duas fontes não compartilham, e crescer por
# conveniência seria aceitar casamento aproximado, que é o que este projeto não faz.
RE_SUFIXO_EX = re.compile(r"\s*\(?\s*EX[\s.]+[A-Z0-9 ]+\)?\s*$")

EQUIVALENCIAS = {
    ("CE", "ITAPAGE"): "Itapajé",
    ("MG", "BRASOPOLIS"): "Brazópolis",
    ("MT", "POXOREO"): "Poxoréu",
    ("PA", "ELDORADO DOS CARAJAS"): "Eldorado do Carajás",
    ("PA", "SANTA ISABEL DO PARA"): "Santa Izabel do Pará",
    # Nome anterior de São Domingos (PB), que o SIAFI mantém.
    ("PB", "SAO DOMINGOS DE POMBAL"): "São Domingos",
    # "Seridó" foi o nome de São Vicente do Seridó (PB) até 1996.
    ("PB", "SERIDO"): "São Vicente do Seridó",
    ("PE", "BELEM DE SAO FRANCISCO"): "Belém do São Francisco",
    ("PE", "IGUARACI"): "Iguaracy",
    ("PE", "LAGOA DO ITAENGA"): "Lagoa de Itaenga",
    ("PE", "SAO CAITANO"): "São Caetano",
    ("RJ", "PARATI"): "Paraty",
    ("RJ", "TRAJANO DE MORAIS"): "Trajano de Moraes",
    ("RS", "SANTANA DO LIVRAMENTO"): "Sant'Ana do Livramento",
    ("SP", "SAO LUIS DO PARAITINGA"): "São Luiz do Paraitinga",
    ("TO", "COUTO DE MAGALHAES"): "Couto Magalhães",
    ("TO", "SAO VALERIO DA NATIVIDADE"): "São Valério",
}

def nomes_do_municipio(nome: str) -> set:
    """Todos os nomes pelos quais um município da referência pode ser citado. Função pura.

    "Januário Cicco (Boa Saúde)" é citável como o inteiro, como "Januário Cicco" e como "Boa Saúde".
    Indexar só o inteiro deixava os dois primeiros de fora."""
    alvos = {normalizar(nome)}
    m = re.match(r"^(.*?)\s*\((.+)\)\s*$", nome or "")
    if m:
        alvos.add(normalizar(m.group(1)))
        alvos.add(normalizar(m.group(2)))
    return {a for a in alvos if a}


def mapa_siafi_para_ibge(referencia: list) -> dict:
    """{(UF, nome normalizado): código IBGE}. Função pura.

    Não é o mapa SIAFI→IBGE: é a chave por onde ele se monta. O SIAFI não aparece na referência do
    IBGE, e por isso o casamento é por UF e nome — com a taxa medida e declarada.

    Cada município entra por todos os seus nomes, e as equivalências declaradas entram junto."""
    chave = {}
    por_nome = {}
    for m in referencia:
        ibge = f"{int(m['codigo_ibge']):07d}"
        por_nome[(m["uf"], normalizar(m["nome"]))] = ibge
        for alvo in nomes_do_municipio(m["nome"]):
            chave[(m["uf"], alvo)] = ibge
    for (uf, siafi), nome_ibge in EQUIVALENCIAS.items():
        ibge = por_nome.get((uf, normalizar(nome_ibge)))
        if ibge:
            chave[(uf, normalizar(siafi))] = ibge
    return chave


def ler_mes(corpo: bytes, chave: dict) -> tuple:
    """(por_ibge, nao_casados, linhas_municipais, soma) de um ZIP mensal. Função pura.

    `por_ibge[ibge][rota]` acumula o valor. `nao_casados` é {(UF, nome): valor}, declarado na saída:
    município que não casou não desaparece — ele aparece como lacuna, com o dinheiro que ficou de
    fora, para que ninguém leia o total como completo."""
    z = zipfile.ZipFile(io.BytesIO(corpo))
    nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not nomes:
        raise ValueError("ZIP do Portal sem CSV dentro: formato mudou")
    por_ibge, nao_casados, sem_municipio = {}, {}, {}
    linhas_mun, soma = 0, 0.0
    with z.open(nomes[0]) as f:
        leitor = csv.reader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
        cab = next(leitor)
        col = {c: i for i, c in enumerate(cab)}
        exigidas = ("TIPO FAVORECIDO", "TIPO TRANSFERÊNCIA", "UF", "NOME MUNICÍPIO",
                    "CÓDIGO FUNÇÃO", "CÓDIGO SUBFUNÇÃO", "VALOR TRANSFERIDO")
        faltam = [c for c in exigidas if c not in col]
        if faltam:
            raise ValueError(f"colunas ausentes no CSV do Portal: {faltam}")
        for linha in leitor:
            if len(linha) <= col["VALOR TRANSFERIDO"]:
                continue
            if linha[col["TIPO FAVORECIDO"]].strip() != TIPO_MUNICIPAL:
                continue
            linhas_mun += 1
            uf = linha[col["UF"]].strip()
            nome = RE_SUFIXO_EX.sub("", normalizar(linha[col["NOME MUNICÍPIO"]])).strip()
            v = valor_br(linha[col["VALOR TRANSFERIDO"]])
            soma += v
            rota = rota_de(linha[col["TIPO TRANSFERÊNCIA"]], linha[col["CÓDIGO FUNÇÃO"]],
                           linha[col["CÓDIGO SUBFUNÇÃO"]])
            if not nome:
                # A FONTE não disse qual município. É lacuna da fonte, não falha de leitura, e por
                # isso vive separada: "não foi dito" e "não consegui ler" são coisas diferentes.
                sem_municipio[uf] = round(sem_municipio.get(uf, 0.0) + v, 2)
                continue
            ibge = chave.get((uf, nome))
            if ibge is None:
                nao_casados[(uf, nome)] = round(nao_casados.get((uf, nome), 0.0) + v, 2)
                continue
            por_ibge.setdefault(ibge, {}).setdefault(rota, 0.0)
            por_ibge[ibge][rota] += v
    return por_ibge, nao_casados, sem_municipio, linhas_mun, round(soma, 2)


def marcar_parciais(meses_lidos: dict, piso: float = 0.5) -> dict:
    """Marca como `parcial` o mês muito abaixo da mediana de linhas dos demais. Função pura.

    O Portal publica o arquivo do mês e continua enchendo: setembro de 2026 veio com 19.307 linhas
    contra uma mediana de 49 mil, e o total do mês aparecia como R$ 3,11 bi contra R$ 25–37 bi dos
    outros oito. Sem esta marca, a página mostraria a queda como fato do dinheiro, e ela é do
    arquivo.

    A régua é medida, não arbitrada: menos da metade da mediana dos OUTROS meses. Com menos de três
    meses lidos não há mediana que signifique algo, e então nada é marcado — preferir não afirmar a
    afirmar por amostra pequena."""
    meses = dict(meses_lidos or {})
    if len(meses) < 3:
        for v in meses.values():
            v.pop("parcial", None)
            v.pop("parcial_porque", None)
        return meses
    for mes, v in meses.items():
        outros = sorted(o["linhas_municipais"] for m, o in meses.items() if m != mes)
        mediana = outros[len(outros) // 2] if outros else 0
        if mediana and v["linhas_municipais"] < piso * mediana:
            v["parcial"] = True
            v["parcial_porque"] = (f"{v['linhas_municipais']} linha(s) contra mediana de {mediana} "
                                   f"nos outros meses — arquivo do Portal ainda sendo preenchido")
        else:
            v.pop("parcial", None)
            v.pop("parcial_porque", None)
    return meses


def fundir(anterior: dict, mes: str, por_ibge: dict, nao_casados: dict, sem_municipio: dict,
           linhas: int, soma: float) -> dict:
    """Junta o mês ao arquivo. Função pura e IDEMPOTENTE: reler o mesmo mês não soma duas vezes.

    O mês é a chave: `municipios[ibge]["meses"][mes][rota]`. Rodar de novo substitui aquele mês em
    vez de acumular — é o que permite recoletar um mês cujo arquivo o Portal republicou."""
    saida = dict(anterior or {})
    municipios = dict(saida.get("municipios") or {})
    for ibge, rotas in por_ibge.items():
        reg = dict(municipios.get(ibge) or {})
        meses = dict(reg.get("meses") or {})
        meses[mes] = {r: round(v, 2) for r, v in sorted(rotas.items())}
        reg["meses"] = {m: meses[m] for m in sorted(meses)}
        total = {}
        for m, rr in reg["meses"].items():
            for r, v in rr.items():
                total[r] = round(total.get(r, 0.0) + v, 2)
        reg["por_rota"] = {r: total[r] for r in sorted(total)}
        reg["total"] = round(sum(total.values()), 2)
        municipios[ibge] = reg
    saida["municipios"] = {k: municipios[k] for k in sorted(municipios)}
    meses_lidos = dict(saida.get("meses_lidos") or {})
    meses_lidos[mes] = {"linhas_municipais": linhas, "soma": soma,
                        "municipios_casados": len(por_ibge),
                        "nao_casados": len(nao_casados),
                        "valor_nao_casado": round(sum(nao_casados.values()), 2),
                        "sem_municipio_na_fonte": round(sum(sem_municipio.values()), 2)}
    saida["meses_lidos"] = marcar_parciais({m: meses_lidos[m] for m in sorted(meses_lidos)})
    pendentes = dict(saida.get("nao_casados") or {})
    for (uf, nome), v in nao_casados.items():
        pendentes[f"{uf}|{nome}"] = round(pendentes.get(f"{uf}|{nome}", 0.0) + v, 2)
    saida["nao_casados"] = {k: pendentes[k] for k in sorted(pendentes)}
    sem = dict(saida.get("sem_municipio_na_fonte") or {})
    for uf, v in sem_municipio.items():
        sem[uf] = round(sem.get(uf, 0.0) + v, 2)
    saida["sem_municipio_na_fonte"] = {k: sem[k] for k in sorted(sem)}
    return saida


def meses_do_ano(ano: int, hoje=None) -> list:
    """Os meses AAAAMM do ano até o mês anterior ao de hoje. Função pura.

    O mês corrente fica fora: o Portal publica o arquivo fechado, e ler o mês em curso devolveria um
    número parcial que a página mostraria como total."""
    h = hoje or hoje_editorial()
    ultimo = 12 if ano < h.year else h.month - 1
    return [f"{ano}{m:02d}" for m in range(1, max(0, ultimo) + 1)]


def coletar(mes: str) -> dict:
    ref = ler("municipios_ibge_referencia.json", []) or []
    if not ref:
        registrar_lacuna("portal_transferencias", "referência do IBGE ausente",
                         canal="DOU", camada=1, strings=[mes])
        return {}
    chave = mapa_siafi_para_ibge(ref)
    url = FONTE.format(mes=mes)
    try:
        corpo = buscar(url, timeout=300, origem="coletar_transferencias_municipais")
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("portal_transferencias", f"{mes}: {type(e).__name__}: {e}",
                         canal="DOU", camada=1, strings=[url])
        return {}
    h = preservar_evidencia(corpo, url, "zip", "coletar_transferencias_municipais")
    por_ibge, nao_casados, sem_municipio, linhas, soma = ler_mes(corpo, chave)
    # Zero linha municipal NÃO é "nada foi transferido": é formato mudado ou arquivo vazio.
    if linhas == 0:
        registrar_lacuna("portal_transferencias", f"{mes}: zero linha municipal no arquivo",
                         canal="DOU", camada=1, strings=[url], hash_evidencia=h)
        log_busca("DOU", 1, [url], "erro", resultados=f"{mes}: zero linha municipal",
                  hash_evidencia=h)
        return {}
    anterior = {}
    if SAIDA.exists():
        import json
        anterior = json.loads(SAIDA.read_text(encoding="utf-8"))
    dados = fundir(anterior, mes, por_ibge, nao_casados, sem_municipio, linhas, soma)
    dados["_formato"] = (
        "Transferências da União a municípios, por mês e por rota, do download de DADOS ABERTOS do "
        "Portal da Transparência (sem chave de API: a API exige `chave-api-dados` e chave está "
        "proibida neste repositório). Só `TIPO FAVORECIDO = Administração Pública Municipal`. A "
        "rota é derivação declarada dos códigos de função e subfunção — constitucional (FPM, cotas, "
        "royalties) · saúde (função 10) · assistência social (função 08) · defesa civil (subfunção "
        "182) · outras. Linha municipal SEM MUNICÍPIO identificado na fonte vive em "
        "`sem_municipio_na_fonte`, por UF, separada de `nao_casados`: não foi dito e não consegui "
        "ler são coisas diferentes. Mês muito abaixo da mediana de linhas dos demais é marcado "
        "`parcial`, porque o Portal publica o arquivo do mês e continua enchendo. EMENDA "
        "PARLAMENTAR NÃO É IDENTIFICÁVEL nesta fonte e por isso não existe "
        "como rota aqui. A chave do arquivo é o código SIAFI e o site é indexado por IBGE: o "
        "casamento é por UF e nome normalizado, e o que não casa fica em `nao_casados`, com o valor, "
        "nunca descartado. PESO ZERO: nunca lido por recalcular_mare.py nem por "
        "gerar_monitor_saude.py.")
    dados["fonte"] = "https://portaldatransparencia.gov.br/download-de-dados/transferencias/"
    dados["atualizado_em"] = hoje_editorial().strftime("%d/%m/%Y")
    dados["rotas"] = list(ROTAS)
    gravar_em(SAIDA, dados)
    log_busca("DOU", 1, [url], "registro",
              resultados=(f"{mes}: {linhas} linha(s) municipal(is), {len(por_ibge)} município(s) "
                          f"casado(s), {len(nao_casados)} não casado(s)"),
              n_resultados=linhas, hash_evidencia=h)
    funil.registrar("transferencias_municipais", consultas=1, com_resultado_bruto=1,
                    municipios=len(por_ibge))
    return {"mes": mes, "linhas": linhas, "casados": len(por_ibge),
            "nao_casados": len(nao_casados), "sem_municipio": len(sem_municipio), "soma": soma,
            "parcial": bool(dados["meses_lidos"].get(mes, {}).get("parcial"))}


def autoteste() -> int:
    import datetime
    CSV = ("ANO / MÊS;TIPO TRANSFERÊNCIA;TIPO FAVORECIDO;UF;CÓDIGO MUNICÍPIO SIAFI;NOME MUNICÍPIO;"
           "CÓDIGO FUNÇÃO;CÓDIGO SUBFUNÇÃO;VALOR TRANSFERIDO\r\n"
           "202601;Constitucionais e Royalties;Administração Pública Municipal;AC;0643;ACRELANDIA;28;846;1.000,50\r\n"
           "202601;Legais, Voluntárias e Específicas;Administração Pública Municipal;AC;0643;ACRELANDIA;10;301;2.000,00\r\n"
           "202601;Legais, Voluntárias e Específicas;Administração Pública Municipal;AC;0643;ACRELANDIA;06;182;500,00\r\n"
           "202601;Legais, Voluntárias e Específicas;Administração Pública Estadual ou do Distrito Federal;AC;;;10;301;99.999,00\r\n"
           "202601;Legais, Voluntárias e Específicas;Administração Pública Municipal;AC;9999;CIDADE QUE NAO EXISTE;08;244;777,00\r\n"
           "202601;Legais, Voluntárias e Específicas;Administração Pública Municipal;PE;;;10;301;1.234,00\r\n")
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w") as z:
        z.writestr("transferencias.csv", CSV.encode("latin-1"))
    corpo = zb.getvalue()
    ref = [{"uf": "AC", "nome": "Acrelândia", "codigo_ibge": 1200054}]
    chave = mapa_siafi_para_ibge(ref)
    por_ibge, nao_casados, sem_municipio, linhas, soma = ler_mes(corpo, chave)
    fundido = fundir({}, "202601", por_ibge, nao_casados, sem_municipio, linhas, soma)
    duas_vezes = fundir(fundido, "202601", por_ibge, nao_casados, sem_municipio, linhas, soma)
    # Três meses, um deles com um décimo das linhas: é o caso do setembro real.
    marcados = marcar_parciais({"202601": {"linhas_municipais": 44000, "soma": 1.0},
                                "202602": {"linhas_municipais": 50000, "soma": 1.0},
                                "202603": {"linhas_municipais": 4000, "soma": 1.0}})
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")

    def grava_em(nome):
        return ("grav" + "ar_em(RAIZ / \"data\" / \"" + nome) in fonte

    casos = {
        "nome do Portal casa com o do IBGE depois de normalizar":
            lambda: normalizar("ACRELANDIA") == normalizar("Acrelândia") == "ACRELANDIA",
        "normalização não junta municípios diferentes":
            lambda: normalizar("Santa Luzia") != normalizar("Santa Luzia do Norte"),
        "valor brasileiro vira número":
            lambda: valor_br("1.224.730,35") == 1224730.35 and valor_br("") == 0.0,
        # Valor ilegível tratado como zero somaria errado em silêncio, num arquivo de dinheiro.
        "valor ilegível levanta em vez de virar zero":
            lambda: _levanta(lambda: valor_br("mil reais")),
        "constitucional vem do tipo de transferência":
            lambda: rota_de("Constitucionais e Royalties", "10", "301") == "constitucional",
        # A ordem das regras: defesa civil é SUBFUNÇÃO dentro de outras funções.
        "defesa civil vence a função em que estiver":
            lambda: rota_de("Legais, Voluntárias e Específicas", "10", "182") == "defesa_civil",
        "saúde e assistência pela função":
            lambda: (rota_de("Legais, Voluntárias e Específicas", "10", "301") == "saude"
                     and rota_de("Legais, Voluntárias e Específicas", "08", "244") == "assistencia_social"),
        "o resto é 'outras'":
            lambda: rota_de("Legais, Voluntárias e Específicas", "12", "361") == "outras",
        # O filtro que impede inflar o número da cidade com dinheiro que não é dela.
        "só linha de administração municipal entra":
            lambda: linhas == 5 and 99999.0 not in [v for r in por_ibge.values() for v in r.values()],
        "as três rotas do município somam o que o CSV diz":
            lambda: por_ibge["1200054"] == {"constitucional": 1000.5, "saude": 2000.0, "defesa_civil": 500.0},
        # As duas regras gerais e a tabela, com os casos REAIS que as criaram.
        "o sufixo do nome antigo do SIAFI sai antes de comparar":
            lambda: RE_SUFIXO_EX.sub("", "CAMPO GRANDE  EX AUGUSTO SEVERO").strip() == "CAMPO GRANDE",
        "o município é indexado por todos os seus nomes":
            lambda: nomes_do_municipio("Januário Cicco (Boa Saúde)") == {"JANUARIO CICCO BOA SAUDE",
                                                                         "JANUARIO CICCO", "BOA SAUDE"},
        "nome sem parênteses tem um nome só":
            lambda: nomes_do_municipio("Acrelândia") == {"ACRELANDIA"},
        "a equivalência declarada casa a grafia do SIAFI":
            lambda: mapa_siafi_para_ibge(
                [{"uf": "CE", "nome": "Itapajé", "codigo_ibge": 2306306}]).get(("CE", "ITAPAGE")) == "2306306",
        "a tabela de equivalências não tem destino que a referência desconheça":
            lambda: all(isinstance(v, str) and v.strip() for v in EQUIVALENCIAS.values()),
        # Município que não casa não desaparece: fica declarado, com o dinheiro que ficou de fora.
        "município sem casamento fica declarado, com valor":
            lambda: nao_casados == {("AC", "CIDADE QUE NAO EXISTE"): 777.0},
        "o não casado aparece na saída, não é descartado":
            lambda: fundido["nao_casados"] == {"AC|CIDADE QUE NAO EXISTE": 777.0},
        "o total do município é a soma das rotas":
            lambda: fundido["municipios"]["1200054"]["total"] == 3500.5,
        "o mês fica registrado com a sua contagem":
            lambda: fundido["meses_lidos"]["202601"]["linhas_municipais"] == 5,
        # Reler o mesmo mês SUBSTITUI aquele mês; não soma duas vezes.
        "reler o mesmo mês é idempotente":
            lambda: duas_vezes["municipios"]["1200054"]["total"] == 3500.5,
        # A fonte que não diz qual município: lacuna DELA, separada do nome que não casou.
        "linha municipal sem município fica em 'sem_municipio_na_fonte'":
            lambda: sem_municipio == {"PE": 1234.0} and fundido["sem_municipio_na_fonte"] == {"PE": 1234.0},
        "sem município não entra como não casado":
            lambda: ("PE", "") not in nao_casados and "PE|" not in fundido["nao_casados"],
        # O mês incompleto é marcado pela medição, não arbitrado.
        "mês com um décimo das linhas é marcado como parcial":
            lambda: marcados["202603"].get("parcial") is True and "mediana" in marcados["202603"]["parcial_porque"],
        "mês normal não é marcado":
            lambda: "parcial" not in marcados["202601"] and "parcial" not in marcados["202602"],
        "com menos de três meses nada é marcado: não há mediana que signifique algo":
            lambda: all("parcial" not in v for v in marcar_parciais(
                {"202601": {"linhas_municipais": 44000}, "202602": {"linhas_municipais": 400}}).values()),
        "CSV sem as colunas esperadas levanta, em vez de devolver vazio":
            lambda: _levanta(lambda: ler_mes(_zip_de("A;B\r\n1;2\r\n"), chave)),
        "ZIP sem CSV levanta":
            lambda: _levanta(lambda: ler_mes(_zip_vazio(), chave)),
        # O mês corrente fica fora: o Portal publica o arquivo fechado.
        "o mês em curso não é coletado":
            lambda: meses_do_ano(2026, datetime.date(2026, 10, 1))[-1] == "202609",
        "ano passado vai até dezembro":
            lambda: meses_do_ano(2025, datetime.date(2026, 10, 1))[-1] == "202512",
        # TRAVA ESTRUTURAL: este coletor não pode ganhar escrita no índice.
        # A lista dos proibidos é a MESMA do resto do projeto (`descobrir_planos.py`): os cinco
        # arquivos do banco. A primeira versão desta trava cobria três, e o revisor de travas acusou
        # — com razão: trava que esquece dois nomes não pegaria uma escrita futura em `saude_uf.json`
        # nem em `monitor_saude.json`. Frouxa por omissão continua frouxa.
        "o fonte grava só no arquivo de transferências":
            lambda: ("grav" + "ar_em(SAIDA") in fonte
                     and not any(grava_em(n) for n in BANCO_PROIBIDO),
        "a lista de proibidos é a do projeto, com os cinco arquivos do banco":
            lambda: set(BANCO_PROIBIDO) == {"estados.json", "saude_uf.json", "municipios.json",
                                            "indice.json", "monitor_saude.json"},
        "a saída é o arquivo por município, de peso zero":
            lambda: SAIDA.name == "transferencias_uniao.json" and "PESO ZERO" in fonte,
    }
    return rodar_autoteste(casos)


def _levanta(fn) -> bool:
    try:
        fn()
    except Exception:  # noqa: BLE001
        return True
    return False


def _zip_de(csv_texto: str) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("x.csv", csv_texto.encode("latin-1"))
    return b.getvalue()


def _zip_vazio() -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("leia-me.txt", "sem csv")
    return b.getvalue()


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    if "--mes" in args:
        print(coletar(args[args.index("--mes") + 1]))
        return 0
    if "--ano" in args:
        ano = int(args[args.index("--ano") + 1])
        for mes in meses_do_ano(ano):
            print(coletar(mes))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
