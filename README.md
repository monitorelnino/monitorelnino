# Monitor El Niño Brasil — 2026/2027 · Pacote de publicação

Nome da plataforma: **Monitor El Niño Brasil — MARÉ**. Pergunta-guia da edição:
"Quem se antecipa, quem apenas reage — e onde agir agora?" Publicação: Futura Evidence Lab.

Plataforma estática com dados externos editáveis. Todos os gráficos, mapas, o índice
e a tabela são gerados dinamicamente a partir dos arquivos em `data/` — para atualizar
a plataforma, **edite apenas os JSONs**; não é preciso tocar no `index.html`.

## Documentação para auditoria profissional

Pacote completo em `docs/`, mais estes arquivos na raiz: `CHANGELOG.md`
(histórico de versões), `LICENSE` (MIT do código), `.env.example` (as três
variáveis de ambiente), `package.json`/`requirements.txt` (dependências
travadas em versão exata). Em `docs/`: `AUDITORIA_CODIGO.md` (arquitetura,
inventário completo dos 20 scripts, segurança e superfície de ataque),
`AUDITORIA_METODOLOGIA.md` (o que o índice mede, cadeia de cálculo,
fontes), `COMO_RODAR_E_PENDENCIAS.md` (instalação, execução, deploy,
pendências declaradas), `LGPD_PRIVACIDADE.md` (o único ponto de coleta de
dado pessoal do sistema, com o fluxo completo até o descarte),
`SBOM.md` + `sbom-python.cdx.json` + `sbom-node.cdx.json` (inventário de
dependências em formato CycloneDX, gerado por ferramenta oficial, com
auditoria de vulnerabilidades) e `MANIFEST_SHA256.txt` (hash de
integridade de cada artefato publicado).

## Como publicar

- **Vercel/Netlify:** arraste a pasta inteira no painel (deploy em ~1 min), ou conecte um repositório Git.
- **Teste local:** `npx serve` (ou `python3 -m http.server`) dentro da pasta e abra o endereço indicado.
- **Atenção:** abrir o `index.html` com duplo clique NÃO funciona — o navegador bloqueia
  o `fetch` de arquivos locais. É preciso servir via HTTP (local ou hospedado).

### Segredos e chaves da hospedagem (OBRIGATÓRIO antes do primeiro deploy)

O site em si é estático e não usa chave alguma; as chaves são da **automação semanal**
(GitHub Actions) e sem elas partes da plataforma param de se atualizar. Cadastre as três
em GitHub → repositório → *Settings → Secrets and variables → Actions*:

| Segredo | Para quê | Como obter | Sem ele |
|---|---|---|---|
| `PORTAL_TRANSPARENCIA_API_KEY` | Atualização semanal do painel de financiamento (`transferencias.json`) | api.portaldatransparencia.gov.br → "Solicitar cadastro" (gratuito, por e-mail; a chave chega por e-mail) | painel de financiamento congela no corte do último deploy — **item da checklist pré-publicação: cadastrar ANTES do primeiro deploy** |
| `NETLIFY_AUTH_TOKEN` | Leitura das contribuições de leitores enviadas pelo formulário | Netlify → User settings → Applications → New access token | contribuições ficam retidas no Netlify sem triagem automática nem fila |
| `NETLIFY_SITE_ID` | Identifica o site do formulário | Netlify → Site configuration → Site ID | idem |

A cada execução, a Action avisa no log qual segredo falta. Teste local: exporte as
variáveis no terminal antes de rodar `python3 atualizar.py`.

## Estrutura

