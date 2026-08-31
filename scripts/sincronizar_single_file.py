#!/usr/bin/env python3
"""
sincronizar_single_file.py
=============================
Regrava, na prévia single-file (o arquivo ~465KB entregue para visualização
em chat), as seis constantes de dados e os valores fixos do herói, a partir
de data/*.json — a mesma operação que vinha sendo feita à mão a cada rodada
de dados, e que já causou pelo menos dois bugs por nome de const errado ou
substituição incompleta (26/08/2026).

ESCOPO E LIMITE HONESTOS: a prévia single-file NÃO faz parte do pacote
publicado (site-futura/monitorelnino) — ela nunca é commitada nem servida;
existe só como conveniência para revisão dentro desta conversa. Por isso este
script não é chamado por atualizar.py (que rege o pacote real, sem essa
prévia) — é uma ferramenta à parte, para rodar sempre que os dados mudarem e
a prévia precisar refletir isso. O pacote publicado (index.html) não precisa
disto: ele busca data/*.json em tempo real via fetch.

Uso:
  python3 sincronizar_single_file.py --arquivo /mnt/user-data/outputs/prototipo_plataforma_el_nino.html
  python3 sincronizar_single_file.py --arquivo ... --tambem-pacote   # também sincroniza os valores
                                                                        fixos do herói em index.html
                                                                        (os consts do pacote não precisam:
                                                                        ele já busca data/*.json ao vivo)
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # scripts/ -> raiz do pacote (mesmo padrão de verificar_estrutura.js)
DATA = RAIZ / "data"

CONSTS = [("TABELA_MUNICIPIOS", "municipios"), ("MARE", "indice"), ("PCT_POR_UF", "percentual_uf"),
          ("TRANSFERENCIAS", "transferencias"), ("MAP_POINTS", "pontos_mapa"), ("META", "meta")]


def media_nacional_fmt(indice: dict) -> str:
    """Média nacional do índice formatada no padrão do site (vírgula decimal, 1 casa)."""
    media = sum(v["total"] for v in indice.values()) / len(indice)
    return f"{media:.1f}".replace(".", ",")


def sincronizar_consts(html: str) -> tuple[str, list[str]]:
    """Substitui no HTML as consts embutidas (TABELA_MUNICIPIOS, MARE etc.) pelos JSON vigentes de data/."""
    log = []
    for nome, arq in CONSTS:
        obj = json.load(open(DATA / f"{arq}.json", encoding="utf-8"))
        pat = rf"const {nome} = [\[{{].*?[\]}}];"
        if not re.search(pat, html, re.S):
            sys.exit(f"Erro: const {nome} não encontrada no arquivo — verifique se é a versão certa do single-file.")
        novo_texto = f"const {nome} = " + json.dumps(obj, ensure_ascii=False) + ";"
        html, n = re.subn(pat, lambda m: novo_texto, html, count=1, flags=re.S)
        log.append(f"const {nome} regravada ({len(obj) if hasattr(obj, '__len__') else '?'} entradas)")
    return html, log


def sincronizar_heroi(html: str, meta: dict, indice: dict) -> tuple[str, list[str]]:
    """Atualiza os valores fixos do herói (média no gauge, datas de corte/atualização) no HTML dado."""
    ver = media_nacional_fmt(indice)
    corte = meta["corte"]
    log = []
    subs = [
        (r'id="gaugeNum">[\d,]+<', f'id="gaugeNum">{ver}<'),
        (r'data-alvo="[\d.]+" style="--galvo:[\d.]+;"', f'data-alvo="{ver.replace(",", ".")}" style="--galvo:{ver.replace(",", ".")};"'),
        (r'MARÉ nacional em [\d,]+ de 100', f'MARÉ nacional em {ver} de 100'),
        (r'id="gaugeCorte">\d{2}/\d{2}/\d{4}<', f'id="gaugeCorte">{corte}<'),
        (r'id="corteDados">\d{2}/\d{2}/\d{4}<', f'id="corteDados">{corte}<'),
    ]
    for pat, novo in subs:
        html2, n = re.subn(pat, novo, html, count=1)
        if n == 0:
            log.append(f"[aviso] padrão não encontrado (pode já estar sincronizado ou o markup mudou): {pat}")
        else:
            html = html2
            log.append(f"substituído: {pat[:40]}...")
    return html, log


def main():
    """CLI: sincroniza o single-file de prévia (e opcionalmente o index.html do pacote) com data/."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", required=True, help="Caminho do arquivo single-file a sincronizar")
    ap.add_argument("--tambem-pacote", metavar="INDEX_HTML", help="Também sincroniza os valores fixos do herói neste index.html (pacote)")
    args = ap.parse_args()

    alvo = Path(args.arquivo)
    html = alvo.read_text(encoding="utf-8")
    meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
    indice = json.load(open(DATA / "indice.json", encoding="utf-8"))

    html, log_consts = sincronizar_consts(html)
    html, log_heroi = sincronizar_heroi(html, meta, indice)
    alvo.write_text(html, encoding="utf-8")

    print(f"{alvo}:")
    for l in log_consts + log_heroi: print(f"  {l}")

    if args.tambem_pacote:
        pk = Path(args.tambem_pacote)
        html_pk = pk.read_text(encoding="utf-8")
        html_pk, log_pk = sincronizar_heroi(html_pk, meta, indice)
        pk.write_text(html_pk, encoding="utf-8")
        print(f"\n{pk} (só herói — consts vêm de fetch ao vivo):")
        for l in log_pk: print(f"  {l}")

    print(f"\nmédia nacional sincronizada: {media_nacional_fmt(indice)} · corte: {meta['corte']}")


if __name__ == "__main__":
    main()
