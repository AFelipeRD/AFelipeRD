#!/usr/bin/env python3
"""
build_assets.py -- Genera las dos composiciones principales del perfil (700 px de ancho de diseño):

  assets/hero.svg   Identidad + holograma 3D (WebP animado incrustado) + ticker + métricas
  assets/deck.svg   Arquitectura de datos (bloques isométricos) + MCP + ML + repos, en una sola pieza

    python scripts/design_tokens.py
    python scripts/build_portrait.py foto.png
    python scripts/generate_hologram.py --photo foto.png      # assets/visual_core.webp
    python scripts/build_assets.py [--preview DIR]

Por qué una sola pieza por bloque: GitHub apila las imágenes sueltas y el perfil se vuelve larguísimo.
Cada SVG contiene su propio layout, así que el README queda compacto. Todo se anima solo (SMIL + CSS),
sin clic: un SVG usado como <img> no recibe el control de reproducción que GitHub pone a los GIF.
"""
import base64
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ds import ROOT, d, doc, iso_cube, save, sphere_defs  # noqa: E402

A = ROOT / "assets"
PREVIEW = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
ARROW = ('<marker id="ah" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
         '<path d="M0 0L7 3.5L0 7z" style="fill:var(--dat)"/></marker>')


# ----------------------------------------------------------------------------- utilidades
def chip_w(t):
    return len(t) * 6.2 + 18


def marquee(items, y, name, dur, reverse, accent):
    """Fila de chips que se desplaza sin fin (dos copias para empalme perfecto)."""
    x, spec = 0, []
    for t in items:
        w = chip_w(t)
        spec.append((x, w, t))
        x += w + 6
    total = x
    g = []
    for off in (0, total):
        for cx, w, t in spec:
            g.append(f'<rect x="{cx + off:.1f}" y="0" width="{w:.1f}" height="20" rx="10" fill="none" style="stroke:var(--{accent}d)" stroke-width="1"/>'
                     f'<text x="{cx + off + 9:.1f}" y="14" class="tag">{t}</text>')
    frm, to = (-total, 0) if reverse else (0, -total)
    css = f"@keyframes {name}{{from{{transform:translateX({frm:.1f}px)}}to{{transform:translateX({to:.1f}px)}}}}"
    return f'<g transform="translate(24,{y})"><g style="animation:{name} {dur}s linear infinite">{"".join(g)}</g></g>', css


def orbit(rx, ry, dur, tilt0, accent, phase):
    """Anillo orbital con partículas: la elipse + el cambio de tamaño/opacidad simulan profundidad 3D."""
    path = f"M{-rx},0 a{rx},{ry} 0 1,0 {2 * rx},0 a{rx},{ry} 0 1,0 {-2 * rx},0"
    dots = ""
    for k, off in enumerate((0, dur / 2)):
        b = -(off + phase)
        dots += (f'<circle r="2" style="fill:var(--{accent})"><animateMotion dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite" path="{path}"/>'
                 f'<animate attributeName="r" values="1.2;3.1;1.2;0.9;1.2" keyTimes="0;.25;.5;.75;1" dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values=".5;1;.5;.25;.5" keyTimes="0;.25;.5;.75;1" dur="{dur}s" begin="{b:.2f}s" repeatCount="indefinite"/></circle>')
    return (f'<g><animateTransform attributeName="transform" type="rotate" from="{tilt0}" to="{tilt0 + 360}" dur="{dur * 4}s" repeatCount="indefinite"/>'
            f'<ellipse rx="{rx}" ry="{ry}" fill="none" style="stroke:var(--bd)" stroke-width="1"/>{dots}</g>')


