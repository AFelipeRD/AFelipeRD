"""
ds.py -- Capa de sistema de diseño compartida por todos los generadores SVG.

Un solo origen de verdad (assets/tokens.json) -> variables CSS en cada SVG, con tema oscuro por
defecto y tema claro vía prefers-color-scheme. Las animaciones usan resorte real (CSS linear())
con cubic-bezier como respaldo para navegadores sin soporte.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from design_tokens import to_hex  # noqa: E402

T = json.loads((ROOT / "assets" / "tokens.json").read_text())
_L = T["light"]
DARK = dict(
    s0=T["surface-0"], s1=T["surface-1"], s2=T["surface-2"], bd=T["border-subtle"], bds=T["border-strong"],
    t1=T["text-primary"], t2=T["text-secondary"], t3=T["text-muted"],
    sig=T["accent-signal"], dat=T["accent-data"], sigd=T["accent-signal-dim"], datd=T["accent-data-dim"],
)
LIGHT = dict(
    s0=_L["surface-0"], s1=_L["surface-1"], s2=to_hex(0.94, 0.007, 258), bd=_L["border-subtle"], bds=_L["border-strong"],
    t1=_L["text-primary"], t2=_L["text-secondary"], t3=_L["text-muted"],
    sig=_L["accent-signal"], dat=_L["accent-data"], sigd=to_hex(0.72, 0.10, 72), datd=to_hex(0.68, 0.07, 209.5),
)
SPRING, EASE = T["motion"]["spring"], T["motion"]["ease-out"]
# True  -> respeta "reducir movimiento" del sistema del visitante (accesible, pero se ve quieto si lo tiene activo).
# False -> el perfil siempre se anima, sin clic y sin depender de la preferencia del sistema.
RESPECT_REDUCED_MOTION = False
MONO, SANS = T["type"]["mono"], T["type"]["sans"]


def style(extra=""):
    rm = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}" if RESPECT_REDUCED_MOTION else ""
    dark = ";".join(f"--{k}:{v}" for k, v in DARK.items())
    light = ";".join(f"--{k}:{v}" for k, v in LIGHT.items())
    return f"""<style>
:root{{{dark}}}
@media (prefers-color-scheme: light){{:root{{{light}}}}}
text{{font-family:{MONO};fill:var(--t2)}}
.sans{{font-family:{SANS}}}
.lbl{{font-size:10px;letter-spacing:.14em;fill:var(--t3)}}
.ttl{{font-size:16px;font-weight:650;fill:var(--t1);letter-spacing:-.01em}}
.dsc{{font-size:12px;fill:var(--t2)}}
.tag{{font-size:10px;fill:var(--t2)}}
.small{{font-size:9.5px;fill:var(--t3)}}
.nl{{font-size:9.5px;letter-spacing:.12em;fill:var(--t3)}}
.nt{{font-size:12px;fill:var(--t1);font-weight:600}}
.card{{fill:none;stroke:var(--bd);stroke-width:1}}
.node{{fill:var(--s1);stroke:var(--bd);stroke-width:1}}
.node-hot{{fill:var(--s1);stroke:var(--sigd);stroke-width:1}}
.node-data{{fill:var(--s1);stroke:var(--datd);stroke-width:1}}
.chip{{fill:none;stroke:var(--bd);stroke-width:1}}
.ln{{stroke:var(--datd);stroke-width:1.5;fill:none}}
.ln-sig{{stroke:var(--sigd);stroke-width:1.5;fill:none}}
.dot-d{{fill:var(--dat)}} .dot-s{{fill:var(--sig)}}
.in,.pop,.draw,.bar,.rise-d{{animation-fill-mode:backwards;animation-duration:.6s;
  animation-timing-function:{EASE};animation-timing-function:{SPRING}}}
