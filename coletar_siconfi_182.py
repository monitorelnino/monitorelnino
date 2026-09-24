#!/usr/bin/env python3
"""
coletar_siconfi_182.py — despesa municipal em defesa civil, por habitante (camada A)
====================================================================================
ESTATUTO: peso ZERO no MARÉ e no MARÉ Saúde, provado por portão. Reproduz o que cada
município declarou ao Tesouro Nacional, com exercício, anexo, coluna e data de consulta.
Nunca estima, nunca interpola, e **ausência nunca vira zero**.

O QUE ESTE ARQUIVO MEDE, E O QUE ELE NÃO MEDE
---------------------------------------------
Mede a **despesa liquidada na subfunção 182 (Defesa Civil)**, declarada na DCA — a
Declaração de Contas Anuais que todo município entrega ao SICONFI. Não mede o saldo do
Fundo Municipal de Proteção e Defesa Civil, que não é dado centralizado e vive só no
portal ou na lei orçamentária de cada município (camada C do pedido, por amostragem).

Duas limitações que a fonte impõe e que a legenda pública é obrigada a dizer:
  1. **A subfunção 182 soma preparação e resposta**, e não há como separá-las no dado.
     Um município que gastou tudo socorrendo uma enchente aparece igual a um que gastou
     tudo em plano e treinamento.
  2. **Parte dos municípios lança defesa civil em OUTRA subfunção** — drenagem (17.512),
     urbanismo (15.451), segurança pública (06.181). "Sem lançamento em 182" não é "sem
     gasto em defesa civil": é ausência de lançamento NAQUELA subfunção, e a classe se
     chama assim.

TRÊS CLASSES DE AUSÊNCIA, QUE SÃO COISAS DIFERENTES
---------------------------------------------------
  `sem_lancamento_182`  — o município entregou a DCA e não lançou nada na 182.
  `sem_declaracao`      — o município não entregou o exercício ao SICONFI.
  `sem_coleta`          — o Monitor ainda não consultou aquele município.
Nenhuma das três é zero, e nenhuma delas tem `rs_hab`.

FORMA DA API, MEDIDA COM REDE EM 24/09/2026
-------------------------------------------
Anexo: `DCA-Anexo I-E` (rótulo "Total Geral da Despesa por Função"). A subfunção vem no
campo `conta`, como "06.182 - Defesa Civil". O campo `coluna` distingue Despesas
Empenhadas, Liquidadas, Pagas e as duas de Inscrição de Restos a Pagar. `id_ente` tem de
ser o código IBGE EXATO: consulta sem `id_ente` devolve zero itens, e não existe consulta
em lote — são 5.570 chamadas, o que cabe na cadência anual da DCA.
Fixture de valor conhecido: Rio de Janeiro (3304557), 2025, liquidada R$ 3.105.485,95.

USO
  python coletar_siconfi_182.py --autoteste          # prova os parsers sem rede
  python coletar_siconfi_182.py --semear             # cria o registro vazio
  python coletar_siconfi_182.py --capitais           # só as 27 capitais (piloto)
  python coletar_siconfi_182.py --uf SP              # uma UF
  python coletar_siconfi_182.py --lote 300           # próximos N municípios pendentes
  python coletar_siconfi_182.py --paralelo 6         # trabalhadores de REDE (padrão 6)
"""
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.parse
from datetime import date

from coletores_base import (abrir_lote_log, buscar, descarregar_lote_log, fechar_lote_log,
                            ler, log_busca, registrar_lacuna, rodar_autoteste, sha256)

RAIZ = pathlib.Path(__file__).parent
DESTINO = RAIZ / "data" / "financiamento" / "municipios" / "despesa_182.json"
POPULACAO = RAIZ / "data" / "populacao_censo2022.json"
REFERENCIA = RAIZ / "data" / "municipios_ibge_referencia.json"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()

API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
ANEXO = "DCA-Anexo I-E"
EXERCICIO_PADRAO = 2025
SUBFUNCAO = "06.182"
# Nomes EXATOS das colunas, como o Tesouro as devolve. A liquidada é a publicada (despesa
# reconhecida como devida); as outras ficam guardadas porque a diferença entre elas é informação.
COLUNA_PUBLICADA = "Despesas Liquidadas"
COLUNAS = {"Despesas Empenhadas": "empenhada", COLUNA_PUBLICADA: "liquidada",
           "Despesas Pagas": "paga",
           "Inscrição de Restos a Pagar Não Processados": "rp_nao_processados",
           "Inscrição de Restos a Pagar Processados": "rp_processados"}
