#!/usr/bin/env python3
"""Valida os workflows do GitHub Actions com detecção de CHAVE DUPLICADA (o pyyaml aceita em
silêncio; o GitHub recusa o workflow inteiro — 03/09/2026: um 'env' duplicado quebrou a rotina).
Roda no portão 1 (verificar_estrutura.js chama este script) e na checagem de PR."""
import glob, sys, yaml
class Dup(yaml.SafeLoader): pass
def cons(loader, node):
    keys = [loader.construct_object(k) for k, _ in node.value]
    dup = [k for k in keys if keys.count(k) > 1]
    if dup: raise ValueError(f"chave duplicada {sorted(set(dup))}")
    return yaml.SafeLoader.construct_mapping(loader, node, deep=True)
Dup.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cons)
erros = 0
for f in sorted(glob.glob(".github/workflows/*.yml")):
    try: yaml.load(open(f, encoding="utf-8"), Loader=Dup)
    except Exception as e: print(f"  ✗ {f}: {e}"); erros += 1
print("✓ WORKFLOWS OK — YAML válido, sem chave duplicada." if not erros else f"✗ WORKFLOWS: {erros} arquivo(s) inválido(s).")
sys.exit(1 if erros else 0)
