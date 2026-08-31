# Monitor El Niño Brasil — MARÉ v2.2.3
## Guia de instalação, publicação e auditoria

Documento de entrega da edição fechada em **31/08/2026**. Serve a três leitores:
quem vai **publicar** o site, quem vai **auditar** o método e o código, e quem vai
**operar** a atualização semanal. Cada seção diz o que fazer e o que esperar.

---

## 1. O que é esta versão, em números

| | |
|---|---|
| Índice MARÉ, média nacional | **47,1 / 100** (faixa *em construção*) |
| Estados com instrumento localizado | 25 de 27 (2 sem plano estadual nominal localizado: PB e RN) |
| Registros municipais verificados | **265**, com documento, data e fonte |
| Municípios cobertos pela verificação | 5.571 (todos os do IBGE geram relatório) |
| Decretos de emergência registrados | 5 (transparência; **não pontuam**) |
| Marcos legais/judiciais vigiados | 7, com 3 prazos em curso |
| Páginas do site | 6 |
| Relatórios em PDF gerados sob demanda | 5.598 (27 estaduais + 5.571 municipais) |
| Portões automáticos bloqueantes | 5 |
| Funções com docstring | 210 de 210 · módulos: 37 de 37 |

**O que o índice mede:** preparação *demonstrável publicamente* — o que está
publicado e verificável em fonte oficial até a data de corte. Não mede
capacidade instalada, não mede suficiência e não afirma que algo não existe.
A linguagem-teto de qualquer afirmação pública é **"não localizamos até o
corte"**.

---

## 2. Publicar o site (30 minutos)

O site é **estático**: HTML, CSS, JS e JSON prontos. Não há build, framework
nem banco de dados. Qualquer hospedagem de arquivos serve.

### 2.1 Caminho recomendado (Netlify, já configurado)

1. Suba o conteúdo deste pacote para um repositório Git.
2. No Netlify: *Add new site → Import an existing project* → selecione o
   repositório. O `netlify.toml` já define `publish = "."`, sem comando de build.
3. Aponte o domínio `monitorelnino.com.br` para o site (Netlify → *Domain
   management*). O HTTPS é automático.
4. **Formulário**: o Netlify detecta `data-netlify="true"` em
   `envie-dados.html` no primeiro deploy; as submissões aparecem em *Site →
   Forms*. Nada além disso precisa ser configurado.

### 2.2 Verificação local antes de subir

```bash
python3 -m http.server 8000     # e abra http://localhost:8000
```
Sem servidor (abrindo o arquivo direto), o navegador bloqueia a leitura dos
JSON e a página aparece vazia — é comportamento esperado, não defeito.

### 2.3 Três segredos, no GitHub (Settings → Secrets → Actions)

| Segredo | Para quê | Sem ele |
|---|---|---|
| `PORTAL_TRANSPARENCIA_API_KEY` | transferências municipais (chave gratuita em portaldatransparencia.gov.br/api-de-dados) | a etapa é pulada com aviso; o resto roda |
| `NETLIFY_AUTH_TOKEN` | ler as contribuições do formulário pela API | contribuições não são processadas |
| `NETLIFY_SITE_ID` | idem | idem |

Chaves reais **nunca** no repositório: `verificar_consistencia.py` bloqueia a
publicação se um `.env` preenchido aparecer no pacote.

---

## 3. Auditar (o que rodar, o que significa)

### 3.1 Protocolo canônico — cinco portões bloqueantes

Rodar nesta ordem, da raiz do pacote. Qualquer falha impede a publicação.

```bash
node scripts/verificar_estrutura.js      # árvore HTML das 6 páginas, masthead, rodapé,
                                         # 1 h1 por página, <main>, fontes, nada <12px
python3 verificar_consistencia.py        # 12 invariantes dos dados (ver 3.2)
python3 recalcular_mare.py --check       # o índice publicado é reproduzível dos dados
node scripts/verificar_runtime.js        # index.html em navegador simulado: mapas, tabelas,
                                         # consulta municipal, botões de PDF, prazos, pedido e-SIC
node scripts/verificar_runtime_mapas.js  # os 7 mapas e 6 gráficos, legendas, harmonização
```

