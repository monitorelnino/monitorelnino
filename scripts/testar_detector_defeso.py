#!/usr/bin/env python3
"""Autoteste do detector de página de defeso (PR-N0 §1.5): fixture positiva no espírito da página da
SUDEC/BA de 02/09/2026 (a captura real deve substituir a fixture assim que arquivada) e negativas."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import classificar_defeso, detectar_defeso, _dominio_publico, rodar_autoteste

FIX_SUDEC = """<!doctype html><html lang="pt-BR"><head><title>SUDEC</title></head><body>
<div class="aviso">Em cumprimento à legislação eleitoral (Lei nº 9.504/97, art. 73, VI, "b"), o conteúdo deste
portal encontra-se temporariamente indisponível durante o período eleitoral. Informações de emergência: 199.</div>
</body></html>"""
FIX_NORMAL = "<html><body><h1>Plano de Contingência 2026</h1><p>Decreto nº 12, de 3 de julho de 2026. Art. 1º Fica instituído…</p></body></html>"
FIX_NOTICIA = "<html><body><p>A eleição municipal de 2024 elegeu o prefeito. O plano de contingência foi publicado.</p></body></html>"

def t1(): return detectar_defeso(FIX_SUDEC) is not None
def t2(): return detectar_defeso(FIX_NORMAL) is None and detectar_defeso("") is None
def t3(): return detectar_defeso(FIX_NOTICIA) is None   # 'eleição' sozinha não é defeso
def t4(): return detectar_defeso("Conteúdo temporariamente indisponível em razão da legislação eleitoral") is not None and detectar_defeso("Conteúdo temporariamente indisponível para manutenção") is None
def t5(): return _dominio_publico("https://www.defesacivil.ba.gov.br/plano") and not _dominio_publico("https://queridodiario.ok.org.br/api/gazettes") and not _dominio_publico("https://api.portaldatransparencia.gov.br/x")

# §182 (23/09/2026): os quatro casos REAIS da rodada de 23/09, que decidem onde o padrão vale.
FIX_ALT_DE_IMAGEM = ('<html><body><a href="/detran"><img src="/uploads/banner.jpeg" '
                     'alt="banner periodo eleitoral" style="max-width:100%"></a>'
                     '<p>Boletim epidemiológico da semana 38 publicado.</p></body></html>')
FIX_TITULO = ('<html><head><meta name="robots" content="noindex, nofollow">'
              '<title>Suspensão Temporária | Período Eleitoral 2026</title></head><body></body></html>')
FIX_META_DESCRICAO = ('<html><head><meta name="description" content="Em função do período eleitoral, '
                      'esta página está indisponível até o Tribunal Regional Eleitoral oficializar o '
                      'resultado."></head><body><style>.lazyloaded{display:block}</style></body></html>')
FIX_TEXTO_VISIVEL = ('<html><body><ul><li><h3 class="titulo"><a href="">Conteúdo indisponível devido ao '
                     'período eleitoral</a></h3></li></ul></body></html>')

def t6(): return detectar_defeso(FIX_ALT_DE_IMAGEM) is None          # saude.pi.gov.br: só o alt casava
def t7(): return detectar_defeso(FIX_TITULO) is not None             # defesacivil.ma.gov.br
def t8(): return detectar_defeso(FIX_META_DESCRICAO) is not None     # defesacivil.mg.gov.br
def t9(): return detectar_defeso(FIX_TEXTO_VISIVEL) is not None      # defesacivil.pr.gov.br
# §182: o ESCOPO do que foi suspenso, nas palavras reais dos sítios em 23/09/2026.
FIX_NOTICIAS_MT = ('<html><body><p>Em cumprimento à legislação eleitoral, o Governo de Mato Grosso '
                   'suspende, a partir deste sábado (4.7), a exibição das notícias institucionais '
                   'publicadas neste portal.</p><p>Plano estadual de contingência 2026 disponível.</p></body></html>')
FIX_NOTICIAS_SP = ('<html><body><p>Em atendimento à legislação eleitoral, os conteúdos desta seção de '
                   'notícias ficarão indisponíveis de 4 de julho de 2026 até o final da eleição.</p></body></html>')
FIX_BANNER_SC = '<html><body><p>banner home - legislacao eleitoral - full banner</p></body></html>'

def t11():
    # notícia institucional suspensa NÃO fecha o canal de documento
    return (classificar_defeso(FIX_NOTICIAS_MT)[1] == "noticias" and detectar_defeso(FIX_NOTICIAS_MT) is None
            and classificar_defeso(FIX_NOTICIAS_SP)[1] == "noticias" and detectar_defeso(FIX_NOTICIAS_SP) is None)

def t12():
    # menção sem declaração de indisponibilidade não é suspensão de nada
    return classificar_defeso(FIX_BANNER_SC)[1] is None and detectar_defeso(FIX_BANNER_SC) is None

def t13():
    # sítio inteiro fora do ar continua sendo suspensão, e é o único caso que fecha o canal
    return (classificar_defeso(FIX_TITULO)[1] == "sitio" and detectar_defeso(FIX_TITULO) is not None
            and classificar_defeso(FIX_META_DESCRICAO)[1] == "sitio")

def t10():
    # classe de CSS e endereço de link não são declaração ao leitor
    return detectar_defeso('<html><body><div class="aviso-periodo-eleitoral-2026">'
                           '<a href="/legislacao-eleitoral">Documentos</a>'
                           '<p>Plano de contingência 2026 publicado.</p></div></body></html>') is None
sys.exit(rodar_autoteste({"fixture SUDEC/BA: detecta": t1, "negativo: página normal e vazia": t2, "negativo: 'eleição' em notícia não é defeso": t3,
                          "indisponível + contexto eleitoral: detecta; manutenção: não": t4, "domínio público vs API": t5,
                          "§182 alt de imagem não suspende o portal (saude.pi.gov.br)": t6,
                          "§182 aviso no <title> detecta (defesacivil.ma.gov.br)": t7,
                          "§182 aviso na <meta description> detecta (defesacivil.mg.gov.br)": t8,
                          "§182 aviso no texto visível detecta (defesacivil.pr.gov.br)": t9,
                          "§182 classe de CSS e href não são declaração ao leitor": t10,
                          "§182 notícia institucional suspensa não fecha o canal (MT, SP)": t11,
                          "§182 nome de banner não é suspensão (saude.sc.gov.br)": t12,
                          "§182 sítio inteiro fora do ar é o caso que fecha o canal (MA, MG)": t13}))
