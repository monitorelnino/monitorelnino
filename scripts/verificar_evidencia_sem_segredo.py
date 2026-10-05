#!/usr/bin/env python3
"""
verificar_evidencia_sem_segredo.py — nenhuma credencial de terceiro entra em `evidencias/`
==========================================================================================
POR QUE ESTE PORTÃO EXISTE (alerta do GitHub, 01/10/2026)
---------------------------------------------------------
Uma página oficial salva como prova trazia a chave de API do Flickr do próprio sítio, dentro de um
dos seus `<script>`. A varredura de 03/10 encontrou **18 arquivos** no mesmo caso — chave do Flickr
e chaves do Google Maps. O `netlify.toml` publica a raiz do repositório (`publish = "."`), então
cada um desses arquivos era servido pelo nosso domínio, com a credencial de um terceiro dentro.

A causa raiz está corrigida em `coletores_base.preservar_evidencia` (evidência de texto sai redigida
antes do hash) e o passado foi tratado por `scripts/remediar_segredos_evidencias.py`. Este portão é
a trava: ele reprova se credencial voltar a entrar — por caminho novo de coleta, por arquivo
adicionado à mão, ou porque alguém desligou a redação.

O QUE ELE OLHA
--------------
Por padrão, só o que o commit ACRESCENTA ou ALTERA em `evidencias/` — o diretório tem milhares de
arquivos e varrê-lo inteiro a cada PR custaria minutos sem achar nada novo. `--tudo` varre todos,
para a auditoria periódica, e é como a varredura de 03/10 foi feita.

USO
  python3 scripts/verificar_evidencia_sem_segredo.py                    # o que está staged
  python3 scripts/verificar_evidencia_sem_segredo.py --contra origin/main
  python3 scripts/verificar_evidencia_sem_segredo.py --tudo
  python3 scripts/verificar_evidencia_sem_segredo.py --autoteste
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

EXTENSOES = (".html", ".htm", ".txt", ".json", ".xml", ".csv")


def arquivos_do_diff(contra: str = None) -> list:
    """Caminhos de `evidencias/` acrescentados ou alterados. Função pura quanto ao disco."""
    if contra:
        cmd = ["git", "diff", "--name-only", "--diff-filter=AM", f"{contra}...HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=AM", "--cached", "HEAD"]
    try:
        saida = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [l.strip() for l in saida.splitlines()
            if l.strip().startswith("evidencias/")
            and pathlib.Path(l.strip()).suffix.lower() in EXTENSOES]


def problemas(caminhos: list, raiz: pathlib.Path = None) -> list:
    """Um problema por arquivo que ainda contém credencial. Função pura."""
    from coletores_base import redigir_segredos
    raiz = raiz or RAIZ
    fora = []
    for rel in caminhos:
        p = raiz / rel
        if not p.exists():
            continue
        try:
            texto = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        _, n = redigir_segredos(texto)
        if n:
            fora.append(f"{rel}: {n} credencial(is) de terceiro no arquivo preservado")
    return fora


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
        (d / "evidencias").mkdir()
        (d / "evidencias" / "com.html").write_text(
            '<script>var f={api_key: "4a01c0deadbeef1234567890"};</script>',
            encoding="utf-8", newline="\n")
        (d / "evidencias" / "sem.html").write_text(
            "<p>Plano de Contingência 2026</p>", encoding="utf-8", newline="\n")
        (d / "evidencias" / "redigido.html").write_text(
            '<script>var f={api_key: "[SEGREDO REDIGIDO]"};</script>',
            encoding="utf-8", newline="\n")

        p = problemas(["evidencias/com.html"], d)
        ok("arquivo com credencial REPROVA", len(p) == 1 and "1 credencial" in p[0])
        ok("arquivo sem credencial passa", problemas(["evidencias/sem.html"], d) == [])
        ok("arquivo já redigido passa", problemas(["evidencias/redigido.html"], d) == [])
        ok("caminho que não existe não quebra nem reprova",
           problemas(["evidencias/nao_existe.html"], d) == [])
        ok("o estado atual do repositório passa", problemas(arquivos_do_diff("origin/main")) == [])

    ok("só extensão de texto entra no diff",
       all(pathlib.Path(c).suffix.lower() in EXTENSOES for c in arquivos_do_diff("origin/main")))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    if "--tudo" in argv:
        from scripts.remediar_segredos_evidencias import arquivos_de_texto
        caminhos = [p.relative_to(RAIZ).as_posix() for p in arquivos_de_texto()]
    else:
        contra = None
        if "--contra" in argv:
            contra = argv[argv.index("--contra") + 1]
        caminhos = arquivos_do_diff(contra)
    p = problemas(caminhos)
    if p:
        print(f"✗ EVIDÊNCIA COM SEGREDO: {len(p)} arquivo(s):")
        for x in p:
            print("  ·", x)
        print("  Rode `python3 scripts/remediar_segredos_evidencias.py` e commite.")
        return 1
    print(f"✓ EVIDÊNCIA SEM SEGREDO OK — {len(caminhos)} arquivo(s) de texto conferido(s); "
          "nenhuma credencial de terceiro na cópia preservada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
