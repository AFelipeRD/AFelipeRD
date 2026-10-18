#!/usr/bin/env python3
"""
build_avatar.py -- Foto de perfil de @AFelipeRD: retrato plano REALISTA y pixel art a partir de él.

Es independiente del modelo 3D del carrusel (build_character.py): aquí no se toca ese modelo.

Qué hace más realista la imagen plana:
  * Proporciones de cabeza humana (cráneo + mandíbula + pómulos + nariz con puente, punta y aletas), no de caricatura.
  * Gorra de UNA sola pieza: la visera nace de la cúpula con unión suave (sin costura "pegada"), con costuras de
    seis paneles y pespuntes que continúan de la cúpula a la visera.
  * Gafas con volumen real (marco gris humo con grosor y profundidad), proyectando sombra sobre la cara.
  * Sombras suaves reales (la visera sobre la frente, la nariz, el marco), oclusión ambiental y piel con dispersión.
  * Textura de rostro pintada: ojos CAFÉS con iris, párpados y brillo; cejas de pelo; bigote fino; perilla; barba de
    contorno con vello de días. El reflejo azul vive solo en las lunas (como en la foto), nunca en los ojos.
Luego se pixeliza ese mismo render: paleta limitada, contorno, fondo con tramado y cubos de marca.

Salidas (assets/):  avatar_realistic.png (plano, RGBA)   avatar_pixel.png (foto de perfil, 504 x 504)

Uso:  python scripts/build_avatar.py            SCALE=140 python scripts/build_avatar.py   (vista rápida)
Dependencias:  pip install numpy pillow cairosvg scipy
"""
import json
import math
import os
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from scipy.ndimage import map_coordinates

from build_character import Cam, F32, capsule, ellipsoid, length, pixelize, round_box, smin, union, v3

ROOT = pathlib.Path(__file__).resolve().parent.parent
A = ROOT / "assets"
tok = json.loads((A / "tokens.json").read_text())
rgb_ = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


# ----------------------------------------------------------------------------- modelo (cabeza y hombros realistas)
def rr2d(P, c, h, r):
    q = np.abs(P[:, :2] - np.array(c, F32)) - np.array((h[0] - r, h[1] - r), F32)
    return length(np.maximum(q, 0)) + np.minimum(np.maximum(q[:, 0], q[:, 1]), 0) - r


def frame_ring(c, ho, hi, ro, ri, z0, th):
    def f(P):
        d2 = np.maximum(rr2d(P, c, ho, ro), -rr2d(P, c, hi, ri))
        return np.maximum(d2, np.abs(P[:, 2] - z0) - th)
    return f


def cut_plane(f, y0, slope):                              # conserva lo que queda sobre un plano inclinado (borde de la gorra)
    return lambda P: np.maximum(f(P), (y0 + slope * np.minimum(P[:, 2], 0.0)) - P[:, 1])


def brim():
    e = ellipsoid((0, 2.52, 0.49), (0.51, 0.038, 0.33))
    lip = ellipsoid((0, 2.53, 0.40), (0.50, 0.055, 0.17))

    def f(P):
        Q = P.copy()
        Q[:, 1] = P[:, 1] + 0.45 * P[:, 0] ** 2 + 0.05 * np.maximum(P[:, 2] - 0.14, 0)
        return smin(np.maximum(e(Q), 0.10 - P[:, 2]) * 0.8, lip(P), 0.05)
    return f


