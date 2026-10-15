#!/usr/bin/env python3
"""
generate_hologram.py -- Núcleo visual animado de @AFelipeRD (visual_core.gif)

Una única nube de partículas que se transforma en bucle:
    GCP Cloud  ->  Red Neuronal  ->  Servidor MCP  ->  Rostro  ->  (vuelve a Cloud)

Principios de movimiento (filosofía "craft"):
  * Cero interpolación lineal. Cada partícula es un resorte amortiguado real
    (integración semi-implícita): tiene masa, inercia y un ligero rebote.
  * Rigidez y amortiguación ligeramente distintas por partícula -> la nube "respira",
    no se mueve como un bloque rígido.
  * Escalonado (stagger): cada transición arranca con una onda direccional
    (izq->der, arriba->abajo, radial) en vez de todo al mismo tiempo.
  * La velocidad tiñe la partícula hacia el acento de señal (ámbar) y deja una estela corta:
    el color comunica energía cinética; en reposo la nube es fría (tonos glacier/tinta).
  * Asignación óptima (algoritmo húngaro) entre forma y forma: las partículas viajan la
    menor distancia total, sin cruces caóticos.

Dependencias:  pip install numpy pillow opencv-python-headless scipy
Uso:
    python scripts/generate_hologram.py --photo foto.png --out assets/visual_core.gif
Opciones útiles:  --size 400  --particles 2400  --fps 20  --seed 7
"""
import argparse
import json
import math
import pathlib
import sys

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
except ImportError:
    sys.exit("Faltan dependencias:  pip install numpy pillow opencv-python-headless scipy")

ROOT = pathlib.Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- utilidades
def hex2rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def sample_mask(mask, n, rng, weights=None):
    """Muestrea n puntos dentro de una máscara (opcionalmente ponderados).
    Devuelve coords normalizadas [-1,1] y los índices de píxel para consultar atributos."""
    ys, xs = np.nonzero(mask)
    p = None
    if weights is not None:
        w = weights[ys, xs].astype(float)
        p = w / w.sum()
    idx = rng.choice(len(xs), n, p=p)
    h, w_ = mask.shape
    x = (xs[idx] + rng.random(n)) / w_ * 2 - 1
    y = (ys[idx] + rng.random(n)) / h * 2 - 1
    return np.stack([x, y], 1), (ys[idx], xs[idx])


# --------------------------------------------------------------------------- formas
def cloud_target(n, rng, R=512):
    """Nube (GCP Cloud): relleno con borde más brillante."""
    img = Image.new("L", (R, R), 0)
    d = ImageDraw.Draw(img)
    d.ellipse((90, 210, 250, 370), fill=255)
    d.ellipse((170, 130, 350, 310), fill=255)
    d.ellipse((290, 190, 440, 340), fill=255)
    d.rounded_rectangle((120, 270, 420, 370), radius=50, fill=255)
    m = np.array(img) > 0
    dist = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    edge = 1 - np.clip(dist / (dist.max() * 0.5), 0, 1)           # 1 en el borde, 0 en el centro
    pts, (iy, ix) = sample_mask(m, n, rng, weights=0.25 + edge ** 2)
    bri = 0.28 + 0.62 * edge[iy, ix] + 0.1 * rng.random(n)
    return pts, np.clip(bri, 0, 1)


