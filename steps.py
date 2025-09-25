import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import streamlit as st
from PIL import Image

# ===================== Parámetros de tamaño (ajustables) =====================
# Límites duros basados en viewport; reduce estos valores si aún ves la imagen grande.
IMG_MAX_VH = 46   # alto máximo visible de la imagen en % del alto de ventana (vh) [file:2]
IMG_MAX_VW = 48   # ancho máximo visible de la imagen en % del ancho de ventana (vw) [file:2]

# Reducción del bitmap por software (mejora nitidez y rendimiento al no enviar imágenes enormes).
DOWNSCALE_MAX_W = 1200  # px [file:2]
DOWNSCALE_MAX_H = 800   # px [file:2]

# ===================== Configuración de página y estilos =====================
st.set_page_config(page_title="Guía de desmontaje", layout="wide")  # layout ancho [file:2]

# CSS global: limita el <img> que renderiza st.image por viewport (sin recortes) y compacta márgenes.
st.markdown(f"""
<style>
.block-container {{ padding-top: 0.6rem; padding-bottom: 0.2rem; }}
.stButton > button {{ width: 100%; }}

.section-title {{ margin: 0.2rem 0 0.2rem 0; }}
.desc-text {{ margin: 0.2rem 0 0.6rem 0; font-size: 0.95rem; opacity: 0.9; }}

div[data-testid="stImage"] img {{
  max-height: {IMG_MAX_VH}vh !important;
  max-width: {IMG_MAX_VW}vw !important;
  width: auto !important;
  height: auto !important;
  object-fit: contain !important;
  border-radius: 6px;
  display: block;
  margin: 0 auto;
}}

@media (max-width: 1280px) {{
  div[data-testid="stImage"] img {{
    max-width: calc({IMG_MAX_VW}vw + 6vw) !important;
  }}
}}
</style>
""", unsafe_allow_html=True)  # límites por viewport y estilo compacto [file:2]

# ===================== Rutas =====================
BASE_DIR = Path(__file__).parent  # raíz del proyecto [file:2]
STEPS_JSON = BASE_DIR / "steps.json"  # archivo de pasos (workflow) [file:2]
ELEMENTS_JSON = BASE_DIR / "elementos.json"  # catálogo de piezas [file:3]

# carpeta de fotos de los pasos; soporta "imagenes montaje" (principal) y "imagenes_montaje" (fallback)
STEPS_IMG_DIR = BASE_DIR / "imagenes montaje"  # fotos del desmontaje [file:2]
if not STEPS_IMG_DIR.exists():
    alt = BASE_DIR / "imagenes_montaje"
    if alt.exists():
        STEPS_IMG_DIR = alt  # fallback si el nombre no tiene espacio [file:2]

ELEMENTS_IMG_DIR = BASE_DIR / "images"  # fotos del catálogo de piezas (mesa/mon) [file:3]