# ----------------------------------------------------------------------------- hero
def hero(embed_png=None):
    W, H = 700, 336
    if embed_png:
        uri = "data:image/png;base64," + base64.b64encode(pathlib.Path(embed_png).read_bytes()).decode()
    else:
        uri = "data:image/webp;base64," + base64.b64encode((A / "visual_core.webp").read_bytes()).decode()
    frag, bright = (A / "portrait.frag").read_text(), (A / "portrait_bright.frag").read_text()
    b = []
    b.append(f"""<defs>
  <clipPath id="left"><rect x="2" y="2" width="352" height="{H - 4}" rx="12"/></clipPath>
  <clipPath id="av"><rect x="24" y="28" width="104" height="104" rx="8"/></clipPath>
  <clipPath id="hw"><rect x="368" y="10" width="316" height="316" rx="6"/></clipPath>
  <clipPath id="ty"><rect class="typing" x="148" y="100" width="190" height="16"/></clipPath>
  <clipPath id="mq"><rect x="24" y="158" width="328" height="52"/></clipPath>
  <pattern id="dg1" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" style="fill:var(--bds)"/>
    <animateTransform attributeName="patternTransform" type="translate" from="0 0" to="14 14" dur="6s" repeatCount="indefinite"/></pattern>
  <pattern id="dg2" width="30" height="30" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1.3" style="fill:var(--dat)"/>
    <animateTransform attributeName="patternTransform" type="translate" from="30 0" to="0 30" dur="14s" repeatCount="indefinite"/></pattern>
  <linearGradient id="rg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--dat)"/><stop offset="1" style="stop-color:var(--sig)"/></linearGradient>
  <linearGradient id="sc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--dat)" stop-opacity="0"/><stop offset=".5" style="stop-color:var(--dat)" stop-opacity=".25"/><stop offset="1" style="stop-color:var(--dat)" stop-opacity="0"/></linearGradient>
  <filter id="gl" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>""")
    b.append(f'<rect class="card" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/>')
    # fondo con paralaje (dos capas de puntos a distinta velocidad)
    b.append(f'<g clip-path="url(#left)" opacity=".42"><rect x="0" y="0" width="354" height="{H}" fill="url(#dg1)"/></g>'
             f'<g clip-path="url(#left)" opacity=".30"><rect x="0" y="0" width="354" height="{H}" fill="url(#dg2)"/></g>')
    b.append(f'<rect class="streak" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" style="stroke:var(--dat)" stroke-width="2.4" '
             f'stroke-linecap="round" pathLength="1000" stroke-dasharray="60 940" filter="url(#gl)"/>')
    # --- avatar con anillos orbitales (giroscopio)
    b.append(f'<g class="in"{d(0.1)}><g class="bob">'
             f'<g transform="translate(76,80)">{orbit(66, 21, 5.6, -22, "dat", 0)}{orbit(58, 17, 7.2, 28, "sig", 1.1)}</g>'
             f'<rect x="24" y="28" width="104" height="104" rx="8" style="fill:var(--s0);stroke:var(--bd)"/>'
             f'<g clip-path="url(#av)"><g transform="translate(24,29) scale(.3152)" fill="none" stroke-linecap="round">{frag}{bright}</g>'
             f'<rect class="scan" x="24" y="28" width="104" height="26" fill="url(#sc)"/></g>'
             f'<path d="M24 38V28h10M118 28h10v10M128 122v10h-10M34 132H24v-10" fill="none" style="stroke:var(--sig)" stroke-width="1.6"/></g></g>')
    # --- nombre, rol, estado
    b.append(f'<g class="in"{d(0.20)}><text class="sans" x="148" y="58" style="font-size:25px;font-weight:700;fill:var(--t1);letter-spacing:-.025em">Andres Felipe</text></g>'
             f'<g class="in"{d(0.30)}><text class="sans" x="148" y="86" style="font-size:25px;font-weight:700;fill:var(--t1);letter-spacing:-.025em">Rincon Duarte</text></g>'
             f'<g clip-path="url(#ty)"><text x="148" y="112" style="font-size:10.5px;letter-spacing:.1em;fill:var(--dat)">DATA ENGINEER · APPLIED AI</text></g>'
             f'<g class="in"{d(0.9)}><circle class="dot-s blink" cx="152" cy="132" r="3.5"/>'
             f'<text x="162" y="136" style="font-size:9.5px;letter-spacing:.14em;fill:var(--sig)">DISPONIBLE · INMEDIATO</text></g>')
    # --- tickers (dos filas en sentidos opuestos)
    r1, c1 = marquee(["GCP", "BigQuery", "ETL/ELT", "APIs REST", "Python", "SQL", "SAS", "Data Quality", "Power BI", "Looker"], 164, "mq1", 26, False, "dat")
    r2, c2 = marquee(["Ollama", "vLLM", "MCP", "Laya", "RAG", "Agentic Workflows", "Scikit-Learn", "XGBoost", "Git", "GitHub Actions", "CI/CD"], 190, "mq2", 30, True, "sig")
    b.append(f'<g clip-path="url(#mq)" class="in"{d(0.5)}>{r1}{r2}</g>')
    # --- métricas (anillo 95 %, 250+, 2+ años)
    tiles = []
    for i, x in enumerate((24, 136, 248)):
        tiles.append(f'<g class="pop"{d(0.7 + i * 0.12)}><rect class="node" x="{x}" y="222" width="104" height="96" rx="10"/></g>')
    tiles.append(f'<g class="in"{d(1.0)}><circle cx="76" cy="256" r="22" fill="none" style="stroke:var(--s2)" stroke-width="5"/>'
                 f'<circle class="ringh" cx="76" cy="256" r="22" fill="none" stroke="url(#rg)" stroke-width="5" stroke-linecap="round" stroke-dasharray="138.2" stroke-dashoffset="6.9" transform="rotate(-90 76 256)"/>'
                 f'<text x="76" y="261" text-anchor="middle" style="font-size:13px;font-weight:800;fill:var(--t1)">95%</text>'
                 f'<text class="small" x="76" y="298" text-anchor="middle">reducción en</text><text class="small" x="76" y="309" text-anchor="middle">procesamiento</text></g>')
    tiles.append(f'<g class="in"{d(1.12)}><text class="sans" x="188" y="262" text-anchor="middle" style="font-size:25px;font-weight:800;fill:var(--dat);letter-spacing:-.02em">250+</text>'
                 f'<text class="small" x="188" y="298" text-anchor="middle">stakeholders</text><text class="small" x="188" y="309" text-anchor="middle">atendidos</text></g>')
    tiles.append(f'<g class="in"{d(1.24)}><text class="sans" x="300" y="262" text-anchor="middle" style="font-size:25px;font-weight:800;fill:var(--sig);letter-spacing:-.02em">2+</text>'
                 f'<text class="small" x="300" y="298" text-anchor="middle">años de datos</text><text class="small" x="300" y="309" text-anchor="middle">habilitados</text></g>')
    b.append("".join(tiles))
    # --- ventana del holograma 3D
    b.append(f'<g class="in"{d(0.15)}><rect x="368" y="10" width="316" height="316" rx="6" style="fill:var(--s0)"/>'
             f'<g clip-path="url(#hw)"><image href="{uri}" x="368" y="10" width="316" height="316" preserveAspectRatio="xMidYMid slice"/>'
             f'<rect class="scan2" x="368" y="10" width="316" height="60" fill="url(#sc)"/></g>'
             f'<rect x="368" y="10" width="316" height="316" rx="6" fill="none" style="stroke:var(--bd)"/>'
             f'<path class="pulse" d="M368 32V10h22M662 10h22v22M684 304v22h-22M390 326h-22v-22" fill="none" style="stroke:var(--sig)" stroke-width="2"/>'
             f'<text class="lbl" x="382" y="30" style="font-size:9px">VISUAL.CORE · 3D</text>'
             f'<circle class="dot-s blink" cx="670" cy="26" r="3"/>'
             f'<path class="sweep-x" d="M368 6h7l-3.5 6z" style="fill:var(--sig)"/></g>')
    css = f"""{c1}{c2}
.streak{{animation:streak 8s linear infinite}}
.scan{{animation:band 4.5s linear infinite}}
.scan2{{animation:band2 6s linear infinite}}
.ringh{{animation:ringh 1.8s cubic-bezier(.3,.6,.2,1) 1.1s backwards}}
.typing{{transform-box:fill-box;transform-origin:0 50%;animation:typing 1.6s steps(26) .5s backwards}}
.sweep-x{{animation:sx 7s cubic-bezier(.77,0,.175,1) infinite alternate}}
@keyframes streak{{to{{stroke-dashoffset:-1000}}}}
@keyframes band{{from{{transform:translateY(-30px)}}to{{transform:translateY(110px)}}}}
@keyframes band2{{from{{transform:translateY(-70px)}}to{{transform:translateY(330px)}}}}
@keyframes ringh{{from{{stroke-dashoffset:138.2}}}}
@keyframes typing{{from{{transform:scaleX(0)}}}}
@keyframes sx{{to{{transform:translateX(316px)}}}}"""
    return doc(W, H, "".join(b), "Andres Felipe Rincon Duarte, Data Engineer y Applied AI Engineer",
               "Retrato con anillos orbitales, nombre y estado disponible, tecnologías en carrusel, métricas (95 %, 250+, 2+ años) y un holograma 3D de partículas que se transforma en nube, red neuronal, servidor MCP y rostro.", css)


