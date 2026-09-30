#!/usr/bin/env python3
"""Delimitação oficial do Semiárido brasileiro — a lista nominal dos 1.477 municípios.

PR 2 do handover do enquadramento federal de risco (editoria, 30/09/2026).

POR QUE A FONTE É O IBGE, E NÃO A PÁGINA DA SUDENE
--------------------------------------------------
O handover manda ler o anexo da Resolução Condel/Sudene nº 150/2021 em `gov.br/sudene`. Essa
página não serve: renderizada com navegador, ela diz "Conteúdo em atualização" e não traz tabela,
PDF nem shapefile; a Resolução 150/2021 não aparece na página de resoluções (lá só estão as da
Diretoria Colegiada, 674 a 681 em 2021) e os endereços diretos que testei devolvem 404.

A editoria autorizou em 30/09/2026 usar a tabela do IBGE. Ela é a mesma delimitação — o IBGE
publica a lista nominal do Semiárido na estrutura territorial, na situação de 2022, que é a
vigente pela Resolução 150/2021 e oficializada pela Resolução nº 176/2024. A aba da planilha se
chama `1477 mun` e tem 1.477 linhas: a contagem do instrumento confere com a contagem do arquivo.

Isto é declarado no site como fonte: a delimitação é da Sudene, a **tabela** é do IBGE. Trocar uma
fonte primária por outra sem dizer qual foi lida seria dar por lido o que não se leu.

PESO ZERO
---------
Camada de contexto. Não escreve em `indice.json`, `estados.json`, `saude_uf.json` nem
`monitor_saude.json`, e não pontua: estar no Semiárido não é preparação nem falta dela.

CADÊNCIA
--------
Semanal, e só reprocessa se o hash do arquivo mudar — a delimitação muda por resolução, não por
dia. `--forcar` ignora a espera.

USO
  python3 coletar_semiarido_sudene.py --autoteste
  python3 coletar_semiarido_sudene.py
"""
import datetime
import io
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

FONTE = ("https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/"
         "semiarido_brasileiro/Situacao_2022/lista_municipios_Semiarido_2022.xlsx")
INSTRUMENTO = ("Delimitação do Semiárido — Sudene, Resolução Condel nº 150/2021, oficializada "
               "pela Resolução nº 176/2024; tabela nominal publicada pelo IBGE "
               "(estrutura territorial, situação 2022)")
SAIDA = RAIZ / "data" / "enquadramento_federal.json"
MUNICIPIOS = RAIZ / "data" / "verificacao_municipal.json"

TOTAL_SEMIARIDO = 1477
# Os nove estados da delimitação: os oito do Nordeste alcançados pela resolução mais Minas Gerais
# e Espírito Santo. Se aparecer UF fora daqui, a leitura pegou linha que não é do Semiárido.
UFS_ESPERADAS = {"AL", "BA", "CE", "ES", "MG", "MA", "PB", "PE", "PI", "RN", "SE"}
# Distribuição MEDIDA na planilha em 30/09/2026, UF por UF, e ela soma 1.477. É trava contra
# leitura parcial: a contagem total pode fechar por acidente, onze contagens não. Os números da
# delimitação de 2021 são maiores do que os da anterior em MG e no PI — foi a resolução que os
# ampliou, e escrever de cabeça a distribuição antiga fez a validação reprovar, com razão.
POR_UF_ESPERADO = {"AL": 42, "BA": 287, "CE": 175, "ES": 6, "MA": 16, "MG": 217,
                   "PB": 198, "PE": 142, "PI": 216, "RN": 148, "SE": 30}
DIAS_ENTRE_COLETAS = 7


def codigos_da_planilha(corpo: bytes) -> list:
    """[(codigo_ibge, nome)] da aba da planilha do IBGE.

    A planilha tem duas colunas, `CD_MUN` e `NM_MUN`, e nenhuma coluna de UF — a UF vem dos dois
    primeiros dígitos do código, casada com a base do projeto. O cabeçalho é descartado pelo
    formato: só linha cujo código tem 7 dígitos entra."""
    import openpyxl
    aba = openpyxl.load_workbook(io.BytesIO(corpo), data_only=True, read_only=True).worksheets[0]
    fora = []
    for linha in aba.iter_rows(values_only=True):
        if not linha or linha[0] is None:
            continue
        codigo = str(linha[0]).strip()
        if not (codigo.isdigit() and len(codigo) == 7):
            continue
        nome = str(linha[1]).strip() if len(linha) > 1 and linha[1] is not None else ""
        fora.append((codigo, nome))
    return fora


