#!/usr/bin/env python3
"""Autoteste da espera de rede compartilhada (§226, 26/09/2026).

POR QUE ESTE PORTÃO EXISTE. Em 25/09/2026 uma varredura nacional mediu que **63 dos 505
primeiros municípios** viraram lacuna declarada por `HTTP 503 Service Unavailable` — 12 %, e
nenhum deles bloqueio de acesso. A correção foi escrita no dia seguinte, e ficou dentro de
`coletar_diarios_municipais.py`: os outros quinze coletores continuaram chamando `buscar()`
direto e desistindo na primeira tentativa. Indisponibilidade temporária é a fonte dizendo
"tente mais tarde", e a resposta certa a isso é tentar mais tarde — em todo coletor, não em um.

O QUE ELE TRAVA, e a razão de cada trava:
  · repetir onde repetir ajuda (429 e 5xx) e NÃO repetir onde não ajuda (4xx);
  · **403 e 451 nunca repetem.** Bloqueio de acesso real se respeita, sempre (CLAUDE.md). Este é
    o teste mais importante do arquivo: uma política de repetição escrita sem cuidado vira
    insistência contra uma fonte que disse não, e isso o projeto proíbe;
  · muro de robô (recusa servida com 200, §186) não repete: não houve erro HTTP para repetir,
    houve recusa, e repetir seria insistir contra ela;
  · a política vive num lugar só. Uma segunda cópia das esperas é exatamente o defeito do §213
    (vocabulário do log em três arquivos) e do §222 (canais em dois) — de novo, agora em rede.

Tudo sem rede e sem esperar de verdade: o transporte e o relógio são injetados.
"""
import ast
import pathlib
import sys
import urllib.error

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import coletores_base as cb  # noqa: E402
from coletores_base import rodar_autoteste  # noqa: E402


def _que_falha(codigos, corpo=b"ok"):
    """Transporte falso que levanta os `codigos` em sequência e depois entrega `corpo`.
    Devolve (fn, tentativas)."""
    pendentes, tentativas = list(codigos), []

    def fn(url, timeout=None):
        tentativas.append(url)
        if pendentes:
            raise urllib.error.HTTPError(url, pendentes.pop(0), "erro", None, None)
        return corpo

    return fn, tentativas


def t_esperas_para_e_pura():
    """A tabela de esperas por status, sem surpresa e sem rede."""
    return (cb.esperas_para(429) == (30,)
            and cb.esperas_para(500) == cb.esperas_para(502) == (5, 15)
            and cb.esperas_para(503) == cb.esperas_para(504) == (5, 15)
            and cb.esperas_para(400) == cb.esperas_para(404) == ()
            and cb.esperas_para(200) == ())


def t_5xx_transitorio_entrega_na_repeticao():
    """O caso medido em 25/09: 503 duas vezes, conteúdo na terceira. Três tentativas, esperas
    crescentes, e o município NÃO vira lacuna."""
    fn, tentativas = _que_falha([503, 503])
    esperas = []
    return (cb.buscar("u", buscar_fn=fn, dormir=esperas.append) == b"ok"
            and len(tentativas) == 3 and esperas == [5, 15])


def t_5xx_persistente_desiste_e_sobe():
    """Fonte fora do ar de verdade: esgota as esperas e LEVANTA, para virar lacuna declarada com
    o código real. Repetir para sempre seria carga indevida sobre serviço público."""
    fn, tentativas = _que_falha([503, 503, 503, 503])
    esperas = []
    try:
        cb.buscar("u", buscar_fn=fn, dormir=esperas.append)
        return False
    except urllib.error.HTTPError as e:
        return e.code == 503 and len(tentativas) == 3 and esperas == [5, 15]


def t_4xx_sobe_na_hora():
    """Consulta errada não melhora com repetição, e repetir dobraria a carga sobre APIs públicas
    mantidas por projetos sem fins lucrativos."""
    for codigo in (400, 404, 410, 422):
        fn, tentativas = _que_falha([codigo] * 5)
        try:
            cb.buscar("u", buscar_fn=fn, dormir=lambda s: (_ for _ in ()).throw(AssertionError("dormiu")))
            return False
        except urllib.error.HTTPError as e:
            if e.code != codigo or len(tentativas) != 1:
                return False
    return True


