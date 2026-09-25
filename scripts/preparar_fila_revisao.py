#!/usr/bin/env python3
"""
preparar_fila_revisao.py — a fila de leitura humana (R7) em ordem de decisão · §218
==================================================================================
PARA QUE SERVE. A promoção ao banco é sempre humana (R7), e as filas somam mais de 900
itens espalhados por sete arquivos, cada um com um formato. Ler isso como JSON cru é o que
faz a fila parar: não porque as decisões sejam difíceis, mas porque encontrar as difíceis
no meio das fáceis custa horas.

O QUE ELE FAZ. Junta as filas, ordena por quanto cada item MERECE a atenção — e mostra o
trecho, para que o descarte seja imediato quando o trecho não sustenta nada. Medido em
25/09/2026 na fila de pistas: das 485 sem julgamento, 19 estão em confiança A com triagem
"candidato forte", e 230 em B/indefinido. A leitura na ordem certa é outra tarefa.

O QUE ELE NÃO FAZ, E ISSO É O PONTO. Não promove, não classifica, não decide e **não
escreve em `data/`**. Ele só ORDENA e APRESENTA o que já está na fila. Nenhum item muda de
estado por ter sido listado aqui; `julgamento_humano` continua sendo escrito por uma
pessoa, pelo caminho de sempre.

ONDE O RELATÓRIO SAI. Fora do repositório, por padrão. Fila de revisão é material de
trabalho da editoria, e o `CLAUDE.md` é explícito: material interno vive no repositório
privado, nunca neste, que é público. O destino é argumento; o padrão é um arquivo temporário.

USO
  python scripts/preparar_fila_revisao.py --autoteste
  python scripts/preparar_fila_revisao.py                    # imprime o resumo
  python scripts/preparar_fila_revisao.py --saida fila.html  # e grava o relatório
"""
import html
import json
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import rodar_autoteste  # noqa: E402

# Cada fila, o campo que guarda a lista, e como ler um item. `chave=None` = o arquivo é a lista.
FILAS = [
    ("Pistas de imprensa e diários", "pistas_imprensa.json", "pistas"),
    ("Transferegov — convênios com objeto de El Niño", "transferegov_el_nino_revisar.json", "itens"),
    ("Transferências federais", "transferencias_revisar.json", None),
    ("Painel do Amazonas", "pistas_painel_am.json", "itens"),
    ("Descobertas em sítios oficiais", "pistas_descobertas.json", "itens"),
    ("Imprensa — saúde", "pistas_imprensa_saude.json", "pistas"),
    ("Sinais de risco", "pistas_sinais.json", "itens"),
]
# Ordem de decisão. Quanto maior, mais cedo a pessoa olha. A escala é declarada aqui e não
# depende de nenhum número mágico espalhado pelo código.
PESO_CONFIANCA = {"A": 300, "B": 200, "C": 100}
PESO_TRIAGEM = {"candidato_forte": 60, "indefinido": 0, "falso_positivo_provavel": -120}


def ja_julgado(item: dict) -> bool:
    """Item que uma pessoa já decidiu sai da fila. Função pura."""
    return bool(item.get("julgamento_humano")) or item.get("documento_oficial_confirmado") is not None


def prioridade(item: dict) -> int:
    """Quanto este item merece a atenção primeiro. Função pura.

    Confiança pesa mais do que triagem, e `falso_positivo_provavel` empurra para o fim sem
    nunca EXCLUIR: quem decide é a pessoa, e um falso positivo provável continua sendo um
    palpite da máquina. `pontos_confianca` desempata."""
    p = PESO_CONFIANCA.get(item.get("nivel_confianca"), 50)
    p += PESO_TRIAGEM.get(item.get("triagem"), 0)
    try:
        p += min(int(item.get("pontos_confianca") or 0), 20)
    except (TypeError, ValueError):
        pass
    return p