FORMULA_RS_HAB = "despesa liquidada na subfunção 06.182 ÷ população do Censo 2022"
# Busca em paralelo: só a REDE. Medido em 24/09/2026 contra o Tesouro — 1 trabalhador dá 60
# chamadas/min, 8 dão 522, sem um erro. Seis é o meio-termo escolhido: corta a varredura nacional
# de seis horas para cerca de vinte minutos sem tratar a fonte como se fosse nossa. Tudo o que
# MUTA estado (registro, log, arquivo) continua numa thread só, na ordem — paralelizar mutação
# seria trocar seis horas por uma corrida de dados no livro de buscas.
TRABALHADORES = 6
RESSALVA_OBRIGATORIA = "inclui preparação e resposta"

# Capital de cada UF pelo CÓDIGO IBGE, que é a chave canônica. A mesma tabela existe em
# coletar_sinais_risco.py (`CAPITAL_IBGE`), e o autoteste compara as duas QUANDO aquele módulo a
# tem — assim este coletor não depende dele para rodar, e uma divergência entre as duas cópias
# reprova em vez de passar em silêncio. Nome e coordenada saem sempre do arquivo de referência.
CAPITAL_IBGE = {
    "1200401", "2704302", "1302603", "1600303", "2927408", "2304400", "5300108", "3205309",
    "5208707", "2111300", "3106200", "5002704", "5103403", "1501402", "2507507", "2611606",
    "2211001", "4106902", "3304557", "2408102", "1100205", "1400100", "4314902", "4205407",
    "2800308", "3550308", "1721000",
}


def hoje() -> str:
    return date.today().strftime("%d/%m/%Y")


def parse_dca_182(dados, exercicio: int = None) -> dict:
    """Lê a resposta do anexo I-E de UM município e devolve as colunas da subfunção 182.

    Devolve {} quando o município não declarou o exercício (resposta sem itens) e
    {'sem_lancamento_182': True, ...} quando declarou e não lançou nada na 182 — que são
    coisas DIFERENTES e não podem virar o mesmo registro. Função pura."""
    itens = (dados or {}).get("items") if isinstance(dados, dict) else dados
    if not itens:
        return {}
    achado, contexto = {}, {}
    for it in itens:
        if not isinstance(it, dict):
            continue
        contexto = {"cod_ibge": it.get("cod_ibge"), "uf": it.get("uf"),
                    "instituicao": it.get("instituicao"), "exercicio": it.get("exercicio"),
                    "populacao_siconfi": it.get("populacao")}
        if not str(it.get("conta") or "").startswith(SUBFUNCAO):
            continue
        rotulo = COLUNAS.get(str(it.get("coluna") or "").strip())
        if rotulo and isinstance(it.get("valor"), (int, float)):
            achado[rotulo] = float(it["valor"])
    if not contexto:
        return {}
    if exercicio and contexto.get("exercicio") not in (exercicio, str(exercicio)):
        return {}
    base = {**contexto, "anexo": ANEXO, "conta": f"{SUBFUNCAO} - Defesa Civil"}
    if not achado:
        # Declarou o exercício e não lançou na subfunção 182. Muitos lançam defesa civil em
        # drenagem, urbanismo ou segurança — por isso a classe NÃO se chama "sem gasto".
        return {**base, "classe": "sem_lancamento_182", "valores": {}, "rs_hab": None}
    return {**base, "classe": "com_lancamento", "valores": achado, "rs_hab": None}


