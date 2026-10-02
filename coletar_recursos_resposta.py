#!/usr/bin/env python3
"""Recursos federais de defesa civil liberados por município — portarias da SEDEC/MIDR no DOU.

Item 7 do handover de 02/10/2026. O MARÉ já registrava o RECONHECIMENTO federal de emergência
(`coletar_s2id.py`) e as transferências constitucionais e legais pagas (Portal da Transparência).
Faltava o elo do meio, que é o que a editoria pediu: **quanto a União autorizou a transferir para
cada município**, por ato, com data e valor.

A FONTE, MEDIDA EM 02/10/2026
-----------------------------
A busca do DOU por `"Autoriza a transferência de recursos"` devolve as portarias da Secretaria
Nacional de Proteção e Defesa Civil — 77 atos entre 20/09 e 02/10/2026. Cada ato traz, no texto
integral, tudo o que o registro precisa:

    Órgão: Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de
    Proteção e Defesa Civil
    PORTARIA Nº 3.181, DE 24 DE SETEMBRO DE 2026
    Art. 1º Autorizar a transferência de recursos ao município de Joaíma/MG para a execução de
    ações de Recuperação … no valor de R$ 416.281,64 …

"LIBERADO" NÃO É "TRANSFERIDO", E "RESPOSTA" NÃO É "RECUPERAÇÃO"
---------------------------------------------------------------
Duas distinções que o vocabulário da METODOLOGIA exige e que este coletor mantém separadas:

1. A portaria **autoriza**; o dinheiro sai depois, e quem registra a saída é o Portal da
   Transparência. O que se guarda aqui é `valor_autorizado`, e a página diz "liberado" — nunca
   "pago" nem "transferido".
2. A mesma rota autoriza ações de **Resposta** e de **Recuperação**, e o próprio art. 1º diz qual é.
   Resposta é o socorro imediato; recuperação é a obra depois. Somar as duas num cartão de
   "recursos de resposta" seria inflar o número com dinheiro de outra finalidade, e por isso o
   arquivo guarda as duas com o rótulo que o ato deu (`acao`), separadas.

MUNICÍPIO QUE NÃO CASA NÃO SOME
-------------------------------
O nome vem do ato, no formato `Joaíma/MG`, e é pareado com a referência do IBGE. O que não casar
entra em `nao_casados`, com o nome como o ato o escreveu — ninguém descarta ato por falha de
pareamento nossa.

USO
  python3 coletar_recursos_resposta.py --autoteste
  python3 coletar_recursos_resposta.py --relatorio            # o que a busca devolve, sem abrir atos
  python3 coletar_recursos_resposta.py [--desde 2026-06-29]
"""
import datetime
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import funil  # noqa: E402
from coletores_base import (buscar, gravar, hoje_editorial, ler, log_busca,  # noqa: E402
                            preservar_evidencia, referencia_ibge, registrar_lacuna,
                            rodar_autoteste, varrer_busca_dou)

SAIDA = "resposta/recursos_liberados.json"
ORIGEM = "coletar_recursos_resposta"
CONSULTA = '"Autoriza a transferência de recursos"'
CICLO = datetime.date(2026, 6, 29)
# A primeira carga NÃO varre o ciclo inteiro. Medido em 02/10/2026: a janela de 29/06 a 02/10 tem
# centenas de atos, e cada um exige abrir o texto integral com o ritmo de 2 s por domínio — horas de
# rede para um arquivo que a rodada diária preenche sozinha, dia a dia. A primeira carga lê 30 dias,
# a janela lida fica DECLARADA no arquivo (`janela_lida`), e a cadência diária estende a cobertura
# para frente. Nada aqui apresenta recorte como varredura.
PRIMEIRA_CARGA_DIAS = 30

