# Página "Calendário eleitoral", arquivada

**Arquivada em 30/09/2026, por decisão da editoria** (item 3 da fila viva). A página inteira sai do
site — não era o bloco 4, era ela toda. Fica guardada e inativa; se voltar, é por decisão nova.

Registro no `CHANGELOG.md`: **§306**.

## O que está aqui

| arquivo | era |
|---|---|
| `calendario-eleitoral.html` | a página, com o calendário do ciclo, os dispositivos legais e a seção "A reabertura" |
| `calendario-eleitoral.js` | o JS dela |

## O dado e a coleta NÃO pararam

Esta é a diferença em relação ao arquivamento da página "Pesquisadores", e é deliberada:

- `data/marcos_ciclo.json` e `data/calendario/dispositivos.json` **continuam sendo mantidos**;
- a rotina que os atualiza **não foi desligada**;
- o portão `scripts/verificar_calendario.js` **continua rodando** sobre esses dados.

A editoria quer a informação guardada para uso futuro — o preprint e uma eventual retomada da página
usam esse histórico. Parar a coleta abriria um buraco no histórico que não se preenche depois:
diário oficial não guarda o que o Monitor não leu na época.

## Esta pasta NÃO é publicada

`netlify.toml` devolve **404** para `/arquivo/*`, e `scripts/verificar_pagina_arquivada.py` reprova
se qualquer HTML publicado voltar a linkar `calendario-eleitoral.html`, se o arquivo reaparecer na
raiz, se a regra de 404 sair do `netlify.toml`, ou se ele voltar sem decisão registrada no CHANGELOG.

## Como reativar

1. Registrar a decisão no `CHANGELOG.md` (o portão exige a linha lá — voltar sem registro é
   exatamente o caso que ele barra).
2. `git mv` dos dois arquivos de volta para a raiz e para `assets/js/`.
3. Tirar as duas entradas de `ARQUIVADAS` em `scripts/verificar_pagina_arquivada.py`.
4. Devolver a entrada ao `sitemap.xml`.
5. Refazer os links que saíram em `index.html`, `prefeituras.html`, `financiamento.html` e
   `imprensa.html` — as frases foram **ajustadas**, não só desligadas, então é preciso reescrevê-las,
   não só recolocar o `<a>`. O §306 do CHANGELOG diz o que cada uma dizia antes.
6. Reativar a seção dela nos portões de página que deixaram de listá-la.
