#!/usr/bin/env python3
"""
generate_hologram.py -- Núcleo visual 3D de @AFelipeRD (assets/visual_core.webp)

Una nube de partículas 3D que se transforma en bucle mientras la cámara orbita:
    Nube GCP (volumétrica)  ->  Red neuronal 3D  ->  Servidor MCP (racks 3D)  ->  Personaje de marca  ->  (vuelta)

Qué lo hace 3D de verdad (no un efecto):
  * Cada partícula tiene (x, y, z). Proyección en perspectiva con distancia de cámara D.
  * Cámara orbital: yaw oscilante (+/-31 grados) y pitch suave; 2 ciclos de yaw por bucle -> empalme perfecto.
  * Suelo con rejilla en perspectiva que gira con la cámara: ancla la escena en el espacio.
  * Profundidad: tamaño por perspectiva + atenuación por distancia + brillo (bloom) aditivo.
  * El rostro es un relieve: z = elipsoide facial + luminosidad (la nariz y la frente "salen").

Movimiento:
  * Resorte amortiguado real por partícula (masa, inercia, ligero rebote) en 3D, rigidez variable.
  * Ola de arranque direccional; asignación óptima (algoritmo húngaro) entre formas.
  * La velocidad tiñe la partícula hacia el ámbar de señal y deja una estela.

Dependencias:  pip install numpy pillow opencv-python-headless scipy
Uso:  python scripts/generate_hologram.py            (usa assets/character_color.png y character_depth.png)
Opciones: --size 320 --particles 3000 --fps 20 --quality 70 --out assets/visual_core.webp
Formato: .webp (animado, recomendado) o .gif según la extensión de --out.
"""
import argparse
import json
import math
import pathlib
import sys

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
except ImportError:
    sys.exit("Faltan dependencias:  pip install numpy pillow opencv-python-headless scipy")

ROOT = pathlib.Path(__file__).resolve().parent.parent


def hex2rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