# O órgão que autoriza transferência de recursos de defesa civil é a Secretaria Nacional de Proteção
# e Defesa Civil, e o DOU declara o órgão no cabeçalho do ato. Ato de outro órgão que apenas casa
# com a mesma expressão não entra — e não é descartado em silêncio: entra em `fora_do_orgao`.
RE_ORGAO = re.compile(r"Prote[çc][ãa]o e Defesa Civil", re.I)
# "PORTARIA Nº 3.181, DE 24 DE SETEMBRO DE 2026" — o número com ou sem ponto de milhar.
RE_PORTARIA = re.compile(r"PORTARIA\s+N[ºo°]?\s*([\d.]+),?\s+DE\s+(\d{1,2})\s+DE\s+([A-Za-zÇç]+)\s+DE\s+(\d{4})",
                         re.I)
# "ao município de Joaíma/MG" — a UF vem junto, com barra, e é isso que permite parear sem adivinhar.
RE_MUNICIPIO = re.compile(r"munic[íi]pio de\s+([^,/]+?)\s*/\s*([A-Z]{2})\b", re.I)
# "no valor de R$ 416.281,64"
RE_VALOR = re.compile(r"no valor de\s+R\$\s*([\d.]+,\d{2})", re.I)
# "para a execução de ações de Recuperação" | "de Resposta" | "de Proteção e Defesa Civil"
RE_ACAO = re.compile(r"execu[çc][ãa]o de a[çc][õo]es de\s+([A-Za-zÀ-ú ]+?)(?:\s+descritas|\s*[,.;]|\s+contid)",
                     re.I)
RE_SEI = re.compile(r"processo\s+SEI\s+n[.º°o]*\s*([\d./-]+)", re.I)
# MEDIDO em 02/10/2026: dois terços dos atos que casam com a consulta são PRORROGAÇÕES DE
# PRAZO ("Art. 1° Prorrogar o prazo de execução das ações … até 19/05/2027"), que alteram o
# prazo de uma portaria anterior e não autorizam dinheiro nenhum. Eles não têm valor porque
# não há valor — e chamá-los de "sem valor declarado" convidaria alguém, depois, a "consertar"
# o regex do valor e passar a somar dinheiro que o ato não autorizou.
RE_PRORROGACAO = re.compile(r"Prorrogar\s+o\s+prazo", re.I)

MESES = {m: i + 1 for i, m in enumerate(
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())}
# Os rótulos que o próprio ato usa, normalizados para o arquivo. Nada além disto é inventado:
# ação que o ato chame de outra coisa fica como `outra`, com o texto original guardado.
ACOES = {"resposta": "resposta", "recuperação": "recuperacao", "recuperacao": "recuperacao"}

# Arquivos do banco onde este coletor NUNCA escreve.
BANCO_PROIBIDO = ("estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json")


# =============================================================================================
# Leitura do ato — funções puras sobre o texto
# =============================================================================================
def texto_limpo(bruto) -> str:
    """O ato como texto corrido. Função pura."""
    t = bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else str(bruto or "")
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def valor_de(texto: str):
    """O valor em reais, como número. Função pura; None quando o ato não declara valor.

    Ato sem valor declarado NÃO vira zero: zero diria que a União autorizou nada, e o que houve foi
    um ato que não diz quanto."""
    m = RE_VALOR.search(texto or "")
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


def acao_de(texto: str) -> tuple:
    """(chave, rótulo como o ato escreveu). Função pura.

    MEDIDO em 02/10/2026: o ato diz "ações de" DUAS vezes, e as duas dizem coisas diferentes. A
    ementa usa o rótulo guarda-chuva da rota ("ações de Proteção e Defesa Civil") e o **art. 1º**
    diz a finalidade de verdade ("ações de Recuperação"). Pegar a primeira ocorrência classificava
    todo ato como `outra` — foi o que a primeira versão desta função fez.

    A regra: entre as ocorrências, vale a primeira que seja uma FINALIDADE (resposta, recuperação);
    o guarda-chuva só vale quando não houver finalidade declarada, e aí o rótulo original fica
    guardado, porque reclassificar o que o ato chamou de outra coisa seria decidir no lugar dele."""
    achados = [re.sub(r"\s+", " ", m.group(1)).strip() for m in RE_ACAO.finditer(texto or "")]
    if not achados:
        return "nao_declarada", None
    for rotulo in achados:
        if rotulo.lower() in ACOES:
            return ACOES[rotulo.lower()], rotulo
    return "outra", achados[0]