def rs_por_habitante(liquidada, populacao) -> float | None:
    """R$ por habitante, com a população do Censo 2022. None quando falta qualquer um dos dois —
    dividir por população ausente produziria número, e número aqui seria invenção.

    Precisão de SEIS casas, não duas. Medido no piloto das capitais em 24/09/2026: Curitiba
    liquidou R$ 2.467,02 para 1,77 milhão de habitantes, o que a duas casas virava **R$ 0,00/hab**
    — um valor real apresentado como zero, que é o defeito que este arquivo existe para não
    cometer. O dado guarda a precisão; a página arredonda para exibir, e dirá "menos de R$ 0,01"
    em vez de "R$ 0,00". Função pura."""
    if not isinstance(liquidada, (int, float)) or not isinstance(populacao, int) or populacao <= 0:
        return None
    valor = round(liquidada / populacao, 6)
    # Um valor positivo nunca pode sair daqui como zero.
    return valor if valor > 0 or liquidada == 0 else None


def esqueleto() -> dict:
    """Registro vazio, com a governança e a fórmula declaradas NO DADO."""
    return {
        "_formato": {
            "descricao": "Despesa municipal liquidada na subfunção 06.182 (Defesa Civil), declarada "
                         "ao SICONFI na DCA, por município e por exercício.",
            "efeito_no_indice": "NENHUM — peso zero. Nunca lido por recalcular_mare.py nem por "
                                "gerar_monitor_saude.py (portão).",
            "formula_rs_hab": FORMULA_RS_HAB,
            "populacao": "Censo 2022 (data/populacao_censo2022.json), sempre — nunca a estimativa "
                         "que o próprio SICONFI devolve, que fica guardada como contexto.",
            "ressalva_obrigatoria": RESSALVA_OBRIGATORIA,
            "limite_da_fonte": "A subfunção 182 soma preparação e resposta, e a fonte não separa. "
                               "Parte dos municípios lança defesa civil em outra subfunção "
                               "(drenagem 17.512, urbanismo 15.451, segurança 06.181).",
            "classes_de_ausencia": {
                "sem_lancamento_182": "entregou a DCA e não lançou nada na subfunção 182 — não é ausência de gasto em defesa civil",
                "sem_declaracao": "não entregou o exercício ao SICONFI",
                "sem_coleta": "o Monitor ainda não consultou este município",
            },
            "escrito_por": "coletar_siconfi_182.py",
        },
        "exercicio": EXERCICIO_PADRAO,
        "gerado_em": hoje(),
        "resumo": {},
        "municipios": {},
    }


def alvos(args) -> list:
    """Lista de (codigo_ibge, nome, uf) a consultar nesta rodada, conforme o recorte pedido."""
    ref = json.loads(REFERENCIA.read_text(encoding="utf-8"))
    todos = [(str(m["codigo_ibge"]).zfill(7), m["nome"], m["uf"]) for m in ref if m.get("codigo_ibge")]
    if "--uf" in args:
        uf = args[args.index("--uf") + 1].upper()
        return [t for t in todos if t[2] == uf]
    if "--capitais" in args:
        return [t for t in todos if t[0] in CAPITAL_IBGE]
    return todos


