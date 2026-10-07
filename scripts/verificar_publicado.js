#!/usr/bin/env node
/**
 * verificar_publicado.js — o site PUBLICADO, contra o domínio real (14/09/2026).
 * Os 19 portões provam o conteúdo antes do merge; este prova o deploy depois:
 *   1. toda página do sitemap.xml responde 200 em HTTPS;
 *   2. cabeçalhos: CSP, HSTS, nosniff presentes; X-Robots-Tag noindex presente no ENSAIO
 *      (--esperar-noindex) e AUSENTE no lançamento (--esperar-index);
 *   3. integridade: o SHA-256 de cada arquivo servido = docs/MANIFEST_SHA256.txt do repositório
 *      (amostra: todas as páginas, todos os data/*.json referenciados no manifesto, PDFs, sitemap);
 *   4. canário de conteúdo: data/meta.json com data de edição; data/indice.json com 27 UFs.
 * Uso: node scripts/verificar_publicado.js --base https://monitorelnino.com.br [--esperar-noindex|--esperar-index] [--amostra N]
 * Sai com 1 se algo falhar. Sem dependências além do Node 20 (fetch nativo).
 */
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const raiz = path.resolve(__dirname, "..");
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? (args[i + 1] || true) : d; };
const BASE = String(opt("--base", "https://monitorelnino.com.br")).replace(/\/$/, "");
// 14/09/2026 (§1.1): o modo padrão vem de data/publicacao.json — indexar=false exige noindex em toda página servida
// (cabeçalho E meta); indexar=true exige o contrário. As flags de linha de comando só sobrepõem para diagnóstico.
const PUB = (() => { try { return JSON.parse(fs.readFileSync(path.join(raiz, "data", "publicacao.json"), "utf8")); } catch (e) { return { indexar: false }; } })();
const ESPERAR_NOINDEX = args.includes("--esperar-noindex") || (!args.includes("--esperar-index") && !args.includes("--neutro") && !PUB.indexar);
const ESPERAR_INDEX = args.includes("--esperar-index") || (!args.includes("--esperar-noindex") && !args.includes("--neutro") && !!PUB.indexar);
const AMOSTRA = parseInt(opt("--amostra", "400"), 10);
const falhas = []; const ok = (nome, cond, extra = "") => { console.log((cond ? "  ✓ " : "  ✗ ") + nome + (extra ? " · " + extra : "")); if (!cond) falhas.push(nome); };

async function get(url, tentativas = 3) {
  for (let i = 0; i < tentativas; i++) {
    try {
      const cab = { "User-Agent": "Monitor El Nino Brasil (verificar_publicado)" };
      if (process.env.PREVIA_BASIC_AUTH) cab["Authorization"] = "Basic " + Buffer.from(process.env.PREVIA_BASIC_AUTH).toString("base64");   // 14/09: domínio com senha
      const r = await fetch(url, { redirect: "manual", headers: cab });
      const buf = Buffer.from(await r.arrayBuffer());
      return { status: r.status, headers: r.headers, buf };
    } catch (e) { if (i === tentativas - 1) return { status: 0, headers: new Map(), buf: Buffer.alloc(0), erro: e.message }; await new Promise(r => setTimeout(r, 1500 * (i + 1))); }
  }
}

