# CLAUDE.md · regras em vigor para o Claude Code neste repositório

Só regras vigentes, uma frase cada, com o portão que a prova. História, justificativas e relatos de
incidente: `docs/HISTORICO_DE_REGIMES.md`. Marca pessoal (paleta, tipografia, tom): `docs/MARCA_PESSOAL.md`.

## Hierarquia das regras (editoria, 02/10/2026)

```
AI_EDITORIAL_NARRATIVE_GOVERNANCE.md   (editorial e narrativa)
AI_VISUAL_ART_DIRECTION.md             (direção de arte)
  >  METODOLOGIA.md                    (travas de PROVA: limite de fato, não de estilo)
  >  CLAUDE.md + docs/MARCA_PESSOAL.md (§ Design, § 3 Paleta, § 4 Tipografia, regras editoriais)
  >  layout/contratos/<pagina>.json    (o layout de cada página)
  >  handovers                         (o pedido da rodada)
```

- Handover contra regra: aplica-se a regra, registra-se a divergência em uma linha, segue-se sem perguntar.
- Regras verificáveis vivem em `layout/regras.json`; quem reprova é `scripts/verificar_conformidade.py`,
  bloqueante em todo PR que toque página, estilo, figura, texto público ou dado exibido.
- Exceção só em `layout/excecoes.json` com regra, página, motivo, data e quem decidiu; sem registro é vermelho.
- Antes de mexer: ler os dois `AI_*`, § Design/Paleta/Tipografia e o contrato da página; mudança de
  layout começa pelo contrato; mudança de regra, pelo documento-fonte e por `regras.json`; o PR anexa
  a lista de conformidade que o portão imprime.
- Precedência na colisão: prova (`METODOLOGIA.md`) > narrativa (governança) > estética (direção de arte).

## O projeto

MARÉ · Monitor de Antecipação e Resposta ao El Niño (monitorelnino.com.br), jornalismo de dados de
interesse público da Futura Evidence Lab. Site estático (HTML + JSON em `data/`), coleta em
Python/Node, publicado pelo Netlify a partir da raiz (`netlify.toml`).

Documentos canônicos: `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` (leitura obrigatória antes de qualquer
conteúdo público) · `AI_VISUAL_ART_DIRECTION.md` (antes de layout, componente, paleta ou gráfico; §25:
observa-se o site inteiro antes de propagar) · `METODOLOGIA.md` (método) · `CHANGELOG.md` ·
`docs/PROTOCOLO_ATUALIZACAO.md` · `docs/GUIA_DO_EDITOR.md` e `docs/VOZ_EDITORIAL.md` (subordinados à
governança; o mais restritivo prevalece) · `.github/workflows/portoes.yml` (lista canônica dos portões).

## Modo de trabalho — autonomia decisória responsável (editoria, 27/09 e 30/09/2026)

- Português do Brasil; output style `caveman` permanente (`.claude/settings.json`); desligar só por PR a pedido da editoria.
- Sempre: rápido, limpo, sem narrar progresso, sem pedir confirmação fora das paradas abaixo.
- Padrão: analisar → decidir → implementar → testar → verificar → corrigir → continuar.
- Lista de itens se executa inteira, na ordem; relatório só ao fim de cada entrega ou de tudo.
- Conflito de merge e portão vermelho não são parada: diagnostica-se e corrige-se.
- Decide sozinho: estrutura, nomes, arquivos, refatoração, erro/retry/timeout/cache, validação,
  estados vazios, responsividade, acessibilidade, layout dentro do sistema, bibliotecas compatíveis,
  bugs, segurança óbvia, ordem de tarefas e todo defeito que o pedido expõe (corrige, testa, CHANGELOG).
- Para e pergunta só: credencial inexistente; exclusão irreversível de dado; regra, peso, régua ou
  categoria do índice; alteração material de texto público editorial/institucional/científico;
  licença e distribuição; risco jurídico ou de privacidade; conflito real de requisitos; impedimento
  que persista após diagnóstico. Pergunta em uma linha, com recomendação e o que acontece sem resposta.
- Ao concluir: relatório de até 6 linhas (o que mudou · verificação · sem solução · o que só a editoria decide).
- Fato só verificado; quanto maior o impacto e menor a reversibilidade, maior a certeza; mudança incremental.
- Skills subordinadas: `karpathy-guidelines` vale para qualidade de código, não para a interação;
  `brainstorming` (Superpowers) e `Grill Me` não entrevistam — vence este arquivo.

