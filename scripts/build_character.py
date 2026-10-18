#!/usr/bin/env python3
"""
build_character.py -- Personaje de marca de @AFelipeRD, modelado en 3D al estilo de los juegos de Mario (referencia: Luigi).

Cómo está hecho (igual que un modelo 3D, pero sin software 3D):
  1. MODELO: formas redondeadas (elipsoides, cápsulas, cajas redondeadas) combinadas con "smooth union"
     -> las superficies se funden como el material blando de los personajes de plataformas.
  2. RENDER: ray-marching sobre campos de distancia con luz principal arriba-izquierda, luz de relleno fría,
     luz de contorno, oclusión ambiental y brillo especular. Cámara ortográfica con 6 grados de inclinación
     hacia abajo (se ve la parte superior de la visera). Bordes suavizados por distancia.
  3. RASGOS DE LA FOTO: gafas rectangulares de marco grueso gris humo con lunas de reflejo azul, cejas gruesas,
     ojos castaños, bigote fino de puntas caídas, perilla vertical y barba de contorno de mandíbula. Se pintan
     como "texturas" sobre el modelo, con la misma iluminación y recortadas por material.
  4. PIXEL ART: sale del MISMO render (promedio por área + paleta limitada + contorno de 1 px), por eso la cara
     es idéntica en la versión 3D y en la de pixeles.

Salidas (assets/), todas ESTÁTICAS (el movimiento vive en el carrusel del holograma):
    character_3d.png            render completo en T-pose (RGBA)
    character_bust.png          busto en primer plano (RGBA)
    avatar_pixel.png            foto de perfil de GitHub, pixel art (512 x 512)
    character_pixel_full.png    cuerpo completo en pixel art
    character_color.png / character_depth.png   entradas del holograma 3D (generate_hologram.py)

Uso:  python scripts/build_character.py          (pip install numpy pillow cairosvg)
      SCALE=120 python scripts/build_character.py   (vista rápida de baja resolución)
      PART=bust python scripts/build_character.py    (solo el busto; PART=full solo el cuerpo)
"""
import io
import json
import math
import os
import pathlib
import sys

try:
    import cairosvg
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("Faltan dependencias:  pip install numpy pillow cairosvg")

ROOT = pathlib.Path(__file__).resolve().parent.parent
A = ROOT / "assets"
tok = json.loads((A / "tokens.json").read_text())
BG = tok["surface-1"]
INK = (10, 13, 18)
F32 = np.float32

# ----------------------------------------------------------------------------- campos de distancia
v3 = lambda *a: np.array(a, F32)


def length(v):
    return np.sqrt((v * v).sum(-1))


def ellipsoid(c, r):
    c, r = v3(*c), v3(*r)

    def f(P):
        p = P - c
        k0 = length(p / r)
        k1 = length(p / (r * r))
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
    return f


def capsule(a, b, r, r2=None):
    a, b = v3(*a), v3(*b)
    ba = b - a
    bb = float((ba * ba).sum())

    def f(P):
        pa = P - a
        h = np.clip((pa @ ba) / bb, 0, 1)
        rr = r if r2 is None else r + (r2 - r) * h
        return length(pa - h[:, None] * ba) - rr
    return f


def round_box(c, b, r):
    c, b = v3(*c), v3(*b)

    def f(P):
        q = np.abs(P - c) - b
        return length(np.maximum(q, 0)) + np.minimum(np.maximum(q[:, 0], np.maximum(q[:, 1], q[:, 2])), 0) - r
    return f


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def union(fs, k):
    def f(P):
        d = fs[0](P)
        for g in fs[1:]:
            d = smin(d, g(P), k)
        return d
    return f


def cut_below_y(f, y):                      # conserva lo que está por encima de y (resta un semiespacio)
    return lambda P: np.maximum(f(P), y - P[:, 1])


def cut_behind_z(f, z):                     # conserva lo que está delante de z
    return lambda P: np.maximum(f(P), z - P[:, 2])


def bent_brim():
    e = ellipsoid((0, 2.50, 0.44), (0.49, 0.040, 0.31))

    def f(P):
        Q = P.copy()
        Q[:, 1] = P[:, 1] + 0.42 * P[:, 0] ** 2 + 0.09 * np.maximum(P[:, 2] - 0.12, 0)   # curva en los lados y cae al frente
        return np.maximum(e(Q), 0.10 - P[:, 2]) * 0.8
    return f


