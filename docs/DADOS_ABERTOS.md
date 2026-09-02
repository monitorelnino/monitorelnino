# Dados abertos do Monitor El Niño Brasil

Tudo o que o site mostra vem de `data/*.json`, público no repositório. Esta
página descreve a exportação **citável** desses dados, gerada a cada
atualização por `gerar_dados_abertos.py` em `dados-abertos/`.

## Arquivos

| Arquivo | O que é | Chave |
|---|---|---|
| `indice.csv` | Índice MARÉ por UF: `mare_total` (0–100), `faixa` (estágio inicial · em construção · consolidado · avançado), componentes e status estadual | `uf` |
| `estados.csv` | Instrumento estadual localizado: `status` (NOVO, READ, VIG, ELAB, LAC), `natureza_doc`, documento, data, órgão, URL | `uf` |
| `municipios.csv` | Registros municipais verificados individualmente: `categoria` (vocabulário controlado do README), documento, data, fonte, URL | `uf` + `municipio` |
| `atos_resposta.csv` | Decretos de emergência/calamidade registrados — atos de resposta, nunca pontuam | `uf` + `municipio` + `data` |
| `historico_mudancas.csv` | Mudanças detectadas entre atualizações (base dos feeds Atom em `feeds/`) | `data` + `titulo` |
| `datapackage.json` | Descritor Frictionless Data Package: esquema de campos, contagens, licença, versão | — |

Convenções: UTF-8, separador vírgula, aspas duplas quando necessário, datas em
`DD/MM/AAAA`, decimais com ponto (para máquinas; o site mostra vírgula), campos
vazios quando "não localizado até o corte" — nunca "não existe".

## Como citar

`CITATION.cff` na raiz do repositório alimenta o botão "Cite this repository"
do GitHub. Enquanto não houver DOI:

> Futura Evidence Lab (2026). *Monitor El Niño Brasil — índice MARÉ (Medida de
> Antecipação e Resposta ao El Niño), dados verificados*, versão 2.2.3, corte de
> DD/MM/AAAA. https://monitorelnino.com.br

## Como emitir o DOI (passo humano, uma vez por edição)

1. Entrar em <https://zenodo.org> com a conta institucional e, em *GitHub*,
   ligar o repositório do Monitor.
2. No GitHub, criar um **release** com a tag da edição (ex.: `v2.2.3`). O
   Zenodo arquiva o release automaticamente e emite um DOI de versão e um
   *concept DOI* (estável entre edições).
3. Copiar o DOI para `CITATION.cff` (bloco `identifiers`, hoje comentado) e
   para `datapackage.json` (`"id"`), e para esta página. Rodar
   `verificar_consistencia.py`.
4. A partir daí, cada release novo (cada corte publicado) ganha DOI próprio.

## Licença dos dados — decisão pendente

O repositório está sob MIT (código). Para **dados**, a prática consolidada é
CC BY 4.0 (uso livre com atribuição) ou CC0. Recomendação: CC BY 4.0, que — **adotada em 02/09/2026 (decisão editorial): dados sob CC BY 4.0; código sob MIT.**
preserva a atribuição ao Futura Evidence Lab. É decisão editorial: até ela ser
tomada, `datapackage.json` declara MIT, a licença vigente do repositório.

## Garantias

`verificar_consistencia.py` confere, a cada publicação, que cada CSV tem
exatamente as linhas do JSON de origem e que `CITATION.cff` mantém o bloco de
DOI (placeholder ou valor). Os arquivos são determinísticos: mesma entrada,
mesmos bytes.
