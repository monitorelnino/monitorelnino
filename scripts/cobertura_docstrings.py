#!/usr/bin/env python3
"""Contagem reproduzível da cobertura de docstrings do código Python do pacote.

Criado pela correção C9 da auditoria de 29/08/2026: o número declarado em
docs/AUDITORIA_CODIGO.md (85/87) divergia da medição independente por AST do
auditor (85/91) porque o CRITÉRIO de contagem não estava fixado — funções
aninhadas, métodos dunder e lambdas nomeados entram ou não conforme quem conta.
Este script fixa o critério e passa a ser a única fonte do número publicado,
no mesmo padrão que o projeto já adota para todos os outros números.

CRITÉRIO FIXADO (o mais abrangente, o do auditor):
  conta-se TODA FunctionDef/AsyncFunctionDef encontrada pelo ast.walk — funções
  de módulo, métodos (dunder inclusive) e funções aninhadas. Lambdas não são
  FunctionDef e ficam fora por definição da gramática, não por escolha.
  Módulos: conta-se docstring de módulo de todo arquivo .py do pacote.

Escopo: *.py da raiz + scripts/, excluindo node_modules e artefatos.
Uso: python3 scripts/cobertura_docstrings.py [--listar-faltantes]
Saída estável, própria para colar em docs/AUDITORIA_CODIGO.md.
"""
import ast
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent.parent


def medir():
    """Percorre os módulos do pacote e devolve (funcoes, com_doc, modulos, mod_doc, faltantes)."""
    arquivos = sorted(RAIZ.glob("*.py")) + sorted((RAIZ / "scripts").glob("*.py"))
    funcoes = com_doc = modulos = mod_doc = 0
    faltantes = []
    for arq in arquivos:
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        modulos += 1
        if ast.get_docstring(arvore):
            mod_doc += 1
        else:
            faltantes.append(f"{arq.relative_to(RAIZ)} (docstring de módulo)")
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcoes += 1
                if ast.get_docstring(no):
                    com_doc += 1
                else:
                    faltantes.append(f"{arq.relative_to(RAIZ)}:{no.lineno} {no.name}()")
    return funcoes, com_doc, modulos, mod_doc, faltantes


def main():
    """Imprime o resumo canônico e, com --listar-faltantes, cada função sem docstring."""
    funcoes, com_doc, modulos, mod_doc, faltantes = medir()
    print(f"Cobertura de docstrings (critério fixado em scripts/cobertura_docstrings.py):")
    print(f"  funções: {com_doc} de {funcoes} com docstring")
    print(f"  módulos: {mod_doc} de {modulos} com docstring de módulo")
    if "--listar-faltantes" in sys.argv:
        for f in faltantes:
            print(f"  — sem docstring: {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