def build_scene():
    S = []
    face = union([ellipsoid((0, 2.36, -0.03), (0.505, 0.52, 0.53)), ellipsoid((0, 2.02, 0.05), (0.455, 0.47, 0.43))], 0.14)
    skin = [face, ellipsoid((-0.31, 2.08, 0.30), (0.16, 0.13, 0.14)), ellipsoid((0.31, 2.08, 0.30), (0.16, 0.13, 0.14)),
            ellipsoid((0, 1.62, 0.30), (0.14, 0.09, 0.12)),
            capsule((0, 2.26, 0.40), (0, 2.07, 0.50), 0.040, 0.052), ellipsoid((0, 2.03, 0.535), (0.060, 0.048, 0.060)),
            ellipsoid((-0.060, 2.03, 0.495), (0.038, 0.036, 0.045)), ellipsoid((0.060, 2.03, 0.495), (0.038, 0.036, 0.045)),
            ellipsoid((-0.505, 2.20, -0.05), (0.05, 0.11, 0.07)), ellipsoid((0.505, 2.20, -0.05), (0.05, 0.11, 0.07)),
            capsule((0, 1.35, -0.02), (0, 1.80, -0.02), 0.19, 0.20)]
    S.append((0, union(skin, 0.035)))
    S.append((1, union([round_box((0, 0.98, -0.02), (0.46, 0.34, 0.22), 0.20), ellipsoid((-0.50, 1.30, -0.02), (0.24, 0.22, 0.24)),
                        ellipsoid((0.50, 1.30, -0.02), (0.24, 0.22, 0.24))], 0.10)))
    dome = cut_plane(ellipsoid((0, 2.62, -0.03), (0.532, 0.33, 0.55)), 2.52, 0.28)
    S.append((2, union([dome, brim(), ellipsoid((0, 2.945, -0.03), (0.04, 0.035, 0.04))], 0.05)))
    fr = [frame_ring((s * 0.265, 2.20), (0.225, 0.155), (0.178, 0.108), 0.065, 0.040, 0.47, 0.030) for s in (-1, 1)]
    fr += [capsule((-0.04, 2.27, 0.50), (0.04, 2.27, 0.50), 0.022)]
    for s in (-1, 1):
        fr.append(capsule((s * 0.488, 2.26, 0.47), (s * 0.505, 2.26, -0.03), 0.018))
    S.append((3, union(fr, 0.012)))
    return S


SCENE = build_scene()
ALB = np.array([(0.84, 0.66, 0.54), (0.95, 0.95, 0.93), (0.045, 0.05, 0.062), (0.30, 0.33, 0.38)], F32)
SPEC = np.array([0.16, 0.04, 0.12, 0.70], F32)
SHIN = np.array([26, 14, 36, 60], F32)


def sdf(P, want_mat=False):
    best, mat = None, None
    for m, f in SCENE:
        d = f(P)
        if best is None:
            best, mat = d, (np.full(len(P), m, np.int8) if want_mat else None)
        else:
            if want_mat:
                mat = np.where(d < best, m, mat).astype(np.int8)
            best = np.minimum(best, d)
    return (best, mat) if want_mat else best


# ----------------------------------------------------------------------------- textura de rostro (mapa frontal en unidades del mundo)
TS, TX0, TY1, TW, TH, SS = 1000, -0.62, 2.95, 1240, 1500, 2


def T(x, y):
    return ((x - TX0) * TS * SS, (TY1 - y) * TS * SS)


class Tex:
    def __init__(self):
        self.img = Image.new("RGBA", (TW * SS, TH * SS), (0, 0, 0, 0))

    def layer(self, fn, blur=0.0, mask=None):
        L = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        fn(ImageDraw.Draw(L, "RGBA"))
        if mask is not None:
            L.putalpha(ImageChops.multiply(L.split()[3], mask))
        if blur:
            L = L.filter(ImageFilter.GaussianBlur(blur * SS))
        self.img = Image.alpha_composite(self.img, L)

    def array(self):
        return np.array(self.img.resize((TW, TH), Image.LANCZOS)).astype(F32) / 255.0


def bez(p0, p1, p2, p3, n=18):
    return [((1 - t) ** 3 * p0[0] + 3 * t * (1 - t) ** 2 * p1[0] + 3 * t * t * (1 - t) * p2[0] + t ** 3 * p3[0],
             (1 - t) ** 3 * p0[1] + 3 * t * (1 - t) ** 2 * p1[1] + 3 * t * t * (1 - t) * p2[1] + t ** 3 * p3[1]) for t in [i / n for i in range(n + 1)]]