```
monitor-el-nino/
├── index.html                 ← o monitor (mapa, índice, consulta municipal, PDFs)
├── mapas-e-graficos.html      ← 7 mapas e 6 gráficos
├── proteja-se.html            ← orientações oficiais, por risco projetado
├── envie-dados.html           ← formulário público de contribuição
├── obrigado.html              ← confirmação da contribuição
├── para-gestores.html         ← checklist de publicação para prefeituras
├── data/                      ← ÚNICA fonte de verdade do site (28 arquivos)
│   ├── estados.json           ← 27 UFs: status, órgão, documento, capital
│   ├── municipios.json        ← registros municipais verificados (265)
│   ├── indice.json            ← MARÉ por UF (componentes, confiança)
│   ├── percentual_uf.json · pontos_mapa.json · geo_uf.json · consist.json
│   ├── atos_resposta.json     ← decretos de emergência (registro; não pontuam)
│   ├── marcos_prazos.json · prazos_uf.json   ← marcos legais/judiciais (§15)
│   ├── transferencias.json · financiamento_uf.json · recursos_uf.json
│   ├── historico_mudancas.json · snapshot_feed.json  ← base dos feeds
│   ├── pistas_imprensa.json · pistas_sinais.json     ← filas de descoberta
│   └── (referências: municipios_ibge_referencia, populacao_censo2022, meta…)
├── selos/                     ← 27 selos SVG + nacional, embutíveis
├── feeds/                     ← Atom: brasil.xml + 27 por UF + index.json
├── dados-abertos/             ← CSVs + datapackage.json (Frictionless)
├── scripts/                   ← portões e auditorias (Node e Python)
│   ├── verificar_estrutura.js · verificar_runtime.js · verificar_runtime_mapas.js
│   ├── auditar_pdfs.py (+2 .js) · auditar_ux.js   ← auditorias manuais
│   └── validar_dicionario.py · cobertura_docstrings.py · gerar_manifesto.py
├── docs/                      ← auditorias, LGPD, SBOM, dados abertos, como rodar
├── METODOLOGIA.md/.pdf · CHANGELOG.md · CITATION.cff · LICENSE
└── *.py                       ← pipeline (ver "Atualização automática")
```

## Vocabulário controlado de categorias (OBRIGATÓRIO)

Use SOMENTE estes valores no campo `categoria` (municipios.json e pontos_mapa.json).
A distinção reativo × preventivo é a espinha dorsal metodológica da plataforma — não misture.

| Valor | Significado | Critério de uso |
|---|---|---|
| `plano` | Plano preventivo publicado | Documento de contingência/prevenção formal, publicado, edição atual |
| `plano_antigo` | Plano preventivo desatualizado | PLANCON publicado, mas edição de anos anteriores sem atualização para o ciclo |
| `plano_elaboracao` | Plano em elaboração | Anunciado oficialmente, mas SEM documento final publicado |
| `decreto` | Decreto reativo de emergência | Decreto de SE/ECP por estiagem/seca/chuva JÁ instalada — resposta, não prevenção |
| `coberto_estadual` | Sem plano próprio, coberto pelo estado | Nenhum documento municipal; cobertura só via instrumento estadual |
| `nao_el_nino` | Ato existe, mas não é de El Niño | Ex.: emergência sanitária (caso Amapá). NUNCA conta como preparação p/ El Niño |
| `nao_localizado` | Nenhum ato localizado | Verificado e nada encontrado em fonte pública — registrar a data da checagem |

## Regras de fonte (OBRIGATÓRIO)

1. **Nunca inventar link.** O campo `url` só recebe endereço realmente verificado.
   Sem URL confirmada → `"url": null` e o nome da fonte em `fonte`.
2. **Hierarquia de fontes:** Diário Oficial (DOU/DOE/DOM) > site oficial do órgão
   (prefeitura/Defesa Civil) > imprensa (só como complemento, nomeando o veículo).
3. **Decretos municipais:** linkar a plataforma DOM do estado onde o ato foi publicado
   (DOM/PB famup, DOM/AL ama, DOM/RN femurn, DOM/PA famep, DOM/SE sergipe — todas em
   diariomunicipal.com.br) e SEMPRE registrar nº do decreto + data em `documento`,
   para que o leitor localize o ato dentro da plataforma.
4. **Registrar a data de verificação** ao atualizar qualquer linha (campo `data` ou
   observação) — um dado sem data de checagem perde valor rapidamente neste tema.
5. **Não converta ausência em negação:** `nao_localizado` significa "não achamos em
   fonte pública", nunca "o município não tem plano".

## Como atualizar cada arquivo

**Adicionar município verificado** → nova entrada em `municipios.json`
(`nome, uf, categoria, documento, data, fonte, url, lat, lon, canal`)
(`canal` ∈ {DOM, DOU, repositorio_estadual, orgao_estadual, site_municipal, imprensa, —}) e em `pontos_mapa.json`
(`nome, uf, categoria, lat, lon, fase`). Coordenadas: use as oficiais do IBGE/dataset
de municípios (não estime).

