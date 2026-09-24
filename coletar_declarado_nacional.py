#!/usr/bin/env python3
"""
coletar_declarado_nacional.py
=============================
Camada DECLARADA nacional (doc de redesenho §3.9, decisão C5): o que o município
DECLARA ter — MUNIC/IBGE (bloco "Gestão de riscos e de desastres": possui plano
de contingência?) e ICM/SEDEC (faixa A–D; variável 8: plano de contingência).
Produz `data/declarado_nacional.json`, por município: `munic_plano_contingencia`
(sim/não/NA + ano da edição), `icm_var8_plano_contingencia` (ICM não fornece nome
descritivo de coluna, só numeração 1–20; `icm_faixa` — A/D por município — não é
extraído por este coletor, ver nota em fontes_declarado.json).

GOVERNANÇA: esta camada foi construída em 02/09/2026 e ficou só simulada
(`recalcular_mare.py --simular-declarado-nacional`, removido do código em
21/09/2026) até essa data, quando foi ATIVADA NA NOTA PÚBLICA por decisão
editorial explícita — antecipada da vigência original de 26/10/2026. O desconto
de 50% já existente (declarar ≠ publicar, §3.4 da transferência) continua
vigente; a diferença é que agora `recalcular_mare.py` (sem flag nenhuma, todo
`--write`/`--check`) já inclui esta camada sempre, em toda atualização — não é
mais um anexo separado.

FONTE MUNIC — verificada por download real em 20/09/2026 (§128), não por
suposição (os nomes anteriores em `fontes_declarado.json`, "MGRD_PlanoContingencia"
e parser CSV, nunca foram conferidos contra arquivo e estavam errados em dois
pontos: (1) a MUNIC não distribui CSV — só .xlsx/.ods; (2) o nome real da
coluna do plano é `Mgrd184`, não `MGRD_PlanoContingencia`).

A MUNIC roda módulos temáticos ROTATIVOS: cada edição cobre um conjunto
diferente de temas, e "Gestão de riscos e de desastres" não está em toda
edição. Confirmado por leitura direta do dicionário de variáveis (aba
"Dicionário" de cada arquivo) e por inspeção das abas de cada ano:
  - 2017 e 2020: têm a aba "Gestão de risco"/"Gestão de riscos" com o bloco.
  - 2019, 2021, 2023, 2024: NÃO têm esse módulo (temas diferentes cada ano;
    colunas com prefixo parecido nessas edições — MREG, Mmig — são de outros
    temas, "Recursos para gestão" e "Gestão migratória", e não devem ser
    confundidas com risco por semelhança de prefixo).
Portanto a edição mais recente com o bloco é 2020, não por escolha editorial,
mas porque é a única disponível nesse recorte temporal.

Dentro do bloco (aba "Gestão de riscos", dicionário seção 6), dois campos são
candidatos a "plano de contingência" e medem coisas diferentes:
  - `Mgrd184` — "Plano de Contingência", dentro de 6.6 Gerenciamento de riscos
    (instrumento geral, ligado a enchentes/inundações/deslizamentos).
  - `Mgrd05` — "O município possui Plano de Contingência e/ou Preservação para
    a seca", dentro de 6.1 Seca.
Usamos `Mgrd184` como padrão: é o instrumento geral de gestão de riscos, no
mesmo nível de abstração que o "plano de contingência" já mede em outras
camadas do MARÉ (S2iD, diários municipais). `Mgrd05` (seca) fica registrado
em paralelo (`munic_plano_contingencia_seca`) para uso futuro, sem entrar na
simulação de nota — decisão sobre usá-lo pertence à editoria, dado que seca é
o padrão de impacto mais associado ao El Niño no Nordeste.

Fontes (§15, "a verificar"): formato de download do ICM segue sem confirmação.
`data/fontes_declarado.json` guarda url e status; sem confirmação → lacuna
declarada. O parser MUNIC (xlsx) é provado por fixture; a primeira coleta real
roda contra o arquivo publicado pelo IBGE.

USO
  python coletar_declarado_nacional.py --autoteste
  python coletar_declarado_nacional.py           # coleta (rede)
"""
import io, sys
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, referencia_ibge,
                            ler, gravar, rodar_autoteste)

