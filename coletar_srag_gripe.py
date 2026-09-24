#!/usr/bin/env python3
"""
coletar_srag_gripe.py — SRAG e síndrome gripal, nacional e por UF (§36, catálogo: srag · sg; 09/09/2026)
=============================================================================================================
Fonte: InfoGripe (Fiocruz/FGV/GT-Influenza, SVS/MS) — série longa com estimativas recentes, publicada em
repositório aberto (GitLab PROCC/Fiocruz), formato "tidy": uma linha por (Tipo, escala, dado, ano
epidemiológico, semana epidemiológica). Tipo ∈ {País, Estado, ...}; dado ∈ {srag, sragflu, sragcovid,
obitos, ...}. Não fornece SRAG por município — é por País e por UF, o que já cobre o gatilho estadual do
plano ("um ou mais alertas... na mesma região").

Como o formato exato de cabeçalho não pôde ser verificado a partir deste ambiente (rede restrita fora da
rotina), o leitor abaixo é DEFENSIVO: localiza as colunas por correspondência de padrão (normalizadas,
sem acento, minúsculas) em vez de nome literal fixo, e REGISTRA no log quais colunas usou — a primeira
rodada real deve ser conferida no relatório do diagnóstico (mesmo princípio do sondar_enso_probabilidades.py).
Se o formato mudar a ponto de não bater nenhum padrão, o coletor falha alto e registra lacuna — nunca adivinha.

Mesmo tratamento do §35 (dengue): canal endêmico (mediana/p75/p90) sobre os mesmos anos, últimas semanas
vazadas até a completude do dado laboratorial, "o Monitor não atribui casos ao El Niño". Peso zero.
  python coletar_srag_gripe.py --autoteste
"""
import json, csv, io, re, statistics, sys, unicodedata
from collections import defaultdict
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
# ESTADO DA FONTE, medido em 24/09/2026 (§198) — os três hosts, um a um:
#   · gitlab.fiocruz.br      → responde, mas com a TELA DE LOGIN do GitLab (HTTP 200, devise-layout);
#                              a API do projeto (`/api/v4/projects/marcelo.gomes%2Finfogripe`) dá 404.
#                              O repositório deixou de ser público.
#   · gitlab.procc.fiocruz.br → inacessível (timeout de conexão), aqui e no runner.
#   DIFERENÇA DE AMBIENTE, declarada para não enganar a próxima sessão: numa máquina Windows o
#   `gitlab.fiocruz.br` nem chega a responder — o servidor manda cadeia TLS incompleta ("unable to
#   get local issuer certificate") e o repositório de raízes do sistema não fecha a cadeia sozinho.
#   O runner do CI, com o repositório de raízes do Linux, alcança o host e recebe a tela de login.
#   Ou seja: rodando local, o coletor registra falha de rede; rodando no CI, registra a recusa. As
#   duas são verdade, e o diagnóstico grava qual delas ocorreu.
#   · infogripe.fiocruz.br    → inacessível (timeout de conexão).
# Consequência: a série de SRAG e de síndrome gripal fica em LACUNA DECLARADA. Os arquivos
# srag_serie.json e sg_serie.json não existem, e a página de saúde já trata ausência de arquivo
# como lacuna — ou seja, o site não mostra dado velho; mostra que não tem. Procurar fonte pública
# equivalente (OpenDataSUS/SIVEP-Gripe é microdado, outra esteira) é trabalho declarado, não feito.
URL_SERIE = "https://gitlab.procc.fiocruz.br/mave/repo/-/raw/master/Dados/InfoGripe/serie_temporal_com_estimativas_recentes.csv"
# 14/09/2026: o host canônico (gitlab.procc) dá timeout desde 09/09 (ver scripts/diagnostico_fontes_saude.py); o InfoGripe
# passou a aparecer também em gitlab.fiocruz.br — a interface pede login, mas o endpoint /-/raw/ pode servir anônimo.
# Tenta em ordem e REGISTRA qual respondeu; nunca mistura as duas.
URLS_SERIE = [URL_SERIE, "https://gitlab.fiocruz.br/marcelo.gomes/infogripe/-/raw/master/Dados/InfoGripe/serie_temporal_com_estimativas_recentes.csv"]
# Indicadores extraídos do mesmo CSV, pela coluna `dado` (rótulos casados por padrão, sem literal fixo). SRAG obrigatório;
# SG (síndrome gripal) só sai se o CSV trouxer um rótulo que case — senão vira lacuna declarada, nunca série vazia/inventada.
INDICADORES = {
    "srag": {"padroes": [r"^srag$", r"^sragflu$"], "arquivo": "saude_desfechos/srag_serie.json", "rotulo": "SRAG", "obrigatorio": True},
    "sg":   {"padroes": [r"^sg$", r"sindrome.*gripal", r"^ili$"],  "arquivo": "saude_desfechos/sg_serie.json",   "rotulo": "síndrome gripal (SG)", "obrigatorio": False},
}
ANOS_CANAL = list(range(2019, 2026))   # 2019–2025; 2024 tratado à parte só quando houver sinal de excepcionalidade nacional (ver nota no §35)
SE_INCOMPLETAS = 4
RESSALVA = "O Monitor não atribui casos ao El Niño; a série é a do InfoGripe (Fiocruz/FGV/GT-Influenza, SVS/MS), notificações do Sivep-Gripe com estimativa de dados recentes."
SIGLA = {"acre":"AC","alagoas":"AL","amapa":"AP","amazonas":"AM","bahia":"BA","ceara":"CE","distrito federal":"DF","espirito santo":"ES","goias":"GO",
         "maranhao":"MA","mato grosso":"MT","mato grosso do sul":"MS","minas gerais":"MG","para":"PA","paraiba":"PB","parana":"PR","pernambuco":"PE",
         "piaui":"PI","rio de janeiro":"RJ","rio grande do norte":"RN","rio grande do sul":"RS","rondonia":"RO","roraima":"RR","santa catarina":"SC",
         "sao paulo":"SP","sergipe":"SE","tocantins":"TO","brasil":"BR","pais":"BR"}


