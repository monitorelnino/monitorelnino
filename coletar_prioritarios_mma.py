#!/usr/bin/env python3
"""Municípios prioritários para controle do desmatamento — Portaria GM/MMA nº 1.202/2024.

PR 3 do handover do enquadramento federal de risco (editoria, 30/09/2026).

O QUE ESTA LISTA É, E O QUE ELA NÃO É
-------------------------------------
Ela é a lista federal de municípios do bioma Amazônia **prioritários para ações de prevenção,
controle e redução do desmatamento e da degradação florestal** (Anexo I, 81 municípios), base do
programa União com Municípios. O Anexo II é outra coisa: municípios com desmatamento **monitorado
e sob controle** (10), e por isso entra como flag separado, nunca somado ao primeiro.

Ela **não é** uma lista de risco de incêndio. Desmatamento e fogo andam juntos na Amazônia e o
programa trata dos dois, mas a portaria fala de desmatamento e degradação florestal — chamar isto
de "lista de risco de incêndio" seria afirmar mais do que o instrumento diz.

A FONTE
-------
O texto publicado no Diário Oficial da União de 13/11/2024, seção 1, página 121. A página do MMA
que listaria os municípios não serve: `combateaodesmatamento.mma.gov.br` responde 403 (recusa de
acesso, que se respeita) e a página de `gov.br/mma` chega sem o conteúdo, montado por JavaScript.
O DOU é a publicação oficial do ato e traz os dois anexos inteiros.

**O anexo traz o código IBGE de cada município.** O handover previa casar por nome e UF, com erro
reportado, porque a portaria poderia não trazer código. Ela traz: `Código · Município · UF`. Então
não há aproximação de nome nenhuma aqui — o código é lido, e conferido contra a base do projeto.

CADÊNCIA E VIGÊNCIA
-------------------
A lista é atualizada anualmente, pelos dados do PRODES/INPE, e cada portaria revoga a anterior (a
1.202/2024 revogou a 834/2023). Não existe fonte pública consultável por máquina que diga "esta é
a vigente": a busca do DOU monta os resultados por um endereço interno, que não se usa. Então o
coletor faz o que pode fazer com honestidade: lê o ato que conhece, grava a data de publicação
dele, e **avisa em voz alta** quando a janela da atualização anual já passou sem que o ato tenha
mudado — para a conferência ser feita por gente, e não presumida.

PESO ZERO
---------
Camada de contexto. Não escreve em `indice.json`, `estados.json`, `saude_uf.json` nem
`monitor_saude.json`, e não pontua.

USO
  python3 coletar_prioritarios_mma.py --autoteste
  python3 coletar_prioritarios_mma.py
"""
import datetime
import html
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

# 01/10/2026 (conferência pedida pela editoria): a 1.202/2024 FOI REVOGADA. A Portaria MMA nº
# 1.717, de 19/06/2026 — publicada na edição extra do DOU de 23/06/2026 — declara as duas listas
# novas e revoga a 1.202 no art. 2º. Ela se apoia nos critérios da Portaria MMA/GM nº 1.716, do
# mesmo dia, que por sua vez revogou a 833/2023.
#
# Como o ato foi encontrado, e por que isto está escrito aqui: a busca do DOU é montada por
# JavaScript e não se lê por máquina, mas a EDIÇÃO do dia se lê — `in.gov.br/leiturajornal` traz
# um `<script id="params">` com a lista de atos daquela seção. Varrendo as edições de junho e
# julho de 2026, seção 1 e seção 1 extra, os atos apareceram na extra de 23/06. A notícia
# regional que levou à conferência dizia "89 municípios"; o ato diz **80**. Pista é pista.
FONTE = ("https://www.in.gov.br/web/dou/-/"
         "portaria-mma-n-1.717-de-19-de-junho-de-2026-714110982")
