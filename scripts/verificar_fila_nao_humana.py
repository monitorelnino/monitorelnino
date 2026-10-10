#!/usr/bin/env python3
"""verificar_fila_nao_humana.py — nenhuma fila espera por uma pessoa (lote 2.9, A1-17, A7-27).

Decisão de 08/10/2026: não há humano tomando decisões. O código julga sozinho, e fila que diz
"lido por humano", "julgamento humano" ou "revisão humana" é fila que nunca esvazia. Este portão
reprova três coisas:

  1. status (ou `status_triagem`) que menciona humano/humana, em qualquer fila — BLOQUEIA sempre;
  2. pista em `pendente_confirmacao…` há mais de 21 dias (o `dias_de_vida` do esquema). O estoque
     de 09/10 (3.415 do Google News sem data de registro, drenado pelo lote 2.6 à razão de ~200
     por noite) tem prazo declarado: até PRAZO_DO_ESTOQUE o portão nomeia o passivo e passa;
     depois, reprova. Pista sem data legível conta no passivo, nunca como nova;
  3. (10/10/2026, meta "zero humano") a palavra humano/humana em CÓDIGO ATIVO de *.py, *.js e
     *.yml versionados fora de `arquivo/` — rota, status, fila, modo, mensagem ou texto gerado.
     Comentário e docstring não contam (o histórico datado pode ficar). Python é lido por
     `tokenize`/`ast`; em JS e YAML, linha de comentário é a que começa com //, *, /* ou #, e o
     trecho depois de // (JS) ou de " #" (YAML) sai da conta. Exceção só pela lista curta
     EXCECOES_DE_CODIGO, com motivo.

USO
    python3 scripts/verificar_fila_nao_humana.py --autoteste
    python3 scripts/verificar_fila_nao_humana.py
"""
from __future__ import annotations

import ast
import datetime as dt
import io
import json
import pathlib
import re
import subprocess
import sys
import tokenize
from email.utils import parsedate_to_datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent

FILAS = (("data/pistas_imprensa.json", "pistas"),
         ("data/pistas_imprensa_saude.json", "pistas"),
         ("data/pistas_descobertas.json", "itens"),
         ("data/pistas_doe.json", "itens"),
         ("data/pistas_querido_diario.json", "pistas"),
         ("data/saude_no_plano_revisar.json", "fila"),
         ("data/decretos_conteudo_revisar.json", "fila"))
DIAS_DE_VIDA = 21
PRAZO_DO_ESTOQUE = "2026-11-15"
RE_HUMANO = re.compile(r"(?<![a-z])human[oa]s?(?![a-z])", re.I)

# Arquivos de código em que a palavra é legítima, com o motivo. Lista curta e explícita.
EXCECOES_DE_CODIGO = {
    "scripts/verificar_fila_nao_humana.py": "o próprio portão: o padrão e os casos do autoteste",
    "scripts/migrar_fim_da_etapa_humana.py": "migração histórica de 09/10/2026: lê o valor legado",
    "scripts/migrar_zero_humano.py": "migração histórica de 10/10/2026: lê os valores legados",
    "scripts/corrigir_log_do_aplicador.py": "conserto histórico do log (28/09/2026): traduz o nome legado",
    "gerar_tese.js": "fotografia datada da tese (27/08/2026), ferramenta de sessão fora da selagem",
}
# Os nomes de arquivo das exceções, que outros arquivos citam (portoes.yml, o portão do escritor).
NOMES_CITAVEIS = tuple(sorted({pathlib.PurePath(c).stem for c in EXCECOES_DE_CODIGO},
                              key=len, reverse=True))
EXTENSOES_DE_CODIGO = (".py", ".js", ".yml")


def _sem_nomes_citaveis(texto: str) -> str:
    for nome in NOMES_CITAVEIS:
        texto = texto.replace(nome, "")
    return texto


def _linhas_de_docstring(fonte: str) -> set:
    linhas = set()
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        return linhas
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant)
                and isinstance(no.value.value, str)):
            linhas.update(range(no.lineno, (no.end_lineno or no.lineno) + 1))
    return linhas


