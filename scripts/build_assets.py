#!/usr/bin/env python3
"""
build_assets.py -- Genera los componentes SVG del README a partir de los tokens de diseño.

    python scripts/design_tokens.py            # 1) tokens (paleta OKLCH + verificación WCAG)
    python scripts/build_portrait.py foto.png  # 2) retrato vectorial de puntos
    python scripts/build_assets.py             # 3) este script
    python scripts/generate_hologram.py --photo foto.png   # 4) holograma de partículas (GIF)

Salida en assets/: header.svg, avatar.svg, avatar_frame.svg, mod_data.svg, mod_mcp.svg, mod_ml.svg, mod_repo.svg
Opcional:  --preview DIR   rasteriza PNG para revisar (requiere cairosvg; ignora animaciones).

Nota: GitHub elimina <svg> en línea dentro del Markdown, por eso cada componente es un archivo .svg
referenciado con <img>. Los fondos son transparentes y los colores salen de variables CSS que cambian
con prefers-color-scheme.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ds import ROOT, chips, d, doc, save  # noqa: E402

A = ROOT / "assets"
PREVIEW = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
MARKER = ('<defs><marker id="ah" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
          '<path d="M0 0L7 3.5L0 7z" fill="var(--dat)"/></marker></defs>')


# ----------------------------------------------------------------------------- header
def header():
    W, H = 580, 100
    body = f"""
<g class="in"{d(0.05)}><text class="sans" x="2" y="38" style="font-size:29px;font-weight:700;fill:var(--t1);letter-spacing:-.025em">Andres Felipe Rincon Duarte</text></g>
<g class="in"{d(0.18)}><text x="2" y="62" style="font-size:12px;letter-spacing:.1em;fill:var(--dat)">DATA ENGINEER · APPLIED AI ENGINEER</text></g>
<g class="in"{d(0.30)}>
  <circle class="dot-s blink" cx="6" cy="82" r="3.5"/>
  <text x="18" y="86" style="font-size:10px;letter-spacing:.14em;fill:var(--sig)">DISPONIBLE · INMEDIATO</text>
  <text x="{W - 2}" y="86" text-anchor="end" style="font-size:10px;fill:var(--t3)">BOGOTÁ D.C. · REMOTO · HÍBRIDO</text>