INSTRUMENTO = ("Portaria MMA nº 1.717, de 19 de junho de 2026, publicada no Diário Oficial da "
               "União de 23/06/2026, edição extra, seção 1 (revoga a Portaria GM/MMA nº "
               "1.202/2024; critérios na Portaria MMA/GM nº 1.716/2026)")
PUBLICADA_EM = datetime.date(2026, 6, 23)
SAIDA = RAIZ / "data" / "enquadramento_federal.json"
MUNICIPIOS = RAIZ / "data" / "verificacao_municipal.json"

TOTAL_ANEXO_I = 80
TOTAL_ANEXO_II = 17
# Amazônia Legal: os nove estados. UF fora daqui significa que a leitura pegou linha de outra
# tabela da mesma página.
UFS_ESPERADAS = {"AC", "AM", "AP", "MA", "MT", "PA", "RO", "RR", "TO"}
# Distribuição MEDIDA no Anexo I da 1.717/2026, e ela soma 80. Trava contra leitura parcial: o
# total pode fechar por acidente, sete contagens não. Estes números são lidos do ato, nunca
# lembrados — escrevi uma versão de cabeça no coletor do Semiárido e a validação reprovou, com
# razão. O MA entra nesta lista pela primeira vez; o AC cai de 5 para 4 e o RO de 6 para 3.
POR_UF_ANEXO_I_ESPERADO = {"AC": 4, "AM": 10, "MA": 1, "MT": 30, "PA": 30, "RO": 3, "RR": 2}

# A 1.202/2024 trazia `Código · Município · UF`; a 1.717/2026 traz `Nº · Código · UF · Município`,
# com as colunas "Desmatamento" e "Degradação" marcadas por X. São dois formatos de tabela para o
# mesmo tipo de ato, e o coletor lê os dois: tentar só o formato novo quebraria a releitura de um
# ato antigo preservado, e tentar só o antigo é o que faria este coletor ler zero linha hoje.
#
# A ordem importa na escolha: o formato NOVO é tentado primeiro, e o antigo só se o novo não
# devolver nada. O inverso daria casamento parcial — `(\d{7})\s+(.+?)\s+([A-Z]{2})` encontra, numa
# linha do formato novo, o código seguido do nome e de uma sigla que é a da LINHA SEGUINTE.
RE_LINHA_NOVA = re.compile(r"\d{1,3}\s+(\d{7})\s+([A-Z]{2})\s+(.+?)(?=(?:\s+X)+|\s+\d{1,3}\s+\d{7}|\s*$|\s+ANEXO)")
RE_LINHA_ANTIGA = re.compile(r"(\d{7})\s+(.+?)\s+([A-Z]{2})(?=\s+\d{7}|\s*$|\s+ANEXO)")


def linhas_de(trecho: str) -> list:
    """[(codigo, nome, uf)] de um trecho de anexo, nos dois formatos de tabela. Função pura."""
    novas = [(cod, nome.strip(), uf) for cod, uf, nome in RE_LINHA_NOVA.findall(trecho)]
    if novas:
        return novas
    return [(cod, nome.strip(), uf) for cod, nome, uf in RE_LINHA_ANTIGA.findall(trecho)]


def texto_do_ato(corpo: bytes) -> str:
    """O texto corrido do ato, a partir do HTML do DOU. Função pura.

    O corpo do ato vive numa `div.texto-dou`; fora dela há menu, rodapé e script, onde qualquer
    sequência de sete dígitos viraria município. Sem a `div`, devolve vazio — e a validação
    reprova, que é melhor do que ler a página inteira e gravar ruído."""
    bruto = corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else str(corpo)
    m = re.search(r'class="texto-dou".*?</div>', bruto, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(0)))).strip()


