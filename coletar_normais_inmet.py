#!/usr/bin/env python3
"""Normais climatológicas 1991–2020 do Inmet: a média das máximas de cada mês, por capital.

Item R10 do handover do Monitor de riscos (editoria, 30/09/2026): o mapa de calor mostra a máxima
prevista ao lado da capital e, na cor, **quanto ela está acima da média histórica daquele mês**.

POR QUE DESVIO, E NÃO TEMPERATURA
---------------------------------
35 °C é normal em Cuiabá e muito quente em Porto Alegre. Pintar as capitais pela temperatura
absoluta faz o mapa dizer "está quente no Centro-Oeste" todo dia do ano, que é geografia, não
notícia. O desvio contra a normal da própria capital responde a pergunta que importa: está mais
quente do que o normal **ali**?

A REGRA QUE O HANDOVER FIXA, E QUE ESTE COLETOR OBEDECE
-------------------------------------------------------
"Coletar as normais uma vez, preservar com hash; se alguma capital não tiver normal, **anel vazio**
('Sem dado'), nunca estimativa." Então:

* **uma vez**: a normal 1991–2020 é um documento fechado, publicado e que só muda quando o Inmet
  publica outro. A cadência é por documento — só reprocessa se o hash do arquivo mudar;
* **nunca estimativa**: capital sem estação na planilha, ou com o traço que o Inmet usa para mês sem
  normal calculada, fica **sem valor**. Não se interpola do mês vizinho nem da capital vizinha, e o
  mapa mostra anel vazio. Dado ausente e dado baixo não podem se parecer.

O CASAMENTO ENTRE ESTAÇÃO E CAPITAL
-----------------------------------
A planilha tem o nome da estação, não o do município, e as duas coisas não são a mesma: há estação
chamada "ALTO DA BOA VISTA" que é no Rio, e capital cujo nome aparece sem acento. O casamento é por
**nome normalizado + UF**, com a lista de equivalências declarada aqui — e **o que não casar fica
sem normal**, nomeado na saída. Aproximação silenciosa aqui viraria desvio errado num mapa público.

PESO ZERO
---------
Camada de contexto do Monitor de riscos. Não escreve em `indice.json`, `estados.json`,
`saude_uf.json` nem `monitor_saude.json`.

USO
  python3 coletar_normais_inmet.py --autoteste
  python3 coletar_normais_inmet.py
"""
import io
import json
import pathlib
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

FONTE = "https://portal.inmet.gov.br/uploads/normais/Normal-Climatologica-TMAX.xlsx"
INSTRUMENTO = ("Normal Climatológica do Brasil 1991–2020, temperatura máxima mensal e anual (°C) — "
               "Instituto Nacional de Meteorologia (Inmet)")
SAIDA = RAIZ / "data" / "normais_capitais.json"

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

CAPITAIS = {
    "AC": "Rio Branco", "AL": "Maceió", "AM": "Manaus", "AP": "Macapá", "BA": "Salvador",
    "CE": "Fortaleza", "DF": "Brasília", "ES": "Vitória", "GO": "Goiânia", "MA": "São Luís",
    "MG": "Belo Horizonte", "MS": "Campo Grande", "MT": "Cuiabá", "PA": "Belém",
    "PB": "João Pessoa", "PE": "Recife", "PI": "Teresina", "PR": "Curitiba",
    "RJ": "Rio de Janeiro", "RN": "Natal", "RO": "Porto Velho", "RR": "Boa Vista",
    "RS": "Porto Alegre", "SC": "Florianópolis", "SE": "Aracaju", "SP": "São Paulo",
    "TO": "Palmas",
}

# Estações cujo NOME não é o da capital, com a razão de cada uma. Declaradas aqui porque
# equivalência de nome é julgamento, e julgamento que não está escrito não pode ser conferido.
EQUIVALENCIAS = {
    # (UF, nome normalizado da estação): capital que ela representa.
    # Três casos, todos de estação que É a da capital e traz o bairro no nome:
    ("BA", "salvador (ondina)"): "Salvador",
    ("PE", "recife (curado)"): "Recife",
    ("SP", "sao paulo(mir.de santana)"): "São Paulo",
}

# Capitais que FICAM SEM normal, com a razão escrita. Elas não entram por equivalência porque não
# há estação delas na planilha — e preencher com a estação mais próxima seria inventar o número que
# o mapa publica. Cada uma aparece como anel vazio.
#
#   MS · Campo Grande — a planilha traz só Paranaíba no estado.
#   RO · Porto Velho  — nenhuma estação de Rondônia na planilha.
#   RJ · Rio de Janeiro — há "ALTO DA BOA VISTA", que fica DENTRO do município, mas é estação de
#        floresta de montanha, a mais de 300 m: a normal dela não é a da cidade, e usá-la como se
#        fosse daria um desvio errado todo dia. Lacuna declarada é melhor do que número bonito.
SEM_ESTACAO_NA_PLANILHA = {"MS": "só Paranaíba no estado",
                           "RO": "nenhuma estação de Rondônia na planilha",
                           "RJ": "só Alto da Boa Vista, estação de montanha, não representativa da cidade"}


