# Resposta à Segunda Auditoria de 29/08/2026 · Pacote v2.2.3

**Origem:** Segunda Auditoria · Monitor El Niño Brasil (MARÉ v2.2.3), executada por Manus AI em 29/08/2026 sobre `monitorelnino-corrigido-29-08-2026.zip`.

**Veredito recebido:** aprovado — nove itens C1–C9 verificados (oito fechados integralmente, C2 fechado na forma mínima com forma forte registrada como pendência de deploy), protocolo canônico verde de ponta a ponta, nova média nacional (40,2) reproduzida bit a bit, zero regressões contra a linha de base da primeira auditoria.

## R1 — resolvido (não apenas declarado)

**Achado:** a selagem dos PDFs (C7) não era reproduzível fora da sessão de geração — o reportlab embute metadados de data/ID a cada build, então dois PDFs de conteúdo idêntico tinham hashes diferentes. O manifesto só conferia para quem recebia o pacote pronto, nunca para quem regenerava os PDFs. O auditor sugeriu duas saídas: declarar a limitação, ou perseguir determinismo real via `SOURCE_DATE_EPOCH`.

**Resolução adotada — a saída forte.** `gerar_pdf_indice.py` e `gerar_pdf_metodologia.py` agora fixam `SOURCE_DATE_EPOCH` a partir da data de corte dos dados (`data/meta.json`), lida nativamente pelo reportlab ≥4. Os PDFs passam a ser função determinística dos **dados**, não do **instante de geração**. Verificações feitas nesta correção:

- Dois builds consecutivos, sem qualquer configuração externa: hash SHA-256 idêntico nos dois PDFs.
- Controle negativo: sem a variável fixada, os hashes voltam a divergir (confirma que a causa é a variável, não coincidência).
- Controle positivo: alterar o conteúdo do METODOLOGIA.md ainda produz hash diferente — o determinismo não mascara divergência real de conteúdo.
- `scripts/gerar_manifesto.py --check` agora **prova** o determinismo a cada execução (regenera os dois PDFs e compara com o manifesto vigente antes de conferir o resto), não apenas o declara. Validado por teste negativo real: desativei propositalmente o fixador, o guard acusou o hash divergente exato, restaurado, verde de novo.

**Consequência prática para o próximo auditor:** rodar `gerar_pdf_*.py` e depois `gerar_manifesto.py --check` fecha sem precisar regravar o manifesto — exatamente o cenário que falhava na segunda auditoria.

Documentado em `docs/AUDITORIA_CODIGO.md` §5 e no CHANGELOG (v2.2.3).

## Observações menores — resolvidas

- **`__pycache__/` no pacote**: removido do empacotamento. Já estava coberto pelo `.gitignore`; o vazamento era do `zip` manual usado para gerar o pacote de entrega, não do repositório.
- **Pendência do PE (2ª rodada de bateria negativa)**: mantida visível e inalterada, como o auditor recomendou — não é item desta correção.

## O que conferir na terceira rodada (se houver)

1. `python3 gerar_pdf_indice.py && python3 gerar_pdf_metodologia.py && python3 scripts/gerar_manifesto.py --check` — deve fechar sem regravar hash nenhum.
2. Confirmar ausência de `__pycache__/` no pacote entregue.
3. Bloqueios pré-publicação inalterados: os três segredos de produção, conferência dos hashes SRI em prévia de navegador, e a segunda rodada da bateria negativa de PE.