# ----------------------------------------------------------------------------- escena (unidades: 1 = alto de la cabeza)
# materiales: 0 piel, 1 camiseta blanca, 2 jogger, 3 gorra negra, 4 tenis, 5 suela, 6..9 cuentas
ALB = np.array([(0.88, 0.67, 0.52), (0.96, 0.96, 0.94), (0.11, 0.13, 0.18), (0.075, 0.085, 0.115), (0.075, 0.085, 0.105),
                (0.96, 0.95, 0.91), (0.97, 0.68, 0.25), (0.95, 0.96, 0.96), (0.37, 0.79, 0.85), (0.06, 0.07, 0.09)], F32)
SPEC = np.array([0.10, 0.035, 0.22, 0.30, 0.45, 0.25, 0.5, 0.5, 0.5, 0.5], F32)
SHIN = np.array([18, 14, 24, 70, 30, 20, 40, 40, 40, 40], F32)


def build_scene():
    G = []
    # --- piel: cabeza redonda con mandíbula, orejas, nariz, cuello, antebrazos y manos
    skin = [ellipsoid((0, 2.30, 0), (0.50, 0.46, 0.46)), ellipsoid((0, 2.07, 0.03), (0.435, 0.32, 0.40)),
            ellipsoid((0, 2.115, 0.50), (0.118, 0.105, 0.118)),
            ellipsoid((-0.505, 2.27, -0.02), (0.06, 0.12, 0.07)), ellipsoid((0.505, 2.27, -0.02), (0.06, 0.12, 0.07)),
            capsule((0, 1.74, 0), (0, 1.95, 0), 0.17)]
    for s in (-1, 1):
        skin += [capsule((s * 0.74, 1.62, 0), (s * 1.14, 1.62, 0), 0.115, 0.098),
                 ellipsoid((s * 1.29, 1.62, 0.0), (0.145, 0.062, 0.12))]
        for ang in (-34, -12, 11, 33):                       # dedos abiertos hacia afuera (como los guantes de Luigi)
            a = math.radians(ang)
            skin.append(capsule((s * 1.34, 1.62, 0.02 * math.sin(a) * 4), (s * (1.34 + 0.19 * math.cos(a)), 1.62, 0.19 * math.sin(a) + 0.02 * math.sin(a) * 4), 0.033, 0.026))
        skin.append(capsule((s * 1.28, 1.62, 0.07), (s * 1.35, 1.62, 0.27), 0.040, 0.030))
    G.append((0, union(skin, 0.06)))
    # --- camiseta blanca oversize
    tee = [round_box((0, 1.38, 0), (0.25, 0.30, 0.165), 0.15), ellipsoid((0, 1.12, 0), (0.33, 0.14, 0.24))]
    for s in (-1, 1):
        tee += [capsule((s * 0.26, 1.62, 0), (s * 0.75, 1.62, 0), 0.15, 0.145), ellipsoid((s * 0.73, 1.62, 0), (0.07, 0.16, 0.16))]
    G.append((1, union(tee, 0.07)))
    # --- joggers
    pants = [ellipsoid((0, 0.96, 0), (0.37, 0.21, 0.26))]
    for s in (-1, 1):
        pants += [capsule((s * 0.17, 0.95, 0), (s * 0.17, 0.33, 0), 0.17, 0.155), ellipsoid((s * 0.17, 0.30, 0), (0.19, 0.075, 0.19))]
    G.append((2, union(pants, 0.05)))
    # --- tenis negros con suela blanca
    shoe, sole = [], []
    for s in (-1, 1):
        shoe += [ellipsoid((s * 0.19, 0.18, 0.10), (0.205, 0.15, 0.35)), ellipsoid((s * 0.19, 0.15, 0.29), (0.18, 0.115, 0.17))]
        sole.append(ellipsoid((s * 0.19, 0.06, 0.10), (0.215, 0.07, 0.375)))
    G.append((4, union(shoe, 0.04)))
    G.append((5, union(sole, 0.03)))
    # --- gorra negra al frente (cúpula + visera curva + botón)
    dome = cut_below_y(ellipsoid((0, 2.58, -0.02), (0.525, 0.40, 0.515)), 2.50)
    G.append((3, union([dome, bent_brim(), ellipsoid((0, 2.985, -0.02), (0.045, 0.04, 0.045))], 0.02)))
    # --- manilla de cuentas (muñeca izquierda del dibujo)
    for i in range(10):
        ph = 2 * math.pi * i / 10
        G.append((6 + i % 4, ellipsoid((-1.00, 1.62 + 0.118 * math.cos(ph), 0.118 * math.sin(ph)), (0.03, 0.03, 0.03))))
    return G