def resumir(item: dict) -> dict:
    """O mínimo para decidir sem abrir o JSON: quem, quando, o que se viu, e onde conferir."""
    mun = item.get("municipio") or item.get("nome_ibge") or item.get("municipio_no_painel") or item.get("_municipio") or "—"
    uf = item.get("uf") or item.get("_uf") or ""
    trecho = (item.get("trecho") or item.get("objeto") or item.get("titulo") or item.get("observacao") or "").strip()
    return {
        "municipio": f"{mun}{('/' + uf) if uf else ''}",
        "data": item.get("data") or item.get("data_publicacao") or item.get("lido_em") or item.get("assinatura") or "",
        "trecho": " ".join(trecho.split())[:320],
        "url": item.get("url") or item.get("dominio") or "",
        "confianca": item.get("nivel_confianca") or "—",
        "triagem": item.get("triagem") or "—",
        "prioridade": prioridade(item),
    }


def carregar(ler_fn) -> list:
    """(nome da fila, itens pendentes já resumidos e ordenados). Puro com `ler_fn` injetado."""
    saida = []
    for nome, arquivo, chave in FILAS:
        bruto = ler_fn(arquivo)
        if bruto is None:
            continue
        itens = bruto if isinstance(bruto, list) else (bruto.get(chave) or [])
        pendentes = [resumir(i) for i in itens if isinstance(i, dict) and not ja_julgado(i)]
        pendentes.sort(key=lambda x: -x["prioridade"])
        saida.append({"fila": nome, "arquivo": arquivo, "total": len(itens), "pendentes": pendentes})
    return saida


def montar_html(filas: list, gerado_em: str) -> str:
    """Relatório legível. Sem CSS externo, sem script: é para abrir e ler."""
    total = sum(len(f["pendentes"]) for f in filas)
    p = ['<!doctype html><meta charset="utf-8"><title>Fila de leitura humana</title>',
         '<style>body{font:16px/1.5 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#15201a}'
         'h1{font-weight:400}h2{margin-top:2.5rem;border-bottom:1px solid #d6c4ac;padding-bottom:.3rem;font-weight:400}'
         'table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #eee;padding:.5rem;'
         'text-align:left;vertical-align:top}th{color:#555}.t{color:#333}.a{font-weight:600}'
         'code{background:#f5f2ec;padding:.1rem .3rem}</style>',
         f'<h1>Fila de leitura humana (R7)</h1><p>{total} item(ns) sem julgamento, em '
         f'{len(filas)} fila(s). Gerado em {html.escape(gerado_em)}. '
         'Nada aqui foi promovido, classificado ou alterado — a ordem é só de leitura.</p>']
    for f in filas:
        if not f["pendentes"]:
            continue
        p.append(f'<h2>{html.escape(f["fila"])}</h2>'
                 f'<p>{len(f["pendentes"])} pendente(s) de {f["total"]} · <code>data/{html.escape(f["arquivo"])}</code></p>')
        p.append('<table><tr><th>Município</th><th>Data</th><th>Conf.</th><th>Triagem</th><th>O que se viu</th></tr>')
        for i in f["pendentes"]:
            link = f' <a href="{html.escape(i["url"])}">fonte</a>' if i["url"] else ""
            classe = ' class="a"' if i["confianca"] == "A" else ""
            p.append(f'<tr><td{classe}>{html.escape(i["municipio"])}</td><td>{html.escape(str(i["data"]))}</td>'
                     f'<td>{html.escape(i["confianca"])}</td><td>{html.escape(i["triagem"])}</td>'
                     f'<td class="t">{html.escape(i["trecho"])}{link}</td></tr>')
        p.append('</table>')
    return "\n".join(p)


def principal(args) -> int:
    from datetime import datetime
    from coletores_base import ler
    filas = carregar(lambda nome: ler(nome, None))
    total = sum(len(f["pendentes"]) for f in filas)
    for f in filas:
        if f["pendentes"]:
            a = sum(1 for i in f["pendentes"] if i["confianca"] == "A")
            forte = sum(1 for i in f["pendentes"] if i["triagem"] == "candidato_forte")
            print(f"{len(f['pendentes']):5d} pendente(s) de {f['total']:5d}  ·  {a} em confiança A, "
                  f"{forte} candidato(s) forte(s)  ·  {f['fila']}")
    print(f"{total:5d} no total, em ordem de decisão")
    destino = args[args.index("--saida") + 1] if "--saida" in args else str(
        pathlib.Path(tempfile.gettempdir()) / "fila_revisao_mare.html")
    pathlib.Path(destino).write_text(
        montar_html(filas, datetime.now().strftime("%d/%m/%Y %H:%M")), encoding="utf-8", newline="\n")
    print(f"→ {destino}")
    return 0


