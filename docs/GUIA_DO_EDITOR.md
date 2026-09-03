# Guia do Editor · como atualizar o site sem ser programador

Este guia é a versão em linguagem simples de `docs/PROTOCOLO_ATUALIZACAO.md`.
Ele diz o que **você** faz, o que o **Claude** faz e o que acontece
**sozinho**. Não há comandos para digitar: só telas para abrir e botões
para clicar.

---

## 1. Cinco palavras que aparecem o tempo todo

| Palavra | O que é, na prática |
|---|---|
| **Repositório** | A pasta oficial do site, guardada no GitHub, com o histórico de toda alteração. O que está nela na versão `main` **é** o que está no ar. |
| **Ramo** (branch) | Uma cópia de trabalho da pasta, onde uma mudança é preparada sem mexer no site. |
| **Pull request** (PR) | Um pedido formal: "aqui está a mudança pronta, revise e aprove". Tem página própria no GitHub, com resumo, lista de arquivos e botão de aprovar. |
| **Prévia** (deploy preview) | Um endereço temporário, gerado pelo Netlify, que mostra como o site ficaria se aquele PR fosse aprovado. Você vê antes de publicar. |
| **Merge** | O clique que aprova o PR e joga a mudança na `main`. Cerca de um minuto depois, o site atualiza. **Esse clique é seu.** |

## 2. Os dois jeitos de o site mudar

**Sozinho, toda segunda-feira às 6h (horário de Brasília).** Um robô busca
boletins, instrumentos novos, transferências e contribuições do formulário;
aplica só o que as regras já aprovadas permitem; roda cinco verificações; e,
se tudo passar, publica. Se qualquer verificação falhar, **nada é
publicado** e o site fica como estava. O robô nunca muda texto, design,
método ou regra — só dados, dentro de limites.

**Com você, quando você quiser.** Texto, design, código, dado novo, regra
nova. Sempre no mesmo fluxo: você pede → Claude prepara num ramo → Claude
abre um PR → você olha a prévia → você clica em Merge → o site atualiza.

## 3. Passo a passo de uma mudança sua