def paint_face():
    tx = Tex()
    rnd = random.Random(11)
    line = lambda d, pts, col, w: d.line([T(*p) for p in pts], fill=col, width=max(1, int(w * TS * SS)), joint="curve")
    for s in (-1, 1):
        cx, cy = s * 0.215, 2.215
        tx.layer(lambda d: d.ellipse([T(cx - 0.17, cy + 0.085), T(cx + 0.17, cy - 0.085)], fill=(105, 62, 50, 40)), blur=0.02)     # cuenca
        tx.layer(lambda d: d.ellipse([T(cx - 0.07, cy - 0.036), T(cx + 0.07, cy - 0.074)], fill=(110, 70, 60, 48)), blur=0.008)      # ojera
        up = [(cx + 0.072 * math.cos(math.pi * i / 24), cy - 0.002 + 0.036 * math.sin(math.pi * i / 24)) for i in range(25)]
        lo = [(cx + 0.072 * math.cos(math.pi * i / 24), cy - 0.002 - 0.027 * math.sin(math.pi * i / 24)) for i in range(25)]
        eye = up + lo[::-1]
        mask = Image.new("L", tx.img.size, 0)
        ImageDraw.Draw(mask).polygon([T(*p) for p in eye], fill=255)
        tx.layer(lambda d: d.polygon([T(*p) for p in eye], fill=(238, 231, 224, 255)))                                              # esclerótica
        tx.layer(lambda d: d.polygon([T(*p) for p in eye], fill=(80, 52, 44, 80)), blur=0.004, mask=mask)

        def iris(d):
            for r, col in ((0.039, (36, 22, 14, 255)), (0.032, (98, 62, 32, 255)), (0.025, (62, 38, 20, 255)), (0.0135, (7, 5, 4, 255))):
                d.ellipse([T(cx - r, cy + r), T(cx + r, cy - r)], fill=col)
            for _ in range(26):                                                                                                     # vetas ámbar del iris
                a, r = rnd.uniform(0, 6.28), rnd.uniform(0.016, 0.03)
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                d.ellipse([T(x - 0.002, y + 0.002), T(x + 0.002, y - 0.002)], fill=(176, 118, 56, 150))
            d.ellipse([T(cx + 0.006, cy + 0.020), T(cx + 0.022, cy + 0.006)], fill=(255, 255, 255, 235))                              # brillo
            d.ellipse([T(cx - 0.016, cy - 0.006), T(cx - 0.008, cy - 0.014)], fill=(255, 255, 255, 110))
        tx.layer(iris, mask=mask)
        tx.layer(lambda d: line(d, up, (26, 16, 12, 235), 0.0075))                                                                  # párpado superior
        tx.layer(lambda d: line(d, [(cx + s * 0.03 + 0.04 * s * (i / 8), cy + 0.034 + 0.003 * i / 8) for i in range(9)][:0] or up[14:], (18, 11, 8, 240), 0.012))
        tx.layer(lambda d: line(d, lo[3:22], (125, 84, 72, 120), 0.0045))                                                           # párpado inferior
        tx.layer(lambda d: line(d, [(x, y + 0.030) for x, y in up[2:23]], (96, 60, 48, 120), 0.0055), blur=0.0015)                 # pliegue
        # ceja de pelo
        a, b = (-0.44, -0.075) if s < 0 else (0.075, 0.44)
        arc = bez((a, 2.372), (a * 0.7 - 0.02 * s, 2.452), (b * 0.7 + 0.02 * s, 2.462), (b, 2.402)) if s < 0 else \
            bez((a, 2.402), (a * 0.7 - 0.02 * s, 2.462), (b * 0.7 + 0.02 * s, 2.452), (b, 2.372))
        tx.layer(lambda d: line(d, arc, (30, 20, 14, 170), 0.045), blur=0.004)
        def hairs(d):
            for i in range(170):
                k = rnd.uniform(0, 1)
                x, y = arc[min(int(k * 18), 17)]
                nx, ny = arc[min(int(k * 18) + 1, 18)]
                ang = math.atan2(ny - y, nx - x) + rnd.uniform(-0.35, 0.35) + (0.25 if s < 0 else -0.25)
                L = rnd.uniform(0.018, 0.034)
                oy = rnd.uniform(-0.016, 0.018)
                d.line([T(x, y + oy), T(x + L * math.cos(ang), y + oy + L * math.sin(ang))], fill=(24, 15, 10, rnd.randint(150, 235)), width=2)
        tx.layer(hairs)
    # nariz: sombra bajo la punta, fosas, brillo del puente
    tx.layer(lambda d: d.ellipse([T(-0.085, 1.985), T(0.085, 1.955)], fill=(112, 66, 48, 90)), blur=0.01)
    for s in (-1, 1):
        tx.layer(lambda d: d.ellipse([T(s * 0.034 - 0.016, 2.002), T(s * 0.034 + 0.016, 1.986)], fill=(60, 32, 24, 150)), blur=0.002)
    tx.layer(lambda d: line(d, [(0.0, 2.24), (0.0, 2.07)], (255, 235, 215, 34), 0.02), blur=0.008)
    # mejillas con un poco de color
    for s in (-1, 1):
        tx.layer(lambda d: d.ellipse([T(s * 0.30 - 0.11, 2.02), T(s * 0.30 + 0.11, 1.92)], fill=(212, 120, 108, 38)), blur=0.03)
    # bigote fino de puntas caídas
    top = bez((-0.31, 1.862), (-0.23, 1.935), (-0.09, 1.952), (0, 1.918)) + bez((0, 1.918), (0.09, 1.952), (0.23, 1.935), (0.31, 1.862))
    bot = bez((0.31, 1.862), (0.29, 1.828), (0.12, 1.872), (0, 1.884)) + bez((0, 1.884), (-0.12, 1.872), (-0.29, 1.828), (-0.31, 1.862))
    tx.layer(lambda d: d.polygon([T(*p) for p in top + bot], fill=(26, 18, 14, 238)), blur=0.0015)
    def must_hairs(d):
        for i in range(260):
            x, y = top[rnd.randint(0, len(top) - 1)]
            ang = math.radians(rnd.uniform(60, 120)) + (0.5 if x > 0 else -0.5) * 0.4
            L = rnd.uniform(0.008, 0.02)
            d.line([T(x, y), T(x + L * math.cos(ang), y + L * math.sin(ang))], fill=(24, 16, 12, rnd.randint(120, 220)), width=2)
    tx.layer(must_hairs)
    # boca: labios y línea de unión
    tx.layer(lambda d: d.polygon([T(*p) for p in bez((-0.075, 1.846), (-0.03, 1.872), (0.03, 1.872), (0.075, 1.846), 10) + bez((0.075, 1.846), (0.03, 1.838), (-0.03, 1.838), (-0.075, 1.846), 10)], fill=(188, 122, 108, 230)), blur=0.0015)
    tx.layer(lambda d: d.polygon([T(*p) for p in bez((-0.07, 1.842), (-0.03, 1.80), (0.03, 1.80), (0.07, 1.842), 10) + bez((0.07, 1.842), (0.03, 1.848), (-0.03, 1.848), (-0.07, 1.842), 10)], fill=(204, 138, 124, 235)), blur=0.0015)
    tx.layer(lambda d: line(d, bez((-0.08, 1.845), (-0.03, 1.835), (0.03, 1.835), (0.08, 1.845), 10), (96, 52, 46, 220), 0.0045), blur=0.001)
    # perilla vertical y barba de contorno con vello
    tx.layer(lambda d: d.polygon([T(-0.018, 1.775), T(0.018, 1.775), T(0.013, 1.69), T(-0.013, 1.69)], fill=(24, 16, 13, 235)), blur=0.003)
    jaw = [(0.425 * math.cos(math.radians(a)), 2.02 + 0.445 * math.sin(math.radians(a))) for a in range(196, 345, 3)]
    tx.layer(lambda d: line(d, jaw, (24, 17, 14, 225), 0.052), blur=0.004)
    for s in (-1, 1):
        tx.layer(lambda d: line(d, [(s * 0.468, 2.17), (s * 0.452, 2.02), (s * 0.44, 1.95)], (24, 17, 14, 205), 0.034), blur=0.004)
    jp = np.array(jaw)
    def stubble(d):
        for _ in range(5200):
            x, y = rnd.uniform(-0.46, 0.46), rnd.uniform(1.58, 2.12)
            dist = np.min(np.hypot(jp[:, 0] - x, jp[:, 1] - y))
            p = max(0.0, 1 - dist / 0.12) ** 1.4
            if rnd.random() < p * 0.8:
                d.ellipse([T(x - 0.0022, y + 0.0022), T(x + 0.0022, y - 0.0022)], fill=(28, 20, 16, rnd.randint(60, 150)))
        for _ in range(900):
            a = math.radians(rnd.uniform(196, 344))
            x, y = 0.425 * math.cos(a) + rnd.uniform(-0.05, 0.05), 2.02 + 0.445 * math.sin(a) + rnd.uniform(-0.05, 0.05)
            d.ellipse([T(x - 0.003, y + 0.003), T(x + 0.003, y - 0.003)], fill=(22, 15, 12, rnd.randint(110, 200)))
    tx.layer(stubble)
    return tx.array()