FIX = {
    "pistas_imprensa.json": {"pistas": [
        {"municipio": "Alfa", "uf": "MG", "nivel_confianca": "B", "triagem": "indefinido", "trecho": "b"},
        {"municipio": "Beta", "uf": "MG", "nivel_confianca": "A", "triagem": "candidato_forte",
         "pontos_confianca": "6", "trecho": "a", "url": "http://x"},
        {"municipio": "Gama", "uf": "MG", "nivel_confianca": "A", "triagem": "falso_positivo_provavel", "trecho": "c"},
        {"municipio": "Delta", "uf": "MG", "nivel_confianca": "A", "triagem": "candidato_forte",
         "julgamento_humano": "recusado", "trecho": "d"},
    ]},
    "pistas_painel_am.json": {"itens": [
        {"nome_ibge": "Ípsilon", "documento_oficial_confirmado": None, "observacao": "o"},
        {"nome_ibge": "Zeta", "documento_oficial_confirmado": True, "observacao": "z"},
    ]},
}


def autoteste() -> int:
    def t1():
        f = carregar(lambda nome: FIX.get(nome))
        pistas = next(x for x in f if x["arquivo"] == "pistas_imprensa.json")
        return [i["municipio"] for i in pistas["pendentes"]] == ["Beta/MG", "Alfa/MG", "Gama/MG"]

    def t2():
        """Item já julgado sai da fila — pelos dois caminhos que o projeto usa para dizer isso."""
        f = carregar(lambda nome: FIX.get(nome))
        pistas = next(x for x in f if x["arquivo"] == "pistas_imprensa.json")
        am = next(x for x in f if x["arquivo"] == "pistas_painel_am.json")
        return (all("Delta" not in i["municipio"] for i in pistas["pendentes"])
                and [i["municipio"] for i in am["pendentes"]] == ["Ípsilon"])

    def t3():
        """Falso positivo provável vai para o FIM, e não é excluído: quem decide é a pessoa."""
        f = carregar(lambda nome: FIX.get(nome))
        p = next(x for x in f if x["arquivo"] == "pistas_imprensa.json")["pendentes"]
        return p[-1]["municipio"] == "Gama/MG" and len(p) == 3

    def t4():
        """Arquivo ausente não derruba e não vira fila vazia inventada."""
        return carregar(lambda nome: None) == []

    def t5():
        """TRAVA ESTRUTURAL: este script não escreve no banco.

        A checagem olha só o CÓDIGO — comentário e texto saem antes, pelo tokenizador do próprio
        Python. Sem isso a trava reprova por causa da prosa que a explica, e foi o que aconteceu
        ao escrevê-la: é o defeito que toda trava por texto cru tem, confundir a menção de um
        nome com a chamada dele."""
        import io as _io
        import re
        import tokenize
        fonte = (RAIZ / "scripts" / "preparar_fila_revisao.py").read_text(encoding="utf-8")
        pedacos = []
        for t in tokenize.generate_tokens(_io.StringIO(fonte).readline):
            if t.type not in (tokenize.COMMENT, tokenize.STRING):
                pedacos.append(t.string)
        return not re.search(r"\bgravar\s*\(|\bDATA\s*/", " ".join(pedacos))

    def t6():
        """O relatório mostra o trecho — é ele que permite descartar sem abrir o documento."""
        f = carregar(lambda nome: FIX.get(nome))
        h = montar_html(f, "25/09/2026 18:00")
        return "Beta/MG" in h and "candidato_forte" in h and "Delta" not in h

    return rodar_autoteste({
        "ordena por confiança, depois triagem, depois pontos": t1,
        "item já julgado sai da fila (pelos dois caminhos)": t2,
        "falso positivo provável vai ao fim, nunca é excluído": t3,
        "fila ausente não derruba nem vira fila vazia": t4,
        "trava: não escreve em data/": t5,
        "o relatório mostra o trecho e omite o já julgado": t6,
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else principal(sys.argv[1:]))