def t_bloqueio_real_nunca_repete():
    """A trava que mais importa: 401, 403 e 451 são recusa, não indisponibilidade. Uma tentativa,
    nenhuma espera, nenhuma insistência — CLAUDE.md, e §187."""
    for codigo in (401, 403, 451):
        fn, tentativas = _que_falha([codigo] * 5)
        dormiu = []
        try:
            cb.buscar("u", buscar_fn=fn, dormir=dormiu.append)
            return False
        except urllib.error.HTTPError as e:
            if e.code != codigo or len(tentativas) != 1 or dormiu:
                return False
    return True


def t_429_espera_o_que_a_fonte_pede_e_repete_uma_vez():
    """Limite de taxa é a fonte mandando esperar. Respeitar é honrar a espera — nem desistir na
    hora, nem insistir sem parar: uma repetição, depois de 30 s."""
    fn, tentativas = _que_falha([429])
    esperas = []
    entregou = cb.buscar("u", buscar_fn=fn, dormir=esperas.append) == b"ok"
    fn2, tentativas2 = _que_falha([429, 429, 429])
    esperas2 = []
    try:
        cb.buscar("u", buscar_fn=fn2, dormir=esperas2.append)
        return False
    except urllib.error.HTTPError:
        return (entregou and len(tentativas) == 2 and esperas == [30]
                and len(tentativas2) == 2 and esperas2 == [30])


def t_muro_de_robo_nao_repete():
    """Recusa servida com 200 (§186) não é erro HTTP: levanta MuroDeRobo na primeira tentativa,
    sem espera. Repetir seria insistir contra uma recusa."""
    tentativas, dormiu = [], []

    def fn(url, timeout=None):
        tentativas.append(url)
        raise cb.MuroDeRobo(url, "pardon our interruption")

    try:
        cb.buscar("u", buscar_fn=fn, dormir=dormiu.append)
        return False
    except cb.MuroDeRobo:
        return len(tentativas) == 1 and not dormiu


def t_sucesso_faz_um_pedido_so():
    """Negativo do caminho feliz: sem erro, uma tentativa e nenhuma espera. A repetição não pode
    custar nada quando a fonte responde."""
    fn, tentativas = _que_falha([])
    dormiu = []
    return cb.buscar("u", buscar_fn=fn, dormir=dormiu.append) == b"ok" and len(tentativas) == 1 and not dormiu


def t_politica_vive_num_lugar_so():
    """§213 e §222 de novo: nenhum coletor mantém cópia das esperas. A trava é por atribuição no
    código-fonte — `ESPERAS_429 = ...` fora de coletores_base é a cópia que envelhece."""
    for arq in sorted(RAIZ.glob("coletar_*.py")) + sorted(RAIZ.glob("atualizar*.py")):
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign) and any(
                    isinstance(d, ast.Name) and d.id in ("ESPERAS_429", "ESPERAS_5XX")
                    for d in no.targets):
                print(f"    cópia da política de espera em {arq.name}:{no.lineno}")
                return False
    return True


def t_buscar_uma_vez_continua_existindo():
    """A tentativa única segue disponível por nome, para sonda e diagnóstico que precisam do
    status cru da fonte sem gastar duas repetições."""
    return callable(getattr(cb, "buscar_uma_vez", None))


def t_conexao_transitoria_entrega_na_repeticao():
    """O caso medido em 24/09/2026: 105 leituras de PDF falharam com `URLError` num dia nos sítios
    de defesa civil de SE e AM. Testados em 26/09, sem mudança de código, os documentos da amostra
    responderam na hora — 5,8 MB, 642 kB e 7,7 MB de PDF válido. Não era fonte fora do ar; era uma
    tarde ruim de rede tratada como ausência de documento."""
    tentativas, esperas = [], []

    def fn(url, timeout=None):
        tentativas.append(url)
        if len(tentativas) < 2:
            raise urllib.error.URLError("conexão reiniciada")
        return b"%PDF-1.4 documento"

    return (cb.buscar("u", buscar_fn=fn, dormir=esperas.append).startswith(b"%PDF")
            and len(tentativas) == 2 and esperas == [5])


def t_conexao_morta_repete_uma_vez_so():
    """Host realmente fora do ar paga a espera em CADA url de uma varredura, e uma varredura tem
    milhares. Por isso a conexão repete UMA vez, e não duas como o 5xx: cinco segundos por url
    morta é aceitável, vinte não."""
    tentativas, esperas = [], []

    def fn(url, timeout=None):
        tentativas.append(url)
        raise urllib.error.URLError("nome não resolve")

    try:
        cb.buscar("u", buscar_fn=fn, dormir=esperas.append)
        return False
    except urllib.error.URLError:
        return len(tentativas) == 2 and esperas == [5]


