# Levantamento: o que é público sem LAI (início em 02/09/2026)

**Objetivo (decisão editorial de 02/09/2026):** antes de enviar os 55 pedidos de
acesso à informação, verificar, UF a UF, se a lista de municípios com plano de
contingência já é pública em fonte oficial. A LAI fica só para o que faltar.
Cada busca está no log (`data/log_buscas.json`, executor `claude`, 02/09/2026).

| UF | O que existe sem LAI | Situação | LAI necessária? |
|---|---|---|---|
| PR | SISDC/PCO (declarado, já usado) | fonte em uso | não, para a lista |
| SC | Farol/TCE-SC (declarado, já usado) | fonte em uso | não, para a lista |
| RS | TCE-RS (declarado, já usado) | fonte em uso | não, para a lista |
| SE | **Repositório estadual público** de planos municipais (defesacivil.se.gov.br/planos-de-contigencia/, atualizado 09/03/2026) | a inventariar e ligar ao coletor de repositórios estaduais | provavelmente não |
| AM | **Repositório estadual público** (defesacivil.am.gov.br/planos-de-contingencia-municipais/) | a inventariar e ligar ao coletor | provavelmente não |
| PB | Só ICM/MIDR (4 A · 39 B · 81 C · 99 D) reproduzido pela imprensa oficial; sem lista de planos no sítio estadual | camada declarada (C5), não registro | **sim** |
| PE | Planos municipais avulsos (ex.: Cabo de Santo Agostinho 2026); sem lista estadual localizada | pistas municipais | **sim** (lista estadual) |
| BA | Portal estadual fora do ar por defeso (02/09) | fonte suspensa | **sim** |
| RN | nada localizado nesta primeira passada | a repetir | **sim** (provável) |
| demais 18 UFs | a levantar | — | — |

**Próximos passos:** (1) inventariar os repositórios de SE e AM e escrevê-los como
fontes de `atualizar_instrumentos_estaduais.py` (canal `repositorio_estadual`);
(2) repetir a passada nas 18 UFs restantes, duas buscas por UF, logadas;
(3) filtrar `data/lai_pedidos.json`: pedidos de defesa civil só para UFs sem
fonte pública; os de saúde permanecem (nenhuma lista pública localizada até aqui).
