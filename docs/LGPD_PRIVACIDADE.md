# Proteção de Dados Pessoais (LGPD) · Monitor El Niño Brasil

Este documento descreve, para fins de auditoria, o único ponto do sistema
onde dado pessoal é coletado, seu fluxo completo até o descarte ou a
transformação em fato público, e as escolhas de desenho que minimizam a
exposição desse dado. Não é parecer jurídico: descreve o comportamento
verificado do código, não uma análise de conformidade legal, para a qual
se recomenda consulta a profissional habilitado.

## 1. Onde dado pessoal é coletado

O único formulário do site é o de contribuição (`envie-dados.html`,
formulário `contribuicao`, entregue via Netlify Forms). Seus campos:

| Campo | Natureza | Obrigatório |
|---|---|---|
| `municipio`, `uf` | dado sobre o ato público, não pessoal | sim |
| `tipo` | categoria do ato (plano, decreto etc.) | sim |
| `numero_data` | número/data do ato público | não |
| `link_oficial` | URL da fonte oficial | sim |
| `observacoes` | texto livre sobre o ato | não |
| `contribuicao` | descrição livre da contribuição | não |
| `email_contato` | **dado pessoal** — e-mail de quem envia | não (campo opcional) |
| `bot-field` | honeypot antispam (Netlify), nunca exibido a humanos | — |

O único dado pessoal identificável é `email_contato`, campo opcional cujo
propósito declarado na interface é permitir que a editoria peça
esclarecimento sobre a contribuição, quando necessário.

## 2. Fluxo completo do dado, do envio ao descarte

1. **Envio.** O navegador do contribuinte envia o formulário ao Netlify
   Forms via POST nativo do HTML (`data-netlify="true"`); este projeto não
   opera servidor próprio nem grava o dado diretamente.
2. **Retenção temporária no Netlify.** A submissão fica disponível no
   painel do Netlify (Site → Forms), sob a política de retenção da própria
   plataforma, até ser lida ou expirar por lá.
3. **Leitura programática.** `verificar_contribuicoes.py` lê as submissões
   pela API do Netlify (autenticada por `NETLIFY_AUTH_TOKEN`), monta a fila
   de verificação humana e grava dois arquivos, incluindo `email_contato`
   tal como recebido, em `fila_contribuicoes/`.
4. **Retenção local — DEPENDE DE ONDE O SCRIPT RODA.** `fila_contribuicoes/`
   está no `.gitignore`: nunca é commitada, nunca chega ao repositório
   público. Se a etapa roda na Action semanal do GitHub, o diretório vive
   apenas dentro do runner efêmero daquela execução e é destruído ao fim do
   job — não há persistência além da execução. Se um editor humano roda o
   script localmente, o diretório persiste na máquina dele até ser apagado
   manualmente; desde 29/08/2026 (C5 da auditoria externa) a exclusão é
   automatizada pela flag `--limpar` de `verificar_contribuicoes.py`,
   **obrigatória em execução local** (documentada na docstring do script):
   ao final da triagem, o diretório inteiro é removido.
5. **Triagem e decisão humana.** A editoria lê a fila (arquivo Markdown
   gerado para leitura humana) e decide, ato a ato, se a contribuição vira
   registro público.
6. **Conversão para registro público — o dado pessoal é descartado aqui.**
   `converter_contribuicao.py` lê o item aprovado e produz o registro no
   formato de `data/municipios.json`: nome do município, categoria, fonte,
   data, canal. **O campo `email_contato` não é lido nem transposto por
   este script** — verificado por inspeção de código e por busca no banco
   publicado, que não contém nenhuma ocorrência de e-mail. O dado pessoal
   morre na fronteira entre a fila privada e o banco público por desenho,
   não por convenção informal.

## 3. Princípios de desenho aplicados

- **Minimização.** Apenas um campo do formulário é dado pessoal, e é
  opcional; nenhum outro dado do visitante (IP, cookies de rastreamento,
  identificadores de terceiros) é coletado por este projeto — o Netlify,
  como operador da infraestrutura de formulário, pode reter metadados
  técnicos da submissão sob sua própria política, fora do controle deste
  código.
- **Finalidade declarada e limitada.** O e-mail existe para viabilizar
  contato editorial sobre a própria contribuição; o código nunca o usa
  para nenhum outro fim (não há envio de e-mail em massa, newsletter ou
  perfilamento neste repositório).
- **Segregação do dado público e do dado pessoal.** O dado que o site
  publica é sempre sobre o ato do ente público (o decreto, o plano, a
  data), nunca sobre quem o reportou. A ponte entre os dois é cortada no
  passo 6.
- **Sem venda ou compartilhamento com terceiros** além do necessário à
  operação técnica (Netlify, como processador da submissão do formulário).

## 4. Direitos do titular

Quem preencheu `email_contato` e deseja que o dado seja removido antes da
triagem editorial pode solicitar a exclusão identificando sua submissão
(município, UF e data aproximada de envio) pelo canal de contato do
Observatório. Como o dado pessoal nunca chega ao banco público (seção 2,
passo 6), não há necessidade de retificação ou exclusão em `data/*.json`
por definição: ele simplesmente não está lá.

## 5. Pendências declaradas

- ~~Automatizar a exclusão de `fila_contribuicoes/`~~ — **fechada em
  29/08/2026 (C5)**: flag `--limpar`, obrigatória em execução local.
- ~~Aviso de privacidade em `envie-dados.html`~~ — **fechada em 29/08/2026
  (C6)**: parágrafo publicado logo abaixo do campo de e-mail, remetendo a
  este documento e ao canal de exclusão.
- Nomear formalmente um canal de contato para solicitações de titulares,
  hoje resolvido apenas pelos canais editoriais gerais do Observatório.