def _hoje():
    import datetime as _dt, json as _js
    try:
        a = _js.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def _plano(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn").strip()


def detectar_colunas(cabecalho: list) -> dict:
    """Localiza, por padrão, as colunas: tipo, escala, dado, ano, semana, valor. Função pura.
    Levanta ValueError se algum papel obrigatório não bater em nenhuma coluna (falha alto, nunca adivinha)."""
    norm = [_plano(h) for h in cabecalho]
    PADROES = {"tipo": [r"^tipo$"], "escala": [r"^escala$"], "dado": [r"^dado$"],
               "ano": [r"ano.*epidemio"], "semana": [r"semana.*epidemio"],
               "valor": [r"casos.*semanais.*reportados", r"^valor$", r"^casos$"]}
    achado = {}
    for papel, pats in PADROES.items():
        for i, h in enumerate(norm):
            if any(re.search(p, h) for p in pats):
                achado[papel] = i; break
        if papel not in achado:
            raise ValueError(f"coluna para '{papel}' não encontrada no cabeçalho InfoGripe: {cabecalho}")
    return achado


def dados_disponiveis(texto: str) -> tuple:
    """(cabeçalho, delimitador, {valores distintos da coluna `dado`}) — para diagnóstico e para escolher o alvo. Função pura."""
    delim = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto), delimiter=delim))
    if not linhas:
        return [], delim, set()
    col = detectar_colunas(linhas[0])
    return linhas[0], delim, {_plano(r[col["dado"]]) for r in linhas[1:] if len(r) > col["dado"]}


def escolher_alvo(disponiveis: set, padroes: list):
    """Primeiro valor de `dado` que casa com algum padrão (na ordem dos padrões); None se nenhum. Função pura."""
    for pat in padroes:
        for d in sorted(disponiveis):
            if re.search(pat, d):
                return d
    return None