def neural_target(n, rng):
    """Red neuronal: nodos densos + conexiones como flujo de partículas."""
    layers = [4, 6, 6, 3]
    xs = np.linspace(-0.74, 0.74, len(layers))
    nodes = [[(lx, y) for y in (np.linspace(-0.62, 0.62, k) if k > 1 else [0.0])] for lx, k in zip(xs, layers)]
    edges = [(a, b) for L in range(len(layers) - 1) for a in nodes[L] for b in nodes[L + 1]]
    flat = [p for L in nodes for p in L]
    n_nodes = int(n * 0.38)
    pts, bri = [], []
    for i in range(n_nodes):
        c = flat[i % len(flat)]
        r, th = abs(rng.normal(0, 0.030)), rng.random() * 2 * math.pi
        pts.append((c[0] + r * math.cos(th), c[1] + r * math.sin(th)))
        bri.append(0.82 + 0.18 * rng.random())
    for _ in range(n - n_nodes):
        a, b = edges[rng.integers(len(edges))]
        t = rng.random()
        pts.append((a[0] + (b[0] - a[0]) * t + rng.normal(0, 0.004),
                    a[1] + (b[1] - a[1]) * t + rng.normal(0, 0.004)))
        bri.append(0.28 + 0.26 * rng.random())
    return np.array(pts), np.array(bri)


def mcp_target(n, rng, R=512):
    """Servidor MCP: rack de 3 unidades con LEDs, enlazado a 3 clientes/herramientas."""
    body = Image.new("L", (R, R), 0)
    led = Image.new("L", (R, R), 0)
    d, dl = ImageDraw.Draw(body), ImageDraw.Draw(led)
    for k in range(3):
        y0 = 100 + k * 100
        d.rounded_rectangle((70, y0, 300, y0 + 78), radius=10, outline=255, width=7)
        for j in range(3):
            d.line((96, y0 + 22 + j * 15, 205, y0 + 22 + j * 15), fill=255, width=4)
        dl.ellipse((262, y0 + 28, 282, y0 + 48), fill=255)
    for ty in (130, 250, 370):
        d.line((300, 250, 430, ty), fill=255, width=5)
        d.ellipse((412, ty - 18, 448, ty + 18), outline=255, width=7)
        dl.ellipse((424, ty - 6, 436, ty + 6), fill=255)
    b, l = np.array(body) > 0, np.array(led) > 0
    m = b | l
    w = np.where(l, 7.0, 1.0)
    pts, (iy, ix) = sample_mask(m, n, rng, weights=w)
    bri = np.where(l[iy, ix], 1.0, 0.45 + 0.2 * rng.random(n))
    return pts, bri


def face_target(n, rng, photo):
    """Rostro: muestreo por importancia sobre luminosidad local (CLAHE + realce de detalle)."""
    img = cv2.imread(str(photo))
    if img is None:
        sys.exit(f"No pude leer la foto: {photo}")
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # máscara: GrabCut (piel) unido a umbral de zonas oscuras (gorra, barba, suéter)
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
    # tono
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
    # recorte cuadrado con zoom sobre cara y hombros
    x0, cw, y0 = int(.12 * W), int(.76 * W), int(.035 * H)
    sl = (slice(y0, y0 + cw), slice(x0, x0 + cw))
    mask, vv, rr = fgm[sl] > 0, v[sl], rim[sl]
    pts, (iy, ix) = sample_mask(mask, n, rng, weights=0.24 + vv)
    bri = np.clip(vv[iy, ix], 0, 1)
    bri = np.where(rr[iy, ix], np.maximum(bri, 0.70), bri)         # silueta luminosa
    return pts * 0.98, bri


# --------------------------------------------------------------------------- simulación
class Cloud:
    def __init__(self, shapes, rng, fps, k_range=(72, 108), zeta=0.58):
        self.n = len(shapes[0][0])
        self.pos = shapes[0][0].copy()
        self.vel = np.zeros_like(self.pos)
        self.bri = shapes[0][1].copy()
        self.k = rng.uniform(*k_range, self.n)[:, None]
        self.c = 2 * zeta * np.sqrt(self.k) * rng.uniform(0.92, 1.08, self.n)[:, None]
        self.target = self.pos.copy()
        self.target_bri = self.bri.copy()
        self.delay = np.zeros(self.n)
        self.t = 0.0
        self.dt = 1.0 / fps
        self.rng = rng

    def retarget(self, pts, bri, wave):
        self.target, self.target_bri = pts, bri
        p = self.pos
        if wave == "x":
            w = (p[:, 0] + 1) / 2
        elif wave == "y":
            w = (p[:, 1] + 1) / 2
        else:
            w = np.clip(np.hypot(p[:, 0], p[:, 1]) / 1.1, 0, 1)
        self.delay = (0.55 * w + 0.45 * self.rng.random(self.n)) * 0.42    # segundos
        self.t = 0.0

    def step(self, sub=4):
        h = self.dt / sub
        active = (self.t >= self.delay)[:, None]
        for _ in range(sub):
            acc = (self.k * (self.target - self.pos) - self.c * self.vel) * active
            self.vel += acc * h                      # semi-implícito: primero v, luego x
            self.pos += self.vel * h
        self.bri += (self.target_bri - self.bri) * 0.16 * active[:, 0]
        self.t += self.dt


