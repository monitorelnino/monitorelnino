# Resposta à Auditoria de 29/08/2026 · Pacote v2.2.3 para reauditoria

**Destinatário:** auditor da próxima rodada
**Pacote:** `monitorelnino-corrigido-29-08-2026.zip` (sucede `monitorelnino-corrigido-27-08-2026.zip`)
**Natureza:** acatamento integral do plano de correção C1–C9 do "Relatório de Auditoria Técnica para Correção" de 29/08/2026, mais uma mudança editorial-metodológica (fim do ranking ordinal como produto público — METODOLOGIA §13). **Motor de cálculo intocado** em toda a versão; a errata de dados do §16 (revisão de natureza dos instrumentos — AC/AM/PE) levou a média nacional de 41,1 para **40,2**, reproduzida bit a bit pelos portões após a correção. Ver seção própria abaixo.

## Estado dos itens do plano de correção

| Item | Estado | Critério de aceite verificado nesta sessão |
|---|---|---|
| C1 · SRI nas 4 tags de CDN | **Fechado** | `grep -c "integrity=" index.html` = 3; `proteja-se.html` = 1; portões 3 e 4 verdes. Hashes SHA-384 do relatório de 29/08/2026 (ambiente de edição sem acesso ao CDN — **conferir em prévia de navegador antes do deploy**); procedimento de recálculo institucionalizado no SBOM. |
| C2 · Fontes do Google | **Forma mínima fechada; forma forte pendente de deploy** | Dependência declarada no `docs/SBOM.md` (recurso externo sem SRI possível, com fundamento). Self-host dos `.woff2` registrado como pendência de deploy (requer rede aberta). |
| C3 · `unhandledrejection` no portão | **Fechado** | Listener adicionado; portão verde no estado atual; **teste negativo executado** (ReferenceError assíncrono proposital acusado com mensagem e linha exatas; restaurado, portão verde — CHANGELOG). Comentário de "LIMITAÇÃO CONHECIDA" atualizado. Registro honesto: no Node ≥15 a rejeição também derruba o processo ruidosamente — dupla cobertura. |
| C4 · `pip-audit`/`npm audit` na Action | **Fechado** | Duas etapas informativas (`continue-on-error: true`) antes dos portões; YAML validado; artefatos em `docs/*-audit-resultado.json`; pendência removida do SBOM; promoção a bloqueante aguarda política de CVE (decisão editorial, registrada). |
| C5 · Limpeza da fila | **Fechado** | Flag `--limpar` implementada e documentada como obrigatória em execução local (docstring + `docs/COMO_RODAR_E_PENDENCIAS.md` + LGPD §4/§5). Simulação: diretório ausente ao final. |
| C6 · Aviso de privacidade | **Fechado** | Parágrafo publicado abaixo do campo de e-mail em `envie-dados.html`, remetendo ao documento de privacidade e ao canal de exclusão; portões 3 e 4 verdes após a edição. |
| C7 · PDFs na selagem | **Fechado (saída forte "a")** | `scripts/gerar_manifesto.py` (novo, versionado) gera o manifesto **incluindo os dois PDFs**, com escopo declarado no cabeçalho; ordem canônica registrada (portões → PDFs → manifesto → `sha256sum -c`). Conferência desta selagem: 63/63 OK. |
| C8 · `gerar_tese.js` | **Fechado (ferramenta de sessão)** | Inventariado em `docs/AUDITORIA_CODIGO.md` §2 e `DOCUMENTACAO_TECNICA.md`; dependência `docx` documentada como instalação de sessão (`npm install --no-save docx`), deliberadamente fora de `package.json`; fora da selagem por escopo declarado no manifesto. |
| C9 · Critério de docstrings | **Fechado** | `scripts/cobertura_docstrings.py` (novo) fixa o critério (o do auditor: toda FunctionDef via AST); número publicado passa a reproduzir a saída do script. Cobertura elevada a **97/97 funções e 24/24 módulos** nesta versão. |

