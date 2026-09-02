#!/usr/bin/env python3
"""Processamento automático das contribuições do formulário — Monitor El Niño Brasil.

Lê os envios do Netlify Forms (formulário "contribuicao"), valida cada um por
regras objetivas e, quando TODAS passam, grava o registro no banco público na
mesma execução — sem intervenção manual. O que não passa é recusado com motivo
registrado em data/contribuicoes_recusadas.json (sem dados pessoais).

Regras de aprovação automática (todas obrigatórias):
  R1  Campos completos e válidos (UF real, tipo reconhecido, URL https).
  R2  Município existe na malha IBGE (casamento exato normalizado — sem
      adivinhação por similaridade: nome ambíguo é recusa, não palpite).
  R7  Reserva de julgamento humano (27/08/2026): tipo "plano" (move o índice)
      e QUALQUER contribuição sobre capital (o maior município da UF — a maior
      alavanca populacional individual do componente de cobertura, v2.2) nunca
      são auto-aplicados — ficam para a fila humana (verificar_contribuicoes →
      converter_contribuicao → aplicar_revisao), onde a categoria é decisão
      humana após leitura do documento. O caminho automático fica restrito,
      por construção, a decretos de não-capitais — neutros ao escore pela
      Correção B. Após aplicar, este script roda recalcular_mare.py --write
      para regravar percentual_uf.json derivado; o portão de consistência do
      job (média nacional idêntica no site) vira a prova mecânica de que o
      caminho automático segue neutro — regressão trava a publicação.
  R3  Tipo automatizável: "plano" ou "decreto". Envios "correção" e "outro
      ato" não são auto-aplicáveis com segurança e ficam registrados para
      tratamento editorial, com motivo explícito.
  R4  Fonte oficial: domínio *.gov.br, *.leg.br, *.jus.br, *.mp.br ou
      plataforma consorciada de Diário Oficial (diariomunicipal.*).
  R5  Documento acessível (HTTP 200, PDF ou HTML) e coerente: o texto deve
      conter o nome do município e vocabulário compatível com o tipo
      declarado (ex.: "contingência"/"PLANCON" para plano; "decreta"/
      "situação de emergência" para decreto).
  R6  Não-regressão: se já existe registro igual ou mais forte para o
      município, o envio é recusado como duplicata; se o envio é mais forte
      (ex.: plano onde havia só decreto), o registro é promovido.

Pós-condições de segurança: este script NÃO recalcula o índice nem publica
nada sozinho — ele apenas grava propostas aprovadas no banco; o recálculo e
os quatro portões de verificação rodam na sequência do mesmo job
(atualizar.py), e qualquer inconsistência bloqueia o commit inteiro.

Decreto aprovado aqui entra apenas como registro de transparência: pela
Correção B (Metodologia §12.4.1), não pontua em nenhum componente.

Variáveis de ambiente: NETLIFY_AUTH_TOKEN e NETLIFY_SITE_ID. Sem elas, o
script pula com aviso e código 0 (não bloqueia o job).
"""
import datetime, json, os, pathlib, re, sys, unicodedata, urllib.request

RAIZ = pathlib.Path(__file__).parent
ARQ_MUN = RAIZ / "data" / "municipios.json"
ARQ_PONTOS = RAIZ / "data" / "pontos_mapa.json"
ARQ_REF = RAIZ / "data" / "municipios_ibge_referencia.json"
ARQ_PROC = RAIZ / "data" / "contribuicoes_processadas.json"
ARQ_REC = RAIZ / "data" / "contribuicoes_recusadas.json"