def data_do_ato(texto: str):
    """A data da portaria, do próprio título. Função pura."""
    m = RE_PORTARIA.search(texto or "")
    if not m:
        return None
    mes = MESES.get(m.group(3).lower())
    if not mes:
        return None
    try:
        return datetime.date(int(m.group(4)), mes, int(m.group(2)))
    except ValueError:
        return None


def ler_ato(texto: str, url: str = "") -> dict:
    """O registro do ato, ou um dicionário com `motivo` quando ele não serve. Função pura.

    Três recusas possíveis, e cada uma é declarada em vez de virar silêncio: órgão que não é a
    defesa civil nacional, ato sem município legível e ato sem valor."""
    if not RE_ORGAO.search(texto or ""):
        return {"motivo": "fora_do_orgao"}
    mm = RE_MUNICIPIO.search(texto or "")
    if not mm:
        return {"motivo": "sem_municipio_legivel"}
    if RE_PRORROGACAO.search(texto or ""):
        return {"motivo": "prorrogacao_de_prazo"}
    mp = RE_PORTARIA.search(texto or "")
    chave, rotulo = acao_de(texto)
    valor = valor_de(texto)
    if valor is None:
        return {"motivo": "sem_valor_declarado"}
    d = data_do_ato(texto)
    sei = RE_SEI.search(texto or "")
    return {
        "municipio": re.sub(r"\s+", " ", mm.group(1)).strip(),
        "uf": mm.group(2).upper(),
        "portaria": (mp.group(1) if mp else None),
        "data": d.isoformat() if d else None,
        "acao": chave,
        "acao_no_ato": rotulo,
        "valor_autorizado": valor,
        "processo_sei": sei.group(1) if sei else None,
        "url": url,
    }


def fundir(anterior: dict, registros: list, nao_casados: dict, janela: dict,
           recusas: dict) -> dict:
    """O arquivo com os atos novos acrescentados. Função pura e APPEND-ONLY por ato.

    A chave do ato é (portaria, município, UF): reler a mesma janela não duplica, e um ato
    republicado com retificação entra como ato próprio — a retificação é um ato, não uma emenda
    silenciosa ao anterior."""
    saida = json.loads(json.dumps(anterior or {}))
    mun = saida.setdefault("municipios", {})
    vistos = {(a.get("portaria"), a.get("municipio"), a.get("uf"))
              for m in mun.values() for a in (m.get("atos") or [])}
    novos = 0
    for r in registros:
        chave = (r.get("portaria"), r.get("municipio"), r.get("uf"))
        if chave in vistos:
            continue
        vistos.add(chave)
        novos += 1
        alvo = mun.setdefault(r["ibge"], {"nome": r["municipio"], "uf": r["uf"],
                                          "por_acao": {}, "atos": []})
        alvo["por_acao"][r["acao"]] = round(alvo["por_acao"].get(r["acao"], 0.0)
                                            + r["valor_autorizado"], 2)
        alvo["atos"].append({k: v for k, v in r.items() if k != "ibge"})
        alvo["total_autorizado"] = round(sum(alvo["por_acao"].values()), 2)
    pend = dict(saida.get("nao_casados") or {})
    for k, v in nao_casados.items():
        pend[k] = round(pend.get(k, 0.0) + v, 2)
    saida["nao_casados"] = {k: pend[k] for k in sorted(pend)}
    saida["janela_lida"] = janela
    saida["recusas"] = recusas
    saida["atos_novos_nesta_rodada"] = novos
    saida["atualizado_em"] = hoje_editorial().strftime("%d/%m/%Y")
    tot = {}
    for m in mun.values():
        for acao, v in (m.get("por_acao") or {}).items():
            tot[acao] = round(tot.get(acao, 0.0) + v, 2)
    saida["total_por_acao"] = tot
    saida["municipios_com_ato"] = len(mun)
    saida["_governanca"] = (
        "Recursos federais de defesa civil AUTORIZADOS por município, lidos das portarias da "
        "Secretaria Nacional de Proteção e Defesa Civil no DOU (consulta "
        f"{CONSULTA}). `valor_autorizado` é o que a portaria autoriza transferir — a saída do "
        "dinheiro é outro fato, e quem o registra é o Portal da Transparência: a página diz "
        "'liberado', nunca 'pago'. As ações de RESPOSTA e de RECUPERAÇÃO ficam separadas em "
        "`por_acao`, com o rótulo que o próprio ato usou, porque somá-las num cartão de resposta "
        "inflaria o número com dinheiro de outra finalidade. Ato sem valor declarado não vira zero: "
        "entra em `recusas.sem_valor_declarado`. Município que não casa com a referência do IBGE "
        "entra em `nao_casados`, com o nome como o ato o escreveu. Derivado de "
        "coletar_recursos_resposta.py — não se edita à mão.")
    return saida