def parse_serie_longa(texto: str, padroes: list = None) -> dict:
    """{'BR'|UF: {'AAAA-SS': valor}} para o `dado` que casar com `padroes` (padrão: SRAG), escala='casos'.
    Delimitador autodetectado (';' ou ','). Função pura."""
    padroes = padroes or INDICADORES["srag"]["padroes"]
    delim = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto), delimiter=delim))
    if not linhas:
        return {}
    col = detectar_colunas(linhas[0])
    disponiveis = {_plano(r[col["dado"]]) for r in linhas[1:] if len(r) > col["dado"]}
    alvo = escolher_alvo(disponiveis, padroes)
    if alvo is None:
        raise ValueError(f"nenhum dado casando {padroes} encontrado; disponíveis: {sorted(disponiveis)[:12]}")
    out = defaultdict(dict)
    for r in linhas[1:]:
        if len(r) <= max(col.values()):
            continue
        if _plano(r[col["escala"]]) != "casos" or _plano(r[col["dado"]]) != alvo:
            continue
        loc = SIGLA.get(_plano(r[col["tipo"]]))
        if loc is None:
            continue
        try:
            ano = int(re.sub(r"\D", "", r[col["ano"]])[:4]); se = int(re.sub(r"\D", "", r[col["semana"]])[:2])
            val = float(r[col["valor"]].replace(",", "."))
        except (ValueError, IndexError):
            continue
        if 1 <= se <= 53:
            out[loc][f"{ano}-{se:02d}"] = val
    return dict(out)


def canal_endemico(serie: dict) -> dict:
    """{SS: {mediana, p75, p90, n_anos}} sobre ANOS_CANAL de uma série {'AAAA-SS': valor}. Função pura."""
    por_se = defaultdict(list)
    for chave, v in serie.items():
        ano, ss = chave.split("-")
        if int(ano) in ANOS_CANAL:
            por_se[ss].append(v)
    out = {}
    for ss, vals in por_se.items():
        vals = sorted(vals); n = len(vals)
        if n < 3:
            continue
        q = lambda p: vals[min(n - 1, max(0, int(round(p * (n - 1)))))]
        out[ss] = {"mediana": statistics.median(vals), "p75": q(0.75), "p90": q(0.90), "n_anos": n}
    return out


def vazar_incompletas(serie: dict, ano: int, n: int = SE_INCOMPLETAS) -> tuple:
    chaves = sorted(k for k in serie if k.startswith(f"{ano}-"))
    inc = set(chaves[-n:]) if chaves else set()
    cons = {k: (None if k in inc else v) for k, v in serie.items()}
    return cons, sorted(inc)


# 24/09/2026 (§198): marcas da página de LOGIN do GitLab. `devise-layout-html` é a classe que o
# Devise (a camada de autenticação do Rails, que o GitLab usa) põe no <html> da tela de entrada —
# é a assinatura mais estável, porque não depende de texto traduzido.
MARCAS_DE_LOGIN = ("devise-layout-html", "sign_in", "user_login", "não autorizado", "unauthorized")


def parece_pagina_de_login(corpo: str) -> bool:
    """True se o que voltou é tela de autenticação em vez de dado. Função pura.

    POR QUE EXISTE. Em 24/09/2026 o repositório do InfoGripe no GitLab da Fiocruz deixou de ser
    público: `gitlab.fiocruz.br/...` responde **HTTP 200** com a tela de login do GitLab, e a API do
    projeto responde 404. Sem este reconhecedor, o coletor tratava a resposta como CSV malformado e
    registrava "cabeçalho: ['<!DOCTYPE html>']" — diagnóstico que faz pensar em defeito de parser
    quando o fato é outro: a fonte fechou. É a mesma classe do muro de robô do §186, e a mesma
    disciplina do §170: login é recusa, e recusa se respeita. Não se contorna autenticação.
    """
    if not corpo:
        return False
    inicio = corpo[:4000].lower()
    if "<!doctype html" not in inicio and "<html" not in inicio:
        return False
    return any(m in inicio for m in MARCAS_DE_LOGIN)