UFS = set("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split())
FORCA = {"nao_localizado": 0, "nao_el_nino": 0, "coberto_estadual": 0,
         "plano_elaboracao": 1, "plano_antigo": 1, "decreto": 1, "plano": 2}
PALAVRAS = {
    "plano": ["contingencia", "plancon", "plano de acao", "plano preventivo"],
    "decreto": ["decreta", "situacao de emergencia", "estado de calamidade",
                "emergencia", "calamidade publica"],
}
DOMINIOS_OFICIAIS = (".gov.br", ".leg.br", ".jus.br", ".mp.br", ".def.br")
AUTOAPLICAR = False  # suspenso em 02/09/2026 (auditoria externa AUD-02/AUD-03)


def norm(s):
    """Normaliza nome de município para comparação robusta contra a base IBGE."""
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def api(caminho, token):
    """Requisição autenticada à API do Netlify (submissions), reaproveitando token e site id do ambiente."""
    req = urllib.request.Request(
        "https://api.netlify.com/api/v1" + caminho,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "MonitorElNino/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


import ipaddress, socket, urllib.parse
DIARIOS_MUNICIPAIS_OFICIAIS = ("diariomunicipal.com.br", "diariomunicipal.sc.gov.br", "diariomunicipal.org")  # allowlist exata (registrável)
TAM_MAX_NUMERO_DATA = 160
PADRAO_NUMERO_DATA = re.compile(r"^[\w\sÀ-ÿ.,;:/º°ª()\-–]+$")  # letras, dígitos, pontuação simples; sem < > \" ' & { } [ ]


def numero_data_valido(v: str) -> bool:
    """AUD-02: o campo livre do formulário só entra no banco se for curto e sem marcação."""
    v = (v or "").strip()
    return bool(v) and len(v) <= TAM_MAX_NUMERO_DATA and bool(PADRAO_NUMERO_DATA.match(v))


def host_oficial(url: str):
    """AUD-03: devolve (ok, host, motivo). Só https, sem userinfo, hostname canônico,
    sufixo oficial ou allowlist exata de diários municipais, e resolução DNS sem IP
    privado/loopback/link-local/reservado (IPv4 e IPv6)."""
    try:
        u = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return False, "", "URL malformada"
    if u.scheme != "https": return False, "", "esquema não é https"
    if u.username or u.password: return False, "", "URL com credenciais"
    host = (u.hostname or "").lower().rstrip(".")
    if not host or host != host.encode("idna").decode("ascii", "ignore") or " " in host: return False, host, "hostname inválido"
    permitido = host.endswith(DOMINIOS_OFICIAIS) or any(host == d or host.endswith("." + d) for d in DIARIOS_MUNICIPAIS_OFICIAIS)
    if not permitido: return False, host, f"domínio '{host}' fora das fontes oficiais aceitas (R4)"
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False, host, "DNS não resolve"
    for fam, _, _, _, sa in infos:
        ip = ipaddress.ip_address(sa[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False, host, f"resolve para endereço não público ({ip})"
    return True, host, ""


class _SemRedirect(urllib.request.HTTPRedirectHandler):
    """Cada salto de redirecionamento é revalidado por host_oficial (máximo 3)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        ok, _, motivo = host_oficial(newurl)
        if not ok: raise urllib.error.URLError(f"redirecionamento para destino não permitido: {motivo}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def baixar_documento(url):
    """Devolve (ok, texto_normalizado, content_type). Nunca levanta exceção."""
    try:
        ok, _, motivo = host_oficial(url)
        if not ok: return False, "", motivo
        opener = urllib.request.build_opener(_SemRedirect()); opener.addheaders = [("User-Agent", "MonitorElNino/1.0")]
        with opener.open(url, timeout=45) as r:
            if r.status != 200:
                return False, "", f"http {r.status}"
            ct = (r.headers.get("Content-Type") or "").lower()
            if not any(k in ct for k in ("pdf", "html", "text/plain")): return False, "", f"tipo de conteúdo não aceito ({ct[:40]})"
            bruto = r.read(8_000_001)
            if len(bruto) > 8_000_000: return False, "", "documento acima de 8 MB"
        if "pdf" in ct or bruto[:4] == b"%PDF":
            try:
                from pypdf import PdfReader
                import io
                texto = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(bruto)).pages[:40])
            except Exception:
                texto = bruto.decode("latin-1", "ignore")  # fallback: texto cru do PDF
        else:
            texto = re.sub(r"<[^>]+>", " ", bruto.decode("utf-8", "ignore"))
        return True, norm(texto), ct
    except Exception as e:
        return False, "", str(e)[:120]


def canal_do_dominio(host, uf):
    """Deriva o canal de obtenção (vocabulário controlado) a partir do domínio do link informado na contribuição."""
    if "diariomunicipal" in host:
        return "DOM"
    if host.endswith("in.gov.br"):
        return "DOU"
    if re.search(rf"(^|\.){uf.lower()}\.gov\.br$", host) and not host.startswith("www."):
        return "orgao_estadual"
    if re.search(rf"\.{uf.lower()}\.gov\.br$", host):
        return "orgao_estadual" if any(host.startswith(p) for p in ("defesacivil.", "cepdec.", "casamilitar.")) else "site_municipal"
    return "site_municipal"


def main():
    """Interface de linha de comando do funil de contribuições: aplica as seis regras R1-R6 e roteia cada item para fila editorial, conversão automática ou recusa."""
    token, site = os.environ.get("NETLIFY_AUTH_TOKEN"), os.environ.get("NETLIFY_SITE_ID")
    if not token or not site:
        print("• NETLIFY_AUTH_TOKEN/NETLIFY_SITE_ID ausentes — processamento de contribuições pulado.")
        return 0

    formularios = api(f"/sites/{site}/forms", token)
    form = next((f for f in formularios if f.get("name") == "contribuicao"), None)
    if not form:
        print("• Formulário 'contribuicao' ainda não existe no Netlify (nenhum envio até hoje).")
        return 0

    envios = api(f"/forms/{form['id']}/submissions?per_page=100", token)
    from recalcular_mare import CAPITAIS  # fonte única da lista de capitais (import tardio: requer numpy)
    processadas = set(json.load(open(ARQ_PROC))) if ARQ_PROC.exists() else set()
    recusadas = json.load(open(ARQ_REC)) if ARQ_REC.exists() else []
    municipios = json.load(open(ARQ_MUN))
    pontos = json.load(open(ARQ_PONTOS))
    ref = {(norm(r["nome"]), r["uf"]): r for r in json.load(open(ARQ_REF))}
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    aprovadas = mudou = reservadas = 0

    def recusa(sid, uf, municipio, motivo):
        """Registra a recusa de um item da fila com o motivo (regra R1-R6 aplicada), sem excluir o registro do histórico de contribuições."""
        recusadas.append({"quando": hoje, "uf": uf, "municipio": municipio, "motivo": motivo})
        processadas.add(sid)
        print(f"  ✗ {municipio or '?'}/{uf or '?'}: {motivo}")

    for e in envios:
        sid = e["id"]
        if sid in processadas:
            continue
        d = e.get("data", {})
        uf, municipio = (d.get("uf") or "").upper(), (d.get("municipio") or "").strip()
        tipo, url = (d.get("tipo") or "").strip(), (d.get("link_oficial") or "").strip()

        if uf not in UFS or not municipio or not url.startswith("https://"):
            recusa(sid, uf, municipio, "campos incompletos ou inválidos (R1)"); continue
        chave = (norm(municipio), uf)
        if chave not in ref:
            recusa(sid, uf, municipio, "município não reconhecido na malha IBGE — grafia precisa ser exata (R2)"); continue
        # AUTOAPLICAÇÃO SUSPENSA (auditoria externa de 02/09/2026, AUD-02/AUD-03): até a
        # editoria reativar por escrito, toda contribuição vai para a fila humana. Reativar =
        # AUTOAPLICAR = True, somente após os testes negativos de XSS/SSRF passarem no CI.
        if not AUTOAPLICAR:
            reservadas += 1
            print(f"  ◷ {municipio}/{uf}: reservada à revisão humana (autoaplicação suspensa — auditoria 02/09/2026)")
            continue
        # v2.2.4 (§7.6): "plano_saude" NUNCA é automatizável — cai sempre na fila humana,
        # como todo tipo fora do par ("plano", "decreto").
        if tipo not in ("plano", "decreto"):
            # R3 (corrigida em 27/08/2026): tipos não-automáticos NÃO são recusados —
            # ficam RESERVADOS à análise editorial, visíveis na fila humana até o
            # julgamento (mesmo mecanismo da R7). Cobre: plano_elaboracao,
            # plano_antigo, ato_antecipatorio (exige teste do objeto §5.2.1),
            # outro_ato e correcao. A categoria final é SEMPRE julgamento humano
            # (converter_contribuicao.py --categoria, obrigatório).
            reservadas += 1
            print(f"  ◷ {municipio or '?'}/{uf or '?'}: reservada à análise editorial (tipo '{tipo}'"
                  + (" — aplicar teste do objeto §5.2.1" if tipo == "ato_antecipatorio" else "") + ")")
            continue
        # R7 — reserva de julgamento humano: "plano" move o índice; capital é
        # maior alavanca populacional individual da UF (v2.2). Nenhum é auto-aplicável.
# Classificação de atos em forma de decreto na revisão humana: TESTE DO OBJETO
# (METODOLOGIA §5.2.1) — objeto ex-ante sem declarar dano + gatilho de previsão
# sem FIDE + rota de recurso próprio/prevenção; precisou de reconhecimento
# federal para cumprir a finalidade → resposta por definição.
# BATERIA NEGATIVA (§4.1.2): antes de manter nao_localizado/LAC de capital ou
# estado na revisão humana, rodar busca pelo NOME DO ENTE × dicionário completo
# e registrar (data, motor, strings, resultados). Denominação atípica achada →
# entra no dicionário com origem e data.
        # NÃO marca como processada nem recusada: a submissão permanece visível
        # na fila humana (verificar_contribuicoes.py) até ser julgada; depois de
        # aplicada via aplicar_revisao.py, a R6 a encerra aqui como duplicata.
        if tipo == "plano" or CAPITAIS.get(ref[chave]["nome"]) == uf:
            reservadas += 1
            print(f"  ◷ {ref[chave]['nome']}/{uf}: reservada à revisão humana (R7 — "
                  + ("plano move o índice" if tipo == "plano" else "capital"), end=")\n")
            continue
        ok_host, host, motivo = host_oficial(url)
        if not ok_host:
            recusa(sid, uf, municipio, motivo + " (R4)"); continue
        if d.get("numero_data") and not numero_data_valido(d.get("numero_data")):
            recusa(sid, uf, municipio, "campo número/data com marcação ou tamanho inválido (R4-bis, AUD-02)"); continue
        ok, texto, info = baixar_documento(url)
        if not ok:
            recusa(sid, uf, municipio, f"documento inacessível ({info}) (R5)"); continue
        if norm(municipio) not in texto:
            recusa(sid, uf, municipio, "documento não menciona o município (R5)"); continue
        if not any(p in texto for p in PALAVRAS[tipo]):
            recusa(sid, uf, municipio, f"conteúdo não confere com o tipo '{tipo}' declarado (R5)"); continue

        existente = next((x for x in municipios if x["nome"] == ref[chave]["nome"] and x["uf"] == uf), None)
        if existente and FORCA.get(existente["categoria"], 0) >= FORCA[tipo]:
            recusa(sid, uf, municipio, f"registro igual ou mais forte já publicado ({existente['categoria']}) (R6)"); continue

        novo = {"nome": ref[chave]["nome"], "uf": uf, "categoria": tipo,
                "documento": (d.get("numero_data") or "").strip() or
                             ("Plano de contingência" if tipo == "plano" else "Decreto de emergência"),
                "data": hoje, "url": url,
                "fonte": f"Contribuição de leitor, verificada automaticamente em {hoje} (fonte oficial e conteúdo do documento conferidos)",
                "canal": canal_do_dominio(host, uf),
                "lat": ref[chave]["lat"], "lon": ref[chave]["lon"]}
        if existente:
            existente.update(novo)
            for p in pontos:
                if p["nome"] == novo["nome"] and p["uf"] == uf:
                    p["categoria"] = tipo
            print(f"  ✓ {novo['nome']}/{uf}: promovido para {tipo}")
        else:
            municipios.append(novo)
            pontos.append({k: novo[k] for k in ("nome", "uf", "categoria", "lat", "lon")})
            print(f"  ✓ {novo['nome']}/{uf}: novo registro ({tipo})")
        processadas.add(sid)
        aprovadas += 1
        mudou = 1

    if mudou:
        json.dump(municipios, open(ARQ_MUN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(pontos, open(ARQ_PONTOS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # Regrava indice.json e percentual_uf.json DERIVADOS da nova base — sem
        # isto, o portão de consistência acusaria "percentual_uf desatualizado"
        # e bloquearia o job mesmo para escrituras neutras ao escore. Como a R7
        # garante que só decretos de não-capitais chegam aqui, o índice regravado
        # é idêntico ao anterior; a checagem de gaugeNum no portão prova isso a
        # cada rodada (achado e corrigido na auditoria de 27/08/2026).
        import subprocess
        r = subprocess.run([sys.executable, str(RAIZ / "recalcular_mare.py"), "--write"], cwd=RAIZ)
        if r.returncode != 0:
            print("  ✗ recálculo derivado falhou — abortando para bloquear a publicação.")
            return 1
    json.dump(sorted(processadas), open(ARQ_PROC, "w"), indent=0)
    json.dump(recusadas, open(ARQ_REC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Contribuições: {aprovadas} aprovada(s) · {reservadas} reservada(s) à revisão humana (R7) · "
          f"{len(recusadas)} recusada(s) acumuladas no log.")
    if reservadas:
        print("  → itens reservados aguardam na fila humana: rode verificar_contribuicoes.py, revise a fila,")
        print("    converta os aprovados com converter_contribuicao.py e aplique com aplicar_revisao.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