def normalizar(texto: str) -> str:
    """Nome sem acento, em minúsculas, com espaços colapsados. Função pura."""
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def valor_de(celula):
    """O número da célula, ou None. Função pura.

    O Inmet usa o traço para "mês sem normal calculada". Traço NÃO é zero, e NÃO é um mês quente:
    é ausência, e volta como None para o mapa mostrar anel vazio."""
    if celula is None:
        return None
    if isinstance(celula, (int, float)):
        return round(float(celula), 1)
    t = str(celula).strip().replace(",", ".")
    if not t or t in {"-", "—", "–", "*"}:
        return None
    try:
        return round(float(t), 1)
    except ValueError:
        return None


def linhas_da_planilha(corpo: bytes) -> list:
    """[(uf, nome da estação, [12 valores])] da planilha do Inmet.

    O cabeçalho é descartado pelo formato: só entra linha cuja terceira coluna é uma UF de duas
    letras maiúsculas e que tenha as doze colunas de mês."""
    import openpyxl
    aba = openpyxl.load_workbook(io.BytesIO(corpo), data_only=True, read_only=True).worksheets[0]
    fora = []
    for linha in aba.iter_rows(values_only=True):
        if not linha or len(linha) < 15:
            continue
        uf = str(linha[2] or "").strip()
        if len(uf) != 2 or not uf.isalpha() or uf != uf.upper():
            continue
        fora.append((uf, str(linha[1] or "").strip(), [valor_de(c) for c in linha[3:15]]))
    return fora


def normais_por_capital(linhas: list, capitais: dict = None, equivalencias: dict = None) -> dict:
    """{UF: {"estacao":…, "tmax": [12 valores]}} só das capitais. Função pura.

    Quando mais de uma estação casa com a mesma capital, fica a que tem MAIS meses com valor — uma
    estação com dez meses em branco não é melhor fonte do que outra completa, e escolher a primeira
    da planilha seria escolher por ordem alfabética, que não é critério."""
    capitais = capitais or CAPITAIS
    equivalencias = equivalencias if equivalencias is not None else EQUIVALENCIAS
    alvo = {(uf, normalizar(nome)): uf for uf, nome in capitais.items()}
    fora = {}
    for uf, estacao, valores in linhas or []:
        chave = (uf, normalizar(estacao))
        capital = None
        if chave in alvo:
            capital = capitais[uf]
        elif chave in equivalencias and equivalencias[chave] == capitais.get(uf):
            capital = capitais[uf]
        if not capital:
            continue
        preenchidos = sum(1 for v in valores if v is not None)
        atual = fora.get(uf)
        if atual is None or preenchidos > atual["_preenchidos"]:
            fora[uf] = {"estacao": estacao, "tmax": valores, "_preenchidos": preenchidos}
    for v in fora.values():
        v.pop("_preenchidos", None)
    return dict(sorted(fora.items()))


def problemas(normais: dict) -> list:
    """As falhas que impedem a gravação. Função pura.

    Capital sem normal NÃO é falha: é lacuna declarada, e o mapa a mostra como anel vazio. Falha é
    a planilha vir vazia, ou vir com valor fora da faixa física — aí a leitura está errada, e um
    desvio calculado sobre leitura errada seria pior do que nenhum desvio."""
    ruins = []
    if not normais:
        ruins.append("nenhuma capital casou com estação da planilha — a leitura falhou")
    for uf, v in sorted((normais or {}).items()):
        vals = [x for x in (v.get("tmax") or []) if x is not None]
        if len(v.get("tmax") or []) != 12:
            ruins.append(f"{uf}: {len(v.get('tmax') or [])} meses, esperados 12")
        fora_da_faixa = [x for x in vals if not (0 <= x <= 50)]
        if fora_da_faixa:
            ruins.append(f"{uf}: temperatura fora da faixa física (0–50 °C): {fora_da_faixa[:3]}")
    return ruins


