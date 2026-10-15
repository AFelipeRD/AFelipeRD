#!/usr/bin/env python3
"""
Sistema de diseño de @AFelipeRD: tokens algorítmicos en OKLCH.

- Neutros: matiz frío fijo (258°) con croma mínimo -> superficies "tinta".
- Acento primario ("signal"): matiz 72° (ámbar). Señal de actividad / atención.
- Acento de datos ("glacier"): 72° + 137.5° (ángulo áureo) = 209.5°. Es el matiz
  perceptualmente más separado del ámbar sin caer en el par neón magenta/cian.
- Tinta de texto: blanco cálido (matiz 85°), evita el azul frío de #FFF sobre fondo oscuro.

Todo texto se ajusta por búsqueda de luminosidad hasta WCAG AAA (>= 7:1) contra la peor
superficie (surface-2). Los bordes funcionales se validan a >= 3:1 (WCAG 1.4.11).

Uso:  python scripts/design_tokens.py     ->  escribe assets/tokens.json
"""
import json
import math
import pathlib


def oklch_to_linear(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def in_gamut(rgb):
    return all(-1e-4 <= c <= 1 + 1e-4 for c in rgb)


def to_hex(L, C, h):
    c = C  # mapeo de gamut: reducir croma hasta entrar en sRGB
    while c > 0 and not in_gamut(oklch_to_linear(L, c, h)):
        c -= 0.002
    rgb = oklch_to_linear(L, max(c, 0), h)
    enc = lambda v: 12.92 * v if v <= 0.0031308 else 1.055 * (max(v, 0) ** (1 / 2.4)) - 0.055
    return "#" + "".join(f"{round(min(max(enc(v), 0), 1) * 255):02X}" for v in rgb)


def luminance(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def ensure(L0, C, h, bg, target, step=0.004, up=True):
    """Mueve L hasta que el contraste contra bg alcance el objetivo."""
    L = L0
    while contrast(to_hex(L, C, h), bg) < target and 0.01 < L < 0.99:
        L += step if up else -step
    return to_hex(L, C, h)


def spring_linear(zeta=0.6, freq=1.15, samples=36):
    """Resorte amortiguado (masa 1) normalizado -> CSS linear() con overshoot natural."""
    w = 2 * math.pi * freq
    wd = w * math.sqrt(1 - zeta ** 2)
    pts = []
    for i in range(samples + 1):
        t = i / samples * 1.45
        x = 1 - math.exp(-zeta * w * t) * (math.cos(wd * t) + zeta * w / wd * math.sin(wd * t))
        pts.append(round(x, 3))
    pts[-1] = 1
    return "linear(" + ", ".join(str(p) for p in pts) + ")"


def build():
    H_NEUTRAL, H_SIGNAL, H_INK = 258, 72, 85
    H_DATA = (H_SIGNAL + 137.5) % 360
    tok = {}
    tok["surface-0"] = to_hex(0.155, 0.012, H_NEUTRAL)
    tok["surface-1"] = to_hex(0.200, 0.013, H_NEUTRAL)
    tok["surface-2"] = to_hex(0.245, 0.014, H_NEUTRAL)
    tok["border-subtle"] = to_hex(0.320, 0.014, H_NEUTRAL)
    tok["border-strong"] = ensure(0.440, 0.016, H_NEUTRAL, tok["surface-0"], 3.0)
    worst = tok["surface-2"]
    tok["text-primary"] = ensure(0.93, 0.012, H_INK, worst, 12.0)
    tok["text-secondary"] = ensure(0.80, 0.010, H_INK, worst, 8.5)
    tok["text-muted"] = ensure(0.70, 0.008, H_NEUTRAL, worst, 7.0)
    tok["accent-signal"] = ensure(0.80, 0.150, H_SIGNAL, worst, 7.0)
    tok["accent-data"] = ensure(0.78, 0.100, H_DATA, worst, 7.0)
    tok["accent-signal-dim"] = to_hex(0.55, 0.095, H_SIGNAL)
    tok["accent-data-dim"] = to_hex(0.50, 0.065, H_DATA)
    # rampa tonal para retrato / holograma (sombra -> luz)
    tok["ramp"] = [to_hex(L, C, h) for L, C, h in
                   [(0.30, 0.040, H_NEUTRAL), (0.46, 0.060, 250), (0.62, 0.070, 230),
                    (0.78, 0.100, H_DATA), (0.94, 0.012, H_INK)]]
    # tema claro (SVG como <img> respeta prefers-color-scheme)
    light = {
        "surface-0": to_hex(0.985, 0.004, H_NEUTRAL),
        "surface-1": to_hex(0.965, 0.006, H_NEUTRAL),
        "border-subtle": to_hex(0.88, 0.008, H_NEUTRAL),
        "border-strong": to_hex(0.62, 0.012, H_NEUTRAL),
    }
    lb = light["surface-1"]
    light["text-primary"] = ensure(0.30, 0.012, H_NEUTRAL, lb, 12.0, up=False)
    light["text-secondary"] = ensure(0.42, 0.010, H_NEUTRAL, lb, 8.5, up=False)
    light["text-muted"] = ensure(0.46, 0.008, H_NEUTRAL, lb, 7.0, up=False)
    light["accent-signal"] = ensure(0.50, 0.130, H_SIGNAL, lb, 7.0, up=False)
    light["accent-data"] = ensure(0.46, 0.095, H_DATA, lb, 7.0, up=False)
    tok["light"] = light
    tok["type"] = {
        "ratio": 1.25, "base": 12, "scale": [10, 12, 15, 19, 23, 29],
        "mono": "'JetBrains Mono','Geist Mono','SF Mono',ui-monospace,Menlo,Consolas,monospace",
        "sans": "'Inter','Geist',system-ui,-apple-system,'Segoe UI',sans-serif",
    }
    tok["space"] = {"grid": 8, "half": 4, "steps": [4, 8, 16, 24, 32, 48, 64]}
    tok["radius"] = {"sm": 4, "md": 8, "lg": 12}
    tok["motion"] = {
        "ease-out": "cubic-bezier(0.23, 1, 0.32, 1)",
        "ease-in-out": "cubic-bezier(0.77, 0, 0.175, 1)",
        "duration": {"fast": 0.15, "base": 0.25, "slow": 0.4, "enter": 0.6},
        "spring": spring_linear(),
    }
    rows = []
    for fg in ("text-primary", "text-secondary", "text-muted", "accent-signal", "accent-data"):
        for bg in ("surface-0", "surface-1", "surface-2"):
            rows.append({"fg": fg, "bg": bg, "ratio": round(contrast(tok[fg], tok[bg]), 2)})
    rows.append({"fg": "border-strong", "bg": "surface-0",
                 "ratio": round(contrast(tok["border-strong"], tok["surface-0"]), 2)})
    for fg in ("text-primary", "text-secondary", "text-muted", "accent-signal", "accent-data"):
        rows.append({"fg": "light." + fg, "bg": "light.surface-1",
                     "ratio": round(contrast(light[fg], light["surface-1"]), 2)})
    tok["_contrast"] = rows
    return tok


if __name__ == "__main__":
    tok = build()
    out = pathlib.Path(__file__).resolve().parent.parent / "assets" / "tokens.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(tok, indent=2, ensure_ascii=False))
    for k in ("surface-0", "surface-1", "surface-2", "border-subtle", "border-strong", "text-primary",
              "text-secondary", "text-muted", "accent-signal", "accent-data", "accent-signal-dim", "accent-data-dim"):
        print(f"{k:19s}{tok[k]}")
    print("ramp ", tok["ramp"])
    print("light", tok["light"])
    for r in tok["_contrast"]:
        v = r["ratio"]
        print(f"{r['fg']:22s} sobre {r['bg']:16s} {v:6.2f}:1", "AAA" if v >= 7 else ("UI>=3" if v >= 3 else "FALLA"))