</g>
<path class="draw" pathLength="1" stroke-dasharray="1" d="M2 95.5H{W - 2}" style="stroke:var(--bd);stroke-width:1;animation-delay:.4s"/>"""
    return doc(W, H, body, "Andres Felipe Rincon Duarte",
               "Data Engineer y Applied AI Engineer. Disponible de inmediato. Bogotá D.C., remoto o híbrido.")


# ----------------------------------------------------------------------------- avatar
def avatar(with_portrait):
    S, m = 320, 26
    inner = S - 2 * m
    p = []
    p.append('<defs><clipPath id="pc"><rect x="%d" y="%d" width="%d" height="%d"/></clipPath>'
             '<filter id="gl" x="-3%%" y="-3%%" width="106%%" height="106%%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
             '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             '<linearGradient id="sc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--dat)" stop-opacity="0"/>'
             '<stop offset=".5" stop-color="var(--dat)" stop-opacity=".22"/><stop offset="1" stop-color="var(--dat)" stop-opacity="0"/>'
             '</linearGradient></defs>' % (m, m, inner, inner))
    if with_portrait:
        frag = (A / "portrait.frag").read_text()
        bright = (A / "portrait_bright.frag").read_text()
        k = inner / 330
        p.append(f'<rect x="{m}" y="{m}" width="{inner}" height="{inner}" fill="var(--s0)"/>')
        p.append(f'<g clip-path="url(#pc)"><g class="in"{d(0.1)}><g transform="translate({m},{m + (inner - 320 * k) / 2:.1f}) scale({k:.4f})" '
                 f'fill="none" stroke-linecap="round">{frag}<g filter="url(#gl)">{bright}</g></g></g>'
                 f'<rect class="scanband" x="{m}" y="{m}" width="{inner}" height="60" fill="url(#sc)"/></g>')
    # escalas perimetrales: menor cada 2 %, mayor cada 10 % (con numeración arriba e izquierda)
    ticks = []
    for i in range(0, 51):
        pos = m + inner * i / 50
        major = i % 5 == 0
        L = 6 if major else 3
        ticks.append(f'M{pos:.1f} {m - 2}v{-L}M{pos:.1f} {m + inner + 2}v{L}M{m - 2} {pos:.1f}h{-L}M{m + inner + 2} {pos:.1f}h{L}')
    p.append(f'<path d="{"".join(ticks)}" fill="none" stroke="var(--bds)" stroke-width="1" opacity=".75"/>')
    for i in range(0, 11):
        pos = m + inner * i / 10
        p.append(f'<text x="{pos:.1f}" y="{m - 10}" text-anchor="middle" style="font-size:7px;fill:var(--t3)">{i * 10:02d}</text>')
        p.append(f'<text x="{m - 10}" y="{pos + 2.5:.1f}" text-anchor="end" style="font-size:7px;fill:var(--t3)">{i * 10:02d}</text>')
    # borde de placa + luz perimetral lenta
    p.append(f'<rect x="{m}" y="{m}" width="{inner}" height="{inner}" fill="none" stroke="var(--bd)" stroke-width="1"/>')
    p.append(f'<rect class="orbit" x="{m}" y="{m}" width="{inner}" height="{inner}" fill="none" stroke="var(--dat)" stroke-width="1.5" '
             f'stroke-linecap="round" pathLength="1000" stroke-dasharray="46 954"/>')
    # anclajes: corchetes de esquina (señal) + retículas en el centro de cada borde
    L = 22
    br = (f'M{m} {m + L}V{m}H{m + L}M{m + inner - L} {m}H{m + inner}V{m + L}'
          f'M{m + inner} {m + inner - L}V{m + inner}H{m + inner - L}M{m + L} {m + inner}H{m}V{m + inner - L}')
    p.append(f'<path class="pulse" d="{br}" fill="none" stroke="var(--sig)" stroke-width="2" stroke-linecap="square"/>')
    c = m + inner / 2
    p.append(f'<path d="M{c - 4} {m}h8M{c} {m - 4}v8M{c - 4} {m + inner}h8M{c} {m + inner - 4}v8'
             f'M{m} {c - 4}v8M{m - 4} {c}h8M{m + inner} {c - 4}v8M{m + inner - 4} {c}h8" stroke="var(--bds)" stroke-width="1" fill="none"/>')
    # marcadores de barrido (resorte, ida y vuelta): uno por escala
    p.append(f'<path class="sweep-x" d="M{m - 3.5} {m - 20}h7l-3.5 6z" fill="var(--sig)"/>')
    p.append(f'<path class="sweep-y" d="M{m - 20} {m - 3.5}v7l6 -3.5z" fill="var(--sig)"/>')
    # metadatos
    p.append(f'<text x="{m}" y="{S - 8}" style="font-size:8px;letter-spacing:.14em;fill:var(--t3)">ID://AFELIPERD</text>')
    p.append(f'<text x="{m + inner - 12}" y="{S - 8}" text-anchor="end" style="font-size:8px;letter-spacing:.1em;fill:var(--t3)">4.71N 74.07W</text>')
    p.append(f'<circle class="dot-s blink" cx="{m + inner - 4}" cy="{S - 11}" r="2.5"/>')
    css = f"""