FONTES_PADRAO = {
    "_governanca": "Fontes da camada declarada nacional (v2.2.4, §3.9). Sem url confirmada → lacuna.",
    "munic": {
        "nome": "MUNIC/IBGE 2020 — bloco Gestão de riscos e desastres",
        "url": "https://ftp.ibge.gov.br/Perfil_Municipios/2020/Base_de_Dados/Base_MUNIC_2020.xlsx",
        "edicao": 2020,
        "status": "a_verificar",
        "aba": "Gestão de riscos",
        "coluna_ibge": "CodMun",
        "coluna_plano": "Mgrd184",
        "coluna_plano_seca": "Mgrd05",
        "_nota": "2017 e 2020 são as únicas edições recentes com este bloco (módulos rotativos "
                 "da MUNIC); 2020 é a mais recente. Verificado por download real em 20/09/2026.",
    },
    "icm": {
        "nome": "ICM/SEDEC — Indicador de Capacidade Municipal, base completa",
        "url": "https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/base_completa_icm_082026.xlsx",
        "edicao": "2026 (base publicada 28/04/2026, correção de falhas)",
        "status": "a_verificar",
        "aba": "Planilha1",
        "coluna_ibge": "Código IBGE",
        "coluna_var8": "8",
        "coluna_var11_dotacao": "11",
        "_nota": "Página oficial: gov.br/mdr/.../icm — variável 8 confirmada como 'Plano de "
                 "Contingência' na descrição das 20 variáveis do indicador. Colunas 1–20 vêm "
                 "numeradas, não nomeadas (o próprio ICM não dá nome descritivo às variáveis). "
                 "Verificado por download real em 21/09/2026.",
    },
}
SIM = {"sim", "s", "1", "true", "possui"}
NAO = {"não", "nao", "n", "0", "false", "não possui", "nao possui"}


def normalizar_sim_nao(v) -> str:
    t = str(v or "").strip().lower()
    return "sim" if t in SIM else "nao" if t in NAO else "NA"


def parse_munic_xlsx(bruto: bytes, aba: str, col_ibge: str, col_plano: str,
                      col_plano_seca: str, edicao) -> dict:
    """{ibge7: {munic_plano_contingencia, munic_plano_contingencia_seca, munic_edicao}}.

    A MUNIC distribui .xlsx, não CSV (confirmado por download real em 20/09/2026,
    §128) — leitura via openpyxl, aba nomeada (não a primeira do arquivo: a aba de
    risco costuma vir depois de "Recursos humanos" e outras, então pegar por nome
    evita repetir o defeito da sonda §126, que só olhava as 3 primeiras abas).
    """
    import openpyxl
    out = {}
    wb = openpyxl.load_workbook(io.BytesIO(bruto), read_only=True, data_only=True)
    try:
        if aba not in wb.sheetnames:
            return out
        ws = wb[aba]
        linhas = ws.iter_rows(values_only=True)
        cabecalho = list(next(linhas))
        try:
            idx_ibge = cabecalho.index(col_ibge)
        except ValueError:
            return out
        idx_plano = cabecalho.index(col_plano) if col_plano in cabecalho else None
        idx_seca = cabecalho.index(col_plano_seca) if col_plano_seca in cabecalho else None
        for linha in linhas:
            cod = str(linha[idx_ibge] or "").strip()
            if len(cod) != 7 or not cod.isdigit():
                continue
            d = {"munic_edicao": edicao}
            if idx_plano is not None:
                d["munic_plano_contingencia"] = normalizar_sim_nao(linha[idx_plano])
            if idx_seca is not None:
                d["munic_plano_contingencia_seca"] = normalizar_sim_nao(linha[idx_seca])
            out[cod] = d
    finally:
        wb.close()
    return out


