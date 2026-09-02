# Política de segurança · Monitor El Niño Brasil

**Como reportar.** Vulnerabilidades no site, nos dados ou na automação: e-mail para
contato@futuraevidencelab.com.br com o assunto "SEGURANÇA — Monitor El Niño". Não abra
issue pública com detalhes exploráveis. Resposta em até 5 dias úteis; correção priorizada
conforme severidade; crédito ao relator, se desejar, no CHANGELOG.

**Escopo.** `monitorelnino.com.br` e este repositório (`monitorelnino/monitorelnino`),
incluindo a rotina automática (`.github/workflows/`) e a cadeia de contribuições do
formulário público. Fora do escopo: serviços de terceiros (Netlify, GitHub, VLibras,
fontes oficiais consultadas).

**Regras que valem para nós mesmos.**
- Nenhum segredo em código, commit, CHANGELOG ou relatório do robô (portão de consistência).
- Toda entrada externa (formulário, documentos baixados) é validada por esquema e
  escapada na carga antes de qualquer interpolação em HTML (auditoria externa de
  02/09/2026, AUD-02/AUD-03); a autoaplicação de contribuições está **suspensa** até
  que os testes negativos de XSS/SSRF rodem no CI.
- URLs de fonte só são aceitas com `https`, sem credenciais, em domínios oficiais
  (allowlist), com resolução DNS pública e redirecionamentos revalidados.
- Cabeçalhos: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
  Permissions-Policy (`netlify.toml`).
- Dependências travadas (`requirements.txt`, `package-lock.json`); `pip-audit` e
  `npm audit` a cada mudança de dependência; SBOM em `docs/`.

**Auditorias externas.** A auditoria anônima de 02/09/2026 (Manus AI, commit `3f049a6`)
está registrada no CHANGELOG com o estado de cada achado.
