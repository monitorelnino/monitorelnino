#!/usr/bin/env python3
"""Gera o PDF de documentação e auditoria do índice MARÉ.

Todos os números do PDF são COMPUTADOS no momento da geração, a partir de
data/ e da bateria analise_sensibilidade.py — o documento não contém valor
digitado à mão e portanto não pode divergir da base publicada. Regenerar
após qualquer mudança de dados é um comando:

  python3 gerar_pdf_indice.py          # grava MARE_Indice_Documentacao.pdf

Requer: reportlab (pip install reportlab), numpy.

DETERMINISMO (R1 da segunda auditoria, 29/08/2026): o reportlab embute
metadados de data/ID no PDF a cada build a partir do relógio da máquina, o
que fazia dois PDFs de conteúdo idêntico terem hashes diferentes — quebrando
a selagem para qualquer auditor que regenerasse o arquivo. Corrigido fixando
SOURCE_DATE_EPOCH (variável padrão de builds reproduzíveis, lida nativamente
pelo reportlab ≥4) a partir da PRÓPRIA data de corte dos dados
(data/meta.json), não do relógio da execução: o PDF passa a ser função
determinística dos dados publicados, não do instante em que foi gerado.
Verificado nesta correção: dois builds consecutivos produzem hash SHA-256
idêntico; sem a variável, ou com dado alterado, o hash diverge (controle
negativo e positivo documentados no CHANGELOG).
"""
import datetime, json, os, pathlib

_META = json.load(open(pathlib.Path(__file__).parent / "data" / "meta.json", encoding="utf-8"))
os.environ.setdefault(
    "SOURCE_DATE_EPOCH",
    str(int(datetime.datetime.strptime(_META["corte"], "%d/%m/%Y")
                              .replace(tzinfo=datetime.timezone.utc).timestamp()))
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)

import analise_sensibilidade as an

RAIZ = pathlib.Path(__file__).parent
TERRA = colors.HexColor("#A65F3F")
AZUL = colors.HexColor("#35566B")
TINTA = colors.HexColor("#1A0E08")
OSSO = colors.HexColor("#F5EFE6")
CINZA = colors.HexColor("#6B6257")

S_TIT = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=TINTA, spaceAfter=2)
S_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=10.5, leading=14, textColor=CINZA, spaceAfter=14)
S_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=TERRA, spaceBefore=14, spaceAfter=5)
S_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=AZUL, spaceBefore=9, spaceAfter=3)
S_P = ParagraphStyle("p", fontName="Helvetica", fontSize=9.3, leading=12.6, textColor=TINTA, spaceAfter=5, alignment=4)
S_NOTA = ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=8.3, leading=11, textColor=CINZA, spaceAfter=5)
S_CEL = ParagraphStyle("c", fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=TINTA)
S_CELB = ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=8.3, leading=10.5, textColor=colors.white)

def tabela(cab, linhas, larguras=None, destaque_azul=False):
    """Desenha uma tabela formatada (cabeçalho, linhas, bordas) na página corrente do PDF do índice."""
    dados = [[Paragraph(f"<b>{c}</b>", S_CELB) for c in cab]] + \
            [[x if isinstance(x, Paragraph) else Paragraph(str(x), S_CEL) for x in ln] for ln in linhas]
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL if destaque_azul else TERRA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, OSSO]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8CFC2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t