def normalizar_binario_icm(v) -> str:
    """As 20 variáveis do ICM vêm como 0/1 (inteiro, não texto — confirmado por download real
    em 21/09/2026). normalizar_sim_nao() não serve aqui: ela faz `str(v or "")`, e `0 or ""`
    vira string vazia em Python (0 é falsy) — inteiro 0 cairia em NA por engano, não em "nao"."""
    if v is None:
        return "NA"
    if isinstance(v, (int, float)):
        return "sim" if v == 1 else "nao" if v == 0 else "NA"
    return normalizar_sim_nao(v)


def parse_icm_xlsx(bruto: bytes, aba: str, col_ibge: str, col_var: str, edicao,
                   col_dotacao: str = "") -> dict:
    """{ibge7: {icm_var8_plano_contingencia, icm_var11_dotacao_loa, icm_edicao}}.

    24/09/2026 (§208, camada B do dinheiro municipal): `col_dotacao` lê a variável **11** do
    ICM, "Dotação orçamentária (LOA) para proteção e Defesa Civil". Ela entrou no lugar da
    variável de FUNDO da MUNIC 2020 porque é melhor em três sentidos, medidos: base de **2026**
    contra 2020; **binária e sem vazio** nos 5.570, contra cinco valores na MUNIC (`Sim` 968,
    `Não` 3.265, `-` 1.229, `Recusa` 90, `Não informou` 18 — 24 % do país sem resposta
    utilizável); e é da própria SEDEC. Confirmação cruzada: os 968 que disseram "sim" à MUNIC em
    2020 têm **todos** 1 na variável 11 do ICM 2026 — nenhuma discordância nesse sentido, o que
    mostra que as duas perguntam a mesma coisa.

    PESO ZERO, e a garantia é estrutural: `recalcular_mare._declarado_nacional_uf()` lê apenas
    `munic_plano_contingencia` e `icm_var8_plano_contingencia`, **por nome**. Um campo novo não
    entra por ficar no mesmo registro. `verificar_financiamento.py` tem a trava que prova isso.

    Esquema real (base_completa_icm,
    download de 21/09/2026): linha 1 é título da planilha; linha 2 é o cabeçalho real —
    'Nº', 'Código IBGE', 'UF', 'Município', 'Região', depois as 20 variáveis do ICM como
    cabeçalho LITERAL '1' a '20' (string), depois 'Soma', 'Municípios Prioritários'. A
    variável 8 é "Plano de Contingência" (confirmado na página oficial do MDR/Sedec,
    gov.br/mdr/.../icm — não suposto). `col_var` aqui é o cabeçalho '8', não um nome
    descritivo — o próprio ICM não nomeia as colunas, só numera."""
    import openpyxl
    out = {}
    wb = openpyxl.load_workbook(io.BytesIO(bruto), read_only=True, data_only=True)
    try:
        if aba not in wb.sheetnames:
            return out
        ws = wb[aba]
        linhas = ws.iter_rows(values_only=True)
        next(linhas, None)  # linha 1: título da planilha, não é cabeçalho
        cabecalho = list(next(linhas, []))
        try:
            idx_ibge = cabecalho.index(col_ibge)
        except ValueError:
            return out
        def indice_de(rotulo):
            """A coluna do ICM é o cabeçalho LITERAL '8' ou '11', não um nome descritivo."""
            if not str(rotulo).strip():
                return None
            for i, c in enumerate(cabecalho):
                if str(c).strip() == str(rotulo).strip():
                    return i
            return None

        idx_var = indice_de(col_var)
        idx_dot = indice_de(col_dotacao)
        for linha in linhas:
            if idx_ibge >= len(linha):
                continue
            cod = str(linha[idx_ibge] or "").strip().zfill(7)
            if len(cod) != 7 or not cod.isdigit():
                continue
            d = {"icm_edicao": edicao}
            if idx_var is not None and idx_var < len(linha):
                d["icm_var8_plano_contingencia"] = normalizar_binario_icm(linha[idx_var])
            if idx_dot is not None and idx_dot < len(linha):
                d["icm_var11_dotacao_loa"] = normalizar_binario_icm(linha[idx_dot])
            out[cod] = d
    finally:
        wb.close()
    return out