SCENE = build_scene()


def sdf(P, want_mat=False):
    best, mat = None, None
    for m, f in SCENE:
        d = f(P)
        if best is None:
            best = d
            mat = np.full(len(P), m, np.int8) if want_mat else None
        else:
            if want_mat:
                mat = np.where(d < best, m, mat).astype(np.int8)
            best = np.minimum(best, d)
    return (best, mat) if want_mat else best


# ----------------------------------------------------------------------------- cámara y render
class Cam:
    def __init__(self, cx, cy, hw, hh, S, pitch_deg=6.0):
        self.cx, self.cy, self.hw, self.hh, self.S = cx, cy, hw, hh, S
        self.W, self.H = int(round(2 * hw * S)), int(round(2 * hh * S))
        p = math.radians(pitch_deg)
        self.cp, self.sp = math.cos(p), math.sin(p)
        self.d = v3(0, -self.sp, -self.cp)                    # dirección de visión (mirando hacia abajo)
        self.ey = v3(0, self.cp, -self.sp)
        self.T = v3(cx, cy, 0)

    def px(self, x, y, z):
        yv = (y - self.cy) * self.cp - z * self.sp
        return (x - self.cx + self.hw) * self.S, (self.hh - yv) * self.S


KEY = v3(-0.55, 0.75, 0.62)
KEY /= np.linalg.norm(KEY)
FILL = v3(0.75, 0.20, 0.55)
FILL /= np.linalg.norm(FILL)


def shade_points(P, d):
    dist, mat = sdf(P, True)
    e = 0.0065                                 # normales más suaves (evita ondas del SDF aproximado)
    n = np.zeros_like(P)
    for k in ((1, -1, -1), (-1, -1, 1), (-1, 1, -1), (1, 1, 1)):
        kk = v3(*k)
        n += kk * sdf(P + kk * e)[:, None]
    n /= np.maximum(length(n), 1e-6)[:, None]
    ao = np.ones(len(P), F32)
    for h, w in ((0.035, 1.0), (0.08, 0.7), (0.15, 0.45)):
        ao -= 0.42 * w * np.clip(h - sdf(P + n * h), 0, None) / h * 0.5
    ao = np.clip(ao, 0.25, 1)
    albedo, ks, sh = ALB[mat], SPEC[mat], SHIN[mat]
    ndl = n @ KEY
    half = (ndl * 0.5 + 0.5) ** 1.7
    fill = np.clip(n @ FILL, 0, 1)
    V = -d
    rim = (1 - np.clip(n @ V, 0, 1)) ** 3
    light = (0.34 + 0.72 * half) * ao + 0.20 * fill * ao
    hv = KEY + V
    hv = hv / np.linalg.norm(hv)
    spec = np.clip(n @ hv, 0, 1) ** sh * ks * (0.35 + 0.65 * ao)
    col = albedo * light[:, None] * v3(1.0, 0.985, 0.95)
    col = col + rim[:, None] * v3(0.10, 0.17, 0.24) * 0.9 + spec[:, None]
    return np.clip(col, 0, 1), light, mat