# ===================== Utilidades =====================
@st.cache_data
def load_steps() -> List[dict]:
    with open(STEPS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("steps", [])  # estructura: {version, updated_at, steps:[...]} [file:2]

@st.cache_data
def load_elements_catalog() -> Dict[str, dict]:
    with open(ELEMENTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    catalog = {}
    for el in data.get("elements", []):
        el_id = el.get("id")
        if el_id:
            catalog[el_id] = el
    return catalog  # clave = id de pieza [file:3]

def downscale_for_display(img_path: Path, max_w: int, max_h: int) -> Image.Image:
    """Reduce el bitmap para que el navegador no tenga que escalar imágenes enormes, manteniendo aspecto."""
    img = Image.open(img_path)
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)  # solo reducir [file:2]
    if scale < 1.0:
        new_size: Tuple[int, int] = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    return img  # imagen físicamente más pequeña [file:2]

def first_existing(dir_path: Path, names: List[str]) -> Optional[Path]:
    for name in names or []:
        p = dir_path / name
        if p.exists():
            return p
    return None  # si nada existe [file:3]

def all_existing(dir_path: Path, names: List[str]) -> List[Path]:
    return [dir_path / n for n in (names or []) if (dir_path / n).exists()]  # lista filtrada existente [file:2]

def topo_sort_steps(steps: List[dict]) -> List[dict]:
    """
    Orden topológico estable por depends_on.
    Si hay dependencias inexistentes, se ignoran en el cálculo pero se mantienen para mostrar.
    """
    id_to_step: Dict[str, dict] = {s.get("id"): s for s in steps if s.get("id")}
    indeg: Dict[str, int] = {sid: 0 for sid in id_to_step.keys()}
    # calcular indegree solo para dependencias presentes
    for s in steps:
        sid = s.get("id")
        deps = s.get("depends_on", []) or []
        for d in deps:
            if d in indeg:
                indeg[sid] += 1

    # cola inicial preservando el orden de aparición
    queue: List[str] = [sid for sid, d in indeg.items() if d == 0]
    seen: Set[str] = set(queue)
    ordered: List[str] = []

    # Kahn estable
    i = 0
    while i < len(queue):
        sid = queue[i]; i += 1
        ordered.append(sid)
        # disminuir indegree de quienes dependen de sid
        for t in steps:
            tid = t.get("id")
            if tid and tid != sid:
                deps = t.get("depends_on", []) or []
                if sid in deps and tid in indeg:
                    indeg[tid] -= 1
                    if indeg[tid] == 0 and tid not in seen:
                        queue.append(tid); seen.add(tid)

    # añadir cualquier resto (ciclos o ids raros) en orden de aparición
    for s in steps:
        sid = s.get("id")
        if sid and sid not in ordered:
            ordered.append(sid)

    return [id_to_step[sid] for sid in ordered if sid in id_to_step]  # lista ordenada final [file:2]

def step_images_paths(step: dict) -> List[Path]:
    return all_existing(STEPS_IMG_DIR, step.get("images", []))  # fotos del paso desde carpeta de montaje [file:2]

def element_info_and_image(element_id: str) -> Tuple[str, str, Optional[Path]]:
    cat = load_elements_catalog()
    el = cat.get(element_id, {})
    name = el.get("name", element_id or "Desconocido")
    desc = el.get("description", "")
    img_path = first_existing(ELEMENTS_IMG_DIR, el.get("images", []))
    return name, desc, img_path  # datos del catálogo y primera imagen existente [file:3]

# ===================== App =====================
def main():
    st.title("Guía de desmontaje")  # encabezado principal [file:2]

    steps = load_steps()
    if not steps:
        st.error("No se encontraron pasos en steps.json.")
        return  # sin datos de workflow [file:2]

    # Orden topológico por dependencias
    ordered_steps = topo_sort_steps(steps)  # respeta depends_on y orden de entrada [file:2]

    # índice de navegación
    if "sidx" not in st.session_state:
        st.session_state.sidx = 0  # índice de paso [file:2]

    # títulos para selector
    titles = [s.get("title", s.get("id", f"Paso {i}")) for i, s in enumerate(ordered_steps)]  # nombres de pasos [file:2]

    # Layout de 3 columnas
    controls_col, content_col, meta_col = st.columns([1, 2, 1])  # columna central moderada para gobernar tamaño [file:2]

    with controls_col:
        st.subheader("Navegación")  # controles [file:2]
        if st.button("Anterior"):
            st.session_state.sidx = (st.session_state.sidx - 1) % len(ordered_steps)  # circular [file:2]
        if st.button("Siguiente"):
            st.session_state.sidx = (st.session_state.sidx + 1) % len(ordered_steps)  # circular [file:2]
        st.selectbox(
            "Ir a",
            options=list(range(len(ordered_steps))),
            format_func=lambda i: titles[i],
            index=st.session_state.sidx,
            key="step_selector",
        )  # salto directo por título [file:2]

    step = ordered_steps[st.session_state.sidx]  # paso actual [file:2]
    step_id = step.get("id", "")
    step_title = step.get("title", step_id or "Paso")  # título [file:2]
    step_desc = step.get("description", "")  # descripción [file:2]
    step_deps = step.get("depends_on", []) or []  # dependencias [file:2]
    step_elements = step.get("elements", []) or []  # ids de piezas relacionadas [file:2]

    with content_col:
        # Título del paso y su descripción arriba
        st.subheader(step_title)  # encabezado del paso [file:2]
        st.markdown(f"<div class='desc-text'>{step_desc if step_desc else 'Sin descripción disponible.'}</div>",
                    unsafe_allow_html=True)  # descripción del paso [file:2]

        # Imágenes del paso (montaje) — puede haber varias
        s_paths = step_images_paths(step)
        if s_paths:
            st.markdown("#### Imágenes del paso", help="Procedencia: carpeta 'imagenes montaje'")  # sección imagen paso [file:2]
            # Mostrar en 1–2 columnas según cantidad
            ncols = 2 if len(s_paths) >= 2 else 1
            cols = st.columns(ncols)
            for i, p in enumerate(s_paths):
                try:
                    img = downscale_for_display(p, DOWNSCALE_MAX_W, DOWNSCALE_MAX_H)
                    with cols[i % ncols]:
                        st.image(img)  # limitado por CSS global (vh/vw)
                except Exception as e:
                    st.warning(f"No se pudo abrir la imagen del paso: {p.name}. Error: {e}")
        else:
            st.info("Este paso no tiene imágenes disponibles en la carpeta de montaje.")

        # Sección de piezas asociadas (catálogo elementos.json)
        if step_elements:
            st.markdown("#### Piezas relacionadas", help="Datos y fotos desde elementos.json")
            for eid in step_elements:
                name, desc, e_img = element_info_and_image(eid)
                st.markdown(f"**{name}**")  # nombre de la pieza (negrita breve)
                if desc:
                    st.markdown(f"<div class='desc-text'>{desc}</div>", unsafe_allow_html=True)
                if e_img is not None:
                    try:
                        img_el = downscale_for_display(e_img, DOWNSCALE_MAX_W, DOWNSCALE_MAX_H)
                        st.image(img_el)  # limitado por CSS global (vh/vw)
                    except Exception as e:
                        st.warning(f"No se pudo abrir la imagen de la pieza: {e_img.name}. Error: {e}")
                else:
                    st.info("Imagen de la pieza no encontrada en ./images.")

    with meta_col:
        st.subheader("Detalles")  # panel lateral [file:2]
        st.write("Paso ID:", step_id)
        st.write("Depende de:", step_deps if step_deps else "—")
        st.write("Piezas:", step_elements if step_elements else "—")
        st.caption("Fotos del paso en ./imagenes montaje; fotos de piezas en ./images.")  # recordatorio rutas [file:2]

    st.caption("Fuente de pasos: steps.json; catálogo de piezas: elementos.json.")  # nota final [file:2][file:3]

if __name__ == "__main__":
    main()  # ejecución [file:2]