# =============================================================================================
# A rodada
# =============================================================================================
def coletar(desde: datetime.date, ate: datetime.date = None, buscar_fn=None) -> dict:
    _buscar = buscar_fn or buscar
    ate = ate or hoje_editorial()
    itens, incompletas = varrer_busca_dou(CONSULTA, desde, ate, buscar_fn=_buscar)
    _, por_nome = referencia_ibge()
    registros, nao_casados = [], {}
    recusas = {"fora_do_orgao": 0, "prorrogacao_de_prazo": 0, "sem_municipio_legivel": 0,
               "sem_valor_declarado": 0, "ato_nao_lido": 0}
    for it in itens:
        url = it.get("url") or ""
        try:
            bruto = _buscar(url, timeout=90, origem=ORIGEM)
        except Exception as e:  # noqa: BLE001 — ato que não abre é lacuna de um ato
            recusas["ato_nao_lido"] += 1
            registrar_lacuna("recursos_resposta", f"{url}: {type(e).__name__}: {e}",
                             canal="DOU", camada=1, nivel="nacional", strings=[url])
            continue
        texto = texto_limpo(bruto)
        r = ler_ato(texto, url)
        if r.get("motivo"):
            recusas[r["motivo"]] = recusas.get(r["motivo"], 0) + 1
            continue
        cod = por_nome.get((r["municipio"], r["uf"]))
        if not cod:
            nao_casados[f"{r['uf']}|{r['municipio']}"] = round(
                nao_casados.get(f"{r['uf']}|{r['municipio']}", 0.0) + r["valor_autorizado"], 2)
            continue
        registros.append({**r, "ibge": str(cod).zfill(7)})

    janela = {"desde": desde.isoformat(), "ate": ate.isoformat(),
              "atos_na_busca": len(itens),
              "janelas_incompletas": [list(map(str, j)) for j in (incompletas or [])]}
    dados = fundir(ler(SAIDA) or {}, registros, nao_casados, janela, recusas)
    corpo = json.dumps({"consulta": CONSULTA, "janela": janela, "recusas": recusas,
                        "atos": registros}, ensure_ascii=False, indent=1).encode("utf-8")
    h = preservar_evidencia(corpo, "https://www.in.gov.br/consulta/-/buscar/dou", "json", ORIGEM)
    gravar(SAIDA, dados)
    decisao = "registro" if registros else ("consultado sem achado" if itens else "erro")
    log_busca("DOU", 1, [CONSULTA], decisao, nivel="nacional", n_resultados=len(itens),
              resultados=(f"recursos_resposta: {len(itens)} ato(s) na busca, {len(registros)} "
                          f"lido(s) e pareado(s), {len(nao_casados)} sem pareamento, "
                          f"{dados['atos_novos_nesta_rodada']} novo(s) no arquivo · recusas "
                          f"{recusas}"), hash_evidencia=h)
    funil.registrar("funil_recursos_resposta", consultas=1,
                    com_resultado_bruto=1 if itens else 0, pistas=len(registros))
    return {"atos_na_busca": len(itens), "lidos": len(registros), "novos": dados["atos_novos_nesta_rodada"],
            "nao_casados": len(nao_casados), "recusas": recusas,
            "total_por_acao": dados["total_por_acao"]}