# --------------------------------------------------------------------------- formas 3D
def unit_vectors(n, rng):
    v = rng.normal(size=(n, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def cloud_target(n, rng):
    """Nube volumétrica: unión de esferas (solo la superficie exterior), brillo por orientación hacia arriba."""
    puffs = np.array([(-0.52, 0.14, 0.00, 0.34), (-0.16, -0.10, 0.04, 0.46), (0.28, -0.02, -0.02, 0.40),
                      (0.58, 0.16, 0.02, 0.28), (0.02, 0.22, 0.00, 0.48)])
    out, nrm = [], []
    w = puffs[:, 3] ** 2 / (puffs[:, 3] ** 2).sum()
    while len(out) < n:
        k = rng.choice(len(puffs), 4 * n, p=w)
        u = unit_vectors(4 * n, rng)
        p = puffs[k, :3] + u * puffs[k, 3:4] * rng.uniform(0.93, 1.0, (4 * n, 1))
        inside = np.zeros(len(p), bool)
        for j, (cx, cy, cz, r) in enumerate(puffs):
            inside |= (k != j) & (np.linalg.norm(p - (cx, cy, cz), axis=1) < r * 0.97)
        p, u = p[~inside], u[~inside]
        out.extend(p.tolist())
        nrm.extend(u.tolist())
    pts, nrm = np.array(out[:n]), np.array(nrm[:n])
    pts[:, 1] *= 0.95
    bri = 0.28 + 0.62 * np.clip(-nrm[:, 1], 0, 1) + 0.10 * rng.random(n)
    return pts, np.clip(bri, 0, 1)


def neural_target(n, rng):
    """Red neuronal 3D: capas a lo largo de x, nodos en rejilla y-z, conexiones como flujo de partículas."""
    xs = [-0.80, -0.27, 0.27, 0.80]
    grids = [[(y, z) for y in (-0.34, 0.34) for z in (-0.30, 0.30)],
             [(y, z) for y in (-0.52, 0, 0.52) for z in (-0.30, 0.30)],
             [(y, z) for y in (-0.52, 0, 0.52) for z in (-0.30, 0.30)],
             [(y, 0.0) for y in (-0.46, 0, 0.46)]]
    layers = [[(x, y, z) for (y, z) in g] for x, g in zip(xs, grids)]
    flat = np.array([p for L in layers for p in L])
    edges = np.array([(a, b) for i in range(3) for a in layers[i] for b in layers[i + 1]])
    nn = int(n * 0.36)
    c = flat[np.arange(nn) % len(flat)]
    nodes = c + unit_vectors(nn, rng) * np.abs(rng.normal(0, 0.032, (nn, 1)))
    e = edges[rng.integers(len(edges), size=n - nn)]
    t = rng.random((n - nn, 1))
    lines = e[:, 0] + (e[:, 1] - e[:, 0]) * t + rng.normal(0, 0.004, (n - nn, 3))
    pts = np.vstack([nodes, lines])
    bri = np.concatenate([0.82 + 0.18 * rng.random(nn), 0.26 + 0.26 * rng.random(n - nn)])
    return pts, bri


def box_edges(c, s):
    cx, cy, cz = c
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    idx = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    return [(np.array(v[a]), np.array(v[b])) for a, b in idx]


def mcp_target(n, rng):
    """Servidor MCP: 3 racks (cajas 3D con ranuras y LED) enlazados a 3 clientes/herramientas (cubos)."""
    segs, slots, leds, links, cubes = [], [], [], [], []
    for yc in (-0.50, 0.02, 0.54):
        segs += box_edges((-0.52, yc, 0), (0.66, 0.38, 0.52))
        for j in range(3):
            y = yc - 0.09 + j * 0.09
            slots.append((np.array((-0.80, y, 0.26)), np.array((-0.50, y, 0.26))))
        leds.append(np.array((-0.30, yc, 0.27)))
    for yc in (-0.50, 0.02, 0.54):
        cubes += box_edges((0.78, yc, 0), (0.17, 0.17, 0.17))
        links.append((np.array((-0.19, 0.02, 0)), np.array((0.69, yc, 0))))
    groups = [(segs, 0.42, 0.50), (slots, 0.11, 0.62), (links, 0.18, 0.40), (cubes, 0.15, 0.55)]
    pts, bri = [], []
    for lst, share, b in groups:
        m = int(n * share)
        e = [lst[i] for i in rng.integers(len(lst), size=m)]
        t = rng.random((m, 1))
        a, bb = np.array([x[0] for x in e]), np.array([x[1] for x in e])
        pts.append(a + (bb - a) * t + rng.normal(0, 0.004, (m, 3)))
        bri.append(b + 0.18 * rng.random(m))
    m = n - sum(len(p) for p in pts)
    L = np.array(leds)[rng.integers(len(leds), size=m)]
    pts.append(L + unit_vectors(m, rng) * np.abs(rng.normal(0, 0.03, (m, 1))))
    bri.append(np.full(m, 1.0))
    return np.vstack(pts), np.clip(np.concatenate(bri), 0, 1)


def face_target(n, rng, photo):
    """Rostro en relieve: muestreo por importancia sobre la luminosidad + profundidad (elipsoide + tono)."""
    img = cv2.imread(str(photo))
    if img is None:
        sys.exit(f"No pude leer la foto: {photo}")
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = np.full((H, W), cv2.GC_PR_BGD, np.uint8)
    m[:int(H * .03), :] = cv2.GC_BGD
    m[:, :int(W * .015)] = cv2.GC_BGD
    m[:, int(W * .985):] = cv2.GC_BGD
    cv2.ellipse(m, (int(W * .5), int(H * .36)), (int(W * .20), int(H * .34)), 0, 0, 360, cv2.GC_PR_FGD, -1)
    m[int(H * .55):, int(W * .12):int(W * .90)] = cv2.GC_PR_FGD
    cv2.ellipse(m, (int(W * .5), int(H * .40)), (int(W * .10), int(H * .20)), 0, 0, 360, cv2.GC_FGD, -1)
    bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, m, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
    gc = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    dark = (cv2.GaussianBlur(gray, (0, 0), 3) < 78).astype(np.uint8) * 255
    fgm = cv2.bitwise_or(gc, dark)
    fgm = cv2.morphologyEx(fgm, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    fgm = cv2.morphologyEx(fgm, cv2.MORPH_OPEN, np.ones((11, 11), np.uint8))
    cnt, lab, st, _ = cv2.connectedComponentsWithStats(fgm)
    fgm = np.where(lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]), 255, 0).astype(np.uint8)
    cl = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(8, 8)).apply(gray).astype(np.float32) / 255
    L = np.clip(cl + 1.7 * (cl - cv2.GaussianBlur(cl, (0, 0), 7)), 0, 1) ** 0.82
    D = np.clip(0.5 + 3.2 * (cl - cv2.GaussianBlur(cl, (0, 0), 3.0)), 0, 1)
    ys, xs = np.mgrid[0:H, 0:W]
    inface = (xs / W > .30) & (xs / W < .72) & (ys / H > .20) & (ys / H < .60)
    isdark = gray < 85
    v = np.where(isdark & inface, 0.06 + 0.30 * D ** 2,
        np.where(isdark & (ys / H < .34), 0.30 + 0.45 * D ** 1.6,
        np.where(isdark, 0.14 + 0.40 * D ** 1.8, L)))
    rim = cv2.subtract(fgm, cv2.erode(fgm, np.ones((19, 19), np.uint8))) > 0
    x0, cw, y0 = int(.12 * W), int(.76 * W), int(.035 * H)
    sl = (slice(y0, y0 + cw), slice(x0, x0 + cw))
    mask, vv, rr = fgm[sl] > 0, v[sl], rim[sl]
    xy, (iy, ix) = _sample(mask, n, rng, 0.24 + vv)
    bri = np.clip(vv[iy, ix], 0, 1)
    bri = np.where(rr[iy, ix], np.maximum(bri, 0.70), bri)
    x, y = xy[:, 0] * 0.98, xy[:, 1] * 0.98
    # relieve: elipsoide facial + tono (lo claro sobresale); hombros más planos y atrás
    face = np.sqrt(np.clip(1 - ((x / 0.58) ** 2 + ((y + 0.10) / 0.78) ** 2), 0, 1))
    z = 0.34 * face + 0.20 * vv[iy, ix] - 0.12
    return np.stack([x, y, z], 1), bri


