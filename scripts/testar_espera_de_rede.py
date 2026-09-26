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
    }))
