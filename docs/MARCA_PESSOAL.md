# Marca pessoal · sistema visual e de tom (movido do CLAUDE.md em 15/10/2026, texto integral)

> Fonte de verdade da skill `marca-pessoal`. Subordinada à `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` e à `AI_VISUAL_ART_DIRECTION.md` (hierarquia no `CLAUDE.md`). As referências "Seção N" abaixo são deste arquivo.


> Acrescentado em 23/09/2026 a pedido da editoria. O conteúdo acima (governança
> do MARÉ) permanece íntegro; esta seção rege **design, edição e conteúdo**.
> Não muda a arquitetura do código.
>
> **DESVIO DECLARADO — o fundo deste site é BRANCO.** A Seção 3 abaixo manda
> "base sempre escura (vazio/abissal) ou osso". Aqui não vale: o fundo branco é
> decisão editorial de 05/09/2026, reafirmada pela editoria em 23/09/2026, e
> está registrada em `assets/tokens.css`. **Não reverter `--bg` para escuro nem
> para osso** por fidelidade à marca — a editoria já decidiu, e decidiu contra.
> Todo o resto da Seção 3 (paleta, papéis das cores, proibições) vale integral.

---

## 1. Pedido de instalação das skills

Antes de editar qualquer página, componente ou texto deste site:

1. Crie a skill de marca em `.claude/skills/marca-pessoal/SKILL.md` (o conteúdo está na Seção 6). Ela é a fonte de verdade visual e de tom deste projeto.
2. Verifique se existe uma skill ou plugin de design de interface instalado (por exemplo `frontend-design`, do marketplace oficial de plugins do Claude Code; use `/plugin` para conferir e instalar). Se existir, use-a para composição, hierarquia e acabamento, **sempre subordinada à `marca-pessoal`**: ela nunca substitui paleta, fontes ou tom daqui, e é proibido cair no visual genérico de IA (gradientes roxos, fontes padrão, cards idênticos).
3. Para gráficos e painéis, use a paleta da Seção 3 como paleta de séries. Sem skill de dataviz disponível, siga as regras da Seção 6.
4. Para conferir o resultado, rode o site localmente e verifique em 375px e em desktop (Playwright ou o navegador disponível), comparando com o checklist da skill.
5. Se algo acima não estiver disponível, siga este arquivo diretamente e avise o que faltou.

## 2. Tese (uma frase para guiar toda decisão)

A marca não fala de sustentabilidade, fala de regeneração: restaurar e co-evoluir, deixar o sistema mais vivo do que se encontrou. O futurismo é **encarnado** (corpo, presença, matéria) e **sintético no sentido de síntese** (o híbrido onde não se distingue o que cresceu do que foi fabricado).

- Slogan pessoal: **O futuro começa como ideia.** / *The future begins as an idea.*
- Frase-manifesto: *O futuro não se prevê. Cultiva-se.* / *The future is not foreseen. It is cultivated.*
- Slogan da Futura Evidence Lab (organização parente): **Imaginar não basta.** A pessoa abre, a Futura cobra.

Personalidade em quatro palavras: **Magnetismo, Provocação, Vitalidade, Espírito.** ("Sedução" foi substituída por magnetismo de propósito: presença que se impõe pela contenção.)

Regra de ouro: **nenhuma imagem bela sem substância; nenhum dado sem beleza.** Toda seção do site que for só bonita precisa de um dado, fonte, tese ou referência. Toda seção só informativa precisa da marca.

---

## 3. Paleta (tokens)

```css
:root {
  /* bases */
  --vazio:    #0E0F0D;
  --abissal:  #15201A;
  --musgo:    #2E3D30;
  --osso:     #EDE6D8;
  --areia:    #D6C4AC;
  /* calor (nunca protagonista) */
  --argila:   #7C4A34;
  --ambar:    #C9814B;
  /* acentos (um por vez, em pequena dose) */
  --bioluz:    #A8C99A;  /* o vivo */
  --sintetico: #5E7C93;  /* o fabricado */
  --mineral:   #8FA5A8;  /* apoio frio */
}
```

Regras de uso:

- **Base sempre escura (vazio/abissal) ou osso.** Eles dominam a página.
  · **Exceção permanente deste site (23/09/2026):** o MARÉ usa fundo **branco**,
  por decisão editorial de 05/09/2026 reafirmada em 23/09/2026. Ver o desvio
  declarado no alto desta seção. O tema técnico sobre branco é o padrão do site.
- Argila e âmbar entram como calor: linhas, detalhes, hover. Nunca como fundo de área grande.
- **Bioluz e sintético são acentos.** Um por vez, em pequena dose: o detalhe que "acende" (link, ponto, sublinhado, número em destaque). Nunca preencher áreas grandes.
- A tensão bioluz × sintético é a marca em duas cores: o híbrido.
- **Proibido:** verde eco-óbvio saturado, prata futurista, cromado, neon, gradientes arco-íris, ícones de folha.
- Modo escuro é o padrão da identidade. O modo claro usa fundo osso, texto vazio, mesmos acentos. Conferir contraste mínimo AA (4.5:1 no texto corrido).