def _gravar_diagnostico(url_ok, cabecalho, disponiveis, erro_por_url):
    """Guarda o que a rodada VIU (host que respondeu, cabeçalho real, rótulos de `dado`) — para a próxima sessão
    ajustar padrões sem precisar de rede. Nunca contém dado epidemiológico."""
    gravar("saude_desfechos/infogripe_diagnostico.json", {
        "_governanca": "Diagnóstico de formato do InfoGripe (14/09/2026): registro do que o coletor encontrou; sem dado epidemiológico.",
        "gerado_em": _hoje().strftime("%d/%m/%Y"), "url_que_respondeu": url_ok, "cabecalho": cabecalho,
        "valores_de_dado": sorted(disponiveis)[:60], "erro_por_url": erro_por_url})


# 24/09/2026 (§199): sítio oficial do InfoGripe, indicado como "fonte original" pela ficha da Base
# dos Dados. Ele NÃO é alcançável da máquina de edição — tempo de conexão esgotado, e o mesmo com um
# navegador real, o que exclui problema de cliente. O runner do CI pode alcançá-lo, e é por isso que
# ele entra aqui como SONDA DE DIAGNÓSTICO, não como fonte: a rodada agendada registra o que o host
# respondeu (status, tipo de conteúdo, primeiros bytes) sem tentar interpretar nada como dado. Fazer
# o CI descobrir o que a máquina local não alcança é barato; chutar um caminho de CSV seria inventar.
SITIO_OFICIAL = "https://info.gripe.fiocruz.br/"


def sondar_sitio_oficial(ler_fn=None) -> dict:
    """Devolve o que o sítio oficial respondeu, para o diagnóstico. Nunca devolve dado epidemiológico."""
    ler_fn = ler_fn or (lambda u: buscar(u, timeout=45))
    try:
        corpo = ler_fn(SITIO_OFICIAL)
        txt = corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else str(corpo)
        return {"alcancado": True, "bytes": len(corpo),
                "parece_login": parece_pagina_de_login(txt),
                "inicio": txt[:160]}
    except Exception as e:  # noqa: BLE001
        return {"alcancado": False, "erro": f"{type(e).__name__}: {str(e)[:80]}"}


