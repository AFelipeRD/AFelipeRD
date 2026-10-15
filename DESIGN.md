# Sistema de diseño · @AFelipeRD

Una sola fuente de verdad (`assets/tokens.json`, generada por `scripts/design_tokens.py`) alimenta todos los SVG, el GIF y el workflow de métricas. Cambiar un tono en un lugar cambia todo el perfil.

## 1. Paleta (OKLCH, verificada por cálculo)

La paleta no parte de colores elegidos a ojo. Se genera en OKLCH (espacio perceptualmente uniforme) con tres reglas:

1. **Neutros "tinta":** matiz frío fijo (258°) y croma casi nulo. Dan profundidad sin parecer azul neón.
2. **Acento de señal (ámbar, matiz 72°):** reservado para actividad, atención y energía. Es el único cálido, por eso se lee de inmediato.
3. **Acento de datos (glacier, matiz 209.5°):** el ámbar + 137.5° (ángulo áureo). Es el matiz más separado del ámbar que no cae en el par magenta/cian típico del synthwave.

| Token | Hex | Rol | Contraste (peor superficie) |
|---|---|---|---|
| `surface-0` | `#090C11` | fondo base | — |
| `surface-1` | `#12161C` | tarjetas y nodos | — |
| `surface-2` | `#1C2127` | elementos elevados, pistas de barras | — |
| `border-subtle` | `#2E333A` | divisores decorativos | decorativo |
| `border-strong` | `#595F68` | bordes funcionales, escalas | 3.04:1 (WCAG 1.4.11) |
| `text-primary` | `#EBE7DF` | títulos (blanco cálido) | 13.14:1 AAA |
| `text-secondary` | `#C1BDB7` | cuerpo | 8.66:1 AAA |
| `text-muted` | `#A8ABB0` | metadatos | 7.03:1 AAA |
| `accent-signal` | `#F8AC3D` | señal / actividad | 8.46:1 AAA |
| `accent-data` | `#5FC9DA` | datos / flujo | 8.37:1 AAA |

Los textos se ajustan por búsqueda de luminosidad hasta superar 7:1 contra `surface-2` (la peor superficie), así que pasan AAA sobre las tres. El tema claro (`prefers-color-scheme: light`) tiene su propio conjunto, también AAA (mínimo 7.01:1).

**Rampa tonal del retrato y el holograma** (sombra → luz): `#212E42` · `#3E5B79` · `#588EA8` · `#5FC9DA` · `#EFEBE2`. La velocidad tiñe las partículas hacia ámbar: en reposo la imagen es fría; en movimiento, cálida.

## 2. Tipografía

Escala modular 1.25 sobre base 12 px: **10 · 12 · 15 · 19 · 23 · 29**.

- Monoespaciada (`JetBrains Mono` → `Geist Mono` → `SF Mono` → sistema): etiquetas, metadatos, datos. Tracking +0.10–0.14 em en mayúsculas pequeñas.
- Sans (`Inter` → `Geist` → sistema): títulos y valores. Tracking −0.01 a −0.025 em en tamaños grandes.
- GitHub no carga fuentes web dentro de SVG usados como `<img>`; por eso cada pila termina en fuentes del sistema.

## 3. Espaciado

Rejilla de 8 pt con medio paso de 4: **4 · 8 · 16 · 24 · 32 · 48 · 64**. Márgenes de tarjeta 24, radios 4/8/12, contenido alineado a la misma columna (x = 24) en todas las tarjetas.

## 4. Movimiento

- **Resorte real:** curva de resorte amortiguado (ζ = 0.6) muestreada y exportada como CSS `linear(...)`. Se declara después de un `cubic-bezier(0.23, 1, 0.32, 1)` de respaldo para navegadores sin soporte.
- **Escalonado:** cada elemento entra con un retardo creciente (0.06–0.12 s por paso).
- **Entradas:** `rise` (8 px) y `pop` (escala .55 → 1). **Bucles:** flujo punteado, pulso, paquete de datos que "salta" entre etapas.
- **Estado final por defecto:** las animaciones solo definen el estado inicial (`backwards`). Si un visor no ejecuta CSS, todo se ve completo y quieto.
- **`prefers-reduced-motion`:** desactiva todas las animaciones.
- **Holograma (GIF):** cada partícula es un resorte con masa e inercia, con rigidez distinta por partícula, ola de arranque direccional, asignación óptima entre formas (algoritmo húngaro) y estela por velocidad.

## 5. Dirección de arte del avatar

Para transformar la fotografía en una pieza coherente con el sistema:

1. **Toma:** luz de estudio suave, luz principal a unos 45° y luz de contorno trasera tenue que separe la silueta del fondo. Fondo liso y mate (gris medio funciona bien para segmentar). Encuadre al pecho, ojos al tercio superior.
2. **Exclusión de fondo:** GrabCut para piel, unido a un umbral de zonas oscuras para gorra, barba y ropa; luego el componente conectado más grande. El fondo nunca entra en el mapa de puntos.
3. **Mapa tonal:** CLAHE (clip 3.2) + realce de detalle (×1.7) + gamma 0.82. Las sombras van a la tinta azulada, los medios al azul acero y las luces al hueso cálido; un contorno fino en glacier separa la silueta.
4. **Zonas oscuras con criterio:** la barba y las cejas se mantienen oscuras y definidas; la gorra queda en un tono medio con su correa visible; el suéter, tenue, para que la cara domine.
5. **Marco:** escalas perimetrales de 00 a 100, corchetes de esquina en ámbar, retículas en el centro de cada borde y dos marcadores que barren las escalas con resorte (uno por eje, desfasados). Una luz glacier recorre el perímetro en 11 s; todo es sutil para no competir con el rostro.

## 6. Pipeline

```bash
pip install numpy pillow opencv-python-headless scipy cairosvg   # cairosvg solo para vistas previas
python scripts/design_tokens.py                    # tokens + verificación WCAG
python scripts/build_portrait.py foto.png          # retrato vectorial
python scripts/build_assets.py                     # header, avatar, marco y 4 módulos
python scripts/generate_hologram.py --photo foto.png   # assets/visual_core.gif
python scripts/build_activity.py --placeholder     # estado vacío inicial (luego lo reemplaza el workflow)
```

## 7. Límites a tener en cuenta

- GitHub elimina `<svg>` en línea del Markdown: todo componente es un archivo `.svg` referenciado con `<img>`.
- Las animaciones se verifican en un navegador, no en la vista previa de los scripts (que solo valida el diseño estático).
- `activity.svg` se regenera con datos reales cada 6 horas; hasta la primera ejecución muestra un estado vacío honesto ("—"), no cifras inventadas.
- El gráfico de barras del módulo de ML es ilustrativo y está rotulado como tal.