**Atualizar % por estado** → `percentual_uf.json`: ajuste `com_ato` (municípios com
`plano`, `plano_antigo` ou `decreto`) — `pct` = com_ato/total×100, com 2 decimais.
`nao_el_nino`, `plano_elaboracao` e `nao_localizado` NÃO entram no numerador.

**Recalcular o MARÉ** (`indice.json`) — metodologia v2.2.4 (reestruturação populacional + régua de antecipação formalizada §5.2.1, 27/08/2026), com Correção B; o cálculo canônico é `python3 recalcular_mare.py --write` (nunca recalcule à mão — ver DOCUMENTACAO_TECNICA.md §5):
```
total      = média simples dos 3 componentes (pesos iguais, 1/3 cada)
total_geo  = média geométrica dos 3 componentes com piso 5 (penaliza desequilíbrio; estilo INFORM)
rank_p5/p95 = intervalo de posições em 90% de 10.000 simulações Monte Carlo
              (pesos sorteados uniformemente no simplex — Dirichlet(1,1,1))
```
Justificativa: sem base para diferenciar a importância dos componentes, pesos iguais são
a escolha neutra recomendada pelo Handbook OCDE/JRC (2008); a sensibilidade do ranking à
escolha dos pesos é quantificada e publicada, em vez de escondida. Ao atualizar os
componentes, re-rode o Monte Carlo para atualizar os intervalos.
- `estado`: NOVO=100 · READ(readaptado)=65 · VIG(recorrente)=45 · ELAB=35 · LAC(lacuna)=0
- `cobertura_pop` (v2.2): Σ(população_Censo2022 × crédito) ÷ população_UF × 100 (máx. 100)
  crédito: plano=1,0 · plano_antigo=0,6 · plano_elaboracao=0,45 · coberto_estadual=0,3 ·
  nao_localizado=0 · decreto=0 (Correção B) · nao_el_nino=0 (vocabulário > escala; ver
  METODOLOGIA §12.4.3). Agregados e camada declarada sem lista nominal: excedente ×
  população municipal MEDIANA da UF × crédito (declarada com desconto de 50%: ×0,5 e ×0,3).
  População: data/populacao_censo2022.json, validado por atualizar_populacao.py.
  A capital não tem mais bloco próprio: vale sua fração demográfica real; a exibição
  editorial dela no card de detalhe continua (estados.json).
- (extinto na v2.2) `capital`: plano=100 · plano_antigo=60 · plano_elaboracao=45 ·
  coberto_estadual=30 · nao_el_nino=10 · nao_localizado=0
- (extinto na v2.2) `municipal` (v2.1): [documentada + declarada] ÷ total_municípios × 100, onde
  documentada = n_plano×1,0 + n_plano_antigo×0,7 (o peso do decreto — 0,4 na v2.1 original —
  foi REMOVIDO pela Correção B de 26/08/2026: decreto é ato de resposta e não pontua em
  nenhum componente; o registro permanece no banco como transparência) e
  declarada = excedente_declarado_plano×0,5 + declarado_desatualizado×0,35
  (fontes declaradas aceitas: levantamentos de TCE e sistemas estaduais — TCE-RS 2025,
  Painel Farol TCE-SC 2026, SISDC/CEPDEC-PR; regra: "declaração vale metade do documento")
- `antecipacao`: 100 se o instrumento estadual foi publicado ANTES do Boletim nº 1 do
  Painel El Niño (29/06/2026); 60 até ~30 dias depois; 30 depois disso; 40 para estruturas
  permanentes/recorrentes; 0–10 para apenas reação por decreto ou nada datado.
- `confianca`: "Alta" = varredura municipal aprofundada (Fase 2) · "Média" = plano estadual
  verificado + capital · "Baixa" = apenas capital verificada.

**Status estadual** → `estados.json` (campo `status` de cada UF: NOVO/READ/ELAB/VIG/LAC)
e o texto de `doc`/`data`/`capital.info`.

## Financiamento — o caminho do recurso e como manter atualizado

O arquivo `data/transferencias.json` cobre três coisas distintas — não misture:
1. `programas` — visão geral de instrumentos financeiros (federal/estadual), nem sempre rastreável por município.
2. `repasses_rs` — lista nominal de municípios com repasse confirmado (hoje: Prepara RS).
3. `fontes_monitoramento` — links oficiais para acompanhar novos repasses.

### Atualização automática

