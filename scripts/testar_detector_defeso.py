#!/usr/bin/env python3
"""Autoteste do detector de página de defeso (PR-N0 §1.5): fixture positiva no espírito da página da
SUDEC/BA de 02/09/2026 (a captura real deve substituir a fixture assim que arquivada) e negativas."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import detectar_defeso, _dominio_publico, rodar_autoteste

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
sys.exit(rodar_autoteste({"fixture SUDEC/BA: detecta": t1, "negativo: página normal e vazia": t2, "negativo: 'eleição' em notícia não é defeso": t3,
                          "indisponível + contexto eleitoral: detecta; manutenção: não": t4, "domínio público vs API": t5}))
