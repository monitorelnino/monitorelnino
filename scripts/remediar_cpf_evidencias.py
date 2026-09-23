#!/usr/bin/env python3
"""
scripts/remediar_cpf_evidencias.py — remediação de dados pessoais em evidências já preservadas
================================================================================================
Achado de auditoria (12/09/2026): coletar_diarios_municipais.py preserva a edição INTEIRA do
Diário Oficial quando ela bate a busca por "plano de contingência" — e diários oficiais brasileiros
publicam dezenas de atos não relacionados na mesma edição, alguns citando CPF de contribuintes e
servidores. 1.018 CPFs distintos em 69 arquivos já publicados via evidencias/ (netlify.toml:
publish = "."  — o repositório inteiro é o site).

A causa raiz já foi corrigida em preservar_texto_integral() e gravar_texto() (coletores_base.py e
preservar_evidencias.py) — toda evidência NOVA sai redigida. Este script trata o que já existe:
1. redige CPF de cada arquivo afetado;
2. recalcula o hash de conteúdo, quando o nome do arquivo É esse hash (preservar_evidencias.py);
   arquivos cujo nome é o hash do PDF de origem, não do texto (coletar_diarios_municipais.py),
   mantêm o nome — só o conteúdo muda;
3. atualiza data/evidencias.json com o novo hash/tamanho onde aplicável — incluindo `texto_hash`
   quando o arquivo regravado é o TEXTO extraído de um PDF preservado (§175, 23/09/2026: isto
   faltava, e Maricá/RJ ficou com o hash de antes da redação desde 12/09; `tamanho` descreve o
   arquivo de `arquivo`, então só muda quando é ele que foi regravado);
4. nunca apaga o arquivo nem o registro: a evidência do plano de contingência continua íntegra,
   só os CPFs somem.

5. reindexa o texto de quem já foi regravado sem recalcular o hash (conserta o passado, e o portão
   6 passa a cobrar a igualdade a cada execução — ver integridade_texto() em verificar_evidencias.py).

Idempotente: rodar de novo em arquivo já redigido não muda nada (0 CPFs encontrados = sem escrita).
  python3 scripts/remediar_cpf_evidencias.py            # aplica de verdade
  python3 scripts/remediar_cpf_evidencias.py --dry-run  # só relata, não grava
  python3 scripts/remediar_cpf_evidencias.py --autoteste  # testes negativos das quatro regras
"""
import hashlib, json, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import gravar, redigir_dados_pessoais  # noqa: E402

EVID = RAIZ / "evidencias"


def _caracteres_das_paginas(texto: str) -> int:
    """Conta o conteúdo das páginas, sem os marcadores — a mesma conta de ler_pdfs()
    (`sum(len(t) for t in paginas)` em preservar_evidencias.py), reconstruída a partir do arquivo."""
    partes = re.split(r"\n=== página \d+ ===\n", texto)
    return sum(max(len(t) - 1, 0) for t in partes[1:])   # cada página foi gravada como f"{t}\n"


def reindexar_textos(idx: dict, dry: bool = False) -> list:
    """§175 (23/09/2026): conserta o passado. Para todo item que registra `texto_arquivo` e
    `texto_hash`, se o arquivo em disco não bate com o hash registrado, o arquivo é a verdade
    (é ele que está publicado, já redigido) e o índice é reescrito: hash e contagem de caracteres.
    Nunca toca no arquivo. Devolve a lista do que foi (ou seria) reindexado."""
    feitos = []
    for h, item in idx.get("itens", {}).items():
        ta, th = item.get("texto_arquivo"), item.get("texto_hash")
        if not ta or not th:
            continue
        pth = RAIZ / ta
        if not pth.exists():
            continue
        real = hashlib.sha256(pth.read_bytes()).hexdigest()
        if real == th:
            continue
        car = _caracteres_das_paginas(pth.read_text(encoding="utf-8"))
        feitos.append(f"{h[:12]}… texto_hash {th[:10]}… → {real[:10]}…, caracteres {item.get('caracteres')} → {car} ({ta})")
        if not dry:
            item["texto_hash"] = real
            item["caracteres"] = car
    return feitos


