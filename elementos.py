import json
from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st
from PIL import Image

# ===================== Parámetros de tamaño (ajustables) =====================
# Límites duros basados en viewport; reduce estos valores si aún ves la imagen grande.
IMG_MAX_VH = 46   # alto máximo visible de la imagen en % del alto de ventana (vh) [file:1]
IMG_MAX_VW = 48   # ancho máximo visible de la imagen en % del ancho de ventana (vw) [file:1]

# Reducción del bitmap por software (mejora nitidez y rendimiento al no enviar imágenes enormes).
DOWNSCALE_MAX_W = 1200  # px [file:1]
DOWNSCALE_MAX_H = 800   # px [file:1]

# ===================== Configuración de página y estilos =====================
st.set_page_config(page_title="Partes del motor", layout="wide")  # layout ancho [file:1]

# CSS global: apunta al componente nativo de Streamlit para imágenes y lo limita por viewport.
# Esta regla SÍ se aplica al <img> que renderiza st.image (sin wrappers), con !important para prevalecer.
st.markdown(f"""
<style>
.block-container {{ padding-top: 0.6rem; padding-bottom: 0.2rem; }}  /* compacta márgenes */ 
.stButton > button {{ width: 100%; }}  /* botones a ancho de columna */

.desc-text {{ margin: 0.2rem 0 0.6rem 0; font-size: 0.95rem; opacity: 0.9; }}  /* descripción encima de imagen */

/* Limita TODAS las imágenes de Streamlit (st.image) en la página */
div[data-testid="stImage"] img {{
  max-height: {IMG_MAX_VH}vh !important;   /* nunca mayor que X% del alto de ventana */
  max-width: {IMG_MAX_VW}vw !important;    /* nunca mayor que X% del ancho de ventana */
  width: auto !important;                  /* evita que se estire a 100% de la columna */
  height: auto !important;                 /* mantiene proporción */
  object-fit: contain !important;          /* sin recortes */
  border-radius: 6px;
  display: block;
  margin: 0 auto;                          /* centrado */
}}

/* Afinado en portátiles más estrechos */
@media (max-width: 1280px) {{
  div[data-testid="stImage"] img {{
    max-width: calc({IMG_MAX_VW}vw + 6vw) !important;  /* da un poco más de ancho si la pantalla es pequeña */
  }}
}}
</style>
""", unsafe_allow_html=True)  # la modificación de IMG_MAX_VH/IMG_MAX_VW surte efecto inmediato tras guardar [file:1]

# ===================== Rutas =====================
BASE_DIR = Path(__file__).parent  # raíz del proyecto [file:1]
JSON_PATH = BASE_DIR / "elementos.json"  # archivo JSON con la lista de elementos [file:1]
IMAGES_DIR = BASE_DIR / "images"  # carpeta con imágenes referenciadas en el JSON [file:1]

# ===================== Utilidades =====================
@st.cache_data
def load_elements():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("elements", [])  # estructura esperada: {version, updated_at, elements:[...]} [file:1]

def get_first_image_path(images_list: List[str]) -> Optional[Path]:
    for name in images_list or []:
        p = IMAGES_DIR / name
        if p.exists():
            return p
    return None  # no hay imagen disponible [file:1]

def downscale_for_display(img_path: Path, max_w: int, max_h: int) -> Image.Image:
    """Reduce el bitmap para que el navegador no tenga que escalar imágenes enormes, manteniendo aspecto."""
    img = Image.open(img_path)
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)  # solo reducir, nunca ampliar [file:1]
    if scale < 1.0:
        new_size: Tuple[int, int] = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    return img  # imagen físicamente más pequeña para render fluido [file:1]

# ===================== App =====================
def main():
    st.title("Explorador de elementos")  # encabezado [file:1]

    elements = load_elements()
    if not elements:
        st.error("No se encontraron elementos en elementos.json.")
        return  # manejo si el JSON está vacío o mal formado [file:1]

    if "idx" not in st.session_state:
        st.session_state.idx = 0  # índice inicial [file:1]

    names = [el.get("name", f"Elemento {i}") for i, el in enumerate(elements)]  # nombres para selector [file:1]

    # Columna central relativamente estrecha; reduce el factor si se desea aún menor anchura del área de imagen.
    controls_col, content_col, meta_col = st.columns([1, 1.6, 1])  # distribución de columnas [file:1]

    with controls_col:
        st.subheader("Navegación")  # controles de movimiento [file:1]
        if st.button("Anterior"):
            st.session_state.idx = (st.session_state.idx - 1) % len(elements)  # navegación circular [file:1]
        if st.button("Siguiente"):
            st.session_state.idx = (st.session_state.idx + 1) % len(elements)  # navegación circular [file:1]
        #st.selectbox(
        #    "Ir a",
        #    options=list(range(len(elements))),
        #    format_func=lambda i: names[i],
        #    index=st.session_state.idx,
        #    key="selector",
        #)  # salto directo a cualquier elemento [file:1]

    current = elements[st.session_state.idx]  # elemento activo [file:1]
    name = current.get("name", "Sin nombre")  # nombre [file:1]
    desc = current.get("description", "")  # descripción [file:1]
    img_path = get_first_image_path(current.get("images", []))  # primera imagen existente de la lista [file:1]

    with content_col:
        # Título y descripción arriba, imagen debajo.
        st.subheader(name)  # título del elemento [file:1]
        st.markdown(
            f"<div class='desc-text'>{desc if desc else 'Sin descripción disponible.'}</div>",
            unsafe_allow_html=True
        )  # descripción compacta encima de la imagen [file:1]

        if img_path is not None:
            try:
                img = downscale_for_display(img_path, DOWNSCALE_MAX_W, DOWNSCALE_MAX_H)  # reduce bitmap [file:1]
                # Importante: no usar use_container_width=True para no forzar 100% de la columna.
                st.image(img)  # la regla CSS global limita altura/anchura reales del <img> [file:1]
            except Exception as e:
                st.warning(f"No se pudo abrir la imagen: {img_path.name}. Error: {e}")  # manejo de errores de imagen [file:1]
        else:
            st.warning("No se encontró la imagen en la carpeta 'images'.")  # aviso si falta imagen [file:1]

    with meta_col:
        st.subheader("Detalles")  # metadatos [file:1]
        st.write("ID:", current.get("id"))  # id del elemento [file:1]
        st.write("Imagen:", current.get("images", []))  # nombres de archivo de imagen en el JSON [file:1]

    st.caption("Asegurar que las imágenes existan en ./images con los nombres indicados en elementos.json.")  # recordatorio [file:1]

if __name__ == "__main__":
    main()  # ejecución de la app [file:1]