def ocorrencias_no_codigo(caminho: str, fonte: str) -> list:
    """[(linha, trecho)] com humano/humana em código ativo. Função pura.

    Python: todo token que não é comentário nem docstring. JS/YAML: linha que não é comentário,
    sem o trecho depois do marcador de comentário de fim de linha."""
    achados = []
    if caminho.endswith(".py"):
        doc = _linhas_de_docstring(fonte)
        try:
            for tk in tokenize.generate_tokens(io.StringIO(fonte).readline):
                if tk.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE):
                    continue
                if tk.type == tokenize.STRING and tk.start[0] in doc:
                    continue
                for k, linha in enumerate(tk.string.splitlines() or [tk.string]):
                    if RE_HUMANO.search(_sem_nomes_citaveis(linha)):
                        achados.append((tk.start[0] + k, linha.strip()[:100]))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            achados.append((0, "arquivo Python ilegível pelo tokenize"))
        return achados
    js = caminho.endswith(".js")
    em_bloco = False
    for n, bruta in enumerate(fonte.splitlines(), 1):
        s = bruta.strip()
        if js:
            if em_bloco:
                if "*/" not in s:
                    continue
                em_bloco, s = False, s.split("*/", 1)[1].strip()
            if s.startswith("/*"):
                if "*/" not in s:
                    em_bloco = True
                    continue
                s = s.split("*/", 1)[1].strip()
            if s.startswith(("//", "*")):
                continue
            codigo = re.split(r"(?<![:\\])//", s, maxsplit=1)[0]
        else:
            if s.startswith("#"):
                continue
            codigo = re.split(r"\s#", s, maxsplit=1)[0]
        if RE_HUMANO.search(_sem_nomes_citaveis(codigo)):
            achados.append((n, s[:100]))
    return achados


def arquivos_de_codigo() -> list:
    """Os *.py, *.js e *.yml versionados, fora de arquivo/ e das exceções."""
    try:
        saida = subprocess.run(["git", "ls-files", "--", *[f"*{e}" for e in EXTENSOES_DE_CODIGO]],
                               cwd=RAIZ, capture_output=True, text=True, check=True).stdout.splitlines()
    except Exception:  # noqa: BLE001 — sem git, varre a árvore
        saida = [str(p.relative_to(RAIZ)) for e in EXTENSOES_DE_CODIGO for p in RAIZ.rglob(f"*{e}")]
    return sorted(c for c in saida if c.endswith(EXTENSOES_DE_CODIGO)
                  and not c.startswith(("arquivo/", "node_modules/")) and "/node_modules/" not in c
                  and c not in EXCECOES_DE_CODIGO)


def codigo_ativo_humano(arquivos=None) -> list:
    """Uma linha por ocorrência em código ativo, fora das exceções."""
    falhas = []
    for rel in arquivos if arquivos is not None else arquivos_de_codigo():
        caminho = RAIZ / rel
        if not caminho.exists():
            continue
        fonte = caminho.read_text(encoding="utf-8", errors="replace")
        for n, trecho in ocorrencias_no_codigo(rel, fonte):
            falhas.append(f"{rel}:{n}: código ativo depende de pessoa — {trecho!r}")
    return falhas


def data_da_pista(p: dict):
    """A data mais confiável de entrada na fila, ou None. Função pura."""
    for campo in ("registrado_em", "descoberto_em", "data_publicacao", "data"):
        bruto = str(p.get(campo) or "").strip()
        if not bruto:
            continue
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", bruto)
        if m:
            return dt.date(int(m[1]), int(m[2]), int(m[3]))
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", bruto)
        if m:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
        try:
            return parsedate_to_datetime(bruto).date()
        except Exception:  # noqa: BLE001
            continue
    return None


def avaliar(filas: dict, hoje: dt.date) -> tuple:
    """(falhas, passivo). `filas` = {nome: [itens]}. Função pura."""
    falhas, passivo = [], 0
    vence = hoje.isoformat() > PRAZO_DO_ESTOQUE
    for nome, itens in filas.items():
        for p in itens or []:
            if not isinstance(p, dict):
                continue
            for campo in ("status", "status_triagem"):
                v = str(p.get(campo) or "")
                if RE_HUMANO.search(v):
                    falhas.append(f"{nome}: {campo} espera por pessoa — {v[:90]!r}")
            if str(p.get("status") or "").startswith("pendente_confirmacao"):
                d = data_da_pista(p)
                velha = d is None or (hoje - d).days > DIAS_DE_VIDA
                if velha:
                    if vence:
                        falhas.append(f"{nome}: pendente há mais de {DIAS_DE_VIDA} dias "
                                      f"({d or 'sem data'}) — {str(p.get('titulo') or p.get('url'))[:70]!r}")
                    else:
                        passivo += 1
    return falhas, passivo


