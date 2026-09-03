#!/usr/bin/env python3
"""Geração canônica de docs/MANIFEST_SHA256.txt (selagem do pacote).

Criado pela correção C7 da auditoria de 29/08/2026: o manifesto era montado à
mão e não cobria os dois PDFs publicados (METODOLOGIA.pdf e
MARE_Indice_Documentacao.pdf) — um PDF adulterado em trânsito não seria
detectado. Adotada a saída forte do relatório (opção "a"): os PDFs entram na
selagem, com o manifesto regenerado após os PDFs (ordem canônica do
protocolo: portões verdes → gerar_pdf_*.py → gerar_manifesto.py →
conferência sha256sum -c).

DETERMINISMO DOS PDFs (R1 da segunda auditoria, 29/08/2026): até esta
correção, o reportlab embutia metadados de data/ID a cada build a partir do
relógio da máquina — dois PDFs de conteúdo idêntico tinham hashes diferentes,
e um auditor que regenerasse os PDFs via `gerar_pdf_*.py` via o manifesto
"quebrar" mesmo sem nenhuma divergência real de conteúdo (a selagem só
funcionava para quem recebia o pacote pronto, não para quem regenerava).
Corrigido em gerar_pdf_indice.py e gerar_pdf_metodologia.py fixando
SOURCE_DATE_EPOCH a partir da data de corte dos dados (data/meta.json) — os
PDFs agora são função determinística dos DADOS, não do instante de geração.
Este script verifica isso a cada `--check`: regenera os dois PDFs e confirma
que os hashes batem com os do manifesto vigente ANTES de conferir o restante
— se um auditor externo rodar `gerar_pdf_*.py` e depois `--check`, a
conferência deve fechar sem precisar regravar o manifesto.

ESCOPO DECLARADO DA SELAGEM (impresso no cabeçalho do próprio manifesto):
  núcleo — código (*.py, scripts/*.py, scripts/*.js), páginas (*.html), dados
  (data/*.json), documentação-fonte (*.md, docs/*.md), configuração
  (netlify.toml, package.json, package-lock.json, requirements.txt,
  .env.example, .github/workflows/*.yml, LICENSE) — e os dois PDFs publicados.
  Fora da selagem, por serem acessórios de sessão ou artefatos de auditoria
  externa: assets/, docs/sbom-*.cdx.json, docs/*-audit-resultado.json e
  gerar_tese.js (ferramenta de sessão, inventariada em docs/AUDITORIA_CODIGO.md
  §2 — correção C8).

Uso: python3 scripts/gerar_manifesto.py           (regrava o manifesto)
     python3 scripts/gerar_manifesto.py --check   (confere sem regravar)
"""
import datetime
import hashlib
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent.parent
MANIFESTO = RAIZ / "docs" / "MANIFEST_SHA256.txt"

FORA = {"gerar_tese.js"}  # ferramenta de sessão (C8): inventariada, não selada


def listar():
    """Devolve a lista ordenada de caminhos relativos cobertos pela selagem."""
    padroes = ["*.py", "*.html", "*.md", "scripts/*.py", "scripts/*.js",
               "data/*.json", "docs/*.md", "netlify.toml", "package.json",
               "package-lock.json", "requirements.txt", ".env.example",
               ".github/workflows/*.yml", "LICENSE",
               "METODOLOGIA.pdf", "MARE_Indice_Documentacao.pdf",
               # AUD-09 (auditoria externa 02/09/2026): derivados publicados também selados
               "dados-abertos/*.csv", "dados-abertos/datapackage.json", "CITATION.cff",
               "feeds/*.xml", "feeds/index.json", "selos/*.svg", "assets/*.css"]
    vistos = set()
    for pad in padroes:
        for p in RAIZ.glob(pad):
            rel = p.relative_to(RAIZ).as_posix()
            if p.is_file() and rel not in FORA:
                vistos.add(rel)
    return sorted(vistos)


def sha256(rel):
    """SHA-256 hexadecimal do arquivo relativo à raiz do pacote."""
    h = hashlib.sha256()
    h.update((RAIZ / rel).read_bytes())
    return h.hexdigest()