def anexos(texto: str) -> tuple:
    """(anexo I, anexo II), cada um [(codigo, nome, uf)]. Função pura.

    Os dois anexos têm o mesmo formato de linha e se distinguem pela posição: o I vai do rótulo
    "ANEXO I" até o "ANEXO II", o II daí ao fim. Ler a página toda de uma vez misturaria as duas
    listas, e elas dizem coisas opostas — prioritário e sob controle."""
    t = texto or ""
    i1, i2 = t.find("ANEXO I"), t.find("ANEXO II")
    if i1 < 0 or i2 < 0 or i2 <= i1:
        return [], []
    return linhas_de(t[i1:i2]), linhas_de(t[i2:])


def registros_de(anexo_i: list, anexo_ii: list, base: dict) -> list:
    """Um registro por município citado na portaria, com os dois flags. Função pura.

    `base` é `{codigo_ibge: {"uf":…, "nome":…}}`. O nome do site vem da base; o da portaria fica
    só para o caso de a base não conhecer o código — e aí a validação reprova de todo modo."""
    fora = {}
    for anexo, chave in ((anexo_i, "mma_prioritario_desmatamento"),
                         (anexo_ii, "mma_monitorado_sob_controle")):
        for codigo, nome, uf in anexo:
            conhecido = base.get(codigo) or {}
            registro = fora.setdefault(codigo, {
                "codigo_ibge": codigo,
                "uf": conhecido.get("uf") or uf,
                "municipio": conhecido.get("nome") or nome.strip(),
                "mma_prioritario_desmatamento": False,
                "mma_monitorado_sob_controle": False,
            })
            registro[chave] = True
    return [fora[c] for c in sorted(fora)]


def problemas(anexo_i: list, anexo_ii: list, registros: list, base: dict) -> list:
    """As falhas que impedem a gravação. Função pura."""
    ruins = []
    if len(anexo_i) != TOTAL_ANEXO_I:
        ruins.append(f"Anexo I: {len(anexo_i)} municípios lidos, {TOTAL_ANEXO_I} esperados")
    if len(anexo_ii) != TOTAL_ANEXO_II:
        ruins.append(f"Anexo II: {len(anexo_ii)} municípios lidos, {TOTAL_ANEXO_II} esperados")
    nos_dois = ({c for c, _, _ in anexo_i} & {c for c, _, _ in anexo_ii})
    if nos_dois:
        ruins.append(f"{len(nos_dois)} município(s) nos dois anexos ao mesmo tempo — prioritário e "
                     f"sob controle se excluem: {', '.join(sorted(nos_dois)[:5])}")
    orfaos = [r["codigo_ibge"] for r in registros if r["codigo_ibge"] not in base]
    if base and orfaos:
        ruins.append(f"{len(orfaos)} código(s) IBGE fora da base de municípios do projeto: "
                     f"{', '.join(orfaos[:5])}")
    estranhas = sorted({r["uf"] for r in registros if r["uf"]} - UFS_ESPERADAS)
    if estranhas:
        ruins.append(f"UF fora da Amazônia Legal: {', '.join(estranhas)}")
    if base:
        contagem = {}
        for c, _, _ in anexo_i:
            uf = (base.get(c) or {}).get("uf")
            contagem[uf] = contagem.get(uf, 0) + 1
        for uf, esperado in POR_UF_ANEXO_I_ESPERADO.items():
            if contagem.get(uf, 0) != esperado:
                ruins.append(f"Anexo I, {uf}: {contagem.get(uf, 0)} municípios, "
                             f"{esperado} esperados")
    sem_nome = [r["codigo_ibge"] for r in registros if not r["municipio"]]
    if sem_nome:
        ruins.append(f"{len(sem_nome)} município(s) sem nome: {', '.join(sem_nome[:5])}")
    return ruins