---

## 4. Tipografia

- **Display:** Fraunces, **peso leve (300)**, com itálico. Nunca bold. Títulos, frases-manifesto, assinatura.
- **Texto:** Archivo. **Legendas, dados, créditos:** Archivo Narrow em versaletes espaçados (`letter-spacing: .12em; text-transform: uppercase`) com números tabulares (`font-variant-numeric: tabular-nums`). É o registro de "espécime de laboratório".
- Fallbacks: `Georgia, 'Playfair Display', serif` no lugar de Fraunces; `Inter, 'Segoe UI', sans-serif` no lugar de Archivo.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500&family=Archivo+Narrow:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300&display=swap" rel="stylesheet">
```

```css
:root {
  --font-display: 'Fraunces', Georgia, 'Playfair Display', serif;
  --font-text: 'Archivo', Inter, 'Segoe UI', sans-serif;
  --font-spec: 'Archivo Narrow', 'Archivo', sans-serif;
}
h1, h2, h3 { font-family: var(--font-display); font-weight: 300; }
.spec { font-family: var(--font-spec); text-transform: uppercase; letter-spacing: .12em; font-variant-numeric: tabular-nums; }
```

---

## 5. Direção de imagem, voz e conteúdo

**Imagem:** retratos com luz dramática e encenação (aura), matéria orgânica com toque resinoso/sintético, texturas táteis e foscas. Nada metálico, nada de banco de imagens genérico. Legenda de imagem sempre com fonte ou tese, em Archivo Narrow.

**Corpo como marca:** presença e contenção. Uma peça-manifesto por composição, todo o resto quieto. Gastar a ousadia em um só lugar da página.

**Tom de voz:** provocador, poético, espirituoso e vivo. A voz seduz a mente antes do olhar.

> **SUBORDINAÇÃO DECLARADA (24/09/2026).** Este parágrafo **não se aplica ao conteúdo público do
> site**. A `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` é a fonte de verdade editorial e tem precedência
> declarada: ela exige voz **clara, segura, precisa, sóbria e não promocional** (§16), proíbe
> dramatização, frase de impacto e metáfora excessiva (§24), e proíbe dizer ao leitor o que pensar
> (§20). Onde as duas colidem, **vence a governança** — e o portão 19 (`verificar_legendas.js`) já
> reprova juízo e interpretação em texto de figura, de modo que a colisão nem chega ao ar.
>
> Onde esta voz **vale**: material de marca e apresentação que não seja conteúdo público do índice.
> Onde ela **não vale**: título, legenda, nota, fonte, tooltip, cartão, prosa de página — tudo o que
> o leitor encontra no site. A razão é do próprio sistema de marca, no fim da Seção 7: *"dúvida entre
> mais bonito e mais rigoroso: escolher o que preserva o rigor visível"*. Num monitor de evidências,
> o rigor visível **é** o produto.

| Faz | Não faz |
|---|---|
| Afirma teses com elegância e lastro | Opina sem fundamentar |
| Provoca com ideias contraintuitivas | Polêmica vazia ou choque fácil |
| Junta metáfora orgânica e precisão científica | Escolhe entre poesia OU dado |
| Ironia inteligente, humor sofisticado | Humor raso, sarcasmo cínico |
| Bilíngue PT/EN quando amplia alcance | Bilíngue decorativo |

**Pilares de conteúdo** (toda seção nova do site deve servir a um): Tese, Artefato ("achados do futuro" legendados como espécimes de 2075), Bastidor do rigor (o dado por trás da beleza) e Presença.

**Relação com a Futura Evidence Lab:** parentesco visual (família terrosa, rigor tipográfico, mão orgânica), sem ser gêmea. A marca pessoal é a voz autoral e mais emocional; a Futura é a organização e mais evidência. Não copiar o layout de uma na outra.

---

## 6. Conteúdo da skill local: `.claude/skills/marca-pessoal/SKILL.md`

Instalada em 23/09/2026. Ver o arquivo; o checklist dele é obrigatório antes de entregar
qualquer edição de design, layout ou texto.

---

## 7. Como o Claude deve trabalhar neste repositório

- Pedidos de "editar o site" ou "melhorar o design" são tratados como **edição e elevação**, não criação do zero: primeiro auditar o que existe, podar o desalinhado, manter o que carrega credibilidade, depois produzir.
- Ao terminar, dizer em duas linhas o que mudou e apontar qualquer trecho que ainda quebra a marca.
- Dúvida entre "mais bonito" e "mais rigoroso": escolher o que preserva o rigor visível. O risco da marca é parecer estética demais e perder credibilidade.
