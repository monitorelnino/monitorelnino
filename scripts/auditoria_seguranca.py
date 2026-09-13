#!/usr/bin/env python3
"""
scripts/auditoria_seguranca.py — auditoria semanal automatizada de segurança e integridade
=============================================================================================
Criado em 13/09/2026, a partir de uma auditoria adversarial manual que encontrou uma exposição
real de dados pessoais (CPF de terceiros em evidências de Diário Oficial preservadas — ver
CHANGELOG, §"LGPD"). Esta rotina automatiza as checagens que SÃO mecanicamente verificáveis
sem julgamento humano; não substitui uma auditoria manual completa, que exige leitura de
código e julgamento editorial (arquitetura, UX, semântica dos indicadores). Roda semanalmente,
nunca falha o build de dados (é diagnóstico, não bloqueante) — resultado vai ao robo-registro,
como os demais diagnósticos do projeto.

Cobre:
  A) dados pessoais (CPF) em qualquer arquivo servido publicamente (evidencias/, data/, feeds/,
     dados-abertos/, *.html) — a mesma classe de achado desta auditoria, verificada de novo a
     cada semana porque a causa raiz (preservar_texto_integral) já foi corrigida, mas uma fonte
     nova ou um coletor futuro pode reintroduzir o padrão sem essa proteção.
  B) segredos/credenciais óbvias hardcoded (padrões de token, chave privada) em código versionado.
  C) deriva de documentação: o comentário de portoes.yml sobre "quantos portões" ainda bate com
     a contagem real de passos no arquivo (achado desta sessão: dizia 12, eram 24+).
  D) integridade de evidencias.json (mesma regra do portão verificar_evidencias.py, chamado aqui
     de novo para ficar num relatório dedicado, não só no log de cada atualização diária).

Não corrige nada — só relata. Correção é decisão humana ou de uma sessão de edição dedicada,
igual ao resto do protocolo de auditoria (fases de diagnóstico e correção são separadas).
"""
import json, re, subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PADRAO_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
# padrões de segredo: os mesmos prefixos que um scanner de secrets comercial usaria; propositalmente
# conservador (poucos falsos positivos) — não é substituto de um scanner dedicado (gitleaks/trufflehog),
# é uma rede de segurança adicional, gratuita, sem dependência nova.
PADROES_SEGREDO = [
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "GitHub PAT (clássico)"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub PAT (fine-grained)"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
    (re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"), "Chave privada"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "Chave de API estilo OpenAI/Anthropic"),
]
DIRETORIOS_PUBLICOS = ["evidencias", "data", "feeds", "dados-abertos"]
EXTENSOES_PUBLICAS = {".txt", ".json", ".html", ".xml", ".csv", ".md"}


def varrer_dados_pessoais() -> list:
    achados = []
    for nome_dir in DIRETORIOS_PUBLICOS:
        d = RAIZ / nome_dir
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix not in EXTENSOES_PUBLICAS:
                continue
            try:
                texto = p.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            n = len(PADRAO_CPF.findall(texto))
            if n:
                achados.append((str(p.relative_to(RAIZ)), n))
    for p in RAIZ.glob("*.html"):
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        n = len(PADRAO_CPF.findall(texto))
        if n:
            achados.append((str(p.relative_to(RAIZ)), n))
    return achados


def varrer_segredos() -> list:
    achados = []
    saida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=False)
    arquivos = [RAIZ / f for f in saida.stdout.splitlines() if f]
    for p in arquivos:
        if not p.is_file() or p.suffix in {".pdf", ".png", ".jpg", ".jpeg"}:
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        for padrao, nome in PADROES_SEGREDO:
            if padrao.search(texto):
                achados.append((str(p.relative_to(RAIZ)), nome))
    return achados


def verificar_deriva_documentacao_portoes() -> list:
    """13/09/2026 (achado desta auditoria): o comentário de portoes.yml dizia '12 portões' quando
    o passo 'Portões 1–11' já continha 24 chamadas reais. Conta as chamadas de verificação
    (node/python3 a scripts de verificação) e compara com o número citado no comentário — não
    corrige a redação (isso é decisão editorial), só sinaliza quando divergem."""
    p = RAIZ / ".github" / "workflows" / "portoes.yml"
    if not p.exists():
        return ["portoes.yml não encontrado"]
    texto = p.read_text(encoding="utf-8")
    n_chamadas = len(re.findall(r"^\s*(?:node|python3|bash)\s+\S+\.(?:js|py|sh)", texto, re.M))
    m = re.search(r"os (\d+) portões", texto)
    if not m:
        return []
    n_citado = int(m.group(1))
    if abs(n_chamadas - n_citado) > 2:  # folga pequena: nem todo "portão" é uma chamada 1:1
        return [f"comentário cita {n_citado} portões, mas o arquivo tem {n_chamadas} chamadas de verificação — provável deriva de documentação"]
    return []


def main() -> int:
    relatorio = ["=== AUDITORIA SEMANAL DE SEGURANÇA E INTEGRIDADE ==="]

    dados_pessoais = varrer_dados_pessoais()
    relatorio.append(f"\n[A] Dados pessoais (CPF): {len(dados_pessoais)} arquivo(s) com ocorrência(s)")
    for caminho, n in dados_pessoais[:30]:
        relatorio.append(f"    {caminho}: {n} ocorrência(s)")
    if len(dados_pessoais) > 30:
        relatorio.append(f"    ... e mais {len(dados_pessoais) - 30}")

    segredos = varrer_segredos()
    relatorio.append(f"\n[B] Segredos/credenciais hardcoded: {len(segredos)} achado(s)")
    for caminho, nome in segredos[:30]:
        relatorio.append(f"    {caminho}: {nome}")

    deriva = verificar_deriva_documentacao_portoes()
    relatorio.append(f"\n[C] Deriva de documentação (portões): {len(deriva)} achado(s)")
    for d in deriva:
        relatorio.append(f"    {d}")

    ok_evidencias = subprocess.run([sys.executable, "verificar_evidencias.py"], cwd=RAIZ,
                                   capture_output=True, text=True, check=False)
    relatorio.append(f"\n[D] Integridade de evidencias.json (verificar_evidencias.py):")
    relatorio.append("    " + (ok_evidencias.stdout.strip() or ok_evidencias.stderr.strip()).replace("\n", "\n    "))

    total_achados = len(dados_pessoais) + len(segredos) + len(deriva) + (0 if ok_evidencias.returncode == 0 else 1)
    relatorio.append(f"\n=== RESUMO: {total_achados} categoria(s) com achado(s) de {4} verificadas ===")
    print("\n".join(relatorio))
    return 0  # diagnóstico: nunca falha o job — o valor está no relatório, não em bloquear


if __name__ == "__main__":
    sys.exit(main())