def marcar_fato_municipal_em_memoria(livro: dict, ibge, campo: str, valor) -> None:
    """Mesma lógica de `coletores_base.marcar_fato_municipal`, mas contra um `livro` já
    carregado em memória — sem ler/gravar o arquivo a cada chamada (ver nota em coletar()).
    Mantida em sincronia deliberada com a função original; se ela mudar, esta acompanha."""
    m = livro["municipios"].setdefault(str(ibge).zfill(7), {"nivel_verificacao": "nao_verificado",
                                                             "ultima_verificacao": None, "fontes": []})
    m[campo] = valor


def coletar() -> int:
    cfg = ler("fontes_declarado.json", None) or FONTES_PADRAO
    por_cod, _ = referencia_ibge()
    reg = ler("declarado_nacional.json", {"_governanca": "Camada declarada nacional (§3.9, C5): construída e "
                                          "SIMULADA desde 02/09/2026; entra na nota só em 26/10/2026. "
                                          "Declarar ≠ publicar: desconto de 50% quando ativada.",
                                          "vigencia_na_nota": "2026-10-26", "municipios": {}})
    # 21/09/2026 (achado real, rodando pela primeira vez contra a rede): marcar_fato_municipal()
    # faz UMA leitura + escrita completa de fontes_consultadas.json (368 mil linhas) POR
    # CHAMADA — correto para coletar_doe.py/coletar_s2id.py (dezenas de municípios com decreto),
    # mas aqui são até 5.570 chamadas na mesma rodada (todos os municípios da base MUNIC/ICM).
    # Isso e a falta de escrita atômica (corrigida em coletores_base.py na mesma sessão) juntas
    # corromperam o arquivo quando a rodada foi interrompida por timeout. Corrigido: uma leitura
    # antes do loop, atualização em memória (mesma lógica de marcar_fato_municipal, sem chamar a
    # função por item), uma escrita no final — mesmo resultado, 5.570× menos I/O.
    livro_fatos = ler("fontes_consultadas.json", {"_governanca": "Livro de fontes consultadas por "
                      "município (v2.2.4).", "municipios": {}})
    for chave in ("munic", "icm"):
        f = cfg[chave]
        if not f.get("url"):
            registrar_lacuna(f["nome"], "url/edição não confirmada (a_verificar)", canal="DOU", camada=1)
            continue
        try:
            bruto = buscar(f["url"], timeout=120)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f["nome"], f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[f["url"]])
            f["status"] = f"erro: {type(e).__name__}"; continue
        ext = "xlsx"
        h = preservar_evidencia(bruto, f["url"], ext, "coletar_declarado_nacional")
        if chave == "munic":
            dados = parse_munic_xlsx(bruto, f["aba"], f["coluna_ibge"], f["coluna_plano"],
                                     f.get("coluna_plano_seca", ""), f.get("edicao"))
            campo, fato = "munic_plano_contingencia", "plano_declarado_munic"
        else:
            dados = parse_icm_xlsx(bruto, f["aba"], f["coluna_ibge"], f["coluna_var8"], f.get("edicao"),
                                   f.get("coluna_var11_dotacao", ""))
            campo, fato = "icm_var8_plano_contingencia", "plano_declarado_icm"
        casados = 0
        for cod, d in dados.items():
            if cod in por_cod:
                reg["municipios"].setdefault(cod, {}).update(d); casados += 1
                if d.get(campo) in ("sim", "nao"):
                    marcar_fato_municipal_em_memoria(livro_fatos, cod, fato, d[campo] == "sim")
        marcar_fonte_consultada([c for c in dados if c in por_cod], f["nome"], "nacional",
                                resultado=f"{casados} municípios na base")
        log_busca("DOU", 1, [f["url"]], "registro", nivel="nacional", n_resultados=casados,
                  resultados=f"{f['nome']}: {casados} municípios casados com IBGE", hash_evidencia=h)
        f["status"] = "ok"; f["ultima_coleta"] = date.today().isoformat()
        print(f"{f['nome']}: {casados} municípios")
    gravar("fontes_consultadas.json", livro_fatos)
    gravar("fontes_declarado.json", cfg); gravar("declarado_nacional.json", reg)
    return 0