.in{{animation-name:rise}}
.pop{{animation-name:pop;transform-box:fill-box;transform-origin:center}}
.draw{{animation-name:draw;animation-duration:.9s;animation-timing-function:{EASE}}}
.bar{{animation-name:grow;animation-duration:1.1s;transform-box:fill-box;transform-origin:0 50%}}
.flow{{stroke-dasharray:3 5;animation:flow 1.1s linear infinite}}
.pulse{{animation:pulse 2.6s ease-in-out infinite}}
.blink{{animation:blink 1.5s steps(1) infinite}}
.travel{{animation:travel var(--tt,3.6s) cubic-bezier(.45,0,.25,1) infinite}}
.float{{animation:float 3.6s ease-in-out infinite}}
.shadow{{transform-box:fill-box;transform-origin:center;animation:shadowp 3.6s ease-in-out infinite}}
.bob{{animation:float 4.4s ease-in-out infinite}}
.grow-y{{transform-box:fill-box;transform-origin:50% 100%;animation:growy 1.2s cubic-bezier(.34,1.56,.64,1) backwards}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
@keyframes shadowp{{0%,100%{{transform:scale(1);opacity:.35}}50%{{transform:scale(.82);opacity:.2}}}}
@keyframes growy{{from{{transform:scaleY(0)}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(8px)}}}}
@keyframes pop{{from{{opacity:0;transform:scale(.55)}}}}
@keyframes draw{{from{{stroke-dashoffset:1}}}}
@keyframes grow{{from{{transform:scaleX(0)}}}}
@keyframes flow{{to{{stroke-dashoffset:-16}}}}
@keyframes pulse{{0%,100%{{opacity:.5}}50%{{opacity:1}}}}
@keyframes blink{{0%,60%{{opacity:1}}61%,100%{{opacity:.15}}}}
@keyframes travel{{0%{{transform:translateX(0);opacity:0}}12%{{opacity:1}}88%{{opacity:1}}100%{{transform:translateX(var(--td,200px));opacity:0}}}}
{rm}
{extra}
</style>"""


def doc(w, h, body, title, desc, extra_css=""):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{title}</title><desc id="d">{desc}</desc>'
            f'{style(extra_css)}{body}</svg>')


def d(sec):
    """Atributo de retardo de animación (escalonado)."""
    return f' style="animation-delay:{sec:.2f}s"'


def chip(x, y, text, accent="bd"):
    w = len(text) * 6.15 + 18
    return (f'<g class="in"{d(0.9)}><rect class="chip" x="{x:.1f}" y="{y}" width="{w:.1f}" height="20" rx="10" '
            f'style="stroke:var(--{accent})"/><text class="tag" x="{x + 9:.1f}" y="{y + 14}">{text}</text></g>', w)


def chips(x0, y, items, max_x, accent="bd", gap=6, row_h=26):
    out, x = [], x0
    for it in items:
        c, w = chip(x, y, it, accent)
        if x + w > max_x:
            x, y = x0, y + row_h
            c, w = chip(x, y, it, accent)
        out.append(c)
        x += w + gap
    return "".join(out), y


def finalize(svg, preview=False):
    """preview=True resuelve var(--x) a hex (tema oscuro) para rasterizadores sin soporte de variables CSS."""
    if preview:
        svg = re.sub(r"var\(--(\w+)\)", lambda m: DARK[m.group(1)], svg)
    return svg


def save(path, svg, preview_dir=None):
    path = pathlib.Path(path)
    path.write_text(svg, encoding="utf-8")
    if preview_dir:
        try:
            import cairosvg
            pv = pathlib.Path(preview_dir)
            pv.mkdir(parents=True, exist_ok=True)
            cairosvg.svg2png(bytestring=finalize(svg, True).encode(), write_to=str(pv / (path.stem + ".png")), scale=1.5)
        except Exception as e:  # la vista previa es opcional
            print("  (sin vista previa:", e, ")")


def _dim(accent):
    return {"dat": "datd", "sig": "sigd"}.get(accent, "bds")


def iso_cube(cx, cy, s=22, accent="bds", h=None, delay=0.0, shadow=True, float_=True):
    """Prisma isométrico (cara superior clara, izquierda media, derecha oscura) con sombra proyectada.
    (cx, cy) = centro de la base. h = alto del prisma (por defecto ~cubo)."""
    w, hh = s, s / 2
    H = h if h is not None else s * 0.95
    top = f"{cx},{cy - H - hh} {cx + w},{cy - H} {cx},{cy - H + hh} {cx - w},{cy - H}"
    left = f"{cx - w},{cy - H} {cx},{cy - H + hh} {cx},{cy + hh} {cx - w},{cy}"
    right = f"{cx},{cy - H + hh} {cx + w},{cy - H} {cx + w},{cy} {cx},{cy + hh}"
    stroke = f"var(--{_dim(accent)})"
    sh = (f'<ellipse class="shadow" cx="{cx}" cy="{cy + hh + 5}" rx="{w * 0.95}" ry="{w * 0.30}" fill="#000" '
          f'style="animation-delay:-{delay:.2f}s"/>') if shadow else ""
    cls = "float" if float_ else ""
    base = "var(--s2)" if accent == "bds" else f"var(--{accent})"
    o = (0.9, 0.55, 0.30) if accent != "bds" else (1.0, 0.75, 0.55)
    return (f'{sh}<g class="{cls}" style="animation-delay:-{delay:.2f}s">'
            f'<polygon points="{left}" fill="{base}" fill-opacity="{o[1]}" stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{right}" fill="{base}" fill-opacity="{o[2]}" stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{top}" fill="{base}" fill-opacity="{o[0]}" stroke="{stroke}" stroke-width="1"/></g>')


def sphere_defs(ident, accent):
    """Gradiente radial para que un círculo parezca una esfera iluminada desde arriba-izquierda."""
    return (f'<radialGradient id="{ident}" cx=".35" cy=".30" r=".78"><stop offset="0" style="stop-color:var(--t1)" stop-opacity=".95"/>'
            f'<stop offset=".30" style="stop-color:var(--{accent})"/><stop offset="1" style="stop-color:var(--{_dim(accent)})"/></radialGradient>')
