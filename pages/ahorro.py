import streamlit as st
from datetime import date
from utils import cfg_derived, q_saldo_ahorro, q_movs_ahorro, invalidar
from database import insertar_movimiento_ahorro, proyeccion_fondo

hoy = date.today()
CFG         = cfg_derived()
META_FONDO  = CFG["META_FONDO_EMERGENCIA"]
META_AHORRO = CFG["META_AHORRO"]

saldo_a  = q_saldo_ahorro()
faltante = max(META_FONDO - saldo_a, 0)
pct_a    = min(saldo_a / META_FONDO, 1.0) if META_FONDO > 0 else 0
meses_r  = proyeccion_fondo(saldo_a, META_AHORRO, META_FONDO)

try:
    from dateutil.relativedelta import relativedelta
    prox_fecha = (hoy + relativedelta(months=meses_r)).strftime("%b %Y") if meses_r > 0 else "—"
except Exception:
    prox_fecha = f"~{meses_r}m" if meses_r > 0 else "—"

color_fondo  = "#10B981" if pct_a >= 1.0 else ("#6366F1" if pct_a >= 0.5 else "#8B5CF6")
estado_fondo = "Completado ✓" if pct_a >= 1.0 else ("Muy cerca" if pct_a >= 0.75 else "En progreso")

st.markdown(f"""
<div class="jf-ahorro-hero">
  <div class="jf-ahorro-hero-left">
    <div class="jf-ahorro-hero-eyebrow">🏦 Cajitas Nubank · Fondo de emergencia</div>
    <div class="jf-ahorro-hero-val" style="color:{color_fondo};">${saldo_a:,.0f}</div>
    <div class="jf-ahorro-hero-sub">de ${META_FONDO:,.0f} COP</div>
    <div class="jf-ahorro-bar-bg">
      <div class="jf-ahorro-bar-fill" style="width:{pct_a*100:.1f}%;background:{color_fondo};"></div>
    </div>
    <div class="jf-ahorro-bar-caption">{pct_a*100:.1f}% completado · Faltan <strong>${faltante:,.0f}</strong></div>
  </div>
  <div class="jf-ahorro-hero-right">
    <div class="jf-ahorro-stat">
      <div class="jf-ahorro-stat-val">{estado_fondo}</div>
      <div class="jf-ahorro-stat-lbl">Estado</div>
    </div>
    <div class="jf-ahorro-stat">
      <div class="jf-ahorro-stat-val">{prox_fecha if meses_r > 0 else "Meta cumplida"}</div>
      <div class="jf-ahorro-stat-lbl">Proyección</div>
    </div>
    <div class="jf-ahorro-stat">
      <div class="jf-ahorro-stat-val">${META_AHORRO:,.0f}</div>
      <div class="jf-ahorro-stat-lbl">Ahorro mensual</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

if pct_a >= 1.0:
    st.success("Fondo completado. Considerá mover el excedente a inversión.")
elif pct_a >= 0.75:
    st.info(f"Vas muy bien. Con ${META_AHORRO:,.0f}/mes lo completás en ~{meses_r} mes(es).")

st.markdown('<div class="jf-section">Registrar movimiento</div>', unsafe_allow_html=True)
with st.form("form_ahorro", clear_on_submit=True):
    fa1, fa2 = st.columns(2)
    with fa1:
        concepto_a = st.text_input("Concepto *", placeholder="Ej: Ahorro mensual, prima...")
        monto_a    = st.number_input("Monto (COP) *", min_value=0, max_value=50_000_000, value=0, step=10_000, format="%d")
        fecha_a    = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY", key="fecha_ahorro")
    with fa2:
        tipo_a = st.radio("Tipo *", ["ingreso", "retiro"],
                          format_func=lambda x: "Ingreso (ahorro)" if x == "ingreso" else "Retiro")
        if tipo_a == "retiro":
            st.warning("Solo en emergencia real.")
    if st.form_submit_button("Registrar", width="stretch", type="primary"):
        if monto_a <= 0:
            st.error("El monto debe ser mayor a $0.")
        elif not concepto_a.strip():
            st.error("Escribe un concepto.")
        else:
            insertar_movimiento_ahorro(fecha_a, concepto_a, monto_a, tipo_a)
            invalidar(); st.success(f"{'Ahorro' if tipo_a=='ingreso' else 'Retiro'} de **${monto_a:,.0f}** registrado."); st.rerun()

st.markdown('<div class="jf-section">Historial de movimientos</div>', unsafe_allow_html=True)
df_mov = q_movs_ahorro()
if df_mov.empty:
    st.info("Sin movimientos registrados.")
else:
    ti = float(df_mov[df_mov["tipo"] == "ingreso"]["monto"].sum())
    tr = float(df_mov[df_mov["tipo"] == "retiro"]["monto"].sum())
    rows_a = ""
    for _, row in df_mov.iterrows():
        es_ing = row["tipo"] == "ingreso"
        rows_a += f"""
<div class="jf-gasto-row">
  <div class="jf-gasto-icon" style="background:{'#F0FDF4' if es_ing else '#FFF1F2'};">{'🏦' if es_ing else '💸'}</div>
  <div class="jf-gasto-info">
    <div class="jf-gasto-desc">{row['concepto']}</div>
    <div class="jf-gasto-cat">{'Ingreso al fondo' if es_ing else 'Retiro del fondo'} · {row['fecha']}</div>
  </div>
  <div class="jf-gasto-right">
    <div style="font-size:0.95rem;font-weight:800;color:{'#10B981' if es_ing else '#EF4444'};">
      {'+'if es_ing else '−'}${row['monto']:,.0f}
    </div>
  </div>
</div>"""
    st.markdown(f'<div class="jf-gasto-list">{rows_a}</div>', unsafe_allow_html=True)
    st.caption(f"Ahorrado: **${ti:,.0f}** · Retirado: **${tr:,.0f}** · Neto: **${ti-tr:,.0f}**")
