import os

import streamlit as st
import requests
import pandas as pd
import io
from datetime import date

# ==============================================================================
# CONFIGURACION
# ==============================================================================
API_URL       = os.getenv("API_URL")
HISTORY_LIMIT = 10
CONN_OPTIONS  = ["Serie", "Paralelo", "Serie-Paralelo", "Estrella"]
MAT_OPTIONS   = ["Cobre", "Aluminio"]
PHASE_OPTIONS = ["Monofasico", "Trifasico"]

st.set_page_config(page_title="Gestion de Bobinados", layout="wide", page_icon="⚡")

# ==============================================================================
# API
# ==============================================================================
def api(method: str, path: str, **kwargs):
    return requests.request(
        method,
        f"{API_URL}{path}",
        headers={"X-API-Key": st.session_state.get("api_key", "")},
        timeout=10,
        **kwargs,
    )

@st.cache_data(ttl=60, show_spinner=False)
def fetch_motors(api_key: str) -> list:
    r = requests.get(API_URL, headers={"X-API-Key": api_key}, timeout=10)
    r.raise_for_status()
    return r.json()

def invalidate_cache():
    fetch_motors.clear()

# ==============================================================================
# AUTENTICACION
# ==============================================================================
def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.write("")
        st.write("")
        st.markdown("## Gestion de Bobinados")
        st.write("")
        with st.form("login_form"):
            pwd = st.text_input("Contrasena", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
        if submitted:
            try:
                r = requests.get(API_URL, headers={"X-API-Key": pwd}, timeout=5)
                if r.status_code == 200:
                    st.session_state.authenticated = True
                    st.session_state.api_key = pwd
                    st.rerun()
                else:
                    st.error("Contrasena incorrecta.")
            except Exception as e:
                st.error(f"Error de conexion: {e}")
    return False

# ==============================================================================
# ESTADO DE SESION
# ==============================================================================
_UI_DEFAULTS = {
    "history_search":  "",
    "selected_row_id": None,
    "active_motor_id": None,
    "detail_open":     False,
    "motors_list":     [],
}

# Prefijo f_ = formulario de alta
# Es una funcion para que date.today() se evalue en el momento del reset,
# no al importar el modulo (si fuera dict fijo la fecha quedaria congelada).
def _form_defaults() -> dict:
    return {
        "f_owner":  "",
        "f_date":   date.today(),
        "f_brand":  "",
        "f_serial": "",
        "f_desc":   "",
        "f_phases": "Trifasico",
        "f_slots":  36,
        "f_pid":    0.0,
        "f_power":  "",
        "f_body":   "",
        "f_ped":    0.0,
        "f_rpm":    1500,
        "f_volt":   "380",
        "f_fb":     "",
        "f_curr":   0.0,
        "f_pl":     0.0,
        "f_rb":     "",
        "f_conn":   "Serie",
        "f_mat":    "Cobre",
        "f_weight": 0.0,
        "f_dl":     False,
        "f_ec":     0.0,
        "f_at":     0.0,
    }

def init_state():
    for k, v in {**_UI_DEFAULTS, **_form_defaults()}.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("new_num_pass", 1)
    st.session_state.setdefault("new_num_wire", 1)

def reset_new_form():
    st.session_state.update(_form_defaults())
    for k in [k for k in st.session_state if k.startswith(("new_cp_", "new_cw_"))]:
        del st.session_state[k]
    st.session_state["new_num_pass"] = 1
    st.session_state["new_num_wire"] = 1

def close_detail(rerun: bool = True):
    st.session_state.detail_open     = False
    st.session_state.active_motor_id = None
    st.session_state.selected_row_id = None
    st.session_state.pop("_edit_loaded_id", None)
    if rerun:
        st.rerun()

# ==============================================================================
# UTILIDADES
# ==============================================================================
def fmt(v, suffix: str = "") -> str:
    if v is None or (isinstance(v, str) and not v.strip()):
        return "-"
    return f"{v}{suffix}"

def kv(label: str, value, suffix: str = "") -> str:
    return f"**{label}:** {fmt(value, suffix)}"

def yesno(v) -> str:
    return "Si" if v else "No"

def phases_ui_to_api(txt: str) -> int:
    return 3 if str(txt).lower().startswith("tri") else 1

def phases_api_to_ui(v) -> str:
    return "Trifasico" if str(v).strip() in ("3", "trifasico", "trifásico") else "Monofasico"

def vol_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)