O pacote inclui um pipeline orquestrado por `atualizar.py` e pelo workflow
`.github/workflows/atualizar.yml` (21 etapas em 31/08/2026; lista canônica e
requisitos de rede em `docs/COMO_RODAR_E_PENDENCIAS.md`). Em resumo:

1. **Descoberta (informativa, nunca escreve no banco):** `atualizar_boletins.py`
   (novo Boletim do Painel El Niño), `monitorar_sinais_federais.py` (DOU e
   STF → `data/pistas_sinais.json`), `monitorar_imprensa_regional.py` e
   `monitorar_atos_resposta.py` (imprensa → `data/pistas_imprensa.json`),
   `monitorar_politica_por_inteiro.py` (painel da Talanoa → filas),
   `verificar_prazos_legais.py` (marcos e prazos → `data/prazos_uf.json`).
2. **Julgamento automático com rollback:** `julgar_e_aplicar_descobertas.py`
   — só aplica pista com fonte oficial e citação completa; o resto vai para a
   fila humana. Contribuições do formulário: `processar_contribuicoes.py`.
3. **Dados oficiais:** `atualizar_instrumentos_estaduais.py` (repositórios
   estaduais, Camada 1) e `atualizar_transferencias.py` (Portal da
   Transparência; requer `PORTAL_TRANSPARENCIA_API_KEY`).
4. **Portões bloqueantes, nesta ordem:** `scripts/verificar_estrutura.js` →
   `verificar_consistencia.py` → `recalcular_mare.py --check` →
   `scripts/verificar_runtime.js` → `scripts/verificar_runtime_mapas.js`.
   Qualquer falha interrompe antes do commit.
5. **Pós-portões:** PDFs regenerados, `verificar_links.py` (informativo, com
   artefato), `data/meta.json` carimbado, commit de `data/`, `index.html`,
   `mapas-e-graficos.html` e `recalcular_mare.py`.

**Quando a etapa 2 encontrar propostas:** revise `data/instrumentos_revisar.json` (apague o que não deve entrar) e rode `python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json` — esse script mescla a revisão aprovada em `municipios.json`/`pontos_mapa.json`, chama `recalcular_mare.py --write`, atualiza o corte e roda os três portões (4/5/7 acima) de ponta a ponta. Nada é publicado automaticamente sem essa aprovação.

**Prévia single-file (fora deste pipeline):** o arquivo de prévia usado para revisão fora do site publicado (não é commitado nem servido) tem seus dados embutidos como constantes e precisa ser resincronizado manualmente após qualquer mudança em `data/`, com `python3 scripts/sincronizar_single_file.py --arquivo <caminho-da-prévia> --tambem-pacote index.html`.

**Execução local:** `python atualizar.py` (os três portões já rodam dentro dele).

**Execução automática:** o workflow `.github/workflows/atualizar.yml` roda toda segunda-feira (e sob demanda). Node/jsdom são instalados **antes** de `atualizar.py` (corrigido em 26/08/2026 — a ordem antiga rodava o Python primeiro e quebraria com "Cannot find module 'jsdom'" na primeira execução real, já que os dois portões em Node ficaram internos ao orquestrador). Cadastre a chave da API como *secret* `PORTAL_TRANSPARENCIA_API_KEY` no repositório. Em Vercel/Netlify, o push do bot dispara o redeploy automaticamente.

## Contribuições de leitores (retroalimentação)

A página "Ajude a completar o mapa" (envie-dados.html) usa **Netlify Forms**: as submissões ficam armazenadas no painel do Netlify (aba *Forms*; ative ali a notificação por e-mail, sem expor endereço no site). A rotina `verificar_contribuicoes.py` puxa a fila pela API (variáveis `NETLIFY_AUTH_TOKEN` e `NETLIFY_SITE_ID`), aplica a triagem automática de completude (campos, município na base IBGE, domínio aparente, duplicidade) e gera a checklist de conferência humana em `fila_contribuicoes/` (fora do versionamento, por conter possíveis e-mails). **Nada entra no banco automaticamente**: a entrada é decisão humana após verificação documental, com o canal de origem do documento registrado. Para levar um item aprovado da fila até o banco, use `converter_contribuicao.py` (gera uma entrada em `data/instrumentos_revisar.json`, o mesmo arquivo da descoberta automática de repositórios) e então `aplicar_revisao.py` — o mesmo ponto único de aplicação para os dois canais de entrada.