# ----------------------------------------------------------------------------- render con sombras suaves
KEY = v3(-0.58, 0.72, 0.62)
KEY /= np.linalg.norm(KEY)
FILL = v3(0.75, 0.15, 0.55)
FILL /= np.linalg.norm(FILL)
TEX = None


def soft_shadow(P, L, k=7.0, steps=24):
    t = np.full(len(P), 0.07, F32)
    res = np.ones(len(P), F32)
    for _ in range(steps):
        h = sdf(P + L * t[:, None])
        res = np.minimum(res, np.clip(k * h / t, 0, 1))
        t = t + np.clip(h, 0.035, 0.15)
    return np.clip(res, 0, 1)


def shade_points(P, d):
    dist, mat = sdf(P, True)
    e = 0.0095                                         # normales suaves: evita ondas del SDF aproximado
    n = np.zeros_like(P)
    for k in ((1, -1, -1), (-1, -1, 1), (-1, 1, -1), (1, 1, 1)):
        kk = v3(*k)
        n += kk * sdf(P + kk * e)[:, None]
    n /= np.maximum(length(n), 1e-6)[:, None]
    albedo = ALB[mat].copy()
    isskin = mat == 0
    if isskin.any():                                                # textura frontal del rostro
        u = (P[isskin, 0] - TX0) * TS
        v = (TY1 - P[isskin, 1]) * TS
        ch = [map_coordinates(TEX[..., c], [v, u], order=1, mode="constant", cval=0.0) for c in range(4)]
        a = ch[3][:, None]
        albedo[isskin] = albedo[isskin] * (1 - a) + np.stack(ch[:3], 1) * a
    fab = (mat == 1) | (mat == 2)                                   # trama de tela: pequeñas perturbaciones de la normal
    if fab.any():
        w = np.stack([np.sin(P[fab, 1] * 210) * np.cos(P[fab, 0] * 190), np.cos(P[fab, 1] * 170) * np.sin(P[fab, 2] * 200), np.sin(P[fab, 0] * 230) * np.cos(P[fab, 1] * 150)], 1)
        n[fab] += 0.014 * w
        n[fab] /= length(n[fab])[:, None]
    ao = np.ones(len(P), F32)
    for h, w in ((0.07, 1.0), (0.14, 0.7), (0.24, 0.45)):
        ao -= 0.40 * w * np.clip(h - sdf(P + n * h), 0, None) / h * 0.5
    ao = np.clip(ao, 0.28, 1)
    sh = soft_shadow(P + n * 0.035, KEY)          # inicio alejado de la superficie: evita bandas de autosombra
    ndl = n @ KEY
    wrap = np.clip((ndl + 0.30) / 1.30, 0, 1)
    fill = np.clip(n @ FILL, 0, 1)
    V = -d
    rim = (1 - np.clip(n @ V, 0, 1)) ** 3
    key = wrap ** 1.25 * (0.22 + 0.78 * sh)
    light = 0.38 * ao + 0.80 * key * (0.55 + 0.45 * ao) + 0.22 * fill * ao
    hv = KEY + V
    hv /= np.linalg.norm(hv)
    ks, shn = SPEC[mat], SHIN[mat]
    spec = np.clip(n @ hv, 0, 1) ** shn * ks * sh * (0.4 + 0.6 * ao)
    col = albedo * light[:, None] * v3(1.0, 0.98, 0.95)
    sss = np.clip(0.55 - ndl, 0, 0.55) * isskin * (0.12 + 0.22 * (1 - sh))                   # dispersión bajo la piel en la zona de penumbra
    col += albedo * sss[:, None] * v3(0.50, 0.16, 0.10)
    col += rim[:, None] * v3(0.07, 0.13, 0.20) * 0.8 + spec[:, None]
    return np.clip(col, 0, 1), light, mat