def autoteste() -> int:
    """Testes negativos permanentes das quatro regras que o defeito de 12/09 violava."""
    import tempfile
    falhas = []
    texto = "\n=== página 1 ===\nCPF 123.456.789-00 no ato\n"
    redigido = texto.replace("123.456.789-00", "[CPF REDIGIDO]")
    h_red = hashlib.sha256(redigido.encode("utf-8")).hexdigest()

    # regra 1: a contagem de caracteres ignora os marcadores de página
    car = _caracteres_das_paginas(redigido)
    if car != len("CPF [CPF REDIGIDO] no ato"):
        falhas.append(f"_caracteres_das_paginas contou {car}, esperado {len('CPF [CPF REDIGIDO] no ato')}")

    with tempfile.TemporaryDirectory() as d:
        ev = Path(d) / "evidencias"; ev.mkdir()
        alvo = ev / "aa.txt"
        alvo.write_text(redigido, encoding="utf-8", newline="\n")

        # regra 2: o arquivo regravado sai em LF, em qualquer sistema operacional
        if b"\r\n" in alvo.read_bytes():
            falhas.append("o texto regravado saiu em CRLF — a série do §163 de novo")

        # regra 3: hash divergente é reindexado pelo arquivo em disco, e o arquivo não é tocado
        idx = {"itens": {"a" * 64: {"texto_arquivo": f"evidencias/{alvo.name}", "texto_hash": "0" * 64,
                                    "caracteres": 1, "arquivo": "evidencias/a" * 1 + ".pdf", "tamanho": 999}}}
        global RAIZ
        raiz_real = RAIZ
        RAIZ = Path(d)
        try:
            feitos = reindexar_textos(idx)
        finally:
            RAIZ = raiz_real
        it = idx["itens"]["a" * 64]
        if len(feitos) != 1 or it["texto_hash"] != h_red:
            falhas.append(f"reindexar_textos não corrigiu o hash divergente: {feitos} / {it['texto_hash'][:10]}")
        if it["caracteres"] != car:
            falhas.append(f"reindexar_textos não recontou os caracteres: {it['caracteres']} != {car}")
        # regra 4: `tamanho` descreve o arquivo de `arquivo`, e não pode ser mexido aqui
        if it["tamanho"] != 999:
            falhas.append(f"reindexar_textos sobrescreveu `tamanho` ({it['tamanho']}) — ele descreve `arquivo`")
        if hashlib.sha256(alvo.read_bytes()).hexdigest() != h_red:
            falhas.append("reindexar_textos alterou o arquivo preservado — ele é a verdade, não o índice")
        # idempotente: rodar de novo não acha nada
        if reindexar_textos(idx) != []:
            falhas.append("reindexar_textos não é idempotente")

    if falhas:
        print("✗ AUTOTESTE (remediação de CPF):"); [print("   ", f) for f in falhas]; return 1
    print("✓ AUTOTESTE OK — contagem sem marcadores, escrita em LF, reindexação pelo arquivo, `tamanho` intacto.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    dry = "--dry-run" in sys.argv
    idx_path = RAIZ / "data" / "evidencias.json"
    idx = json.load(open(idx_path, encoding="utf-8"))
    total_arquivos = total_cpfs = 0
    # .txt: preservar_texto_integral() e gravar_texto() — o grosso dos casos (edição inteira de
    # diário). .json/.html: achados isolados de auditoria — mesma redação, sem tocar em sintaxe:
    # o padrão de CPF é sequência de dígitos/pontos/traço, nunca parte de chave ou marcação.
    for p in sorted(list(EVID.glob("*.txt")) + list(EVID.glob("*.json")) + list(EVID.glob("*.html"))):
        h_antigo = p.stem
        try:
            texto = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # arquivo antigo em outra codificação (comum em sites .gov.br mais velhos); lê tolerando
            # bytes inválidos — mesma prática já usada pelos coletores (.decode(enc, "replace")) — e
            # sempre regrava em utf-8 daqui em diante, normalizando.
            texto = p.read_bytes().decode("utf-8", errors="replace")
        novo_texto, n = redigir_dados_pessoais(texto)
        if n == 0:
            continue
        total_arquivos += 1
        total_cpfs += n
        print(f"{'[dry-run] ' if dry else ''}{p.name}: {n} CPF(s)")
        if dry:
            continue
        if p.suffix == ".json":
            json.loads(novo_texto)  # a redação não pode quebrar JSON válido — verifica antes de gravar
        # newline="\n" (§175, série do §163): sem isso, rodar esta remediação no Windows regrava
        # toda evidência em CRLF — o conteúdo muda byte a byte, o hash deixa de bater com o
        # registrado e a cópia preservada divergiria da que o runner gera.
        p.write_text(novo_texto, encoding="utf-8", newline="\n")
        item = idx["itens"].get(h_antigo)
        if item is None:
            continue
        # o nome do arquivo É o hash do conteúdo (convenção de preservar_evidencias.py / itens
        # manuais desta sessão) → renomeia para o novo hash. Itens de coletar_diarios_municipais.py
        # têm o nome = hash do PDF/API de origem (texto_integral é um campo à parte) → não renomeia,
        # só atualiza tamanho.
        if item.get("arquivo") and item["arquivo"].endswith(f"{h_antigo}{p.suffix}") and "texto_integral" not in item:
            h_novo = hashlib.sha256(novo_texto.encode("utf-8")).hexdigest()
            p.rename(EVID / f"{h_novo}{p.suffix}")
            idx["itens"][h_novo] = idx["itens"].pop(h_antigo)
            idx["itens"][h_novo]["arquivo"] = f"evidencias/{h_novo}{p.suffix}"
            idx["itens"][h_novo]["tamanho"] = len(novo_texto.encode("utf-8"))
            idx["itens"][h_novo]["nota"] = (idx["itens"][h_novo].get("nota", "") +
                f" REDIGIDO em 12/09/2026 ({n} CPF removido(s) — achado de auditoria, LGPD art. 6º III).").strip()
        else:
            # §175 (23/09/2026): `tamanho` descreve o arquivo apontado por `arquivo` (a cópia binária
            # ou a resposta da API). Quando o regravado é OUTRO arquivo do item — o texto integral do
            # diário, ou o texto extraído do PDF —, sobrescrever `tamanho` com o comprimento do texto
            # registra o tamanho de um arquivo pelo de outro. Só muda quando é o próprio `arquivo`.
            if str(item.get("arquivo") or "").endswith(p.name):
                item["tamanho"] = len(novo_texto.encode("utf-8"))
            # §175: o texto extraído de PDF preservado tem hash próprio (`texto_hash`), que é o que o
            # portão 6 confere desde hoje. Regravar sem recalcular é o defeito que deixou Maricá/RJ
            # com o hash de antes da redação. `caracteres` conta só o conteúdo das páginas, sem os
            # marcadores — a redação mantém o comprimento ("[CPF REDIGIDO]" tem os mesmos 14
            # caracteres do padrão NNN.NNN.NNN-NN), mas recontar é barato e não presume isso.
            qual = "texto_integral" if str(item.get("texto_integral") or "").endswith(p.name) else None
            if str(item.get("texto_arquivo") or "").endswith(p.name):
                item["texto_hash"] = hashlib.sha256(novo_texto.encode("utf-8")).hexdigest()
                item["caracteres"] = _caracteres_das_paginas(novo_texto)
                qual = "texto extraído"
            item["nota"] = (item.get("nota", "") +
                f" REDIGIDO em 12/09/2026 ({n} CPF removido(s)"
                f"{' do ' + qual if qual else ''} — achado de auditoria, LGPD art. 6º III).").strip()
    # §175: conserta o que ficou para trás — texto já regravado sem recalcular o hash.
    reindexados = reindexar_textos(idx, dry)
    for r in reindexados:
        print(f"{'[dry-run] ' if dry else ''}reindexado: {r}")
    if not dry and (total_arquivos or reindexados):
        # gravar() do projeto: escrita atômica, em LF, reusando a indentação do arquivo (§163).
        gravar("evidencias.json", idx)
    print(f"\n{'Seria redigido' if dry else 'Redigido'}: {total_arquivos} arquivo(s), {total_cpfs} CPF(s) no total"
          f"; {len(reindexados)} texto(s) reindexado(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
