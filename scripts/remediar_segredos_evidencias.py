#!/usr/bin/env python3
"""
scripts/remediar_segredos_evidencias.py — credencial de terceiro em evidência já preservada
===========================================================================================
ACHADO (alerta do GitHub, 01/10/2026: "Possible valid secrets detected")
------------------------------------------------------------------------
`evidencias/84cd5fbf….html` — uma página oficial salva como prova — trazia, em um dos seus 51
`<script>`, a **chave de API do Flickr do próprio sítio**. O `netlify.toml` publica a raiz do
repositório (`publish = "."`), de modo que a cópia preservada é servida pelo nosso domínio: com ela,
a credencial de um terceiro que nunca nos autorizou a redistribuí-la.

A fonte original já publicava a chave, e isso não nos desobriga. Republicá-la indexada no domínio do
projeto é um ato nosso, e é a mesma razão de minimização que fundamentou `redigir_dados_pessoais` em
12/09/2026 — ali para CPF de terceiros, aqui para credencial de terceiros.

A causa raiz foi corrigida em `coletores_base.preservar_evidencia`: evidência de TEXTO nova sai
redigida **antes** do hash. Este script trata o que já está no disco:

1. redige a credencial com `coletores_base.redigir_segredos` (redige o VALOR, nunca o nome do campo
   — quem auditar continua vendo que havia uma chave ali, e onde);
2. recalcula o hash do arquivo redigido e **troca a chave** do item em `data/evidencias.json`,
   guardando a anterior em `hash_antes_da_redacao`. A troca é necessária, não cosmética: o portão de
   evidências exige `sha256(arquivo) == chave`, e é essa igualdade que faz a cópia ser verificável;
3. renomeia o arquivo para o hash novo, pelo mesmo motivo;
4. nunca apaga arquivo nem registro: a prova do documento continua inteira, só a credencial sai.

Idempotente: rodar de novo em arquivo já redigido não encontra nada e não escreve.

  python3 scripts/remediar_segredos_evidencias.py             # aplica
  python3 scripts/remediar_segredos_evidencias.py --dry-run   # só relata
  python3 scripts/remediar_segredos_evidencias.py --autoteste # sem rede, sem escrita em evidencias/
"""
import hashlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

EVID = RAIZ / "evidencias"
EXTENSOES = (".html", ".htm", ".txt", ".json", ".xml", ".csv")


def arquivos_de_texto(evid: pathlib.Path = None) -> list:
    """Os arquivos de evidência em que faz sentido procurar credencial. Função pura."""
    evid = evid or EVID
    if not evid.exists():
        return []
    return sorted(p for p in evid.iterdir()
                  if p.is_file() and p.suffix.lower() in EXTENSOES)


def achar_segredos(caminho: pathlib.Path) -> tuple:
    """(texto_redigido, quantidade) do arquivo, ou (None, 0) quando não há o que redigir.

    Arquivo que não decodifica em UTF-8 não é tratado: preferimos deixá-lo intacto e visível no
    relatório a arriscar reescrever prova com uma decodificação adivinhada.
    """
    from coletores_base import redigir_segredos
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None, 0
    limpo, n = redigir_segredos(texto)
    return (limpo, n) if n else (None, 0)


def remediar(dry_run: bool = False) -> int:
    from coletores_base import gravar, ler
    idx = ler("evidencias.json", {"itens": {}})
    itens = idx.get("itens", {})
    por_arquivo = {str(it.get("arquivo") or ""): h for h, it in itens.items()}
    tratados = 0
    for caminho in arquivos_de_texto():
        limpo, n = achar_segredos(caminho)
        if not n:
            continue
        rel = caminho.relative_to(RAIZ).as_posix()
        novo_hash = hashlib.sha256(limpo.encode("utf-8")).hexdigest()
        antigo = por_arquivo.get(rel)
        print(f"  {rel}: {n} credencial(is) · hash {str(antigo)[:12]}… → {novo_hash[:12]}…")
        tratados += 1
        if dry_run:
            continue
        novo_nome = EVID / f"{novo_hash}{caminho.suffix}"
        caminho.write_text(limpo, encoding="utf-8", newline="\n")
        if novo_nome != caminho:
            caminho.rename(novo_nome)
        if antigo and antigo in itens:
            item = itens.pop(antigo)
            item["arquivo"] = novo_nome.relative_to(RAIZ).as_posix()
            item["tamanho"] = len(limpo.encode("utf-8"))
            item["segredos_redigidos"] = n
            item["hash_antes_da_redacao"] = antigo
            itens[novo_hash] = item
    if tratados and not dry_run:
        idx["itens"] = itens
        gravar("evidencias.json", idx)
    print(f"{'(dry-run) ' if dry_run else ''}{tratados} arquivo(s) com credencial de terceiro"
          + (" — nada a fazer" if not tratados else ""))
    return 0


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    import tempfile
    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t)
        com = d / "a.html"
        com.write_text('<script>var f={api_key: "4a01c0deadbeef1234567890"};</script>',
                       encoding="utf-8", newline="\n")
        sem = d / "b.html"
        sem.write_text("<p>Plano de Contingência 2026</p>", encoding="utf-8", newline="\n")
        pdf = d / "c.pdf"
        pdf.write_bytes(b"%PDF-1.4 api_key: 4a01c0deadbeef1234567890")

        alvos = arquivos_de_texto(d)
        ok("só arquivo de texto entra na varredura", pdf not in alvos and com in alvos)
        limpo, n = achar_segredos(com)
        ok("a credencial é encontrada", n == 1)
        ok("o nome do campo fica, o valor sai",
           "api_key" in limpo and "4a01c0deadbeef1234567890" not in limpo)
        ok("página sem credencial não é tocada", achar_segredos(sem) == (None, 0))
        ok("segunda passada no texto já redigido não encontra nada",
           achar_segredos(sem)[1] == 0)
        from coletores_base import redigir_segredos
        ok("idempotente: redigir o redigido não muda nada",
           redigir_segredos(limpo)[1] == 0)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "remediar", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções de leitura não escrevem",
       not ({"write_text", "write_bytes", "rename", "gravar"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita em evidencias/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    return remediar(dry_run="--dry-run" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