def atualizacao_anual_pendente(hoje, publicada_em=PUBLICADA_EM) -> bool:
    """True quando a janela da atualização anual já passou. Função pura.

    As portarias de 2023 e 2024 saíram em novembro; a de 2026 saiu em junho. O mês do ato, portanto,
    não é régua — a régua é o ANO: passado um ano da publicação do ato que este coletor conhece, é
    provável que exista portaria nova, e provável não é sabido, por isso o coletor avisa em vez de
    decidir. Aviso não bloqueia: a lista lida continua sendo a que se leu, e o site diz qual ato ela é.

    01/10/2026: a régua anterior era "1º de dezembro do ano seguinte", desenhada para atos de
    novembro. Com a 1.717 publicada em junho de 2026, ela só avisaria em dezembro de 2027 — dezoito
    meses de silêncio. O aniversário da publicação não tem esse buraco."""
    return hoje >= datetime.date(publicada_em.year + 1, publicada_em.month, publicada_em.day)


def fundir(anterior: dict, registros: list) -> dict:
    """Junta os registros do MMA ao arquivo, sem apagar o que os outros coletores gravaram.

    Mesma regra do coletor do Semiárido: o arquivo é de três famílias e cada coletor escreve só a
    sua chave. Quem saiu da lista fica com o flag falso — sair de uma lista federal é informação,
    e um município que desaparecesse do arquivo apareceria no site como nunca listado. Função
    pura."""
    fora = dict(anterior or {})
    municipios = dict(fora.get("municipios") or {})
    novos = {r["codigo_ibge"] for r in registros}
    for codigo, registro in list(municipios.items()):
        if codigo in novos:
            continue
        if registro.get("mma_prioritario_desmatamento") or \
                registro.get("mma_monitorado_sob_controle"):
            registro = dict(registro)
            registro["mma_prioritario_desmatamento"] = False
            registro["mma_monitorado_sob_controle"] = False
            municipios[codigo] = registro
    for r in registros:
        atual = dict(municipios.get(r["codigo_ibge"]) or {})
        atual.update(r)
        municipios[r["codigo_ibge"]] = atual
    fora["municipios"] = dict(sorted(municipios.items()))
    return fora


ATO = (' <div class="texto-dou"> PORTARIA GM/MMA Nº 1.202 ... resolve: ANEXO I LISTA DE MUNICÍPIOS'
       ' SITUADOS NO BIOMA AMAZÔNIA CONSIDERADOS PRIORITÁRIOS Código Município UF'
       ' 1500602 Altamira PA 5105507 Vila Bela da Santíssima Trindade MT'
       ' ANEXO II LISTA DE MUNICÍPIOS COM DESMATAMENTO MONITORADO E SOB CONTROLE'
       ' Código Município UF 5100250 Alta Floresta MT </div>')


