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
# SINTAXE DO SHELL EM TODO `run:` (30/09/2026). Achado real: um `if/else` com DOIS `else`
# seguidos passou por este validador, pelo pyyaml e pelo GitHub — e só quebrou no runner, depois de
# esperar a fila, com "syntax error: unexpected 'else'". O YAML estava válido; o shell dentro dele,
# não. `bash -n` lê sem executar e custa milissegundos.
#
# As expressões do GitHub (`${{ ... }}`) viram um valor inócuo antes da checagem: elas não são
# shell, e deixá-las no texto faria o `bash -n` reclamar do que não é problema.
import re as _re
import subprocess as _sp
import tempfile as _tmp

_RE_EXPRESSAO = _re.compile(r"\$\{\{[^}]*\}\}")
erros_de_shell = []
for f, wf in carregados.items():
    for nome, job in ((wf or {}).get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for i, passo in enumerate(job.get("steps") or []):
            corpo = passo.get("run") if isinstance(passo, dict) else None
            if not corpo:
                continue
            limpo = _RE_EXPRESSAO.sub("x", corpo)
            with _tmp.NamedTemporaryFile("w", suffix=".sh", delete=False,
                                         encoding="utf-8", newline="\n") as t:
                t.write(limpo)
                caminho = t.name
            r = _sp.run(["bash", "-n", caminho], capture_output=True, text=True)
            pathlib.Path(caminho).unlink(missing_ok=True)
            if r.returncode != 0:
                rotulo = passo.get("name") or f"passo {i + 1}"
                detalhe = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "shell invalido"
                erros_de_shell.append(f"{f}: job '{nome}', {rotulo}: {detalhe}")
for m in erros_de_shell:
    print(f"  X {m}")
erros += len(erros_de_shell)

# 04/10/2026 (20:30) — PASSO COM `run` E `with` AO MESMO TEMPO: o GitHub rejeita o arquivo.
#
# Medido pela central: `busca_web_cadencia.yml` e `auditoria_seguranca.yml` passaram a aparecer no
# GitHub com o CAMINHO no lugar do nome, e cada push na `main` gerava um run `failure` com ZERO
# jobs — cinco vezes entre 13:40 e 14:29 BRT. A busca web não rodou desde 11:25, e a auditoria de
# segurança parou.
#
# A causa foi minha, e o YAML não acusava: ao inserir o tique oportunista nos workflows, o passo
# entrou NO MEIO do `actions/setup-python`, e o `with: { python-version }` dele ficou dentro do meu
# passo — que também tem `run`. Um passo com `run` e `with` é inválido para o GitHub e **válido**
# para qualquer parser YAML, porque sintaticamente é só um mapa com duas chaves. `actionlint` e
# este validador passavam; só o GitHub reprovava, e sem mensagem pela API.
#
# A trava é esta: nenhum passo tem `run` com `with` ou `uses`. São as três chaves que decidem o que
# o passo É, e duas delas juntas significam que alguém colou um passo dentro do outro.
EXCLUSIVAS = ("run", "uses")
passo_ambiguo = []
for f, wf in carregados.items():
    for nome, job in ((wf or {}).get("jobs") or {}).items():
        for i, passo in enumerate((job or {}).get("steps") or []):
            if not isinstance(passo, dict):
                continue
            rotulo = passo.get("name") or f"passo {i + 1}"
            if "run" in passo and "uses" in passo:
                passo_ambiguo.append(f"{f}: job '{nome}', {rotulo}: tem `run` E `uses` — um passo "
                                     f"ou executa um comando, ou usa uma ação")
            if "run" in passo and "with" in passo:
                passo_ambiguo.append(f"{f}: job '{nome}', {rotulo}: tem `run` E `with` — `with` é "
                                     f"de ação (`uses`); o GitHub rejeita o arquivo inteiro e o "
                                     f"workflow passa a aparecer com o caminho no lugar do nome")
for m in passo_ambiguo:
    print(f"  X {m}")
erros += len(passo_ambiguo)

# 04/10/2026 — `secrets` em `if` NÃO EXISTE, e o GitHub rejeita o arquivo inteiro.
#
# Medido: `pacote_do_blog.yml` entrou com `if: ${{ secrets.ROBO_DEPLOY_KEY != '' }}` num passo.
# O contexto `secrets` não está disponível em `if`, e a consequência não é o passo ser ignorado: o
# workflow passa a aparecer com o CAMINHO no lugar do nome e cada push gera um run `failure`. O
# painel dos temporizadores foi quem mostrou, na primeira execução real. A decisão sobre um segredo
# existir pertence ao `run`, onde ele chega como variável de ambiente.
segredo_em_if = []
for f, wf in carregados.items():
    for nome, job in ((wf or {}).get("jobs") or {}).items():
        alvos = [("job", job.get("if"))]
        for i, passo in enumerate((job or {}).get("steps") or []):
            alvos.append((passo.get("name") or f"passo {i + 1}", (passo or {}).get("if")))
        for rotulo, condicao in alvos:
            if condicao and "secrets." in str(condicao):
                segredo_em_if.append(
                    f"{f}: job '{nome}', {rotulo}: `secrets` em `if` — o contexto não existe ali e "
                    f"o GitHub rejeita o arquivo; teste a variável dentro do `run`")
for m in segredo_em_if:
    print(f"  X {m}")
erros += len(segredo_em_if)

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

# ASSUNTO DECLARADO EM TODO PORTÃO DE PÁGINA (§237, 26/09/2026). Os perfis rápidos de
# `portoes_locais.py` (`cor`, `texto`, `--rapido`) derivam de uma linha `# assunto: ...` acima de
# cada comando, no próprio portoes.yml — nunca de lista escolhida a olho, porque o CLAUDE.md
# registra que subconjunto escolhido assim custou um ciclo de CI em 23/09/2026.
#
# A trava existe para o defeito que este projeto já viu três vezes (§213, §222, §226): portão novo
# entra, ninguém o declara, e o perfil segue verde sem nunca rodá-lo. Silenciosamente, o laço de
# design passaria a cobrir menos do que quem o roda acredita.
import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
try:
    from portoes_locais import comandos_do_workflow as _cmds
except Exception as _e:                                   # noqa: BLE001
    print(f"  ✗ não deu para derivar os portões para conferir o assunto: {_e}")
    erros += 1
else:
    _sem = [c for g, c, a in _cmds() if g == "paginas" and not (a - {"rapido"})]
    if _sem:
        print(f"  ✗ {len(_sem)} portão(ões) de página sem `# assunto:` declarado — ficariam fora "
              f"dos perfis `cor` e `texto` em silêncio: {', '.join(c[:46] for c in _sem[:3])}"
              f"{'…' if len(_sem) > 3 else ''}")
        erros += 1

# §259 (27/09/2026): a reposição urgente do domínio não pode compartilhar fila com a rodada.
# `concurrency` no nível do workflow enfileira o RUN inteiro, e o job `repor_dominio_manual` foi
# construído para ser independente — mas ficava preso mesmo assim. Em 27/09 uma reposição
# disparada às 15h30 ficou `pending` porque a rodada das 13h14 ocupava o grupo, com até 300 min
# de teto. O grupo passou a ser CONDICIONAL, e este portão exige que continue sendo: sem isso, a
# regressão volta calada, e só aparece no dia em que o domínio estiver no ar errado.
import pathlib as _pl  # noqa: E402
_at = _pl.Path(__file__).resolve().parent.parent / ".github" / "workflows" / "atualizar.yml"
if _at.exists():
    _grupo = (yaml.safe_load(_at.read_text(encoding="utf-8")).get("concurrency") or {}).get("group", "")
    if "apenas_repor_dominio" not in str(_grupo):
        print("  ✗ atualizar.yml: o grupo de concorrência não é condicional em "
              "`apenas_repor_dominio` — a reposição urgente do domínio voltaria a esperar a "
              "rodada na fila, e é justamente quando ela é urgente que a rodada está correndo")
        erros += 1

# 28/09/2026 (§272): dois workflows agendados no MESMO minuto competem pelo runner sem necessidade, e
# no caso do publicador com a busca web isso põe um lendo enquanto o outro commita — o cenário de "main
# em movimento" que o laço de rebase-e-push do item 1a existe para sobreviver. Colisão não cancela nada
# (os grupos de concorrência são separados), então ela nunca aparece como falha: aparece como rodada
# lenta e conflito de push. Deslocar minutos custa nada; este portão impede que a colisão volte.
# A HORA continua livre — 06h e 22h são compromisso público. O que ele cobra é o minuto.
_agendados = {}
for _p in sorted((_pl.Path(__file__).resolve().parent.parent / ".github" / "workflows").glob("*.yml")):
    _d = yaml.safe_load(_p.read_text(encoding="utf-8")) or {}
    _gat = _d[True] if True in _d else (_d.get("on") or {})
    if not isinstance(_gat, dict):
        continue
    for _c in (_gat.get("schedule") or []):
        _campos = str(_c.get("cron", "")).split()
        if len(_campos) != 5:
            continue
        for _hh in str(_campos[1]).split(","):
            if _hh.strip().isdigit():
                _agendados.setdefault((_campos[0], _hh.strip(), _campos[4]), []).append(_p.name)
for (_m, _h, _dia), _quais in sorted(_agendados.items()):
    if len(_quais) > 1:
        print(f"  ✗ dois workflows no mesmo minuto ({_h}:{_m} UTC, dia-da-semana {_dia}): "
              f"{', '.join(_quais)} — desloque o minuto de um deles")
        erros += 1

# ───────── 05/10/2026 (item 3.2 do handover da noite confiável) ─────────
# NENHUM SCRIPT CANCELA RUN DE OUTRO.
#
# Na noite de 04→05/10 o job `diarios / coletar` foi cancelado às 01:14:09 UTC, dois minutos depois
# de começar, e com ele a coleta da noite. A API REST não diz QUEM cancela um run — `actor` e
# `triggering_actor` são quem disparou —, então essa pergunta não se responde pelo GitHub. O que se
# pode garantir é o lado de cá, e a varredura de 05/10 confirmou que hoje não há nenhum
# cancelamento automático na árvore.
#
# Esta trava existe para que continue assim: um `gh run cancel` acrescentado por conveniência
# reintroduziria, calada, a perda que custou a noite. Cancelar é decisão de quem está ao teclado.
#
# Concorrência NÃO é cancelamento: `cancel-in-progress` é configuração de grupo, e o publicador o
# usa de propósito (publicar duas vezes o mesmo estado não tem valor). Aqui o assunto é chamada
# explícita de cancelamento, em workflow ou em script.
import re as _re_cancel

_PADROES_DE_CANCELAMENTO = (
    (_re_cancel.compile(r"\bgh\s+run\s+cancel\b"), "gh run cancel"),
    (_re_cancel.compile(r"actions/runs/[^\s\"']*/cancel"), "chamada /cancel na API de runs"),
)
_RAIZ_CANCEL = _pl.Path(__file__).resolve().parent.parent
_CANCEL_IGNORA = ("arquivo/", "node_modules/", ".git/", "scripts/validar_workflows.py")

for _alvo in sorted(list(_RAIZ_CANCEL.glob(".github/workflows/*.yml"))
                    + list(_RAIZ_CANCEL.rglob("*.py"))
                    + list(_RAIZ_CANCEL.glob("scripts/*.sh"))):
    _rel = _alvo.relative_to(_RAIZ_CANCEL).as_posix()
    if _rel.startswith(_CANCEL_IGNORA) or _rel in _CANCEL_IGNORA:
        continue
    try:
        _fonte = _alvo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    for _n, _linha in enumerate(_fonte.splitlines(), start=1):
        _nua = _linha.strip()
        if _nua.startswith("#") or _nua.startswith("//"):
            continue
        for _padrao, _nome in _PADROES_DE_CANCELAMENTO:
            if _padrao.search(_nua):
                print(f"  ✗ {_rel}:{_n}: {_nome} — nenhum script cancela run de outro "
                      f"(item 3.2 de 05/10/2026). Cancelar é decisão de quem está ao teclado; "
                      f"automação que cancela apaga coleta sem aviso.")
                erros += 1
                break

print("✓ WORKFLOWS OK — YAML válido, sem chave duplicada, todo job com teto de tempo, "
      "todo portão de página com assunto declarado, reposição do domínio fora da fila da rodada, "
      "nenhum script cancelando run de outro."
      if not erros else f"✗ WORKFLOWS: {erros} problema(s).")
sys.exit(1 if erros else 0)
