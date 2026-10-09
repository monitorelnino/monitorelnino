#!/usr/bin/env python3
"""Portão: autoteste de coletor não escreve no banco.

NASCEU DE PERDA DE DADO MEDIDA, em 02/10/2026. Os coletores que gravam `atos_resposta.json` tiveram
a chamada de escrita trocada por um ajudante de outro módulo, que carimbava e gravava. Pareceu
melhor: carimbo numa definição só. Mas `coletar_diarios_consorciados.py --autoteste` isola a escrita
**trocando o `gravar` do próprio módulo** por um falso — e um ajudante que chama o `gravar` de outro
módulo passa por fora da troca. O autoteste gravou a sua fixture no arquivo real: **907 eventos do
ciclo viraram 1**, e a página publicou 657 municípios com decreto em vez de 736 sem que nada
reprovasse. Só apareceu porque os números do mapa pareceram baixos.

A lição não é sobre aquele ajudante: é que o isolamento do autoteste **não era verificado**. Este
portão verifica. Ele guarda o resumo dos arquivos de banco, roda os autotestes declarados e exige
que nenhum tenha mudado.

Não substitui `revisor-de-trava` (que confere se o coletor TEM autoteste): confere se o autoteste
que existe mente sobre não escrever.

Uso:
    python3 scripts/verificar_autoteste_nao_escreve.py
    python3 scripts/verificar_autoteste_nao_escreve.py --autoteste
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Coletores cujo autoteste exercita o caminho de escrita (mocando `gravar`) — são eles que podem
# furar o isolamento. A lista cresce quando um coletor novo mocar escrita.
COLETORES = (
    "coletar_s2id.py",
    "coletar_doe.py",
    "coletar_diarios_municipais.py",
    "coletar_diarios_consorciados.py",
    "coletar_edicoes_doe.py",
    "coletar_recursos_resposta.py",
    # 05/10/2026: os coletores que passaram a gravar pela porta única
    # (`scripts/pistas.sincronizar` / `gravar_lote`). Entram aqui porque o furo que a migração
    # abriu foi exatamente este: um ajudante que chamasse `coletores_base.gravar` passaria por
    # fora da troca do autoteste e gravaria a fixture no arquivo real — e gravou, duas pistas de
    # fixture em `pistas_imprensa.json`, antes de a porta passar a receber `ler_fn`/`gravar_fn`.
    "descobrir_planos.py",
    "seguir_pistas.py",
    "monitorar_redes_oficiais.py",
    "monitorar_busca_web.py",
    # 08/10/2026 (A6-26): a varredura cobria dez dos trinta e seis scripts com autoteste. Entram
    # os que escrevem em `data/` na rodada real — que é a condição que torna o autoteste perigoso
    # — e os cinco que tinham autoteste verde e não estavam no `portoes.yml`.
    "coletar_cobertura_qd.py",
    "coletar_execucao_mps.py",
    "coletar_transferegov.py",
    "coletar_financiamento.py",
    "coletar_saude.py",
    "coletar_declarado_nacional.py",
    "coletar_sinais_risco.py",
    "atualizar_instrumentos_estaduais.py",
    "atualizar_populacao.py",
    "atualizar_recursos.py",
    "atualizar_marcos_severidade.py",
    "converter_contribuicao.py",
    "processar_contribuicoes.py",
    "monitorar_politica_por_inteiro.py",
    "ler_caixa_lai.py",
    "gerar_painel.py",
    "gerar_lai.py",
)
# Arquivos de banco que um autoteste jamais deve tocar. São os que guardam o ciclo inteiro: perder
# um deles é perder evidência, não refazer uma conta.
BANCO = (
    "atos_resposta.json",
    "municipios.json",
    "pistas_imprensa.json",
    "pistas_doe.json",
    "doe_ocorrencias.json",
    "resposta/recursos_liberados.json",
    "evidencias.json",
    "pistas_descobertas.json",
    "pistas_sinais.json",
    "pistas_rejeitadas.json",
    # 05/10/2026, achado na mesclagem do #555: o nosso lado tinha SEIS linhas MENOS que a base
    # comum em `data/log_buscas/2026-10.jsonl` — seis execuções reais do canal DOM contra
    # defesacivil.am.gov.br, apagadas por um autoteste de coletor que gravou no arquivo real. O log
    # é o livro-razão da coleta: ele só cresce, e perder linha dele é perder a prova de que a
    # consulta aconteceu. Era o mesmo furo das pistas, em arquivo que não estava nesta lista.
    "log_buscas_resumo.json",
    "log_buscas/2026-10.jsonl",
)


def resumo(caminhos) -> dict:
    """{nome: sha256 ou None}. Função pura sobre o sistema de arquivos."""
    fora = {}
    for rel in caminhos:
        p = RAIZ / "data" / rel
        fora[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    return fora


def mudaram(antes: dict, depois: dict) -> list:
    """Os arquivos que mudaram. Função pura — é ela que o autoteste exercita."""
    return sorted(k for k in antes if antes.get(k) != depois.get(k))


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

    ok("igual não acusa", mudaram({"a": "1"}, {"a": "1"}) == [])
    ok("conteúdo diferente acusa", mudaram({"a": "1"}, {"a": "2"}) == ["a"])
    ok("arquivo criado pelo autoteste acusa", mudaram({"a": None}, {"a": "2"}) == ["a"])
    ok("arquivo apagado pelo autoteste acusa", mudaram({"a": "1"}, {"a": None}) == ["a"])
    ok("ordem estável", mudaram({"b": "1", "a": "1"}, {"b": "2", "a": "2"}) == ["a", "b"])
    ok("todo coletor declarado existe", all((RAIZ / c).exists() for c in COLETORES))
    # 08/10/2026 (A6-26): quatro scripts tinham autoteste e ninguém o rodava, porque a flag se
    # chamava `--self-test` e o portão chama `--autoteste`. O nome canônico passa a ser cobrado.
    import re as _re
    sem_flag = []
    for c in COLETORES:
        fonte = (RAIZ / c).read_text(encoding="utf-8", errors="ignore")
        if not _re.search(r'--autoteste', fonte):
            sem_flag.append(c)
    ok("todo script declarado aceita `--autoteste` pelo nome canônico", not sem_flag)
    if sem_flag:
        print("        sem a flag canônica: " + ", ".join(sem_flag))
    ok("todo arquivo de banco declarado é caminho relativo",
       all(not r.startswith("/") for r in BANCO))
    ok("as duas listas não estão vazias", bool(COLETORES) and bool(BANCO))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    ruins = []
    for coletor in COLETORES:
        antes = resumo(BANCO)
        r = subprocess.run([sys.executable, coletor, "--autoteste"], cwd=str(RAIZ),
                           capture_output=True, text=True)
        depois = resumo(BANCO)
        tocados = mudaram(antes, depois)
        if tocados:
            ruins.append(f"{coletor}: o autoteste escreveu em {', '.join(tocados)}")
        if r.returncode != 0:
            ruins.append(f"{coletor}: o autoteste reprovou (código {r.returncode})")
    if ruins:
        print("✗ AUTOTESTE DE COLETOR ESCREVEU NO BANCO:")
        for x in ruins:
            print("   - " + x)
        return 1
    print(f"✓ OK — {len(COLETORES)} autoteste(s) de coletor rodaram sem tocar "
          f"{len(BANCO)} arquivo(s) de banco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