# =============================================================================================
# Autoteste — offline, sem rede e sem escrever em data/
# =============================================================================================
def fonte_do_coletor() -> str:
    texto = pathlib.Path(__file__).read_text(encoding="utf-8")
    corte = texto.find("def autoteste")
    return texto[:corte] if corte > 0 else texto


# Recorte REAL do ato lido em 02/10/2026 (texto encurtado; a estrutura é a que veio).
FIXTURE = (
    "09/2026 | Edição: 182 | Seção: 1 | Página: 39 Órgão: Ministério da Integração e do "
    "Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil PORTARIA Nº 3.181, "
    "DE 24 DE SETEMBRO DE 2026 Autoriza a transferência de recursos ao município de Joaíma/MG, "
    "para execução de ações de Proteção e Defesa Civil. A UNIÃO, por intermédio do MINISTÉRIO DA "
    "INTEGRAÇÃO E DO DESENVOLVIMENTO REGIONAL, … resolve: Art. 1º Autorizar a transferência de "
    "recursos ao município de Joaíma/MG para a execução de ações de Recuperação descritas no Plano "
    "de Trabalho aprovado no Sistema Integrado de Informações sobre Desastres (S2iD) e contido no "
    "processo SEI n.º 59053.024553/2026-22, no valor de R$ 416.281,64 (quatrocentos e dezesseis mil "
    "duzentos e oitenta e um reais e sessenta e quatro centavos). Art. 2º Os recursos financeiros "
    "serão transferidos, a título de Transferência Legal …")
# O segundo recorte é OUTRA portaria: a chave do ato é (portaria, município, UF), e usar o mesmo
# número para simular duas finalidades testaria o dedup, não a soma — foi o que a primeira versão
# destes casos fez, e os três que falharam estavam certos em falhar.
FIXTURE_RESPOSTA = (FIXTURE.replace("ações de Recuperação", "ações de Resposta")
                    .replace("R$ 416.281,64", "R$ 1.000.000,00")
                    .replace("PORTARIA Nº 3.181", "PORTARIA Nº 3.182"))


