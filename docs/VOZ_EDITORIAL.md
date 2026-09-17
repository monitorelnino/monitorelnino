# Voz editorial · como o site descreve o que mostra (16/09/2026)

Regra fixada com a editoria depois de uma revisão do site inteiro: as legendas,
notas e fichas do MARÉ tinham o hábito de fazer três coisas que não são
tarefa delas.

## O que uma legenda faz

Diz **o que a figura ou seção é**: fonte, período, unidade, escopo. Só isso.
Se o leitor perguntasse "o que estou vendo?", a legenda é a resposta — nada
além dela.

## Os quatro hábitos a evitar

**1. Explicar a política editorial do site em vez do conteúdo.**
Errado: *"Achar os planos publicados é tarefa do Monitor, não das
prefeituras — mas qualquer pessoa pode ajudar."*
Certo: diga o que a seção faz ("envie um documento que ainda não está no
banco"). Se o leitor não pediu para saber de quem é a responsabilidade,
não é conteúdo da legenda.

**2. Avisar o leitor sobre o que ele não deve concluir.**
Errado: *"Peso zero; o Monitor não atribui casos ao El Niño."* repetido em
cinco legendas da mesma página.
Certo: a ressalva metodológica real (peso zero, resposta ≠ preparação, o
que uma figura não mede) aparece **uma vez por página**, no lugar
apropriado — a ficha "Como ler", ou uma nota "O que a figura não diz" — e
as legendas individuais ficam limpas.

**3. Categórico por hábito, não por necessidade.**
"Nunca", "sempre", "jamais" usados como ênfase retórica, quando a frase já
era clara sem eles. "As duas metades nunca se combinam num número" vira
"As duas metades são mostradas separadamente" — mesma informação, sem o
tom de regra sendo aplicada.

## Léxico e teto probatório (antes só em `docs/GUIA_DO_EDITOR.md`, integrado aqui 17/09/2026)

Além dos quatro hábitos acima, nenhuma legenda, ficha ou prosa de dado usa:

- **Léxico avaliativo**: "preocupante", "alarmante", "grave", "crítico", "positivo",
  "insuficiente", "avanço importante", "chama atenção", "fica evidente".
- **Abertura interpretativa**: "revela", "demonstra", "os números mostram que…".
- **Causalidade não demonstrada**: "X e Y aumentaram no período", nunca "X provocou Y".
- **Teto probatório**: "sem plano **localizado**", nunca "sem plano" nem "não existe".

Adjetivo vira número: não "aumento expressivo", mas "de 12 mil (2020) para 18 mil (2024)".
Interpretação mora fora da figura — no parágrafo narrativo, no insight ou na ficha — nunca na
legenda. Hierarquia: título (o que se vê) · subtítulo (período · variável · unidade) · figura ·
legenda · fonte e data · texto narrativo (só aqui, quando couber, a interpretação). Termos
técnicos que contêm essas palavras ("síndrome respiratória aguda grave", "janela crítica" do
Ministério da Saúde, "nível 3 (alerta)") estão na lista de exceções do portão, por serem
vocabulário oficial da fonte, não juízo do site.

## Por que isso acontecia

Rigor e voz são coisas diferentes. Não inventar dado, separar fato de
interpretação, nunca deixar uma afirmação sem lastro — isso é como o texto
é *escrito*, e continua valendo integralmente. O erro era deixar esse
cuidado vazar para dentro do texto como frase, fazendo o site narrar a
própria cautela a cada parágrafo. O leitor não precisa ver o processo;
precisa ver o resultado, dito com clareza.

## Onde a ressalva metodológica mora

Toda página com método a explicar tem (ou deveria ter) **um** lugar
para isso — a ficha "Como ler o MARÉ" (ou "Como ler as rotas", "Como ler o
dinheiro preventivo"), ou uma nota "O que a figura não diz" dedicada.
Esse é o único lugar onde vale explicar o que algo não significa, o que não
é medido, ou como uma categoria é definida. Fora dali, a legenda descreve.

## Exceção: Proteja-se e Para gestores

Instruções de segurança ("ligue 199, não o número da coordenação
estadual") e passos de ação ("registre no S2iD em até 10 dias") não são
o padrão que este guia corrige — são o conteúdo em si dessas duas
páginas, cujo propósito é dizer ao leitor o que fazer. A regra vale para
legendas de figura, fichas metodológicas e cartões informativos nas
páginas de dados e na Imprensa.

## Como testar uma frase antes de publicar

Pergunte: essa frase descreve o que a figura mostra, ou está corrigindo
uma leitura que o leitor ainda nem fez? Se for a segunda, ou ela vira uma
frase descritiva, ou ela sai — e, se for uma ressalva real, vai para a
ficha da página, uma vez.

## Adendo de 16/09/2026 — quarto hábito: travessão como muleta de escrita

**4. Travessão como muleta de escrita.**
Errado: *"O índice mede preparação, o decreto, resposta."* com travessões
separando os apostos.
Certo: reescrever a frase de modo que ela não precise da pausa gráfica,
quase sempre com vírgula, ponto, ou dividindo em duas frases.
Motivo: travessão em série é como texto gerado por máquina soa; frase
corrida é como uma pessoa escreve.

Nenhuma prosa do site usa travessão (—) como pontuação de frase, em
`p`, `li`, `dd`, `figcaption`, `summary`, texto de `dialog` e strings de
prosa renderizadas por JS, nas páginas de dados e na Imprensa. A regra
não afeta o ponto médio "·" (separador de metadado, já padrão do site),
nem o hífen curto em intervalos numéricos ("2019–2025"), nem o hífen em
palavras compostas ("pós-evento").
