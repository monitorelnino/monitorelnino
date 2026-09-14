# Instruções para a próxima sessão — Monitor El Niño Brasil
**Escrito em 14/09/2026 (segunda), ~08h30 UTC, pela sessão que fechou as PRs #171–#187.**
Leia inteiro antes de mexer em qualquer coisa. Está em ordem de prioridade.

---

## 0. Como retomar (5 minutos)

```bash
cd /home/claude/repo && git checkout main && git pull origin main
git checkout -b edicao/AAAA-MM-DD-<assunto>      # SEMPRE antes de editar — esta sessão commitou no main local duas vezes por esquecer isso
```

Token do GitHub: `ACESSO_GITHUB_claude.txt` (válido até ~30/11/2026). Relatórios das rotinas: repositório
`monitorelnino/robo-registro`, pasta `relatorios/` (ler pela API: `Accept: application/vnd.github.raw`).

Portão visual (Chromium local — o CI o roda, mas aqui também dá) — recriar `/tmp/run_visual_check.js` (o /tmp reseta):
```js
process.env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = '1';
const { chromium } = require('playwright'); const orig = chromium.launch.bind(chromium);
chromium.launch = o => orig({...o, executablePath: '/home/claude/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome'});
require('/home/claude/repo/scripts/verificar_consistencia_visual.js');
```
Bateria completa antes de qualquer PR: os 24 `verificar_*` (py e js) + `node /tmp/run_visual_check.js` + os autotestes dos coletores tocados.
Depois: `python3 scripts/carimbar_assets.py` → `git add -A` → `python3 scripts/gerar_manifesto.py` → `git add docs/MANIFEST_SHA256.txt` → commit → push → PR → esperar o CI (~4–5 min) → merge → apagar o branch.

---

## 1. Rede: o que a Patricia precisa liberar (e o que NÃO adianta)

**Sessão interativa (este sandbox):** a lista de domínios é fechada. Testado em 14/09: `info.dengue.mat.br` e
`gitlab.procc.fiocruz.br` → `403 x-deny-reason: host_not_allowed`. A lista só muda em **sessão nova**.

Onde liberar (Central de Ajuda, artigo 12111783): `claude.ai/settings/capabilities` → *Code execution and file creation* ON →
*Allow network egress* ON → *Domain allowlist* = "Package managers only" → *Additional allowed domains*: adicionar um a um.
Em plano Team/Enterprise fica em *Organization settings → Capabilities* e só o proprietário da organização vê.

Domínios a adicionar, na ordem em que vão ser usados:
| Domínio | Para quê | Status conhecido |
|---|---|---|
| `info.dengue.mat.br` | dengue e chikungunya (InfoDengue, `alertcity`) | funciona do runner (dengue coleta há semanas) |
| `gitlab.procc.fiocruz.br` | SRAG/SG, host canônico do InfoGripe | **fora do ar** desde 09/09 (timeout até de navegador no Brasil) |
| `gitlab.fiocruz.br` | SRAG/SG, host novo (endpoint `/-/raw/`) | interface pede login; o raw ainda não foi testado do runner |
| `tabnet.datasus.gov.br`, `opendatasus.saude.gov.br`, `sisaps.saude.gov.br` | 15 doenças "candidatas" | **a verificar** — nunca abertos |

