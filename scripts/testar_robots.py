#!/usr/bin/env python3
"""Autoteste da camada de robots.txt (§185, 23/09/2026): leitura, ritmo e rastro.

A regra é decisão da editoria: o Monitor LÊ o robots.txt, RESPEITA o Crawl-delay, ACESSA
documento público mesmo contra o pedido do robots — com cliente identificado — e DEIXA RASTRO.
Estes testes travam cada uma das quatro partes, sem rede: o robots.txt é injetado, o relógio é
falso e o registro vai para um diretório temporário. São negativos por construção: o teste que
importa mais é o do rastro — acesso contra o robots sem registro é o que a política proíbe.
"""
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import coletores_base as cb  # noqa: E402
from coletores_base import rodar_autoteste  # noqa: E402

ROBOTS_MT = """User-agent: Googlebot
Disallow:
Allow: /inicio
Crawl-delay: 10

User-agent: *
Disallow: /
Disallow: /web/
Crawl-delay: 30

Sitemap: http://www.defesacivil.mt.gov.br/sitemap.xml
"""
ROBOTS_LIVRE = "User-agent: *\nDisallow:\n"
ROBOTS_SO_NOS = f"User-agent: {cb.UA.split('/')[0]}\nDisallow: /\n\nUser-agent: *\nDisallow:\n"


def _limpo():
    cb._ROBOTS_CACHE.clear()
    cb._ULTIMO_ACESSO.clear()


def t_le_o_grupo_que_nos_alcanca():
    """O grupo '*' vale para nós quando não há grupo com o nosso nome (RFC 9309 § 2.2.1)."""
    _limpo()
    r = cb.robots_de("mt.exemplo", lambda h, timeout=0: (200, ROBOTS_MT))
    return r["status"] == "proibe" and r["crawl_delay"] == 30.0 and cb.robots_permite("mt.exemplo", "https://mt.exemplo/plano.pdf") is False


def t_grupo_com_nosso_nome_prevalece():
    _limpo()
    r = cb.robots_de("x.exemplo", lambda h, timeout=0: (200, ROBOTS_SO_NOS))
    return r["status"] == "proibe"


def t_sem_robots_e_sem_restricao():
    """4xx no robots.txt = sem restrição (RFC 9309 § 2.3.1); indeterminado quando não respondeu."""
    _limpo()
    a = cb.robots_de("a.exemplo", lambda h, timeout=0: (404, ""))
    b = cb.robots_de("b.exemplo", lambda h, timeout=0: (None, ""))
    return a["status"] == "sem_robots" and cb.robots_permite("a.exemplo", "https://a.exemplo/") is None \
        and b["status"] == "indeterminado"


def t_le_uma_vez_por_host():
    _limpo()
    chamadas = []
    def ler(h, timeout=0):
        chamadas.append(h); return 200, ROBOTS_LIVRE
    cb.robots_de("c.exemplo", ler); cb.robots_de("c.exemplo", ler)
    return chamadas == ["c.exemplo"]


def t_crawl_delay_e_respeitado():
    """Segundo acesso ao mesmo host espera o que o sítio pediu; sem pedido, não espera."""
    _limpo()
    dormiu = []
    cb._respeitar_ritmo("mt.exemplo", 30.0, dormir=dormiu.append)
    cb._respeitar_ritmo("mt.exemplo", 30.0, dormir=dormiu.append)
    cb._respeitar_ritmo("livre.exemplo", None, dormir=dormiu.append)
    return len(dormiu) == 1 and 29.0 < dormiu[0] <= 30.0


def t_crawl_delay_tem_teto():
    _limpo()
    r = cb.robots_de("lento.exemplo", lambda h, timeout=0: (200, "User-agent: *\nCrawl-delay: 3600\n"))
    return r["crawl_delay"] == cb.CRAWL_DELAY_MAXIMO