def coletar() -> int:
    bruto = None; url_ok = None; erro_por_url = {}
    for url in URLS_SERIE:
        try:
            bruto = buscar(url, timeout=90).decode("utf-8", "replace"); url_ok = url; break
        except Exception as e:  # noqa: BLE001
            erro_por_url[url] = type(e).__name__
    if bruto is None:
        # §199: com todos os CSV fora do ar, a rodada aproveita para sondar o sítio oficial e
        # registrar o que ele responde. É diagnóstico, não coleta.
        erro_por_url = dict(erro_por_url, **{SITIO_OFICIAL: json.dumps(sondar_sitio_oficial(), ensure_ascii=False)[:300]})
        _gravar_diagnostico(None, [], set(), erro_por_url)
        registrar_lacuna("InfoGripe (série SRAG)", " · ".join(f"{u.split('/')[2]}: {e}" for u, e in erro_por_url.items()), canal="DOU", camada=1)
        print("srag/sg: falha de rede em todos os hosts — lacuna declarada"); return 0
    if parece_pagina_de_login(bruto):
        _gravar_diagnostico(url_ok, ["<página de login do GitLab>"], set(),
                            dict(erro_por_url, **{url_ok: "acesso recusado: repositório exige autenticação"}))
        registrar_lacuna("InfoGripe (série SRAG e síndrome gripal)",
                         "repositório passou a exigir autenticação — HTTP 200 com tela de login do GitLab; "
                         "a API do projeto responde 404. Login é recusa que se respeita (§170); a série fica "
                         "como lacuna declarada até haver fonte pública equivalente",
                         canal="DOU", camada=1)
        print("srag/sg: a fonte passou a exigir login — recusa respeitada, lacuna declarada")
        return 0
    try:
        cabecalho, _delim, disponiveis = dados_disponiveis(bruto)
    except ValueError as e:
        _gravar_diagnostico(url_ok, bruto.split("\n", 1)[0].split(";")[:20], set(), erro_por_url)
        registrar_lacuna("InfoGripe (formato da série SRAG)", str(e)[:180], canal="DOU", camada=1)
        print(f"srag/sg: {e} — coletor não adivinha; ver data/saude_desfechos/infogripe_diagnostico.json")
        return 0
    _gravar_diagnostico(url_ok, list(cabecalho), disponiveis, erro_por_url)
    hoje = _hoje().strftime("%d/%m/%Y"); ano_corrente = _hoje().year
    escritos = 0
    for chave, ind in INDICADORES.items():
        alvo = escolher_alvo(disponiveis, ind["padroes"])
        if alvo is None:
            registrar_lacuna(f"InfoGripe ({ind['rotulo']})", f"nenhum rótulo de `dado` casou {ind['padroes']}; disponíveis: {sorted(disponiveis)[:12]}", canal="DOU", camada=1)
            print(f"{chave}: rótulo não encontrado no CSV — lacuna declarada (ver infogripe_diagnostico.json)")
            if ind["obrigatorio"]: return 0
            continue
        serie = parse_serie_longa(bruto, ind["padroes"])
        if not serie:
            registrar_lacuna(f"InfoGripe ({ind['rotulo']})", "série vazia após leitura", canal="DOU", camada=1); print(f"{chave}: série vazia — lacuna declarada")
            if ind["obrigatorio"]: return 0
            continue
        canal = {loc: canal_endemico(s_) for loc, s_ in serie.items()}
        consolidada = {}; nowcasting = {}
        for loc, s_ in serie.items():
            cons, vaz = vazar_incompletas(s_, ano_corrente)
            consolidada[loc] = cons
            nowcasting[loc] = {k: s_[k] for k in vaz if k in s_}
        gov = (f"{ind['rotulo']} — nacional e por UF (§36, catálogo). Peso zero, sem nota, sem faixa. " + RESSALVA +
               " Canal endêmico: mediana/p75/p90 de " + f"{min(ANOS_CANAL)}–{max(ANOS_CANAL)}" + ". Últimas " + str(SE_INCOMPLETAS) +
               " SE vazadas (dado laboratorial incompleto); nowcasting = valor bruto do InfoGripe nessas semanas, sem faixa de incerteza própria (a fonte não publica min/max nesta série).")
        (RAIZ / "data" / "saude_desfechos").mkdir(parents=True, exist_ok=True)
        gravar(ind["arquivo"], {"_governanca": gov, "gerado_em": hoje, "fonte": url_ok, "indicador": chave, "rotulo_dado": alvo, "ano_corrente": ano_corrente,
                                "anos_canal": ANOS_CANAL, "se_incompletas": SE_INCOMPLETAS, "serie": consolidada, "nowcasting": nowcasting, "canal_endemico": canal})
        log_busca("DOU", 1, [url_ok], "registro", nivel="nacional", n_resultados=len(serie), resultados=f"{ind['rotulo']}: série lida para {len(serie)} localidade(s) (BR + UFs); dado='{alvo}'; colunas detectadas por padrão")
        ult_br = max((k for k in serie.get("BR", {})), default=None)
        print(f"{chave}: {len(serie)} localidade(s); dado='{alvo}'; última SE (BR): {ult_br or '—'}")
        escritos += 1
    return 0