def autoteste() -> int:
    lido = ler_ato(FIXTURE, "https://x/ato")
    resp = ler_ato(FIXTURE_RESPOSTA, "https://x/ato2")
    sem_valor = ler_ato(FIXTURE.replace("no valor de R$ 416.281,64", "sem valor"), "u")
    outro_orgao = ler_ato(FIXTURE.replace("Proteção e Defesa Civil", "Cultura"), "u")
    sem_mun = ler_ato(FIXTURE.replace("município de Joaíma/MG", "órgão central"), "u")

    r1 = {**lido, "ibge": "3135605"}
    r2 = {**resp, "ibge": "3135605"}
    um = fundir({}, [r1], {}, {"desde": "x"}, {})
    dois = fundir(um, [r1, r2], {}, {"desde": "x"}, {})

    casos = {
        "o ato real é lido: município, UF, portaria e data":
            lambda: (lido["municipio"] == "Joaíma" and lido["uf"] == "MG"
                     and lido["portaria"] == "3.181" and lido["data"] == "2026-09-24"),
        "o valor sai do ato, em número":
            lambda: lido["valor_autorizado"] == 416281.64,
        "a ação vem do próprio ato, e recuperação não é resposta":
            lambda: lido["acao"] == "recuperacao" and resp["acao"] == "resposta",
        "o rótulo original da ação é guardado":
            lambda: lido["acao_no_ato"] == "Recuperação",
        "o processo é guardado para conferência":
            lambda: lido["processo_sei"] == "59053.024553/2026-22",
        # As três recusas, cada uma declarada.
        "prorrogação de prazo não é dinheiro, e é recusada com o nome certo":
            lambda: ler_ato(FIXTURE.replace(
                "Art. 1º Autorizar a transferência de recursos ao município de Joaíma/MG para a "
                "execução de ações de Recuperação",
                "Art. 1° Prorrogar o prazo de execução das ações de Proteção e Defesa Civil no "
                "Município de Joaíma/MG até 19/05/2027"), "u") == {"motivo": "prorrogacao_de_prazo"},
        "ato sem valor declarado não vira zero: é recusa com motivo":
            lambda: sem_valor == {"motivo": "sem_valor_declarado"},
        "ato de outro órgão não entra, e diz por quê":
            lambda: outro_orgao == {"motivo": "fora_do_orgao"},
        "ato sem município legível não entra, e diz por quê":
            lambda: sem_mun == {"motivo": "sem_municipio_legivel"},
        "valor ausente devolve None, nunca 0.0":
            lambda: valor_de("texto sem valor") is None,
        "ação não declarada é dita, não adivinhada":
            lambda: acao_de("texto qualquer") == ("nao_declarada", None),
        # O arquivo: append-only por ato, e as duas finalidades separadas.
        "o mesmo ato lido duas vezes entra uma vez":
            lambda: (dois["municipios"]["3135605"]["atos"].__len__() == 2
                     and dois["atos_novos_nesta_rodada"] == 1),
        "resposta e recuperação somam separadas":
            lambda: dois["total_por_acao"] == {"recuperacao": 416281.64, "resposta": 1000000.0},
        "o total do município é a soma das duas":
            lambda: dois["municipios"]["3135605"]["total_autorizado"] == 1416281.64,
        "município que não casa entra em nao_casados, com o nome do ato":
            lambda: fundir({}, [], {"MG|Joaima do Ato": 10.0}, {}, {})["nao_casados"]
                    == {"MG|Joaima do Ato": 10.0},
        # A trava de vocabulário: o arquivo não pode chamar autorização de pagamento.
        "a governança diz 'liberado', e nunca 'pago'":
            lambda: ("'liberado', nunca 'pago'" in um["_governanca"]
                     and "valor_autorizado" in um["_governanca"]),
        # TRAVA ESTRUTURAL: nenhuma escrita no banco, nem numa edição futura.
        "o fonte não grava em nenhum arquivo do banco":
            lambda: not any(f'gravar("{nome}' in fonte_do_coletor() for nome in BANCO_PROIBIDO),
        "a lista proibida é a canônica do projeto, com os cinco arquivos":
            lambda: set(BANCO_PROIBIDO) == {"estados.json", "saude_uf.json", "municipios.json",
                                            "indice.json", "monitor_saude.json"},
        "o fonte grava só no próprio arquivo":
            lambda: sorted(set(re.findall(r"gravar\((SAIDA|\"[^\"]+\")", fonte_do_coletor()))) == ["SAIDA"],
    }
    return rodar_autoteste(casos)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    desde = max(CICLO, hoje_editorial() - datetime.timedelta(days=PRIMEIRA_CARGA_DIAS))
    if "--desde" in args:
        desde = datetime.date.fromisoformat(args[args.index("--desde") + 1])
    else:
        # Incremental: relê os sete dias anteriores à última janela, para pegar ato publicado com
        # atraso ou retificado. Reler é barato; perder ato publicado fora de ordem não é.
        anterior = (ler(SAIDA) or {}).get("janela_lida") or {}
        if anterior.get("ate"):
            desde = max(CICLO, datetime.date.fromisoformat(anterior["ate"])
                        - datetime.timedelta(days=7))
    if "--relatorio" in args:
        itens, inc = varrer_busca_dou(CONSULTA, desde, hoje_editorial())
        print(json.dumps({"consulta": CONSULTA, "desde": desde.isoformat(),
                          "atos_na_busca": len(itens),
                          "janelas_incompletas": len(inc or [])}, ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(coletar(desde), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