def render(cam, chunk=50000):
    H, W, S = cam.H, cam.W, cam.S
    u = (np.arange(W) + 0.5) / S - cam.hw
    v = cam.hh - (np.arange(H) + 0.5) / S
    UU, VV = np.meshgrid(u, v)
    ex = v3(1, 0, 0)
    O_all = cam.T + UU.reshape(-1, 1) * ex + VV.reshape(-1, 1) * cam.ey - 7.0 * cam.d
    N = O_all.shape[0]
    color = np.zeros((N, 3), F32)
    light = np.zeros(N, F32)
    mat = np.full(N, -1, np.int8)
    alpha = np.zeros(N, F32)
    depth = np.zeros(N, F32)
    for s0 in range(0, N, chunk):
        O = O_all[s0:s0 + chunk]
        n = len(O)
        t = np.zeros(n, F32)
        dmin = np.full(n, 1e9, F32)
        Pm = O.copy()
        tm = np.zeros(n, F32)
        act = np.arange(n)
        for _ in range(110):
            P = O[act] + t[act, None] * cam.d
            dist = sdf(P) * 0.9
            better = dist < dmin[act]
            ia = act[better]
            dmin[ia] = dist[better]
            Pm[ia] = P[better]
            tm[ia] = t[act][better]
            t[act] += np.maximum(dist, 0.0006)
            keep = (dist > 0.0006) & (t[act] < 14)
            act = act[keep]
            if act.size == 0:
                break
        a = np.clip(1.0 - np.maximum(dmin, 0) * S * 1.0, 0, 1)
        sel = np.nonzero(a > 0.02)[0]
        if sel.size:
            c, l, m = shade_points(Pm[sel], cam.d)
            color[s0 + sel], light[s0 + sel], mat[s0 + sel] = c, l, m
            alpha[s0 + sel] = a[sel]
            depth[s0 + sel] = tm[sel]
    sh = lambda x: x.reshape(H, W, *x.shape[1:])
    return dict(color=sh(color), light=sh(light), mat=sh(mat), alpha=sh(alpha), depth=sh(depth))


# ----------------------------------------------------------------------------- rasgos pintados sobre el modelo
def zface(x, y):
    zu = 0.46 * math.sqrt(max(0.0, 1 - (x / 0.50) ** 2 - ((y - 2.30) / 0.46) ** 2))
    zj = 0.03 + 0.40 * math.sqrt(max(0.0, 1 - (x / 0.435) ** 2 - ((y - 2.07) / 0.32) ** 2))
    return max(zu, zj, 0.05)


def dome_z(x, y):
    return -0.02 + 0.515 * math.sqrt(max(0.0, 1 - (x / 0.525) ** 2 - ((y - 2.58) / 0.40) ** 2))


def bez(p0, p1, p2, p3, n=14):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def rrect(x0, y0, x1, y1, r, n=8):
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


