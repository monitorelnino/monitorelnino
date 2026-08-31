# Como rodar, instalar e hospedar · Monitor El Niño Brasil (MARÉ v2.2.2)

## Requisitos
- **Python 3.12** (testado; 3.10+ deve funcionar) com as quatro dependências
  de `requirements.txt` (`pip install -r requirements.txt`; versões travadas,
  ver `docs/SBOM.md`).
- **Node.js ≥18** com as dependências de `package.json`
  (`npm install`, ou `npm ci` se `package-lock.json` estiver presente).
- Nenhuma outra ferramenta é necessária: o site não tem passo de build.

## Site local (sem qualquer dependência)
1. Descompacte o pacote; na raiz: `python3 -m http.server 8000`; abra
   `http://localhost:8000`.
2. As três páginas (index, proteja-se, envie-dados) funcionam localmente e
   buscam `data/*.json` por `fetch`; o formulário só envia de verdade no
   domínio publicado (detecção de ambiente proposital, ver `envie-dados.html`).

## Pipeline completo (ordem canônica)
```
python3 verificar_vigencia.py
python3 recalcular_mare.py --write
python3 verificar_consistencia.py
python3 recalcular_mare.py --check
node scripts/verificar_estrutura.js
node scripts/verificar_runtime.js
python3 gerar_pdf_metodologia.py
python3 gerar_pdf_indice.py
```
Ou, de uma vez, via orquestrador: `python3 atualizar.py` (executa as oito
etapas do pipeline, incluindo as aquisições de rede tolerantes a falha,
antes dos quatro portões bloqueantes). Critério de aprovação de qualquer
mudança: os quatro portões terminam com `✓` e a média nacional do índice é
reproduzida bit a bit.

## Variáveis de ambiente
Copie `.env.example` para `.env` (não versionado) e preencha, ou cadastre
como GitHub Secrets do repositório (produção). Nenhuma tem valor default:
ausência de qualquer uma faz a etapa correspondente ser pulada com aviso,
nunca publicar dado não confirmado.
- `PORTAL_TRANSPARENCIA_API_KEY` — cadastro gratuito em
  `portaldatransparencia.gov.br/api-de-dados`.
- `NETLIFY_AUTH_TOKEN` / `NETLIFY_SITE_ID` — painel do Netlify, necessários
  para deploy automático e para `verificar_contribuicoes.py` ler o
  formulário programaticamente.

## Hospedagem (Netlify, conforme `netlify.toml`)
1. Conecte o repositório no Netlify (Import from Git); `netlify.toml` já
   declara `publish = "."` e não há comando de build.
2. O formulário (`envie-dados.html`) é detectado automaticamente pelo
   Netlify (`data-netlify="true"`); nenhuma configuração extra é exigida.
3. Cadastre `NETLIFY_AUTH_TOKEN` e `NETLIFY_SITE_ID` como segredos do
   repositório para que a Action semanal leia as submissões
   programaticamente (`verificar_contribuicoes.py`); sem eles, o
   formulário funciona normalmente, só a leitura automatizada é pulada.
4. Hospedagem alternativa: qualquer servidor de arquivos estáticos serve o
   site (não há dependência de Netlify no HTML/CSS/JS em si); o formulário
   precisaria então de outro backend de submissão, fora do escopo deste
   pacote.

## Produção (GitHub Actions)
Workflow `.github/workflows/atualizar.yml`, semanal (segundas 09h UTC) e
sob demanda (`workflow_dispatch`). Instala as dependências Python e Node
antes de rodar `atualizar.py`; os quatro portões são etapas obrigatórias
do próprio job — uma falha para a Action antes de qualquer commit.

## Vigias de descoberta em produção — o que precisa existir (31/08/2026)

Nenhum dos vigias roda no sandbox de edição (rede restrita a pacotes). Em
produção (Action ou máquina de quem publica) eles precisam de:

| Vigia | Sai para a internet em | Credencial | Se falhar |
|---|---|---|---|
| `monitorar_sinais_federais.py` | in.gov.br (DOU), portal.stf.jus.br | nenhuma | pula, informativo |
| `monitorar_imprensa_regional.py` / `monitorar_atos_resposta.py` | news.google.com (RSS) | nenhuma | pula, informativo |
| `atualizar_boletins.py` | gov.br/cemaden, gov.br/inpe | nenhuma | pula, informativo |
| `atualizar_transferencias.py` | api.portaldatransparencia.gov.br | `PORTAL_TRANSPARENCIA_API_KEY` (**ainda não cadastrada**) | pula com aviso |
| **`monitorar_politica_por_inteiro.py`** | politicaporinteiro.org **e o host de onde o painel puxa os dados** (só se sabe na 1ª execução) | nenhuma | 1 pista de manutenção, informativo |
| `verificar_links.py` | os 188 domínios do site e do banco | nenhuma | `::warning::` + artefato; nunca remove link |