(async () => {
  console.log(`verificar_publicado · base=${BASE} · modo=${ESPERAR_NOINDEX ? "ensaio (noindex)" : ESPERAR_INDEX ? "lançamento (index)" : "sem exigência de robots"}`);
  // 1. sitemap
  const sm = await get(`${BASE}/sitemap.xml`);
  ok("sitemap.xml responde 200", sm.status === 200, `status=${sm.status}`);
  const locs = [...sm.buf.toString("utf8").matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].trim());
  ok("sitemap lista as páginas (≥ 11)", locs.length >= 11, `${locs.length} entradas`);
  const paginas = locs.filter(u => /\/$|\.html$/.test(u));
  for (const u of paginas) {
    const alvo = u.replace(/^https?:\/\/[^/]+/, BASE);
    const r = await get(alvo);
    const h = r.headers;
    ok(`200 · ${alvo.replace(BASE, "") || "/"}`, r.status === 200, `status=${r.status}${r.erro ? " " + r.erro : ""}`);
    if (r.status !== 200) continue;
    const csp = h.get("content-security-policy") || "", hsts = h.get("strict-transport-security") || "", nosniff = h.get("x-content-type-options") || "";
    ok(`cabeçalhos · ${alvo.replace(BASE, "") || "/"}`, csp.includes("default-src 'self'") && hsts.includes("max-age") && nosniff === "nosniff");
    const robots = (h.get("x-robots-tag") || "").toLowerCase();
    if (ESPERAR_NOINDEX) ok(`noindex presente · ${alvo.replace(BASE, "") || "/"}`, robots.includes("noindex") && /<meta name="robots" content="noindex/.test(r.buf.toString("utf8")), `x-robots-tag=${robots || "(vazio)"} · meta=${/<meta name="robots" content="noindex/.test(r.buf.toString("utf8"))}`);
    if (ESPERAR_INDEX) ok(`noindex AUSENTE · ${alvo.replace(BASE, "") || "/"}`, !robots.includes("noindex"), `x-robots-tag=${robots || "(vazio)"}`);
    const html = r.buf.toString("utf8");
    ok(`sem mixed content · ${alvo.replace(BASE, "") || "/"}`, !/(src|href)=["']http:\/\//.test(html));
  }
  // 2. robots.txt coerente com o modo
  const rb = await get(`${BASE}/robots.txt`);
  if (ESPERAR_NOINDEX) ok("robots.txt bloqueia tudo (ensaio)", rb.status === 200 && /Disallow:\s*\/\s*$/m.test(rb.buf.toString()));
  if (ESPERAR_INDEX) ok("robots.txt do site (lançamento), com sitemap", rb.status === 200 && /Sitemap:/i.test(rb.buf.toString()) && !/^Disallow:\s*\/\s*$/m.test(rb.buf.toString()));
  // 2b. 14/09/2026: quando a editoria publica o domínio em modo "senha" (data/publicacao.json · dominio), a home SEM credencial
  // tem de responder 401 (Basic-Auth do servidor). Se o plano do Netlify ignorar o cabeçalho, isto falha — e é para falhar.
  if (PUB.dominio === "senha") {
    try { const semAuth = await fetch(BASE + "/", { redirect: "manual", headers: { "User-Agent": "Monitor El Nino Brasil (verificar_publicado)" } });
      ok("modo senha: a home sem credencial responde 401 (Basic-Auth ativo no servidor)", semAuth.status === 401, `status=${semAuth.status}`); } catch (e) { ok("modo senha: teste sem credencial", false, e.message); }
  }
  // 3. integridade contra o manifesto do repositório
  const manifesto = path.join(raiz, "docs", "MANIFEST_SHA256.txt");
  if (fs.existsSync(manifesto)) {
    const linhas = fs.readFileSync(manifesto, "utf8").split("\n").map(l => l.trim()).filter(Boolean);
    const entradas = linhas.map(l => { const m = l.match(/^([0-9a-f]{64})\s+\*?(.+)$/); return m ? { hash: m[1], arq: m[2].replace(/^\.\//, "") } : null; }).filter(Boolean);
    // 03/10/2026: `dados-abertos/` sai da amostra. A regra 1 da editoria tirou a distribuição de
    // dados do site, e o `netlify.toml` passou a devolver 301 para `/dados-abertos/*` — os arquivos
    // continuam selados no manifesto, porque existem no repositório, mas o site não os serve, e
    // cobrar 200 deles é cobrar o contrário da decisão. Foram as oito "ausentes (301)" de hoje.
    const REDIRECIONADOS = /^dados-abertos\//;
    // robots.txt fica de fora no ensaio (é trocado de propósito); .github, scripts, docs e node não são servidos ao público
    // fora da amostra: o que o Netlify não serve (dotfiles, netlify.toml) e o que não é do site público
    const servidos = entradas.filter(e => !REDIRECIONADOS.test(e.arq) && !/^(\.github|scripts|docs|node_modules|tests?|leituras_qd)\//.test(e.arq) && !/^\./.test(e.arq) && !/^(robots\.txt|netlify\.toml|package.*\.json|requirements\.txt|.*\.py|README\.md|CHANGELOG\.md|METODOLOGIA\.md|LICENSE.*)$/.test(e.arq));
    const prioridade = servidos.filter(e => /\.(html|pdf|xml)$|^data\/(meta|indice|sinais_risco|saude_sinais|monitor_saude)\.json$|^data\/saude_desfechos\/(serie_painel|dda_serie|chik_serie_painel|srag_serie)\.json$|^assets\/js\/|^assets\/.*\.css$/.test(e.arq));
    const resto = servidos.filter(e => !prioridade.includes(e));
    const amostra = prioridade.concat(resto.slice(0, Math.max(0, AMOSTRA - prioridade.length)));
    let iguais = 0, prettyUrls = 0, hud = 0, aspas = 0, forms = 0, diferentes = [], ausentes = [];
    // 14/09/2026 (2º ensaio, já com skip_processing): o que restava não era pós-processamento — é o "Netlify HUD",
    // recurso de painel do site que INJETA <script async src="/.netlify/scripts/hud?..."> em toda página ao servir e,
    // ao reserializar, troca aspas de atributos (class="x" → class='x'). Só se desliga no painel do Netlify. Aqui ele
    // é reconhecido pelo nome, removido para a comparação e reportado como achado próprio — nunca escondido.
    // 07/10/2026: as DUAS reescritas do Netlify passam a ser normalizações SEPARADAS, cada uma
    // aceita por si. Antes elas viviam numa função só, e o resultado só era aproveitado quando o
    // script do HUD estava presente E a página voltava a bater por inteiro — bastava uma das duas
    // não casar para a outra ser descartada junto. Era o caso do `index.html`: ele reprovava
    // sozinho por `class="btn-nav"` servido como `class='btn-nav'`, e a normalização de aspas, que
    // existia, nunca chegava a ser aplicada nele. Separadas, cada reescrita conhecida é desfeita e
    // CONTADA pelo que é, e o que sobrar continua sendo divergência real.
    const semHud = (txt) => {
      const fora = txt.replace(/<script[^>]*\/\.netlify\/scripts\/hud[^>]*><\/script>\s*/g, "");
      return [fora, fora !== txt];
    };
    // A reserialização do Netlify troca a aspa de atributos (class="x" → class='x'). Só desfaz
    // onde o VALOR não contém aspa dupla: `style='font-family:"X"'` com aspas invertidas não é a
    // mesma coisa, e reescrevê-lo mudaria o atributo em vez de restaurá-lo.
    const semAspaTrocada = (txt) => {
      const fora = txt.replace(/(<[a-z][^>]*?\s[a-z-]+=)'([^'"]*)'/g, '$1"$2"');
      return [fora, fora !== txt];
    };
    // A TERCEIRA reescrita conhecida: o Netlify Forms. Onde a marcação declara
    // `data-netlify="true"`, o servidor REESCREVE o formulário — tira `data-netlify` e
    // `netlify-honeypot`, reordena os atributos em ordem alfabética, troca `/obrigado.html` por
    // `/obrigado` e injeta `<input name="form-name">`. É o mecanismo do recurso, não divergência;
    // desfazê-lo com fidelidade exigiria reimplementar a reescrita do Netlify, e reimplementar
    // o que não controlamos é como o portão passa a provar a nossa cópia em vez do site.
    //
    // Então o BLOCO do formulário — e só ele — sai da comparação byte a byte, nos dois lados, e o
    // relatório diz quantos HTML foram comparados assim. O resto da página continua conferido
    // byte a byte, inclusive tudo o que vem antes e depois do formulário.
    //
    // DECISÃO DA EDITORIA (07/10/2026): ela autorizou tirar o bloco, sabendo que isso reduz o que
    // o portão prova naquele trecho. Hoje é UM formulário em UMA página (index.html, a
    // contribuição pública); se aparecer um segundo, a contagem do relatório o mostra.
    const semFormNetlify = (txt) => {
      const fora = txt.replace(/<form\b[^>]*>[\s\S]*?<\/form>/gi, "<!-- form -->");
      return [fora, fora !== txt];
    };
    for (const e of amostra) {
      const r = await get(`${BASE}/${e.arq.split("/").map(encodeURIComponent).join("/")}`);
      if (r.status !== 200) { ausentes.push(`${e.arq} (${r.status})`); continue; }
      let comparado = r.buf; let h = crypto.createHash("sha256").update(r.buf).digest("hex");
      if (h !== e.hash && /\.html$/.test(e.arq)) {
        // 14/09/2026 (provado no 1º ensaio): o "Pretty URLs" do Netlify reescreve href="x.html" → href='/x' e
        // href="index.html" → href='/'. Desfazemos SÓ essa reescrita conhecida e comparamos de novo — qualquer
        // outra diferença continua sendo divergência real.
        // cobre também âncoras e consultas: href='/#x' → "index.html#x"; href='/pagina#x' → "pagina.html#x"
        const norm = r.buf.toString("utf8").replace(/href='\/([a-z0-9-]*)((?:[#?][^']*)?)'/g, (m, pag, resto) => `href="${pag ? pag + ".html" : "index.html"}${resto}"`);
        comparado = Buffer.from(norm, "utf8");
        h = crypto.createHash("sha256").update(comparado).digest("hex");
        if (h === e.hash) prettyUrls++;
        if (h !== e.hash) {
          // As duas em sequência, e cada uma contada pelo que é. A comparação final é a do texto
          // com AS DUAS desfeitas — qualquer outra diferença sobrevive a isto e reprova.
          const [txtHud, tinhaHud] = semHud(comparado.toString("utf8"));
          const [txtAspa, tinhaAspa] = semAspaTrocada(txtHud);
          // O bloco do formulário sai dos DOIS lados, e só quando o lado do repositório realmente
          // tem um formulário declarado para o Netlify: numa página sem `data-netlify` um `<form>`
          // é marcação nossa, e tirá-lo da comparação esconderia uma mudança de verdade.
          const localBruto = fs.existsSync(path.join(raiz, e.arq))
            ? fs.readFileSync(path.join(raiz, e.arq), "utf8") : "";
          const temFormNetlify = /<form\b[^>]*\sdata-netlify=/i.test(localBruto);
          const [txtLimpo, tirouForm] = temFormNetlify ? semFormNetlify(txtAspa) : [txtAspa, false];
          if (tinhaHud || tinhaAspa || tirouForm) {
            const alvo = tirouForm
              ? crypto.createHash("sha256").update(Buffer.from(semFormNetlify(localBruto)[0], "utf8")).digest("hex")
              : e.hash;
            const h2 = crypto.createHash("sha256").update(Buffer.from(txtLimpo, "utf8")).digest("hex");
            // `comparado` recebe o texto normalizado mesmo quando ele NÃO volta a bater: é esse o
            // texto que a prova da divergência imprime logo abaixo, e imprimir o texto cru fazia o
            // relatório apontar uma reescrita já conhecida no lugar da diferença que resta.
            comparado = Buffer.from(txtLimpo, "utf8");
            if (h2 === alvo) {
              // `h` recebe o hash do manifesto porque a comparação que VALEU foi a do texto
              // normalizado contra o repositório normalizado do mesmo jeito. Contar as três
              // separadamente é o que mantém o relatório honesto sobre o que foi desfeito.
              h = e.hash;
              if (tinhaHud) hud++;
              if (tinhaAspa) aspas++;
              if (tirouForm) forms++;
            }
          }
        }
      }
      if (h === e.hash) { iguais++; continue; }
      diferentes.push(e.arq);
      // prova da divergência (depois da normalização): tamanho e primeiro trecho diferente
      const local = fs.existsSync(path.join(raiz, e.arq)) ? fs.readFileSync(path.join(raiz, e.arq)) : null;
      if (local) {
        let i = 0; while (i < local.length && i < comparado.length && local[i] === comparado[i]) i++;
        console.log(`    · ${e.arq}: repositório=${local.length} B · servido(normalizado)=${comparado.length} B · diverge no byte ${i}`);
        console.log(`      repo:    ${JSON.stringify(local.toString("utf8", Math.max(0, i - 60), i + 160))}`);
        console.log(`      servido: ${JSON.stringify(comparado.toString("utf8", Math.max(0, i - 60), i + 160))}`);
      }
    }
    ok(`integridade: ${iguais}/${amostra.length} arquivo(s) servidos batem com o manifesto` + (prettyUrls ? ` (${prettyUrls} HTML só com a reescrita "Pretty URLs" do Netlify)` : "") + (hud ? ` (${hud} HTML idênticos depois de remover o script do Netlify HUD)` : "") + (aspas ? ` (${aspas} HTML idênticos depois de desfazer a troca de aspas de atributo)` : "") + (forms ? ` (${forms} HTML idênticos fora do bloco do formulário, que o Netlify Forms reescreve ao servir)` : ""), diferentes.length === 0 && ausentes.length === 0,
       (diferentes.length ? "diferentes: " + diferentes.slice(0, 8).join(", ") : "") + (ausentes.length ? " · ausentes: " + ausentes.slice(0, 8).join(", ") : ""));
    // O HUD é um script de terceiro não pedido, em todas as páginas de um site de interesse público: no lançamento é
    // bloqueante; no ensaio, aviso com a instrução. Desligar: painel do Netlify → Site configuration → (Build & deploy /
    // Post processing ou "Netlify HUD") → desativar; não há como pelo repositório.
    if (hud) ok(`Netlify HUD ${ESPERAR_INDEX ? "precisa estar DESLIGADO no lançamento" : "detectado"}: ${hud} página(s) com script injetado pelo Netlify — desligar no painel do site`, !ESPERAR_INDEX);
    // 07/10/2026: a tag é injetada ao servir e está fora do nosso alcance, mas o RECURSO não.
    // `netlify.toml` devolve 404 no caminho do script, e isto confere que o domínio o cumpre.
    // Vale medir separado da tag porque são duas coisas: uma é o HTML que o Netlify escreve, a
    // outra é o que o domínio entrega quando o navegador vai buscar. A segunda é nossa.
    if (hud) {
      const alvo = await get(`${BASE}/.netlify/scripts/hud`);
      ok(`script do HUD inalcançável no domínio (404 por netlify.toml) · status=${alvo.status}`,
         alvo.status === 404);
    }
  } else ok("manifesto presente no repositório", false);
  // 4. canários de conteúdo
  const meta = await get(`${BASE}/data/meta.json`);
  let m = null; try { m = JSON.parse(meta.buf.toString()); } catch (e) {}
  ok("data/meta.json com data de edição (dd/mm/aaaa)", !!m && /^\d{2}\/\d{2}\/\d{4}$/.test(m.atualizado_em || ""), m ? `atualizado_em=${m.atualizado_em} corte=${m.corte}` : `status=${meta.status}`);
  const idx = await get(`${BASE}/data/indice.json`);
  let I = null; try { I = JSON.parse(idx.buf.toString()); } catch (e) {}
  ok("data/indice.json com 27 UFs", !!I && Object.keys(I).filter(k => k.length === 2).length === 27);
  console.log(falhas.length ? `\n✗ PUBLICADO: ${falhas.length} verificação(ões) falharam.` : "\n✓ PUBLICADO OK — páginas, cabeçalhos, robots no modo esperado, integridade contra o manifesto e canários.");
  process.exit(falhas.length ? 1 : 0);
})();