Resultado esperado, nesta versão: **os cinco verdes**.

### 3.2 O que `verificar_consistencia.py` garante

Contagens e somas entre arquivos; `percentual_uf.json` derivado das categorias
documentadas; vocabulário controlado; natureza do documento coerente com o
status (Correção B: ato de resposta não pontua); nomenclatura das faixas
idêntica nos seis lugares onde aparece; selos batendo com o índice; feeds Atom
bem formados; CSVs de dados abertos com as linhas dos JSON; nenhum `.env`
preenchido.

### 3.3 Auditorias manuais (não rodam no CI; exigem navegador)

```bash
npm install --no-save jspdf playwright chart.js d3 jsdom @axe-core/playwright
python3 scripts/auditar_pdfs.py    # gera e inspeciona os 5.598 PDFs, por dentro
node scripts/auditar_ux.js         # axe-core (WCAG 2.1 AA) nas 6 páginas × 3 viewports
python3 verificar_links.py         # 188+ URLs do site e do banco (precisa de rede aberta)
```

Resultado desta versão: **5.598 PDFs sem problema**; **0 violações axe em 18
combinações**; links a verificar na primeira execução com rede.

### 3.4 Self-tests dos vigias (sem rede, com fixtures)

```bash
for s in gerar_selos gerar_feeds gerar_dados_abertos monitorar_politica_por_inteiro \
         monitorar_sinais_federais monitorar_imprensa_regional verificar_prazos_legais \
         julgar_e_aplicar_descobertas verificar_links; do python3 $s.py --self-test; done
```

### 3.5 Reprodutibilidade

`docs/MANIFEST_SHA256.txt` traz o hash de cada artefato desta edição
(`python3 scripts/gerar_manifesto.py` regenera). Os PDFs são bit-reprodutíveis:
`SOURCE_DATE_EPOCH` fica preso à data de corte, não à hora da geração.

---

## 4. Operar a atualização semanal

### 4.1 Automática (recomendado)

`.github/workflows/atualizar.yml` roda **segundas, 09h UTC**, e sob demanda
(*Run workflow*). São 21 etapas: descoberta → julgamento automático → dados
oficiais → **os cinco portões** → PDFs → links → commit. Falha em portão
interrompe **antes** do commit: o site publicado nunca fica inconsistente.

### 4.2 Manual

```bash
python3 atualizar.py     # o pipeline inteiro, com os portões dentro
```

### 4.3 O que é automático e o que é humano

**Automático:** localizar atos em fontes oficiais, classificar, aplicar com
rollback, recalcular o índice, regravar selos/feeds/CSVs/PDFs, publicar.

**Humano, sempre:** promover pista a marco; aprovar contribuição do formulário
(regra R7); decidir sobre link quebrado; qualquer mudança de método. As filas
`data/pistas_*.json` têm trava explícita — nenhum código as promove.

### 4.4 Vigias: rede e credencial

| Vigia | Sai para | Credencial | Se falhar |
|---|---|---|---|
| `monitorar_sinais_federais.py` | DOU, STF | — | pula, informativo |
| `monitorar_imprensa_regional.py` / `monitorar_atos_resposta.py` | Google News RSS | — | pula, informativo |
| `atualizar_boletins.py` | CEMADEN, INPE | — | pula, informativo |
| `atualizar_transferencias.py` | Portal da Transparência | chave | pula com aviso |
| `monitorar_politica_por_inteiro.py` | politicaporinteiro.org + host dos dados | — | 1 pista de manutenção |
| `verificar_links.py` | 188 domínios | — | aviso + artefato |

**Primeira execução do vigia da Política Por Inteiro:** o painel carrega os
atos por JavaScript. O vigia procura na página a fonte de dados (JSON, CSV,
planilha, `wp-json`). Se não achar, deixa **uma** pista `manutencao/PPI`. Nesse
caso: abrir o painel com DevTools → aba *Network* → filtrar XHR/Fetch → copiar a
URL dos dados → ajustar `PADROES_FONTE_DADOS` no script. Cortesia recomendada
antes do lançamento: avisar a Talanoa (imprensa@institutotalanoa.org) que o
painel é fonte de descoberta creditada no site.

