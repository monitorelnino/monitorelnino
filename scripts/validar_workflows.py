#!/usr/bin/env python3
"""Valida os workflows do GitHub Actions com detecção de CHAVE DUPLICADA (o pyyaml aceita em
silêncio; o GitHub recusa o workflow inteiro — 03/09/2026: um 'env' duplicado quebrou a rotina).
Roda no portão 1 (verificar_estrutura.js chama este script) e na checagem de PR."""
import glob, pathlib, sys, yaml
class Dup(yaml.SafeLoader): pass
def cons(loader, node):
    keys = [loader.construct_object(k) for k, _ in node.value]
    dup = [k for k in keys if keys.count(k) > 1]
    if dup: raise ValueError(f"chave duplicada {sorted(set(dup))}")
    return yaml.SafeLoader.construct_mapping(loader, node, deep=True)
Dup.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cons)
erros = 0
carregados = {}
for f in sorted(glob.glob(".github/workflows/*.yml")):
    try: carregados[f] = yaml.load(open(f, encoding="utf-8"), Loader=Dup)
    except Exception as e: print(f"  ✗ {f}: {e}"); erros += 1

# TETO DE TEMPO EM TODO JOB (23/09/2026). Achado real: a rodada diária de 23/09 ficou 45+ min
# presa numa fonte que não respondia. O job não declarava `timeout-minutes`, então herdava as
# SEIS HORAS de padrão do GitHub; com a trava de concorrência do workflow de atualização
# (`cancel-in-progress: false`), isso vira a fila parada o dia inteiro — e nada reprova, porque
# um job pendurado não é um job vermelho. Só foi notado porque alguém foi olhar.
#
# O teto é por JOB e não por passo de propósito: um passo sem teto dentro de um job com teto
# ainda termina; um job sem teto, não. Workflow novo nasce com a rede de segurança.
TETO_MAXIMO_MIN = 360   # o padrão do GitHub; declarar 360 é o mesmo que não declarar nada
sem_teto = []
for f, wf in carregados.items():
    for nome, job in ((wf or {}).get("jobs") or {}).items():
        if not isinstance(job, dict) or job.get("uses"):
            continue            # job que só chama workflow reutilizável herda o teto de lá
        t = job.get("timeout-minutes")
        if t is None:
            sem_teto.append(f"{f}: job '{nome}' sem timeout-minutes (herda 6 h do GitHub)")
        elif isinstance(t, int) and t >= TETO_MAXIMO_MIN:
            sem_teto.append(f"{f}: job '{nome}' com timeout-minutes={t} — igual ou maior que "
                            f"o padrão de {TETO_MAXIMO_MIN} min, não é teto nenhum")
for m in sem_teto:
    print(f"  ✗ {m}")
erros += len(sem_teto)

# A LISTA DO COMMIT COBRE O QUE A RODADA REESCREVE (23/09/2026). Achado real: o passo de
# commit da rodada de atualização nomeava só `index.html` e `defesa-civil.html`. Mas
# preencher_fallback_estatico.py reescreve também saude.html e financiamento.html — que é o
# que o leitor SEM JavaScript vê, e o que o aria-label da barra de progresso anuncia ao
# leitor de tela — e carimbar_assets.py reescreve as 12 páginas.
#
# O resultado não era só portão 12 vermelho: o manifesto guardava o hash da página NOVA
# enquanto a página VELHA continuava no ar. A página de Saúde serviu 31,8 durante duas
# rodadas, quando o valor era 32,5; "17 estados verificados", quando eram 20. Silencioso,
# porque descartar uma mudança no `git add` não produz erro nenhum.
paginas = sorted(pathlib.Path(".").glob("*.html"))
# A cobrança vale só para quem REESCREVE página: carimbar_assets e preencher_fallback_estatico
# mexem no HTML, e gerar_manifesto sela o hash delas. Workflow que só commita evidência ou
# dado não tem página a perder — e portão que cobra o que não se aplica acaba desligado.
REESCREVE = ("carimbar_assets", "preencher_fallback_estatico", "gerar_manifesto")
for f, wf in carregados.items():
    texto = open(f, encoding="utf-8").read()
    if not any(x in texto for x in REESCREVE):
        continue
    for linha in texto.splitlines():
        t = linha.strip()
        if not t.startswith("git add ") or " -A" in t:
            continue
        caminhos = t[len("git add "):].split()
        if "*.html" in caminhos or "." in caminhos:
            continue          # glob cobre as páginas de hoje e as de amanhã
        fora = [pg.name for pg in paginas if pg.name not in caminhos]
        if fora:
            print(f"  ✗ {f}: `git add` não cobre {len(fora)} página(s) que a cadeia de "
                  f"derivados reescreve: {', '.join(fora[:4])}"
                  f"{'…' if len(fora) > 4 else ''} — a mudança seria descartada em silêncio, "
                  f"e o manifesto guardaria o hash da versão que não foi commitada")
            erros += 1

print("✓ WORKFLOWS OK — YAML válido, sem chave duplicada, todo job com teto de tempo."
      if not erros else f"✗ WORKFLOWS: {erros} problema(s).")
sys.exit(1 if erros else 0)