def t_httperror_nao_cai_no_ramo_de_conexao():
    """`HTTPError` é subclasse de `URLError`. Se a ordem dos `except` invertesse, TODO status
    passaria a ser tratado como erro de conexão e o projeto perderia a distinção entre recusa e
    indisponibilidade — 403 ganharia uma repetição que a política proíbe."""
    for codigo, esperado in ((403, []), (503, [5, 15]), (429, [30])):
        fn, tentativas = _que_falha([codigo] * 6)
        esperas = []
        try:
            cb.buscar("u", buscar_fn=fn, dormir=esperas.append)
            return False
        except urllib.error.HTTPError:
            if esperas != esperado:
                return False
    return True


def t_timeout_repete_como_conexao():
    """Timeout é a conexão que não completou, não resposta da fonte: mesma política da conexão."""
    tentativas, esperas = [], []

    def fn(url, timeout=None):
        tentativas.append(url)
        if len(tentativas) < 2:
            raise TimeoutError("tempo esgotado")
        return b"ok"

    return cb.buscar("u", buscar_fn=fn, dormir=esperas.append) == b"ok" and esperas == [5]


def t_connectionerror_e_incompleteread_repetem_como_conexao():
    """A6-08: reset no meio da leitura e corpo cortado são a conexão que não completou. Repetem
    como URLError — uma vez, depois de 5 s — e sobem com o próprio tipo se persistirem."""
    import http.client
    for erro in (ConnectionResetError("reset"), http.client.IncompleteRead(b"meio", 10)):
        tentativas, esperas = [], []

        def fn(url, timeout=None, erro=erro):
            tentativas.append(url)
            if len(tentativas) < 2:
                raise erro
            return b"ok"

        if not (cb.buscar("u", buscar_fn=fn, dormir=esperas.append) == b"ok" and esperas == [5]):
            return False
        tentativas2, esperas2 = [], []

        def morto(url, timeout=None, erro=erro):
            tentativas2.append(url)
            raise erro
        try:
            cb.buscar("u", buscar_fn=morto, dormir=esperas2.append)
            return False
        except type(erro):
            if len(tentativas2) != 2 or esperas2 != [5]:
                return False
    return True


def _http_com_retry_after(codigo, valor):
    import email.message
    cab = email.message.Message()
    if valor is not None:
        cab["Retry-After"] = valor
    return urllib.error.HTTPError("u", codigo, "erro", cab, None)


def t_retry_after_e_respeitado_com_teto():
    """A6-25: 429/503 com `Retry-After` em segundos esperam o que a fonte pede, com teto de 120 s;
    sem cabeçalho, ou com data HTTP, fica a espera da tabela. O número de tentativas não muda."""
    if not (cb.retry_after_segundos(_http_com_retry_after(429, "45")) == 45
            and cb.retry_after_segundos(_http_com_retry_after(503, "9999")) == cb.RETRY_AFTER_TETO == 120
            and cb.retry_after_segundos(_http_com_retry_after(503, "Wed, 21 Oct 2026 07:28:00 GMT")) is None
            and cb.retry_after_segundos(_http_com_retry_after(503, None)) is None
            and cb.retry_after_segundos(_http_com_retry_after(500, "45")) is None):
        return False
    for codigo, valor, esperado in ((429, "45", [45]), (503, "7", [7, 7]), (503, "600", [120, 120]),
                                    (503, None, [5, 15])):
        tentativas, esperas = [], []

        def fn(url, timeout=None, codigo=codigo, valor=valor):
            tentativas.append(url)
            raise _http_com_retry_after(codigo, valor)
        try:
            cb.buscar("u", buscar_fn=fn, dormir=esperas.append)
            return False
        except urllib.error.HTTPError:
            if esperas != esperado or len(tentativas) != len(esperado) + 1:
                print(f"    {codigo} {valor}: esperas {esperas}")
                return False
    return True


