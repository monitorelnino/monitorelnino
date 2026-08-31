# Selos do índice MARÉ

Um selo SVG por estado (`mare-UF.svg`) e um nacional (`mare-brasil.svg`),
regravados a cada atualização semanal com o número publicado no índice.
Para embutir no seu site, cole:

```html
<a href="https://monitorelnino.com.br/#SC"><img src="https://monitorelnino.com.br/selos/mare-SC.svg" width="360" height="92"
   alt="MARÉ, Monitor El Niño Brasil: Santa Catarina, preparação demonstrável publicamente"></a>
```

O selo diz o que o índice mede — preparação *demonstrável publicamente* — e
nunca "preparado". Não altere o número: o arquivo é regravado pelo pipeline e
o site confere, a cada publicação, que cada selo bate com `data/indice.json`.
Licença: MIT, como o restante do projeto.