## Correção pela raiz, código menor ou igual (editoria, 13/10/2026)

- (1) Nomear a causa raiz com prova; (2) corrigir onde nasce; (3) remover o remendo que a escondia;
  (4) portão novo só se nenhum existente cobre, de preferência substituindo um redundante.
- Função que já existe (prazo, janela, `.feito`, reaplicação, commit, resolvedor, verificador de texto)
  não se copia: o outro lugar passa a usá-la.
- Todo PR declara linhas líquidas (+/−); PR de correção com saldo positivo diz por quê em uma linha.
  Plano: `robo-registro/notas/HANDOVER_CONSOLIDACAO_13-10-2026.md`.

## Publicação e quem faz o quê

- Merge com portões verdes autoriza publicar e republicar dentro da cortina (senha + `noindex`), com
  capturas no PR (os portões de navegador as sobem como artefato); não vale para mexer na cortina,
  na senha, no `noindex` ou em `data/publicacao.json` (só a editoria decide).
- Lançar o domínio ou revertê-lo exige a palavra da editoria ("siga pra publicação").
- Protótipo de página ou recurso: mostrar à editoria antes de mesclar.
- A central (chat) não commita, não mescla e não publica no site: escreve o handover; o Code executa.
- Alterar `.github/workflows/` é permitido quando o pedido exigir.

## Preprint e site são rotinas separadas (editoria, 27/09/2026)

- Sem pedido explícito: não rodar tarefa do preprint (T0–T11), não abrir PR público a partir de achado
  do preprint, não criar portão nem disparar rodada por causa dele, não criar worktree do site para ele.
- O preprint vive em `robo-registro/preprint/` e `robo-registro/notas/`; defeito do site achado nele vira
  registro no privado e pedido separado à editoria.

## Fluxo de mudança (PROTOCOLO §3.1)

1. Partir da `main` atualizada; ramo `edicao/AAAA-MM-DD-tema`; um ramo e um PR por entrega.
2. Consultar o `CODEMAP.md` (gerado por `scripts/gerar_codemap.py`, nunca à mão; portão reprova se
   envelhece) e ler só o que ele lista.
3. Editar com verificação de âncora antes de cada substituição.
4. Rodar os portões que `python3 scripts/quais_portoes.py` indicar (`--comando` dá a linha); na dúvida,
   `python3 scripts/portoes_locais.py tudo` (ou `paginas` | `dados`; `--listar` mostra sem rodar).
   Nada sobe com portão vermelho.
5. `CHANGELOG.md`: entrada `## AAAA-MM-DD · #PR · título`, até 80 palavras (portão
   `verificar_changelog_curto.py`); fundamentação longa vai para a `METODOLOGIA.md`.
6. Todo PR resela o manifesto: `bash scripts/verificar_derivados.sh` e commit (portão 12); derivado não
   se edita à mão (hook bloqueia).
7. Push, conferir que chegou (`git merge-base --is-ancestor HEAD origin/<ramo>`), PR, Action "Portões"
   verde, merge.
- Não abrir PR para uma frase: pedido pequeno de texto entra no próximo PR de página ou num "ajustes de
  texto de dd/mm" — salvo "publica isso agora".
- Portão 12 vermelho: `verificar_derivados.sh` → `git add -A` → commit → rodar de novo; antes de assumir
  culpa, `/e-da-main`.
- Atalhos: `/portoes`, `/p12`, `/e-da-main`, `/merge-main`, `/lote`; subagente `portoes-runner` para a suíte inteira.

## Arquivos que nunca entram em contexto

Consultar sempre agregando (`python3 -c "import json,collections; ..."`), nunca com `Read`; hook bloqueia
acima de 1 MB em `data/`, `dados-abertos/` e `evidencias/`. Tamanhos envelhecem: quem vir defasado remede.

