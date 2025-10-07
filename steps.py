import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import streamlit as st
from PIL import Image

# ===================== Página =====================
st.set_page_config(page_title="Guía de desmontaje", layout="wide")  # layout ancho [web:1]

# ===================== Estilos: centrados reales =====================
st.markdown("""
<style>
/* Limitar ancho total y centrar todo el contenido */
.main .block-container { max-width: 1100px; margin: 0 auto; padding-top: 0.5rem; }

/* Títulos, texto e imágenes centrados */
.center-title { text-align: left; margin: 0.2rem 0 0.3rem 0; }
.center-text  { text-align: left; }
.desc-text    { text-align: left; margin: 0.2rem 0 0.6rem 0; font-size: 0.95rem; opacity: 0.9; }

/* Fila de navegación: dos botones juntos y centrados (sin columnas 50/50) */
.nav-row { display: flex; justify-content: flex-start; align-items: center; gap: 0.6rem; margin: 0.2rem 0 0.35rem 0; }
.nav-row .stButton > button { padding: 0.45rem 1.0rem; border-radius: 8px; }

/* Contenedor de imagen centrado con ancho máximo común */
.img-wrap      { display:flex; justify-content:center; }
.img-inner     { width: min(100%, 960px); }  /* mismo ancho visual para todas las imágenes */
.img-inner img {
  width: 100% !important;
  height: auto !important;
  max-height: clamp(220px, 46vh, 900px);
  object-fit: contain !important;
  border-radius: 6px;
  display: block;
  margin: 0 auto;
}

/* Móvil */
@media (max-width: 768px) {
  .main .block-container { padding-top: 0.4rem; }
  .img-inner img { max-height: clamp(220px, 54vh, 900px); }
}
</style>
""", unsafe_allow_html=True)  # centrado de botones e imágenes [web:21]

# ===================== Rutas =====================
BASE_DIR = Path(__file__).parent
STEPS_JSON = BASE_DIR / "steps.json"
ELEMENTS_JSON = BASE_DIR / "elementos.json"
STEPS_IMG_DIR = BASE_DIR / "imagenes montaje"
if not STEPS_IMG_DIR.exists():
    alt = BASE_DIR / "imagenes_montaje"
    if alt.exists():
        STEPS_IMG_DIR = alt
ELEMENTS_IMG_DIR = BASE_DIR / "images"