# ----------------------------------------------------------------------------- deck
def deck():
    W, H = 700, 330
    b = [f'<defs>{ARROW}{sphere_defs("sp1", "dat")}{sphere_defs("sp2", "sig")}</defs>',
         f'<rect class="card" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/>']
    # ---------- A. arquitectura de datos (isométrico)
    b.append(f'<g class="in"{d(0)}><rect x="24" y="22" width="6" height="6" rx="1.5" style="fill:var(--dat)"/><text class="lbl" x="38" y="29.5">01 · DATA.ARCHITECTURE</text></g>'
             f'<text class="ttl sans in" x="24" y="52"{d(0.06)}>Arquitectura de datos en GCP / BigQuery</text>')
    pill = "−95 % tiempos de procesamiento"
    pw = len(pill) * 6.3 + 22
    b.append(f'<g class="in"{d(0.2)}><rect x="{W - 24 - pw:.1f}" y="20" width="{pw:.1f}" height="22" rx="11" fill="none" style="stroke:var(--sigd)"/>'
             f'<text x="{W - 24 - pw / 2:.1f}" y="35" text-anchor="middle" style="font-size:10px;fill:var(--sig);font-weight:600">{pill}</text></g>')
    xs = [76 + i * 137 for i in range(5)]
    cy = 112
    b.append(f'<path class="ln flow" d="M{xs[0]} {cy - 6}H{xs[-1]}" style="opacity:.55"/>')
    b.append(f'<circle class="dot-s travel" cx="{xs[0]}" cy="{cy - 6}" r="3.5" style="--td:{xs[-1] - xs[0]}px;--tt:5.4s"/>')
    spec = [("SOURCES", "Qualtrics · APIs", "bds"), ("INGEST", "Python · SAS", "bds"), ("WAREHOUSE", "BigQuery · GCP", "dat"),
            ("QUALITY GATE", "Python / SQL", "sig"), ("SERVE", "Looker · Power BI", "bds")]
    for i, (x, (lab, nm, ac)) in enumerate(zip(xs, spec)):
        b.append(f'<g class="pop"{d(0.25 + i * 0.12)}>{iso_cube(x, cy, 24, ac, delay=i * 0.55)}</g>')
        b.append(f'<g class="in"{d(0.5 + i * 0.1)}><text class="nl" x="{x}" y="{cy + 34}" text-anchor="middle" style="font-size:8.5px">{lab}</text>'
                 f'<text class="nt sans" x="{x}" y="{cy + 48}" text-anchor="middle" style="font-size:11px">{nm}</text></g>')
    b.append(f'<line x1="24" y1="176" x2="{W - 24}" y2="176" style="stroke:var(--bd)"/>')
    # ---------- B. tres módulos
    cols = [24, 246, 468]
    cw = 208
    # MCP
    x = cols[0]
    b.append(f'<g class="in"{d(0.7)}><rect x="{x}" y="192" width="6" height="6" rx="1.5" style="fill:var(--sig)"/><text class="lbl" x="{x + 14}" y="199.5">02 · LOCAL.MCP</text>'
             f'<text class="sans" x="{x}" y="218" style="font-size:13px;font-weight:650;fill:var(--t1)">Servidores MCP locales</text>'
             f'<text class="sans" x="{x}" y="233" style="font-size:10.5px;fill:var(--t2)">LLMs locales ↔ bases de datos y APIs</text></g>')
    b.append(f'<path class="ln flow" d="M{x + 62} 276L{x + 136} 262M{x + 62} 276L{x + 136} 290" marker-end="url(#ah)"/>')
    b.append(f'<circle class="dot-s travel" cx="{x + 62}" cy="276" r="3" style="--td:72px;--tt:2.6s"/>')
    b.append(f'<g class="pop"{d(0.9)}>{iso_cube(x + 30, 290, 18, "dat", h=10, delay=0)}{iso_cube(x + 30, 276, 18, "dat", h=10, delay=0, shadow=False, float_=False)}</g>')
    b.append(f'<g class="pop"{d(1.0)}>{iso_cube(x + 160, 266, 13, "sig", delay=0.8)}</g><g class="pop"{d(1.1)}>{iso_cube(x + 160, 294, 13, "bds", delay=1.4)}</g>')
    b.append(f'<g class="in"{d(1.2)}><text class="small" x="{x + 30}" y="322" text-anchor="middle">Ollama · vLLM</text><text class="small" x="{x + 172}" y="322" text-anchor="middle">DB · APIs</text></g>')
    # ML (barras 3D que crecen con resorte)
    x = cols[1]
    b.append(f'<line x1="{x - 12}" y1="190" x2="{x - 12}" y2="{H - 14}" style="stroke:var(--bd)"/>')
    b.append(f'<g class="in"{d(0.8)}><rect x="{x}" y="192" width="6" height="6" rx="1.5" style="fill:var(--dat)"/><text class="lbl" x="{x + 14}" y="199.5">03 · ML.MODELS</text>'
             f'<text class="sans" x="{x}" y="218" style="font-size:13px;font-weight:650;fill:var(--t1)">Modelos de ML</text>'
             f'<text class="sans" x="{x}" y="233" style="font-size:10.5px;fill:var(--t2)">Scikit-Learn · XGBoost · Laya (OSS)</text></g>')
    for i, (hgt, ac) in enumerate([(46, "dat"), (24, "dat"), (12, "bds")]):
        bx = x + 26 + i * 40
        b.append(f'<g class="grow-y" style="animation-delay:{1.0 + i * 0.15:.2f}s">{iso_cube(bx, 296, 15, ac, h=hgt, shadow=False, float_=False)}</g>')
    b.append(f'<g class="in"{d(1.3)}><text class="small" x="{x + 26}" y="322" text-anchor="middle">A</text><text class="small" x="{x + 66}" y="322" text-anchor="middle">B</text>'
             f'<text class="small" x="{x + 106}" y="322" text-anchor="middle">C</text><text class="small" x="{x + 206}" y="322" text-anchor="end">// ilustrativo</text></g>')
    # REPO (grafo con esferas)
    x = cols[2]
    b.append(f'<line x1="{x - 12}" y1="190" x2="{x - 12}" y2="{H - 14}" style="stroke:var(--bd)"/>')
    b.append(f'<g class="in"{d(0.9)}><rect x="{x}" y="192" width="6" height="6" rx="1.5" style="fill:var(--sig)"/><text class="lbl" x="{x + 14}" y="199.5">04 · REPO.ENGINEERING</text>'
             f'<text class="sans" x="{x}" y="218" style="font-size:13px;font-weight:650;fill:var(--t1)">Ingeniería de repositorios</text>'
             f'<text class="sans" x="{x}" y="233" style="font-size:10.5px;fill:var(--t2)">Commits semánticos · CI/CD · Actions</text></g>')
    b.append(f'<path class="ln draw" pathLength="1" stroke-dasharray="1" d="M{x + 4} 292H{x + 204}" style="animation-delay:1s"/>')
    b.append(f'<path class="ln-sig draw" pathLength="1" stroke-dasharray="1" d="M{x + 48} 292C{x + 58} 292 {x + 62} 268 {x + 76} 268H{x + 138}C{x + 152} 268 {x + 156} 292 {x + 168} 292" style="animation-delay:1.3s"/>')
    for i, (cx_, cy_, grad, r) in enumerate([(4, 292, "sp1", 5), (48, 292, "sp1", 5), (84, 268, "sp1", 5), (112, 268, "sp1", 5), (138, 268, "sp1", 5), (168, 292, "sp2", 6.5), (204, 292, "sp1", 5)]):
        b.append(f'<g class="pop"{d(1.2 + i * 0.12)}><g class="bob" style="animation-delay:-{i * 0.5:.1f}s"><circle cx="{x + cx_}" cy="{cy_}" r="{r}" fill="url(#{grad})"/></g></g>')
    b.append(f'<g class="in"{d(1.8)}><text class="small" x="{x + 4}" y="314">main</text><text class="small" x="{x + 112}" y="256" text-anchor="middle">feature</text>'
             f'<text class="small" x="{x + 168}" y="314" text-anchor="middle">merge</text></g>')
    return doc(W, H, "".join(b), "Arquitectura de datos, MCP, ML e ingeniería de repositorios",
               "Pipeline de datos con bloques isométricos (fuentes, ingesta, BigQuery, control de calidad, consumo), servidores MCP locales, modelos de ML y un grafo de commits.")


if __name__ == "__main__":
    prev_png = None
    if PREVIEW:
        # el rasterizador de vista previa no decodifica WebP animado: usa un cuadro fijo del holograma
        from PIL import Image
        pathlib.Path(PREVIEW).mkdir(parents=True, exist_ok=True)
        g = Image.open(A / "visual_core.webp")
        g.seek(min(155, g.n_frames - 1))
        prev_png = pathlib.Path(PREVIEW) / "_holo_frame.png"
        g.convert("RGB").save(prev_png)
    for name, svg in [("hero.svg", hero(prev_png)), ("deck.svg", deck())]:
        out = A / name
        if name == "hero.svg" and prev_png:      # el archivo final siempre lleva el WebP real
            save(A / "_tmp_prev.svg", svg, PREVIEW)
            (A / "_tmp_prev.svg").unlink()
            pathlib.Path(PREVIEW, "_tmp_prev.png").rename(pathlib.Path(PREVIEW, "hero.png"))
            svg = hero()
        save(out, svg, PREVIEW if name != "hero.svg" else None)
        print(f"  {name:10s}{len(svg) / 1024:8.1f} KB")
