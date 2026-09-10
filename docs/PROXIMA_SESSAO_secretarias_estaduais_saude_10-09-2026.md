# Monitor El Niño Brasil — transferência para a próxima sessão
**Tema: dados de desfechos em saúde publicados pelas secretarias estaduais (§36)**
**Escrito em:** 10/09/2026, ao fim da sessão que abriu a frente das SES
**Para:** a próxima sessão de atualização do site (Claude, ou quem continuar)

---

## 0. Antes de tudo: como rodar

```
git clone https://github.com/monitorelnino/monitorelnino.git
cd monitorelnino
pip install -r requirements.txt --break-system-packages
npm ci
bash scripts/verificar_derivados.sh          # cadeia canônica; NÃO fixe SOURCE_DATE_EPOCH à mão — ver §5
```

Antes de abrir um PR, rode a suíte inteira listada em `.github/workflows/portoes.yml` (25 portões). Peça
autorização explícita da editoria para qualquer mudança visível no site (o histórico desta sessão é todo de
PRs pedidos por ela, um a um — não decida sozinho).

---

## 1. O que esta sessão resolveu

A pergunta original: *"as secretarias de vigilância em saúde dos estados têm dados sobre os desfechos
cobertos pelo decreto do MS — vamos usar isso para construir um monitor epidemiológico."* A resposta é
**sim**, e a sessão fez três coisas:

1. **Achou o instrumento federal que faltava** — o Plano de Contingência para Emergências em Saúde Pública
   por Seca e Estiagem (MS/SVSA, 2026, lido na íntegra) e a Portaria GM/MS nº 6.918/2025 (Sala Nacional de
   Emergências Climáticas em Saúde) — e derivou dele um **catálogo de 20 desfechos** e **17 gatilhos**
   numéricos por estágio operacional.
2. **Varreu os 27 estados** atrás do instrumento equivalente (Sala/Comitê/decreto) e da fonte de dado
   (boletim/painel).
3. **Escreveu o primeiro coletor de verdade** — não catalogação, coleta — para o boletim semanal da SES-MS,
   validado contra o texto real do PDF (não só uma fixture inventada).

## 2. Onde as coisas estão guardadas

```
data/saude_desfechos/
  instrumentos.json      federais + 27 UFs (Sala/Comitê/decreto) + planos_adaptasus
  catalogo.json          os 20 desfechos do Quadro 2, com status de coleta
  gatilhos.json          os 17 gatilhos do Quadro 5, com o que o Monitor já computa
  fontes_uf.json         onde cada SES publica boletim/painel/CIEVS
  ses_ms_dengue.json     série própria, construída pelo coletor de MS (cresce a cada rodada)
coletar_boletim_ms_dengue.py    o coletor — leia-o como referência antes de escrever o próximo
verificar_saude.py               portões (n) a (q) cobrem toda essa estrutura
METODOLOGIA.md §36               a narrativa completa, com todas as fontes citadas
```

## 3. O placar exato, estado a estado

| Camada | Contagem | Quais |
|---|---|---|
| Instrumento de governança localizado (Sala/Comitê/decreto) | 3 de 27 | **MT** (SES lidera), **RJ** (Defesa Civil lidera, câmara de Saúde), **SC** (Defesa Civil lidera, gatilho de saúde) |
| Fonte de dado ativa identificada (boletim/painel) | 8 de 27 | **SP, MG**(¹), **CE, BA, DF, PB, PE, MS** |
| **Coletor de máquina escrito e testado** | **1 de 27** | **MS** — `coletar_boletim_ms_dengue.py` |
| Plano estadual de adaptação (AdaptaSUS — trilha distinta, não confundir) | 27 de 27 (por declaração ministerial, não confirmado estado a estado) | concluído: BA, PA, PI · em elaboração: MG, MA, RJ, MS · fase inicial: os outros 20 |

(¹) MG tem painel, mas está em **defeso** (Power BI fora do ar por decisão da SES, verificação humana de
07/09) — não dá para avançar aí até 26/10/2026.

Catálogo de desfechos (20 no total): **3 coletados** (dengue via InfoDengue + MS; SRAG e síndrome gripal via
InfoGripe), **16 candidatos** (fonte aberta identificada, coletor ainda não escrito), **1 sem fonte aberta
identificada** (doenças de pele e olhos).

## 4. Recomendação de ordem para a próxima sessão

Por retorno/esforço, nesta ordem:

1. **DF** — o mais fácil depois de MS. Série mensal numerada, URL estável
   (`saude.df.gov.br/informes-dengue-chikungunya-zika-febre-amarela`), e por ser um município-estado não
   tem a complexidade da tabela por município que MS tem.
2. **PE** — portal CIEVS dedicado (`portalcievs.saude.pe.gov.br`), parece estruturado por semana
   epidemiológica de um jeito parecido com MS. **Confira o PDF de verdade antes de codar** (ver §5).
3. **BA e CE** — repositórios centrais de boletins, não um único boletim de dengue; cobrem mais do que
   arbovirose (BA já tem página própria de DTHA, que está no catálogo). Mais trabalho de triagem por
   agravo, mas mais desfechos por fonte.
4. **PB** — boletins numerados sequenciais (`no_01_2026.pdf`, `no_02_2026.pdf`...), parece simples, mas o
   texto real ainda não foi lido — não pule a verificação.
5. **MG** — não mexer até o painel sair do defeso (26/10/2026 ou depois).
6. **Os outros 19 estados** — instrumento e fonte de dado ainda não localizados. Seguir o mesmo roteiro do
   §7 abaixo, região por região.