---

## 5. Pendências antes de publicar

**Bloqueiam o lançamento:**
1. Os três segredos cadastrados (seção 2.3).
2. Baterias negativas obrigatórias de PE e das UFs em LAC (registradas como
   obrigatórias na METODOLOGIA).
3. Verificação individual de link das capitais.
4. Conferir no navegador real que os hashes SRI das tags de CDN passam.

**Decisões suas, sem prazo técnico:**
5. **Licença dos dados** — hoje herdam MIT; recomendação CC BY 4.0
   (`docs/DADOS_ABERTOS.md`).
6. **DOI** — Zenodo + release do GitHub; o campo está como placeholder
   comentado em `CITATION.cff` (nada inventado).
7. **URL do repositório** — idem, a preencher em `CITATION.cff` e
   `datapackage.json`.
8. **Opção B (ponderação populacional)** — aprovada, nunca aplicada: exige a
   primeira Action rodar `atualizar_populacao.py` e a simulação antes/depois ser
   apresentada para autorização. **Muda o índice de todos os estados.**
9. **Tensão §5.2.1** ("40 = estrutura recorrente" no texto × "30" na prática
   para RJ/ES/MG/SP) — reservada para a v2.3.

**Fila de triagem humana (`data/pistas_sinais.json`):**
10. Portaria MDS nº 1.207 — fatos confirmados em duas fontes; falta o link do
    DOU (o vigia deve achá-lo).
11. MP nº 1.383/2026 (R$ 360 mi ao MIDR, resposta) — localizar a página no
    Congresso e decidir a promoção.

**Verificar assim que possível:**
12. **A Action está rodando?** A fila de sinais federais estava vazia numa
    segunda-feira com uma portaria de 18/08 publicada — conferir o histórico em
    *Actions*. Se ela não roda, nada do que está automatizado acontece.
13. Fontes do Google não são self-hosted (achado C2 de duas auditorias): além de
    confiabilidade, cada visita envia o IP do leitor ao Google.

---

## 6. Onde ler cada coisa

| Pergunta | Documento |
|---|---|
| Como o índice é calculado, e por quê | `METODOLOGIA.md` / `.pdf` (§1–§18) |
| O que mudou, quando, e por decisão de quem | `CHANGELOG.md` |
| Como rodar cada script, pendências detalhadas | `docs/COMO_RODAR_E_PENDENCIAS.md` |
| Esquema dos dados abertos, como citar, DOI | `docs/DADOS_ABERTOS.md` |
| Dado pessoal do formulário (LGPD) | `docs/LGPD_PRIVACIDADE.md` |
| Dependências e vulnerabilidades | `docs/SBOM.md` + os `.cdx.json` |
| Achados das auditorias externas e respostas | `docs/AUDITORIA_*.md`, `docs/RESPOSTA_*.md` |
| Hash de cada artefato | `docs/MANIFEST_SHA256.txt` |
| Vocabulário das categorias, regras de fonte | `README.md` |

---

## 7. Princípios que o código faz cumprir

Não são aspirações: cada um tem um portão ou um teste.

1. **"Não localizamos até o corte"** é o teto de qualquer afirmação pública —
   nunca "não existe", nunca "descumpriu".
2. **Ato de resposta não pontua.** Decreto de emergência entra no mapa de
   transparência; o índice mede preparação anterior ao dano (Correção B).
3. **Regra declarada antes de beneficiar alguém.** Mudança de método é
   registrada com data e justificativa antes de valer.
4. **Imprensa e agregadores descobrem; documento oficial registra.** Nenhuma
   pista entra no banco sem o documento primário e citação completa.
5. **Toda mudança automática é reversível**, com backup e rollback verificado.
6. **Sem ranking ordinal público** — o Monte Carlo mostra a instabilidade
   posicional; a decisão está documentada (§13).
7. **Nada inventado**: link, DOI, número ou data que não foi verificado não
   entra — fica como lacuna declarada.

---

*Monitor El Niño Brasil · MARÉ v2.2.3 · corte de dados 31/08/2026 ·
Uma publicação Futura Evidence Lab · monitorelnino.com.br*