def render(cam, chunk=40000):
    H, W, S = cam.H, cam.W, cam.S
    u = (np.arange(W) + 0.5) / S - cam.hw
    v = cam.hh - (np.arange(H) + 0.5) / S
    UU, VV = np.meshgrid(u, v)
    O_all = cam.T + UU.reshape(-1, 1) * v3(1, 0, 0) + VV.reshape(-1, 1) * cam.ey - 7.0 * cam.d
    N = len(O_all)
    color, light, alpha = np.zeros((N, 3), F32), np.zeros(N, F32), np.zeros(N, F32)
    mat = np.full(N, -1, np.int8)
    for s0 in range(0, N, chunk):
        O = O_all[s0:s0 + chunk]
        n = len(O)
        t, dmin = np.zeros(n, F32), np.full(n, 1e9, F32)
        Pm = O.copy()
        act = np.arange(n)
        for _ in range(110):
            P = O[act] + t[act, None] * cam.d
            dist = sdf(P) * 0.9
            better = dist < dmin[act]
            dmin[act[better]], Pm[act[better]] = dist[better], P[better]
            t[act] += np.maximum(dist, 0.0006)
            act = act[(dist > 0.0006) & (t[act] < 14)]
            if act.size == 0:
                break
        a = np.clip(1.0 - np.maximum(dmin, 0) * S, 0, 1)
        sel = np.nonzero(a > 0.02)[0]
        if sel.size:
            c, l, m = shade_points(Pm[sel], cam.d)
            color[s0 + sel], light[s0 + sel], mat[s0 + sel], alpha[s0 + sel] = c, l, m, a[sel]
        print(f"  {min(s0 + chunk, N) * 100 // N:3d} %", end="\r", flush=True)
    sh = lambda x: x.reshape(H, W, *x.shape[1:])
    return sh(color), sh(light), sh(mat), sh(alpha)