**Aviso honesto:** há bug ativo (issues #93562/#93589/#93656 no repo `anthropics/claude-code`, regressão de 10→11/09/2026) em que a
liberação de domínios **não é aplicada** nas sessões em nuvem. Se depois de liberar + sessão nova ainda der 403, não é erro de
configuração — é esse bug; o caminho é o suporte da Anthropic. **Não dependa disso:** ver §2.

---

## 2. As rotinas (GitHub Actions) têm rede própria — use-as

`.github/workflows/atualizar.yml` roda `atualizar.py`: **segunda 09h UTC** (única rodada que coleta e comita; nas outras
a cadência encerra sem coletar — `[cadência] fora da semana intensiva…`), mais duas rodadas diárias que só valem na semana
intensiva (`INTENSIVO_ATE`). Tem `workflow_dispatch` (botão "Run workflow"; input `ensaio=true` = roda sem comitar).
**Não dispare manual perto das 09h UTC de segunda** — não há `concurrency` e duas rodadas comitando colidem.

Disparar pela API (o token tem permissão — foi usado em 14/09 para `diagnostico_sinais.yml`):
```bash
curl -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/monitorelnino/monitorelnino/actions/workflows/<arquivo>.yml/dispatches -d '{"ref":"main"}'
```
`diagnostico_sinais.yml` (rápido, não comita) roda `scripts/diagnostico_fontes_saude.py`: testa exatamente os hosts do
InfoGripe, DF/PE/PB e o Wayback. **Primeira coisa a fazer na próxima sessão: ler o relatório
`relatorios/2026-09-14_*_diagnostico_sinais.txt`** — ele diz se `gitlab.fiocruz.br` (raw) responde anônimo.

---

## 3. Coletores de saúde — estado exato

| Doença / indicador | Coletor | Estado em 14/09 08h30 UTC |
|---|---|---|
| Dengue | `coletar_desfechos_saude.py` (padrão) | ✅ roda há semanas; `data/saude_desfechos/{serie_painel,canal_endemico,completude,serie_uf}.json` |
| **Chikungunya** | mesmo coletor, `--doenca chikungunya` (PR #187) | ✅ código + autoteste; **nenhum dado ainda** — primeira rodada real é a de segunda 14/09 09h UTC (`atualizar.py` já chama). Produz `chik_*.json` |
| **SRAG** | `coletar_srag_gripe.py` (reescrito 14/09) | ✅ código + autoteste; **nunca coletou** (fonte fora do ar). Agora tenta 2 hosts em ordem e grava `infogripe_diagnostico.json` |
| **Síndrome gripal (SG)** | idem, extraído do mesmo CSV por padrão de rótulo (`^sg$`, `sindrome.*gripal`, `^ili$`) | ✅ código + autoteste; **só escreve `sg_serie.json` se o CSV trouxer o rótulo** — senão lacuna declarada. Os padrões são hipótese: confirmar em `infogripe_diagnostico.json` (campo `valores_de_dado`) na primeira rodada que alcançar a fonte |
| 15 "candidatas" do catálogo | nenhum | ❌ não começadas. Ver §5 |
| 1 "sem fonte identificada" (pele e olhos, e-SUS APS) | — | ❌ sem fonte aberta; não tentar |

Gráficos (saude.html): seletor **Dengue | Chikungunya** governa o comparador único e o mapa por nível; seletor
**SRAG | SG** na figura respiratória. Sem arquivo = **lacuna declarada** (legenda avisa, mapa/canvas vazio, crédito sem
data). Testes de runtime cobrem os dois seletores nos dois estados (com e sem arquivo): `scripts/verificar_runtime_saude.js`.

**Ao abrir a sessão, conferir se a rodada de segunda coletou:**
```bash
git pull; ls data/saude_desfechos/chik_* data/saude_desfechos/sg_serie.json data/saude_desfechos/infogripe_diagnostico.json 2>&1
```
- `chik_serie_painel.json` existe → abrir saude.html, trocar para Chikungunya, olhar se o canal endêmico faz sentido
  (chikungunya tem série mais curta e mais esparsa que dengue — municípios sem casos aparecem com 0, não com null; conferir
  que o acumulado de 2024 não está absurdo).
- `infogripe_diagnostico.json` existe → ler `url_que_respondeu` e `valores_de_dado`. Se SG tiver outro rótulo, ajustar
  `INDICADORES["sg"]["padroes"]` no coletor (nunca literal solto: sempre lista de regex) e rodar o autoteste.

---

## 4. Bugs e pendências herdadas (não fechadas nesta sessão)

1. **CPF no histórico de PRs** — só a Patricia: chamado em github.com/contact pedindo purga das refs `refs/pull/N/head` do
   repositório. O `git filter-repo` já foi feito (0 CPF em commits); o que sobrou é inacessível por API.
2. **PB (arboviroses)**: `coletar_boletim_pb_arboviroses.py` chuta números 01–06 e recebe HTML. Precisa de descoberta real de
   URL (listagem da página) — não adivinhação.
3. **DF**: `scripts/sondar_listagem_df.py` foi mesclada; **ler o resultado da sonda** no relatório e corrigir o padrão de link
   do coletor (a listagem via Wayback não usa `informativo_epidemiologico_seNN`).
4. **Ouro Branco/AL**: URL corrigida em 12/09; conferir na rodada de 14/09 se o aviso sumiu (bloqueante a partir de 15/09).
5. **Duas tarefas da Patricia ainda não feitas** (pedidas em 13/09, "quando terminar" o redesenho):
   - "Como ler o MARÉ" vira **ficha popup** na home (mesmo `<dialog>` do detalhe do estado), com um link **logo abaixo da
     barra do contador do índice** dizendo exatamente "como ler o MARÉ". Remover os links de atalho "Resposta por estado" e
     "Encontre sua cidade" (o `.hero-links` da home).
   - "O que a lei deixa aberto" (calendario-eleitoral) vira **nota para a imprensa em `imprensa.html`** (além do que já está
     na METODOLOGIA) e **sai da página principal**.
6. Financiamento: unificar "Por estado" + "Contadores por estado" + "Resposta por decreto" numa tabela só é refinamento
   opcional — os dados reais não sustentam mais granularidade que a atual.
7. Saúde: mapa de status do instrumento e mapa de risco já têm "Ver em tabela"; a proposta pedia removê-los como figura —
   decisão editorial pendente da Patricia (esta sessão preferiu manter, ver PR #186 mensagem).

---

## 5. As 15 doenças "candidatas" — como atacar (uma por vez, nunca em lote)

Fonte: `data/saude_desfechos/catalogo.json` (campo `fonte_aberta`). Regra da casa: **abrir a fonte primeiro**, ver o formato
real, só então escrever coletor — no estilo defensivo dos existentes (colunas por padrão, falha alto, registra lacuna, nunca
adivinha). Cada coletor novo: autoteste com fixture sintética + chamada em `atualizar.py` + figura com lacuna declarada +
teste de runtime nos dois estados.

Ordem sugerida (do mais parecido com o que já existe para o mais diferente):
1. **Doenças diarreicas agudas (DDA)** — OpenDataSUS Sivep-DDA, agregado semanal por município: mesmo grão do painel amostral.
2. **Leptospirose** — OpenDataSUS Sinan (CSV anual grande; filtrar pelos 313 municípios do painel).
3. **Agravos por calor (CID T67)** — Painel de Excesso de Calor (MS) + TabNet SIH/SIM.
4. **Internações respiratórias / cardiovasculares / renais / ICSAP / desidratação** — todas TabNet SIH: um coletor
   parametrizado por CID, como o de InfoDengue por doença (TabNet é POST com formulário — sondar antes).
5. Malária (Sivep-Malária BI), desnutrição (SISVAN), saúde mental e mortalidade geral (SIM preliminar), tuberculose (Sinan).

Domínios prováveis (a confirmar no primeiro acesso): `opendatasus.saude.gov.br`, `s3.sa-east-1.amazonaws.com` (buckets do
OpenDataSUS), `tabnet.datasus.gov.br`, `sisaps.saude.gov.br`, `infoms.saude.gov.br`.

---

## 6. Princípios que esta sessão precisou reaprender (para não repetir)

- **Branch antes de editar.** Duas vezes o commit foi parar no `main` local. Conserto: `git branch <nome>` no commit,
  `git reset --hard origin/main`, `git checkout <nome>`, push.
- **Nunca dado inventado.** Sem arquivo = lacuna declarada visível. Um cartão "Tendência" foi deixado de fora do perfil de
  estado (PR #185) porque não existe tendência por UF nos dados — não fabricar.
- **Nunca estilo próprio num elemento.** O Portão 18 pegou duas vezes: `margin-top` num `h2`, `font-size` num `<select>`
  sem classe. Sempre reaproveitar (`.card-sep`, `.seletor`, utilitários `u-*`).
- **jsdom não é navegador.** Sem `showModal()`/`close()` no `<dialog>`, sem `destroy()` no stub de `Chart`, `getContext()`
  devolve null. Guardar com `typeof` e usar `.open`/`hidden`; o Portão 18 (Chromium) cobre o comportamento real.
- **Conferir o que outra rodada já fez.** Em 13/09 as PRs #176/#177 apareceram mescladas entre duas mensagens (rotina ou
  sessão paralela). Antes de retomar: `git pull` e ler `git log --oneline -15`.