def registros_de(codigos: list, base: dict) -> list:
    """Um registro por município do Semiárido, com UF e nome da base do projeto. Função pura.

    `base` é `{codigo_ibge: {"uf":…, "nome":…}}`. O nome do site é o da base, não o da planilha —
    a planilha alterna caixa alta e caixa mista na mesma coluna, e o leitor do site lê um nome só."""
    fora, vistos = [], set()
    for codigo, nome_planilha in codigos:
        if codigo in vistos:
            continue
        vistos.add(codigo)
        conhecido = base.get(codigo) or {}
        fora.append({
            "codigo_ibge": codigo,
            "uf": conhecido.get("uf"),
            "municipio": conhecido.get("nome") or nome_planilha,
            "semiarido": True,
        })
    return sorted(fora, key=lambda r: r["codigo_ibge"])


def problemas(registros: list, base: dict) -> list:
    """As falhas que impedem a gravação. Função pura.

    Erro de casamento **não grava**: um código que a base do projeto não conhece significa que a
    planilha mudou de formato ou que a base está velha, e nos dois casos o certo é parar."""
    ruins = []
    if len(registros) != TOTAL_SEMIARIDO:
        ruins.append(f"{len(registros)} municípios lidos, {TOTAL_SEMIARIDO} esperados pela "
                     f"delimitação vigente")
    orfaos = [r["codigo_ibge"] for r in registros if r["codigo_ibge"] not in base]
    if orfaos:
        ruins.append(f"{len(orfaos)} código(s) IBGE fora da base de municípios do projeto: "
                     f"{', '.join(orfaos[:5])}")
    if base:
        estranhas = sorted({r["uf"] for r in registros if r["uf"]} - UFS_ESPERADAS)
        if estranhas:
            ruins.append(f"UF fora da delimitação: {', '.join(estranhas)}")
        contagem = {}
        for r in registros:
            contagem[r["uf"]] = contagem.get(r["uf"], 0) + 1
        for uf, esperado in POR_UF_ESPERADO.items():
            if contagem.get(uf, 0) != esperado:
                ruins.append(f"{uf}: {contagem.get(uf, 0)} municípios, {esperado} esperados")
    sem_nome = [r["codigo_ibge"] for r in registros if not r["municipio"]]
    if sem_nome:
        ruins.append(f"{len(sem_nome)} município(s) sem nome: {', '.join(sem_nome[:5])}")
    return ruins


def precisa_reprocessar(anterior: dict, hash_novo: str, hoje, dias=DIAS_ENTRE_COLETAS) -> bool:
    """True quando vale gravar de novo. Função pura.

    Documento novo sempre reprocessa. Documento igual só depois da cadência, para o carimbo de
    consulta não congelar numa data velha — o leitor precisa saber quando foi a última conferência,
    e "conferimos e nada mudou" é informação diferente de "paramos de conferir"."""
    if not anterior:
        return True
    fontes = (anterior.get("fontes") or {}).get("semiarido") or {}
    if fontes.get("hash") != hash_novo:
        return True
    consultado = fontes.get("consultado_em")
    try:
        antes = datetime.date.fromisoformat(str(consultado))
    except (TypeError, ValueError):
        return True
    return (hoje - antes).days >= dias


def fundir(anterior: dict, registros: list) -> dict:
    """Junta os registros do Semiárido ao arquivo, sem apagar o que os outros coletores gravaram.

    O arquivo é de três famílias — Casa Civil, Sudene e MMA — e cada coletor escreve só a sua
    chave. Um coletor que reescrevesse o arquivo inteiro apagaria as outras duas na primeira
    rodada em que corresse sozinho. Função pura."""
    fora = dict(anterior or {})
    municipios = dict(fora.get("municipios") or {})
    novos = {r["codigo_ibge"] for r in registros}
    for codigo, registro in list(municipios.items()):
        if codigo not in novos and registro.get("semiarido"):
            registro = dict(registro)
            registro["semiarido"] = False          # saiu da delimitação: registra, não some
            municipios[codigo] = registro
    for r in registros:
        atual = dict(municipios.get(r["codigo_ibge"]) or {})
        atual.update(r)
        municipios[r["codigo_ibge"]] = atual
    fora["municipios"] = dict(sorted(municipios.items()))
    return fora


