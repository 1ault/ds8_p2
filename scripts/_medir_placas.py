"""Mide la geometria real con que Wokwi dibuja el diagrama del proyecto.

Abre el proyecto publico en Chrome headless, lee el rectangulo en pantalla de
cada componente (son elementos DOM con etiquetas `wokwi-*` / `board-*`) y
traduce esos pixeles a unidades del diagrama usando dos componentes conocidos.
Con eso se obtiene el tamano real de las placas de pan y las coordenadas
exactas para dejarlas centradas bajo cada grupo.

Uso:
    python scripts/_medir_placas.py [url]
Salida:
    .tmp/medicion_parts.json, .tmp/placa_render.png
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from capturar_wokwi import Navegador, encontrar_navegador  # noqa: E402

URL = "https://wokwi.com/projects/480692575433146369"

JS_PARTES = """
(() => {
  const salida = [];
  for (const e of document.querySelectorAll('*')) {
    const r = e.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) continue;
    const tag = e.tagName.toLowerCase();
    salida.push({
      tag: tag,
      clase: (e.className && String(e.className).slice(0, 40)) || '',
      id: e.id || '',
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height)
    });
  }
  return salida;
})()
"""

JS_UNION = """
(() => {
  const partes = [...document.querySelectorAll('*')].filter(e =>
    /^(wokwi-|board-)/.test(e.tagName.toLowerCase()));
  if (!partes.length) return null;
  let x1 = 1e9, y1 = 1e9, x2 = 0, y2 = 0;
  for (const p of partes) {
    const r = p.getBoundingClientRect();
    if (r.width < 5 || r.height < 5) continue;
    x1 = Math.min(x1, r.x); y1 = Math.min(y1, r.y);
    x2 = Math.max(x2, r.right); y2 = Math.max(y2, r.bottom);
  }
  if (x1 > x2) return null;
  const m = 40;
  return {x: x1 - m, y: y1 - m, w: (x2 - x1) + 2 * m, h: (y2 - y1) + 2 * m};
})()
"""


async def medir(url: str) -> int:
    ejecutable = encontrar_navegador()
    if not ejecutable:
        print("no se encontro Chrome")
        return 1

    async with Navegador(ejecutable, puerto=9461, ancho=1680, alto=1400) as nav:
        await nav.navegar(url)

        partes = []
        for _ in range(60):
            partes = await nav.evaluar(JS_PARTES) or []
            if len(partes) >= 10:
                break
            await asyncio.sleep(0.5)

        if not partes:
            print("no se detectaron componentes en la pagina")
            return 2

        datos = RAIZ / ".tmp" / "medicion_parts.json"
        datos.write_text(json.dumps(partes, indent=1), encoding="utf-8")
        print("elementos grandes detectados:", len(partes))
        # Solo los que parecen componentes o placas: los mas grandes de la pagina
        grandes = sorted(partes, key=lambda p: p["w"] * p["h"], reverse=True)[:14]
        for parte in grandes:
            print("  %-26s %-22s x=%-6d y=%-6d w=%-5d h=%-5d" % (
                parte["tag"], parte["clase"], parte["x"], parte["y"],
                parte["w"], parte["h"]))

        union = await nav.evaluar(JS_UNION)
        if union:
            await nav.capturar(RAIZ / ".tmp" / "placa_render.png", union)
        return 0


if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else URL
    sys.exit(asyncio.run(medir(destino)))
