---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---

<!-- ─────────────────────────────────────────────────────────────────────────────
BLOCO DO PROJETO — acrescentado em 26/09/2026 pela editoria do MARÉ.
Tudo o que vem depois do último delimitador de comentário deste arquivo é LITERAL
da origem, sem uma vírgula alterada, para que qualquer pessoa possa compará-lo
com a fonte. Este bloco evita de propósito citar trechos de lá: cada citação
atrapalharia essa comparação.
───────────────────────────────────────────────────────────────────────────────── -->

## Procedência (lida, não suposta)

- **Origem:** <https://github.com/multica-ai/andrej-karpathy-skills>
- **Commit:** `2c606141936f1eeef17fa3043a72095b4765b9c2` (20/04/2026)
- **Trazida em:** 26/09/2026, arquivo `skills/karpathy-guidelines/SKILL.md`
- **Licença:** o frontmatter acima e o `plugin.json` da origem declaram MIT. **O repositório não
  tem arquivo `LICENSE`** — conferido pela API do GitHub, que devolve 404 e `license: null`. Como
  este repositório é público, fica registrado o que existe e o que não existe.
- Trazida como **cópia**, e não como plugin de marketplace: cópia é auditável no diff, e não cria
  dependência de terceiro na cadeia de execução do projeto.

## Precedência — onde esta skill vale, e onde ela cede

> **REVOGAÇÃO, 27/09/2026 (noite) — ler antes do resto desta seção.** O que vem abaixo registra a
> decisão de **26/09** (§238), e a parte dela sobre **interação foi revogada no dia seguinte**: o
> `CLAUDE.md` (§ "Histórico de regimes") diz que a editoria desfez o regime de 26/09 porque "o
> código conversava demais e pedia decisões que sabia tomar". A regra em vigor é **autonomia
> decisória responsável**: analisar → decidir → implementar → testar → verificar → corrigir →
> continuar, sem narrar e sem pedir permissão fora das paradas que o `CLAUDE.md` lista.
>
> Então, hoje: **o §1 "pergunte" NÃO vale** para decisão técnica de rotina — vale a lista de paradas
> do `CLAUDE.md` (credencial que não existe · exclusão irreversível · mudança de regra, peso ou
> régua do índice · alteração material de texto público · licença e distribuição · risco jurídico ou
> de privacidade · conflito real entre requisitos · impedimento que persista após diagnóstico
> razoável). O **§3 "Surgical Changes" continua valendo integralmente**, e o §2 e o §4 também: esta
> skill segue sendo a referência de **qualidade de código** (escopo, simplicidade, nada de mudança
> gratuita), não de interação. Nas colisões, **vence o `CLAUDE.md`**.
>
> O texto de 26/09 fica abaixo como histórico, não como instrução — apagá-lo esconderia a troca, e a
> troca é a informação.

Ela é **subordinada** às três fontes de verdade do projeto (`METODOLOGIA.md`,
`AI_EDITORIAL_NARRATIVE_GOVERNANCE.md`, `AI_VISUAL_ART_DIRECTION.md`), que são limite de prova e de
governança e não se negociam. Já nas duas colisões de **conduta de trabalho** abaixo, a editoria
decidiu em 26/09/2026 (§238) que **vence a skill** — o `CLAUDE.md` foi alterado para refleti-lo:

**§1 "Think Before Coding" — a parte do "pergunte". VALE.** Até 26/09/2026 o `CLAUDE.md` mandava o
contrário — execução silenciosa, sem pedir confirmação para decisão técnica de rotina —, e a
editoria tinha reafirmado isso como instrução permanente. Ela mudou de ideia no mesmo dia, depois
de ver as duas colisões escritas. Agora: declarar a suposição, apresentar as leituras quando há mais
de uma, e **parar e perguntar diante de dúvida real**.

**§3 "Surgical Changes" — "não refatore o que não está quebrado". VALE.** O mandato anterior era o
oposto: *"avalie todo o código de todos os coletores e implemente todas as soluções que você
conhece"*, e foi dele que nasceram os §§226 a 235 — a política de espera saindo de um coletor para
os dezesseis, 75 datas em UTC migradas em 41 arquivos, 33 escritas de JSON levadas à porta atômica,
23 arquivos passando a um cliente só. **Esse mandato deixou de ser permanente em 26/09/2026.**
Conserto que atravessa o repositório passa a ser pedido, um a um.

Fica registrado o que a troca custa, porque ela tem custo: as 137 barreiras do inventário do §230
seguem medidas e nomeadas, e nenhuma será atacada sem pedido. Defeito que eu encontrar fora do
escopo eu **nomeio** — não conserto de passagem.

O que o §3 mantém intacto aqui: **não mexer no estilo alheio**, não apagar código morto
pré-existente sem pedir, e limpar só o órfão que a própria mudança criou.

**§2 e §4 reforçam o projeto e não precisam de ressalva.** O §4 ("defina critério verificável e
itere até verificar") é literalmente o que os portões são: 69 comandos que reprovam de verdade, e
nada sobe com portão vermelho. Uma nota sobre o §2: "código mínimo" vale para CÓDIGO. A densidade de
comentário deste repositório é deliberada — cada conserto registra a medição que o motivou, com data
e número, porque foi assim que se descobriu que a mesma lição estava aplicada em um coletor de
dezesseis. Comentário que carrega prova não é excesso.

<!-- ── fim do bloco do projeto; daqui para baixo, texto literal da origem ── -->

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
