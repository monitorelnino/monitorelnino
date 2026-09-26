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

Ela é **subordinada** às três fontes de verdade do projeto (`METODOLOGIA.md`,
`AI_EDITORIAL_NARRATIVE_GOVERNANCE.md`, `AI_VISUAL_ART_DIRECTION.md`) e ao `CLAUDE.md`. Duas seções
dela colidem de frente com regras deste repositório, e nas duas **vence o repositório**:

**§1 "Think Before Coding" — a parte do "pergunte".** Ela manda parar e perguntar diante de
dúvida. O `CLAUDE.md` manda o contrário: *"Execução silenciosa: não narrar passos intermediários
nem pedir confirmação para decisões técnicas rotineiras"*, e lista as únicas razões para
interromper — credencial ausente, ação destrutiva, risco de perda de dado, decisão de produto não
inferível, conflito real entre requisitos, impedimento técnico após diagnóstico. A editoria
reafirmou isso como instrução permanente. O que FICA valendo do §1 é o resto, que não colide e é
bom: declarar a suposição em vez de escondê-la, apresentar as interpretações quando há mais de uma,
e dizer quando existe caminho mais simples.

**§3 "Surgical Changes" — "não refatore o que não está quebrado".** É boa regra geral e é o oposto
do que a editoria pediu para este projeto: *"avalie todo o código de todos os coletores e implemente
todas as soluções que você conhece"*. Os §§226 a 235 do `CHANGELOG.md` são exatamente trabalho
transversal — a política de espera saindo de um coletor para os dezesseis, 75 datas em UTC migradas
em 41 arquivos, 33 escritas de JSON levadas à porta atômica, 23 arquivos passando a um cliente só.
Sob leitura literal do §3, **nenhum deles existiria**, e os defeitos que eles corrigiram seguiriam
em produção. Onde a editoria pede auditoria, o escopo é o que ela pediu, não a linha vizinha.

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
