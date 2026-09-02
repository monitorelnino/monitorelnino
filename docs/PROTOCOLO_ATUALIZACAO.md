# Protocolo de atualização do site publicado · Monitor El Niño Brasil

**Vigência:** a partir de 01/09/2026. **Estado do lançamento (02/09/2026):** o domínio monitorelnino.com.br serve a página "Em atualização" (ramo `publico`); o site completo v2.3 está no endereço reservado de prévia. O lançamento é decisão da editoria (§7).
**Complementa:** `INSTALACAO_E_AUDITORIA.md` (como reproduzir) e
`docs/COMO_RODAR_E_PENDENCIAS.md` (como rodar). Este documento diz **como
uma mudança entra no site em produção** — quem faz o quê, em que ordem, com
que portões.
**Versão simples, para a editoria:** `docs/GUIA_DO_EDITOR.md`.

---

## 1. Princípio

O que está na branch `main` do repositório **é** o site: o Netlify publica a
raiz do repositório sem passo de montagem (`netlify.toml`, `publish = "."`).
Logo, **nada entra na `main` sem passar por um portão** — mecânico (scripts)
ou humano (aprovação da editoria) — e toda entrada é reversível.

Duas pistas levam à `main`, com regras diferentes:

| Pista | Quem executa | O que pode tocar | Portão |
|---|---|---|---|
| **A — automática** (Action `atualizar.yml`: semanal às segundas; diária durante a semana intensiva, controlada por `INTENSIVO_ATE`) | robô, sem intervenção | apenas `data/` (inclui `data/sinais_risco.json`), o número do medidor em `index.html`, `mapas-e-graficos.html`, o dicionário `ESTADOS` em `recalcular_mare.py`, PDFs, `selos/`, `feeds/`, `dados-abertos/` — e só via funções com rollback de `julgar_e_aplicar_descobertas.py` | os **sete** portões bloqueantes de `atualizar.py`; falha ⇒ nenhum commit |
| **B — editorial** (sessão Claude + editoria) | Claude prepara; editoria aprova | qualquer arquivo | ramo + pull request + prévia + aprovação humana + portões |

A pista A **executa regras**; nunca as cria. Tudo que a regra não cobre vai
para fila (`data/instrumentos_revisar.json`, `data/pistas_imprensa.json`) e
espera a pista B. Isso é a governança automático × humano do projeto
(`TRANSFERENCIA_CONCEITUAL_MARE.md` §9) aplicada ao deploy.

## 2. Pista A — atualização automática semanal

- **Gatilho:** segundas-feiras, 09h UTC (06h Brasília), ou botão *Run
  workflow* na aba Actions. Primeira execução: **domingo, 06/09/2026, 06h Brasília** — dia 0 da semana intensiva (`INTENSIVO_DE=2026-09-06`, `INTENSIVO_ATE=2026-09-13`); antes de 06/09 a execução diária encerra sem coletar.
- **Segredos necessários** (Settings → Secrets and variables → Actions):
  `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`, `PORTAL_TRANSPARENCIA_API_KEY`.
  Confirmados presentes em 01/09/2026. Ausência de qualquer um faz a etapa
  correspondente ser **pulada com aviso**, nunca publicar dado não confirmado.
- **Resultado esperado:** commit `Atualização automática de dados (dd/mm/aaaa)`
  na `main` pelo usuário `monitor-el-nino-bot`, ou "Sem alterações."
- **Sinais para a editoria** (aba Actions, execução da semana):
  - ✅ verde sem avisos — nada a fazer;
  - ✅ verde com `::warning::` — há pistas/propostas na fila humana ou links
    quebrados; abrir sessão da pista B para julgar;
  - ❌ vermelho — nada foi publicado; o site continua como estava. Abrir
    sessão da pista B com o link da execução para diagnóstico.
- **Notificação:** o GitHub envia e-mail ao dono do repositório quando a
  execução falha. Sucesso não gera e-mail — a conferência semanal é
  responsabilidade da editoria (Guia do Editor, §4).

## 3. Pista B — mudança editorial (texto, design, código, dados, método)

### 3.1 Sequência obrigatória

```
1. Editoria descreve a mudança no chat (o que, onde, por quê).
2. Claude clona a main atual com o token (nunca trabalha sobre cópia antiga).
3. Claude cria ramo  edicao/AAAA-MM-DD-tema  a partir da main.
4. Claude edita com assert-before-write (âncora verificada por grep antes
   de cada substituição; verificação de sintaxe após cada arquivo).
5. Claude roda os portões locais (§3.3) — todos ✓ ou a mudança não sobe.
6. Claude registra no CHANGELOG.md e, se cabível, em METODOLOGIA.md.
7. Claude faz push do ramo e abre um pull request contra a main, com:
   resumo em linguagem simples · lista de arquivos · saída dos portões ·
   o que a editoria deve olhar na prévia.
8. Netlify gera a prévia (Deploy Preview) do PR.
9. Editoria abre a prévia, confere e decide: aprovar (Merge) ou pedir ajuste.
10. Merge na main ⇒ Netlify publica em ~1 min.
11. Claude (ou a editoria) confere o site vivo; CHANGELOG muda de
    "em publicação" para a data.
```