# ----------------------------------------------------------------------------- lunas, costuras y acabado
def finish(cam, color, light, mat, alpha):
    H, W, S = cam.H, cam.W, cam.S
    img = Image.fromarray((np.clip(color, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    P = lambda x, y, z: cam.px(x, y, z)
    # costuras de seis paneles + pespuntes (negro sobre negro): una sola pieza de la cúpula a la visera
    seam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(seam)
    def dome_z(x, y):
        return -0.03 + 0.55 * math.sqrt(max(0.0, 1 - (x / 0.532) ** 2 - ((y - 2.62) / 0.33) ** 2))
    for xs in (0.0, -0.22, 0.22):
        pts = []
        for i in range(0, 41):
            y = 2.95 - (2.95 - 2.535) * i / 40
            x = xs * (1 - (2.95 - y) / 0.42) if xs else 0.0
            pts.append(P(x, y, dome_z(x, y) + 0.004))
        d.line(pts, fill=(52, 60, 74, 150), width=max(1, int(S * 0.0075)), joint="curve")
    for inset, al in ((0.93, 150), (0.80, 100)):
        pts = []
        for i in range(0, 41):
            th = math.pi * i / 40
            x, z = 0.51 * inset * math.cos(th), 0.49 + 0.33 * inset * math.sin(th)
            pts.append(P(x, 2.52 + 0.036 - 0.45 * x * x - 0.05 * max(z - 0.14, 0), z))
        d.line(pts, fill=(58, 66, 80, al), width=max(1, int(S * 0.006)), joint="curve")
    m = Image.fromarray(((mat == 2) * 255).astype(np.uint8))
    seam.putalpha(ImageChops.multiply(seam.split()[3], m))
    img = Image.alpha_composite(img, seam)
    # lunas: casi transparentes, con reflejo azul del recubrimiento (solo en el vidrio, nunca en los ojos)
    lens = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lens)
    for s in (-1, 1):
        cx = s * 0.265
        pts = []
        for ang_c, (qx, qy) in ((0, (cx + 0.178 - 0.04, 2.20 + 0.108 - 0.04)), (90, (cx - 0.178 + 0.04, 2.20 + 0.108 - 0.04)),
                                (180, (cx - 0.178 + 0.04, 2.20 - 0.108 + 0.04)), (270, (cx + 0.178 - 0.04, 2.20 - 0.108 + 0.04))):
            for i in range(9):
                a = math.radians(ang_c + 90 * i / 8)
                pts.append(P(qx + 0.04 * math.cos(a), qy + 0.04 * math.sin(a), 0.47))
        ld.polygon(pts, fill=(120, 175, 235, 42))
        ld.polygon([P(cx - 0.12, 2.13, 0.47), P(cx - 0.05, 2.30, 0.47), P(cx - 0.02, 2.30, 0.47), P(cx - 0.09, 2.13, 0.47)], fill=(255, 255, 255, 74))
        ld.polygon([P(cx + 0.04, 2.13, 0.47), P(cx + 0.075, 2.26, 0.47), P(cx + 0.09, 2.26, 0.47), P(cx + 0.055, 2.13, 0.47)], fill=(255, 255, 255, 46))
        ld.polygon([P(cx + 0.02, 2.145, 0.47), P(cx + 0.15, 2.145, 0.47), P(cx + 0.165, 2.19, 0.47), P(cx + 0.05, 2.19, 0.47)], fill=(70, 150, 255, 92))   # reflejo azul del recubrimiento
    lens = lens.filter(ImageFilter.GaussianBlur(0.7))
    img = Image.alpha_composite(img, lens)
    arr = np.array(img).astype(F32)
    rng = np.random.default_rng(3)
    arr[..., :3] = np.clip(arr[..., :3] + rng.normal(0, 1.6, arr.shape[:2] + (1,)), 0, 255)       # grano fino de fotografía
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = arr[..., :3].astype(np.uint8)
    out[..., 3] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    return out


# ----------------------------------------------------------------------------- pixel art llamativo
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], F32) / 16.0