| arquivo | tamanho (05–11/10/2026) |
|---|---|
| `evidencias/` | ~4,1 GB |
| `data/log_buscas/*.jsonl` | ~31 MB, um por mês |
| `data/pistas_imprensa.json` | ~26 MB |
| `data/fontes_consultadas.json` | ~12 MB |
| `data/financiamento/municipios/transferencias_uniao.json` | ~5 MB, cresce todo mês |
| `data/financiamento/municipios/fns_municipios_2026.json` | ~0,3 MB por mês, cresce |
| `data/verificacao_municipal.json` | ~3 MB |
| `data/log_buscas.json` | ~1 MB |

## Corrente noturna (editoria, 05/10/2026)

1. Nenhum coletor grava pista fora de `scripts/pistas.py` (`gravar`, `gravar_lote`, `sincronizar`;
   recusa com motivo em `data/pistas_rejeitadas.json`; operação de fila inteira declara-se em `MANUTENCAO`).
   Portão: `verificar_escritor_de_pista.py`.
2. Um escritor por arquivo (`config/escritores.json`) ou resolução declarada em
   `scripts/unir_conflito_de_rodada.py` / `pendente`. Portão: `verificar_escritores.py`.
3. Cancelado e pulado nunca contam como feito: conta o run `in_progress` ou com o marcador
   `data/noite/<noite>/<elo>.feito`, gravado depois dos comandos e antes do commit
   (`painel_da_noite.trabalhou`).
4. Nenhum script cancela run de outro; grupo de concorrência é fila (`cancel-in-progress: false`),
   salvo o publicador.
5. O portão de esquema quarentena e não bloqueia a publicação; bloqueia só se a quarentena falhar.
6. Toda mudança na corrente passa pelos dois ensaios: o simulado (`scripts/ensaio_da_noite.py`) verde
   no PR **e** o real (`ensaio_real_da_noite.yml`) verde disparado depois do merge, antes das 23:30 UTC;
   vermelho é reverter ou consertar. Falha nova vira linha em `config/falhas_da_noite.json`.
- Todo workflow com `schedule:` tem entrada em `config/temporizadores.json`; nenhum temporizador fora dele.
- Nenhum commit automático na `main` fora da janela da noite (01:00–09:00 UTC); fora da `main`,
  só `ensaio-real/*` e `coleta-dia/*` recebem commit de elo.
- Antes de tocar coletor, workflow, cron ou `data/`: skill `noite-e-coletores`.

## O que barra a publicação de dado (editoria, 06/10/2026)

- Barra: integridade do dado (esquema → quarentena), segredo ou dado pessoal, vocabulário proibido e
  `texto_proibido`, página que não renderiza, trava de tamanho.
- Não barra (publica e abre Issue no `robo-registro`): layout, tipografia, CODEMAP, documentação e todo
  portão que só mede código. Perfil: `python3 scripts/portoes_locais.py publicacao`.
- Os portões seguem bloqueantes no PR; muda só o que barra o publicador.
- Medidor espera condição, nunca relógio (`scripts/_layout_dump.js`; prova em
  `scripts/testar_corrida_do_medidor.js`).
- Idempotência é portão de PR: `verificar_idempotencia_dos_derivados.py`.

## Log e fila que só crescem

- `data/log_buscas*`, `data/historico_mudancas.json` e filas de pista unem-se pela base comum
  (`base + nossos_novos + deles_novos`); total final ≥ cada lado; nunca deduplicar por conteúdo
  (execuções idênticas são tentativas distintas). Use `/merge-main`.
- Nas filas de pista: acréscimo dos dois lados entra; campo tocado por um lado entra; mesmo campo com
  valores diferentes é recusado.

## Regras editoriais do site

- Dizemos o que disponibilizamos, nunca o que não: "A metodologia é pública." Nenhuma frase sobre código,
  base de dados ou licença de dados (nem "dados abertos", nem "CC BY" em dado); a metodologia é o único
  material técnico público. Mapas e gráficos podem ser reproduzidos com crédito; recortes sob medida pelo
  e-mail da imprensa (editoria, 03/10/2026).
- Nunca inventar dado; ausência é lacuna declarada, com fonte; teto: "não localizamos até o corte",
  nunca "não existe".
- Zero, ausência de dado, dado indisponível e dado não coletado são coisas distintas.
- Decreto (`categoria=decreto`) não pontua no índice; mudança de pesos, créditos ou componentes exige
  versão maior (METODOLOGIA §12).
- Legendas, títulos de figura, tooltips e cartões só descrevem (variável, período, território, unidade,
  fato); interpretação vive no texto narrativo (portão 19, `verificar_legendas.js`).
