#!/usr/bin/env python3
"""
build_portrait.py -- Convierte la foto en retrato vectorial de puntos (halftone hexagonal).

Mapa tonal alineado con la paleta del sistema (assets/tokens.json -> "ramp"):
  sombras -> tinta azulada, medios -> azul acero, luces -> hueso cálido, bordes/siluetas -> glacier.
Salida: assets/portrait.frag y assets/portrait_bright.frag (fragmentos SVG con trazos redondos de longitud cero
agrupados por tono/tamaño: ~110 KB para ~8.5k puntos).

Uso:  python scripts/build_portrait.py foto.png
"""
import cv2, numpy as np, random, json, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
tok = json.loads((ROOT / "assets" / "tokens.json").read_text())
random.seed(11)
img = cv2.imread(sys.argv[1])
if img is None: sys.exit("Uso: python scripts/build_portrait.py foto.png")
H,W = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# --- máscara: GrabCut (piel) UNIDO con umbral de zonas oscuras (gorra, suéter, barba)
m = np.full((H,W), cv2.GC_PR_BGD, np.uint8)
m[:int(H*0.03),:]=cv2.GC_BGD; m[:, :int(W*0.015)]=cv2.GC_BGD; m[:, int(W*0.985):]=cv2.GC_BGD
cv2.ellipse(m,(int(W*.50),int(H*.36)),(int(W*.20),int(H*.34)),0,0,360,cv2.GC_PR_FGD,-1)
m[int(H*.55):, int(W*.12):int(W*.90)] = cv2.GC_PR_FGD
cv2.ellipse(m,(int(W*.50),int(H*.40)),(int(W*.10),int(H*.20)),0,0,360,cv2.GC_FGD,-1)
bg=np.zeros((1,65)); fg=np.zeros((1,65))
cv2.grabCut(img, m, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
gc = np.where((m==cv2.GC_FGD)|(m==cv2.GC_PR_FGD),255,0).astype(np.uint8)
dark = (cv2.GaussianBlur(gray,(0,0),3) < 78).astype(np.uint8)*255
fgm = cv2.bitwise_or(gc, dark)
fgm = cv2.morphologyEx(fgm, cv2.MORPH_CLOSE, np.ones((25,25),np.uint8))
fgm = cv2.morphologyEx(fgm, cv2.MORPH_OPEN, np.ones((11,11),np.uint8))
n,lab,st,_ = cv2.connectedComponentsWithStats(fgm)
fgm = np.where(lab==1+np.argmax(st[1:,cv2.CC_STAT_AREA]),255,0).astype(np.uint8)

# --- tono: CLAHE + realce de detalle (textura del suéter, correa, lentes)
cl = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(8,8)).apply(gray).astype(np.float32)/255
low = cv2.GaussianBlur(cl,(0,0),7)
hp = cl - cv2.GaussianBlur(cl,(0,0),3.0)
L = np.clip(cl + 1.7*(cl-low), 0, 1)**0.82
D = np.clip(0.5 + 3.2*hp, 0, 1)
isdark = gray < 85

N = 132; S = 330; SH = 320; step = S/N
cx0 = 0.12*W; cw = 0.76*W; cy0 = 0.035*H; ch = cw*SH/S
rim = cv2.subtract(fgm, cv2.erode(fgm, np.ones((19,19),np.uint8)))
r = tok['ramp']; COL = [r[0], r[1], r[2], r[4], r[3]]   # sombra, medio, luz-fría, hueso, glacier(borde)
groups = {}
cnt = 0
for j in range(int(SH/step)):
    for i in range(N):
        x = i*step + (step/2 if j%2 else 0) + step/2
        y = j*step + step/2
        px = int(min(W-1, cx0 + x/S*cw)); py = int(min(H-1, cy0 + y/SH*ch))
        if fgm[py,px]==0: continue
        fx, fy = px/W, py/H
        inface = (0.30<fx<0.72) and (0.20<fy<0.60)
        if isdark[py,px]:
            if inface:
                v = 0.06 + 0.30*D[py,px]**2          # barba, bigote, cejas, montura: oscuros y definidos
            elif fy < 0.34:
                v = 0.30 + 0.45*D[py,px]**1.6        # gorra: tono medio con su correa visible
            else:
                v = 0.14 + 0.40*D[py,px]**1.8          # suéter: tenue, con cuello y cremallera
        else:
            v = L[py,px]
        r = 0.40 + 1.05*(v**1.0)
        ci = 0 if v<0.26 else 1 if v<0.50 else 2 if v<0.74 else 3
        if D[py,px]>0.80 and inface and 0.26<fy<0.44: ci = 4   # bordes finos de lentes/barba en turquesa
        if rim[py,px]>0 and v<0.6: ci = 4; r = max(r, 0.95)
        rb = round(r*2)/2 if r<1.2 else round(r*4)/4
        t = random.random()
        an = 'a' if t<.07 else 'b' if t<.14 else 'c' if t<.20 else ''
        groups.setdefault((ci, rb, an), []).append((round(x,1), round(y,1)))
        cnt += 1
out = []; bright = []
for (ci, rb, an), pts in sorted(groups.items()):
    d = ''.join(f'M{x:g} {y:g}h0' for x,y in pts)
    cls = f' class="{an}"' if an else ''
    (bright if ci>=3 else out).append(f'<path{cls} stroke="{COL[ci]}" stroke-width="{round(2*rb,2)}" d="{d}"/>')
open(ROOT/'assets'/'portrait.frag','w').write(''.join(out))
open(ROOT/'assets'/'portrait_bright.frag','w').write(''.join(bright))
print(cnt, 'puntos,', len(groups), 'grupos,', (len(''.join(out))+len(''.join(bright)))//1024, 'KB')