def autoteste() -> int:
    linhas = [
        ("SP", "SAO PAULO MIRANTE", [28.0] * 12),
        ("SP", "SAO PAULO", [27.0] * 6 + [None] * 6),
        ("MT", "CUIABA", [34.5] * 12),
        ("RJ", "ALTO DA BOA VISTA", [30.2] * 12),
        ("BA", "ALAGOINHAS", [33.1] * 12),
    ]
    capitais = {"SP": "São Paulo", "MT": "Cuiabá", "RJ": "Rio de Janeiro", "BA": "Salvador"}
    n = normais_por_capital(linhas, capitais)
    casos = [
        ("tira acento e caixa", normalizar("São Luís") == "sao luis"),
        ("colapsa espaços", normalizar("  Rio   Branco  ") == "rio branco"),
        ("texto nulo não quebra", normalizar(None) == ""),
        ("número vira valor", valor_de(31.1) == 31.1),
        ("texto com vírgula vira valor", valor_de("31,1") == 31.1),
        ("traço do Inmet é ausência, não zero", valor_de("-") is None),
        ("célula vazia é ausência", valor_de(None) is None),
        ("texto que não é número é ausência", valor_de("sem dado") is None),

        ("casa a capital pelo nome", "MT" in n and n["MT"]["estacao"] == "CUIABA"),
        ("estação da capital com bairro no nome entra por equivalência declarada",
         "BA" in normais_por_capital([("BA", "SALVADOR (ONDINA)", [31.0] * 12)],
                                     {"BA": "Salvador"},
                                     {("BA", "salvador (ondina)"): "Salvador"})),
        ("estação que não é capital fica de fora", "BA" not in n),
        ("estação de nome diferente não casa sozinha", "RJ" not in n),
        ("entre duas estações da mesma capital, fica a mais completa",
         normais_por_capital([("SP", "SAO PAULO", [27.0] * 6 + [None] * 6),
                              ("SP", "SAO PAULO", [28.0] * 12)],
                             {"SP": "São Paulo"})["SP"]["tmax"][0] == 28.0),
        ("devolve os doze meses", len(n["MT"]["tmax"]) == 12),
        ("ordena por UF", list(n) == sorted(n)),
        ("sem linhas devolve vazio", normais_por_capital([], capitais) == {}),
        ("linhas nulas não quebram", normais_por_capital(None, capitais) == {}),
        ("equivalência declarada casa",
         "RJ" in normais_por_capital(linhas, capitais,
                                     {("RJ", "alto da boa vista"): "Rio de Janeiro"})),

        ("normais boas passam", problemas(n) == []),
        ("dicionário vazio reprova", len(problemas({})) == 1),
        ("menos de doze meses reprova",
         any("esperados 12" in p for p in problemas({"SP": {"tmax": [20.0]}}))),
        ("temperatura impossível reprova",
         any("faixa física" in p for p in problemas({"SP": {"tmax": [99.0] * 12}}))),
        ("mês sem normal NÃO é falha",
         problemas({"SP": {"tmax": [28.0] * 6 + [None] * 6}}) == []),
    ]
    ruins = [n_ for n_, ok in casos if not ok]
    for n_, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n_}")
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
    corpo = buscar(FONTE, timeout=180, origem="coletar_normais_inmet")
    impressao = sha256(corpo)
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    if (anterior.get("fonte") or {}).get("hash") == impressao and "--forcar" not in sys.argv:
        print(f"documento igual ao da coleta de {(anterior.get('fonte') or {}).get('consultado_em')}:"
              f" a normal 1991–2020 só muda quando o Inmet publica outra. Nada a reprocessar.")
        return 0
    preservar_evidencia(corpo, FONTE, "xlsx", "coletar_normais_inmet")

    normais = normais_por_capital(linhas_da_planilha(corpo))
    ruins = problemas(normais)
    sem_normal = sorted(set(CAPITAIS) - set(normais))
    print(f"{len(normais)} capital(is) com normal · {len(sem_normal)} sem: "
          f"{', '.join(sem_normal) or 'nenhuma'} · evidência {impressao[:12]}")
    if ruins:
        print("X VALIDAÇÃO — nada foi gravado:")
        for r in ruins:
            print("   -", r)
        return 1

    gravar_em(SAIDA, {
        "_governanca": ("Normal climatológica 1991–2020 do Inmet, temperatura máxima mensal, por "
                        "capital. Serve ao DESVIO do mapa de calor do Monitor de riscos: camada de "
                        "contexto, PESO ZERO, não entra na nota do MARÉ. Capital ausente aqui é "
                        "lacuna declarada — o mapa mostra anel vazio, nunca estimativa."),
        "fonte": {"instrumento": INSTRUMENTO, "url": FONTE,
                  "consultado_em": hoje.isoformat(), "hash": impressao},
        "meses": MESES,
        "capitais_sem_normal": sem_normal,
        "por_que_sem_normal": {uf: SEM_ESTACAO_NA_PLANILHA.get(uf, "não localizada na planilha")
                               for uf in sem_normal},
        "capitais": normais,
    })                                                       # §229
    print(f"{SAIDA.relative_to(RAIZ)} gravado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