def rodape(canvas, doc):
    """Escreve o rodapé padrão (numeração de página, carimbo de corte dos dados) em cada página do PDF."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(18 * mm, 12 * mm, "Monitor El Niño Brasil · Futura Evidence Lab — MARÉ v2.3: documentação e auditoria do índice")
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"página {doc.page}")
    canvas.setStrokeColor(TERRA); canvas.setLineWidth(0.6)
    canvas.line(18 * mm, 16 * mm, A4[0] - 18 * mm, 16 * mm)
    canvas.restoreState()


def construir():
    """Monta o PDF do índice do zero: capa, metodologia resumida, ranking, mapas e apêndices, computando os números ao vivo a partir de data/ e da bateria de sensibilidade."""
    R = an.rodar()
    idx, ufs = R["idx"], R["ufs"]
    meta = json.load(open(RAIZ / "data" / "meta.json", encoding="utf-8"))
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    nomes = ["Instrumento estadual", "Cobertura populacional", "Antecipação"]

    E = []
    E.append(Paragraph("MARÉ v2.3 — Documentação do Índice", S_TIT))
    E.append(Paragraph("Medida de Antecipação e Resposta ao El Niño · Monitor El Niño Brasil (monitorelnino.com.br) · Futura Evidence Lab", S_SUB))
    E.append(Paragraph(
        f"Documento gerado programaticamente em {hoje} a partir dos dados publicados (corte {meta['corte']}); "
        f"todos os valores são computados na geração — nenhum foi digitado à mão. Média nacional vigente: "
        f"<b>{R['media']:.1f}/100</b>. Documentos irmãos: METODOLOGIA.md (fundamentos e errata), "
        "DOCUMENTACAO_TECNICA.md (arquitetura e reprodução), Livro-Razão de Verificação (rastreabilidade dos julgamentos). "
        "Em divergência, o código (recalcular_mare.py) é a referência de implementação e o METODOLOGIA.md a referência normativa.", S_P))
    # v2.2.4 — nota do defeso (permanente, E13) e contador público da verificação
    E.append(Paragraph(
        "<b>Período eleitoral (04/07–25/10/2026):</b> a Lei 9.504/1997 (art. 73, VI) suspende transferências "
        "voluntárias e parte da comunicação oficial na janela crítica de preparação; nenhuma regra que altere "
        "notas muda nesse período, e baterias negativas do intervalo são provisórias até repetição posterior "
        "(METODOLOGIA §24). Esta nota permanece após o período, como memória do registro.", S_P))
    try:
        _vr = json.load(open(RAIZ / "data" / "verificacao_resumo.json", encoding="utf-8"))
        _t = _vr.get("totais_por_nivel", {})
        _fila = _vr.get("fila_citacao_incompleta")
        E.append(Paragraph(
            f"<b>Contador público da verificação:</b> {_t.get('nacional',0)} municípios verificados em fontes "
            f"nacionais · {_t.get('estadual',0)} também em estaduais · {_t.get('municipal_completo',0)} com verificação "
            f"completa · {_t.get('nao_verificado',0)} ainda não verificados (de {_vr.get('total_municipios',0)}). "
            f"Fontes suspensas por defeso na última rodada: {_vr.get('fontes_suspensas_defeso_ultima_rodada',0)}. "
            + (f"Fila pública de citação incompleta: {_fila} registro(s), prazo 25/10/2026." if _fila is not None else ""), S_P))
    except FileNotFoundError:
        pass

    E.append(Paragraph("1. O que o índice mede — e o que não mede", S_H1))
    E.append(Paragraph(
        "O MARÉ mede <b>preparação demonstrável publicamente</b> para o ciclo El Niño 2026/2027, por unidade federativa: "
        "a existência, a atualidade e a tempestividade de instrumentos formais de contingência localizáveis em fonte "
        "pública oficial. Não mede a qualidade interna dos planos, a execução ou a preparação real não publicada; "
        "ausência de registro não é registro de ausência (\u201cnao_localizado\u201d = verificado e não encontrado, com data). "
        "Por decisão estrutural (Correção B, 26/08/2026), <b>atos de resposta — decretos de SE/ECP e reconhecimentos "
        "federais — não pontuam em componente algum</b>: a IN MDR nº 2/2016 exige dano já ocorrido para o decreto "
        "existir, e a literatura demonstra a endogeneidade política dos reconhecimentos (Silva & Batista, 2020). "
        "Um índice de preparação que subisse com a chegada do desastre criaria o incentivo exatamente errado. "
        "Delimitação de objeto (METODOLOGIA §5.0): o MARÉ mede o <b>arcabouço público da preparação</b> — condição "
        "necessária, não suficiente, de capacidade instalada — mais a tempestividade com que ele foi erguido; e seu "
        "valor probatório é assimétrico: <b>nota baixa é evidência mais forte de despreparo do que nota alta é de "
        "preparo</b>, porque o documento é a parte mais barata da preparação.", S_P))

    E.append(Paragraph("2. Os três componentes (pesos nominais iguais, 1/3 cada) — v2.2", S_H1))
    E.append(tabela(
        ["Componente", "O que pontua", "Escala"],
        [["Instrumento estadual", "Status do instrumento de contingência do estado, por verificação documental externa",
          "NOVO 100 · READ 65 · VIG 45 · ELAB 35 · LAC 0"],
         ["Cobertura populacional", "Fração da POPULAÇÃO da UF (Censo 2022) residente em municípios com instrumento ex-ante, com crédito por categoria (§3). Funde os antigos componentes capital e cobertura municipal: a capital vale sua fração demográfica real, como qualquer município — sua proeminência permanece editorial (card de detalhe), não aritmética (§12.4.2 da Metodologia)",
          "crédito: plano 1,0 · plano_antigo 0,6 · plano_elaboracao 0,45 · coberto_estadual 0,3 · nao_localizado 0 · decreto 0 (Correção B) · nao_el_nino 0 (desvio declarado do §12.4.2: o vocabulário obrigatório veda crédito a ato alheio ao ciclo; a herança do 0,1 da escala da capital dava 2,6 pontos ao AP por emergência sanitária — achado na simulação de 27/08/2026)"],
         ["Antecipação", "Tempestividade do instrumento estadual ante o Boletim nº 1 do Painel El Niño (29/06/2026)",
          "régua: 100 (antes) · 60 (≈30 dias) · 40 (estrutura recorrente ativada) · 30 · 20 · 10 · 0. Só instrumento ex-ante cronometra; decreto de emergência nunca (teste do objeto e definição de atraso: METODOLOGIA §5.2.1; escala de dano considerada e descartada, mesmo local)"]],
        larguras=[34 * mm, 78 * mm, 62 * mm]))
    E.append(Paragraph(
        f"Valores de antecipação em uso na edição: {R['antecip_valores']} — todos pertencentes à régua declarada (verificado).", S_NOTA))

    E.append(Paragraph("3. Fórmula da cobertura populacional (três camadas, ponderadas pelo Censo 2022)", S_H1))
    E.append(Paragraph(
        "<b>Camada nominal:</b> w += população_do_município × crédito_da_categoria, para cada registro individual do "
        "banco (junção pela grafia oficial IBGE; o motor FALHA se um registro não casar com a malha). Decreto tem "
        "crédito 0 por regra estrutural (Correção B): a exclusão vive na tabela CRED_POP, não em purga de dados. "
        "<b>Camada de agregados oficiais tipados:</b> número verificado sem lista nominal entra pelo excedente sobre "
        "os já nomeados × <b>população municipal mediana da UF</b> × crédito — hoje apenas RO (38 planos ao MP-RO); "
        "a mediana é o estimador declarado para população não atribuível nominalmente. "
        "<b>Camada declarada (desconto de 50% sobre o crédito):</b> mesmo estimador de mediana — "
        "max(declarado_plano − documentados, 0) × mediana × 0,5 + declarado_antigo × mediana × 0,3 — com fontes "
        "restritas a órgãos de controle e sistemas estaduais (TCE-RS 2025, Painel Farol TCE-SC, SISDC/CEPDEC-PR). "
        "<b>cobertura_pop = min(100, 100 × w / população_da_UF)</b>, com populações do Censo 2022 validadas por "
        "atualizar_populacao.py (5.570 municípios exatos; total nacional exato da apuração identificada; cinco "
        f"municípios-sentinela conferidos valor a valor). Malha de referência: {R['malha']['linhas']} linhas — os "
        "5.570 municípios do Censo (Fernando de Noronha/PE incluído, escolha declarada; efeito máximo "
        f"1/{R['malha']['pe_total']} em PE) + Boa Esperança do Norte/MT, instalado em 2025, pós-Censo: peso "
        "populacional 0 sob esta safra censitária, com seus habitantes contidos nos municípios de origem.", S_P))

    E.append(Paragraph("4. Agregação e incerteza", S_H1))
    E.append(Paragraph(
        "<b>Manchete (linear):</b> total = média aritmética dos três componentes. <b>Tooltip (geométrica):</b> "
        "total_geo = exp(média dos logaritmos), com piso 5 — o piso resolve o problema clássico do zero na média "
        "geométrica (precedente: transição do IDH em 2010) e penaliza perfis desequilibrados. "
        "<b>Incerteza:</b> 10.000 vetores de pesos sorteados de Dirichlet(1,1,1) com semente fixa 42. Desde a "
        "v2.2.3 (decisão de 29/08/2026, METODOLOGIA §13), o índice <b>não publica posição ordinal entre "
        "estados</b>: o produto público por UF é a nota, a faixa interpretativa e a confiança da verificação. "
        "O Monte Carlo permanece integralmente computado, selado (data/robustez_mc.json) e publicado como "
        "evidência de robustez na §5.8 — sempre com o intervalo p5–p95 junto do rank mediano, nunca o ordinal "
        "isolado. Fundamento: 12 pares de UFs distam menos de 2 pontos e a amplitude mediana do intervalo é de "
        "7 posições — a resolução do instrumento sustenta a leitura por faixa, não a comparação ordinal fina "
        "(precedente doméstico: o ICM da SEDEC/MIDR publica faixas A–D, não ranking). Faixas interpretativas "
        "(cortes normativos declarados): "
        "Faixas (estágio do arcabouço público): 0–25 estágio inicial · 25–50 em construção · 50–70 consolidado · 70–100 avançado (o índice sobe a cada plano preventivo publicado; cortes intocados; a leitura probatória segue regida pelo §5.0 da Metodologia).", S_P))

    E.append(PageBreak())
    E.append(Paragraph("5. Auditoria de robustez (executada em 27/08/2026; reproduzível por analise_sensibilidade.py)", S_H1))
    E.append(Paragraph(
        "Seguindo o Handbook OCDE/JRC e a revisão de literatura v2.1→v2.2, cada escolha normativa foi submetida a "
        "análise de sensibilidade sobre os dados reais da edição. Métrica: deslocamento de posições no ranking das 27 "
        "UFs (mediana e máximo) em relação à configuração publicada.", S_P))

    E.append(Paragraph("5.1 Forma de agregação e piso da geométrica", S_H2))
    ag = R["agregacao"]
    linhas_piso = [[f"piso = {p:g}", v["mediana"], v["max"], ", ".join(f"{u} ({s})" for s, u in v["piores"] if s)]
                   for p, v in R["piso"].items()]
    E.append(tabela(["Variação", "Troca mediana", "Troca máxima", "Mais deslocados"],
                    [["linear → geométrica (piso 5)", ag["mediana"], ag["max"],
                      ", ".join(f"{u} ({s})" for s, u in ag["piores"] if s) + f" · Spearman {ag['spearman']}"]] + linhas_piso,
                    larguras=[44 * mm, 26 * mm, 26 * mm, 78 * mm]))
    E.append(Paragraph("Leitura: as duas agregações permanecem altamente concordantes (Spearman 0,92), mas com três "
                       "componentes a geométrica pune com mais força os perfis com zeros — os maiores deslocamentos "
                       "concentram-se em UFs de perfil desequilibrado, exatamente as de intervalo p5–p95 largo. A "
                       "linear segue como manchete declarada; o valor do piso tem efeito mediano nulo.", S_NOTA))

    E.append(Paragraph("5.2 Descontos da camada declarada", S_H2))
    E.append(tabela(["Variação do desconto", "Troca mediana", "Troca máxima"],
                    [[n, v["mediana"], v["max"]] for n, v in R["descontos"].items()],
                    larguras=[70 * mm, 52 * mm, 52 * mm]))
    E.append(Paragraph("Leitura: a calibração \u201cdeclaração vale metade\u201d (0,5) e o 0,3 do declarado-desatualizado são as "
                       "escolhas mais questionáveis em tese — e, sob ponderação populacional, tornaram-se quase "
                       "inertes no ranking: variações de até ±40% movem no máximo 1 posição (na v2.1, por contagem, "
                       "já eram ≤1; o estimador de mediana dilui ainda mais a alavanca).", S_NOTA))

    E.append(Paragraph("5.3 Esquemas de ponderação alternativos", S_H2))
    kn = R["knockouts"]
    E.append(tabela(["Esquema", "Troca mediana", "Troca máxima", "Mais deslocados"],
                    [[Paragraph(f"PCA (1º comp.: {', '.join(f'{n} {p:.2f}' for n, p in zip(['est','cob','ant'], R['pca']['pesos']))}; "
                                f"var. explicada {R['pca']['var_explicada']:.0%}) · Spearman {R['pca']['spearman']}", S_CEL),
                      R["pca"]["mediana"], R["pca"]["max"],
                      ", ".join(f"{u} ({s})" for s, u in R["pca"]["piores"] if s)]] +
                    [[f"knockout sem {n}", v["mediana"], v["max"],
                      ", ".join(f"{u} ({s})" for s, u in v["piores"] if s)] for n, v in kn.items()],
                    larguras=[76 * mm, 24 * mm, 24 * mm, 50 * mm]))
    E.append(Paragraph("Leitura: o 1º componente principal explica 55% da variância e é dominado pelo par instrumento "
                       "estadual + antecipação, atribuindo peso quase nulo à cobertura populacional — ponderar "
                       "estatisticamente significaria apagar a única dimensão local do índice. É o argumento decisivo "
                       "contra a ponderação por PCA (crítica de Greco et al.) e pela manutenção dos pesos iguais como "
                       "escolha normativa declarada; a assimetria de influência resultante é quantificada na §5.4.", S_NOTA))

    E.append(Paragraph("5.4 Pesos nominais × influência efetiva", S_H2))
    E.append(tabela(["Componente", "Peso nominal", "Contribuição efetiva à variância do total", "Média", "Desvio-padrão"],
                    [[nomes[j], "33,3%", f"{100 * R['contrib_var'][j]:.0f}%",
                      R["stats_comp"][j][0], R["stats_comp"][j][1]] for j in range(3)],
                    larguras=[46 * mm, 26 * mm, 56 * mm, 22 * mm, 24 * mm], destaque_azul=True))
    E.append(Paragraph("Leitura: pesos iguais nominais não implicam influência igual — o instrumento estadual contribui "
                       "com 44% da variância do total e a antecipação com 38%; a cobertura populacional, de menor "
                       "dispersão, com 18%. Somada à correlação da §5.5, a consequência é declarada sem eufemismo na "
                       "§7: cerca de dois terços do índice respondem, direta ou indiretamente, ao instrumento "
                       "estadual. A ponderação igual permanece como escolha normativa declarada (Beccari 2016), com a "
                       "assimetria publicada em vez de omitida.", S_NOTA))

    E.append(Paragraph("5.5 Correlações entre componentes", S_H2))
    C = R["correl"]
    E.append(tabela([""] + [n.split()[0] for n in nomes],
                    [[nomes[i].split()[0]] + [f"{C[i][j]:+.2f}" for j in range(3)] for i in range(3)],
                    larguras=[44 * mm, 42 * mm, 42 * mm, 42 * mm]))
    E.append(Paragraph("Leitura: a exceção declarada permanece — instrumento estadual × antecipação (+0,66), ambos "
                       "derivando parcialmente do mesmo fato (existência e data do instrumento estadual). Com a fusão "
                       "da v2.2, esse par passou a somar 2/3 do peso nominal: a limitação foi AGRAVADA pela "
                       "reestruturação, é reconhecida como tal na §7, e seu tratamento (fator de alinhamento, com "
                       "confiabilidade inter-avaliadores medida) é o candidato central da v2.3.", S_NOTA))

    E.append(PageBreak())
    E.append(Paragraph("5.6 Transparência de camadas: de onde vem a cobertura populacional de cada UF", S_H2))
    linhas_cam = []
    for u in ufs:
        if u in R["camadas"]:
            d, a, de = R["camadas"][u]
            linhas_cam.append([u, f"{idx[u]['cobertura_pop']:.1f}", f"{d}%", f"{a}%", f"{de}%"])
    E.append(tabela(["UF", "Cobertura", "Nominal", "Agregado oficial (mediana)", "Declarada (mediana, c/ desconto)"], linhas_cam,
                    larguras=[18 * mm, 26 * mm, 42 * mm, 42 * mm, 46 * mm]))
    E.append(Paragraph("Leitura: a ponderação populacional REDUZIU drasticamente a dependência de dado declarado — na "
                       "v2.1 (por contagem), o componente local de PR era 100% declarado, RS 99% e SC 95%; na v2.2, "
                       "45%, 35% e 31%, porque os municípios nomeados individualmente concentram população muito acima "
                       "da mediana usada no estimador da camada declarada. RO permanece o caso de maior dependência de "
                       "agregado (49%). O desconto de 50% precifica a diferença de lastro; esta tabela a torna "
                       "auditável UF a UF.", S_NOTA))

    E.append(Paragraph("5.7 Verificações de borda e do Monte Carlo", S_H2))
    sob = R["sobreposicao"].get("RS", {})
    E.append(tabela(["Verificação", "Resultado"],
                    [["Teto min(100, ·) da cobertura populacional", "Dormante: nenhuma UF o atinge na base atual" if not R["teto_ativo"] else f"ATIVO em {R['teto_ativo']}"],
                     ["Sobreposição declarado-desatualizado × plano_antigo documentado",
                      f"RS: {sob.get('declarado_antigo', 0)} declarados-antigos × {sob.get('plano_antigo_doc', 0)} documentados individualmente → teto do risco de dupla contagem: {sob.get('teto_pp', 0):.2f} p.p. da cobertura"],
                     ["Estabilidade do Monte Carlo entre sementes (3 reexecuções)", f"variação máxima de p5/p95: ±{R['mc_sementes']} posição"],
                     ["Convergência: 10.000 × 100.000 iterações (semente 42)", f"deslocamento máximo de p5/p95: {R['mc_convergencia']} posição — 10k é suficiente"],
                     ["Determinismo", "semente fixa 42: reprodução bit a bit por qualquer auditor"],
                     ["Teste de estresse §12.1 (27 decretos simultâneos)", "Δ = 0 em todas as casas decimais, todos os campos, todas as UFs (reimplementado de forma independente na auditoria)"]],
                    larguras=[88 * mm, 86 * mm]))

    E.append(Paragraph("5.8 Anexo de robustez: posições sob perturbação de pesos (não é produto público)", S_H2))
    rob = json.load(open(RAIZ / "data" / "robustez_mc.json", encoding="utf-8"))
    linhas_rob = [[u, f"{idx[u]['total']:.1f}".replace(".", ","), str(rob[u]["rank_mediano"]),
                   f"{rob[u]['rank_p5']}–{rob[u]['rank_p95']}", str(rob[u]["amplitude"])]
                  for u in ufs if u in rob]
    E.append(tabela(["UF", "Nota", "Rank mediano", "Intervalo p5–p95", "Amplitude"], linhas_rob,
                    larguras=[20 * mm, 26 * mm, 34 * mm, 48 * mm, 30 * mm]))
    E.append(Paragraph("Leitura: este anexo é a evidência que fundamenta a decisão da v2.2.3 de não publicar "
                       "posição ordinal por UF (METODOLOGIA §13). A nota de cada UF é determinística e estável; "
                       "a posição relativa no pelotão intermediário não é — a amplitude correlaciona r = 0,74 com "
                       "a dispersão interna dos componentes (auditoria de 29/08/2026), e os extremos são os únicos "
                       "protegidos. O intervalo p5–p95 acompanha o rank mediano em toda superfície onde ele "
                       "aparecer (recomendação acatada da mesma auditoria); nenhuma superfície pública exibe o "
                       "ordinal isolado.", S_NOTA))

    E.append(Paragraph("6. Escolhas normativas declaradas (síntese)", S_H1))
    E.append(Paragraph(
        "São escolhas de desenho, não derivações estatísticas — declaradas aqui e testadas na §5: (i) pesos iguais de "
        "1/3; (ii) as escalas ordinais dos componentes estadual e de antecipação, e a escala de crédito populacional "
        "por categoria (generalização declarada da antiga escala da capital); (iii) o desconto de 50% da camada "
        "declarada (0,5 e 0,3); (iv) o piso 5 da geométrica; (v) os cortes das faixas interpretativas; (vi) a "
        "composição da malha (Fernando de Noronha incluído; Boa Esperança do Norte/MT com peso populacional 0 sob a "
        "safra do Censo 2022); (vii) a exclusão integral de atos de resposta (Correção B) — a única com fundamento "
        "legal-empírico direto; (viii) o estimador de população municipal MEDIANA da UF para agregados e declarações "
        "sem lista nominal; (ix) o crédito 0 para nao_el_nino — desvio documentado da letra do §12.4.2, imposto pelo "
        "vocabulário obrigatório e demonstrado na simulação (caso AP).", S_P))

    E.append(Paragraph("7. Limitações reconhecidas", S_H1))
    E.append(Paragraph(
        "(1) O índice mede o <b>arcabouço público</b> da preparação, não capacidade instalada — com valor probatório "
        "assimétrico, declarado na METODOLOGIA §5.0: mais confiável no fundo do ranking do que no topo. (2) Concentração no instrumento estadual: com a fusão da v2.2, instrumento estadual + "
        "antecipação somam 2/3 do peso nominal e, com a correlação +0,66 (§5.5) e 82% da variância combinada (§5.4), "
        "cerca de dois terços do índice respondem ao instrumento estadual — limitação AGRAVADA pela reestruturação, "
        "declarada aqui; o fator de alinhamento com confiabilidade inter-avaliadores medida é o candidato da v2.3. "
        "(3) Safra censitária fixa: as populações são as do Censo 2022 durante todo o ciclo (Boa Esperança do Norte/MT "
        "com peso 0; dinâmicas migratórias pós-Censo não capturadas). (4) A camada declarada repousa em levantamentos "
        "de terceiros E num estimador (mediana populacional da UF) — o desconto de 50% precifica o lastro, a mediana "
        "declara a incerteza de atribuição, e a decomposição da §5.6 expõe ambos UF a UF. "
        "(5) Escalas ordinais tratadas em agregação cardinal — limitação herdada do estado da arte (Sendai Meta E, "
        "IGR/BID-IDEA), mitigada por avaliação documental externa em vez de auto-relato e pelos intervalos p5–p95. "
        "(6) Julgamento de avaliador único nesta edição; confiabilidade inter-avaliadores é meta declarada da v2.3.", S_P))

    E.append(Paragraph("8. Reprodução", S_H1))
    E.append(Paragraph(
        "Na raiz do pacote publicado: <b>python3 recalcular_mare.py --check</b> reproduz os 27×10 campos publicados "
        f"(saída esperada: média nacional {R['media']:.1f}); <b>python3 analise_sensibilidade.py</b> reexecuta "
        "integralmente a bateria da §5; <b>python3 gerar_pdf_indice.py</b> regenera este documento a partir dos dados "
        "vigentes. Roteiro completo de auditoria independente: DOCUMENTACAO_TECNICA.md §10. Recomenda-se que auditores "
        "reimplementem o teste de estresse com código próprio — a reprodução independente é parte do valor probatório.", S_P))

    doc = SimpleDocTemplate(str(RAIZ / "MARE_Indice_Documentacao.pdf"), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=22 * mm,
                            title="MARÉ v2.3 — Documentação do Índice",
                            author="Futura Evidence Lab · Monitor El Niño Brasil")
    doc.build(E, onFirstPage=rodape, onLaterPages=rodape)
    print(f"MARE_Indice_Documentacao.pdf gerado · média nacional {R['media']:.1f} · corte {meta['corte']}")


if __name__ == "__main__":
    construir()