# --------------------------------------------------------------------------- render
def load_font(size):
    for name in ("JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf", "Consolas.ttf", "Menlo.ttc", "cour.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(cloud, S, SS, tok, label, hud):
    bg = hex2rgb(tok["surface-0"])
    ramp = np.array([hex2rgb(c) for c in tok["ramp"]])
    signal = hex2rgb(tok["accent-signal"])
    S2 = S * SS
    img = Image.new("RGB", (S2, S2), tuple(int(c) for c in bg))
    d = ImageDraw.Draw(img, "RGB")
    p, b = cloud.pos, np.clip(cloud.bri, 0, 1)
    speed = np.linalg.norm(cloud.vel, axis=1)
    tint = np.clip(speed / 1.5, 0, 1) ** 0.8
    # color por tono (rampa) + tinte cinético hacia ámbar + desvanecido por profundidad radial
    f = b * (len(ramp) - 1)
    i0 = np.clip(f.astype(int), 0, len(ramp) - 2)
    col = ramp[i0] * (1 - (f - i0))[:, None] + ramp[i0 + 1] * (f - i0)[:, None]
    col = col * (1 - tint[:, None] * 0.85) + signal * (tint[:, None] * 0.85)
    depth = 1 - 0.55 * np.clip(np.hypot(p[:, 0], p[:, 1]) / 1.15, 0, 1) ** 2
    col = bg + (col - bg) * depth[:, None]
    scale = S2 * 0.455
    px, py = p[:, 0] * scale + S2 / 2, p[:, 1] * scale + S2 / 2
    rad = (0.55 + 1.25 * b) * (S / 400) * SS * 0.95
    order = np.argsort(b)                                                   # lo brillante encima
    fast = speed > 0.75
    for i in order:
        r = rad[i]
        c = tuple(int(v) for v in col[i])
        if fast[i]:                                                          # estela corta
            vx, vy = cloud.vel[i] * scale * 0.020
            d.line((px[i] - vx, py[i] - vy, px[i], py[i]), fill=c, width=max(1, int(r * 1.3)))
        d.ellipse((px[i] - r, py[i] - r, px[i] + r, py[i] + r), fill=c)
    img = img.resize((S, S), Image.LANCZOS)
    hud(ImageDraw.Draw(img), label)
    return img


def make_hud(S, tok, font_small, n_particles):
    border = tuple(int(v) for v in hex2rgb(tok["border-strong"]))
    muted = tuple(int(v) for v in hex2rgb(tok["text-muted"]))
    second = tuple(int(v) for v in hex2rgb(tok["text-secondary"]))
    signal = tuple(int(v) for v in hex2rgb(tok["accent-signal"]))
    data = tuple(int(v) for v in hex2rgb(tok["accent-data"]))
    sub = tuple(int(v) for v in hex2rgb(tok["border-subtle"]))
    m, L = 14, 16

    def hud(d, label):
        idx, name, moving, frame_t = label
        for (x, y, sx, sy) in ((m, m, 1, 1), (S - m, m, -1, 1), (m, S - m, 1, -1), (S - m, S - m, -1, -1)):
            d.line((x, y, x + sx * L, y), fill=border, width=1)
            d.line((x, y, x, y + sy * L), fill=border, width=1)
        d.text((m + 6, m + 6), "VISUAL.CORE", font=font_small, fill=muted)
        d.text((S - m - 6, m + 6), f"N={n_particles}", font=font_small, fill=muted, anchor="ra")
        d.text((m + 6, S - m - 20), ("→ " if moving else "● ") + f"{idx + 1:02d} {name}", font=font_small,
               fill=signal if moving else second, anchor="ls" if False else None)
        d.text((S - m - 6, S - m - 20), f"t={frame_t:05.2f}s", font=font_small, fill=muted, anchor="ra")
        seg_w, gap = (S - 2 * (m + 6) - 3 * 6) / 4, 6
        for k in range(4):
            x = m + 6 + k * (seg_w + gap)
            d.rectangle((x, S - m - 8, x + seg_w, S - m - 6), fill=data if k == idx else sub)
    return hud


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Genera visual_core.gif (holograma de partículas).")
    ap.add_argument("--photo", required=True, help="Foto frontal (se segmenta y se convierte en nube).")
    ap.add_argument("--out", default=str(ROOT / "assets" / "visual_core.gif"))
    ap.add_argument("--tokens", default=str(ROOT / "assets" / "tokens.json"))
    ap.add_argument("--size", type=int, default=400)
    ap.add_argument("--particles", type=int, default=2400)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--trans", type=float, default=1.4, help="Segundos de transición")
    ap.add_argument("--hold", type=float, default=1.0, help="Segundos de reposo")
    ap.add_argument("--colors", type=int, default=48, help="Colores de la paleta GIF")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    tok = json.loads(pathlib.Path(a.tokens).read_text())
    rng = np.random.default_rng(a.seed)
    n = a.particles
    names = ["GCP.CLOUD", "NEURAL.NET", "MCP.SERVER", "IDENTITY"]
    raw = [cloud_target(n, rng), neural_target(n, rng), mcp_target(n, rng), face_target(n, rng, a.photo)]

    # asignación óptima encadenada: cada forma se reordena respecto a la anterior
    shapes = [raw[0]]
    for k in range(1, 4):
        cost = cdist(shapes[-1][0], raw[k][0], "sqeuclidean")
        _, col = linear_sum_assignment(cost)
        shapes.append((raw[k][0][col], raw[k][1][col]))
    cost = cdist(shapes[-1][0], raw[0][0], "sqeuclidean")                      # cierre del bucle
    _, col = linear_sum_assignment(cost)
    back = (raw[0][0][col], raw[0][1][col])

    cloud = Cloud([shapes[0]], rng, a.fps)
    S, SS = a.size, 2
    hud = make_hud(S, tok, load_font(max(9, S // 40)), n)
    seg_frames = int((a.trans + a.hold) * a.fps)
    trans_frames = int(a.trans * a.fps)
    waves = ["x", "y", "r", "x"]
    sequence = [(1, shapes[1]), (2, shapes[2]), (3, shapes[3]), (0, back)]
    frames = []
    for seg, (idx, (pts, bri)) in enumerate(sequence):
        cloud.retarget(pts, bri, waves[seg])
        for f in range(seg_frames):
            cloud.step()
            frames.append(render(cloud, S, SS, tok, (idx, names[idx], f < trans_frames, len(frames) / a.fps), hud))
        print(f"  segmento {seg + 1}/4 -> {names[idx]}", flush=True)

    # paleta global compartida (evita parpadeo de color entre cuadros)
    sample = frames[::max(1, len(frames) // 24)]
    strip = Image.new("RGB", (S, S * len(sample)))
    for i, fr in enumerate(sample):
        strip.paste(fr, (0, i * S))
    pal = strip.quantize(colors=a.colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    q[0].save(out, save_all=True, append_images=q[1:], duration=int(1000 / a.fps), loop=0, optimize=False, disposal=1)
    print(f"OK {out}  {len(frames)} cuadros  {out.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
