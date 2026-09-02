# Como contribuir · Monitor El Niño Brasil

**Documentos e correções de dado** entram pelo formulário público do site
(`envie-dados.html`) — é a via que preserva a cadeia de prova (fonte oficial, número e
data do ato, análise humana). Não abra pull request alterando `data/*.json` diretamente:
o motor e os portões só aceitam dados que passaram por `aplicar_revisao.py`.

**Código, texto e design** entram por pull request contra `main`, seguindo
`docs/PROTOCOLO_ATUALIZACAO.md`: ramo próprio, os portões todos verdes
(`python atualizar.py` roda a suíte; ou os comandos de §3.3), CHANGELOG atualizado,
manifesto regenerado, nenhum segredo. O merge é da editoria.

**Método.** Mudanças que alterem pesos, créditos, componentes, faixas ou régua do índice
não são aceitas por PR: são decisões editoriais declaradas com data e vigência
(`METODOLOGIA.md` §12.4), nunca aplicadas durante o período eleitoral (§24).

**Conduta.** Debate técnico, com fontes; sem ataques pessoais; cláusula de
neutralidade: o Monitor não recomenda política pública nem identifica parlamentares.

**Segurança:** ver `SECURITY.md`.