def autoteste() -> int:
    base = {"2900207": {"uf": "BA", "nome": "Abaíra"},
            "3100104": {"uf": "MG", "nome": "Abadia dos Dourados"}}
    casos = []

    regs = registros_de([("2900207", "ABAÍRA"), ("3100104", "Abadia dos Dourados")], base)
    casos.append(("lê um registro por código", len(regs) == 2))
    casos.append(("nome vem da base do projeto, não da planilha em caixa alta",
                  regs[0]["municipio"] == "Abaíra"))
    casos.append(("UF vem da base", regs[0]["uf"] == "BA"))
    casos.append(("marca semiarido", all(r["semiarido"] is True for r in regs)))
    casos.append(("ordena por código", [r["codigo_ibge"] for r in regs] == ["2900207", "3100104"]))
    casos.append(("código repetido entra uma vez",
                  len(registros_de([("2900207", "A"), ("2900207", "A")], base)) == 1))
    casos.append(("sem base, usa o nome da planilha",
                  registros_de([("2900207", "ABAÍRA")], {})[0]["municipio"] == "ABAÍRA"))

    casos.append(("contagem diferente de 1.477 reprova",
                  any("1477 esperados" in p for p in problemas(regs, base))))
    cheio = [{"codigo_ibge": str(2900000 + i), "uf": "BA", "municipio": f"m{i}",
              "semiarido": True} for i in range(TOTAL_SEMIARIDO)]
    base_cheia = {r["codigo_ibge"]: {"uf": "BA", "nome": r["municipio"]} for r in cheio}
    casos.append(("1.477 com distribuição errada reprova pela distribuição",
                  any("287 esperados" in p for p in problemas(cheio, base_cheia))))
    casos.append(("sem base do projeto, a distribuição por UF não é conferida",
                  not any("esperados" in p for p in problemas(cheio, {}))))
    orfao = problemas([{"codigo_ibge": "9999999", "uf": "BA", "municipio": "x",
                        "semiarido": True}], base)
    casos.append(("código fora da base reprova", any("fora da base" in p for p in orfao)))
    fora_da_regiao = problemas([{"codigo_ibge": "2900207", "uf": "SP", "municipio": "x",
                                 "semiarido": True}], base)
    casos.append(("UF fora da delimitação reprova",
                  any("fora da delimitação" in p for p in fora_da_regiao)))
    casos.append(("município sem nome reprova",
                  any("sem nome" in p for p in problemas(
                      [{"codigo_ibge": "2900207", "uf": "BA", "municipio": "",
                        "semiarido": True}], base))))

    hoje = datetime.date(2026, 9, 30)
    casos.append(("arquivo inexistente reprocessa", precisa_reprocessar(None, "h", hoje)))
    anterior = {"fontes": {"semiarido": {"hash": "h", "consultado_em": "2026-09-29"}}}
    casos.append(("hash igual e dentro da cadência não reprocessa",
                  not precisa_reprocessar(anterior, "h", hoje)))
    casos.append(("hash diferente reprocessa sempre",
                  precisa_reprocessar(anterior, "outro", hoje)))
    casos.append(("hash igual e cadência vencida reprocessa",
                  precisa_reprocessar({"fontes": {"semiarido": {
                      "hash": "h", "consultado_em": "2026-09-20"}}}, "h", hoje)))
    casos.append(("carimbo ilegível reprocessa",
                  precisa_reprocessar({"fontes": {"semiarido": {"hash": "h",
                                                                "consultado_em": "ontem"}}},
                                      "h", hoje)))

    velho = {"municipios": {"1500107": {"codigo_ibge": "1500107", "uf": "PA",
                                        "cadastro_casa_civil": True},
                            "2900207": {"codigo_ibge": "2900207", "uf": "BA",
                                        "semiarido": True}}}
    fundido = fundir(velho, registros_de([("3100104", "Abadia dos Dourados")], base))
    casos.append(("não apaga o que outro coletor gravou",
                  fundido["municipios"]["1500107"]["cadastro_casa_civil"] is True))
    casos.append(("quem saiu da delimitação fica com semiarido falso, não desaparece",
                  fundido["municipios"]["2900207"]["semiarido"] is False))
    casos.append(("quem entrou é acrescentado",
                  fundido["municipios"]["3100104"]["semiarido"] is True))
    casos.append(("quem nunca esteve na delimitação não ganha o campo",
                  "semiarido" not in fundido["municipios"]["1500107"]))
    casos.append(("preserva campo de outra família no mesmo município",
                  fundir({"municipios": {"3100104": {"codigo_ibge": "3100104",
                                                     "mma_prioritario_desmatamento": True}}},
                         registros_de([("3100104", "x")], base)
                         )["municipios"]["3100104"]["mma_prioritario_desmatamento"] is True))
    casos.append(("anterior vazio não quebra", "municipios" in fundir({}, [])))
    casos.append(("chaves em ordem de código",
                  list(fundido["municipios"]) == sorted(fundido["municipios"])))

    planilha = io.BytesIO()
    try:
        import openpyxl
        livro = openpyxl.Workbook()
        aba = livro.active
        aba.append(["CD_MUN", "NM_MUN"])
        aba.append([2900207, "ABAÍRA"])
        aba.append([3100104, "Abadia dos Dourados"])
        aba.append([None, None])
        livro.save(planilha)
        lido = codigos_da_planilha(planilha.getvalue())
        casos.append(("lê a planilha e descarta cabeçalho e linha vazia", len(lido) == 2))
        casos.append(("código chega como texto de 7 dígitos", lido[0][0] == "2900207"))
        casos.append(("nome chega da planilha", lido[1][1] == "Abadia dos Dourados"))
    except ImportError:
        casos.append(("openpyxl disponível", False))

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
    corpo = buscar(FONTE, timeout=120, origem="coletar_semiarido_sudene")
    impressao = sha256(corpo)
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    if not precisa_reprocessar(anterior, impressao, hoje) and "--forcar" not in sys.argv:
        print(f"documento igual e conferido em "
              f"{anterior['fontes']['semiarido'].get('consultado_em')}: nada a reprocessar "
              f"(cadência de {DIAS_ENTRE_COLETAS} dias). `--forcar` ignora a espera.")
        return 0
    preservar_evidencia(corpo, FONTE, "xlsx", "coletar_semiarido_sudene")

    base = {}
    if MUNICIPIOS.exists():
        base = {str(m["ibge"]).zfill(7): {"uf": m.get("uf"), "nome": m.get("nome")}
                for m in json.loads(MUNICIPIOS.read_text(encoding="utf-8")) if m.get("ibge")}
    registros = registros_de(codigos_da_planilha(corpo), base)
    print(f"planilha: {len(registros)} municípios · evidência {impressao[:12]}")

    ruins = problemas(registros, base)
    if ruins:
        print("X VALIDAÇÃO — nada foi gravado:")
        for r in ruins:
            print("   -", r)
        return 1

    saida = fundir(anterior, registros)
    fontes = dict(saida.get("fontes") or {})
    fontes["semiarido"] = {"instrumento": INSTRUMENTO, "url": FONTE,
                           "consultado_em": hoje.isoformat(), "hash": impressao,
                           "total": TOTAL_SEMIARIDO}
    saida["fontes"] = fontes
    saida["_governanca"] = (
        "Enquadramento federal de risco por município: camada de CONTEXTO, PESO ZERO. Não pontua "
        "e não entra no índice. Constar de lista federal não é preparação; não constar não é falta "
        "de preparação. Cada família tem seu instrumento e sua fonte, declarados em `fontes`."
    )
    saida["atualizado_em"] = hoje.isoformat()
    gravar_em(SAIDA, saida)                                 # §229
    print(f"{SAIDA.relative_to(RAIZ)} gravado · {len(registros)} municípios no Semiárido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
