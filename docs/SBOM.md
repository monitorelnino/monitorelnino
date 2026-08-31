# SBOM (Software Bill of Materials) · Monitor El Niño Brasil · v2.2.2

Gerado em 27/08/2026 por ferramentas oficiais do próprio ecossistema, não à
mão: `cyclonedx-py` (CycloneDX Python) contra um ambiente virtual limpo
criado só para este relatório, e `@cyclonedx/cyclonedx-npm` (CycloneDX
oficial do npm) contra `package.json`/`package-lock.json`. Os artefatos
machine-readable ficam ao lado deste resumo:

- `docs/sbom-python.cdx.json` — CycloneDX 1.6, formato JSON
- `docs/sbom-node.cdx.json` — CycloneDX 1.6, formato JSON
- `docs/pip-audit-resultado.json` / `docs/npm-audit-resultado.json` — evidência bruta da auditoria de vulnerabilidades

## Dependências diretas

| Ecossistema | Pacote | Versão travada | Usado por |
|---|---|---|---|
| Python | requests | 2.33.1 | scripts `atualizar_*` e `consultar_querido_diario.py` (chamadas HTTP a APIs oficiais) |
| Python | numpy | 2.4.4 | `analise_sensibilidade.py` (Monte Carlo, correlações) |
| Python | openpyxl | 3.1.5 | leitura/escrita auxiliar de planilhas (verificação de dados de origem) |
| Python | reportlab | 4.4.10 | `gerar_pdf_indice.py`, `gerar_pdf_metodologia.py` |
| Node.js | jsdom | 30.0.1 | `scripts/verificar_estrutura.js`, `scripts/verificar_runtime.js` (navegador simulado) |
| Node.js | d3 | 7.9.0 | `scripts/verificar_runtime.js` (os mesmos mapas do site, executados de verdade no portão) |

O site publicado (`index.html`, `proteja-se.html`, `envie-dados.html`) não
tem dependência de build: Chart.js, d3 e jsPDF são carregados no navegador
do visitante via CDN (`cdnjs.cloudflare.com`), listados no `<head>` de cada
página, fora do escopo deste SBOM porque não são instalados neste
repositório — o auditor deve inspecioná-los como recurso externo carregado
em runtime pelo próprio navegador do usuário final. Desde 29/08/2026 (C1 da
auditoria externa), as quatro tags carregam SRI (SHA-384) com
`crossorigin="anonymous"`; os hashes valem apenas para as versões exatas
fixadas — a cada bump de versão, recalcular com
`curl -s URL | openssl dgst -sha384 -binary | openssl base64 -A` e conferir em
prévia de navegador (procedimento institucionalizado aqui, como o relatório
recomenda). **Recurso externo adicional declarado (C2):** as quatro páginas
carregam CSS de `fonts.googleapis.com` (famílias Fraunces, Archivo e Archivo
Narrow) — dependência **sem SRI possível**, porque o CSS desse endpoint varia
por User-Agent; risco menor que o de script (CSS não executa lógica
arbitrária), mitigação recomendada: self-host dos `.woff2` em `assets/fonts/`
com `@font-face` local (pendência de deploy, seção de pendências).

## Transitivos

- Python: mais sete pacotes na árvore de dependência real (`certifi`,
  `charset-normalizer`, `idna`, `urllib3` — a cadeia HTTP do `requests`;
  `pillow`, `et_xmlfile` — insumos do `reportlab`/`openpyxl`). Total do
  ambiente isolado: 11 pacotes, listados por completo no CycloneDX.
- Node.js: 75 componentes na árvore transitiva de `jsdom` (que embute um
  parser de HTML/CSS completo) e `d3`. Nenhuma dependência de produção do
  site em si: escopo inteiramente confinado aos portões de verificação.

## Auditoria de vulnerabilidades conhecidas (27/08/2026)

- `pip-audit` contra `requirements.txt`: **nenhuma vulnerabilidade
  conhecida** nos quatro pacotes diretos.
- `npm audit` contra `package-lock.json`: **nenhuma vulnerabilidade
  conhecida** (0 info/low/moderate/high/critical).
- Dois avisos de descontinuação (não vulnerabilidade) observados na
  instalação do npm, herdados de transitivos de `jsdom`:
  `prebuild-install@7.1.3` (não mantido) e `glob@10.5.0` (versão antiga,
  recomenda atualização). Nenhum dos dois é dependência direta deste
  projeto nem afeta o site publicado; registrado aqui por transparência,
  não por risco identificado.

## Política de atualização

As versões Python foram travadas (antes: faixas `>=`) em 27/08/2026 para
que o pipeline seja reproduzível bit a bit pelo auditor. Reabrir a trava
para receber patches de segurança é decisão editorial explícita, não
automática — o próprio `pip-audit`/`npm audit` acima é o instrumento
recomendado para decidir quando uma atualização é necessária.

## Pendências declaradas

- ~~Adicionar hashes de integridade (SRI) às bibliotecas de CDN~~ —
  **fechada em 29/08/2026 (C1)**: as quatro tags têm `integrity=` SHA-384;
  conferência obrigatória em prévia de navegador antes do próximo deploy.
- ~~Automatizar `pip-audit`/`npm audit` no pipeline semanal~~ — **fechada em
  29/08/2026 (C4)**: duas etapas informativas na Action, artefatos em
  `docs/*-audit-resultado.json`; promover a bloqueantes quando a política de
  resposta a CVE for decidida (decisão editorial pendente, registrada aqui).
- Self-host das fontes do Google (Fraunces, Archivo, Archivo Narrow) em
  `assets/fonts/` — recomendação da auditoria (C2, forma forte), requer
  baixar os `.woff2` em ambiente com acesso; até lá, a dependência fica
  declarada acima como recurso externo sem SRI possível (forma mínima,
  aplicada em 29/08/2026).
