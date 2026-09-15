/* Portão de senha da prévia (03/09/2026). Ativo apenas nos endereços *.netlify.app do main
   (a prévia); no domínio final, em localhost e no navegador simulado dos portões não faz nada.
   Compara o SHA-256 do que foi digitado com o hash abaixo; guarda a liberação no navegador.
   Não é segurança — é um véu para visualização casual (o servidor pode exigir Basic-Auth). */
(function () {
  var HASH = "165f92940dea02be87267b182cf31661985184fb5ae74419548a55709555076c";
  var h = location.hostname || "";
  if (typeof crypto === "undefined" || !crypto.subtle) return;
  if (!h || /^(localhost|127\.0\.0\.1)$/.test(h)) return;   // portões e uso local: nunca pede senha
  // 14/09/2026: no domínio final o véu só existe quando a editoria publica em modo "senha" (data/publicacao.json · dominio: "senha")
  if (!/\.netlify\.app$/.test(h)) {
    fetch("data/publicacao.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (p) { if (p && p.dominio === "senha") comecar(); }).catch(function () {});
    return;
  }
  comecar();
  function comecar() {
  try { if (localStorage.getItem("mare_previa_ok") === HASH) return; } catch (e) {}
  document.documentElement.style.visibility = "hidden";
  function sha256(t) { return crypto.subtle.digest("SHA-256", new TextEncoder().encode(t)).then(function (b) { return Array.from(new Uint8Array(b)).map(function (x) { return x.toString(16).padStart(2, "0"); }).join(""); }); }
  function pedir() {
    var s = window.prompt("Prévia restrita do MARÉ — informe a senha de acesso:");
    if (s === null) { document.documentElement.innerHTML = "<body style=\"font-family:sans-serif;padding:40px\">Acesso restrito.</body>"; document.documentElement.style.visibility = "visible"; return; }
    sha256(s).then(function (x) { if (x === HASH) { try { localStorage.setItem("mare_previa_ok", HASH); } catch (e) {} document.documentElement.style.visibility = "visible"; } else pedir(); });
  }
  pedir();
  }
})();
