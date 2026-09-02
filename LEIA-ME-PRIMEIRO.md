# Monitor El Niño Brasil · MARÉ v2.3 — PACOTE ÚNICO (02/09/2026)

**A versão desta edição é v2.3 — designação editorial de 02/09/2026 para o redesenho da verificação (níveis, defeso, fontes, saúde). O motor de cálculo é o mesmo da v2.2.3; nenhuma nota mudou.**
Corte de dados: 31/08/2026 · média nacional 45,9 · 6 páginas · 265 registros municipais.

Este pacote contém TUDO: o site pronto para publicar, o pipeline completo para
auditar e operar, e a documentação. Um único diretório serve aos três usos.

## Como usar, por papel

**Para PUBLICAR** — o site é a própria raiz deste pacote: as 6 páginas
(`index.html`, `mapas-e-graficos.html`, `proteja-se.html`, `envie-dados.html`,
`obrigado.html`, `para-gestores.html`) e os diretórios que elas referenciam
(`data/`, `selos/`, `feeds/`, `dados-abertos/`), mais os PDFs e o
`netlify.toml`. Suba a raiz inteira para o Netlify (ou qualquer hospedagem
estática): os scripts `.py`/`.js` e a documentação não atrapalham — são
arquivos servidos como qualquer outro, e é assim que a metodologia aberta fica
auditável no próprio site. Roteiro de 30 minutos: `INSTALACAO_E_AUDITORIA.md`,
seção 2.

**Para AUDITAR** — protocolo na seção 3 do mesmo guia: 5 portões bloqueantes
(`verificar_estrutura`, `verificar_consistencia`, `recalcular_mare --check`,
`verificar_runtime`, `verificar_runtime_mapas`) + auditorias de PDFs,
acessibilidade e links. Integridade: `docs/MANIFEST_SHA256.txt` sela cada
artefato (`sha256sum -c` confere).

**Para OPERAR** — `python3 atualizar.py` roda o pipeline com os portões
dentro; a Action semanal está em `.github/workflows/atualizar.yml`. Seções 4 e
5 do guia: vigias, segredos e pendências.

## Atenção

Os arquivos avulsos `pagina_1_…` a `pagina_6_….html` que circularam fora deste
pacote são **prévias de revisão visual** (dados embutidos, nomes com prefixo).
**Não publicar, não renomear, não auditar como se fossem o site** — o site é
este pacote.
