import streamlit as st
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import (
    init_db, insertar_movimiento_ahorro,
    obtener_saldo_ahorro, obtener_movimientos_ahorro,
    META_FONDO_EMERGENCIA, META_AHORRO, proyeccion_fondo
)

st.set_page_config(page_title="Ahorro — Jean Finance OS", page_icon="🐷", layout="wide")
init_db()

st.markdown("## Fondo de emergencia")
st.caption("Cajitas Nubank · Meta: 3 meses de gastos fijos")
st.divider()

# ─── DATOS ────────────────────────────────────────────────────────────────────
saldo = obtener_saldo_ahorro()
faltante = max(META_FONDO_EMERGENCIA - saldo, 0)
pct = min(saldo / META_FONDO_EMERGENCIA, 1.0) if META_FONDO_EMERGENCIA > 0 else 0
meses_restantes = proyeccion_fondo(saldo, META_AHORRO)

# ─── MÉTRICAS ─────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Saldo actual", f"${saldo:,.0f}", delta=f"{pct:.0%} completado", delta_color="off")
with col2:
    st.metric("Meta", f"${META_FONDO_EMERGENCIA:,.0f}", delta=f"Faltan ${faltante:,.0f}", delta_color="off")
with col3:
    if meses_restantes == 0:
        st.metric("Proyección", "¡Completado!")
    elif meses_restantes == -1:
        st.metric("Proyección", "Sin datos")
    else:
        from datetime import date
        from dateutil.relativedelta import relativedelta
        try:
            fecha_est = date.today() + relativedelta(months=meses_restantes)
            st.metric("Proyección", fecha_est.strftime("%b %Y"), delta=f"~{meses_restantes} meses", delta_color="off")
        except Exception:
            st.metric("Proyección", f"~{meses_restantes} meses")

# ─── BARRA DE PROGRESO ────────────────────────────────────────────────────────
st.markdown(f"**Progreso: {pct:.0%}**")
st.progress(pct)
st.caption(f"${saldo:,.0f} / ${META_FONDO_EMERGENCIA:,.0f}")

if pct >= 1.0:
    st.success("✅ Fondo de emergencia completado. Podés iniciar inversión en acciones.")
elif pct >= 0.75:
    st.info(f"Vas muy bien. Faltan ${faltante:,.0f} COP para completar el fondo.")

st.divider()

# ─── REGISTRAR MOVIMIENTO ─────────────────────────────────────────────────────
st.markdown("#### Registrar movimiento")

with st.form("form_ahorro", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        concepto = st.text_input(
            "Concepto *",
            placeholder="Ej: Ahorro mensual, prima junio, retiro..."
        )
        monto_mov = st.number_input(
            "Monto (COP) *",
            min_value=0,
            max_value=50_000_000,
            value=0,
            step=10_000,
            format="%d"
        )
    with col_b:
        tipo = st.radio(
            "Tipo de movimiento *",
            options=["ingreso", "retiro"],
            format_func=lambda x: "➕ Ingreso (ahorro)" if x == "ingreso" else "➖ Retiro (excepción)"
        )
        fecha_mov = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")

    if tipo == "retiro":
        st.warning("Recuerda: el fondo de emergencia es intocable salvo emergencia real.")

    sub_ahorro = st.form_submit_button("Registrar", use_container_width=True, type="primary")

    if sub_ahorro:
        if monto_mov <= 0:
            st.error("El monto debe ser mayor a $0.")
        elif not concepto.strip():
            st.error("Escribe un concepto para el movimiento.")
        else:
            insertar_movimiento_ahorro(fecha_mov, concepto, monto_mov, tipo)
            accion = "Ingreso" if tipo == "ingreso" else "Retiro"
            st.success(f"{accion} de **${monto_mov:,.0f}** registrado.")
            st.rerun()

st.divider()

# ─── HISTORIAL ────────────────────────────────────────────────────────────────
st.markdown("#### Historial de movimientos")

df_mov = obtener_movimientos_ahorro()

if df_mov.empty:
    st.info("Sin movimientos registrados. Registra tu primer ingreso al fondo.")
else:
    def formato_monto(row):
        if row["tipo"] == "ingreso":
            return f"+${row['monto']:,.0f}"
        return f"-${row['monto']:,.0f}"

    df_mov["movimiento"] = df_mov.apply(formato_monto, axis=1)

    df_display = df_mov.rename(columns={
        "fecha": "Fecha",
        "concepto": "Concepto",
        "tipo": "Tipo",
        "movimiento": "Monto"
    })[["Fecha", "Concepto", "Tipo", "Monto"]]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Monto": st.column_config.TextColumn("Monto", width="medium"),
        }
    )
    total_ingresos = df_mov[df_mov["tipo"] == "ingreso"]["monto"].sum()
    total_retiros = df_mov[df_mov["tipo"] == "retiro"]["monto"].sum()
    st.caption(f"Total ingresos: ${total_ingresos:,.0f}  •  Total retiros: ${total_retiros:,.0f}")