## Seção 6 do relatório (volatilidade do ranking) — decisão tomada

A recomendação foi acatada na **forma forte** (METODOLOGIA §13, decisão editorial datada de 29/08/2026): o ranking ordinal **deixa de ser produto público**. `rank_mediano`/`rank_p5`/`rank_p95` saíram de `data/indice.json` e migraram para `data/robustez_mc.json` — computados, selados e conferidos pelo portão 2 como antes, mas publicados apenas como evidência de robustez (anexo §5.8 da Documentação do Índice), onde o intervalo p5–p95 acompanha o rank mediano por construção. Produto público por UF: nota, faixa interpretativa e **confiança da verificação** (desambiguação do campo `confianca` registrada no §13 — era juízo de evidência, não de posição; a convivência sem distinção produzia leitura contraditória, inclusive no relatório de auditoria executada, que leu o intervalo do ES como "confiança atribuída ao ranking").

## Adição metodológica desta rodada (além do plano C1–C9)

**Regra do Distrito Federal — METODOLOGIA §14** (registro ex-ante, caso dormente): verificação jurídica da acumulação de competências do DF (Lei 12.608 art. 2º; CF arts. 32 §1º e 23) e declaração antecipada de que um futuro instrumento distrital preencherá os dois componentes por força constitucional, com simetria de critérios e duas pistas de verificação registradas. Não altera nenhum número publicado (DF permanece LAC, cobertura 0,0).

**Prazos federais e vigia de sinais — METODOLOGIA §15**: registro curado de marcos (`data/marcos_prazos.json`), rotina de checagem de prazos × banco (`verificar_prazos_legais.py` → `data/prazos_uf.json`, marcador editorial, nunca pontuação) e rotina de descoberta (`monitorar_sinais_federais.py` → `data/pistas_sinais.json`, triagem humana, nunca classificação; self-test offline com garantia de não-escrita nos curados). Ambas informativas na Action. Nenhum número publicado muda; pista PA/ADPF registrada para a fila humana.

**Errata de dados e portão de natureza — METODOLOGIA §16**: revisão dos 27 estados (varredura de léxico + verificação em fonte primária, buscas logadas) corrigiu AC (ato de resposta pontuado → base trocada para o Decreto 11.899, READ/antec 100, 58,0→69,6), AM (data corrigida, antec 60→100, 70,8→84,1) e PE (Situação de Emergência SINPDEC pontuada como NOVO → LAC, 58,8→8,8; 2ª rodada de bateria negativa obrigatória pré-publicação); MS e PA sustentados. Novo portão bloqueante de natureza em `verificar_consistencia.py` (campo `natureza_doc` + `justificativa_ex_ante`), validado por teste negativo real. Superfícies (gauge, tabela risco×instrumento, figuras CONSIST/AREAS) sincronizadas sob o portão de figuras.

## O que conferir na reauditoria

1. Protocolo canônico completo (verde nesta sessão, ponta a ponta): `verificar_vigencia.py` → `recalcular_mare.py --check` (agora 27×7 campos + robustez) → 4 portões → `gerar_pdf_*.py` → `scripts/gerar_manifesto.py --check` → `sha256sum -c docs/MANIFEST_SHA256.txt` (63 arquivos, PDFs incluídos).
2. Bateria de sensibilidade (`analise_sensibilidade.py`): executada integralmente nesta sessão, resultados inalterados (knockout máx. 9; MC estável a ±1 posição entre sementes e em 10k×100k).
3. Teste negativo do C3 (reproduzir se desejado): injetar `Promise.resolve().then(() => { x; })` em `index.html`, confirmar acusação clara, restaurar.
4. Bloqueios pré-publicação **remanescentes e inalterados**: cadastrar os três segredos de produção (inclui a chave do Portal da Transparência para `atualizar_transferencias.py`); conferência dos hashes SRI em prévia de navegador; pendências metodológicas pré-lançamento listadas em `docs/COMO_RODAR_E_PENDENCIAS.md` §4-5.