def gerar():
    """Monta o texto completo do manifesto, cabeçalho de escopo incluído."""
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    linhas = [
        f"# MANIFEST_SHA256 · Monitor El Niño Brasil · selado em {hoje} por scripts/gerar_manifesto.py",
        "# Escopo: código, páginas, dados, documentação-fonte, configuração E os dois PDFs publicados",
        "# (METODOLOGIA.pdf, MARE_Indice_Documentacao.pdf — C7 da auditoria de 29/08/2026; os PDFs são",
        "# regenerados com números vivos; desde a v2.2.3 são bit-deterministicos via SOURCE_DATE_EPOCH,",
        "# fixado a partir da data de corte dos dados — regenerar não muda o hash sem mudar os dados).",
        "# Fora da selagem (declarado): docs/sbom-*.cdx.json e docs/*-audit-resultado.json (relatórios de ferramenta), gerar_tese.js (ferramenta de sessão),",
        "# evidencias/ (cópias de documentos-fonte, indexadas por hash em data/evidencias.json), node_modules/ e arquivos de imagem. Tudo o mais versionado está selado (AUD-09).",
        "# (ferramenta de sessão — inventário em docs/AUDITORIA_CODIGO.md §2). Conferência: sha256sum -c",
    ]
    linhas += [f"{sha256(rel)}  {rel}" for rel in listar()]
    return "\n".join(linhas) + "\n"


def verificar_determinismo_pdfs():
    """Regenera os dois PDFs e confere que o hash bate com o do manifesto vigente.

    Prova viva de que R1 (2ª auditoria, 29/08/2026) está corrigido: um auditor
    que rode gerar_pdf_*.py de novo não deve ver o manifesto quebrar sem
    motivo. Roda os geradores como subprocesso (mesmo interpretador) para não
    poluir o processo atual com os efeitos colaterais de SOURCE_DATE_EPOCH.
    """
    import subprocess
    alvo = {"METODOLOGIA.pdf": None, "MARE_Indice_Documentacao.pdf": None}
    atual = MANIFESTO.read_text(encoding="utf-8") if MANIFESTO.exists() else ""
    for linha in atual.splitlines():
        for nome in alvo:
            if linha.endswith("  " + nome):
                alvo[nome] = linha.split()[0]
    for script, pdf in (("gerar_pdf_metodologia.py", "METODOLOGIA.pdf"),
                        ("gerar_pdf_indice.py", "MARE_Indice_Documentacao.pdf")):
        r = subprocess.run([sys.executable, str(RAIZ / script)], cwd=RAIZ,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"✗ DETERMINISMO — falha ao regenerar {pdf}: {r.stderr[-300:]}")
            return False
        novo_hash = sha256(pdf)
        if alvo[pdf] and novo_hash != alvo[pdf]:
            print(f"✗ DETERMINISMO QUEBRADO em {pdf}: hash mudou ao regenerar sem alterar dados "
                  f"(esperado {alvo[pdf][:12]}…, obtido {novo_hash[:12]}…) — ver R1, 2ª auditoria")
            return False
    print("✓ PDFs bit-deterministicos — regeneração não alterou os hashes (R1 corrigido)")
    return True


def main():
    """CLI: regrava o manifesto, ou com --check confere o publicado contra o recomputado."""
    if "--check" in sys.argv and not verificar_determinismo_pdfs():
        return 1
    novo = gerar()
    if "--check" in sys.argv:
        atual = MANIFESTO.read_text(encoding="utf-8") if MANIFESTO.exists() else ""
        # compara só as linhas de hash (o cabeçalho carrega a data da selagem)
        h = lambda t: [l for l in t.splitlines() if l and not l.startswith("#")]
        if h(atual) != h(novo):
            print("✗ MANIFESTO DESATUALIZADO — rode scripts/gerar_manifesto.py após regenerar os PDFs")
            return 1
        print(f"✓ MANIFESTO CONFERE — {len(h(novo))} arquivos selados")
        return 0
    MANIFESTO.write_text(novo, encoding="utf-8")
    print(f"docs/MANIFEST_SHA256.txt regravado — {len([l for l in novo.splitlines() if not l.startswith('#')]) - 1 + 1} arquivos selados (PDFs incluídos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
