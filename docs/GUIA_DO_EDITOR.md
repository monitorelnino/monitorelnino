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
- **Lançar** (quando decidir): Netlify → *Site configuration* → *Build &
  deploy* → *Branches and deploy contexts* → *Configure* → em *Production
  branch*, trocar `publico` por `main` → *Save*. Em um minuto o domínio mostra
  o site completo. Para voltar ao branco, o caminho inverso.

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
