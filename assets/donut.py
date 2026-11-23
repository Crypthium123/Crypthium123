"""Renders a1k0n's donut.c as an animated SVG (frame by frame, pure CSS)."""
import math
COLS, ROWS, N, DUR = 64, 30, 72, 6.0
RAMP = ".,-~:;=!*#$@"

def frame(A, B):
    out = [" "] * (COLS * ROWS); z = [0.0] * (COLS * ROWS)
    cA, sA, cB, sB = math.cos(A), math.sin(A), math.cos(B), math.sin(B)
    j = 0.0
    while j < 6.28:
        cj, sj = math.cos(j), math.sin(j); h = cj + 2
        i = 0.0
        while i < 6.28:
            ci, si = math.cos(i), math.sin(i)
            D = 1 / (si * h * sA + sj * cA + 5)
            t = si * h * cA - sj * sA
            x = int(COLS / 2 + 30 * D * (ci * h * cB - t * sB))
            y = int(ROWS / 2 + 15 * D * (ci * h * sB + t * cB))
            N_ = int(8 * ((sj * sA - si * cj * cA) * cB - si * cj * sA - sj * cA - ci * cj * sB))
            o = x + COLS * y
            if 0 <= y < ROWS and 0 <= x < COLS and D > z[o]:
                z[o] = D; out[o] = RAMP[max(N_, 0)]
            i += 0.02
        j += 0.07
    return ["".join(out[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

CW, LH, PX, PY = 9.0, 15.0, 0, 0
W, H = int(COLS * CW), int(ROWS * LH)
dim, bright = set(".,-~:;"), set("=!*#$@")
groups = []
for f in range(N):
    rows = frame(2 * math.pi * 2 * f / N, 2 * math.pi * f / N)
    layers = []
    for chars, cls in ((dim, "d"), (bright, "b")):
        t = "".join(
            f'<tspan x="0" y="{(r + 1) * LH:.0f}">{esc("".join(c if c in chars else " " for c in row).rstrip())}</tspan>'
            for r, row in enumerate(rows))
        layers.append(f'<text class="{cls}" xml:space="preserve">{t}</text>')
    groups.append(f'<g style="animation-delay:{f * DUR / N:.3f}s">{"".join(layers)}</g>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
text{{font-family:ui-monospace,'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace;font-size:14px;white-space:pre}}
.d{{fill:#8c959f}}.b{{fill:#1f2328}}
@media (prefers-color-scheme:dark){{.d{{fill:#6e7681}}.b{{fill:#e6edf3}}}}
g{{opacity:0;animation:f {DUR}s steps(1,end) infinite}}
@keyframes f{{0%{{opacity:1}}{100 / N:.4f}%{{opacity:0}}100%{{opacity:0}}}}
</style>
{"".join(groups)}
</svg>'''
open("donut.svg", "w").write(svg)

import os
if os.environ.get("PREVIEW"):
    os.makedirs("/tmp/fr", exist_ok=True)
    head = svg.split("<g style")[0].replace("g{{opacity:0".replace("{{","{"), "g{opacity:1").replace(".d{fill:#8c959f}.b{fill:#1f2328}", ".d{fill:#6e7681}.b{fill:#e6edf3}")
    for k, g in enumerate(groups):
        open(f"/tmp/fr/{k:03}.svg", "w").write(head.replace("<style>", f'<rect width="100%" height="100%" fill="#0d1117"/><style>', 1) + g + "</svg>")