**O clique de Merge é da editoria.** Claude não faz merge por conta própria
de nenhum PR da pista B, mesmo com autorização genérica prévia — cada PR é
uma decisão. Exceção única: correção de emergência (§5), com autorização
explícita naquela sessão.

### 3.2 Classes de mudança e o que cada uma exige

| Classe | Exemplos | Além da sequência 3.1 exige | Versão |
|---|---|---|---|
| **Texto/editorial** | frase do herói, legenda, rótulo, texto de página | auditoria de vocabulário controlado (`grep` contra frases-teto e frases proibidas; "não localizamos até o corte" é o teto) · paridade METODOLOGIA ↔ site onde o texto é espelhado | mantém |
| **Design** | cores, layout, posição de figuras, cartões | prévia obrigatória (desktop, tablet e celular); componentes compartilhados só em `assets/base.css` e tokens só em `assets/tokens.css` — nenhuma página redefine o núcleo (portão 1); acessibilidade e responsividade pelo portão 11; nenhum rótulo de faixa ou legenda pode afirmar mais do que o índice mede (§2.2 da transferência conceitual) · os quatro `verificar_runtime_*.js` verdes | mantém |
| **Código** | scripts, workflow, dependências | portões completos (§3.3) · SBOM e `MANIFEST_SHA256.txt` regenerados (`scripts/gerar_manifesto.py`) · SRI recalculado se algum CDN mudar · `pip-audit`/`npm audit` sem CVE crítico novo | patch (v2.2.x) |
| **Dados** | registrar instrumento, reclassificar ato, aplicar contribuição | entra **somente** por `aplicar_revisao.py` / `converter_contribuicao.py`, nunca por edição direta de `data/*.json` · citação completa (número + data do ato) · `recalcular_mare.py --write` seguido de `--check` · determinismo do PDF (`SOURCE_DATE_EPOCH` = corte) · errata se corrige registro anterior | mantém; novo corte em `data/meta.json` |
| **Método** | pesos, créditos, componentes, faixas, régua | regra **declarada antes** de beneficiar alguém (§3.5 da transferência) · simulação antes/depois apresentada à editoria · teste de estresse · seção datada em METODOLOGIA · entrada em errata/governança | **maior** (v2.3, v3…) |

Contribuições do formulário público seguem o caminho já definido
(`verificar_contribuicoes.py → converter_contribuicao.py → aplicar_revisao.py`)
e são a única reserva de julgamento humano que Claude **nunca** executa sozinho.

### 3.3 Portões locais (ordem canônica, todos bloqueantes) — v2.3: doze portões

```
 1. node   scripts/verificar_estrutura.js        (8 páginas; tokens.css; nav canônica; :root inline proibido)
 2. python verificar_consistencia.py             (vocabulário com nao_verificado; log v2; nada-localizado exige
                                                  nível completo; dicionário; fósseis; segredos)
 3. python recalcular_mare.py --check            (índice, robustez e os dois derivados de verificação, bit a bit)
 4. python verificar_sinais.py                   (sinais de risco: peso zero, proveniência)
 5. python verificar_saude.py                    (saúde: peso zero provado no motor e no índice, vocabulário, créditos)
 6. python verificar_evidencias.py               (evidência preservada: aviso até 09/09/2026, bloqueante depois)
 7. node   scripts/verificar_runtime.js          (+ portão de linguagem: "não localizamos" só com verificação completa)
 8. node   scripts/verificar_runtime_mapas.js
 9. node   scripts/verificar_runtime_sinais.js
10. node   scripts/verificar_runtime_saude.js
11. node   scripts/verificar_acessibilidade.js   (idioma, viewport, skip-link, títulos, alt, rótulos, SVG, foco,
                                                  contraste AA dos tokens, pontos de quebra; base.css obrigatória)
12. bash   scripts/verificar_derivados.sh        (regenera índice → feeds → dados abertos → PDFs → manifesto com
                                                  relógio no corte e exige git diff --exit-code: derivado obsoleto bloqueia)
```
Critério: doze `✓` (o 6º admite `⚠` até 09/09/2026) e média nacional reproduzida bit a bit. Os coletores têm `--autoteste` próprio (fixtures + testes negativos), rodado antes de qualquer PR que os toque. Todo portão novo entra com teste negativo (quebra proposital acusada, restauração verde). Se a mudança
tocou dados: antes disso, `recalcular_mare.py --write` e regeneração dos PDFs.
Se tocou código ou dependências: também `scripts/gerar_manifesto.py`.