class Paint:
    def __init__(self, cam):
        self.cam = cam
        self.items = {"face": [], "face_shine": [], "cap": [], "shoe": [], "tee": []}

    def P(self, pts, zfun=None):
        zfun = zfun or zface
        return [self.cam.px(x, y, zfun(x, y)) for x, y in pts]

    def path(self, layer, pts, fill=None, stroke=None, sw=0.0, op=1.0, close=True, zfun=None, defs=""):
        q = self.P(pts, zfun)
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in q) + ("Z" if close else "")
        st = f'fill="{fill or "none"}"'
        if stroke:
            st += f' stroke="{stroke}" stroke-width="{sw * self.cam.S:.2f}" stroke-linejoin="round" stroke-linecap="round"'
        self.items[layer].append((defs, f'<path d="{d}" {st} opacity="{op}"/>'))

    def path3(self, layer, pts3, stroke, sw, op=1.0):
        q = [self.cam.px(*p) for p in pts3]
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in q)
        self.items[layer].append(("", f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw * self.cam.S:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}"/>'))

    def ellipse(self, layer, cx, cy, rx, ry, fill, op=1.0, defs=""):
        pts = [(cx + rx * math.cos(2 * math.pi * i / 40), cy + ry * math.sin(2 * math.pi * i / 40)) for i in range(40)]
        self.path(layer, pts, fill=fill, op=op, defs=defs)

    def svg(self, layer):
        cam = self.cam
        defs = "".join(d for d, _ in self.items[layer])
        body = "".join(m for _, m in self.items[layer])
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{cam.W}" height="{cam.H}" viewBox="0 0 {cam.W} {cam.H}"><defs>{defs}</defs>{body}</svg>'

    def raster(self, layer):
        png = cairosvg.svg2png(bytestring=self.svg(layer).encode(), output_width=self.cam.W, output_height=self.cam.H)
        return np.array(Image.open(io.BytesIO(png)).convert("RGBA")).astype(F32) / 255.0


def paint_character(cam):
    p = Paint(cam)
    # ----- rostro (a partir de la selfie): barba de contorno, perilla vertical, bigote fino de puntas caídas
    arc = lambda a0, a1, st=3: [(0.385 * math.cos(math.radians(a)), 2.07 + 0.285 * math.sin(math.radians(a))) for a in range(a0, a1, st)]
    p.path("face", [(0.425 * math.cos(math.radians(a)), 2.07 + 0.315 * math.sin(math.radians(a))) for a in range(205, 336, 4)],
           stroke="#1A1210", sw=0.10, op=0.18, close=False)                                   # halo de barba de días
    p.path("face", arc(200, 341), stroke="#171010", sw=0.064, close=False)
    for s in (-1, 1):
        p.path("face", [(s * 0.455, 2.24), (s * 0.44, 2.09)], stroke="#171010", sw=0.036, close=False)   # patillas
    p.path("face", [(-0.017, 1.915), (0.017, 1.915), (0.013, 1.845), (-0.013, 1.845)], fill="#171010")   # perilla vertical
    p.path("face", bez((-0.07, 1.948), (-0.03, 1.93), (0.03, 1.93), (0.07, 1.948), 8), stroke="#8E4B42", sw=0.012, close=False)
    p.ellipse("face", 0, 1.925, 0.058, 0.016, "#C0847B", 0.75)                                 # labios
    top = bez((-0.31, 1.99), (-0.24, 2.045), (-0.10, 2.062), (0, 2.040)) + bez((0, 2.040), (0.10, 2.062), (0.24, 2.045), (0.31, 1.99))
    bot = bez((0.31, 1.99), (0.29, 1.955), (0.12, 2.0), (0, 2.008)) + bez((0, 2.008), (-0.12, 2.0), (-0.29, 1.955), (-0.31, 1.99))
    p.path("face", top + bot, fill="#1B1311")
    for s in (-1, 1):
        ex = s * 0.20
        p.ellipse("face", ex, 2.215, 0.086, 0.076, "#F7F2ED")
        p.ellipse("face", ex, 2.215, 0.058, 0.058, "#4B2F1F")
        p.ellipse("face", ex, 2.215, 0.030, 0.030, "#120C0A")
        p.ellipse("face", ex + 0.022, 2.238, 0.013, 0.013, "#FFFFFF")
        p.path("face", bez((ex - 0.094, 2.210), (ex - 0.07, 2.305), (ex + 0.07, 2.307), (ex + 0.094, 2.214), 14), stroke="#2A1B14", sw=0.014, close=False)
        if s < 0:
            br = bez((-0.41, 2.395), (-0.30, 2.465), (-0.16, 2.475), (-0.07, 2.415), 14)
        else:
            br = bez((0.07, 2.415), (0.16, 2.475), (0.30, 2.465), (0.41, 2.395), 14)
        p.path("face", br, stroke="#19110D", sw=0.052, close=False)                            # cejas gruesas
    # ----- nariz: sombra bajo la punta, fosas y brillo
    p.ellipse("face", 0, 2.040, 0.080, 0.024, "#8A5238", 0.38)
    for s in (-1, 1):
        p.ellipse("face", s * 0.033, 2.052, 0.014, 0.010, "#6E3E2C", 0.6)
    p.ellipse("face_shine", -0.028, 2.150, 0.030, 0.022, "#FFFFFF", 0.32)
    # ----- gafas: rectangulares, marco grueso gris humo translúcido, lunas con reflejo azul (solo en el ojo izquierdo del dibujo)
    lens_defs = ('<linearGradient id="lens" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#A9DAFF" stop-opacity=".30"/>'
                 '<stop offset=".6" stop-color="#6FA8E8" stop-opacity=".20"/><stop offset="1" stop-color="#3A6FC0" stop-opacity=".28"/></linearGradient>')
    for s in (-1, 1):
        x0, x1 = (-0.465, -0.062) if s < 0 else (0.062, 0.465)
        frame = rrect(x0, 2.105, x1, 2.370, 0.055)
        p.path("face_shine", rrect(x0 + 0.02, 2.125, x1 - 0.02, 2.350, 0.04), fill="url(#lens)", op=0.95, defs=lens_defs)
        p.path("face", frame, stroke="#3A4048", sw=0.066)
        p.path("face", frame, stroke="#6E7782", sw=0.044)
        p.path("face", [(x0 + 0.045, 2.357), (x1 - 0.045, 2.357)], stroke="#6E7782", sw=0.030, close=False)   # marco superior más grueso
        p.path("face_shine", rrect(x0 + 0.010, 2.115, x1 - 0.010, 2.360, 0.047), stroke="#B8C0CB", sw=0.006, op=0.50)
        p.ellipse("face", (x0 + 0.018) if s < 0 else (x1 - 0.018), 2.357, 0.011, 0.011, "#C7CDD6")           # remache plateado
        gx = s * 0.20 - (0.01 if s < 0 else 0)
        p.path("face_shine", [(gx - 0.12, 2.125), (gx - 0.06, 2.345), (gx - 0.03, 2.345), (gx - 0.09, 2.125)], fill="#FFFFFF", op=0.38)
        p.path("face_shine", [(gx + 0.03, 2.13), (gx + 0.06, 2.25), (gx + 0.075, 2.25), (gx + 0.045, 2.13)], fill="#FFFFFF", op=0.26)
        p.path("face", [(s * 0.465, 2.33), (s * 0.50, 2.315)], stroke="#3A4048", sw=0.04, close=False)
    p.path("face", [(-0.07, 2.295), (0.07, 2.295)], stroke="#3A4048", sw=0.062, close=False)
    p.path("face", [(-0.07, 2.295), (0.07, 2.295)], stroke="#6E7782", sw=0.040, close=False)
    p.ellipse("face_shine", -0.20, 2.215, 0.092, 0.092, "url(#glare)", 0.9,
              defs='<radialGradient id="glare"><stop offset="0" stop-color="#2D8CF0" stop-opacity=".85"/><stop offset=".6" stop-color="#2D8CF0" stop-opacity=".45"/><stop offset="1" stop-color="#2D8CF0" stop-opacity="0"/></radialGradient>')
    # ----- gorra: costuras de seis paneles y pespuntes de la visera (negro sobre negro, sutil)
    for xs in (0.0, -0.21, 0.21):
        pts3 = []
        for i in range(0, 25):
            y = 2.985 - (2.985 - 2.51) * i / 24
            x = xs * (1 - (2.985 - y) / 0.49) if xs else 0.0
            pts3.append((x, y, dome_z(x, y) + 0.004))
        p.path3("cap", pts3, "#2E3541", 0.011, 0.95)
    for inset, op in ((0.95, 0.90), (0.86, 0.60)):
        pts3 = []
        for i in range(0, 31):
            th = math.pi * i / 30
            x = 0.49 * inset * math.cos(th)
            z = 0.44 + 0.31 * inset * math.sin(th)
            pts3.append((x, 2.50 + 0.040 - 0.42 * x * x - 0.09 * max(z - 0.12, 0), z))
        p.path3("cap", pts3, "#323946", 0.009, op)
    # ----- cuello de la camiseta y cordones de los tenis
    p.path3("tee", [(0.215 * math.cos(math.radians(a)), 1.80, 0.20 * math.sin(math.radians(a)) + 0.01) for a in range(185, 356, 6)], "#C9C9C6", 0.026, 0.95)
    for s in (-1, 1):
        for z in (0.08, 0.17, 0.26):
            y = 0.18 + 0.15 * math.sqrt(max(0.0, 1 - ((z - 0.10) / 0.35) ** 2)) + 0.004
            p.path3("shoe", [(s * 0.19 - 0.08, y, z), (s * 0.19 + 0.08, y, z)], "#D2D2CE", 0.014, 0.9)
    return p


def compose(cam, base):
    p = paint_character(cam)
    color, light, mat, alpha = base["color"].copy(), base["light"], base["mat"], base["alpha"]
    masks = {"face": mat == 0, "face_shine": mat == 0, "cap": mat == 3, "shoe": mat == 4, "tee": (mat == 1) | (mat == 0)}
    for layer in ("tee", "cap", "shoe", "face", "face_shine"):
        if not p.items[layer]:
            continue
        L = p.raster(layer)
        a = (L[..., 3] * masks[layer])[..., None]
        rgb = L[..., :3] if layer == "face_shine" else np.clip(L[..., :3] * light[..., None] * 1.0, 0, 1)
        color = color * (1 - a) + rgb * a
    return color, alpha


def to_rgba(color, alpha):
    out = np.zeros(color.shape[:2] + (4,), np.uint8)
    out[..., :3] = (np.clip(color, 0, 1) * 255).astype(np.uint8)
    out[..., 3] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    return out


# ----------------------------------------------------------------------------- pixel art desde el mismo render
def pixelize(rgba, grid, colors=32):
    """Remuestreo exacto a la cuadrícula (sin recortar bordes) -> promedio ponderado por alfa -> paleta limitada -> contorno de 1 px."""
    gx, gy = grid
    sup = 6
    a = rgba[..., 3:4].astype(F32) / 255.0
    pa = np.concatenate([rgba[..., :3].astype(F32) * a, rgba[..., 3:4].astype(F32)], axis=2)
    big = np.stack([np.array(Image.fromarray(pa[..., c], mode="F").resize((gx * sup, gy * sup), Image.BOX)) for c in range(4)], axis=2)
    small = big.reshape(gy, sup, gx, sup, 4).mean(axis=(1, 3))
    al = small[..., 3] / 255.0
    rgb = np.where(al[..., None] > 1e-3, small[..., :3] / np.maximum(al[..., None], 1e-3), 0)
    mask = al > 0.5
    q = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    out = np.zeros((gy, gx, 4), np.uint8)
    out[..., :3] = np.array(q)
    out[..., 3] = np.where(mask, 255, 0)
    ring = np.zeros_like(mask)
    ring[1:, :] |= mask[:-1, :]
    ring[:-1, :] |= mask[1:, :]
    ring[:, 1:] |= mask[:, :-1]
    ring[:, :-1] |= mask[:, 1:]
    ring &= ~mask
    out[ring] = (*INK, 255)
    return out


def on_bg(arr, scale):
    h, w = arr.shape[:2]
    bg = Image.new("RGBA", (w, h), (*[int(BG[i:i + 2], 16) for i in (1, 3, 5)], 255))
    bg.alpha_composite(Image.fromarray(arr))
    return bg.resize((w * scale, h * scale), Image.NEAREST)


# ----------------------------------------------------------------------------- main
def main():
    S_full = int(os.environ.get("SCALE", 200))
    S_bust = int(S_full * 1.5)
    part_ = os.environ.get("PART", "all")
    if part_ in ("all", "full"):                     # cuerpo completo en T-pose
        cam = Cam(0.0, 1.46, 1.62, 1.54, S_full)
        base = render(cam)
        color, alpha = compose(cam, base)
        full = to_rgba(color, alpha)
        Image.fromarray(full).save(A / "character_3d.png")
        Image.fromarray(full).save(A / "character_color.png")
        t = base["depth"]
        m = base["alpha"] > 0.5
        tn = (t - t[m].min()) / max(t[m].max() - t[m].min(), 1e-6)
        dep = np.where(m, 255 * (0.25 + 0.75 * (1 - tn)), 0).astype(np.uint8)
        Image.fromarray(dep).save(A / "character_depth.png")
        gx = 80
        gy = int(round(gx * cam.H / cam.W))
        on_bg(pixelize(full, (gx, gy), 36), 8).save(A / "character_pixel_full.png")
    if part_ in ("all", "bust"):                     # busto en primer plano -> foto de perfil
        camb = Cam(0.0, 2.24, 0.78, 0.78, S_bust)
        bb = render(camb)
        cb, ab = compose(camb, bb)
        bust = to_rgba(cb, ab)
        Image.fromarray(bust).save(A / "character_bust.png")
        on_bg(pixelize(bust, (72, 72), 40), 7).save(A / "avatar_pixel.png")
    for f in ("character_3d.png", "character_bust.png", "avatar_pixel.png", "character_pixel_full.png", "character_color.png", "character_depth.png"):
        print(f"  {f:28s}{(A / f).stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
