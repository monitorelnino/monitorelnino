# Página "Pesquisadores", arquivada

**Arquivada em 27/09/2026, por decisão da editoria.** Sai do site por ora e fica guardada e
inativa; será **reconstruída quando o preprint e a validação metodológica estiverem prontos**. O
que fazer com ela depois é outra decisão, que ainda não foi tomada.

Handover de origem: `notas/HANDOVER_suprimir_pagina_pesquisadores_27-09-2026.md`, no repositório
privado da editoria. Registro no `CHANGELOG.md` do §258 e na `METODOLOGIA.md` §34.

## O que está aqui

| arquivo | era |
|---|---|
| `pesquisadores.html` | a página, com as doze seções listadas abaixo |
| `pesquisadores.js` | o JS dela, incluindo a tabela `AREAS` (COBRADE) |

## Esta pasta NÃO é publicada

`netlify.toml` tem uma regra que devolve **404** para `/arquivo/*`, e o portão
`scripts/verificar_pagina_arquivada.py` reprova se qualquer HTML publicado voltar a linkar
`pesquisadores.html`, ou se o arquivo reaparecer na raiz sem decisão registrada no CHANGELOG.

O portão existe porque arquivar sem trava é o mesmo que deixar a página voltar por descuido: um
`git checkout` distraído, uma mesclagem malfeita, e o link quebrado vai ao ar sem ninguém ver.

## Para onde foi cada seção

As seções de proveniência **não foram arquivadas**: cada uma foi para a página que a citava, como
bloco "Fontes e registros" ao fim dela, no componente de ficha que o site já usa.

| seção | foi para |
|---|---|
| Fontes dos sinais de risco | `monitor-de-riscos.html` |
| Fontes e consultas do financiamento | `financiamento.html` |
| Créditos extraordinários de 2026 (MP 1.367 e MP 1.384) | `financiamento.html` |
| O que a União publicou | `saude.html` |
| Backlog de fontes | `saude.html` |
| Log de verificação e cobertura | `defesa-civil.html` |
| Registros e fontes dos dados | `defesa-civil.html` |
| Painel amostral | `defesa-civil.html` |
| tabela `AREAS` (COBRADE) | `assets/js/defesa-civil.js`, e o portão de consistência lê de lá |

**Ficaram arquivadas com a página**, por decisão da editoria: "Como usar o site e os dados",
"Metodologia e versões", "Dados abertos, feeds e selos" e "Código e replicação" — esta última
inclui a frase sobre "código para replicar", que a editoria já mandou rever em 23/09 e que não
deve voltar ao ar como está.

O **formulário "Indique um documento publicado"** não foi arquivado: a editoria quer manter canal
para ser informada de documento que o Monitor não localizou. Ele passou ao rodapé de todas as
páginas, aberto num `<dialog>`, e `obrigado.html` continua respondendo.

## Como reativar

1. Ler a decisão da editoria que autoriza a volta, e registrá-la no `CHANGELOG.md` — o portão
   exige a linha lá, não aceita só o arquivo de volta.
2. Mover `pesquisadores.html` para a raiz e `pesquisadores.js` para `assets/js/`.
3. Decidir o que acontece com as seções de proveniência: elas hoje vivem nas páginas que as usam.
   Duplicá-las seria criar duas verdades sobre a mesma fonte — o site tem regra contra isso.
4. Devolver "Pesquisadores" à ordem canônica da barra de navegação, que está em
   `scripts/verificar_estrutura.js`, e aos portões que a citam.
5. Retirar a regra de 404 de `/arquivo/*` em `netlify.toml`, se a pasta deixar de existir.
6. Rever a frase sobre "código para replicar" antes de publicar: a editoria já pediu isso.
