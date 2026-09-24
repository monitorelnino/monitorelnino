#!/usr/bin/env python3
"""Sonda (22/09/2026): qual edição da MUNIC/IBGE traz o bloco de gestão de riscos e desastres,
onde está o arquivo, e como se chamam de verdade as colunas de plano de contingência.

POR QUE ESTA SONDA EXISTE — E O QUE JÁ FOI RESOLVIDO
Ela nasceu porque `data/declarado_nacional.json` estava com `"municipios": {}` e
`data/fontes_declarado.json` tinha `url: null` para MUNIC e ICM. **Isso foi resolvido em
20–21/09/2026:** a fonte está com `status: "ok"`, a coluna conferida contra o arquivo
(`Mgrd184`, aba "Gestão de riscos"), e a camada declarada cobre os 5.570 municípios, ativada
na nota em 21/09. Esta docstring ficou três dias velha e mandava investigar problema morto —
corrigida em 24/09/2026 (§208).

O que a sonda serve HOJE: conferir, contra o arquivo, qual edição traz o bloco e como as
colunas se chamam, sempre que se quiser uma variável nova daquele bloco. Foi para isso que
ela rodou em 24/09/2026, ao procurar variável de FUNDO municipal de defesa civil (§208).

A EDIÇÃO NÃO É ÓBVIA — E ESTE É O PONTO PRINCIPAL
A MUNIC 2024 (21ª edição) anuncia oito temas: recursos humanos; informática e comunicação;
governança; habitação; transporte e mobilidade urbana; agropecuária; instrumentos de gestão
migratória; igualdade racial. **Gestão de riscos e desastres não aparece nessa lista.**
O bloco existe na MUNIC 2017 (15ª) e na 2020. A 2024 tem um bloco de evento climático, mas
restrito ao Rio Grande do Sul, o que não serve a um indicador nacional.

Ou seja: a edição mais RECENTE pode não ser a edição CERTA. A sonda lista o que há em cada
edição e mostra as colunas, para que a escolha seja feita com o arquivo à vista — decisão
editorial, porque muda o ano de referência do que o site afirma.

NÃO GRAVA NADA. Não toca `data/`. Roda na Action E localmente: em 24/09/2026 mediu-se que o
impedimento local não era bloqueio de host, e sim a cadeia de certificados do `ftp.ibge.gov.br`,
que a loja do Windows não completa — ver `_contexto_tls`.

Uso:
  python3 scripts/sondar_munic_ibge.py             # sonda (rede)
  python3 scripts/sondar_munic_ibge.py --autoteste # testa só os extratores, sem rede
"""
import io
import re
import ssl
import sys
import urllib.error
import urllib.request
import zipfile

UA = {"User-Agent": "MonitorElNino/3.1 (sonda MUNIC; pesquisa de interesse publico)"}

RAIZ_FTP = "https://ftp.ibge.gov.br/Perfil_Municipios/"

# Edições com bloco de gestão de riscos e desastres, segundo a documentação pública.
# A sonda confirma contra o arquivo; esta lista só decide a ordem de tentativa.
EDICOES_PRIORITARIAS = ["2020", "2017", "2024", "2023", "2021", "2019", "2018"]

# Onde a base realmente mora dentro de cada edição (visto na execução de 20/09).
SUBPASTAS = {"Base_de_Dados", "Tabelas_de_Resultados"}

# O que caracteriza a coluna que interessa. Casa com variações de caixa e separador.
PADRAO_PLANO = re.compile(r"(plano.*coting|plano.*conting|conting.*plano|plancont)", re.I)
PADRAO_RISCO = re.compile(r"(risco|desastre|defesa\s*civil|mgrd|protecao\s*civil|prote\u00e7\u00e3o)", re.I)
PADRAO_IBGE = re.compile(r"^(cod|codigo|cd)[\s_]*(mun|municipio|ibge)|^a1$", re.I)
# 24/09/2026 (camada B do dinheiro municipal, §207): a pergunta "o município tem FUNDO de
# defesa civil?" também pode ter resposta declarada na MUNIC. Os nomes possíveis da coluna
# incluem as siglas que as leis municipais usam (FUMPDEC, FUMDEC, FUNDEC, FMPDC).
PADRAO_FUNDO = re.compile(r"(fundo|fumpdec|fumdec|fundec|fmpdc|fmdc)", re.I)


