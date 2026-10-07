#!/usr/bin/env python3
"""Roda os portões locais DERIVANDO a lista de .github/workflows/portoes.yml (§167, 23/09/2026).

POR QUE EXISTE. Até hoje havia três listas de portões que divergiam entre si: a do CLAUDE.md
(páginas + validar_workflows), a numerada do PROTOCOLO §3.3 (mistura página e dado) e a do
próprio portoes.yml, que é a única que reprova de verdade. Rodar um subconjunto coerente com
uma das listas e passar batido por um portão que só existe noutra custou um ciclo de CI em
23/09/2026 (verificar_seguranca.js: Action sem SHA fixado).

A correção não é escrever a lista uma quarta vez: é parar de escrevê-la. Este script lê o
workflow e roda o que ele roda, na ordem em que ele roda. Portão novo no CI passa a valer
aqui sem ninguém lembrar de copiar.

SAÍDA ENXUTA, DE PROPÓSITO. Imprime uma linha por portão (a última linha da saída dele, que
nos scripts do projeto é sempre o veredito). Só o portão que reprova mostra saída completa.
A suíte inteira em modo verboso são centenas de linhas de ✓ que não informam nada e custam
contexto caro quando lidas por um agente.

Uso: python3 scripts/portoes_locais.py [paginas|dados|tudo|cor|texto] [--rapido]
                                       [--verboso] [--ate N] [--listar]
  paginas  portões que rodam sempre no CI (não dependem de dado ter mudado)
  dados    portões condicionados a `dado_mudou` no workflow (inclui autotestes de coletor)
  tudo     os dois, na ordem do workflow (padrão)
  cor      §237: os portões de página cujo ASSUNTO declarado é `cor` — tokens, leiaute,
           contraste, 375 px, figura, CSP, cabeça do HTML. Para troca de fonte, cor ou forma.
  texto    §237: os de assunto `texto` — legenda, vocabulário público, voz, ficha semântica,
           ausência declarada.
  --rapido §237: dentro do perfil pedido, só os que declaram a etiqueta `rapido` (respondem em
           até 2 s). É o laço de iterar, e NÃO substitui a suíte antes do PR.

O ASSUNTO não é escolhido aqui: vem declarado no próprio `portoes.yml`, numa linha
`# assunto: ...` imediatamente acima do comando — mesma disciplina da trilha, que é derivada da
condição do CI. O `CLAUDE.md` registra que subconjunto escolhido a olho custou um ciclo de CI em
23/09/2026, e `scripts/validar_workflows.py` reprova portão de página sem assunto declarado, para
que portão novo não fique fora dos perfis em silêncio.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / ".github" / "workflows" / "portoes.yml"

# Passos que existem no workflow mas NÃO são portão: diagnóstico, preparo de ambiente,
# publicação de relatório. Casados pelo nome do passo, que é estável e legível.
PASSOS_IGNORADOS = re.compile(
    r"diagn[óo]stico|relat[óo]rio|detectar se a mudan|checkout|setup|instalar|depend[êe]ncias",
    re.IGNORECASE)

# Uma linha de `run:` só vira portão se começa por um destes. `for c in ...` cobre o laço de
# autotestes de coletor, que roda como uma linha de shell.
INICIOS = ("python3 ", "node ", "bash ", "for c in ")


ASSUNTO = re.compile(r"^#\s*assunto:\s*(.+?)\s*$")


def comandos_do_workflow():
    """[(grupo, comando, assuntos)] na ordem do workflow. grupo ∈ {'paginas','dados'}.

    Classificação declarada: passo com `if: ... dado_mudou ...` é de dado; o resto é de
    página. É a mesma divisão que o CI faz, e por isso não inventa uma terceira semântica.

    §237: `assuntos` é o conjunto lido da linha `# assunto: ...` imediatamente acima do comando,
    no próprio workflow. Mesma disciplina: o perfil rápido não é escolhido aqui, é declarado lá."""
    import yaml
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = next(iter(wf["jobs"].values()))
    saida = []
    for passo in job.get("steps", []):
        nome = passo.get("name") or ""
        run = passo.get("run")
        if not run or PASSOS_IGNORADOS.search(nome):
            continue
        grupo = "dados" if "dado_mudou" in str(passo.get("if", "")) else "paginas"
        pendente = frozenset()
        for linha in run.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("#"):
                m = ASSUNTO.match(linha)
                if m:
                    pendente = frozenset(m.group(1).split())
                continue
            if linha.startswith(INICIOS):
                saida.append((grupo, linha, pendente))
            pendente = frozenset()      # o marcador vale para O comando seguinte, e só
    return saida


def rodar(cmd: str, verboso: bool) -> tuple:
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, cwd=RAIZ, capture_output=True, text=True)
    saida = (p.stdout or "") + (p.stderr or "")
    linhas = [x for x in saida.splitlines() if x.strip()]
    veredito = linhas[-1] if linhas else "(sem saída)"
    return p.returncode, veredito, saida, time.time() - t0


# O QUE BARRA A PUBLICACAO DE DADO, E O QUE NAO BARRA (item 4 do handover de 06/10/2026).
#
# Entre 03 e 06/10 a publicacao falhou 33 vezes, e as 33 foram portao de CODIGO reprovando num
# publicador de DADO: 29 por derivado obsoleto (gerador nao idempotente) e 3 por corrida no
# medidor de layout. Em nenhuma delas o dado estava errado.
#
# O principio: codigo que esta na `main` JA passou por esses portoes no PR. Quando eles reprovam de
# novo no publicador, o que pegam e nao determinismo -- nao erro. E parar a publicacao do dado do
# dia por nao determinismo de um portao de codigo e trocar um problema pequeno por um grande: o
# site fica velho, e ninguem olha o portao.
#
# BARRA: integridade do dado, segredo, dado pessoal, vocabulario proibido (dado externo traz
# palavra proibida) e pagina que nao RENDERIZA (erro de runtime).
# NAO BARRA: presenca e estrutura de layout, tipografia, CODEMAP, documentacao, e todo portao que
# so mede codigo. Reprovacao ali publica mesmo assim e abre Issue.
#
# Os portoes NAO mudam: continuam todos bloqueantes no PR, e a conformidade diaria do site
# publicado segue igual. O que muda e so o que barra a PUBLICACAO.
BARRAM_A_PUBLICACAO = (
    "verificar_esquema_de_pista",      # integridade do dado: quarentena por arquivo
    "verificar_seguranca",             # segredo e dado pessoal
    "verificar_evidencia_sem_segredo",
    "verificar_vocabulario_publico",   # dado externo pode trazer palavra proibida
    "verificar_palavras",
    "verificar_voz_editorial",
    "verificar_legendas",
    "verificar_runtime",               # pagina que nao renderiza
    "verificar_tamanho_dos_dados",     # arquivo que estourou nao sobe
    "verificar_marcadores_de_conflito",
    "verificar_escrita_portavel",
)


def barra_a_publicacao(comando: str) -> bool:
    """Este portao pode impedir a publicacao do dado do dia? Funcao pura."""
    return any(nome in str(comando or "") for nome in BARRAM_A_PUBLICACAO)


def main() -> int:
    args = sys.argv[1:]
    verboso = "--verboso" in args
    listar = "--listar" in args
    rapido = "--rapido" in args
    pedido = next((a for a in args if a in ("paginas", "dados", "tudo", "cor", "texto",
                                            "publicacao")), "tudo")
    ate = None
    if "--ate" in args:
        ate = int(args[args.index("--ate") + 1])

    todos = comandos_do_workflow()
    if pedido in ("cor", "texto"):
        # §237: perfil por assunto. Só portão de PÁGINA entra — mudança de fonte, cor, forma ou
        # texto público não toca data/, e os portões de dado não têm o que dizer sobre ela.
        cmds = [(g, c, a) for g, c, a in todos if g == "paginas" and pedido in a]
    elif pedido == "publicacao":
        cmds = [(g, c, a) for g, c, a in todos if barra_a_publicacao(c)]
    else:
        cmds = [(g, c, a) for g, c, a in todos if pedido == "tudo" or g == pedido]
    if rapido:
        cmds = [(g, c, a) for g, c, a in cmds if "rapido" in a]
    cmds = cmds[:ate]
    if listar:
        for i, (g, c, a) in enumerate(cmds, 1):
            print(f"{i:2}. [{g:7}] {c}")
        print(f"\n{len(cmds)} portão(ões) derivado(s) de {WORKFLOW.relative_to(RAIZ)}")
        return 0

    print(f"{len(cmds)} portão(ões) — derivados de {WORKFLOW.relative_to(RAIZ)}\n")
    falhou = None
    for i, (g, c, _a) in enumerate(cmds, 1):
        rotulo = c if len(c) <= 52 else c[:49] + "..."
        print(f"{i:2}/{len(cmds)} [{g:7}] {rotulo:<52} ", end="", flush=True)
        rc, veredito, saida, dt = rodar(c, verboso)
        if rc == 0:
            print(f"✓ {dt:5.1f}s")
            if verboso:
                print(saida)
        else:
            print(f"✗ {dt:5.1f}s")
            print("\n--- saída do portão que reprovou ---")
            print(saida[-4000:])
            falhou = c
            break          # para no primeiro vermelho: o resto perde o sentido

    if falhou:
        print(f"\n✗ PORTÕES: parou em `{falhou}`. Nada sobe com portão vermelho.")
        return 1
    print(f"\n✓ PORTÕES OK — {len(cmds)} portão(ões) verdes.")
    if pedido in ("cor", "texto") or rapido:
        print("  Perfil parcial: é o laço de iterar. Antes do PR, `tudo` — nada sobe com "
              "portão vermelho, e subconjunto escolhido a olho já custou um ciclo de CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
