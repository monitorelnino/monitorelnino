# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: — a — (0 execução(ões) registrada(s), 7 dias de histórico).

Nenhum script essencial com erro e nenhum coletor errando duas rodadas seguidas.

## Última execução de cada script

Sem linhas de saúde ainda. O arquivo é escrito pelos jobs noturnos e pelo publicador, a partir de `scripts/saude_pipeline.py --rodar`.