- Texto explicativo direto ao que se vê, sem instrução de uso e sem nota interna.
- Nenhum nome de autor parlamentar no site.
- "Semana epidemiológica" é proibida em texto público: a semana sai em datas por `assets/semana.js`;
  eixos em meses. Portão: `verificar_semana_epidemiologica.js`.
- Decisão que exige a editoria (governança §29): redefinir metodologia, mudar significado de indicador,
  eliminar evidência substantiva, nova interpretação científica, mudar objetivo, conclusão não sustentada,
  alterar fato ou fonte. Ordem, agrupamento, redundância, posição de nota, transição, gramática e
  responsividade, o Claude decide.

## Nenhuma etapa humana (editoria, 08/10/2026)

- O código coleta, lê e julga sozinho: julgamento automático com documento oficial lido pela máquina,
  errata humana por linha (METODOLOGIA §106).
- Nenhuma fila, status ou texto "para humano / revisão / a aprovar" no código (portão
  `verificar_fila_nao_humana.py`); contribuição pública vira pista pela porta única e segue o juiz (D7).
- Dúvida vira a opção mais conservadora, registrada; na dúvida, o classificador não classifica.

## Blog (editoria, 03 e 04/10/2026)

- Blog = acontecimentos do ciclo em prosa corrida (onde, quando, quanto, quem, com fonte); sem tópicos,
  listas ou cartões; nada de método, decisões ou funcionamento do site (isso vive na metodologia e em
  `mudancas.html`).
- Dois textos por semana: *Legal e financiamento* (pacote de domingo, texto na segunda) e *Saúde*
  (pacote de quarta, texto na quinta); *Acontecimento* só quando algo grande ocorrer.
- O Code não escreve, não edita e não aprova texto do blog (`robo-registro/blog/*.md` é da central;
  guia `blog/GUIA_DE_REDACAO.md`); publica só o que tiver `aprovado: sim`.
- `gerar_pacote_blog.py`: só contagens, somas, listas alfabéticas, datas e documentos, cada fato com
  fonte, URL e data; sem ranking nem razão; dado com mais de nove dias vira lacuna. O pacote do workflow
  fica no artefato do run (90 dias); para o privado, roda-se o gerador à mão.
- `scripts/verificar_texto_blog.py` antes de publicar: todo número e data do corpo está no pacote;
  reprovado não vai ao ar e não bloqueia o site; número ausente do pacote corrige-se no gerador.

## Design

- Cor em hexadecimal só em `assets/tokens.css` e `assets/mapas.js`.
- Escala tipográfica fixa: 12 · 14 · 16 · 18 · 22 · 28 · 36 · 48 px.
- Elementos equivalentes usam o mesmo componente, classe e token; nada de ajuste manual de pixel.
- Toda figura usa o componente padrão de figura, com fonte e data de atualização, sem numeração.
- O fundo do site é **branco** (decisão editorial de 05/09, reafirmada em 23/09/2026): não reverter
  `--bg` para escuro nem osso por fidelidade à marca.
- Marca pessoal (paleta, tipografia, imagem, checklist): `docs/MARCA_PESSOAL.md` e skill `marca-pessoal`;
  a voz da marca não vale para conteúdo público (vence a governança, §16, §20, §24).
- Dúvida entre "mais bonito" e "mais rigoroso": o que preserva o rigor visível.

## Segurança e o que não entra neste repositório

- Repositório público: nunca commitar token, chave, senha ou `.env` preenchido.
- Material privado (LAI, notas jurídicas e internas, diagnósticos) vive no repositório privado.
- Nenhuma API ou produto pago dependurado no código, nem atrás de chave configurável.
- `robots.txt` é pedido, não tranca (RFC 9309 §1.3): respeitar `Crawl-delay`, cliente sempre
  identificado, rastro em `data/robots_registro.json`; nunca disfarçar o cliente
  (portão `verificar_cliente_identificado.py`).
- Bloqueio real (`401`, `403`, `429`, `451`, captcha, login) se respeita, sempre.
- Recusa servida com `200` (muro de robô, geobloqueio de WAF) é recusa:
  `coletores_base.detectar_muro_de_robo` levanta antes de preservar; nomear a recusa certo.