def show_list_as_df(rows: list, col_map: dict):
    if not rows:
        st.caption("Sin datos")
        return
    df = pd.DataFrame(rows).rename(columns=col_map)
    cols = [v for v in col_map.values() if v in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

# ==============================================================================
# CONSTRUCCION DE PAYLOAD
# ==============================================================================
def collect_passes(prefix: str, n: int) -> list:
    return [
        {"pass_length": int(st.session_state.get(f"{prefix}cp_l_{i}", 0)),
         "pass_turn":   int(st.session_state.get(f"{prefix}cp_t_{i}", 0))}
        for i in range(n)
        if int(st.session_state.get(f"{prefix}cp_l_{i}", 0)) > 0
    ]

def collect_wires(prefix: str, n: int) -> list:
    return [
        {"wire_quantity": int(st.session_state.get(f"{prefix}cw_q_{i}", 0)),
         "wire_diameter": float(st.session_state.get(f"{prefix}cw_d_{i}", 0.0))}
        for i in range(n)
        if int(st.session_state.get(f"{prefix}cw_q_{i}", 0)) > 0
    ]

def build_payload(pfx: str, passes: list, wires: list) -> dict:
    ss = st.session_state
    ec = float(ss.get(f"{pfx}ec", 0.0))
    return {
        "power":           ss.get(f"{pfx}power", ""),
        "phases":          phases_ui_to_api(ss.get(f"{pfx}phases", "Monofasico")),
        "rpm":             int(ss.get(f"{pfx}rpm", 0)),
        "voltage":         str(ss.get(f"{pfx}volt", "")).strip(),
        "nominal_current": float(ss.get(f"{pfx}curr", 0.0)),
        "general": {
            "owner":         ss.get(f"{pfx}owner", ""),
            "brand":         ss.get(f"{pfx}brand", ""),
            "description":   ss.get(f"{pfx}desc", ""),
            "serial_number": ss.get(f"{pfx}serial", ""),
            "date":          str(ss.get(f"{pfx}date")),
        },
        "chassis": {
            "body":                    ss.get(f"{pfx}body", ""),
            "slots":                   int(ss.get(f"{pfx}slots", 0)),
            "plate_internal_diameter": float(ss.get(f"{pfx}pid", 0.0)),
            "plate_external_diameter": float(ss.get(f"{pfx}ped", 0.0)),
            "plate_length":            float(ss.get(f"{pfx}pl", 0.0)),
            "rear_bearing":            ss.get(f"{pfx}rb", ""),
            "front_bearing":           ss.get(f"{pfx}fb", ""),
        },
        "winding": {
            "connection":   ss.get(f"{pfx}conn", "Serie"),
            "material":     ss.get(f"{pfx}mat", "Cobre"),
            "double_layer": bool(ss.get(f"{pfx}dl", False)),
            "coil_weight":  float(ss.get(f"{pfx}weight", 0.0)),
            "passes":       passes,
            "wires":        wires,
        },
        "empty_test": {
            "empty_current":   ec,
            "applied_tension": float(ss.get(f"{pfx}at", 0.0)),
        } if ec > 0 else None,
    }

# ==============================================================================
# WIDGET: PASOS + ALAMBRES (reutilizable con prefijo)
# ==============================================================================
def render_passes_wires(prefix: str):
    nk_p = f"{prefix}num_pass"
    nk_w = f"{prefix}num_wire"
    st.session_state.setdefault(nk_p, 1)
    st.session_state.setdefault(nk_w, 1)

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**Pasos**")
            for i in range(st.session_state[nk_p]):
                s1, s2 = st.columns(2)
                s1.number_input("Largo",   min_value=0, max_value=2000, step=1, key=f"{prefix}cp_l_{i}")
                s2.number_input("Vueltas", min_value=0, max_value=2000, step=1, key=f"{prefix}cp_t_{i}")
            b1, b2 = st.columns(2)
            if b1.button("Quitar", key=f"{prefix}rem_cp", use_container_width=True):
                if st.session_state[nk_p] > 1:
                    st.session_state[nk_p] -= 1
                    last = st.session_state[nk_p]
                    st.session_state.pop(f"{prefix}cp_l_{last}", None)
                    st.session_state.pop(f"{prefix}cp_t_{last}", None)
                    st.rerun()
            if b2.button("Agregar", key=f"{prefix}add_cp", use_container_width=True):
                if st.session_state[nk_p] < 12:
                    st.session_state[nk_p] += 1
                    st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("**Alambres**")
            for i in range(st.session_state[nk_w]):
                s1, s2 = st.columns(2)
                s1.number_input("Cant.",    min_value=0,   max_value=50,  step=1,    key=f"{prefix}cw_q_{i}")
                s2.number_input("Diam. mm", min_value=0.0, max_value=10.0, step=0.01, format="%.2f", key=f"{prefix}cw_d_{i}")
            b1, b2 = st.columns(2)
            if b1.button("Quitar", key=f"{prefix}rem_cw", use_container_width=True):
                if st.session_state[nk_w] > 1:
                    st.session_state[nk_w] -= 1
                    last = st.session_state[nk_w]
                    st.session_state.pop(f"{prefix}cw_q_{last}", None)
                    st.session_state.pop(f"{prefix}cw_d_{last}", None)
                    st.rerun()
            if b2.button("Agregar", key=f"{prefix}add_cw", use_container_width=True):
                if st.session_state[nk_w] < 12:
                    st.session_state[nk_w] += 1
                    st.rerun()

# ==============================================================================
# FORMULARIO UNIFICADO (alta y edicion usan el mismo)
# ==============================================================================
def render_motor_form(pfx: str):
    """
    Renderiza todos los campos del formulario.
      pfx="f_"  -> alta (prefijo dinamico "new_")
      pfx="e_"  -> edicion (prefijo dinamico "edit_")
    """
    dyn = "new_" if pfx == "f_" else "edit_"

    with st.container(border=True):
        st.subheader("Datos Generales")
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Propietario", key=f"{pfx}owner")
        c2.date_input("Fecha",       key=f"{pfx}date")
        c3.text_input("Marca",       key=f"{pfx}brand")
        c4.text_input("N° Serie",    key=f"{pfx}serial")
        st.text_area("Anotaciones",  key=f"{pfx}desc")

    with st.container(border=True):
        st.subheader("Datos del Motor")
        c1, c2, c3, c4 = st.columns(4)
        c1.selectbox("Fases",              PHASE_OPTIONS, key=f"{pfx}phases")
        c1.number_input("Ranuras",         min_value=0,   max_value=120,    step=1,    key=f"{pfx}slots")
        c1.number_input("Diam. Int (mm)",  min_value=0.0, max_value=1000.0, step=0.01, key=f"{pfx}pid")
        c2.text_input("Potencia",          placeholder="Ej: 5.5HP",                   key=f"{pfx}power")
        c2.text_input("Cuerpo",            placeholder="Ej: C90",                     key=f"{pfx}body")
        c2.number_input("Diam. Ext (mm)",  min_value=0.0, max_value=1000.0, step=0.01, key=f"{pfx}ped")
        c3.number_input("RPM",             min_value=0,   max_value=6000,   step=10,   key=f"{pfx}rpm")
        c3.text_input("Voltaje (V)",       placeholder="Ej: 380",                     key=f"{pfx}volt")
        c3.text_input("Rod. Delantero",                                                key=f"{pfx}fb")
        c4.number_input("Amperaje (A)",    min_value=0.0, max_value=500.0,  step=0.1,  key=f"{pfx}curr")
        c4.number_input("Largo Paq. (mm)", min_value=0.0, max_value=1000.0, step=0.01, key=f"{pfx}pl")
        c4.text_input("Rod. Trasero",                                                  key=f"{pfx}rb")

    with st.container(border=True):
        st.subheader("Bobinado")
        c1, c2, c3, c4 = st.columns(4, vertical_alignment="bottom")
        c1.selectbox("Conexion",  CONN_OPTIONS, key=f"{pfx}conn")
        c2.selectbox("Material",  MAT_OPTIONS,  key=f"{pfx}mat")
        c3.number_input("Peso (g)", min_value=0.0, max_value=100000.0, step=10.0, key=f"{pfx}weight")
        c4.checkbox("Doble Capa",                                                  key=f"{pfx}dl")
        render_passes_wires(dyn)

    with st.expander("Test de Vacio"):
        c1, c2 = st.columns(2)
        c1.number_input("Corriente (A)", min_value=0.0, max_value=200.0,  step=0.01, key=f"{pfx}ec")
        c2.number_input("Tension (V)",   min_value=0.0, max_value=2000.0, step=1.0,  key=f"{pfx}at")

# ==============================================================================
# CALLBACKS
# ==============================================================================
def on_create():
    n_p = st.session_state.get("new_num_pass", 1)
    n_w = st.session_state.get("new_num_wire", 1)
    payload = build_payload("f_", collect_passes("new_", n_p), collect_wires("new_", n_w))
    try:
        r = api("POST", "", json=payload)
        if r.status_code in (200, 201):
            invalidate_cache()
            reset_new_form()
            st.toast("Motor guardado con exito.", icon="✅")
        else:
            st.toast(f"Error: {r.text}", icon="❌")
    except Exception as e:
        st.toast(f"Error de conexion: {e}", icon="❌")

def on_save_edit(m_id: int):
    n_p = st.session_state.get("edit_num_pass", 1)
    n_w = st.session_state.get("edit_num_wire", 1)
    payload = build_payload("e_", collect_passes("edit_", n_p), collect_wires("edit_", n_w))
    try:
        r = api("PUT", f"/{m_id}", json=payload)
        if r.status_code in (200, 201, 204):
            invalidate_cache()
            st.session_state.pop("_edit_loaded_id", None)
            st.toast("Motor actualizado con exito.", icon="✅")
        else:
            st.toast(f"Error al guardar: {r.text}", icon="❌")
    except Exception as e:
        st.toast(f"Error de conexion: {e}", icon="❌")

# ==============================================================================
# PRECARGA DEL FORMULARIO DE EDICION
# ==============================================================================
def preload_edit(motor: dict):
    """Carga datos del motor en session_state con prefijo e_. Solo una vez por motor."""
    m_id = motor.get("id")
    if st.session_state.get("_edit_loaded_id") == m_id:
        return

    gen   = motor.get("general")    or {}
    chas  = motor.get("chassis")    or {}
    win   = motor.get("winding")    or {}
    empty = motor.get("empty_test") or {}

    try:
        parsed_date = pd.Timestamp(gen.get("date")).date()
    except Exception:
        parsed_date = date.today()

    updates = {
        "e_owner":  gen.get("owner", ""),
        "e_date":   parsed_date,
        "e_brand":  gen.get("brand", ""),
        "e_serial": gen.get("serial_number", ""),
        "e_desc":   gen.get("description", ""),
        "e_phases": phases_api_to_ui(motor.get("phases", 3)),
        "e_slots":  int(chas.get("slots") or 0),
        "e_pid":    float(chas.get("plate_internal_diameter") or 0.0),
        "e_power":  str(motor.get("power", "") or ""),
        "e_body":   str(chas.get("body", "") or ""),
        "e_ped":    float(chas.get("plate_external_diameter") or 0.0),
        "e_rpm":    int(motor.get("rpm") or 0),
        "e_volt":   vol_str(motor.get("voltage")),
        "e_fb":     str(chas.get("front_bearing", "") or ""),
        "e_curr":   float(motor.get("nominal_current") or 0.0),
        "e_pl":     float(chas.get("plate_length") or 0.0),
        "e_rb":     str(chas.get("rear_bearing", "") or ""),
        "e_conn":   str(win.get("connection", "Serie") or "Serie"),
        "e_mat":    str(win.get("material", "Cobre") or "Cobre"),
        "e_weight": float(win.get("coil_weight") or 0.0),
        "e_dl":     bool(win.get("double_layer", False)),
        "e_ec":     float(empty.get("empty_current") or 0.0),
        "e_at":     float(empty.get("applied_tension") or 0.0),
    }
    st.session_state.update(updates)

    # Pasos
    passes = win.get("passes") or []
    for k in [k for k in st.session_state if k.startswith("edit_cp_")]:
        del st.session_state[k]
    st.session_state["edit_num_pass"] = max(len(passes), 1)
    for i, p in enumerate(passes):
        st.session_state[f"edit_cp_l_{i}"] = int(p.get("pass_length", 0))
        st.session_state[f"edit_cp_t_{i}"] = int(p.get("pass_turn", 0))

    # Alambres
    wires = win.get("wires") or []
    for k in [k for k in st.session_state if k.startswith("edit_cw_")]:
        del st.session_state[k]
    st.session_state["edit_num_wire"] = max(len(wires), 1)
    for i, w in enumerate(wires):
        st.session_state[f"edit_cw_q_{i}"] = int(w.get("wire_quantity", 0))
        st.session_state[f"edit_cw_d_{i}"] = float(w.get("wire_diameter", 0.0))

    st.session_state["_edit_loaded_id"] = m_id

# ==============================================================================
# VISTA LECTURA DE UN MOTOR
# ==============================================================================
def field(label: str, value, suffix: str = "") -> str:
    """Renderiza un campo como label gris encima y valor abajo, estilo ficha."""
    v = fmt(value, suffix)
    return (
        f"<div style='margin-bottom:12px'>"        f"<div style='font-size:0.72rem;color:#888;text-transform:uppercase;"
        f"letter-spacing:.05em;margin-bottom:2px'>{label}</div>"        f"<div style='font-size:0.97rem;font-weight:500'>{v}</div>"        f"</div>"
    )

def fields_row(pairs: list):
    """Renderiza una fila de (label, value[, suffix]) en columnas iguales."""
    cols = st.columns(len(pairs))
    for col, item in zip(cols, pairs):
        label = item[0]; value = item[1]; suffix = item[2] if len(item) > 2 else ""
        col.markdown(field(label, value, suffix), unsafe_allow_html=True)

def section(title: str):
    st.markdown(
        f"<p style='font-size:0.75rem;font-weight:600;color:#888;"
        f"text-transform:uppercase;letter-spacing:.08em;"
        f"margin:18px 0 10px'>{title}</p>",
        unsafe_allow_html=True,
    )

def render_vista(motor: dict):
    gen   = motor.get("general")    or {}
    chas  = motor.get("chassis")    or {}
    win   = motor.get("winding")    or {}
    empty = motor.get("empty_test") or {}

    with st.container(border=True):
        section("General")
        fields_row([
            ("Propietario", gen.get("owner")),
            ("Fecha",       gen.get("date")),
            ("Marca",       gen.get("brand")),
            ("N° Serie",    gen.get("serial_number")),
        ])
        desc = gen.get("description")
        if desc and str(desc).strip():
            st.markdown(field("Anotaciones", desc), unsafe_allow_html=True)

    with st.container(border=True):
        section("Motor")
        fields_row([
            ("Potencia",  motor.get("power")),
            ("Fases",     phases_api_to_ui(motor.get("phases"))),
            ("RPM",       motor.get("rpm")),
            ("Voltaje",   motor.get("voltage"), " V"),
            ("Amperaje",  motor.get("nominal_current"), " A"),
        ])
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        fields_row([
            ("Cuerpo",      chas.get("body")),
            ("Ranuras",     chas.get("slots")),
            ("Diam. Int",   chas.get("plate_internal_diameter"), " mm"),
            ("Diam. Ext",   chas.get("plate_external_diameter"), " mm"),
            ("Largo Paq.",  chas.get("plate_length"), " mm"),
        ])
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        fields_row([
            ("Rod. Delantero", chas.get("front_bearing")),
            ("Rod. Trasero",   chas.get("rear_bearing")),
            ("", None), ("", None), ("", None),
        ])

    with st.container(border=True):
        section("Bobinado")
        fields_row([
            ("Conexion",    win.get("connection")),
            ("Material",    win.get("material")),
            ("Peso",        win.get("coil_weight"), " g"),
            ("Doble Capa",  yesno(win.get("double_layer"))),
        ])
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        col_p, col_w = st.columns(2)
        with col_p:
            st.markdown("<div style='font-size:0.78rem;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px'>Pasos</div>", unsafe_allow_html=True)
            show_list_as_df(win.get("passes") or [], {"pass_length": "Largo", "pass_turn": "Vueltas"})
        with col_w:
            st.markdown("<div style='font-size:0.78rem;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px'>Alambres</div>", unsafe_allow_html=True)
            show_list_as_df(win.get("wires") or [], {"wire_quantity": "Cant.", "wire_diameter": "Diam."})

    if empty.get("empty_current") or empty.get("applied_tension"):
        with st.container(border=True):
            section("Test de Vacio")
            fields_row([
                ("Corriente", empty.get("empty_current"),   " A"),
                ("Tension",   empty.get("applied_tension"), " V"),
            ])

# ==============================================================================
# FICHA TECNICA
# ==============================================================================
def render_motor_detail(m_id: int):
    motor = next((m for m in st.session_state.motors_list if m.get("id") == m_id), None)
    if not motor:
        st.error("Motor no encontrado.")
        if st.button("Cerrar", key="close_missing"):
            close_detail()
        return

    hl, hr = st.columns([5, 1])
    with hl:
        st.markdown("## Ficha Tecnica")
        st.caption(f"ID: {m_id}")
    with hr:
        if st.button("✕ Cerrar", use_container_width=True, key=f"close_{m_id}"):
            close_detail()
    st.divider()

    tab_v, tab_e = st.tabs(["Vista", "Editar"])

    with tab_v:
        render_vista(motor)

    with tab_e:
        preload_edit(motor)
        render_motor_form("e_")
        st.button(
            "Guardar Cambios",
            type="primary",
            use_container_width=True,
            on_click=on_save_edit,
            args=(m_id,),
            key=f"save_edit_{m_id}",
        )

# ==============================================================================
# SECCION: NUEVO MOTOR
# ==============================================================================
def render_nuevo_motor():
    render_motor_form("f_")
    st.button("Guardar Motor", type="primary", use_container_width=True, on_click=on_create)

# ==============================================================================
# SECCION: HISTORIAL
# ==============================================================================
def render_historial():
    st.session_state.setdefault("current_page", 1)
    st.session_state.setdefault("_last_search", "")

    # ── Barra superior: busqueda + acciones ──────────────────────────────────
    col_s, col_r, col_e = st.columns([6, 0.9, 0.9], vertical_alignment="bottom")
    search = col_s.text_input(
        "Buscar", placeholder="🔍  Marca, cliente, potencia...", label_visibility="collapsed"
    )
    if search != st.session_state.history_search:
        st.session_state.history_search = search
        st.session_state["current_page"] = 1
        close_detail(rerun=False)

    if col_r.button("↺  Actualizar", use_container_width=True):
        invalidate_cache()
        st.session_state.motors_list = fetch_motors(st.session_state.api_key)
        close_detail(rerun=False)
        st.toast("Datos actualizados.", icon="🔄")
        st.rerun()

    motors = st.session_state.motors_list
    if not motors:
        st.info("No hay datos. Carga un motor nuevo.")
        return

    # ── Armar dataframe ──────────────────────────────────────────────────────
    df = pd.json_normalize(motors)
    col_map = {
        "id": "ID", "general.owner": "Cliente", "general.brand": "Marca",
        "power": "Potencia", "rpm": "RPM", "general.serial_number": "Serie",
    }
    for c in col_map:
        if c not in df.columns:
            df[c] = None
    df = df.rename(columns=col_map)

    if search:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        df = df[mask]

    # CSV export (sobre el df ya filtrado)
    buf = io.StringIO()
    df[["ID", "Cliente", "Marca", "Potencia", "RPM", "Serie"]].to_csv(buf, index=False)
    col_e.download_button("⬇  CSV", data=buf.getvalue(), file_name="motores.csv",
                          mime="text/csv", use_container_width=True)

    if df.empty:
        st.warning("Sin resultados para esa busqueda.")
        close_detail(rerun=False)
        return

    # ── Paginacion ───────────────────────────────────────────────────────────
    total       = len(df)
    total_pages = max(1, -(-total // HISTORY_LIMIT))

    if search != st.session_state.get("_last_search"):
        st.session_state["_last_search"] = search
        st.session_state["current_page"] = 1
        close_detail(rerun=False)

    page = max(1, min(st.session_state["current_page"], total_pages))
    st.session_state["current_page"] = page

    # Caption con cantidad de resultados, alineado a la derecha de la barra
    label = f"{total} resultado{'s' if total != 1 else ''}"
    if search:
        label += f' para "{search}"'
    st.caption(label)

    start   = (page - 1) * HISTORY_LIMIT
    df_page = df.iloc[start : start + HISTORY_LIMIT]

    # ── Dataframe ────────────────────────────────────────────────────────────
    event = st.dataframe(
        df_page[["ID", "Cliente", "Marca", "Potencia", "RPM", "Serie"]],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={"ID": st.column_config.NumberColumn(format="%d", width="small")},
        key=f"hist_df_{search}_{page}",
    )

    # ── Paginacion centrada debajo del dataframe ──────────────────────────────
    if total_pages > 1:
        _, c_prev, c_info, c_next, _ = st.columns([2.5, 0.5, 1.5, 0.5, 2.5])
        if c_prev.button("←", use_container_width=True, disabled=(page <= 1), key="pg_prev"):
            st.session_state["current_page"] -= 1
            close_detail(rerun=False)
            st.rerun()
        c_info.markdown(
            f"<p style='text-align:center;margin:0;padding-top:7px;"
            f"font-size:0.85rem;color:gray'>{page} / {total_pages}</p>",
            unsafe_allow_html=True,
        )
        if c_next.button("→", use_container_width=True, disabled=(page >= total_pages), key="pg_next"):
            st.session_state["current_page"] += 1
            close_detail(rerun=False)
            st.rerun()

    # ── Seleccion y apertura de ficha ─────────────────────────────────────────
    selected_id = (
        int(df_page.iloc[event.selection.rows[0]]["ID"])
        if event.selection.rows else None
    )
    st.session_state.selected_row_id = selected_id

    with st.form("open_form"):
        open_clicked = st.form_submit_button(
            "Abrir Ficha", type="primary", use_container_width=True,
            disabled=(selected_id is None),
        )

    if open_clicked and selected_id is not None:
        if selected_id != st.session_state.get("_edit_loaded_id"):
            st.session_state.pop("_edit_loaded_id", None)
        st.session_state.active_motor_id = selected_id
        st.session_state.detail_open     = True
        # Sin st.rerun(): el form_submit_button ya hace rerun y mantiene la tab activa

    st.divider()

    if st.session_state.detail_open and st.session_state.active_motor_id:
        render_motor_detail(st.session_state.active_motor_id)
    else:
        st.markdown("## Ficha Tecnica")
        st.caption("Selecciona un motor y presiona Abrir Ficha.")

# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================
init_state()

if not check_password():
    st.stop()

# Carga de datos (cacheada por api_key, TTL 60s)
try:
    st.session_state.motors_list = fetch_motors(st.session_state.api_key)
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# Header con tabs de navegacion
h_col, logout_col = st.columns([8, 1], vertical_alignment="bottom")
with h_col:
    st.markdown("## ⚡ Gestion de Bobinados")
with logout_col:
    if st.button("Salir", use_container_width=True):
        invalidate_cache()
        st.session_state.clear()
        st.rerun()

tab_nuevo, tab_hist = st.tabs(["✏️  Nuevo Motor", "🔍  Historial"])

with tab_nuevo:
    if st.session_state.detail_open:
        close_detail(rerun=False)
    render_nuevo_motor()

with tab_hist:
    render_historial()