def t_corpo_vazio_com_200_nao_e_conteudo():
    """A6-25: 200 sem corpo não é documento. `buscar_uma_vez` levanta CorpoVazio (sem rede: o
    urlopen e o robots são falsos), e a espera o trata como conexão — repete uma vez."""
    import contextlib
    if cb.exigir_corpo("u", 200, b"x") != b"x" or cb.exigir_corpo("u", 204, b"") != b"":
        return False

    class Resp:
        status = 200
        headers = {}

        def read(self):
            return b""

    host = "vazio.exemplo.invalid"
    salvo_urlopen, salvo_cache = cb.urllib.request.urlopen, cb._ROBOTS_CACHE.get(host)
    cb._ROBOTS_CACHE[host] = {"status": "sem_robots", "crawl_delay": None, "rp": None}
    cb.urllib.request.urlopen = lambda *a, **k: contextlib.nullcontext(Resp())
    try:
        cb.buscar_uma_vez(f"https://{host}/doc")
        return False
    except cb.CorpoVazio:
        pass
    finally:
        cb.urllib.request.urlopen = salvo_urlopen
        if salvo_cache is None:
            cb._ROBOTS_CACHE.pop(host, None)
    tentativas, esperas = [], []

    def fn(url, timeout=None):
        tentativas.append(url)
        if len(tentativas) < 2:
            raise cb.CorpoVazio(url)
        return b"ok"
    return cb.buscar("u", buscar_fn=fn, dormir=esperas.append) == b"ok" and esperas == [5]


def t_lacuna_de_httperror_leva_o_codigo():
    """A6-14: coletor que registra `type(e).__name__` de um HTTPError gravava só "HTTPError". O
    ponto central é `registrar_lacuna`: dentro do except, o código entra no motivo. Sem escrever
    no log — `log_busca` é trocado por um falso durante o teste."""
    e503 = urllib.error.HTTPError("u", 503, "Service Unavailable", None, None)
    if not (cb.motivo_com_codigo_http("HTTPError", e503) == "HTTPError 503"
            and cb.motivo_com_codigo_http("HTTPError: HTTP Error 503: x", e503) == "HTTPError: HTTP Error 503: x"
            and cb.motivo_com_codigo_http("URLError", e503) == "URLError"
            and cb.motivo_com_codigo_http("HTTPError", None) == "HTTPError"):
        return False
    gravados = []
    salvo = cb.log_busca
    cb.log_busca = lambda *a, **k: gravados.append(k.get("resultados"))
    try:
        try:
            raise e503
        except urllib.error.HTTPError as e:
            cb.registrar_lacuna("Fonte X", type(e).__name__, canal="DOU", camada=1)
        cb.registrar_lacuna("Fonte Y", "HTTPError", canal="DOU", camada=1)   # fora do except
    finally:
        cb.log_busca = salvo
    return gravados == ["Fonte X: HTTPError 503", "Fonte Y: HTTPError"]


if __name__ == "__main__":
    sys.exit(rodar_autoteste({
        "tabela de esperas por status é pura": t_esperas_para_e_pura,
        "503 transitório entrega na repetição (o caso medido em 25/09)": t_5xx_transitorio_entrega_na_repeticao,
        "5xx persistente esgota as esperas e sobe com o código real": t_5xx_persistente_desiste_e_sobe,
        "negativo: 4xx sobe na hora, sem espera": t_4xx_sobe_na_hora,
        "bloqueio real (401, 403, 451) nunca repete": t_bloqueio_real_nunca_repete,
        "429 espera o que a fonte pede e repete uma vez": t_429_espera_o_que_a_fonte_pede_e_repete_uma_vez,
        "negativo: muro de robô não repete": t_muro_de_robo_nao_repete,
        "negativo: sucesso faz um pedido só e não dorme": t_sucesso_faz_um_pedido_so,
        "a política de espera vive num lugar só (§213, §222)": t_politica_vive_num_lugar_so,
        "buscar_uma_vez continua disponível para sonda": t_buscar_uma_vez_continua_existindo,
        "conexão transitória entrega na repetição (os 105 PDFs de 24/09)": t_conexao_transitoria_entrega_na_repeticao,
        "conexão morta repete UMA vez só — custo de varredura": t_conexao_morta_repete_uma_vez_so,
        "HTTPError não cai no ramo de conexão (ordem dos except)": t_httperror_nao_cai_no_ramo_de_conexao,
        "timeout repete como conexão, não como resposta da fonte": t_timeout_repete_como_conexao,
        "ConnectionError e IncompleteRead repetem como conexão (A6-08)": t_connectionerror_e_incompleteread_repetem_como_conexao,
        "Retry-After de 429/503 é respeitado, com teto de 120 s (A6-25)": t_retry_after_e_respeitado_com_teto,
        "negativo: 200 com corpo vazio não é conteúdo (A6-25)": t_corpo_vazio_com_200_nao_e_conteudo,
        "lacuna de HTTPError leva o código (A6-14)": t_lacuna_de_httperror_leva_o_codigo,
    }))