def calcular_resumo(registro: dict) -> dict:
    """Contagens e mediana do R$/hab. A mediana é sobre quem TEM lançamento: incluir as três
    classes de ausência como zero rebaixaria a mediana com não-dado, que é o erro que este
    arquivo existe para não cometer."""
    muns = registro.get("municipios") or {}
    com = [v["rs_hab"] for v in muns.values() if v.get("classe") == "com_lancamento" and v.get("rs_hab") is not None]
    com.sort()
    mediana = None
    if com:
        n = len(com)
        mediana = com[n // 2] if n % 2 else round((com[n // 2 - 1] + com[n // 2]) / 2, 6)
    return {
        "consultados": len(muns),
        "com_lancamento": sum(1 for v in muns.values() if v.get("classe") == "com_lancamento"),
        "sem_lancamento_182": sum(1 for v in muns.values() if v.get("classe") == "sem_lancamento_182"),
        "sem_declaracao": sum(1 for v in muns.values() if v.get("classe") == "sem_declaracao"),
        "com_rs_hab": len(com),
        "mediana_rs_hab": mediana,
        "minimo_rs_hab": com[0] if com else None,
        "maximo_rs_hab": com[-1] if com else None,
    }


def gravar(registro: dict) -> None:
    registro["gerado_em"] = hoje()
    registro["resumo"] = calcular_resumo(registro)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8", newline="\n")
    r = registro["resumo"]
    print(f"→ {DESTINO.relative_to(RAIZ)}: {r['consultados']} consultado(s), "
          f"{r['com_lancamento']} com lançamento, {r['sem_lancamento_182']} sem lançamento na 182, "
          f"{r['sem_declaracao']} sem declaração · mediana R$ {r['mediana_rs_hab']}/hab")


def coletar(args) -> int:
    exercicio = int(args[args.index("--exercicio") + 1]) if "--exercicio" in args else EXERCICIO_PADRAO
    registro = json.loads(DESTINO.read_text(encoding="utf-8")) if DESTINO.exists() else esqueleto()
    registro["exercicio"] = exercicio
    populacao = json.loads(POPULACAO.read_text(encoding="utf-8"))
    pendentes = [t for t in alvos(args) if t[0] not in registro["municipios"]]
    if "--lote" in args:
        pendentes = pendentes[: int(args[args.index("--lote") + 1])]
    print(f"SICONFI 182 · exercício {exercicio} · {len(pendentes)} município(s) nesta rodada")
    # Varredura nacional: sem lote, seriam 5.570 leituras e gravações de um log de 16 MB (§209).
    # O lote acumula em memória e descarrega de 250 em 250, junto com o salvamento parcial abaixo.
    abrir_lote_log()
    ok = sem_decl = falhas = 0
    trabalhadores = int(args[args.index("--paralelo") + 1]) if "--paralelo" in args else TRABALHADORES

    def puxar(alvo):
        """Só rede, e devolve o erro em vez de levantar — quem consome muta o estado, em ordem."""
        cod, nome, uf = alvo
        url = f"{API}?an_exercicio={exercicio}&no_anexo={urllib.parse.quote(ANEXO)}&id_ente={cod}"
        try:
            return alvo, url, buscar(url, timeout=40, origem="coletar_siconfi_182"), None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return alvo, url, None, e

    piscina = ThreadPoolExecutor(max_workers=trabalhadores)
    resultados = piscina.map(puxar, pendentes)
    for i, ((cod, nome, uf), url, bruto, erro) in enumerate(resultados, 1):
        if erro is not None:
            registrar_lacuna(f"SICONFI 182/{nome}-{uf}", type(erro).__name__, canal="DOU", camada=1,
                             uf=uf, municipio=nome, ibge=cod, strings=[url])
            falhas += 1
            if falhas > 200 and falhas > ok:
                # A fonte caiu de vez: parar e declarar, em vez de varrer 5 mil erros.
                piscina.shutdown(wait=False, cancel_futures=True)
                fechar_lote_log(); gravar(registro)
                print(f"[aviso] SICONFI: {falhas} falhas de rede contra {ok} leituras — rodada interrompida.")
                return 0
            continue
        try:
            lido = parse_dca_182(json.loads(bruto.decode("utf-8", "replace")), exercicio)
        except (ValueError, json.JSONDecodeError):
            falhas += 1
            continue
        if not lido:
            # Resposta sem itens: o município não entregou este exercício. É classe própria, com
            # fonte e data, e nunca um valor.
            # Exceção federativa medida em 24/09/2026: o Distrito Federal não entrega DCA de
            # MUNICÍPIO porque não é município — declara como estado. Chamar isso de "não
            # entregou" imputaria a ele uma falha que não existe.
            registro["municipios"][cod] = {
                "nome": nome, "uf": uf, "exercicio": exercicio, "classe": "sem_declaracao",
                "valores": {}, "rs_hab": None, "fonte_url": url, "consultado_em": hoje(),
                "sha256": sha256(bruto),
                **({"nota": "O Distrito Federal não entrega DCA municipal: declara como estado, "
                            "por natureza federativa. Não é ausência de entrega."} if cod == "5300108" else {}),
            }
            sem_decl += 1
        else:
            liquidada = (lido.get("valores") or {}).get("liquidada")
            pop = populacao.get(cod)
            registro["municipios"][cod] = {
                **lido, "nome": nome, "uf": uf, "exercicio": exercicio,
                "populacao_censo2022": pop,
                "rs_hab": rs_por_habitante(liquidada, pop),
                "formula_rs_hab": FORMULA_RS_HAB,
                "fonte_url": url, "consultado_em": hoje(), "sha256": sha256(bruto),
            }
            ok += 1
        log_busca("DOU", 1, [url], "registro", uf=uf, municipio=nome, ibge=cod, nivel=None,
                  n_resultados=1, resultados=f"SICONFI 182: {registro['municipios'][cod]['classe']}",
                  hash_evidencia=sha256(bruto))
        if i % 200 == 0:
            descarregar_lote_log()
            gravar(registro)      # salva parcial: 5.570 chamadas não podem depender de terminar
            print(f"  … {i}/{len(pendentes)}", flush=True)
    piscina.shutdown(wait=True)
    fechar_lote_log()
    gravar(registro)
    print(f"  com lançamento nesta rodada: {ok} · sem declaração: {sem_decl} · falhas de rede: {falhas}")
    return 0


# ---------------------------------------------------------------------------
# AUTOTESTE — sem rede, sem escrever em data/
# ---------------------------------------------------------------------------
def _resposta(itens):
    return {"items": itens}


def _linha(coluna, valor, conta="06.182 - Defesa Civil", exercicio=2025):
    return {"exercicio": exercicio, "instituicao": "Prefeitura Municipal do Rio de Janeiro - RJ",
            "cod_ibge": 3304557, "uf": "RJ", "anexo": ANEXO, "rotulo": "Total Geral da Despesa por Função",
            "coluna": coluna, "cod_conta": "TotalDespesas", "conta": conta, "valor": valor,
            "populacao": 6625849}


# Valores REAIS do Rio de Janeiro em 2025, medidos com rede em 24/09/2026. Fixture de valor
# conhecido: se o Tesouro mudar a forma da resposta, este teste cai antes de qualquer publicação.
FIX_RJ = _resposta([
    _linha("Despesas Empenhadas", 3159065.0),
    _linha(COLUNA_PUBLICADA, 3105485.95),
    _linha("Despesas Pagas", 2934401.56),
    _linha("Inscrição de Restos a Pagar Não Processados", 53579.05),
    _linha("Inscrição de Restos a Pagar Processados", 171084.39),
    _linha(COLUNA_PUBLICADA, 39127713548.11, conta="Despesas Exceto Intraorçamentárias"),
])


def autoteste() -> int:
    def t1():
        r = parse_dca_182(FIX_RJ, 2025)
        return (r["classe"] == "com_lancamento" and r["valores"]["liquidada"] == 3105485.95
                and r["valores"]["empenhada"] == 3159065.0 and r["valores"]["paga"] == 2934401.56)

    def t2():   # a linha do TOTAL da despesa não pode entrar como se fosse a subfunção
        r = parse_dca_182(FIX_RJ, 2025)
        return r["valores"]["liquidada"] != 39127713548.11

    def t3():   # R$/hab com valor conhecido, e a população escolhida MUDA o número publicado
        # 3.105.485,95 / 6.625.849 (estimativa do SICONFI) = 0,468...
        # 3.105.485,95 / 6.211.423 (Censo 2022, que é a nossa)  = 0,499...
        pelo_siconfi = rs_por_habitante(3105485.95, 6625849)
        pelo_censo = rs_por_habitante(3105485.95, 6211423)
        return (round(pelo_siconfi, 2) == 0.47 and round(pelo_censo, 2) == 0.5
                and pelo_censo > pelo_siconfi)

    def t3b():  # valor real pequeno NUNCA sai como zero (Curitiba, medida no piloto de 24/09/2026)
        v = rs_por_habitante(2467.02, 1773718)
        return v is not None and v > 0 and round(v, 2) == 0.0 and v == round(2467.02 / 1773718, 6)

    def t4():   # declarou e não lançou na 182 ≠ não declarou: classes diferentes, nenhuma é zero
        semLanc = parse_dca_182(_resposta([_linha(COLUNA_PUBLICADA, 1000.0, conta="04.122 - Administração Geral")]), 2025)
        naoDecl = parse_dca_182(_resposta([]), 2025)
        return (semLanc["classe"] == "sem_lancamento_182" and semLanc["valores"] == {}
                and semLanc["rs_hab"] is None and naoDecl == {})

    def t5():   # ausência NUNCA vira zero: sem população, sem liquidada, valores absurdos
        return (rs_por_habitante(3105485.95, None) is None
                and rs_por_habitante(None, 6625849) is None
                and rs_por_habitante(1000.0, 0) is None
                and rs_por_habitante(1000.0, -5) is None)

    def t6():   # exercício diferente do pedido não é aceito como se fosse
        outro = parse_dca_182(_resposta([_linha(COLUNA_PUBLICADA, 500.0, exercicio=2023)]), 2025)
        return outro == {}

    def t7():   # negativo: resposta malformada não quebra e não inventa registro
        return (parse_dca_182(None) == {} and parse_dca_182({}) == {}
                and parse_dca_182({"items": [None, 1, "x"]}) == {})

    def t8():   # a mediana é sobre quem TEM lançamento; ausência não rebaixa a mediana com não-dado
        reg = {"municipios": {
            "1": {"classe": "com_lancamento", "rs_hab": 10.0},
            "2": {"classe": "com_lancamento", "rs_hab": 20.0},
            "3": {"classe": "com_lancamento", "rs_hab": 30.0},
            "4": {"classe": "sem_lancamento_182", "rs_hab": None},
            "5": {"classe": "sem_declaracao", "rs_hab": None},
        }}
        r = calcular_resumo(reg)
        return (r["mediana_rs_hab"] == 20.0 and r["com_rs_hab"] == 3
                and r["sem_lancamento_182"] == 1 and r["sem_declaracao"] == 1
                and r["consultados"] == 5)

    def t9():   # a fórmula e a ressalva ficam declaradas NO DADO, não no HTML
        f = esqueleto()["_formato"]
        return (f["formula_rs_hab"] == FORMULA_RS_HAB
                and f["ressalva_obrigatoria"] == RESSALVA_OBRIGATORIA
                and "NENHUM" in f["efeito_no_indice"]
                and set(f["classes_de_ausencia"]) == {"sem_lancamento_182", "sem_declaracao", "sem_coleta"})

    def t10():  # o autoteste não escreve em data/
        return not DESTINO.exists() or DESTINO.read_bytes() == _SNAP

    def t11():  # as 27 capitais resolvem no arquivo de referência, uma por UF
        ref = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        achadas = {m["uf"]: m["nome"] for m in ref if str(m.get("codigo_ibge", "")).zfill(7) in CAPITAL_IBGE}
        return (len(CAPITAL_IBGE) == 27 and len(achadas) == 27 and set(achadas) == set(UFS)
                and achadas["DF"] == "Brasília" and achadas["RJ"] == "Rio de Janeiro")

    def t12():  # a cópia desta tabela não divergiu da de coletar_sinais_risco.py
        try:
            from coletar_sinais_risco import CAPITAL_IBGE as canonica
        except ImportError:
            return True                     # o outro módulo ainda não tem a tabela: nada a comparar
        return {str(c).zfill(7) for c in canonica.values()} == CAPITAL_IBGE

    _SNAP = DESTINO.read_bytes() if DESTINO.exists() else b""
    return rodar_autoteste({
        "DCA: lê as cinco colunas da subfunção 182 (valores reais do RJ em 2025)": t1,
        "DCA: a linha do total da despesa não entra como subfunção": t2,
        "R$/hab: valor conhecido do RJ, e a população escolhida muda o número": t3,
        "R$/hab: valor real pequeno nunca sai como zero (Curitiba)": t3b,
        "classes: 'declarou e não lançou na 182' ≠ 'não declarou'": t4,
        "ausência NUNCA vira zero (sem população, sem valor, população inválida)": t5,
        "exercício diferente do pedido não é aceito": t6,
        "negativo: resposta malformada não inventa registro": t7,
        "mediana: calculada só sobre quem tem lançamento": t8,
        "fórmula e ressalva declaradas no dado": t9,
        "negativo: autoteste não escreve em data/": t10,
        "capitais: os 27 códigos resolvem no arquivo de referência, um por UF": t11,
        "capitais: esta tabela não divergiu da de coletar_sinais_risco.py": t12,
    })


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    if "--semear" in args:
        reg = esqueleto()
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        DESTINO.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"→ {DESTINO.relative_to(RAIZ)} semeado (vazio, com a governança declarada).")
        return 0
    return coletar(args)


if __name__ == "__main__":
    sys.exit(main())