def t_acesso_contra_robots_deixa_rastro():
    """A parte que a política exige: acessar onde o robots pediu que não, SEM registro, é proibido."""
    _limpo()
    real = cb.DATA
    with tempfile.TemporaryDirectory() as d:
        try:
            cb.DATA = pathlib.Path(d)
            cb.robots_de("mt.exemplo", lambda h, timeout=0: (200, ROBOTS_MT))
            cb.registrar_acesso_contra_robots("mt.exemplo", "https://mt.exemplo/plano.pdf", "teste")
            cb.registrar_acesso_contra_robots("mt.exemplo", "https://mt.exemplo/plano2.pdf", "teste")
            reg = cb.ler(cb.ROBOTS_REGISTRO)
            h = reg["hosts"]["mt.exemplo"]
            return (h["total_acessos"] == 2 and len(h["acessos"]) == 2
                    and h["status_robots"] == "proibe" and h["crawl_delay"] == 30.0
                    and h["acessos"][0]["url"].endswith("plano.pdf")
                    and h["acessos"][0]["cliente"].startswith("MonitorElNino")
                    and "quando" in h["acessos"][0])
        finally:
            cb.DATA = real
            _limpo()


def t_rastro_guarda_os_ultimos_200_mas_conta_todos():
    _limpo()
    real = cb.DATA
    with tempfile.TemporaryDirectory() as d:
        try:
            cb.DATA = pathlib.Path(d)
            cb.robots_de("mt.exemplo", lambda h, timeout=0: (200, ROBOTS_MT))
            for i in range(205):
                cb.registrar_acesso_contra_robots("mt.exemplo", f"https://mt.exemplo/{i}.pdf", "teste")
            h = cb.ler(cb.ROBOTS_REGISTRO)["hosts"]["mt.exemplo"]
            return h["total_acessos"] == 205 and len(h["acessos"]) == 200
        finally:
            cb.DATA = real
            _limpo()


def t_cliente_nunca_e_disfarcado():
    """O UA do projeto se nomeia e aponta o sítio; não imita navegador nem Googlebot."""
    ua = cb.UA.lower()
    return ua.startswith("monitorelnino") and "monitorelnino.com.br" in ua \
        and "mozilla" not in ua and "googlebot" not in ua


def t_canal_renderizado_tambem_deixa_rastro():
    """O navegador não passa por buscar(): o rastro do render tem de ser deixado pelo lado Python.
    Sem isto, a política teria rastro só do canal HTTP — que é o que menos precisa dele."""
    import ast
    fonte = (RAIZ / "descobrir_planos.py").read_text(encoding="utf-8")
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.FunctionDef) and no.name == "descobrir_renderizado":
            corpo = ast.get_source_segment(fonte, no) or ""
            return "robots_permite(" in corpo and "registrar_acesso_contra_robots(" in corpo
    return False


def t_buscar_declara_a_regra_no_codigo():
    """buscar() precisa consultar robots_de e registrar o acesso contra o robots — pela fonte."""
    import ast
    fonte = (RAIZ / "coletores_base.py").read_text(encoding="utf-8")
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.FunctionDef) and no.name == "buscar":
            corpo = ast.get_source_segment(fonte, no) or ""
            return "robots_de(" in corpo and "_respeitar_ritmo(" in corpo and "registrar_acesso_contra_robots(" in corpo
    return False


if __name__ == "__main__":
    sys.exit(rodar_autoteste({
        "lê o grupo '*' quando não há grupo com o nosso nome": t_le_o_grupo_que_nos_alcanca,
        "grupo com o nosso nome prevalece sobre '*'": t_grupo_com_nosso_nome_prevalece,
        "4xx no robots = sem restrição; sem resposta = indeterminado": t_sem_robots_e_sem_restricao,
        "lê o robots uma vez por host": t_le_uma_vez_por_host,
        "Crawl-delay é respeitado entre acessos ao mesmo host": t_crawl_delay_e_respeitado,
        "Crawl-delay tem teto": t_crawl_delay_tem_teto,
        "acesso contra o robots deixa rastro com URL, data, origem e cliente": t_acesso_contra_robots_deixa_rastro,
        "rastro guarda os 200 últimos e conta todos": t_rastro_guarda_os_ultimos_200_mas_conta_todos,
        "o cliente nunca é disfarçado": t_cliente_nunca_e_disfarcado,
        "buscar() consulta o robots, respeita o ritmo e registra": t_buscar_declara_a_regra_no_codigo,
        "o canal renderizado também deixa rastro": t_canal_renderizado_tambem_deixa_rastro,
    }))