### 3.4 Convivência entre as pistas

O robô só toca os arquivos listados em §1. Um ramo da pista B que edite
qualquer um deles deve ser **rebaseado na `main`** imediatamente antes do
merge (a Action pode ter comitado na segunda-feira). Conflito em
`data/*.json` nunca é resolvido "à mão": refaz-se a alteração por
`aplicar_revisao.py` sobre a base nova.

### 3.5 Push confirmado (lição de 02/09/2026)

Nenhum push é dado como feito por uma mensagem de sucesso: a sessão confere que o commit
existe no remoto (`git fetch && git merge-base --is-ancestor HEAD origin/<ramo>`) antes de
abrir PR ou pedir merge. Um push falhou em silêncio nessa data e o site chegou a ser
mesclado sem a designação de versão.

## 4. Reversão (rollback)

- **Site:** Netlify → *Deploys* → escolher o deploy anterior → *Publish
  deploy*. Instantâneo, sem tocar no repositório. Use quando o site vivo
  estiver visivelmente errado.
- **Repositório:** `git revert` do commit problemático, via PR da pista B
  (mantém histórico; nunca `force push` na `main`).
- Toda ação da pista A já é revertida pelos rollbacks internos de
  `julgar_e_aplicar_descobertas.py`; se um commit automático inteiro precisar
  cair, aplica-se o `git revert` acima.

## 5. Correção de emergência

Definição: erro **público e material** no site vivo (número errado no
medidor, afirmação que ultrapassa o teto probatório, link malicioso, dado
pessoal exposto). Fluxo: rollback pelo Netlify **primeiro** (§4), depois PR
normal com a correção. Nesse caso, e só nele, a editoria pode autorizar
Claude a fazer o merge na mesma sessão, por escrito no chat.

## 6. Acessos e segredos

| Item | Onde vive | Quem vê |
|---|---|---|
| Token GitHub (fine-grained, `claude-monitorelnino`, Contents + Pull requests, vence ~30/11/2026) | arquivo `ACESSO_GITHUB_claude.txt` nos arquivos do projeto Claude — **nunca** no repositório | Claude, em sessão |
| Segredos da Action | GitHub Secrets | ninguém (só nomes) |
| Conector Netlify | conta Claude da editoria | Claude, em sessões novas |

Regras: `.env.example` permanece modelo vazio; nenhuma chave em commit,
CHANGELOG, PR ou memória. Rotação do token: criar novo no GitHub, substituir
o arquivo do projeto, apagar o antigo.

## 7. Fase de testes (a partir de 01/09/2026)

**Constatação de 01/09/2026:** o site no Netlify (`site_id` em segredo) foi
publicado manualmente e **não está ligado ao GitHub**. Em vez de ligar, o
deploy passou a ser feito pelo próprio GitHub Actions, com a CLI do Netlify e
os segredos já cadastrados — o repositório continua sendo a única fonte:

| Workflow | Ramo | Gatilho | Publica em |
|---|---|---|---|
| `publicar_dominio.yml` (vive no ramo `publico`) | `publico` (órfão: `index.html` em branco, `robots.txt`, `netlify.toml` com `/* → /index.html` e `noindex`) | push em `publico` | **produção** — monitorelnino.com.br |
| `publicar_previa.yml` (vive no `main`) | `main` (site completo) | push em `main` — inclusive os commits da Action semanal | endereço reservado `main--<NETLIFY_SITE_NAME>.netlify.app` (Netlify serve com `noindex`) |

Segredos adicionais: `NETLIFY_SITE_NAME` (nome aleatório do site, aplicado
por `updateSite` de forma idempotente) e `ROBO_TOKEN` (para o robô gravar
relatórios). Relatórios de toda execução vão para o repositório **privado**
`monitorelnino/robo-registro` — nunca para este repositório público, que não
deve conter o nome do site nem o endereço reservado.

**Lançamento** = PR no `main` que copie `publicar_dominio.yml` (ajustado para
`branches: [main]`) e remova `publicar_previa.yml`; merge pela editoria.
**Reversão** = o inverso. O ramo `publico` nunca recebe merge de `main`.
Se um dia o site for ligado ao GitHub pelo painel do Netlify, estes
workflows devem ser desativados antes, para não haver dois publicadores.

## 8. Registro

Todo PR da pista B referencia a entrada correspondente do `CHANGELOG.md`.
Toda execução da pista A fica registrada na aba Actions (90 dias de
artefatos; relatório de links por 30 dias). A trajetória da média nacional
continua registrada em `METODOLOGIA.md` §5.5.

---
*Protocolo de atualização · Futura Evidence Lab · 01/09/2026.*