def pixel_background(g):
    ramp = [rgb_(c) for c in ("#0A1230", "#10244A", "#163B63", "#1C5878", "#2A7B8A", "#4FB0B8")]
    yy, xx = np.mgrid[0:g, 0:g].astype(F32)
    base = 0.18 + 0.55 * (yy / g)                                                   # degradado vertical
    halo = np.clip(1 - np.hypot((xx - g * 0.5) / (g * 0.46), (yy - g * 0.46) / (g * 0.50)), 0, 1) ** 1.3
    v = np.clip(base * 0.8 + halo * 0.55, 0, 1) * (len(ramp) - 1)
    v = v + (BAYER[yy.astype(int) % 4, xx.astype(int) % 4] - 0.5) * 0.9              # tramado Bayer
    idx = np.clip(np.round(v).astype(int), 0, len(ramp) - 1)
    bg = np.zeros((g, g, 4), np.uint8)
    bg[..., :3] = np.array(ramp, np.uint8)[idx]
    bg[..., 3] = 255
    return bg


def stamp_cube(arr, cx, cy, col):
    """Cubo isométrico de 9 x 10 px con 3 tonos (marca del perfil)."""
    top, left, right = [tuple(min(255, int(c * f)) for c in col) for f in (1.25, 0.92, 0.62)]
    rows = {0: ("..TTT..."[:8],), }
    spr = ["....TT....", "..TTTTTT..", "TTTTTTTTTT", "LLLLRRRRRR"[:10], "LLLLRRRRRR", "LLLLRRRRRR", ".LLLRRRRR.", "..LLRRRR..", "...LRRR...", "....RR...."]
    spr = ["...TT...", ".TTTTTT.", "TTTTTTTT", "LLLRRRRR", "LLLRRRRR", "LLLRRRRR", ".LLRRRR.", "..LRRR.."]
    mp = {"T": top, "L": left, "R": right}
    ink = (8, 10, 16)
    for j, row in enumerate(spr):
        for i, ch in enumerate(row):
            if ch in mp:
                arr[cy + j, cx + i, :3], arr[cy + j, cx + i, 3] = mp[ch], 255
    return arr


