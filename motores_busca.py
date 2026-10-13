#!/usr/bin/env python3
"""
motores_busca.py
================
O motor de origem que a camada 4 pede ao SearXNG — o que responde do runner, medido.

13/10/2026 (HANDOVER_DESCOBERTA item 1, correção pela raiz). Aqui vivia um disjuntor por motor
(sentinela, contagem por rodada, desligamento por 24 h, piso de dois ativos; 312 linhas e um arquivo
de estado). Ele desligava os motores mudos e o piso trazia de volta os que respondiam lixo — e nunca
pediu o único que funcionava. Medida do runner (`medir_revocacao.yml`, run 38433496633, 15
municípios com plano registrado × 9 strings): revocação 60%, e os 761 candidatos vieram TODOS de
`google cse`, que não estava na lista; duckduckgo devolveu CAPTCHA/403, brave 429, e bing resultado
alheio à consulta (wikipedia, reddit na rodada de 13/10).

A regra agora é a do handover: motor que não responde do runner sai — sem disjuntor, sem retry. A
lista muda por medição (`medir_revocacao.yml`), registrada no CHANGELOG. Consulta sem resposta é
`motor_sem_resposta` na própria decisão do coletor, nunca ausência.

USO
  python3 motores_busca.py --autoteste
"""
import sys

MOTORES = ("google cse",)


def autoteste() -> int:
    ok = MOTORES == ("google cse",) and all(isinstance(m, str) and m for m in MOTORES)
    print(("✓" if ok else "✗") + " AUTOTESTE — lista de motores declarada e não vazia.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else 0)
