import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from database import (
    init_db,
    insertar_gasto, eliminar_gasto,
    obtener_gastos_mes, gasto_total_mes,
    gasto_por_categoria_mes, gasto_por_metodo_mes,
    insertar_movimiento_ahorro, obtener_saldo_ahorro,
    obtener_movimientos_ahorro, proyeccion_fondo,
    insertar_ingreso, obtener_ingresos_mes,
    total_ingresos_mes, eliminar_ingreso,
    CATEGORIAS, METODOS_PAGO, TIPOS_INGRESO,
    INGRESO_NETO, LIMITE_GASTOS, META_AHORRO,
    META_DESARROLLO, META_FONDO_EMERGENCIA,
)

st.set_page_config(
    page_title="Jean Finance OS",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

# ─── CSS EXTERNO ──────────────────────────────────────────────────────────────
_css_path = Path(__file__).parent / "assets" / "style.css"
with open(_css_path, encoding="utf-8") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
hoy = date.today()
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

def _selector_mes(key_prefix: str) -> tuple[int, int]:
    """Devuelve (anio, mes) seleccionados. Por defecto el mes actual."""
    anos_disp = list(range(2024, hoy.year + 3))
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        anio_s = st.selectbox(
            "Año", options=anos_disp,
            index=anos_disp.index(hoy.year),
            key=f"{key_prefix}_anio",
        )
    with c2:
        mes_s = st.selectbox(
            "Mes", options=list(range(1, 13)),
            format_func=lambda m: MESES_ES[m],
            index=hoy.month - 1,
            key=f"{key_prefix}_mes",
        )
    return anio_s, mes_s

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="jf-header">
  <div class="jf-logo">💰</div>
  <div>
    <div class="jf-title">Jean Finance OS</div>
    <div class="jf-subtitle">Ingreso base: ${INGRESO_NETO:,.0f} COP &nbsp;·&nbsp; Regla 80 / 10 / 20</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab_home, tab_ingresos, tab_registro, tab_ahorro, tab_analisis = st.tabs([
    "📊  Dashboard",
    "💵  Ingresos",
    "➕  Registro",
    "🐷  Ahorro",
    "📈  Análisis",
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — DASHBOARD  (siempre muestra el mes en curso)
# ══════════════════════════════════════════════════════════════════════════════
with tab_home:
    anio, mes = hoy.year, hoy.month
    gasto_mes    = gasto_total_mes(anio, mes)
    ingreso_mes  = total_ingresos_mes(anio, mes)
    saldo_ahorro = obtener_saldo_ahorro()
    df_gastos    = obtener_gastos_mes(anio, mes)

    # Separar débito vs crédito — las TC no salen de caja hasta que se paguen con TD
    gasto_td    = df_gastos[df_gastos["metodo_pago"] == "TD Bancolombia"]["monto"].sum()
    gasto_tc_nu = df_gastos[df_gastos["metodo_pago"] == "TC Nubank"]["monto"].sum()
    gasto_tc_bc = df_gastos[df_gastos["metodo_pago"] == "TC Bancolombia"]["monto"].sum()
    gasto_tc    = gasto_tc_nu + gasto_tc_bc

    pct_gasto = gasto_mes / LIMITE_GASTOS if LIMITE_GASTOS > 0 else 0
    pct_fondo = saldo_ahorro / META_FONDO_EMERGENCIA if META_FONDO_EMERGENCIA > 0 else 0

    # Balance de caja real: solo descuenta lo pagado con débito
    if ingreso_mes > 0:
        balance_neto = ingreso_mes - gasto_td
        neg          = balance_neto < 0
        pct_disp     = balance_neto / ingreso_mes * 100
        st.markdown(f"""
<div class="jf-balance-card {'negative' if neg else ''}">
  <div class="jf-balance-left">
    <div class="jf-balance-label">{'Déficit' if neg else 'Saldo de caja'} — {MESES_ES[mes]} {anio}</div>
    <div class="jf-balance-value">{'−' if neg else '+'}${abs(balance_neto):,.0f} COP</div>
    <div class="jf-balance-sub">Ingresos ${ingreso_mes:,.0f} · Débito ${gasto_td:,.0f} · TC pendiente ${gasto_tc:,.0f}</div>
  </div>
  <div class="jf-balance-badge">{'déficit' if neg else f'{pct_disp:.0f}% disponible'}</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("")
    else:
        st.caption(f"Sin ingresos registrados · Ingreso base de referencia: ${INGRESO_NETO:,.0f} COP")

    # Métricas principales
    st.markdown('<div class="jf-section">Resumen del mes</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        df_ing_home = obtener_ingresos_mes(anio, mes)
        st.metric("Ingresos registrados", f"${ingreso_mes:,.0f}",
                  delta="Sin registros aún" if ingreso_mes == 0 else f"{len(df_ing_home)} movimiento(s)",
                  delta_color="off")
    with c2:
        delta_g = gasto_mes - LIMITE_GASTOS
        st.metric("Gastos totales", f"${gasto_mes:,.0f}",
                  delta=f"${abs(delta_g):,.0f} {'sobre' if delta_g > 0 else 'bajo'} límite",
                  delta_color="inverse")
    with c3:
        st.metric("TD Bancolombia", f"${gasto_td:,.0f}",
                  delta="Salida real de caja", delta_color="off")
    with c4:
        st.metric("Fondo emergencia", f"${saldo_ahorro:,.0f}",
                  delta=f"{pct_fondo:.0%} completado", delta_color="off")

    # Métricas tarjetas de crédito
    st.markdown('<div class="jf-section">Tarjetas de crédito — por pagar</div>', unsafe_allow_html=True)
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.metric("TC Nubank", f"${gasto_tc_nu:,.0f}",
                  delta="Pendiente de pago" if gasto_tc_nu > 0 else "Sin movimientos",
                  delta_color="off")
    with tc2:
        st.metric("TC Bancolombia", f"${gasto_tc_bc:,.0f}",
                  delta="Pendiente de pago" if gasto_tc_bc > 0 else "Sin movimientos",
                  delta_color="off")
    with tc3:
        st.metric("Total TC pendiente", f"${gasto_tc:,.0f}",
                  delta=f"Pagá con TD para descontar de caja",
                  delta_color="off")

    # 80/10/20
    st.markdown('<div class="jf-section">Regla 80 / 10 / 20</div>', unsafe_allow_html=True)
    col_bars, col_ref = st.columns([3, 1])

    with col_bars:
        st.markdown(f"**Gastos** — {MESES_ES[mes]} {anio}")
        st.progress(min(pct_gasto, 1.0))
        st.caption(f"${gasto_mes:,.0f} de ${LIMITE_GASTOS:,.0f} · {pct_gasto:.0%}")

        st.markdown("**Fondo de emergencia**")
        st.progress(min(pct_fondo, 1.0))
        st.caption(f"${saldo_ahorro:,.0f} de ${META_FONDO_EMERGENCIA:,.0f} · {pct_fondo:.0%}")

        st.markdown("**Desarrollo / inversión** (20%)")
        st.progress(0.0)
        st.caption(f"Presupuesto: ${META_DESARROLLO:,.0f}/mes")

    with col_ref:
        st.markdown(f"""
<div class="jf-ref-table">
  <div class="jf-ref-header">Distribución</div>
  <div class="jf-ref-row">
    <span class="jf-ref-label">80% gastos</span>
    <span class="jf-ref-value">${LIMITE_GASTOS:,.0f}</span>
  </div>
  <div class="jf-ref-row">
    <span class="jf-ref-label">10% ahorro</span>
    <span class="jf-ref-value">${META_AHORRO:,.0f}</span>
  </div>
  <div class="jf-ref-row">
    <span class="jf-ref-label">20% desarrollo</span>
    <span class="jf-ref-value">${META_DESARROLLO:,.0f}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    if pct_gasto >= 0.85:
        st.error(f"Llevas el {pct_gasto:.0%} del límite. Quedan **${max(LIMITE_GASTOS - gasto_mes,0):,.0f} COP**.")
    elif pct_gasto >= 0.70:
        st.warning(f"Llevas el {pct_gasto:.0%} del límite mensual. Revisa los gastos.")

    # Últimos gastos
    st.markdown('<div class="jf-section">Últimos gastos</div>', unsafe_allow_html=True)
    if df_gastos.empty:
        st.info("Sin gastos este mes. Usa la pestaña **Registro** para agregar uno.")
    else:
        df_disp = df_gastos.head(8).copy()
        df_disp["monto"] = df_disp["monto"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(
            df_disp.rename(columns={
                "fecha": "Fecha", "descripcion": "Descripción",
                "categoria": "Categoría", "monto": "Monto",
                "metodo_pago": "Método de pago",
            })[["Fecha", "Descripción", "Categoría", "Monto", "Método de pago"]],
            use_container_width=True, hide_index=True,
        )

    # Proyección fondo
    st.markdown('<div class="jf-section">Proyección fondo de emergencia</div>', unsafe_allow_html=True)
    faltante = META_FONDO_EMERGENCIA - saldo_ahorro
    if faltante <= 0:
        st.success("Fondo de emergencia completado.")
    else:
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            st.metric("Saldo actual", f"${saldo_ahorro:,.0f}")
        with cp2:
            st.metric("Falta", f"${faltante:,.0f}")
        with cp3:
            meses_est = int(faltante // META_AHORRO) + 1 if META_AHORRO > 0 else 0
            try:
                from dateutil.relativedelta import relativedelta
                fecha_est = date.today() + relativedelta(months=meses_est)
                st.metric("Estimado", fecha_est.strftime("%b %Y"),
                          delta=f"~{meses_est} meses", delta_color="off")
            except Exception:
                st.metric("Estimado", f"~{meses_est} meses")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — INGRESOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ingresos:
    # Selector de mes
    st.markdown('<div class="jf-section">Período</div>', unsafe_allow_html=True)
    anio_i, mes_i = _selector_mes("ing")

    df_ing    = obtener_ingresos_mes(anio_i, mes_i)
    total_ing = df_ing["monto"].sum() if not df_ing.empty else 0.0

    # Métricas
    st.markdown('<div class="jf-section">Ingresos</div>', unsafe_allow_html=True)
    mi1, mi2, mi3 = st.columns(3)
    with mi1:
        st.metric("Total registrado", f"${total_ing:,.0f}",
                  delta=f"{len(df_ing)} movimiento(s)", delta_color="off")
    with mi2:
        diff_base = total_ing - INGRESO_NETO
        st.metric("vs Ingreso base", f"${INGRESO_NETO:,.0f}",
                  delta=f"${abs(diff_base):,.0f} {'extra' if diff_base >= 0 else 'menos'}",
                  delta_color="normal" if diff_base >= 0 else "inverse")
    with mi3:
        quincenas = df_ing[df_ing["tipo"].isin(["Quincenal 1", "Quincenal 2"])] if not df_ing.empty else pd.DataFrame()
        total_q   = quincenas["monto"].sum() if not quincenas.empty else 0.0
        st.metric("Solo quincenas", f"${total_q:,.0f}", delta_color="off")

    # Formulario
    st.markdown('<div class="jf-section">Registrar ingreso</div>', unsafe_allow_html=True)
    with st.form("form_ingreso", clear_on_submit=True):
        fi1, fi2 = st.columns(2)
        with fi1:
            concepto_i = st.text_input("Concepto *",
                placeholder="Ej: Quincena 1, Prima de servicios...")
            monto_i = st.number_input("Monto (COP) *",
                min_value=0, max_value=50_000_000, value=0, step=50_000, format="%d")
        with fi2:
            tipo_i  = st.radio("Tipo *", options=TIPOS_INGRESO, index=0)
            fecha_i = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")

        sub_i = st.form_submit_button("Registrar ingreso", use_container_width=True, type="primary")
        if sub_i:
            if monto_i <= 0:
                st.error("El monto debe ser mayor a $0.")
            elif not concepto_i.strip():
                st.error("Escribe un concepto.")
            else:
                insertar_ingreso(fecha_i, concepto_i, monto_i, tipo_i)
                st.success(f"Ingreso de **${monto_i:,.0f}** ({tipo_i}) registrado.")
                st.rerun()

    # Historial
    st.markdown(f'<div class="jf-section">Historial — {MESES_ES[mes_i]} {anio_i}</div>', unsafe_allow_html=True)
    if df_ing.empty:
        st.info("Sin ingresos en este período.")
    else:
        df_ing_disp = df_ing.copy()
        df_ing_disp["Monto"] = df_ing_disp["monto"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(
            df_ing_disp.rename(columns={
                "id": "ID", "fecha": "Fecha", "concepto": "Concepto", "tipo": "Tipo",
            })[["ID", "Fecha", "Concepto", "Tipo", "Monto"]],
            use_container_width=True, hide_index=True,
        )
        st.caption(f"Total: **${total_ing:,.0f} COP**")

        with st.expander("Eliminar un ingreso"):
            id_del_i = st.number_input("ID a eliminar", min_value=1, step=1,
                                       format="%d", key="del_ingreso")
            if st.button("Eliminar", type="secondary", key="btn_del_ingreso"):
                if id_del_i in df_ing["id"].tolist():
                    eliminar_ingreso(id_del_i)
                    st.success(f"Ingreso #{id_del_i} eliminado.")
                    st.rerun()
                else:
                    st.error(f"ID {id_del_i} no existe.")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — REGISTRO DE GASTOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_registro:
    st.markdown('<div class="jf-section">Nuevo gasto</div>', unsafe_allow_html=True)

    with st.form("form_gasto", clear_on_submit=True):
        f1, f2 = st.columns([1, 1])
        with f1:
            monto_g = st.number_input("Monto (COP) *",
                min_value=0, max_value=10_000_000, value=0, step=1000, format="%d",
                help="Sin puntos ni comas")
            descripcion = st.text_input("Descripción (opcional)",
                placeholder="Ej: Éxito Laureles, gasolina, Netflix...")
            fecha_g = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
        with f2:
            categoria = st.radio("Categoría *", options=CATEGORIAS, index=0)

        metodo_pago = st.radio("Método de pago *", options=METODOS_PAGO, index=0, horizontal=True)

        submitted = st.form_submit_button("Registrar gasto", use_container_width=True, type="primary")
        if submitted:
            if monto_g <= 0:
                st.error("El monto debe ser mayor a $0.")
            else:
                insertar_gasto(fecha_g, descripcion, categoria, monto_g, metodo_pago)
                st.success(f"Gasto de **${monto_g:,.0f}** en **{categoria}** registrado.")

    # Selector de mes para consultar historial
    st.markdown('<div class="jf-section">Historial de gastos</div>', unsafe_allow_html=True)
    anio_r, mes_r = _selector_mes("reg")
    df_r = obtener_gastos_mes(anio_r, mes_r)

    if df_r.empty:
        st.info(f"Sin gastos en {MESES_ES[mes_r]} {anio_r}.")
    else:
        total_r = df_r["monto"].sum()
        st.caption(f"Total: **${total_r:,.0f} COP** · {len(df_r)} transacciones")

        rf1, rf2 = st.columns(2)
        with rf1:
            filtro_cat = st.multiselect("Filtrar por categoría",
                options=sorted(df_r["categoria"].unique()), key="filt_cat_reg")
        with rf2:
            filtro_met = st.multiselect("Filtrar por método",
                options=sorted(df_r["metodo_pago"].unique()), key="filt_met_reg")

        df_fil = df_r.copy()
        if filtro_cat:
            df_fil = df_fil[df_fil["categoria"].isin(filtro_cat)]
        if filtro_met:
            df_fil = df_fil[df_fil["metodo_pago"].isin(filtro_met)]

        df_fil["monto_fmt"] = df_fil["monto"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(
            df_fil.rename(columns={
                "id": "ID", "fecha": "Fecha", "descripcion": "Descripción",
                "categoria": "Categoría", "monto_fmt": "Monto", "metodo_pago": "Método de pago",
            })[["ID", "Fecha", "Descripción", "Categoría", "Monto", "Método de pago"]],
            use_container_width=True, hide_index=True,
        )

        with st.expander("Eliminar un gasto"):
            id_del = st.number_input("ID a eliminar", min_value=1, step=1,
                                     format="%d", key="del_gasto")
            if st.button("Eliminar", type="secondary", key="btn_del_gasto"):
                if id_del in df_r["id"].tolist():
                    eliminar_gasto(id_del)
                    st.success(f"Gasto #{id_del} eliminado.")
                    st.rerun()
                else:
                    st.error(f"ID {id_del} no existe en este mes.")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — AHORRO
# ══════════════════════════════════════════════════════════════════════════════
with tab_ahorro:
    saldo_a    = obtener_saldo_ahorro()
    faltante_a = max(META_FONDO_EMERGENCIA - saldo_a, 0)
    pct_a      = min(saldo_a / META_FONDO_EMERGENCIA, 1.0) if META_FONDO_EMERGENCIA > 0 else 0
    meses_r    = proyeccion_fondo(saldo_a, META_AHORRO)

    st.markdown('<div class="jf-section">Fondo de emergencia · Cajitas Nubank</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Saldo actual", f"${saldo_a:,.0f}", delta=f"{pct_a:.0%} completado", delta_color="off")
    with m2:
        st.metric("Meta total", f"${META_FONDO_EMERGENCIA:,.0f}", delta=f"Faltan ${faltante_a:,.0f}", delta_color="off")
    with m3:
        if meses_r == 0:
            st.metric("Proyección", "Completado")
        elif meses_r == -1:
            st.metric("Proyección", "Sin datos")
        else:
            try:
                from dateutil.relativedelta import relativedelta
                fecha_proy = date.today() + relativedelta(months=meses_r)
                st.metric("Proyección", fecha_proy.strftime("%b %Y"),
                          delta=f"~{meses_r} meses", delta_color="off")
            except Exception:
                st.metric("Proyección", f"~{meses_r} meses")

    st.markdown(f"**Progreso: {pct_a:.0%}**")
    st.progress(pct_a)
    st.caption(f"${saldo_a:,.0f} / ${META_FONDO_EMERGENCIA:,.0f}")

    if pct_a >= 1.0:
        st.success("Fondo completado. Podés iniciar inversión en acciones.")
    elif pct_a >= 0.75:
        st.info(f"Vas muy bien. Faltan **${faltante_a:,.0f} COP**.")

    # Formulario
    st.markdown('<div class="jf-section">Registrar movimiento</div>', unsafe_allow_html=True)
    with st.form("form_ahorro", clear_on_submit=True):
        fa1, fa2 = st.columns(2)
        with fa1:
            concepto_a = st.text_input("Concepto *",
                placeholder="Ej: Ahorro mensual, prima junio, retiro...")
            monto_a = st.number_input("Monto (COP) *",
                min_value=0, max_value=50_000_000, value=0, step=10_000, format="%d")
        with fa2:
            tipo_a  = st.radio("Tipo *", options=["ingreso", "retiro"],
                format_func=lambda x: "Ingreso (ahorro)" if x == "ingreso" else "Retiro")
            fecha_a = st.date_input("Fecha", value=date.today(),
                format="DD/MM/YYYY", key="fecha_ahorro")

        if tipo_a == "retiro":
            st.warning("El fondo de emergencia es intocable salvo emergencia real.")

        sub_a = st.form_submit_button("Registrar", use_container_width=True, type="primary")
        if sub_a:
            if monto_a <= 0:
                st.error("El monto debe ser mayor a $0.")
            elif not concepto_a.strip():
                st.error("Escribe un concepto.")
            else:
                insertar_movimiento_ahorro(fecha_a, concepto_a, monto_a, tipo_a)
                st.success(f"{'Ingreso' if tipo_a == 'ingreso' else 'Retiro'} de **${monto_a:,.0f}** registrado.")
                st.rerun()

    # Historial
    st.markdown('<div class="jf-section">Historial completo</div>', unsafe_allow_html=True)
    df_mov = obtener_movimientos_ahorro()

    if df_mov.empty:
        st.info("Sin movimientos registrados.")
    else:
        df_mov["Monto"] = df_mov.apply(
            lambda r: f"+${r['monto']:,.0f}" if r["tipo"] == "ingreso" else f"-${r['monto']:,.0f}", axis=1
        )
        st.dataframe(
            df_mov.rename(columns={"fecha": "Fecha", "concepto": "Concepto", "tipo": "Tipo"})[
                ["Fecha", "Concepto", "Tipo", "Monto"]
            ],
            use_container_width=True, hide_index=True,
            column_config={
                "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                "Monto": st.column_config.TextColumn("Monto", width="medium"),
            },
        )
        ti = df_mov[df_mov["tipo"] == "ingreso"]["monto"].sum()
        tr = df_mov[df_mov["tipo"] == "retiro"]["monto"].sum()
        st.caption(f"Total ingresos: **${ti:,.0f}** · Total retiros: **${tr:,.0f}**")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analisis:
    st.markdown('<div class="jf-section">Período</div>', unsafe_allow_html=True)
    anio_sel, mes_sel = _selector_mes("anal")

    mes_ant  = mes_sel - 1 if mes_sel > 1 else 12
    anio_ant = anio_sel if mes_sel > 1 else anio_sel - 1

    df_cat_act = gasto_por_categoria_mes(anio_sel, mes_sel)
    df_cat_ant = gasto_por_categoria_mes(anio_ant, mes_ant)
    df_met_act = gasto_por_metodo_mes(anio_sel, mes_sel)
    total_act  = gasto_total_mes(anio_sel, mes_sel)
    total_ant  = gasto_total_mes(anio_ant, mes_ant)
    ing_sel    = total_ingresos_mes(anio_sel, mes_sel)

    # Alerta deseos
    if not df_cat_act.empty:
        row_d = df_cat_act[df_cat_act["categoria"] == "Deseos"]
        if not row_d.empty:
            gd    = row_d["monto"].values[0]
            pct_d = gd / META_DESARROLLO if META_DESARROLLO > 0 else 0
            if pct_d >= 0.70:
                st.warning(f"**Deseos** lleva ${gd:,.0f} — {pct_d:.0%} del límite sugerido (${META_DESARROLLO:,.0f}).")

    # Comparativo
    st.markdown('<div class="jf-section">Comparativo</div>', unsafe_allow_html=True)
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("Ingresos mes", f"${ing_sel:,.0f}", delta_color="off")
    with mc2:
        dg = total_act - total_ant
        st.metric("Gasto total", f"${total_act:,.0f}",
                  delta=f"${abs(dg):,.0f} {'más' if dg > 0 else 'menos'} que mes anterior",
                  delta_color="inverse")
    with mc3:
        st.metric("Mes anterior", f"${total_ant:,.0f}", delta_color="off")
    with mc4:
        pct_lim = total_act / LIMITE_GASTOS if LIMITE_GASTOS > 0 else 0
        st.metric("% del límite", f"{pct_lim:.0%}",
                  delta=f"Límite: ${LIMITE_GASTOS:,.0f}", delta_color="off")

    # Gráfica categorías
    st.markdown('<div class="jf-section">Gasto por categoría — mes actual vs anterior</div>', unsafe_allow_html=True)
    if df_cat_act.empty and df_cat_ant.empty:
        st.info("Sin datos para este período.")
    else:
        todas_cats = list(dict.fromkeys(
            list(df_cat_act["categoria"]) + list(df_cat_ant["categoria"]) + CATEGORIAS
        ))
        montos_act, montos_ant = [], []
        for cat in todas_cats:
            ra = df_cat_act[df_cat_act["categoria"] == cat]
            rp = df_cat_ant[df_cat_ant["categoria"] == cat]
            montos_act.append(ra["monto"].values[0] if not ra.empty else 0)
            montos_ant.append(rp["monto"].values[0] if not rp.empty else 0)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=f"{MESES_ES[mes_sel]}", x=todas_cats, y=montos_act,
            marker_color="#0F172A",
            marker_line_width=0,
            text=[f"${v:,.0f}" if v > 0 else "" for v in montos_act],
            textposition="outside", textfont=dict(size=9, color="#94A3B8"),
        ))
        fig.add_trace(go.Bar(
            name=f"{MESES_ES[mes_ant]}", x=todas_cats, y=montos_ant,
            marker_color="#E2E8F0",
            marker_line_width=0,
            text=[f"${v:,.0f}" if v > 0 else "" for v in montos_ant],
            textposition="outside", textfont=dict(size=9, color="#94A3B8"),
        ))
        fig.update_layout(
            barmode="group", height=340,
            margin=dict(t=30, b=10, l=0, r=0),
            yaxis=dict(tickprefix="$", tickformat=",.0f",
                       gridcolor="#F1F5F9", color="#CBD5E1",
                       showgrid=True, zeroline=False),
            xaxis=dict(tickangle=-30, color="#CBD5E1", gridcolor="rgba(0,0,0,0)",
                       showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="left", x=0, font=dict(color="#94A3B8", size=11)),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#94A3B8"),
            bargap=0.25,
            bargroupgap=0.08,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Métodos de pago
    st.markdown('<div class="jf-section">Métodos de pago</div>', unsafe_allow_html=True)
    if df_met_act.empty:
        st.info("Sin datos de métodos de pago.")
    else:
        cols_m = st.columns(len(df_met_act))
        for i, (_, row) in enumerate(df_met_act.iterrows()):
            pct_m = row["monto"] / total_act if total_act > 0 else 0
            with cols_m[i]:
                st.metric(row["metodo_pago"], f"${row['monto']:,.0f}",
                          delta=f"{pct_m:.0%}", delta_color="off")

        fig_pie = go.Figure(go.Pie(
            labels=df_met_act["metodo_pago"],
            values=df_met_act["monto"],
            hole=0.6,
            marker=dict(
                colors=["#0F172A", "#64748B", "#CBD5E1"],
                line=dict(color="#F7F8FA", width=3),
            ),
            textinfo="label+percent",
            textfont=dict(size=11, color="#374151"),
            insidetextorientation="radial",
        ))
        fig_pie.update_layout(
            height=260,
            margin=dict(t=10, b=10, l=0, r=0),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Detalle + export
    st.markdown('<div class="jf-section">Detalle de transacciones</div>', unsafe_allow_html=True)
    df_raw = obtener_gastos_mes(anio_sel, mes_sel)
    if df_raw.empty:
        st.info("Sin transacciones en este período.")
    else:
        df_raw["monto_fmt"] = df_raw["monto"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(
            df_raw.rename(columns={
                "fecha": "Fecha", "descripcion": "Descripción",
                "categoria": "Categoría", "monto_fmt": "Monto",
                "metodo_pago": "Método de pago",
            })[["Fecha", "Descripción", "Categoría", "Monto", "Método de pago"]],
            use_container_width=True, hide_index=True,
        )
        csv = df_raw.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Exportar CSV",
            data=csv,
            file_name=f"gastos_{anio_sel}_{mes_sel:02d}.csv",
            mime="text/csv",
        )
