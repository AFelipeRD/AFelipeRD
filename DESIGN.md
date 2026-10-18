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
- **Holograma 3D (WebP animado dentro de `hero.svg`):** cada partícula tiene (x, y, z) y es un resorte con masa e inercia, rigidez distinta por partícula, ola de arranque direccional y asignación óptima entre formas (algoritmo húngaro). La cámara orbita (yaw ±31°, 2 ciclos por bucle, empalme perfecto) con perspectiva, suelo con rejilla, atenuación por profundidad y brillo (bloom). El rostro es un relieve (elipsoide facial + luminosidad).

## 5. Profundidad y movimiento en los SVG

- **Bloques isométricos:** cada prisma tiene cara superior clara, izquierda media y derecha oscura, más sombra proyectada que se contrae cuando el bloque flota. Es la misma luz (arriba-izquierda) en toda la escena.
- **Esferas con volumen:** gradiente radial con brillo especular desplazado a arriba-izquierda (grafo de commits).
- **Órbitas:** anillos elípticos que precesan, con partículas que cambian de tamaño y opacidad según su posición (delante/detrás), lo que lee como giroscopio 3D.
- **Paralaje:** dos capas de puntos que derivan a velocidades distintas detrás del avatar.
- **Todo en bucle y sin clic:** carrusel de tecnologías, destello perimetral, barrido de escáner, flujo de datos, paquetes que "saltan" entre etapas, barras que crecen con resorte y brillo diagonal en las tarjetas de repos.
- **Movimiento reducido:** `RESPECT_REDUCED_MOTION` en `scripts/ds.py` (por defecto `False`: el perfil siempre se anima). Ponlo en `True` para respetar la preferencia del sistema de cada visitante.

## 6. Presupuesto de ancho

GitHub muestra el README en una columna de unos 700 a 900 px según la ventana. Todo se diseña a **700 px** y las imágenes se escalan con `width="100%"`. Cada bloque (hero, deck, actividad) es un único SVG con su layout interno, porque GitHub apila las imágenes sueltas y alarga el perfil.

## 7. Dirección de arte del retrato

1. **Toma:** luz de estudio suave, principal a unos 45°, contraluz tenue; fondo liso y mate; encuadre al pecho.
2. **Exclusión de fondo:** GrabCut (piel) unido a un umbral de zonas oscuras (gorra, barba, ropa) y el componente conectado más grande.
3. **Mapa tonal:** CLAHE (clip 3.2) + realce de detalle (×1.7) + gamma 0.82; sombras a tinta azulada, medios a azul acero, luces a hueso cálido, silueta en glacier.
4. **Criterio por zona:** barba y cejas oscuras y definidas; gorra en tono medio con la correa visible; suéter tenue.

## 8. Pipeline

```bash
pip install numpy pillow opencv-python-headless scipy cairosvg
python scripts/design_tokens.py                          # tokens + verificación WCAG
python scripts/build_portrait.py foto.png                # retrato vectorial
python scripts/build_character.py                        # personaje 3D + mapas del holograma
python scripts/build_avatar.py                           # retrato realista + pixel art de perfil
python scripts/generate_hologram.py                      # assets/visual_core.webp (holograma 3D)
python scripts/build_assets.py                           # assets/hero.svg y assets/deck.svg
python scripts/build_activity.py --placeholder           # estado vacío inicial (luego lo llena el workflow)
```

## 9. Límites a tener en cuenta

- GitHub elimina `<svg>` en línea del Markdown: cada componente es un archivo `.svg` cargado con `<img>`.
- `hero.svg` incrusta el WebP animado en base64 (~2.5 MB). GitHub rechaza imágenes de más de unos 5 MB en su proxy; si regeneras con más calidad o más cuadros, comprueba el tamaño.
- Las tarjetas de repos y la actividad se regeneran con datos reales cada 6 horas. Hasta la primera ejecución muestran un estado vacío honesto.
- El gráfico de barras del módulo de ML es ilustrativo y está rotulado así.
- Las animaciones no se pueden verificar con la vista previa de los scripts (solo valida el diseño estático): ábrelos en un navegador.

## 10. Personaje de marca

Personaje 3D estático modelado al estilo de los juegos de Mario (referencia: Luigi en T-pose) a partir de una selfie frontal. No se mueve: el movimiento vive en el carrusel de partículas del holograma, donde es la cuarta forma (`AFELIPE.RD`).

- **Modelo:** formas redondeadas (elipsoides, cápsulas, cajas redondeadas) con unión suave, renderizadas por ray-marching: luz principal arriba-izquierda, relleno frío, luz de contorno, oclusión ambiental y brillo especular.
- **Rasgos de la foto:** gorra negra completa puesta al frente (visera visible, costuras de seis paneles), gafas rectangulares de marco grueso gris humo con lunas de reflejo azul, cejas gruesas, ojos castaños, bigote fino de puntas caídas, perilla vertical, barba de contorno de mandíbula, camiseta blanca oversize, joggers oscuros, tenis negros de suela blanca y manilla de cuentas.
- **Pixel art:** sale del mismo render (promedio por área, paleta de 36 a 40 colores, contorno de 1 px), así que la cara es idéntica en ambas versiones.
- **Archivos:** `character_3d.png` (cuerpo), `character_bust.png` (busto), `avatar_pixel.png` (foto de perfil de GitHub, 504 x 504), `character_pixel_full.png`, y `character_color.png` / `character_depth.png` (entradas del holograma).
- **Ajustes rápidos** (en `scripts/build_character.py`): color de camiseta (`ALB`, material 1), forma de la gorra (`dome`, `bent_brim`), tamaño de las gafas (`paint_character`, bloque de gafas). Resolución: `SCALE=240`; vista rápida: `SCALE=100`.

## 11. Foto de perfil (retrato realista y pixel art)

`scripts/build_avatar.py` es independiente del modelo 3D del carrusel.

- **Retrato plano realista:** cabeza con proporciones humanas (cráneo, mandíbula, pómulos y nariz con puente, punta y aletas), gorra de una sola pieza (la visera nace de la cúpula con unión suave y las costuras continúan hasta la visera), gafas con volumen real que proyectan sombra, sombras suaves, oclusión ambiental y piel con dispersión. Ojos cafés pintados con iris, párpados y brillo; el reflejo azul vive solo en las lunas.
- **Pixel art:** sale de ese retrato (mediana, paleta de 44 colores, contorno de 1 px), con los ojos cafés colocados pixel a pixel, tinte azul en las lunas, fondo con tramado Bayer, cubos de marca y destellos. Resultado: `assets/avatar_pixel.png` (504 x 504, foto de perfil de GitHub).
- **Uso:** `python scripts/build_avatar.py` (requiere `scipy`). `SCALE=140` para una vista rápida.

## 12. Repos del README (config en un solo archivo)

La lista de proyectos que muestran las tarjetas animadas está en `repos.json`. El workflow `activity` lee ese archivo cada 6 horas (y cuando cambia): regenera las tarjetas con la descripción, el lenguaje y las estrellas reales de cada repo, borra las tarjetas de repos que ya no están y reescribe el bloque entre `<!-- REPOS:START -->` y `<!-- REPOS:END -->` del README. Para cambiar un proyecto solo hay que editar `repos.json`.

`.gitattributes` marca `assets/**` como generado para que GitHub no cuente esos archivos en las estadísticas de lenguajes del repo.
