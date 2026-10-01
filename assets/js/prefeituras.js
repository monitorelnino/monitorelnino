/* ===== prefeituras.html · "Para gestores" ================================================
 *
 * 01/10/2026 (decisão da editoria): a página passa a ser convite, não cobrança, e perde duas
 * coisas — com elas, o código que as alimentava:
 *
 *   - A seção "O que ainda é possível no período eleitoral", que lia `nao_suspenso` de
 *     `data/calendario/dispositivos.json`. A lista estava vazia e apontava para um calendário que
 *     já havia sido apagado do site; a editoria tirou a seção e toda menção ao período eleitoral.
 *   - O seletor de município e o cartão da cidade, que liam `data/municipios_card.json`. A mesma
 *     consulta existe na página inicial, e duas buscas para a mesma pergunta divergem na primeira
 *     correção — a desta página era a segunda. O ponteiro para a inicial ficou no lugar dela.
 *
 * O que sobra é o VLibras, e sobra de propósito: tudo o mais nesta página é texto e ponteiro, que
 * não precisam de script. Deixar os dois blocos aqui, escrevendo em `id`s que a página não tem
 * mais, seria código morto apontando para o vazio — e o portão de estrutura reprova justamente
 * isso, com razão: ele não consegue distinguir "removido de propósito" de "quebrado".
 */
window.addEventListener('load', function(){
  if (window.VLibras && window.VLibras.Widget){
    try { new window.VLibras.Widget('https://vlibras.gov.br/app'); } catch (e) {}
  }
});