1. **Abra uma conversa no projeto do Claude** e descreva a mudança: o que
   muda, onde, por quê. Não precisa de vocabulário técnico ("o texto do topo
   da página inicial", "o cartão da cidade", "a cor da faixa avançada").
2. **Claude faz tudo o que é técnico:** baixa a versão atual, cria o ramo,
   edita, roda as verificações, registra no histórico (CHANGELOG) e abre o
   PR. Ao final ele manda o **link do PR** e diz **o que você deve olhar**.
3. **Abra o link do PR.** Na página, procure a caixa de verificações
   (checks). Haverá uma linha do Netlify com o texto *Deploy Preview ready* e
   um link **Details** — clique nele. Abre a prévia do site.
4. **Confira na prévia** exatamente o que Claude pediu para olhar. Navegue
   como uma leitora: o texto está certo? A frase respeita o teto ("não
   localizamos até o corte")? O layout ficou como você queria?
5. **Decida:**
   - **Aprovar:** volte à página do PR, role até o fim, clique no botão verde
     **Merge pull request** e depois **Confirm merge**. Pronto. Em um minuto o
     site está atualizado; abra monitorelnino.com.br e confira.
   - **Pedir ajuste:** volte ao chat e diga o que mudar. Claude atualiza o
     mesmo PR e a prévia se refaz sozinha. Repita a partir do passo 3.
   - **Desistir:** na página do PR, role até o fim e clique em **Close pull
     request**. Nada acontece com o site.

O que **não** precisa fazer: baixar arquivos, editar nada no GitHub, mexer no
Netlify, digitar comandos.

## 4a. Semana intensiva (de domingo 06/09 a domingo 13/09/2026)

A partir de **domingo, 06/09/2026** (dia 0), o robô roda **todo dia às 6h** por sete dias, um lote por vez — antes disso ele não coleta nada, mesmo se os PRs forem aprovados antes: dia 1
reconhecimentos federais e a camada declarada; dias 2–4 diários oficiais dos
estados por região; dias 4–7 diários municipais em lotes. O que você faz:

1. Cada manhã, a mesma olhada da rotina de segunda (abaixo): cor da bolinha.
2. Com bolinha amarela, haverá **pistas** para julgar (documentos que o robô
   achou mas que só um humano pode promover a registro) — abra uma conversa
   e diga "há pistas para julgar".
3. O fim da semana intensiva é automático: a data está numa variável do
   repositório (`INTENSIVO_ATE`); depois dela o robô volta ao ritmo semanal
   sozinho. Se quiser esticar ou encurtar, diga ao Claude a data nova.
4. Quatro fontes nascem marcadas "a verificar" (S2iD, MUNIC, ICM e a cobertura
   dos diários estaduais): o robô tenta, e o que não confirmar aparece como
   lacuna declarada — nunca como dado inventado.

## 4. Rotina de segunda-feira (5 minutos)

1. Abra github.com/monitorelnino/monitorelnino e clique na aba **Actions**.
2. Veja a execução mais recente de *Atualização semanal de dados*:
   - **bolinha verde, sem avisos** — tudo certo, nada a fazer;
   - **bolinha verde com um ⚠ amarelo** — há algo esperando seu julgamento
     (uma pista de instrumento, uma contribuição do formulário, um link
     quebrado). Abra uma conversa com o Claude e diga "há avisos na execução
     de segunda"; ele lê a fila e apresenta cada item para você decidir;
   - **bolinha vermelha** — a atualização falhou e **nada foi publicado**; o
     site continua íntegro. Copie o endereço da página da execução e cole no
     chat; Claude diagnostica.
3. Se a execução falhar, o GitHub também manda um e-mail para a conta
   monitorelnino. Se der tudo certo, ele não avisa — por isso a olhada
   semanal.

## 4a-bis. Duas páginas de peso zero e o painel

- **Saúde e El Niño** e **Por onde o dinheiro chega** são registros de transparência: nada
  delas entra na nota, e um portão prova isso (apagar a pasta inteira do financiamento
  não muda nenhuma nota). Quando o robô coletar a série de transferências, o gráfico do
  bloco 2 preenche sozinho — a faixa do período eleitoral já está desenhada e fica.
- O **painel amostral** (313 municípios, 12 por estado, sorteados com semente publicada)
  é reverificado toda segunda. A lista é imutável: se um dia precisar trocar um município,
  é errata pública, nunca edição silenciosa.
- Nomes de parlamentares não aparecem no site, em texto nem em link (regra E10, provada
  por portão).

## 4a-ter. Página para jornalistas e linha narrativa

- **Para jornalistas** (`imprensa.html`, no menu e no rodapé): release lido ao vivo dos
  dados, o que o índice mede e não mede, como citar, dados abertos, feeds, selos, FAQ e
  o contato imprensa@monitorelnino.com.br. O release muda sozinho quando a média muda.
- Um portão (o 16º) lê o texto visível de todas as páginas e bloqueia jargão interno —
  nomes de arquivo, códigos de decisão, "portão", "robô", números de PR, auditoria,
  qualquer menção a pedidos de LAI enviados. Se quiser proibir uma expressão nova, é
  uma linha na lista do portão.

## 4b. Pedidos de acesso à informação (uma vez, dia 0)

Os 55 textos ficam no repositório **privado** (`robo-registro`, pasta `notas/lai/textos`),
nunca no site nem no repositório público (decisão de 03/09/2026). O envio é seu: no
Fala.BR (falabr.cgu.gov.br) ou no e-SIC de cada estado, cole o texto, envie e anote o
**número de protocolo**. Depois, numa conversa, diga ao Claude "registre o protocolo NNN
do pedido de defesa civil de SC, enviado em DD/MM" — ele grava no registro privado. No
site aparece apenas, sem contagens, que a verificação de um estado depende de resposta
a pedido de acesso à informação.

## 4c. Lançamento oficial: o que vigiar

- O site é estático e escala sozinho na CDN; o que pode estourar no plano gratuito do
  Netlify é o **formulário** (100 envios por mês) e, com muito tráfego, a **banda**
  (100 GB/mês ≈ 330 mil visitas à página inicial). Se o lançamento for grande, vale
  subir o plano do Netlify antes — é uma troca de plano no painel, sem mudar nada no site.
- Dados novos aparecem em até 5 minutos para quem já visitou (cache); a página em si
  sempre revalida.

## 5. Se o site estiver errado agora (o "botão de desfazer")

Qualquer versão anterior do site pode voltar ao ar em segundos, sem tocar em
nada do repositório:

1. Entre em app.netlify.com com a conta do site.
2. Clique no site → aba **Deploys**.
3. A lista mostra cada publicação, com data e hora. Clique na última que
   você sabe que estava certa.
4. Clique em **Publish deploy**. O site volta para aquela versão.
5. Avise o Claude no chat para que a correção definitiva entre pelo fluxo
   normal (PR).

Use isso para erro visível e importante — número errado no medidor, frase
que afirma mais do que o índice mede, dado pessoal exposto. Para ajuste
comum, o fluxo do §3 basta.

## 6. O que continua sendo só seu

- **Contribuições do formulário público** que possam mudar o índice (tipo
  "plano", qualquer capital): Claude prepara, você decide, sempre.
- **Qualquer regra nova** de método: Claude só implementa depois de mostrar
  a simulação antes/depois e de a regra estar escrita e datada.
- **Design e vocabulário**: nada vai ao ar sem sua prévia.
- **O clique de Merge.**

## 7. Fase de testes: domínio em branco, site completo em endereço reservado

Enquanto o site não é lançado, o domínio monitorelnino.com.br mostra uma
**página em branco** (ramo `publico`), e o site completo (ramo `main`) fica
num **endereço reservado** do Netlify, no formato
`main--NOME-DO-SITE.netlify.app`. Esse endereço não aparece em buscadores
(o Netlify marca como "não indexar") e só quem tem o link chega nele. Não é
senha: é um endereço não divulgado. Se um dia precisar de senha de verdade,
isso existe no Netlify como recurso pago — é só pedir.

- **Testar:** abra o endereço reservado. É o site completo, sempre na
  versão atual do `main`.
- **Prévias de PR** continuam funcionando normalmente.
- **A rotina de segunda-feira** continua atuando no `main`; o domínio em
  branco não é tocado.
- **Quem publica é o robô do repositório**, não o painel do Netlify: cada
  mudança aprovada no `main` vai sozinha para o endereço reservado, e o
  domínio em branco só muda se alguém mexer no ramo `publico`.
- **Lançar** (quando decidir): diga ao Claude "lançar o site". Ele prepara um
  PR que troca o publicador do domínio para o `main`; você aprova com Merge e,
  em dois minutos, monitorelnino.com.br mostra o site completo. Para voltar
  ao branco, o inverso — também por PR.

## 8. Acessos (onde está cada coisa)

- **Token do GitHub:** no arquivo `ACESSO_GITHUB_claude.txt`, dentro dos
  arquivos do projeto Claude. Claude lê sozinho a cada conversa. Vence por
  volta de 30/11/2026: Claude avisa antes; você cria outro na mesma tela em
  que criou este (Settings → Developer settings → Fine-grained tokens) e
  substitui o arquivo no projeto.
- **Senhas da rotina automática:** guardadas no GitHub, em Settings →
  Secrets and variables → Actions. Ninguém vê os valores, nem você, nem
  Claude — só os nomes. Se precisar trocar uma, é "Update" na mesma tela.
- **Netlify:** ligado como conector na sua conta Claude. Numa conversa nova,
  Claude consegue ver as publicações e as prévias por lá.

---
*Guia do Editor · Futura Evidence Lab · 01/09/2026.*
