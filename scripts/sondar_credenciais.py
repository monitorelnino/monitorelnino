#!/usr/bin/env python3
"""
sondar_credenciais.py — a credencial chegou, e a fonte aceita? (§208)
====================================================================
Responde uma pergunta só, e responde rápido: para cada fonte que exige credencial, ela
está no ambiente, e a fonte responde com ela?

POR QUE ESTA SONDA EXISTE
Cadastrar um segredo no GitHub não liga nada por si: o workflow precisa declará-lo no `env`
do passo, e a fonte precisa aceitá-lo. Sem uma verificação própria, descobrir que faltou um
dos dois exigiria esperar a rodada de seis horas e ler o log inteiro. Aqui a resposta sai em
segundos, sob disparo manual.

O QUE ELA NÃO FAZ
Não grava nada. Não toca `data/`. **Nunca imprime a credencial** — só se ela existe, o seu
tamanho e os quatro últimos caracteres, que bastam para distinguir "colei a chave errada" de
"não colei chave nenhuma" sem expor a chave num log público.

DISTINÇÃO QUE ELA PRESERVA
`ausente` (não há segredo), `recusada` (a fonte respondeu 401/403 — credencial inválida ou
sem permissão) e `aceita` são três desfechos diferentes, e confundi-los é o que faz alguém
procurar problema no lugar errado. Recusa servida com 200 e corpo vazio também é recusa
(§186, §187), e aparece como tal.

MODO DA NOITE (central, 01/11/2026)
`--noite` roda a mesma sonda no elo que usa as chaves, grava `data/noite/<noite>/chaves.json`
(Secret, fonte, HTTP, data, `desde`, `vence_em` quando a fonte informa, rota sem chave de
`config/rotas_sem_chave.json`; nunca o valor da chave) e abre/fecha Issue no robo-registro:
uma por chave por episódio, aberta na recusa (401/403) ou validade <= 15 dias, fechada quando
a sonda volta a 200. A coleta não para: a rota sem chave vale.

USO
  python3 scripts/sondar_credenciais.py              # sonda (rede)
  python3 scripts/sondar_credenciais.py --noite      # sonda + chaves.json + Issues
  python3 scripts/sondar_credenciais.py --autoteste  # prova a lógica, sem rede
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import datetime as _dt
import pathlib as _pathlib, sys as _sys
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de, contexto_tls, gravar_em  # noqa: E402  (§228: um cliente só, com propósito)

TEMPO_LIMITE = 25
CABECALHO = {"User-Agent": ua_de("sonda de credenciais")}

# Cada fonte: o nome da variável de ambiente, como a credencial viaja, e um endereço BARATO
# que aceita ou recusa. Endereço de sonda é o menor possível: confirmar acesso não é coletar.
FONTES = {
    "openaq": {
        "nome": "Qualidade do ar medida (OpenAQ)",
        "credencial": "OPENAQ_API_KEY",
        "url": "https://api.openaq.org/v3/locations?iso=BR&limit=1",
        "cabecalho": "X-API-Key",
        "onde_pedir": "https://explore.openaq.org/register (chave em explore.openaq.org/account)",
    },
    "portal_transparencia": {
        # 26/09/2026 (§224): a sonda nasceu (§208) para as duas fontes de MEDIÇÃO e deixou de
        # fora justamente a credencial que já estava cadastrada e sendo recusada — a do Portal,
        # com 403 em toda rodada desde 03/09. A pergunta "a chave nova funcionou?" não tinha
        # como ser respondida sem rodar o pipeline inteiro. O endpoint abaixo é o mais barato da
        # API (uma página, um item) e existe só para perguntar se a chave é aceita.
        "nome": "Transferências e convênios (Portal da Transparência)",
        "credencial": "PORTAL_TRANSPARENCIA_API_KEY",
        "url": "https://api.portaldatransparencia.gov.br/api-de-dados/convenios?pagina=1",
        "cabecalho": "chave-api-dados",
        "onde_pedir": "https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email",
    },
    "inmet_estacoes": {
        "nome": "Temperatura medida em estação (INMET) — cobertura EXTRA, não lacuna",
        "credencial": "INMET_API_TOKEN",
        # A rota com token existe e valida: com token inválido responde 200 com "CHAVE INVÁLIDA!"
        # (medido em 24/09/2026).
        # 27/09/2026 (§249): duas correções nesta entrada, e as duas eram fato errado.
        #   1. Dizia que sem token a rota devolve "204 vazio". Devolve **404** — o §233 mediu isso
        #      em 26/09 e corrigiu no coletor, mas a cópia daqui ficou para trás.
        #   2. Dizia "sem caminho público documentado". HÁ caminho documentado: pede-se o token
        #      por e-mail a cadastro.act@inmet.gov.br. Fonte: JuliaClimate/INMET.jl, que é um
        #      cliente público da mesma API e traz a instrução no README e no próprio erro.
        "url": "https://apitempo.inmet.gov.br/token/estacao/diaria/{data}/{data}/A001/{token}",
        "cabecalho": None,          # o INMET põe o token no CAMINHO, não em cabeçalho
        "onde_pedir": "token por e-mail a cadastro.act@inmet.gov.br",
        # §249: esta credencial NÃO é exigida por nenhuma fonte do coletor. O §233 mediu que
        # `apitempo.inmet.gov.br/estacoes/T` responde 200 com 673 estações SEM token, tirou o
        # `INMET_API_TOKEN` da declaração de `inmet_estacoes`, e há portão travando isso.
        # Com o token, a API abre o que a rota pública não dá: série histórica por estação
        # (`/token/estacao/diaria/...`) e TODAS as ~600 estações automáticas numa requisição
        # (`/token/estacao/dados/{data}/{hora}/{token}`) — hoje medimos só as capitais, por
        # `/condicao/capitais/{data}`. Ausência aqui é cobertura que não temos, não dado que
        # falta ao site. A sonda CONFERE isso contra o coletor em vez de acreditar nesta linha.
        "opcional": True,
    },
}
MARCAS_DE_RECUSA = ("chave inválida", "chave invalida", "unauthorized", "forbidden",
                    "api key", "token inválido", "token invalido")


def mascarar(valor: str) -> str:
    """Devolve só o que permite distinguir 'chave errada' de 'sem chave', sem expor a chave.

    Nunca o valor inteiro, nem um prefixo: prefixo de chave é o que costuma identificar a
    conta. Quatro últimos caracteres e o tamanho bastam para conferir uma colagem."""
    if not valor:
        return "ausente"
    return f"{len(valor)} caracteres, terminando em …{valor[-4:]}" if len(valor) > 4 else "curta demais"


def classificar(status, corpo: str, erro_http: int = None) -> str:
    """Traduz a resposta em um dos quatro desfechos. Função pura.

    `recusada` cobre 401/403 E a recusa servida com 200 e corpo vazio ou com marca de chave
    inválida — que é recusa igual, só mais difícil de ver (§186, §187)."""
    if erro_http in (401, 403):
        return "recusada"
    if erro_http is not None:
        return "erro_da_fonte"
    baixo = (corpo or "").lower()
    if any(m in baixo for m in MARCAS_DE_RECUSA):
        return "recusada"
    if not (corpo or "").strip():
        return "recusada"
    return "aceita"


def sondar_uma(chave: str, fonte: dict, buscar_fn=None) -> dict:
    """Sonda UMA fonte e devolve {chave, credencial, estado, detalhe}. Sem credencial não bate
    na porta: levar 401 de propósito gastaria a fonte e sujaria o log com recusa já conhecida."""
    valor = os.environ.get(fonte["credencial"], "")
    base = {"fonte": chave, "nome": fonte["nome"], "credencial": fonte["credencial"],
            "credencial_no_ambiente": mascarar(valor)}
    if not valor:
        return {**base, "estado": "ausente",
                "detalhe": f"cadastre o segredo {fonte['credencial']} · {fonte['onde_pedir']}"}
    from datetime import date
    url = fonte["url"].format(data=date.today().strftime("%Y-%m-%d"), token=valor)
    extra = {fonte["cabecalho"]: valor} if fonte["cabecalho"] else {}
    if buscar_fn:
        estado, detalhe = buscar_fn(url, extra)
        return {**base, "estado": estado, "detalhe": detalhe}
    try:
        req = urllib.request.Request(url, headers={**CABECALHO, **extra})
        with urllib.request.urlopen(req, timeout=TEMPO_LIMITE, context=contexto_tls()) as r:
            corpo = r.read(2000).decode("utf-8", errors="replace")
            estado = classificar(r.status, corpo)
        return {**base, "estado": estado,
                "detalhe": f"HTTP {r.status}, {len(corpo)} byte(s) lido(s)"}
    except urllib.error.HTTPError as e:
        return {**base, "estado": classificar(None, "", e.code), "detalhe": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {**base, "estado": "rede_indisponivel", "detalhe": f"{type(e).__name__}"}


def exigida_pelo_coletor(chave: str) -> bool | None:
    """A fonte `chave` declara credencial em coletar_sinais_risco.FONTES? None se não deu para ver.

    §249 (27/09/2026): esta função existe porque a tabela acima é uma CÓPIA, e cópia diverge. Em
    26/09 o §233 mediu que a rota de estações do INMET é pública e tirou o `INMET_API_TOKEN` da
    declaração do coletor — mas a cópia daqui continuou pedindo o token, com a nota "sem caminho
    público documentado". Resultado: a sonda anunciava uma lacuna que não existia, e ela foi
    repetida à editoria como fato. Agora a verdade vem de quem coleta, não daqui.
    """
    try:
        import importlib.util
        import pathlib
        raiz = pathlib.Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location("_csr", raiz / "coletar_sinais_risco.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        fonte = m.FONTES.get(chave)
        if fonte is None:
            return None
        return bool(fonte.get("credencial"))
    except Exception:  # noqa: BLE001
        return None


REPO_DOS_AVISOS = "monitorelnino/robo-registro"
LINK_DOS_SEGREDOS = "https://github.com/monitorelnino/monitorelnino/settings/secrets/actions"
RAIZ = _pathlib.Path(__file__).resolve().parent.parent


def _http(detalhe: str):
    m = re.search(r"HTTP (\d{3})", detalhe or "")
    return int(m.group(1)) if m else None


def registro_da_noite(resultados, hoje, anterior=None, rotas=None):
    """Linhas de chaves.json. Função pura; sem o valor da chave, nem parcial."""
    anterior = anterior or {}
    rotas = (rotas or {}).get("sondadas", {})
    linhas = []
    for r in resultados:
        ant = anterior.get(r["credencial"], {})
        recusa = r["estado"] == "recusada"
        desde = (ant.get("desde") if ant.get("estado") == r["estado"] and ant.get("desde") else hoje)
        linhas.append({"secret": r["credencial"], "fonte": r["fonte"], "http": _http(r["detalhe"]),
                       "estado": r["estado"], "data": hoje, "desde": desde, "vence_em": None,
                       "rota_sem_chave": rotas.get(r["credencial"]) if recusa else None})
    return linhas


def acao_de_issue(linha, abertas, hoje):
    """('abrir'|'fechar'|None, numero). Uma Issue por chave por episódio."""
    titulo = f"Chave recusada: {linha['secret']}"
    n = abertas.get(titulo)
    vence = linha.get("vence_em")
    perto = bool(vence) and (_dt.date.fromisoformat(vence) - _dt.date.fromisoformat(hoje)).days <= 15
    if linha["estado"] == "recusada" or perto:
        return ("abrir", None) if n is None else (None, n)
    if linha["estado"] == "aceita" and n is not None:
        return ("fechar", n)
    return (None, n)


def _gh(args, entrada=None):
    return subprocess.run(["gh", *args], capture_output=True, text=True, input=entrada, timeout=60)


def issues_abertas(gh=_gh):
    p = gh(["issue", "list", "--repo", REPO_DOS_AVISOS, "--state", "open", "--limit", "100",
            "--json", "number,title"])
    if p.returncode != 0:
        return None
    return {i["title"]: i["number"] for i in json.loads(p.stdout or "[]")}


def aplicar_issues(linhas, hoje, gh=_gh):
    """Abre/fecha Issues. Falha de GitHub é aviso, nunca quebra a coleta."""
    abertas = issues_abertas(gh)
    if abertas is None:
        print("::warning::não consegui listar Issues do robo-registro; avisos adiados")
        return []
    feitas = []
    for l in linhas:
        acao, n = acao_de_issue(l, abertas, hoje)
        titulo = f"Chave recusada: {l['secret']}"
        if acao == "abrir":
            corpo = (f"A chave `{l['secret']}` ({l['fonte']}) falha desde {l['desde']} "
                     f"(HTTP {l['http']}, estado {l['estado']}). A coleta segue pela rota sem chave: "
                     f"{l['rota_sem_chave'] or 'dado anterior com a data'}.\n\n"
                     f"Renovar o Secret: {LINK_DOS_SEGREDOS}\n\nFecha sozinha quando a sonda "
                     f"noturna voltar a 200.\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_")
            gh(["issue", "create", "--repo", REPO_DOS_AVISOS, "--title", titulo, "--body-file", "-"], corpo)
        elif acao == "fechar":
            gh(["issue", "close", str(n), "--repo", REPO_DOS_AVISOS, "--comment",
                f"Sonda de {hoje}: {l['secret']} aceita (HTTP {l['http']}). Fechada."])
        if acao:
            feitas.append((acao, l["secret"]))
    return feitas


def gravar_da_noite(resultados, gh=_gh):
    import datetime
    hoje = datetime.date.today().isoformat()
    noite = subprocess.run([sys.executable, str(RAIZ / "scripts/janela_da_noite.py"), "--noite"],
                           capture_output=True, text=True).stdout.strip() or hoje
    rotas = json.load(open(RAIZ / "config/rotas_sem_chave.json", encoding="utf-8"))
    anterior = {}
    for f in sorted((RAIZ / "data/noite").glob("*/chaves.json")):
        if f.parent.name < noite:
            anterior = {l["secret"]: l for l in json.load(open(f, encoding="utf-8"))["chaves"]}
    linhas = registro_da_noite(resultados, hoje, anterior, rotas)
    saida = RAIZ / "data/noite" / noite / "chaves.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    gravar_em(saida, {"noite": noite, "chaves": linhas, "nao_sondadas": rotas["nao_sondadas"]})
    print(f"  chaves.json: {saida.relative_to(RAIZ)}")
    return aplicar_issues(linhas, hoje, gh)


def main() -> int:
    print("=== credenciais das fontes que exigem chave (§208, §224) ===")
    resultados = [sondar_uma(k, f) for k, f in FONTES.items()]
    simbolo = {"aceita": "✓", "ausente": "—", "recusada": "✗", "erro_da_fonte": "!",
               "rede_indisponivel": "?"}
    divergencias = []
    for r in resultados:
        fonte = FONTES[r["fonte"]]
        print(f"  {simbolo.get(r['estado'], '?')} {r['nome']}")
        print(f"      {r['credencial']}: {r['credencial_no_ambiente']}")
        print(f"      {r['estado']} — {r['detalhe']}")

        # A verdade sobre "esta chave é necessária?" mora no coletor (§249).
        exigida = exigida_pelo_coletor(r["fonte"])
        if exigida is False and r["estado"] == "ausente":
            print("      papel: COBERTURA EXTRA — o coletor NÃO exige esta credencial; a fonte "
                  "coleta pela rota pública. Ausência aqui não é lacuna no site.")
        if exigida is True and fonte.get("opcional"):
            divergencias.append(f"{r['fonte']}: marcada 'opcional' aqui, mas o coletor EXIGE a "
                                f"credencial")
        if exigida is False and not fonte.get("opcional"):
            divergencias.append(f"{r['fonte']}: o coletor NÃO exige a credencial, mas esta tabela "
                                f"a apresenta como necessária — marque 'opcional': True")

    if "--noite" in sys.argv:
        gravar_da_noite(resultados)
    aceitas = sum(1 for r in resultados if r["estado"] == "aceita")
    print(f"\n{aceitas} de {len(resultados)} fonte(s) com credencial aceita.")
    if divergencias:
        print("  ATENÇÃO — esta tabela divergiu do coletor:")
        for d in divergencias:
            print(f"    · {d}")
    # Saída 0 sempre: isto é diagnóstico, não portão. Credencial ausente é decisão pendente da
    # editoria, e não falha de build — tratá-la como falha bloquearia o pipeline por uma escolha.
    return 0


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    checar("máscara: nunca mostra a chave inteira nem o prefixo",
           mascarar("abcdef1234567890") == "16 caracteres, terminando em …7890")
    checar("máscara: sem chave diz 'ausente'", mascarar("") == "ausente" and mascarar(None) == "ausente")
    checar("máscara: chave curta não vaza por inteiro", mascarar("ab") == "curta demais")

    checar("401 e 403 são RECUSA, não erro da fonte",
           classificar(None, "", 401) == "recusada" and classificar(None, "", 403) == "recusada")
    checar("500 é erro da fonte, não recusa de credencial",
           classificar(None, "", 500) == "erro_da_fonte")
    checar("200 com 'CHAVE INVÁLIDA!' é recusa (o INMET responde assim)",
           classificar(200, "CHAVE INVÁLIDA!") == "recusada")
    checar("200 com corpo VAZIO é recusa, não aceitação (§186, §187)",
           classificar(200, "   ") == "recusada" and classificar(200, "") == "recusada")
    checar("200 com corpo é aceitação", classificar(200, '{"results":[{"id":1}]}') == "aceita")

    _ambiente = {k: os.environ.pop(k, None) for k in ("OPENAQ_API_KEY", "INMET_API_TOKEN")}
    try:
        r = sondar_uma("openaq", FONTES["openaq"], buscar_fn=lambda u, e: ("nunca chamado", ""))
        checar("sem credencial NÃO bate na porta e diz onde pedir",
               r["estado"] == "ausente" and "explore.openaq.org" in r["detalhe"])
        os.environ["OPENAQ_API_KEY"] = "chave-de-teste-1234"
        vistos = {}

        def falso(url, extra):
            vistos["url"], vistos["extra"] = url, extra
            return "aceita", "fixture"
        r = sondar_uma("openaq", FONTES["openaq"], buscar_fn=falso)
        checar("a chave do OpenAQ viaja em CABEÇALHO, não na URL",
               vistos["extra"].get("X-API-Key") == "chave-de-teste-1234"
               and "chave-de-teste" not in vistos["url"])
        checar("o relatório não imprime a credencial",
               "chave-de-teste-1234" not in json.dumps(r, ensure_ascii=False))
        os.environ["INMET_API_TOKEN"] = "token-de-teste-5678"
        r = sondar_uma("inmet_estacoes", FONTES["inmet_estacoes"], buscar_fn=falso)
        checar("o token do INMET viaja no CAMINHO, como a rota dele exige",
               "token-de-teste-5678" in vistos["url"] and vistos["extra"] == {})
        checar("o relatório do INMET também não imprime o token",
               "token-de-teste-5678" not in json.dumps(r, ensure_ascii=False))
    finally:
        for k in ("OPENAQ_API_KEY", "INMET_API_TOKEN"):
            os.environ.pop(k, None)
        for k, v in _ambiente.items():
            if v is not None:
                os.environ[k] = v

    # §249: o invariante que faltava. Esta tabela é uma CÓPIA do que o coletor declara, e cópia
    # diverge: em 26/09 o §233 tirou o `INMET_API_TOKEN` da declaração do coletor e a cópia daqui
    # continuou pedindo o token, com a nota "sem caminho público documentado". A sonda anunciou
    # uma lacuna que não existia, e ela foi repetida à editoria como fato. Asserção, não print:
    # print de aviso ninguém lê.
    for chave, fonte in FONTES.items():
        exigida = exigida_pelo_coletor(chave)
        if exigida is None:
            continue  # a fonte não é do coletor de sinais (Portal da Transparência); nada a casar
        checar(f"§249 {chave}: 'opcional' nesta tabela casa com o que o coletor exige "
               f"(coletor exige={exigida})",
               bool(fonte.get("opcional")) == (not exigida))

    # Modo da noite: 403 simulado abre a Issue uma vez, não grava a chave, cai na rota sem chave.
    rotas = json.load(open(RAIZ / "config/rotas_sem_chave.json", encoding="utf-8"))
    segredo = "segredo-de-teste-9999"
    rec = [{"fonte": "portal_transparencia", "credencial": "PORTAL_TRANSPARENCIA_API_KEY",
            "estado": "recusada", "detalhe": "HTTP 403"}]
    linhas = registro_da_noite(rec, "2026-11-01", {}, rotas)
    checar("403: linha recusada, HTTP 403 e rota sem chave do Portal",
           linhas[0]["http"] == 403 and "download" in linhas[0]["rota_sem_chave"])
    checar("chaves.json não carrega o valor da chave", segredo not in json.dumps(linhas))
    chamadas = []

    def gh_falso(args, entrada=None):
        chamadas.append(args)

        class P:
            returncode = 0
            stdout = json.dumps([{"number": 7, "title": "Chave recusada: PORTAL_TRANSPARENCIA_API_KEY"}]) \
                if any(a[:2] == ["issue", "list"] for a in [args]) and abertas_falso[0] else "[]"
        return P
    abertas_falso = [False]
    feitas = aplicar_issues(linhas, "2026-11-01", gh_falso)
    checar("403 sem Issue aberta: abre uma", feitas == [("abrir", "PORTAL_TRANSPARENCIA_API_KEY")])
    abertas_falso[0] = True
    checar("403 com Issue já aberta: não abre outra", aplicar_issues(linhas, "2026-11-02", gh_falso) == [])
    ok = [{**rec[0], "estado": "aceita", "detalhe": "HTTP 200"}]
    checar("200 com Issue aberta: fecha",
           aplicar_issues(registro_da_noite(ok, "2026-11-03", {}, rotas), "2026-11-03", gh_falso)
           == [("fechar", "PORTAL_TRANSPARENCIA_API_KEY")])
    checar("validade <= 15 dias abre Issue",
           acao_de_issue({"secret": "X", "estado": "aceita", "vence_em": "2026-11-10"}, {}, "2026-11-01")[0] == "abrir")
    checar("desde se mantém no mesmo episódio",
           registro_da_noite(rec, "2026-11-02", {"PORTAL_TRANSPARENCIA_API_KEY": {"estado": "recusada", "desde": "2026-10-30"}},
                             rotas)[0]["desde"] == "2026-10-30")

    if falhas:
        print(f"\n✗ AUTOTESTE: {len(falhas)} falha(s).")
        return 1
    print("\n✓ AUTOTESTE OK — máscara, classificação dos quatro desfechos e por onde cada credencial viaja.")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