def autoteste() -> int:
    base = {"1500602": {"uf": "PA", "nome": "Altamira"},
            "5105507": {"uf": "MT", "nome": "Vila Bela da Santíssima Trindade"},
            "5100250": {"uf": "MT", "nome": "Alta Floresta"}}
    casos = []

    texto = texto_do_ato(ATO.encode("utf-8"))
    casos.append(("lê o corpo do ato da div do DOU", "ANEXO I" in texto))
    casos.append(("página sem a div devolve vazio",
                  texto_do_ato(b"<html><body>1500602 Altamira PA</body></html>") == ""))

    a1, a2 = anexos(texto)
    casos.append(("separa o Anexo I", [c for c, _, _ in a1] == ["1500602", "5105507"]))
    casos.append(("separa o Anexo II", [c for c, _, _ in a2] == ["5100250"]))
    casos.append(("nome com espaços fica inteiro", a1[1][1] == "Vila Bela da Santíssima Trindade"))
    casos.append(("texto sem anexo devolve duas listas vazias", anexos("qualquer coisa") == ([], [])))
    casos.append(("texto vazio não quebra", anexos("") == ([], [])))

    regs = registros_de(a1, a2, base)
    casos.append(("um registro por município citado", len(regs) == 3))
    casos.append(("prioritário do Anexo I marcado",
                  regs[0]["mma_prioritario_desmatamento"] is True))
    casos.append(("prioritário não vira monitorado",
                  regs[0]["mma_monitorado_sob_controle"] is False))
    monitorado = [r for r in regs if r["codigo_ibge"] == "5100250"][0]
    casos.append(("Anexo II marca só o flag de monitorado",
                  monitorado["mma_monitorado_sob_controle"] is True
                  and monitorado["mma_prioritario_desmatamento"] is False))
    casos.append(("nome vem da base do projeto", regs[0]["municipio"] == "Altamira"))
    casos.append(("sem base, usa o nome da portaria",
                  registros_de(a1, [], {})[0]["municipio"] == "Altamira"))
    casos.append(("ordena por código",
                  [r["codigo_ibge"] for r in regs] == sorted(r["codigo_ibge"] for r in regs)))

    casos.append(("contagem errada do Anexo I reprova",
                  any("Anexo I: 2 municípios" in p for p in problemas(a1, a2, regs, base))))
    cheio_i = [(str(1500000 + i), f"m{i}", "PA") for i in range(TOTAL_ANEXO_I)]
    cheio_ii = [(str(5100000 + i), f"n{i}", "MT") for i in range(TOTAL_ANEXO_II)]
    casos.append(("contagens certas e sem base não reprovam por contagem",
                  not any("esperados" in p and "Anexo I:" in p
                          for p in problemas(cheio_i, cheio_ii, [], {}))))
    repetido = problemas([("1500602", "x", "PA")], [("1500602", "x", "PA")], [], {})
    casos.append(("município nos dois anexos reprova",
                  any("nos dois anexos" in p for p in repetido)))
    casos.append(("código fora da base reprova",
                  any("fora da base" in p for p in problemas(
                      a1, a2, [{"codigo_ibge": "9999999", "uf": "PA", "municipio": "x"}], base))))
    casos.append(("UF fora da Amazônia Legal reprova",
                  any("Amazônia Legal" in p for p in problemas(
                      a1, a2, [{"codigo_ibge": "1500602", "uf": "SP", "municipio": "x"}], base))))
    casos.append(("distribuição por UF do Anexo I é conferida com base",
                  any("Anexo I, PA" in p for p in problemas(a1, a2, regs, base))))
    casos.append(("município sem nome reprova",
                  any("sem nome" in p for p in problemas(
                      a1, a2, [{"codigo_ibge": "1500602", "uf": "PA", "municipio": ""}], base))))

    # A data do ato entra EXPLÍCITA: estes casos testam a função, não a portaria da vez. Antes eles
    # usavam o padrão, e quando a 1.717/2026 substituiu a 1.202/2024 dois deles reprovaram sozinhos
    # — o teste media o calendário em vez da regra.
    _nov = datetime.date(2024, 11, 13)
    casos.append(("no mesmo ano do ato não avisa",
                  not atualizacao_anual_pendente(datetime.date(2024, 12, 20), _nov)))
    casos.append(("um dia antes do aniversário não avisa",
                  not atualizacao_anual_pendente(datetime.date(2025, 11, 12), _nov)))
    casos.append(("no aniversário da publicação avisa",
                  atualizacao_anual_pendente(datetime.date(2025, 11, 13), _nov)))
    casos.append(("depois do aniversário avisa",
                  atualizacao_anual_pendente(datetime.date(2026, 9, 30), _nov)))
    # Ato de junho: a régua antiga ("dezembro do ano seguinte") só avisaria 18 meses depois.
    _jun = datetime.date(2026, 6, 23)
    casos.append(("ato de junho: avisa no aniversário, não em dezembro",
                  atualizacao_anual_pendente(datetime.date(2027, 6, 23), _jun)
                  and not atualizacao_anual_pendente(datetime.date(2027, 6, 22), _jun)))

    velho = {"municipios": {"2900207": {"codigo_ibge": "2900207", "semiarido": True},
                            "1500800": {"codigo_ibge": "1500800", "uf": "PA",
                                        "mma_prioritario_desmatamento": True}}}
    fundido = fundir(velho, regs)
    casos.append(("não apaga o que outro coletor gravou",
                  fundido["municipios"]["2900207"]["semiarido"] is True))
    casos.append(("quem saiu da lista fica com flag falso, não desaparece",
                  fundido["municipios"]["1500800"]["mma_prioritario_desmatamento"] is False))
    casos.append(("quem nunca esteve na lista não ganha o campo",
                  "mma_prioritario_desmatamento" not in fundido["municipios"]["2900207"]))
    casos.append(("quem entrou é acrescentado",
                  fundido["municipios"]["1500602"]["mma_prioritario_desmatamento"] is True))
    casos.append(("anterior vazio não quebra", "municipios" in fundir({}, [])))
    casos.append(("chaves em ordem de código",
                  list(fundido["municipios"]) == sorted(fundido["municipios"])))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita em data/.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import buscar, gravar_em, hoje_editorial, preservar_evidencia, sha256
    hoje = hoje_editorial()
    corpo = buscar(FONTE, timeout=120, origem="coletar_prioritarios_mma")
    texto = texto_do_ato(corpo)
    # O hash é do TEXTO do ato, não do HTML: a página do DOU muda de bytes a cada resposta (menu,
    # script, carimbo de sessão) e um hash do HTML nunca repetiria, guardando uma evidência nova
    # por semana para um ato que não muda. O texto do ato é o que importa e é estável.
    impressao = sha256(texto.encode("utf-8"))
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    igual = ((anterior.get("fontes") or {}).get("mma_desmatamento") or {}).get("hash") == impressao
    if not igual:
        preservar_evidencia(corpo, FONTE, "html", "coletar_prioritarios_mma")

    anexo_i, anexo_ii = anexos(texto)
    base = {}
    if MUNICIPIOS.exists():
        base = {str(m["ibge"]).zfill(7): {"uf": m.get("uf"), "nome": m.get("nome")}
                for m in json.loads(MUNICIPIOS.read_text(encoding="utf-8")) if m.get("ibge")}
    registros = registros_de(anexo_i, anexo_ii, base)
    print(f"Anexo I: {len(anexo_i)} · Anexo II: {len(anexo_ii)} · "
          f"evidência {impressao[:12]}")

    ruins = problemas(anexo_i, anexo_ii, registros, base)
    if ruins:
        print("X VALIDAÇÃO — nada foi gravado:")
        for r in ruins:
            print("   -", r)
        return 1

    if atualizacao_anual_pendente(hoje):
        print(f"! ATENÇÃO — a lista do MMA é atualizada todo ano, e o ato lido é de "
              f"{PUBLICADA_EM.strftime('%d/%m/%Y')}. A janela da atualização anual já passou: "
              f"confira no DOU se existe portaria posterior antes de tratar esta como vigente.")

    saida = fundir(anterior, registros)
    fontes = dict(saida.get("fontes") or {})
    fontes["mma_desmatamento"] = {
        "instrumento": INSTRUMENTO, "url": FONTE, "consultado_em": hoje.isoformat(),
        "publicada_em": PUBLICADA_EM.isoformat(), "hash": impressao,
        "total_anexo_i": TOTAL_ANEXO_I, "total_anexo_ii": TOTAL_ANEXO_II,
    }
    saida["fontes"] = fontes
    saida.setdefault("_governanca", (
        "Enquadramento federal de risco por município: camada de CONTEXTO, PESO ZERO. Não pontua "
        "e não entra no índice. Constar de lista federal não é preparação; não constar não é falta "
        "de preparação. Cada família tem seu instrumento e sua fonte, declarados em `fontes`."
    ))
    saida["atualizado_em"] = hoje.isoformat()
    gravar_em(SAIDA, saida)                                 # §229
    print(f"{SAIDA.relative_to(RAIZ)} gravado · {len(anexo_i)} prioritários, "
          f"{len(anexo_ii)} monitorados e sob controle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