.sweep-x{{animation:sx 7s cubic-bezier(.77,0,.175,1) infinite alternate}}
.sweep-y{{animation:sy 7s cubic-bezier(.77,0,.175,1) -3.5s infinite alternate}}
.orbit{{animation:orbit 11s linear infinite;opacity:.8}}
.scanband{{animation:band 6s linear infinite}}
@keyframes sx{{to{{transform:translateX({inner}px)}}}}
@keyframes sy{{to{{transform:translateY({inner}px)}}}}
@keyframes orbit{{to{{stroke-dashoffset:-1000}}}}
@keyframes band{{from{{transform:translateY(-70px)}}to{{transform:translateY({inner + 10}px)}}}}"""
    return doc(S, S, "".join(p), "Retrato de Andres Felipe Rincon Duarte" if with_portrait else "Marco de avatar",
               "Retrato hecho de puntos dentro de un marco técnico con escalas numéricas perimetrales." if with_portrait
               else "Marco vectorial con escalas numéricas, corchetes de anclaje y marcadores animados.", css)


# ----------------------------------------------------------------------------- módulos
def card(W, H, label, accent, title, desc_lines):
    out = [f'<rect class="card" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/>',
           f'<g class="in"{d(0.0)}><rect x="24" y="26" width="6" height="6" rx="1.5" fill="var(--{accent})"/>'
           f'<text class="lbl" x="38" y="33.5">{label}</text></g>',
           f'<text class="ttl sans in" x="24" y="60"{d(0.06)}>{title}</text>']
    for i, ln in enumerate(desc_lines):
        out.append(f'<text class="dsc sans in" x="24" y="{80 + i * 17}"{d(0.12 + i * 0.05)}>{ln}</text>')
    return "".join(out)


def node(x, y, w, h, label, name, kind="node", delay=0.3, fs=12):
    cx = x + w / 2
    ly = y + h / 2 - 3 if label else y + h / 2 + 4
    s = f'<g class="pop"{d(delay)}><rect class="{kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
    if label:
        s += f'<text class="nl" x="{cx}" y="{y + h / 2 - 5}" text-anchor="middle">{label}</text>'
        s += f'<text class="nt sans" x="{cx}" y="{y + h / 2 + 12}" text-anchor="middle" style="font-size:{fs}px">{name}</text>'
    else:
        s += f'<text class="nt sans" x="{cx}" y="{ly}" text-anchor="middle">{name}</text>'
    return s + "</g>"


def mod_data():
    W, H = 904, 268
    b = [MARKER, card(W, H, "01 · DATA.ARCHITECTURE", "dat", "Arquitectura de datos en GCP / BigQuery",
                      ["Pipelines ETL/ELT: de la ingesta segura vía API al consumo analítico, con calidad validada."])]
    pill = "−95 % tiempos de procesamiento"
    pw = len(pill) * 6.4 + 22
    b.append(f'<g class="in"{d(0.2)}><rect x="{W - 24 - pw:.1f}" y="20" width="{pw:.1f}" height="22" rx="11" fill="none" '
             f'stroke="var(--sigd)"/><text x="{W - 24 - pw / 2:.1f}" y="35" text-anchor="middle" style="font-size:10.5px;fill:var(--sig);font-weight:600">{pill}</text></g>')
    xs = [22 + i * 180 for i in range(5)]
    # paquete de datos (detrás de los nodos: solo se ve "saltando" entre etapas)
    b.append(f'<circle class="dot-s travel" cx="22" cy="150" r="3.5" style="--td:858px;--tt:5.2s"/>')
    spec = [("SOURCES", "Qualtrics · APIs REST", "node"), ("INGEST", "Python · SAS", "node"),
            ("WAREHOUSE", "BigQuery · GCP", "node-data"), ("QUALITY GATE", "Python / SQL", "node"),
            ("SERVE", "Looker · Power BI", "node")]
    for i, (x, (lab, nm, kind)) in enumerate(zip(xs, spec)):
        if i < 4:
            b.append(f'<path class="ln flow" d="M{x + 144 + 3} 150H{xs[i + 1] - 6}" marker-end="url(#ah)"/>')
        b.append(node(x, 120, 144, 60, lab, nm, kind, 0.25 + i * 0.12, 11))
    b.append(f'<text class="small in" x="24" y="208"{d(0.9)}>Token ID / API REST · OAuth2 · actualización diaria en Looker · procesos documentados en runbooks</text>')
    tg, _ = chips(24, 222, ["GCP", "BigQuery", "ETL/ELT", "APIs REST", "OAuth2", "Python", "SAS", "SQL", "Data Quality"], 880, "bd")
    b.append(tg)
    return doc(W, H, "".join(b), "Arquitectura de datos en GCP y BigQuery",
               "Flujo: fuentes (Qualtrics, APIs REST), ingesta con Python y SAS, BigQuery en GCP, control de calidad en Python y SQL, consumo en Looker y Power BI.")


def mod_mcp():
    W, H = 292, 268
    b = [MARKER, card(W, H, "02 · LOCAL.MCP", "sig", "Servidores MCP locales",
                      ["LLMs en tu propia infraestructura,", "conectados a bases de datos y APIs."])]
    b.append('<circle class="dot-s travel" cx="20" cy="158" r="3" style="--td:236px;--tt:3.4s"/>')
    b.append('<path class="ln flow" d="M114 158H124" marker-end="url(#ah)"/>')
    b.append('<path class="ln flow" d="M190 152L202 140" marker-end="url(#ah)"/><path class="ln flow" d="M190 164L202 176" marker-end="url(#ah)"/>')
    b.append(node(20, 134, 94, 48, "LLM LOCAL", "Ollama · vLLM", "node-data", 0.25, 10.5))
    b.append(node(128, 130, 62, 56, "MCP", "server", "node-hot", 0.37))
    b.append(node(204, 122, 66, 28, "", "DB", "node", 0.49))
    b.append(node(204, 166, 66, 28, "", "APIs", "node", 0.55))
    tg, _ = chips(24, 214, ["100 % local", "Ollama", "vLLM", "MCP"], 270, "bd")
    b.append(tg)
    return doc(W, H, "".join(b), "Servidores MCP locales",
               "Un LLM local (Ollama, vLLM) se conecta mediante un servidor MCP a bases de datos y APIs.")


def mod_ml():
    W, H = 292, 268
    b = [card(W, H, "03 · ML.MODELS", "dat", "Modelos de Machine Learning",
              ["Scikit-Learn y XGBoost; Laya (open source)", "para categorizar texto y sentimiento."])]
    for i, (lab, w, col) in enumerate([("A", 150, "dat"), ("B", 34, "datd"), ("C", 16, "bds")]):
        y = 126 + i * 20
        b.append(f'<g class="in"{d(0.25 + i * 0.1)}><text class="small" x="24" y="{y + 7.5}">{lab}</text>'
                 f'<rect x="40" y="{y}" width="196" height="9" rx="4.5" fill="var(--s2)"/></g>')
        b.append(f'<rect class="bar" x="40" y="{y}" width="{w}" height="9" rx="4.5" fill="var(--{col})"{d(0.45 + i * 0.12)}/>')
    b.append(f'<text class="small in" x="270" y="124" text-anchor="end"{d(0.5)}>p(clase)</text>')
    b.append(f'<text class="small in" x="24" y="200"{d(0.7)}>// ilustrativo: salidas tipadas con probabilidades</text>')
    tg, _ = chips(24, 214, ["Scikit-Learn", "XGBoost", "Laya"], 270, "bd")
    b.append(tg)
    return doc(W, H, "".join(b), "Modelos de Machine Learning",
               "Scikit-Learn y XGBoost para ML clásico; Laya, modelo de decisión de código abierto, para categorizar texto y sentimiento. Gráfico ilustrativo.")


def mod_repo():
    W, H = 292, 268
    b = [card(W, H, "04 · REPO.ENGINEERING", "sig", "Ingeniería de repositorios",
              ["Arquitectura modular, commits semánticos,", "CHANGELOG automático y CI/CD."])]
    b.append('<path class="ln draw" pathLength="1" stroke-dasharray="1" d="M22 168H270" style="animation-delay:.2s"/>')
    b.append('<path class="ln-sig draw" pathLength="1" stroke-dasharray="1" d="M78 168C90 168 96 138 112 138H190C206 138 212 168 226 168" style="animation-delay:.5s"/>')
    commits = [(22, 168, "dat"), (78, 168, "dat"), (126, 138, "dat"), (158, 138, "dat"), (190, 138, "dat"), (226, 168, "sig"), (270, 168, "dat")]
    for i, (x, y, col) in enumerate(commits):
        r = 5.5 if col == "sig" else 4.2
        b.append(f'<circle class="pop" cx="{x}" cy="{y}" r="{r}" fill="var(--s0)" stroke="var(--{col})" stroke-width="1.6"{d(0.4 + i * 0.12)}/>')
    b.append(f'<text class="small in" x="22" y="190"{d(1.0)}>main</text>')
    b.append(f'<text class="small in" x="126" y="124"{d(1.0)}>feature</text>')
    b.append(f'<text class="small in" x="226" y="190" text-anchor="middle"{d(1.0)}>merge</text>')
    tg, _ = chips(24, 214, ["Git", "GitHub Actions", "CI/CD", "Commits semánticos"], 270, "bd")
    b.append(tg)
    return doc(W, H, "".join(b), "Ingeniería de repositorios",
               "Grafo de ramas: una rama de feature se fusiona en main; flujo con Git, GitHub Actions y CI/CD.")


if __name__ == "__main__":
    A.mkdir(exist_ok=True)
    for name, svg in [("header.svg", header()), ("avatar.svg", avatar(True)), ("avatar_frame.svg", avatar(False)),
                      ("mod_data.svg", mod_data()), ("mod_mcp.svg", mod_mcp()), ("mod_ml.svg", mod_ml()), ("mod_repo.svg", mod_repo())]:
        save(A / name, svg, PREVIEW)
        print(f"  {name:18s}{len(svg) / 1024:6.1f} KB")
