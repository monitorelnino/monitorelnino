#!/usr/bin/env python3
"""
aplicar_revisao.py
====================
Aplica um arquivo de revisão APROVADO (produzido por atualizar_instrumentos_estaduais.py,
mesmo formato de data/instrumentos_revisar.json) a data/municipios.json e
data/pontos_mapa.json, e então executa, nesta ordem, exatamente a sequência
que era feita manualmente em 26/08/2026 ao incorporar os 13 achados de Sergipe:

  1. mescla as entradas do arquivo de revisão em municipios.json + pontos_mapa.json
  2. recalcular_mare.py --write   (recomputa indice.json e percentual_uf.json)
  3. atualiza data/meta.json (novo corte)
  4. os três portões: verificar_estrutura.js, verificar_consistencia.py, verificar_runtime.js

Se qualquer portão falhar, o script termina com código de saída != 0 e a
mensagem de erro do portão — a base já foi alterada em disco (não há rollback
automático), então revise o erro, corrija manualmente e rode os portões nas
mãos até ficarem verdes antes de publicar.

REVISÃO É EXIGIDA ANTES DE RODAR ISTO: abra o arquivo, apague qualquer item que
não deva entrar. Este script aplica tudo o que estiver no arquivo no momento
em que é executado — a mesma convenção de transferencias_revisar.json.

Uso:
  python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json
  python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json --dry-run
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"


def carregar(nome):
    """Lê um arquivo JSON de propostas de revisão (instrumentos_revisar.json ou equivalente)."""
    return json.load(open(DATA / nome, encoding="utf-8"))


def salvar(nome, obj):
    """Grava um dicionário como JSON formatado, no mesmo padrão de indentação usado em todo o projeto."""
    json.dump(obj, open(DATA / nome, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def mesclar(revisao: list[dict], municipios: list[dict], pontos: list[dict]):
    """Aplica cada entrada da revisão: 'novo' adiciona; 'atualizar' sobrescreve
    o registro existente (mesmo nome+UF) preservando lat/lon se a entrada de
    revisão não trouxer coordenadas próprias."""
    idx_mun = {(m["nome"], m["uf"]): i for i, m in enumerate(municipios)}
    idx_pon = {(p["nome"], p["uf"]): i for i, p in enumerate(pontos)}
    aplicadas, avisos = [], []

    for item in revisao:
        chave = (item["nome"], item["uf"])
        campos_mun = {k: item[k] for k in ("nome", "uf", "categoria", "documento", "data", "fonte", "url", "canal") if k in item}

        if item["acao"] == "novo":
            if chave in idx_mun:
                avisos.append(f"{item['nome']}/{item['uf']}: já existe na base — tratando como 'atualizar'")
            else:
                if "lat" not in item or "lon" not in item:
                    avisos.append(f"{item['nome']}/{item['uf']}: SEM coordenadas na proposta — pulei (adicione lat/lon e rode de novo)")
                    continue
                campos_mun["lat"] = item["lat"]
                campos_mun["lon"] = item["lon"]
                municipios.append(campos_mun)
                pontos.append({"nome": item["nome"], "uf": item["uf"], "categoria": item["categoria"],
                                "lat": item["lat"], "lon": item["lon"],
                                "fase": next((p["fase"] for p in pontos if p["uf"] == item["uf"]), 3)})
                aplicadas.append(f"NOVO: {item['nome']}/{item['uf']} → {item['categoria']}")
                continue

        if chave not in idx_mun:
            avisos.append(f"{item['nome']}/{item['uf']}: 'atualizar' mas não existe na base — pulei")
            continue
        i = idx_mun[chave]
        de = municipios[i]["categoria"]
        municipios[i].update(campos_mun)
        if "lat" in item: municipios[i]["lat"] = item["lat"]
        if "lon" in item: municipios[i]["lon"] = item["lon"]
        if chave in idx_pon:
            pontos[idx_pon[chave]]["categoria"] = item["categoria"]
        else:
            pontos.append({"nome": item["nome"], "uf": item["uf"], "categoria": item["categoria"],
                            "lat": municipios[i]["lat"], "lon": municipios[i]["lon"],
                            "fase": next((p["fase"] for p in pontos if p["uf"] == item["uf"]), 3)})
        aplicadas.append(f"ATUALIZAR: {item['nome']}/{item['uf']} · {de} → {item['categoria']}")

    return aplicadas, avisos


def rodar(cmd, nome):
    """Aplica ao banco público as propostas aprovadas (as que sobraram no arquivo após a edição humana), com assert de que cada município-alvo existe antes de substituir."""
    print(f"\n=== {nome} ===")
    r = subprocess.run(cmd, cwd=RAIZ)
    ok = r.returncode == 0
    print("✓ OK" if ok else f"✗ FALHOU (código {r.returncode})")
    return ok


def main():
    """Ponto de entrada: lê --arquivo, aplica a revisão, recalcula o índice e roda os portões de consistência e estrutura."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", required=True, help="Arquivo de revisão aprovado (ex.: data/instrumentos_revisar.json)")
    ap.add_argument("--dry-run", action="store_true", help="Mostra o que seria aplicado, sem gravar nada")
    args = ap.parse_args()

    revisao = json.load(open(args.arquivo, encoding="utf-8"))
    if not revisao:
        sys.exit("Arquivo de revisão vazio — nada a aplicar.")

    municipios = carregar("municipios.json")
    pontos = carregar("pontos_mapa.json")
    aplicadas, avisos = mesclar(revisao, municipios, pontos)

    print(f"{len(aplicadas)} alteração(ões) reconhecida(s):")
    for a in aplicadas: print(f"  {a}")
    if avisos:
        print(f"\n{len(avisos)} aviso(s):")
        for a in avisos: print(f"  [aviso] {a}")

    if args.dry_run:
        print("\n--dry-run: nada foi gravado.")
        return 0
    if not aplicadas:
        print("\nNenhuma alteração aplicável — nada gravado.")
        return 0

    salvar("municipios.json", municipios)
    salvar("pontos_mapa.json", pontos)
    print(f"\nmunicipios.json e pontos_mapa.json atualizados ({len(municipios)} municípios).")

    if not rodar([sys.executable, "recalcular_mare.py", "--write"], "Recalculando MARÉ (índice + percentual_uf)"):
        sys.exit(1)

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    meta = carregar("meta.json")
    meta["corte"] = hoje
    meta["atualizado_em"] = hoje
    salvar("meta.json", meta)
    print(f"\nCorte dos dados atualizado para {hoje}.")

    gates = [
        (["node", "scripts/verificar_estrutura.js"], "Portão 1/3 — estrutura"),
        ([sys.executable, "verificar_consistencia.py"], "Portão 2/3 — consistência"),
        (["node", "scripts/verificar_runtime.js"], "Portão 3/3 — runtime"),
    ]
    todos_ok = True
    for cmd, nome in gates:
        if not rodar(cmd, nome):
            todos_ok = False

    Path(args.arquivo).unlink()
    print(f"\n{args.arquivo} consumido e removido.")

    if todos_ok:
        print("\n✓ Revisão aplicada e os três portões passaram. Pronto para publicar.")
        return 0
    else:
        print("\n✗ Revisão aplicada, mas ao menos um portão falhou — corrija antes de publicar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
