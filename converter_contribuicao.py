#!/usr/bin/env python3
"""
converter_contribuicao.py
============================
Fecha a lacuna entre os dois canais de entrada de dados do Monitor El Niño
Brasil, que até 26/08/2026 não convergiam:

  Canal A (automático) — atualizar_instrumentos_estaduais.py varre repositórios
    estaduais e já produz data/instrumentos_revisar.json, pronto para
    aplicar_revisao.py.
  Canal B (humano) — verificar_contribuicoes.py puxa o formulário do site e
    produz fila_contribuicoes/fila_DATA.json, mas em formato PRÓPRIO — sem
    categoria (só "tipo", mais genérico), sem coordenadas, sem canal/fonte
    padronizados. Não havia nenhum script que levasse um item aprovado da
    fila até o banco: a entrada tinha que ser editada à mão em municipios.json,
    fora do fluxo testado (mesclar → recalcular → três portões).

Este script converte UM item aprovado da fila (você aponta qual, pelo índice
mostrado no .md) para uma entrada no formato de instrumentos_revisar.json —
a MESMA fila que aplicar_revisao.py já sabe aplicar. A partir de agora, os
dois canais convergem para um único ponto de aplicação.

O QUE ESTE SCRIPT NÃO FAZ (regra de ouro, sem exceção):
  - NÃO infere a categoria (plano / plano_antigo / decreto / etc.) a partir
    do "tipo" que o leitor marcou no formulário — o "tipo" do formulário é
    grosseiro demais (ex.: "plano" não diz se é edição vigente ou antiga).
    A categoria É UM JULGAMENTO HUMANO, feito depois de abrir o documento —
    por isso --categoria é obrigatório e nunca tem valor padrão.
  - NÃO escreve em municipios.json. Só acrescenta a data/instrumentos_revisar.json,
    de onde aplicar_revisao.py (já existente) mescla, recalcula e roda os
    três portões — o mesmo caminho do Canal A, sem exceção para o Canal B.

Uso (depois de marcar os checkboxes do .md e decidir a categoria):
  python3 converter_contribuicao.py --arquivo fila_contribuicoes/fila_2026-08-26.json \\
      --indice 1 --categoria plano

  # Múltiplos itens aprovados da mesma fila:
  python3 converter_contribuicao.py --arquivo fila_contribuicoes/fila_2026-08-26.json \\
      --indice 1 --categoria plano
  python3 converter_contribuicao.py --arquivo fila_contribuicoes/fila_2026-08-26.json \\
      --indice 3 --categoria plano_antigo

  # Depois, uma vez só, para todos os itens acumulados:
  python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json
"""
import argparse
import datetime
import json
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"

CATEGORIAS_VALIDAS = {"plano", "plano_antigo", "plano_elaboracao", "decreto",
                      "coberto_estadual", "nao_el_nino", "nao_localizado"}


def norm(s: str) -> str:
    """Normaliza nome de município para comparação robusta (minúsculas, sem acento) contra a base IBGE."""
    return unicodedata.normalize("NFD", s.upper()).encode("ascii", "ignore").decode()


def buscar_coordenadas(nome: str, uf: str, ref: list[dict]):
    """Localiza latitude e longitude do município na base de referência do IBGE, para posicionar o registro nos mapas do site."""
    for r in ref:
        if r["uf"] == uf and norm(r["nome"]) == norm(nome):
            return r.get("lat"), r.get("lon"), r["nome"]  # devolve a grafia oficial também
    return None, None, None


def main():
    """Lê um item aprovado da fila de contribuições e o converte para o formato de registro do banco público (sem e-mail nem qualquer dado de contato), pronto para revisão final e integração."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", required=True, help="Arquivo fila_contribuicoes/fila_AAAA-MM-DD.json")
    ap.add_argument("--indice", type=int, required=True, help="Posição do item na lista 'fila' (1 = primeiro, como no .md)")
    ap.add_argument("--categoria", required=True, choices=sorted(CATEGORIAS_VALIDAS),
                     help="Categoria — decisão humana após abrir o documento, nunca inferida")
    ap.add_argument("--saida", default=str(DATA / "instrumentos_revisar.json"),
                     help="Arquivo de revisão de destino (padrão: data/instrumentos_revisar.json, o mesmo do Canal A)")
    args = ap.parse_args()

    fila_doc = json.load(open(args.arquivo, encoding="utf-8"))
    fila = fila_doc.get("fila", [])
    if not (1 <= args.indice <= len(fila)):
        sys.exit(f"Erro: --indice {args.indice} fora do intervalo (a fila tem {len(fila)} item(ns)).")
    item = fila[args.indice - 1]

    uf = item["uf"].strip().upper()
    ref = json.load(open(DATA / "municipios_ibge_referencia.json", encoding="utf-8"))
    lat, lon, nome_oficial = buscar_coordenadas(item["municipio"], uf, ref)
    if lat is None:
        sys.exit(f"Erro: '{item['municipio']}/{uf}' não casou com a malha IBGE — confira a grafia "
                  f"antes de converter (mesma regra do Canal A: nada entra sem casar com o oficial).")

    municipios = json.load(open(DATA / "municipios.json", encoding="utf-8"))
    ja_existe = any(m["uf"] == uf and norm(m["nome"]) == norm(nome_oficial) for m in municipios)

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    entrada = {
        "acao": "atualizar" if ja_existe else "novo",
        "uf": uf,
        "nome": nome_oficial,
        "categoria": args.categoria,
        "documento": item.get("numero_data") or "(número/data não informados pelo leitor — conferir no link)",
        "data": hoje,
        "fonte": f"Contribuição de leitor, verificada em {hoje}" + (f" — {item['observacoes']}" if item.get("observacoes") else ""),
        "url": item["link"],
        "canal": "contribuicao_leitor",
        "lat": lat, "lon": lon,
    }

    saida_p = Path(args.saida)
    fila_saida = json.load(open(saida_p, encoding="utf-8")) if saida_p.exists() else []
    fila_saida.append(entrada)
    json.dump(fila_saida, open(saida_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Convertido: {entrada['acao'].upper()} {nome_oficial}/{uf} → {args.categoria}")
    print(f"  fonte: {item['link']}")
    print(f"  acrescentado a {saida_p} ({len(fila_saida)} item(ns) agora na fila)")
    print(f"\nQuando terminar de converter os itens aprovados desta rodada, rode:")
    print(f"  python3 aplicar_revisao.py --arquivo {saida_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
