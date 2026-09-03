# Ramo `publico` — página em branco (fase de testes)

Este ramo NÃO é o site. Contém apenas uma página inicial em branco, servida em
monitorelnino.com.br enquanto o site completo (ramo `main`) é testado no
endereço secundário do Netlify (`main--<nome-do-site>.netlify.app`).

- Lançamento: Netlify → Site configuration → Build & deploy → Branches and
  deploy contexts → Production branch: trocar `publico` por `main`.
- Este ramo nunca recebe dados nem código do site; a rotina semanal continua
  atuando só no `main`. **Única exceção (03/09/2026):** `progresso.json`, um
  contador operacional (quantos municípios já foram consultados na varredura
  dos diários oficiais, sobre quantos no total) — nunca dado do índice, nunca
  afirmação sobre existência de plano. Atualizado pelo robô a cada rodada via
  `scripts/atualizar_contador_cortina.py`, para a editoria acompanhar o
  andamento pelo próprio domínio, sem precisar da prévia com senha.