def autoteste() -> int:
    def t1():
        cab = ["Tipo", "escala", "dado", "Ano epidemiológico", "Semana epidemiológica", "Casos semanais reportados até a última atualização"]
        c = detectar_colunas(cab)
        return c["tipo"] == 0 and c["ano"] == 3 and c["valor"] == 5
    def t2():
        try:
            detectar_colunas(["a", "b", "c"]); return False
        except ValueError:
            return True
    csv_txt = "Tipo;escala;dado;Ano epidemiológico;Semana epidemiológica;Casos semanais reportados até a última atualização\n"
    for ano in (2019, 2020, 2021, 2022, 2023, 2025):
        csv_txt += f"País;casos;srag;{ano};10;{100+ano-2019}\n"
        csv_txt += f"São Paulo;casos;srag;{ano};10;{20+ano-2019}\n"
    for se in range(30, 36):
        csv_txt += f"País;casos;srag;2026;{se};{300 if se <= 32 else 50}\n"
    csv_txt += "País;incidencia;srag;2026;33;9.9\n"   # escala diferente: deve ser ignorada
    def t3():
        s = parse_serie_longa(csv_txt); return "BR" in s and "SP" in s and s["BR"]["2026-30"] == 300 and "2026-33" in s["BR"]
    def t4():
        s = parse_serie_longa(csv_txt); c = canal_endemico(s["BR"]); return c["10"]["n_anos"] == 6 and c["10"]["p90"] >= c["10"]["p75"] >= c["10"]["mediana"]
    def t5():
        s = parse_serie_longa(csv_txt); cons, vaz = vazar_incompletas(s["BR"], 2026)
        return set(vaz) == {"2026-32", "2026-33", "2026-34", "2026-35"} and cons["2026-32"] is None and cons["2026-30"] == 300
    def t6():
        return "não atribui casos ao El Niño" in RESSALVA and SIGLA["sao paulo"] == "SP" and SIGLA["pais"] == "BR"
    # 14/09/2026: SRAG e SG do mesmo CSV; SG só quando o rótulo existe; dois hosts em ordem
    def t7():
        _, _, disp = dados_disponiveis(csv_txt)
        return escolher_alvo(disp, INDICADORES["srag"]["padroes"]) == "srag" and escolher_alvo(disp, INDICADORES["sg"]["padroes"]) is None
    def t8():
        com_sg = csv_txt + "País;casos;sg;2026;30;900\n"
        _, _, disp = dados_disponiveis(com_sg)
        return escolher_alvo(disp, INDICADORES["sg"]["padroes"]) == "sg" and parse_serie_longa(com_sg, INDICADORES["sg"]["padroes"])["BR"]["2026-30"] == 900
    def t9():
        try:
            parse_serie_longa(csv_txt, INDICADORES["sg"]["padroes"]); return False
        except ValueError:
            return len(URLS_SERIE) == 2 and URLS_SERIE[0] == URL_SERIE and "gitlab.fiocruz.br" in URLS_SERIE[1]
    def t_sonda_so_diagnostica():
        """§199: a sonda registra o que o host respondeu e nada mais. Falha vira registro, não exceção;
        e o que ela devolve nunca contém dado epidemiológico — só tamanho, veredito de login e início."""
        falha = sondar_sitio_oficial(lambda u: (_ for _ in ()).throw(TimeoutError("x")))
        login = sondar_sitio_oficial(lambda u: b'<!DOCTYPE html><html class="devise-layout-html">')
        return (falha["alcancado"] is False and "TimeoutError" in falha["erro"]
                and login["alcancado"] is True and login["parece_login"] is True
                and set(login) <= {"alcancado", "bytes", "parece_login", "inicio"})

    def t_reconhece_a_tela_de_login():
        """§198: HTTP 200 com tela de login não é CSV malformado — é recusa, e tem de ser nomeada
        assim. Sem isto, o diagnóstico dizia "cabeçalho: ['<!DOCTYPE html>']" e mandava a próxima
        sessão caçar defeito de parser onde a fonte apenas fechou."""
        LOGIN = '<!DOCTYPE html>' + '\\n' + '<html class="devise-layout-html">'
        CSV = 'SE;ano;dado;valor' + '\\n' + '202601;2026;srag;123'
        casos = [(LOGIN, True),
                 ('<!doctype html><html><body>unauthorized</body></html>', True),
                 (CSV, False),
                 ('', False),
                 ('<!DOCTYPE html><html><p>Boletim InfoGripe</p></html>', False)]
        return all(parece_pagina_de_login(c) is r for c, r in casos)

    return rodar_autoteste({
        "§198 reconhece a tela de login e não a confunde com CSV": t_reconhece_a_tela_de_login,
        "§199 sonda do sítio oficial nunca devolve dado, só diagnóstico": t_sonda_so_diagnostica,"detecção de colunas por padrão": t1, "coluna ausente falha alto (nunca adivinha)": t2,
                            "parse: BR e UF, escala 'casos' filtrada": t3, "canal endêmico: 6 anos, ordenado": t4,
                            "últimas 4 SE vazadas": t5, "ressalva e siglas": t6,
                            "alvo: srag casa, sg ausente → None": t7, "sg extraído só quando o rótulo existe": t8,
                            "sg ausente falha alto; dois hosts em ordem": t9})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