def _xlsx_fixture() -> bytes:
    """Monta um .xlsx mínimo em memória, mesmo layout da MUNIC real (aba nomeada,
    cabeçalho na primeira linha), para o autoteste não depender de rede."""
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Gestão de riscos")
    ws.append(["CodMun", "UF", "Mgrd01", "Mgrd05", "Mgrd184"])
    ws.append([4202404, "SC", "Sim", "Não", "Sim"])
    ws.append([2927408, "BA", "Não", "Sim", "Não"])
    ws.append([99, "XX", "Sim", "Sim", "Sim"])  # código inválido (não IBGE de 7 dígitos) — deve ser ignorado
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


def _xlsx_fixture_icm() -> bytes:
    """Mesmo layout real do ICM (base_completa_icm, download de 21/09/2026): linha 1 é
    título da planilha, linha 2 é o cabeçalho real, variáveis numeradas 1–20 como inteiro
    0/1 (não texto — é por isso que normalizar_binario_icm existe, não normalizar_sim_nao)."""
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Planilha1")
    ws.append(["Base Completa do Indicador de Capacidade Municipal - ICM"])
    ws.append(["Nº", "Código IBGE", "UF", "Município", "Região"] + [str(i) for i in range(1, 21)]
             + ["Soma", "Municípios Prioritários"])
    linha1 = [1, 4202404, "SC", "Cidade Um", "3 - Sul"] + [0] * 7 + [1] + [0] * 12 + [8, "Sim"]
    linha2 = [2, 2927408, "BA", "Cidade Dois", "2 - Nordeste"] + [1] * 7 + [0] + [1] * 12 + [19, "Não"]
    ws.append(linha1); ws.append(linha2)
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