def autoteste() -> int:
    hoje = dt.date(2026, 10, 9)
    depois = dt.date(2026, 11, 20)
    casos = [
        ("status com 'lido por humano' reprova",
         len(avaliar({"f": [{"status": "pista — exige documento primário lido por humano"}]}, hoje)[0]) == 1),
        ("status_triagem 'pendente_julgamento_humano' reprova",
         len(avaliar({"f": [{"status_triagem": "pendente_julgamento_humano"}]}, hoje)[0]) == 1),
        ("status sem pessoa passa",
         avaliar({"f": [{"status": "pista — na fila, aguardando busca dirigida e juiz"}]}, hoje) == ([], 0)),
        ("pendente de 30 dias antes do prazo do estoque: passivo, não falha",
         avaliar({"f": [{"status": "pendente_confirmacao_documento", "registrado_em": "2026-09-01"}]}, hoje)
         == ([], 1)),
        ("pendente de 30 dias depois do prazo do estoque: reprova",
         len(avaliar({"f": [{"status": "pendente_confirmacao_documento", "registrado_em": "2026-10-15"}]},
                     depois)[0]) == 1),
        ("pendente de 5 dias passa",
         avaliar({"f": [{"status": "pendente_confirmacao_documento", "registrado_em": "2026-11-15"}]}, depois)
         == ([], 0)),
        ("data do feed (RFC 822) é lida",
         data_da_pista({"data_publicacao": "Tue, 25 Aug 2026 07:00:00 GMT"}) == dt.date(2026, 8, 25)),
        ("sem data conta no passivo",
         avaliar({"f": [{"status": "pendente_confirmacao_documento"}]}, hoje) == ([], 1)),
        ("código Python: string ativa com 'humana' reprova",
         len(ocorrencias_no_codigo("a.py", 'x = {"modo": "verificacao_humana"}\n')) == 1),
        ("código Python: comentário e docstring histórico passam",
         ocorrencias_no_codigo("a.py", '"""Até 09/10 havia fila humana."""\n'
                                       '# revisão humana (histórico)\nx = 1\n') == []),
        ("código Python: f-string que pede pessoa reprova",
         len(ocorrencias_no_codigo("a.py", 'n = 1\nprint(f"{n} para triagem humana")\n')) == 1),
        ("código JS: comentário passa, valor ativo reprova",
         ocorrencias_no_codigo("a.js", "// leitura humana (histórico)\n/* fila humana\n antiga */\n"
                                       "const a = 1;\n") == []
         and len(ocorrencias_no_codigo("a.js", "const s = {leitura_humana: 2}; // nota\n")) == 1),
        ("código YAML: comentário passa, nome de passo reprova",
         ocorrencias_no_codigo("a.yml", "  # revisão humana de 22/09\n- run: echo ok  # humano\n") == []
         and len(ocorrencias_no_codigo("a.yml", "- name: Avisar revisão humana\n")) == 1),
        ("citação do nome de arquivo de uma exceção passa",
         ocorrencias_no_codigo("a.yml", "  python3 scripts/migrar_fim_da_etapa_humana.py --autoteste\n") == []),
        ("as exceções ficam fora da varredura",
         "scripts/verificar_fila_nao_humana.py" not in arquivos_de_codigo()),
    ]
    falhas = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if falhas:
        print(f"X AUTOTESTE: {len(falhas)} falha(s)")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    filas = {}
    for arq, chave in FILAS:
        caminho = RAIZ / arq
        if not caminho.exists():
            continue
        d = json.loads(caminho.read_text(encoding="utf-8"))
        filas[arq] = d.get(chave) if isinstance(d, dict) else d
    sys.path.insert(0, str(RAIZ))
    from coletores_base import hoje_editorial
    falhas, passivo = avaliar(filas, hoje_editorial())
    codigo = codigo_ativo_humano()
    if codigo:
        print(f"✗ CÓDIGO NÃO HUMANO: {len(codigo)} linha(s) de código ativo com humano/humana:")
        for f in codigo[:40]:
            print(f"  - {f}")
    if falhas:
        print(f"✗ FILA NÃO HUMANA: {len(falhas)} item(ns) esperando por pessoa ou vencidos:")
        for f in falhas[:30]:
            print(f"  - {f}")
    if codigo or falhas:
        return 1
    print(f"✓ CÓDIGO NÃO HUMANO OK — {len(arquivos_de_codigo())} arquivo(s) *.py/*.js/*.yml lidos, "
          f"{len(EXCECOES_DE_CODIGO)} exceção(ões) declarada(s).")
    print(f"✓ FILA NÃO HUMANA OK — nenhuma fila espera por pessoa; passivo declarado: {passivo} "
          f"pendente(s) antigo(s), prazo do estoque {PRAZO_DO_ESTOQUE}.")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