## 5. AVISO — o erro que consumiu a maior parte do fim desta sessão

**Nunca fixe `SOURCE_DATE_EPOCH` à mão com uma data hard-coded.** Nesta sessão, o `corte` em
`data/meta.json` avançou de 31/08/2026 para 10/09/2026 no meio do trabalho (a rotina automática do robô
mexe nesse campo). Eu continuei exportando manualmente a data velha em várias chamadas, enquanto
`bash scripts/verificar_derivados.sh` sempre lê o `corte` certo, fresco, do arquivo. Isso produziu dois
PDFs (`METODOLOGIA.pdf`, `MARE_Indice_Documentacao.pdf`) com conteúdo de data diferente do que o CI gerava
— e eu passei um tempo enorme investigando uma pista falsa (diferença de versão do zlib entre ambientes)
antes de perceber que era só isso.

**A regra:** sempre rode `bash scripts/verificar_derivados.sh` (sem nada exportado antes) para regenerar a
cadeia. Se precisar do valor da época por algum motivo, leia-o do jeito que o script lê:
```python
import json, datetime
corte = json.load(open('data/meta.json'))['corte']
dd, mm, aa = corte.split('/')
epoch = int(datetime.datetime(int(aa), int(mm), int(dd)).timestamp())
```
nunca escreva a data como literal num comando.

(Um efeito colateral que ficou, sem problema: `gerar_pdf_metodologia.py` e `gerar_pdf_indice.py` agora
rodam com `pageCompression=0` e `invariant=1` — os PDFs saem maiores, sem compressão, mas o build fica
mais robusto a diferenças de ambiente. Não foi a causa do bug, mas é bom mantê-lo.)

## 6. Como funciona o coletor de MS — leia antes de escrever o próximo

`coletar_boletim_ms_dengue.py` é a referência de estilo para qualquer coletor de boletim estadual novo.
Princípios que ele segue e que os próximos devem seguir:

- **Nunca adivinha uma URL de arquivo.** Localiza a página do post da semana por um permalink previsível
  (`.../boletim-epidemiologico-dengue-semana-{SE}-{ANO}/`, recuando até 3 semanas se ainda não publicado),
  e só então extrai o link do PDF de **dentro** do HTML daquela página, por regex.
- **Recusa publicar dado parcial.** Se a tabela municipal vier com menos de 70 dos 79 municípios de MS, o
  coletor registra lacuna e não grava nada — nunca um resultado incompleto disfarçado de completo.
- **Constrói a própria série.** A SES só publica o instantâneo da semana + o total do ano; o Monitor
  acumula a série semanal por conta própria, uma leitura por rodada, a partir do dia em que o coletor
  nasceu. É normal a série começar fina.
- **Testado contra o texto real do PDF antes de qualquer autoteste sintético valer alguma coisa.** Eu
  busquei o PDF de verdade (`web_fetch` com `web_fetch_pdf_extract_text=true`) e colei o texto real extraído
  num teste manual antes de escrever os autotestes formais. **Faça isso para cada estado novo** — cada SES
  formata diferente; não existe atalho de generalizar sem ler primeiro.
- Portão (q) em `verificar_saude.py` cobre: peso zero, nunca lido pelo motor, código IBGE válido (7
  dígitos), ressalva de não-atribuição presente. Copie esse padrão de portão para cada novo coletor
  estadual, com uma letra nova.

## 7. Roteiro de busca para os 19 estados sem nada localizado

O que funcionou nesta sessão, em ordem:
1. Busca geral (`"Sala de Situação" OR "Comitê" El Niño <estado> saúde decreto 2026`) — pouco retorno,
   mas às vezes acha o instrumento de governança.
2. Busca do boletim direto (`boletim epidemiológico arboviroses site:saude.<uf>.gov.br 2026` ou
   `dados.gov OR painel dengue <estado>`) — foi isso que achou CE, BA, DF, PB, PE, MS.
3. Se `data/saude_uf.json` já tem um domínio de SES verificado para o estado (18 dos 27 já têm, do
   trabalho do §35), comece a busca ali — é o atalho mais forte.
4. Sempre prefira o **boletim/painel primário da própria SES** a notícias secundárias sobre ele — a
   notícia dá a pista, mas o link do PDF/painel é o que interessa.

## 8. Faxina pendente, fora do escopo de saúde

Dois PRs antigos (07/09/2026) continuam abertos no GitHub e provavelmente já foram superados por trabalho
posterior direto no `main`:
- **#103** — "Rótulo do envio: 'Envie um plano ou decreto'" (o rótulo já está em produção, decidido e
  aplicado por outro caminho).
- **#96** — "METODOLOGIA §36 — publicação como objeto, ADPF 743 e padrão de conteúdo" (o §36 que existe
  hoje foi escrito depois, direto no `main`, por PRs diferentes).

Confirme que o conteúdo de ambos já está coberto antes de fechá-los — não feche sem checar primeiro.

## 9. O que NÃO fazer

- Não escrever um coletor "genérico para qualquer SES" — cada uma formata diferente; um parser genérico ou
  fica frágil ou vira um monte de casos especiais disfarçado. Um coletor por estado, cada um lido contra o
  PDF real primeiro.
- Não mexer no painel de MG antes de 26/10/2026 (defeso).
- Não misturar a trilha do AdaptaSUS (adaptação de médio prazo) com a Sala de Situação/Comitê do ciclo
  2026/2027 (governança operacional) — são coisas diferentes, documentadas em chaves separadas no JSON de
  propósito.
- Não fixar datas à mão em nenhum script (§5).
