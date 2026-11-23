"""Shared look for every generated SVG."""
from html import escape as esc
BG = "#0d1117"; PANEL = "#161b22"; LINE = "#30363d"; FG = "#e6edf3"; DIM = "#7d8590"
BLUE = "#58a6ff"; PURPLE = "#bc8cff"; GREEN = "#3fb950"; YELLOW = "#d29922"
ORANGE = "#f0883e"; RED = "#ff7b72"; CYAN = "#39c5cf"; PINK = "#f778ba"
RAMP = ["#3d2c8d", "#5a3fc0", "#6e5ce6", "#3b82f6", "#38bdf8", "#22d3ee",
        "#34d399", "#a3e635", "#facc15", "#fb923c", "#f472b6", "#fff1f2"]
FONT = "ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"


def frame(w, h, inner, extra_css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<style>text{{font-family:{FONT};white-space:pre}}{extra_css}</style>'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" stroke="{LINE}"/>'
            f'{inner}</svg>')


def runs(pairs):
    """[(text,color),...] -> tspans, merging equal colors."""
    out, cur, buf = [], None, ""
    for t, c in pairs:
        if c == cur:
            buf += t
        else:
            if buf:
                out.append((buf, cur))
            cur, buf = c, t
    if buf:
        out.append((buf, cur))
    return "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' if c else esc(t) for t, c in out)


def label(x, y, text, color=DIM, size=11, anchor="start", weight=400):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" text-anchor="{anchor}"'
            f' font-weight="{weight}">{esc(text)}</text>')