def make_pixel(real, cam, g=72):
    bg = pixel_background(g)
    flat = np.array(Image.fromarray(real[..., :3]).filter(ImageFilter.MedianFilter(5)))
    px = pixelize(np.concatenate([flat, real[..., 3:4]], axis=2), (g, g), 44)
    f = px[..., :3].astype(F32)
    f = 255.0 * (f / 255.0) ** 0.86                                              # más luz de piel y de camiseta
    gray = f.mean(axis=2, keepdims=True)
    f = np.clip((gray + (f - gray) * 1.30 - 128) * 1.10 + 128, 0, 255)             # color y contraste para que destaque
    px[..., :3] = f.astype(np.uint8)
    mask = px[..., 3] > 0
    ink = (10, 13, 18)
    inkmask = np.all(px[..., :3] == ink, axis=2) & mask
    k = cam.W / g
    G = lambda x, y, z: (int(round(cam.px(x, y, z)[0] / k - 0.5)), int(round(cam.px(x, y, z)[1] / k - 0.5)))
    # lunas con el tinte azul del recubrimiento (solo en el vidrio)
    for sgn in (-1, 1):
        (x0, y0), (x1, y1) = G(sgn * 0.265 - 0.165, 2.20 + 0.095, 0.47), G(sgn * 0.265 + 0.165, 2.20 - 0.095, 0.47)
        for yy in range(y0 + 1, y1):
            for xx in range(x0 + 1, x1):
                if px[yy, xx, 3] and not inkmask[yy, xx]:
                    px[yy, xx, :3] = (0.72 * px[yy, xx, :3] + 0.28 * np.array((92, 150, 232))).astype(np.uint8)
    # ojos CAFÉS colocados pixel a pixel (esclerótica, iris, pupila, brillo y párpados)
    for sgn in (-1, 1):
        cx, cy = G(sgn * 0.215, 2.215, 0.42)
        put = lambda dx, dy, col: px.__setitem__((cy + dy, cx + dx), (*col, 255))
        for dx in range(-3, 3):
            put(dx, -2, (30, 20, 16))
            put(dx, 0, (240, 233, 226))
            put(dx, -1, (214, 204, 196))
        for dx in range(-2, 2):
            put(dx, 1, (150, 108, 94))
        for dy in (-1, 0):
            for dx in (-1, 0):
                put(dx, dy, (104, 64, 32))
        put(-1, 0, (22, 13, 9))
        put(0, -1, (255, 250, 240))
    # luz de contorno en la cúpula de la gorra (la separa del fondo y la hace más viva)
    dark = (px[..., :3].astype(int).sum(axis=2) < 150) & mask & ~inkmask
    for yy in range(1, g):
        for xx in range(1, g):
            if dark[yy, xx] and (inkmask[yy - 1, xx] or inkmask[yy, xx - 1]) and yy < g * 0.40:
                px[yy, xx, :3] = (70, 104, 150)
    halo = np.zeros_like(mask)
    halo[1:, :] |= inkmask[:-1, :]
    halo[:-1, :] |= inkmask[1:, :]
    halo[:, 1:] |= inkmask[:, :-1]
    halo[:, :-1] |= inkmask[:, 1:]
    halo &= ~mask
    bg[halo, :3] = rgb_(tok["accent-data"])
    comp = Image.fromarray(bg)
    comp.alpha_composite(Image.fromarray(px))
    arr = np.array(comp)
    arr = stamp_cube(arr, 58, 8, rgb_(tok["accent-data"]))
    arr = stamp_cube(arr, 5, 52, rgb_(tok["accent-signal"]))
    for (x, y) in ((10, 10), (63, 40), (8, 36), (62, 22)):                          # destellos
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            arr[y + dy, x + dx, :3] = (255, 244, 214) if (dx, dy) == (0, 0) else rgb_(tok["accent-signal"])
    return Image.fromarray(arr).resize((g * 7, g * 7), Image.NEAREST)


def main():
    global TEX
    S = int(os.environ.get("SCALE", 380))
    print("textura de rostro...")
    TEX = paint_face()
    cam = Cam(0.0, 2.24, 0.86, 0.86, S, pitch_deg=6.0)
    print("render...")
    color, light, mat, alpha = render(cam)
    real = finish(cam, color, light, mat, alpha)
    Image.fromarray(real).save(A / "avatar_realistic.png")
    make_pixel(real, cam).save(A / "avatar_pixel.png")
    for f in ("avatar_realistic.png", "avatar_pixel.png"):
        print(f"  {f:24s}{(A / f).stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