# ===================== Utilidades =====================
@st.cache_data
def load_steps() -> List[dict]:
    with open(STEPS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("steps", [])  # contiene lista elements por paso para saber cuántas piezas hay [file:34]

@st.cache_data
def load_elements_catalog() -> Dict[str, dict]:
    with open(ELEMENTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {el.get("id"): el for el in data.get("elements", []) if el.get("id")}  # catálogo por id [web:15]

def downscale_for_display(img_path: Path, max_w: int = 1200, max_h: int = 800) -> Image.Image:
    img = Image.open(img_path)
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img  # reducción para rendimiento manteniendo nitidez [web:21]

def first_existing(dir_path: Path, names: List[str]) -> Optional[Path]:
    for name in names or []:
        p = dir_path / name
        if p.exists():
            return p
    return None  # primera imagen válida [web:21]

def all_existing(dir_path: Path, names: List[str]) -> List[Path]:
    return [dir_path / n for n in (names or []) if (dir_path / n).exists()]  # lista de imágenes existentes [web:21]

def topo_sort_steps(steps: List[dict]) -> List[dict]:
    id_to_step: Dict[str, dict] = {s.get("id"): s for s in steps if s.get("id")}
    indeg: Dict[str, int] = {sid: 0 for sid in id_to_step.keys()}
    for s in steps:
        sid = s.get("id"); deps = s.get("depends_on", []) or []
        for d in deps:
            if d in indeg:
                indeg[sid] += 1
    queue = [sid for sid, d in indeg.items() if d == 0]
    seen, ordered = set(queue), []
    i = 0
    while i < len(queue):
        sid = queue[i]; i += 1; ordered.append(sid)
        for t in steps:
            tid = t.get("id")
            if tid and tid != sid:
                deps = t.get("depends_on", []) or []
                if sid in deps and tid in indeg:
                    indeg[tid] -= 1
                    if indeg[tid] == 0 and tid not in seen:
                        queue.append(tid); seen.add(tid)
    for s in steps:
        sid = s.get("id")
        if sid and sid not in ordered:
            ordered.append(sid)
    return [id_to_step[sid] for sid in ordered if sid in id_to_step]  # orden por dependencias estable [web:1]

def step_images_paths(step: dict) -> List[Path]:
    return all_existing(STEPS_IMG_DIR, step.get("images", []))  # imágenes del paso [web:21]

def element_info_and_image(element_id: str):
    cat = load_elements_catalog()
    el = cat.get(element_id, {})
    name = el.get("name", element_id or "Desconocido")
    desc = el.get("description", "")
    img_path = first_existing(ELEMENTS_IMG_DIR, el.get("images", []))
    return name, desc, img_path  # datos e imagen de pieza del catálogo [web:15]

# ===================== App =====================
def main():
    # Título centrado
    st.markdown("<h1 class='center-title'>Guía de desmontaje</h1>", unsafe_allow_html=True)  # título centrado [web:1]

    steps = load_steps()
    if not steps:
        st.error("No se encontraron pasos en steps.json.")
        return  # validación de datos [file:34]

    ordered_steps = topo_sort_steps(steps)

    # Estado de navegación
    if "sidx" not in st.session_state:
        st.session_state.sidx = 0  # índice del paso actual [web:15]

    # Botones Anterior/Siguiente realmente centrados y juntos (sin columnas 50/50)
    st.markdown("<div class='nav-row'>", unsafe_allow_html=True)  # fila flex a la izquierda [web:38]
    b_prev = st.button("Anterior", key="prev_step")                # [web:24]
    b_next = st.button("Siguiente", key="next_step")               # [web:24]
    st.markdown("</div>", unsafe_allow_html=True)                  # [web:38]
    
    if b_prev:
        st.session_state.sidx = (st.session_state.sidx - 1) % len(ordered_steps)  # [web:24]
    if b_next:
        st.session_state.sidx = (st.session_state.sidx + 1) % len(ordered_steps)  # [web:24]

    # Paso actual
    step = ordered_steps[st.session_state.sidx]
    step_id = step.get("id", "")
    step_title = step.get("title", step_id or "Paso")
    step_desc = step.get("description", "")
    step_elements = step.get("elements", []) or []  # para contar piezas y decidir botones [file:34]

    # Reset del índice de pieza al cambiar de paso
    if "last_step_id" not in st.session_state or st.session_state.last_step_id != step_id:
        st.session_state.last_step_id = step_id
        st.session_state[f"eidx_{step_id}"] = 0  # índice de pieza actual [web:15]

    # Info del paso centrada
    st.markdown(f"<h2 class='center-title'>{step_title}</h2>", unsafe_allow_html=True)  # subtítulo centrado [web:1]
    if step_desc:
        st.markdown(f"<div class='desc-text'>{step_desc}</div>", unsafe_allow_html=True)  # descripción centrada [web:1]

    # Imagen del paso en contenedor centrado y ancho unificado
    s_paths = step_images_paths(step)
    if s_paths:
        try:
            img = downscale_for_display(s_paths[0])
            st.markdown("<div class='img-wrap'><div class='img-inner'>", unsafe_allow_html=True)  # contenedor centrado [web:21]
            st.image(img, width="stretch")  # ocupar ancho del contenedor común [web:21]
            st.markdown("</div></div>", unsafe_allow_html=True)  # cierre contenedor [web:21]
        except Exception as e:
            st.warning(f"No se pudo abrir la imagen del paso: {s_paths[0].name}. Error: {e}")  # manejo de error [web:21]
    else:
        st.info("Este paso no tiene imagen disponible.")  # no hay imagen para el paso [file:34]

    # Sección piezas centrada
    st.markdown("<h3 class='center-title'>Piezas</h3>", unsafe_allow_html=True)  # encabezado piezas [web:1]
    if step_elements:
        ekey = f"eidx_{step_id}"
        eidx = st.session_state.get(ekey, 0) % len(step_elements)  # índice acotado [web:15]

        # Botones de piezas centrados y juntos solo si hay varias
        if len(step_elements) > 1:  # cuenta en steps.json para decidir visibilidad [file:34]
            st.markdown("<div class='nav-row'>", unsafe_allow_html=True)  # fila flex centrada [web:1]
            b_prev_piece = st.button("Pieza anterior", key=f"prev_piece_{step_id}")  # [web:24]
            b_next_piece = st.button("Siguiente pieza", key=f"next_piece_{step_id}")  # [web:24]
            st.markdown("</div>", unsafe_allow_html=True)  # [web:38]
        
            if b_prev_piece:
                st.session_state[ekey] = (eidx - 1) % len(step_elements)  # [web:24]
                eidx = st.session_state[ekey]  # actualizar índice local  # [web:29]
            if b_next_piece:
                st.session_state[ekey] = (eidx + 1) % len(step_elements)  # [web:24]
                eidx = st.session_state[ekey]  # actualizar índice local  # [web:29]
        current_eid = step_elements[eidx]
        name, desc, e_img = element_info_and_image(current_eid)

        st.markdown(f"<div class='center-text'><strong>{name}</strong></div>", unsafe_allow_html=True)  # nombre centrado [web:1]
        if desc:
            st.markdown(f"<div class='desc-text'>{desc}</div>", unsafe_allow_html=True)  # descripción centrada [web:1]

        # Imagen de pieza en contenedor centrado y ancho unificado
        if e_img is not None:
            try:
                img_el = downscale_for_display(e_img)
                st.markdown("<div class='img-wrap'><div class='img-inner'>", unsafe_allow_html=True)  # contenedor centrado [web:21]
                st.image(img_el, width="stretch")  # ancho consistente para alinear con la imagen del paso [web:21]
                st.markdown("</div></div>", unsafe_allow_html=True)  # cierre contenedor [web:21]
            except Exception as e:
                st.warning(f"No se pudo abrir la imagen de la pieza: {e_img.name}. Error: {e}")  # manejo de error [web:21]
        else:
            st.info("Imagen de la pieza no encontrada en ./images.")  # sin imagen de pieza [web:15]

    else:
        st.info("Sin piezas asociadas en este paso.")  # no hay elementos para este paso [file:34]

if __name__ == "__main__":
    main()  # ejecutar app [web:1]