def autoteste() -> int:
    def t1():
        d = parse_munic_xlsx(_xlsx_fixture(), "Gestão de riscos", "CodMun", "Mgrd184", "Mgrd05", 2020)
        return d == {
            "4202404": {"munic_edicao": 2020, "munic_plano_contingencia": "sim",
                        "munic_plano_contingencia_seca": "nao"},
            "2927408": {"munic_edicao": 2020, "munic_plano_contingencia": "nao",
                        "munic_plano_contingencia_seca": "sim"},
        }
    def t2():  # var8 da linha 1 é o 8º "0"/valor da sequência — colocado como 1 (sim);
        # linha 2 tem 0 (não) na mesma posição — testa especificamente o caso 0 int (falsy).
        d = parse_icm_xlsx(_xlsx_fixture_icm(), "Planilha1", "Código IBGE", "8", "2026")
        return (len(d) == 2 and d["4202404"]["icm_var8_plano_contingencia"] == "sim"
                and d["2927408"]["icm_var8_plano_contingencia"] == "nao")
    def t2b():
        """§208: a variável 11 (dotação na LOA) é lida à parte da 8, e o cruzamento da fixture
        prova que as colunas não se confundem — na linha 1 a 8 é 1 e a 11 é 0; na linha 2, o
        contrário. Se o parser trocasse os índices, este teste cairia."""
        d = parse_icm_xlsx(_xlsx_fixture_icm(), "Planilha1", "Código IBGE", "8", "2026", "11")
        return (d["4202404"]["icm_var8_plano_contingencia"] == "sim"
                and d["4202404"]["icm_var11_dotacao_loa"] == "nao"
                and d["2927408"]["icm_var8_plano_contingencia"] == "nao"
                and d["2927408"]["icm_var11_dotacao_loa"] == "sim")

    def t2c():
        """Sem a coluna pedida, o campo NÃO aparece — e não aparece como 'nao', que seria afirmar
        ausência de dotação em cima de ausência de coleta."""
        d = parse_icm_xlsx(_xlsx_fixture_icm(), "Planilha1", "Código IBGE", "8", "2026")
        sem_pedir = all("icm_var11_dotacao_loa" not in v for v in d.values())
        d2 = parse_icm_xlsx(_xlsx_fixture_icm(), "Planilha1", "Código IBGE", "8", "2026", "99")
        return sem_pedir and all("icm_var11_dotacao_loa" not in v for v in d2.values())

    def t3():
        return (normalizar_sim_nao("talvez") == "NA" and normalizar_sim_nao(None) == "NA"
                and normalizar_binario_icm(0) == "nao" and normalizar_binario_icm(1) == "sim"
                and normalizar_binario_icm(None) == "NA")  # 0 é falsy em Python — achado real 21/09
    def t4():  # negativo: aba errada → vazio, nunca exceção
        return parse_munic_xlsx(_xlsx_fixture(), "Aba Inexistente", "CodMun", "Mgrd184", "Mgrd05", 2020) == {}
    def t5():  # negativo: coluna do plano ausente da aba → ainda casa por IBGE, sem o campo do plano
        import openpyxl
        wb = openpyxl.Workbook(); wb.remove(wb.active)
        ws = wb.create_sheet("Gestão de riscos")
        ws.append(["CodMun", "OutraColuna"])
        ws.append([4202404, "x"])
        buf = io.BytesIO(); wb.save(buf)
        d = parse_munic_xlsx(buf.getvalue(), "Gestão de riscos", "CodMun", "Mgrd184", "Mgrd05", 2020)
        return d == {"4202404": {"munic_edicao": 2020}}
    def t5b():  # negativo: aba errada no ICM → vazio, nunca exceção
        return parse_icm_xlsx(_xlsx_fixture_icm(), "Aba Inexistente", "Código IBGE", "8", "2026") == {}
    def t5c():  # negativo: linha 1 (título) nunca é lida como cabeçalho — se fosse, "Código
        # IBGE" não bateria e tudo viraria vazio; prova que o pulo da linha 1 está funcionando
        return len(parse_icm_xlsx(_xlsx_fixture_icm(), "Planilha1", "Código IBGE", "8", "2026")) == 2
    def t6():  # 21/09/2026: marcar_fato_municipal_em_memoria replica a lógica da função
        # original (mesmos defaults, cria o registro se não existir) sem I/O — testado contra
        # um livro em memória, dois municípios, um já existente e um novo.
        livro = {"municipios": {"1100015": {"nivel_verificacao": "estadual", "ultima_verificacao": "2026-09-01",
                                            "fontes": ["x"]}}}
        marcar_fato_municipal_em_memoria(livro, "1100015", "plano_declarado_munic", True)
        marcar_fato_municipal_em_memoria(livro, 3106200, "plano_declarado_munic", False)  # int, não string
        existente_preservado = (livro["municipios"]["1100015"]["nivel_verificacao"] == "estadual"
                                and livro["municipios"]["1100015"]["plano_declarado_munic"] is True)
        novo_criado = (livro["municipios"]["3106200"]["nivel_verificacao"] == "nao_verificado"
                      and livro["municipios"]["3106200"]["plano_declarado_munic"] is False)
        return existente_preservado and novo_criado
    return rodar_autoteste({"parser MUNIC (xlsx, aba nomeada)": t1, "parser ICM (xlsx, var8 inteiro 0/1)": t2,
                            "§208 ICM var11 (dotação na LOA) lida à parte da var8, sem trocar coluna": t2b,
                            "§208 negativo: coluna de dotação não pedida ou ausente não vira 'nao'": t2c,
                            "valores fora do vocabulário viram NA; binário ICM trata 0 int corretamente": t3,
                            "negativo: aba inexistente (MUNIC)": t4,
                            "negativo: coluna do plano ausente (MUNIC)": t5,
                            "negativo: aba inexistente (ICM)": t5b,
                            "linha 1 (título) do ICM nunca é lida como cabeçalho": t5c,
                            "marcar_fato_municipal_em_memoria: preserva registro existente e cria novo": t6})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