**Painel da Política Por Inteiro (Instituto Talanoa) — primeira execução.**
O painel carrega os atos por JavaScript; a página HTML chega vazia. O vigia
procura na marcação uma fonte de dados (JSON, CSV, planilha Google, endpoint
`wp-json`, Airtable) e a lê. Na primeira execução real, uma de duas coisas
acontece: (a) ele acha a fonte e enfileira as pistas — conferir a fila e o
`::warning::` de pistas pendentes; ou (b) enfileira **uma** pista de
manutenção `manutencao/PPI` dizendo que não achou fonte legível. No caso (b),
abrir o painel num navegador com DevTools → aba Network → filtrar XHR/Fetch
→ copiar a URL de onde os dados vêm, e ajustar `PADROES_FONTE_DADOS` em
`monitorar_politica_por_inteiro.py` (ou, se for uma planilha pública,
apontar direto para a exportação CSV). O esquema dos campos é heurístico
(`normalizar()`); se os nomes de coluna do painel divergirem, ajustar ali.
Estatuto da fonte: METODOLOGIA §4.1.1.1 — pista, nunca registro; toda pista
passa pelo julgamento automático (`julgar_e_aplicar_descobertas.py`) ou pela
fila humana. Cortesia recomendada antes do lançamento: avisar a Talanoa
(imprensa@institutotalanoa.org, contato indicado no próprio painel) que o
painel é fonte de descoberta creditada no site — o vigia se identifica no
User-Agent e roda uma vez por semana. Isto encerra a pendência
"conciliação fina com o catálogo Talanoa" listada abaixo: passou de tarefa
manual a mecanismo.

## O que falta para publicar

**1. Bloqueio duro (ação da editora, fora do escopo deste código):**
os três segredos de produção cadastrados no GitHub (lista acima).

**2. Qualidade pré-lançamento** (gravadas como obrigatórias na
`METODOLOGIA.md`): bateria negativa de AL, DF, PB, RN, SE; capitais sem
verificação de link individual; conciliação fina com o catálogo Talanoa;
leitura das íntegras da Portaria 260/2022 e da 3.646/2022; sistematização
do varrido de precedentes internacionais e da varredura de financiamento
preventivo estadual (bateria nas 26 UFs restantes, gabaritos já prontos
em `buscar_financiamento_preventivo.py --gabaritos UF`).

**3. Primeira execução em produção popula:** pistas do Querido Diário,
fila de conteúdo de decretos, PIB per capita (sob sentinelas) e
transferências (sob chave) — com a avaliação humana da editora reservada
exclusivamente às contribuições do formulário (regra R7).

**4. Achados desta auditoria de código, ainda não corrigidos** (declarados,
não escondidos — ver `docs/AUDITORIA_CODIGO.md` e `docs/SBOM.md` para o
detalhe de cada um):
   - ~~C10, chaves de API nunca no repositório~~ — verificado limpo e fechado
     preventivamente (30/08/2026): `.env` agora coberto pelo `.gitignore`;
     `verificar_consistencia.py` bloqueia se `.env.example` vier preenchido
     ou se um `.env` real aparecer no pacote. Chaves reais SEMPRE em GitHub
     Secrets / variáveis do Netlify — nunca em arquivo versionado.
   - ~~SRI nas tags de CDN~~ — fechada (C1, 29/08/2026). Resta a
     conferência em prévia de navegador antes do deploy (os hashes vieram
     do relatório de auditoria; o ambiente de edição não acessa o CDN).
   - ~~`unhandledrejection` no portão de runtime~~ — fechada (C3,
     29/08/2026), com teste negativo documentado no CHANGELOG.
   - ~~Limpeza de `fila_contribuicoes/`~~ — fechada (C5, 29/08/2026):
     execução local deve usar `python3 verificar_contribuicoes.py --limpar`
     (docstring do script; `docs/LGPD_PRIVACIDADE.md` seção 5).
   - ~~`pip-audit`/`npm audit` na Action~~ — fechada (C4, 29/08/2026),
     etapas informativas; promoção a bloqueantes aguarda política de CVE.
   - ~~Aviso de privacidade no formulário~~ — fechada (C6, 29/08/2026).
   - Self-host das fontes do Google (C2, forma forte) — pendência de
     deploy: baixar os `.woff2` e ativar `@font-face` local; a dependência
     está declarada no SBOM (forma mínima aplicada).
   - Rotinas do §15 (opcionais fora da Action, informativas dentro dela):
     `python3 monitorar_sinais_federais.py` (vigia DOU/ADPF; `--self-test`
     valida offline) e `python3 verificar_prazos_legais.py` (prazos ×
     banco; `--simular` gera quadro experimental não publicável). Nenhuma
     das duas pontua ou classifica; ver METODOLOGIA §15.
   - Selagem: `docs/MANIFEST_SHA256.txt` agora é gerado por
     `scripts/gerar_manifesto.py` e **inclui os dois PDFs publicados** (C7);
     a ordem canônica de fechamento de sessão passa a ser: portões verdes →
     `gerar_pdf_*.py` → `scripts/gerar_manifesto.py` → `sha256sum -c`.

**5. Pós-lançamento (v2.3, reservada; ver `CHANGELOG.md`):** fator de
alinhamento risco-plano com κ inter-avaliadores; população real na camada
declarada; anexo MARÉ×ICM. **v3:** instrumento de financiamento
preventivo como subcritério, condicionado à bateria negativa completa.