def ramp_cols(bri, tok):
    ramp = np.array([hex2rgb(c) for c in tok["ramp"]])
    f = np.clip(bri, 0, 1) * (len(ramp) - 1)
    i0 = np.clip(f.astype(int), 0, len(ramp) - 2)
    return ramp[i0] * (1 - (f - i0))[:, None] + ramp[i0 + 1] * (f - i0)[:, None]


def character_target(n, rng, color_png, tok):
    """Personaje de marca: partículas con SU color real, relieve desde el mapa de profundidad y silueta luminosa."""
    color_png = pathlib.Path(color_png)
    col = np.array(Image.open(color_png).convert("RGBA"))
    dep = np.array(Image.open(color_png.with_name("character_depth.png")).convert("L")).astype(float) / 255
    H, W = col.shape[:2]
    alpha = col[..., 3] > 40
    lum = (0.299 * col[..., 0] + 0.587 * col[..., 1] + 0.114 * col[..., 2]) / 255
    edge = np.clip(np.hypot(cv2.Sobel(lum.astype(np.float32), cv2.CV_32F, 1, 0), cv2.Sobel(lum.astype(np.float32), cv2.CV_32F, 0, 1)) * 3, 0, 1)
    ring = alpha & ~cv2.erode(alpha.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    xy, (iy, ix) = _sample(alpha, n, rng, 0.45 + 1.1 * edge + 0.9 * ring + 0.35 * lum)
    x, y = xy[:, 0] * (W / H) * 1.10, xy[:, 1] * 1.10 + 0.04
    z = (dep[iy, ix] - 0.62) * 1.25
    rgb = col[iy, ix, :3].astype(float)
    L = lum[iy, ix]
    lift = np.clip(0.45 - L, 0, 0.45)[:, None]                   # lo oscuro no desaparece sobre el fondo
    rgb = rgb * (1 - lift) + hex2rgb(tok["ramp"][2]) * lift
    rim = ring[iy, ix][:, None]
    rgb = np.where(rim, rgb * 0.35 + hex2rgb(tok["ramp"][3]) * 0.65, rgb)
    return np.stack([x, y, z], 1), np.clip(0.35 + 0.65 * L, 0, 1), np.clip(rgb * 1.08, 0, 255)


def _sample(mask, n, rng, weights):
    ys, xs = np.nonzero(mask)
    w = weights[ys, xs].astype(float)
    idx = rng.choice(len(xs), n, p=w / w.sum())
    h, w_ = mask.shape
    x = (xs[idx] + rng.random(n)) / w_ * 2 - 1
    y = (ys[idx] + rng.random(n)) / h * 2 - 1
    return np.stack([x, y], 1), (ys[idx], xs[idx])


# --------------------------------------------------------------------------- simulación (3D)
class Cloud:
    def __init__(self, shape, rng, fps, k_range=(70, 106), zeta=0.58):
        self.n = len(shape[0])
        self.pos, self.bri, self.col = shape[0].copy(), shape[1].copy(), shape[2].copy()
        self.target_col = self.col.copy()
        self.vel = np.zeros_like(self.pos)
        self.k = rng.uniform(*k_range, self.n)[:, None]
        self.c = 2 * zeta * np.sqrt(self.k) * rng.uniform(0.92, 1.08, self.n)[:, None]
        self.target, self.target_bri = self.pos.copy(), self.bri.copy()
        self.delay = np.zeros(self.n)
        self.t, self.dt, self.rng = 0.0, 1.0 / fps, rng

    def retarget(self, pts, bri, col, wave):
        self.target, self.target_bri, self.target_col = pts, bri, col
        p = self.pos
        w = {"x": (p[:, 0] + 1) / 2, "y": (p[:, 1] + 1) / 2, "z": (p[:, 2] + 1) / 2}.get(
            wave, np.clip(np.linalg.norm(p, axis=1) / 1.2, 0, 1))
        self.delay = (0.55 * w + 0.45 * self.rng.random(self.n)) * 0.42
        self.t = 0.0

    def step(self, sub=4):
        h = self.dt / sub
        active = (self.t >= self.delay)[:, None]
        for _ in range(sub):
            acc = (self.k * (self.target - self.pos) - self.c * self.vel) * active
            self.vel += acc * h
            self.pos += self.vel * h
        self.bri += (self.target_bri - self.bri) * 0.16 * active[:, 0]
        self.col += (self.target_col - self.col) * 0.16 * active
        self.t += self.dt


# --------------------------------------------------------------------------- cámara y render
D_CAM, FLOOR_Y = 3.4, 1.08


def camera(t, loop):
    yaw = 0.55 * math.sin(2 * math.pi * 2 * t / loop)           # 2 ciclos por bucle: empalme perfecto
    pitch = 0.16 + 0.07 * math.sin(2 * math.pi * t / loop + 1.0)
    return yaw, pitch


def project(P, yaw, pitch, K, C):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    x1 = P[:, 0] * cy + P[:, 2] * sy
    z1 = -P[:, 0] * sy + P[:, 2] * cy
    y2 = P[:, 1] * cp - z1 * sp
    z2 = P[:, 1] * sp + z1 * cp
    s = D_CAM / (D_CAM - z2)
    return x1 * s * K + C, y2 * s * K + C, z2, s


def load_font(size):
    for name in ("JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf", "Consolas.ttf", "Menlo.ttc", "cour.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def floor_lines():
    """Rejilla del suelo (líneas en x y en z) como segmentos 3D."""
    g = np.linspace(-1.5, 1.5, 11)
    segs = []
    for v in g:
        segs.append(((v, FLOOR_Y, -1.5), (v, FLOOR_Y, 1.5)))
        segs.append(((-1.5, FLOOR_Y, v), (1.5, FLOOR_Y, v)))
    return segs


def render(cloud, S, SS, tok, t, loop, label, fonts, floor):
    bg = hex2rgb(tok["surface-0"])
    ramp = np.array([hex2rgb(c) for c in tok["ramp"]])
    signal, border = hex2rgb(tok["accent-signal"]), hex2rgb(tok["border-subtle"])
    S2 = S * SS
    K, C = S2 * 0.335, S2 / 2
    yaw, pitch = camera(t, loop)
    layer = Image.new("RGB", (S2, S2), (0, 0, 0))
    d = ImageDraw.Draw(layer, "RGB")
    # suelo: líneas atenuadas por distancia
    for a, b in floor:
        P = np.array([a, b], float)
        sx, sy, z2, _ = project(P, yaw, pitch, K, C)
        fade = np.clip(0.55 - 0.30 * (z2.mean() + 1.5) / 3.0, 0.05, 0.55)
        col = tuple(int(v) for v in border * fade * 1.6)
        d.line((sx[0], sy[0] + S2 * 0.04, sx[1], sy[1] + S2 * 0.04), fill=col, width=SS)
    # partículas
    P, b = cloud.pos, np.clip(cloud.bri, 0, 1)
    sx, sy, z2, s = project(P, yaw, pitch, K, C)
    speed = np.linalg.norm(cloud.vel, axis=1)
    tint = np.clip(speed / 1.5, 0, 1) ** 0.8
    col = cloud.col * (1 - tint[:, None] * 0.85) + signal * (tint[:, None] * 0.85)
    depth = np.clip(0.62 + 0.42 * z2, 0.22, 1.0)                       # cerca = brillante
    col = col * depth[:, None]
    rad = (0.50 + 1.15 * b) * s * (S / 320) * SS * 0.95
    order = np.argsort(z2)                                              # pintor: lejos -> cerca
    fast = speed > 0.75
    for i in order:
        r, c = rad[i], tuple(int(v) for v in col[i])
        if fast[i]:
            vx, vy = cloud.vel[i, 0] * K * 0.02, cloud.vel[i, 1] * K * 0.02
            d.line((sx[i] - vx, sy[i] - vy, sx[i], sy[i]), fill=c, width=max(1, int(r * 1.2)))
        d.ellipse((sx[i] - r, sy[i] - r, sx[i] + r, sy[i] + r), fill=c)
    layer = layer.resize((S, S), Image.LANCZOS)
    bloom = layer.filter(ImageFilter.GaussianBlur(S / 55))
    bloom = bloom.point(lambda v: min(255, int(v * 0.85)))
    lit = ImageChops.add(layer, bloom)
    base = Image.new("RGB", (S, S), tuple(int(v) for v in bg))
    img = ImageChops.add(base, lit)
    hud(ImageDraw.Draw(img), img, S, tok, fonts, label, t)
    return img


def hud(d, img, S, tok, font, label, t):
    muted = tuple(int(v) for v in hex2rgb(tok["text-muted"]))
    second = tuple(int(v) for v in hex2rgb(tok["text-secondary"]))
    signal = tuple(int(v) for v in hex2rgb(tok["accent-signal"]))
    data = tuple(int(v) for v in hex2rgb(tok["accent-data"]))
    sub = tuple(int(v) for v in hex2rgb(tok["border-subtle"]))
    idx, name, moving = label
    m = 12
    d.text((m, S - m - 22), ("→ " if moving else "● ") + f"{idx + 1:02d} {name}", font=font, fill=signal if moving else second)
    d.text((S - m, S - m - 22), f"t={t:05.2f}s", font=font, fill=muted, anchor="ra")
    seg, gap = (S - 2 * m - 18) / 4, 6
    for k in range(4):
        x = m + k * (seg + gap)
        d.rectangle((x, S - m - 8, x + seg, S - m - 6), fill=data if k == idx else sub)


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Genera visual_core.webp (holograma 3D de partículas).")
    ap.add_argument("--photo", default=None, help="Solo si usas --shape4 face")
    ap.add_argument("--character", default=str(ROOT / "assets" / "character_color.png"), help="Render del personaje (build_character.py)")
    ap.add_argument("--shape4", choices=["character", "face"], default="character")
    ap.add_argument("--out", default=str(ROOT / "assets" / "visual_core.webp"))
    ap.add_argument("--tokens", default=str(ROOT / "assets" / "tokens.json"))
    ap.add_argument("--size", type=int, default=320)
    ap.add_argument("--particles", type=int, default=3000)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--trans", type=float, default=1.5)
    ap.add_argument("--hold", type=float, default=1.1)
    ap.add_argument("--quality", type=int, default=70, help="Calidad WebP (0-100)")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    tok = json.loads(pathlib.Path(a.tokens).read_text())
    rng = np.random.default_rng(a.seed)
    n = a.particles
    names = ["GCP.CLOUD", "NEURAL.NET", "MCP.SERVER", "AFELIPE.RD"]
    with_cols = lambda sh: (sh[0], sh[1], ramp_cols(sh[1], tok))
    if a.shape4 == "face":
        fourth = with_cols(face_target(n, rng, a.photo))
    else:
        fourth = character_target(n, rng, a.character, tok)
    raw = [with_cols(cloud_target(n, rng)), with_cols(neural_target(n, rng)), with_cols(mcp_target(n, rng)), fourth]
    pick = lambda sh, ix: (sh[0][ix], sh[1][ix], sh[2][ix])
    shapes = [raw[0]]
    for k in range(1, 4):                                   # asignación húngara encadenada (3D)
        _, ix = linear_sum_assignment(cdist(shapes[-1][0], raw[k][0], "sqeuclidean"))
        shapes.append(pick(raw[k], ix))
    _, ix = linear_sum_assignment(cdist(shapes[-1][0], raw[0][0], "sqeuclidean"))
    back = pick(raw[0], ix)

    cloud = Cloud(shapes[0], rng, a.fps)
    S, SS = a.size, 2
    seg_frames, trans_frames = int((a.trans + a.hold) * a.fps), int(a.trans * a.fps)
    loop = 4 * seg_frames / a.fps
    font, floor = load_font(max(9, S // 34)), floor_lines()
    waves = ["x", "y", "r", "z"]
    sequence = [(1, shapes[1]), (2, shapes[2]), (3, shapes[3]), (0, back)]
    frames = []
    for seg, (idx, (pts, bri, cols)) in enumerate(sequence):
        cloud.retarget(pts, bri, cols, waves[seg])
        for f in range(seg_frames):
            cloud.step()
            t = len(frames) / a.fps
            frames.append(render(cloud, S, SS, tok, t, loop, (idx, names[idx], f < trans_frames), font, floor))
        print(f"  segmento {seg + 1}/4 -> {names[idx]}", flush=True)

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = int(1000 / a.fps)
    if out.suffix.lower() == ".gif":
        pal = frames[0].quantize(colors=64, dither=Image.Dither.NONE)
        q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
        q[0].save(out, save_all=True, append_images=q[1:], duration=dur, loop=0, disposal=1)
    else:
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=dur, loop=0,
                       quality=a.quality, method=4, lossless=False)
    print(f"OK {out}  {len(frames)} cuadros  {out.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
