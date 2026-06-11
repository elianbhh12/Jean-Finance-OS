import streamlit as st
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import (
    init_db, insertar_gasto, eliminar_gasto,
    obtener_gastos_mes, CATEGORIAS, METODOS_PAGO
)

st.set_page_config(page_title="Registro — Jean Finance OS", page_icon="➕", layout="wide")
init_db()

st.markdown("## Registro de gastos")
st.divider()

# ─── FORMULARIO ───────────────────────────────────────────────────────────────
with st.form("form_gasto", clear_on_submit=True):
    col1, col2 = st.columns([1, 1])

    with col1:
        monto = st.number_input(
            "Monto (COP) *",
            min_value=0,
            max_value=10_000_000,
            value=0,
            step=1000,
            format="%d",
            help="Ingresa el monto sin puntos ni comas"
        )
        descripcion = st.text_input(
            "Descripción (opcional)",
            placeholder="Ej: Éxito Laureles, gasolina, Netflix..."
        )
        fecha = st.date_input(
            "Fecha",
            value=date.today(),
            format="DD/MM/YYYY"
        )

    with col2:
        categoria = st.radio(
            "Categoría *",
            options=CATEGORIAS,
            index=0,
            horizontal=False
        )

    metodo_pago = st.radio(
        "Método de pago *",
        options=METODOS_PAGO,
        index=0,
        horizontal=True
    )

    submitted = st.form_submit_button(
        "✅ Registrar gasto",
        use_container_width=True,
        type="primary"
    )

    if submitted:
        if monto <= 0:
            st.error("El monto debe ser mayor a $0.")
        else:
            insertar_gasto(fecha, descripcion, categoria, monto, metodo_pago)
            st.success(f"Gasto de **${monto:,.0f}** en **{categoria}** registrado.")

st.divider()

# ─── TABLA DEL MES ────────────────────────────────────────────────────────────
hoy = date.today()
st.markdown(f"#### Gastos registrados — {hoy.strftime('%B %Y')}")

df = obtener_gastos_mes(hoy.year, hoy.month)

if df.empty:
    st.info("Sin gastos este mes todavía.")
else:
    total_mes = df["monto"].sum()
    st.caption(f"Total: **${total_mes:,.0f} COP**  •  {len(df)} transacciones")

    col_fil1, col_fil2 = st.columns(2)
    with col_fil1:
        filtro_cat = st.multiselect(
            "Filtrar por categoría",
            options=sorted(df["categoria"].unique()),
            default=[]
        )
    with col_fil2:
        filtro_metodo = st.multiselect(
            "Filtrar por método de pago",
            options=sorted(df["metodo_pago"].unique()),
            default=[]
        )

    df_filtrado = df.copy()
    if filtro_cat:
        df_filtrado = df_filtrado[df_filtrado["categoria"].isin(filtro_cat)]
    if filtro_metodo:
        df_filtrado = df_filtrado[df_filtrado["metodo_pago"].isin(filtro_metodo)]

    df_display = df_filtrado.copy()
    df_display["monto_fmt"] = df_display["monto"].apply(lambda x: f"${x:,.0f}")
    df_display = df_display.rename(columns={
        "id": "ID",
        "fecha": "Fecha",
        "descripcion": "Descripción",
        "categoria": "Categoría",
        "monto_fmt": "Monto",
        "metodo_pago": "Método de pago"
    })[["ID", "Fecha", "Descripción", "Categoría", "Monto", "Método de pago"]]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ─── ELIMINAR GASTO ───────────────────────────────────────────────────────
    with st.expander("Eliminar un gasto"):
        id_eliminar = st.number_input(
            "ID del gasto a eliminar",
            min_value=1,
            step=1,
            format="%d"
        )
        if st.button("Eliminar", type="secondary"):
            ids_validos = df["id"].tolist()
            if id_eliminar in ids_validos:
                eliminar_gasto(id_eliminar)
                st.success(f"Gasto #{id_eliminar} eliminado.")
                st.rerun()
            else:
                st.error(f"El ID {id_eliminar} no existe en este mes.")