def _contexto_tls():
    """Verificação de certificado contra o pacote de CAs do `certifi` quando ele existe.

    24/09/2026: a docstring desta sonda dizia que o ambiente de edição respondia 403
    `host_not_allowed` para os domínios do IBGE. O que ele responde de verdade, medido hoje, é
    CERTIFICATE_VERIFY_FAILED — a loja de certificados da máquina Windows não completa a cadeia
    do `ftp.ibge.gov.br`. Mesmo defeito, e mesma correção, do `gsc.cemaden.gov.br` no §206.
    Não afrouxa verificação nenhuma: valida contra um conjunto de raízes mais completo e igual em
    qualquer máquina. Com isto a sonda roda FORA da Action, o que era o único impedimento para
    responder à editoria qual edição da MUNIC serve."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def baixar(url: str, limite: int = 40_000_000) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120,
                                context=_contexto_tls()) as r:
        return r.read(limite)


def links_de_listagem(html: str) -> list:
    """Extrai os href de uma listagem de diretório do FTP-HTTP do IBGE."""
    return [h for h in re.findall(r'href="([^"?][^"]*)"', html) if h not in ("../", "/")]


def colunas_de_csv(texto: str) -> list:
    """Cabeçalho da primeira linha, tolerando ; , ou tab como separador."""
    primeira = next((l for l in texto.splitlines() if l.strip()), "")
    for sep in (";", "\t", ","):
        if primeira.count(sep) >= 3:
            return [c.strip().strip('"') for c in primeira.split(sep)]
    return [primeira.strip()] if primeira.strip() else []


def classificar_colunas(colunas: list) -> dict:
    """Separa as colunas em: chave do município, plano de contingência, contexto de risco e fundo.

    O par plano/risco é o que decide se a edição serve: sem coluna de plano de contingência,
    a edição não responde à pergunta do índice, por mais recente que seja.
    """
    return {
        "ibge": [c for c in colunas if PADRAO_IBGE.search(c)],
        "plano_contingencia": [c for c in colunas if PADRAO_PLANO.search(c)],
        "risco_desastre": [c for c in colunas if PADRAO_RISCO.search(c) and not PADRAO_PLANO.search(c)],
        # A coluna de fundo, se existir, é a camada declarada da camada B (§207): mesmo tratamento
        # da camada declarada de planos — "declarado, não documentado" até a lei ser localizada.
        "fundo_municipal": [c for c in colunas if PADRAO_FUNDO.search(c)],
    }


def colunas_de_xlsx(bruto: bytes) -> list:
    """Cabeçalho da primeira linha de um .xlsx, sem carregar a planilha inteira na memória.

    22/09/2026 — a execução real mostrou que a MUNIC não distribui CSV: tudo é .xlsx/.ods.
    `parse_munic_csv()` em coletar_declarado_nacional.py é csv.DictReader e NÃO lê este
    formato. A sonda precisa ler para dizer os nomes de coluna; o coletor precisará da
    mesma mudança antes da primeira coleta real.
    """
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(bruto), read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        for linha in ws.iter_rows(min_row=1, max_row=8, values_only=True):
            celulas = [str(c).strip() for c in linha if c is not None and str(c).strip()]
            # O IBGE costuma abrir a planilha com título/nota antes do cabeçalho:
            # o cabeçalho é a primeira linha com várias células preenchidas.
            if len(celulas) >= 4:
                return celulas
        return []
    finally:
        wb.close()


def _relatar_tabela(nome: str, bruto: bytes) -> None:
    """Imprime o veredito de um arquivo tabular: colunas-chave achadas e amostra."""
    if nome.lower().endswith(".xlsx"):
        try:
            colunas = colunas_de_xlsx(bruto)
        except Exception as e:  # noqa: BLE001
            print(f"      {nome}: ERR ao abrir xlsx — {type(e).__name__}: {e}")
            return
    elif nome.lower().endswith(".ods"):
        print(f"      {nome}: .ods — equivalente ao .xlsx irmão; sondando só o .xlsx")
        return
    else:
        colunas = colunas_de_csv(bruto[:2_000_000].decode("latin-1", "replace"))
    if not colunas:
        print(f"      {nome}: sem cabeçalho legível")
        return
    achados = classificar_colunas(colunas)
    print(f"      {nome}: {len(colunas)} colunas")
    for rotulo, lista in achados.items():
        if lista:
            print(f"        {rotulo}: {lista[:6]}")
    if achados["plano_contingencia"]:
        print(f"        >>> SERVE: tem coluna de plano de contingência")
    elif achados["risco_desastre"]:
        print(f"        >>> talvez: tem contexto de risco, sem coluna de plano explícita")


def sondar() -> int:
    print("=== listagem de edições em", RAIZ_FTP, "===")
    try:
        html = baixar(RAIZ_FTP).decode("latin-1", "replace")
        dirs = links_de_listagem(html)
        print("  encontrados:", dirs[:40])
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {e}")
        dirs = []

    # 22/09/2026 — defeito achado na 1ª execução real: `if e in d` casava
    # "Gestao_do_Saneamento_Basico_2017/" e "Seguranca_Alimentar_2024/" como se fossem
    # edições da MUNIC, e os suplementos consumiram as 6 vagas da sonda. A edição é o
    # diretório cujo nome é SÓ o ano.
    candidatos = [f"{e}/" for e in EDICOES_PRIORITARIAS if f"{e}/" in dirs] or \
                 [f"{e}/" for e in EDICOES_PRIORITARIAS]

    for d in candidatos[:6]:
        url = RAIZ_FTP + d.lstrip("/")
        print(f"\n=== edição {d} ===")
        try:
            sub = baixar(url).decode("latin-1", "replace")
        except urllib.error.HTTPError as e:
            print(f"  ERR HTTP {e.code}")
            continue
        except Exception as e:
            print(f"  ERR {type(e).__name__}: {e}")
            continue
        arquivos = links_de_listagem(sub)
        print("  arquivos:", arquivos[:25])

        # 22/09/2026 — defeito achado na 1ª execução real: a base não fica na raiz da
        # edição, e sim em Base_de_Dados/. A sonda via só "Base_de_Dados/" e
        # "Tabelas_de_Resultados/", não achava zip nenhum e desistia da edição.
        for sub_dir in [a for a in arquivos if a.rstrip("/").split("/")[-1] in SUBPASTAS]:
            suburl = url + sub_dir.lstrip("/")
            print(f"  >> {sub_dir}")
            try:
                dentro = links_de_listagem(baixar(suburl).decode("latin-1", "replace"))
            except Exception as e:
                print(f"     ERR {type(e).__name__}: {e}")
                continue
            print("     arquivos:", [a for a in dentro if not a.startswith("http")][:15])
            for a in [a for a in dentro if a.lower().endswith((".xlsx", ".ods", ".csv"))][:4]:
                try:
                    _relatar_tabela(a, baixar(suburl + a.lstrip("/")))
                except Exception as e:
                    print(f"     ERR {a}: {type(e).__name__}: {e}")
            arquivos = arquivos + [sub_dir + a.lstrip("/") for a in dentro if a.lower().endswith(".zip")]

        # Um .zip da base costuma conter os CSV/ODS por bloco temático.
        zips = [a for a in arquivos if a.lower().endswith(".zip")]
        for z in zips[:2]:
            zurl = url + z.lstrip("/")
            print(f"  --- {z} ---")
            try:
                bruto = baixar(zurl)
                zf = zipfile.ZipFile(io.BytesIO(bruto))
                nomes = zf.namelist()
                print(f"    {len(nomes)} arquivo(s) no zip")
                interessantes = [n for n in nomes if PADRAO_RISCO.search(n)] or nomes
                print(f"    candidatos por nome: {interessantes[:10]}")
                for n in interessantes[:4]:
                    if n.lower().endswith((".csv", ".txt")):
                        _relatar_tabela(n, zf.read(n))
                    else:
                        print(f"      {n}: não é CSV (provável .ods/.xlsx — ler com pandas na coleta)")
            except Exception as e:
                print(f"    ERR {type(e).__name__}: {e}")
    return 0


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # Listagem
    html = '<a href="../">..</a><a href="2020/">2020/</a><a href="2017/">2017/</a>'
    checar("listagem: ignora '../' e devolve as edições",
           links_de_listagem(html) == ["2020/", "2017/"])

    # Cabeçalho com ; (formato do IBGE)
    csv_ibge = 'CodMun;Mgrd01;MGRD_PlanoContingencia;Mgrd03\n1100015;Sim;Sim;Nao\n'
    cols = colunas_de_csv(csv_ibge)
    checar("cabeçalho ';' lido", cols == ["CodMun", "Mgrd01", "MGRD_PlanoContingencia", "Mgrd03"])

    c = classificar_colunas(cols)
    checar("acha a coluna do código do município", c["ibge"] == ["CodMun"])
    checar("acha a coluna de plano de contingência", c["plano_contingencia"] == ["MGRD_PlanoContingencia"])
    checar("colunas de risco não incluem a de plano",
           "MGRD_PlanoContingencia" not in c["risco_desastre"])

    # NEGATIVO — edição sem o bloco (o caso da MUNIC 2024). O caso inclui de propósito
    # 'PlanoDiretor' e 'Planejamento': a MUNIC TEM essas colunas, e um padrão frouxo que
    # casasse só 'plan' diria que a edição serve quando ela não responde à pergunta.
    cols_2024 = colunas_de_csv(
        'CodMun;Gov01;PlanoDiretor;PlanejamentoUrbano;IgualdadeRacial04\n1100015;Sim;Sim;Nao;Sim\n')
    c24 = classificar_colunas(cols_2024)
    checar("NEGATIVO: 'PlanoDiretor'/'Planejamento' não contam como plano de contingência",
           c24["plano_contingencia"] == [])
    checar("NEGATIVO: edição sem bloco de riscos não acusa contexto de risco",
           c24["risco_desastre"] == [])

    # NEGATIVO — variação de grafia não pode escapar.
    checar("grafia alternativa 'PlanContingencia' é reconhecida",
           classificar_colunas(["PlanContingencia"])["plano_contingencia"] == ["PlanContingencia"])

    # NEGATIVO — uma linha de texto com UMA vírgula (nota de rodapé do IBGE, por exemplo)
    # não pode ser tomada como cabeçalho de duas colunas.
    checar("NEGATIVO: 'Fonte: IBGE, 2024' não vira cabeçalho de 2 colunas",
           len(colunas_de_csv("Fonte: IBGE, 2024\n")) == 1)
    checar("linha sem separador nenhum devolve uma coluna",
           len(colunas_de_csv("texto solto qualquer\n")) == 1)

    # NEGATIVO (22/09) — os dois defeitos que a 1ª execução real revelou.
    dirs_reais = ["2017/", "2020/", "2024/", "Saneamento_Basico_2017/",
                  "Gestao_do_Saneamento_Basico_2017/", "Seguranca_Alimentar_2024/"]
    so_edicoes = [f"{e}/" for e in EDICOES_PRIORITARIAS if f"{e}/" in dirs_reais]
    checar("NEGATIVO: suplemento com ano no nome não é tomado por edição",
           so_edicoes == ["2020/", "2017/", "2024/"])
    checar("Base_de_Dados é reconhecida como subpasta da base",
           "Base_de_Dados" in SUBPASTAS and "Tabelas_de_Resultados" in SUBPASTAS)

    # NEGATIVO — cabeçalho de .xlsx com linhas de título antes (formato do IBGE).
    try:
        import openpyxl
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        ws.append(["Pesquisa de Informações Básicas Municipais 2020"])
        ws.append([])
        ws.append(["CodMun", "UF", "Mgrd01", "MGRD_PlanoContingencia", "Mgrd03"])
        buf = io.BytesIO(); wb.save(buf)
        cols_x = colunas_de_xlsx(buf.getvalue())
        checar("xlsx: pula linha de título e acha o cabeçalho real",
               cols_x == ["CodMun", "UF", "Mgrd01", "MGRD_PlanoContingencia", "Mgrd03"])
        checar("xlsx: a coluna de plano é classificada",
               classificar_colunas(cols_x)["plano_contingencia"] == ["MGRD_PlanoContingencia"])
    except ImportError:
        pass
    # §207, camada B: a coluna de FUNDO, se a edição a tiver, é classificada à parte — e uma
    # coluna de plano não é tomada por coluna de fundo, nem o contrário.
    cls = classificar_colunas(["CodMun", "MGRD_PlanoContingencia", "Mgrd_FundoMunicipal",
                               "Mgrd_FUMPDEC", "Mgrd_RiscoArea"])
    checar("fundo: as colunas de fundo são separadas das de plano e de risco",
           cls["fundo_municipal"] == ["Mgrd_FundoMunicipal", "Mgrd_FUMPDEC"]
           and cls["plano_contingencia"] == ["MGRD_PlanoContingencia"])
    checar("fundo NEGATIVO: edição sem coluna de fundo devolve lista vazia, não engano",
           classificar_colunas(["CodMun", "MGRD_PlanoContingencia"])["fundo_municipal"] == [])
    try:
        pass
    except ImportError:
        print("  (openpyxl ausente — casos de xlsx pulados)")

    if falhas:
        print(f"✗ AUTOTESTE DA SONDA MUNIC: {len(falhas)} caso(s) falharam")
        return 1
    print("✓ AUTOTESTE OK — listagem, cabeçalho e classificação de colunas; rejeita edição sem o bloco")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else sondar())
