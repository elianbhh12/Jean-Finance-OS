import streamlit as st
from datetime import date
from utils import (
    cfg_derived, q_ingresos_mes, invalidar,
    selector_mes, confirmar_eliminar,
    MESES_ES, TIPO_ICON,
)
from database import insertar_ingreso, editar_ingreso, eliminar_ingreso, TIPOS_INGRESO

hoy = date.today()
CFG          = cfg_derived()
INGRESO_NETO = CFG["INGRESO_NETO"]

anio_i, mes_i = selector_mes("ing")
df_ing    = q_ingresos_mes(anio_i, mes_i)
total_ing = float(df_ing["monto"].sum()) if not df_ing.empty else 0.0
diff_i    = total_ing - INGRESO_NETO
pct_ing   = (total_ing / INGRESO_NETO * 100) if INGRESO_NETO > 0 else 0
q_sum     = float(df_ing[df_ing["tipo"].isin(["Quincenal 1", "Quincenal 2"])]["monto"].sum()) if not df_ing.empty else 0.0

d_color = "#10B981" if diff_i >= 0 else "#F59E0B"
d_bg    = "#F0FDF4" if diff_i >= 0 else "#FFFBEB"
d_text  = f"+${abs(diff_i):,.0f} sobre la base" if diff_i >= 0 else f"−${abs(diff_i):,.0f} bajo la base"

st.markdown(f"""
<div class="jf-ing-hero">
  <div class="jf-ing-hero-left">
    <div class="jf-ing-hero-eyebrow">{MESES_ES[mes_i]} {anio_i}</div>
    <div class="jf-ing-hero-val">${total_ing:,.0f} <span class="jf-ing-hero-cop">COP</span></div>
    <div class="jf-ing-hero-diff" style="color:{d_color};background:{d_bg};">{d_text}</div>
  </div>
  <div class="jf-ing-hero-stats">
    <div class="jf-ing-stat"><div class="jf-ing-stat-n">{len(df_ing)}</div><div class="jf-ing-stat-l">Movimientos</div></div>
    <div class="jf-ing-stat-divider"></div>
    <div class="jf-ing-stat"><div class="jf-ing-stat-n">${q_sum:,.0f}</div><div class="jf-ing-stat-l">Quincenas</div></div>
    <div class="jf-ing-stat-divider"></div>
    <div class="jf-ing-stat"><div class="jf-ing-stat-n">{pct_ing:.0f}%</div><div class="jf-ing-stat-l">vs base</div></div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Formulario ────────────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Registrar ingreso</div>', unsafe_allow_html=True)
with st.form("form_ingreso", clear_on_submit=True):
    fi1, fi2 = st.columns(2)
    with fi1:
        concepto_i = st.text_input("Concepto *", placeholder="Ej: Quincena 1, Prima...")
        monto_i    = st.number_input("Monto (COP) *", min_value=0, max_value=50_000_000, value=0, step=50_000, format="%d")
        fecha_i    = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
        nota_i     = st.text_input("Nota (opcional)", placeholder="Ej: con comisión incluida")
    with fi2:
        tipo_i = st.radio("Tipo *", TIPOS_INGRESO)
    if st.form_submit_button("Registrar ingreso", width="stretch", type="primary"):
        if monto_i <= 0:
            st.error("El monto debe ser mayor a $0.")
        elif not concepto_i.strip():
            st.error("Escribe un concepto.")
        else:
            insertar_ingreso(fecha_i, concepto_i, monto_i, tipo_i, nota_i)
            invalidar(); st.success(f"Ingreso de **${monto_i:,.0f}** registrado."); st.rerun()

# ── Historial ─────────────────────────────────────────────────────────────────
st.markdown(f'<div class="jf-section">Historial — {MESES_ES[mes_i]} {anio_i}</div>', unsafe_allow_html=True)
if df_ing.empty:
    st.info("Sin ingresos en este período.")
else:
    rows_i = ""
    for _, row in df_ing.iterrows():
        icon_i = TIPO_ICON.get(row["tipo"], "💰")
        nota_h = f'<div class="jf-gasto-nota">📝 {row["nota"]}</div>' if row.get("nota") else ""
        rows_i += f"""
<div class="jf-gasto-row">
  <div class="jf-gasto-icon" style="background:#F0FDF4;">{icon_i}</div>
  <div class="jf-gasto-info">
    <div class="jf-gasto-desc">{row['concepto']}</div>
    <div class="jf-gasto-cat">{row['tipo']} · {row['fecha']} · ID #{int(row['id'])}</div>
    {nota_h}
  </div>
  <div class="jf-gasto-right"><div class="jf-ing-monto">+${row['monto']:,.0f}</div></div>
</div>"""
    st.markdown(f'<div class="jf-gasto-list">{rows_i}</div>', unsafe_allow_html=True)
    st.caption(f"Total: **${total_ing:,.0f} COP** · {len(df_ing)} movimiento(s)")

    with st.expander("✏️ Editar un ingreso"):
        opts_i = {f"#{int(r['id'])} — {r['concepto']} · ${r['monto']:,.0f}": int(r['id']) for _, r in df_ing.iterrows()}
        sel_i  = st.selectbox("Selecciona el ingreso", list(opts_i.keys()), key="sel_ei")
        fe     = df_ing[df_ing["id"] == opts_i[sel_i]].iloc[0]
        ec1, ec2 = st.columns(2)
        with ec1:
            new_conc  = st.text_input("Concepto", value=fe["concepto"], key="ei_conc")
            new_monto = st.number_input("Monto", value=float(fe["monto"]), step=1000.0, format="%.0f", key="ei_monto")
            new_fecha = st.date_input("Fecha", value=date.fromisoformat(fe["fecha"]), key="ei_fecha")
            new_nota  = st.text_input("Nota", value=fe.get("nota", ""), key="ei_nota")
        with ec2:
            new_tipo = st.radio("Tipo", TIPOS_INGRESO,
                                index=TIPOS_INGRESO.index(fe["tipo"]) if fe["tipo"] in TIPOS_INGRESO else 0,
                                key="ei_tipo")
        if st.button("Guardar cambios", key="btn_ei", type="primary"):
            editar_ingreso(int(opts_i[sel_i]), new_fecha, new_conc or "", new_monto, new_tipo, new_nota or "")
            invalidar(); st.success("Ingreso actualizado."); st.rerun()

    with st.expander("🗑️ Eliminar un ingreso"):
        opts_di = {f"#{int(r['id'])} — {r['concepto']} · ${r['monto']:,.0f}": int(r['id']) for _, r in df_ing.iterrows()}
        sel_di  = st.selectbox("Selecciona el ingreso a eliminar", list(opts_di.keys()), key="sel_del_i")
        if confirmar_eliminar("ing") and st.button("Eliminar", type="secondary", key="btn_del_i"):
            eliminar_ingreso(opts_di[sel_di]); invalidar()
            st.success("Ingreso eliminado."); st.rerun()
