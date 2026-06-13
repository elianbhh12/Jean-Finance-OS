import streamlit as st
from utils import cfg_derived, invalidar
from database import get_config, set_config, get_derived, DB_PATH

cfg_actual = get_config()

st.markdown("""
<div class="jf-balance-card">
  <div class="jf-balance-left">
    <div class="jf-balance-label">⚙️ Configuración personal</div>
    <div class="jf-balance-value" style="font-size:1.4rem;">Ajusta tu base mensual</div>
    <div class="jf-balance-sub">Los cambios se aplican a todos los cálculos al instante.</div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="jf-section">Ingreso y metas</div>', unsafe_allow_html=True)
with st.form("form_config"):
    cc1, cc2 = st.columns(2)
    with cc1:
        new_ingreso = st.number_input(
            "Ingreso neto mensual (COP)",
            min_value=100_000, max_value=100_000_000,
            value=int(cfg_actual["ingreso_neto"]), step=50_000, format="%d",
            help="Tu salario neto o ingreso promedio mensual")
        new_fondo = st.number_input(
            "Meta fondo de emergencia (COP)",
            min_value=100_000, max_value=500_000_000,
            value=int(cfg_actual["meta_fondo"]), step=100_000, format="%d",
            help="Recomendado: 3-6 meses de gastos fijos")
    with cc2:
        st.markdown("**Regla 80 / 10 / 10**")
        new_gastos_pct = st.slider("% máximo en gastos", 50, 95,
                                   int(cfg_actual["limite_gastos_pct"] * 100), 5)
        new_ahorro_pct = st.slider("% destinado a ahorro", 5, 40,
                                   int(cfg_actual["meta_ahorro_pct"] * 100), 5)
        new_dev_pct    = st.slider("% para desarrollo/inversión", 5, 40,
                                   int(cfg_actual["meta_desarrollo_pct"] * 100), 5)
        total_pct = new_gastos_pct + new_ahorro_pct + new_dev_pct
        if total_pct != 100:
            st.warning(f"Los porcentajes suman {total_pct}% (deben ser 100%)")

        st.markdown("**Preview:**")
        st.caption(f"Gastos:     ${new_ingreso * new_gastos_pct/100:,.0f}")
        st.caption(f"Ahorro:     ${new_ingreso * new_ahorro_pct/100:,.0f}")
        st.caption(f"Desarrollo: ${new_ingreso * new_dev_pct/100:,.0f}")

    if st.form_submit_button("Guardar configuración", type="primary", width="stretch"):
        if total_pct != 100:
            st.error("Los porcentajes deben sumar 100%.")
        else:
            set_config("ingreso_neto",       float(new_ingreso))
            set_config("meta_fondo",          float(new_fondo))
            set_config("limite_gastos_pct",   new_gastos_pct / 100)
            set_config("meta_ahorro_pct",     new_ahorro_pct / 100)
            set_config("meta_desarrollo_pct", new_dev_pct / 100)
            cfg_derived.clear(); invalidar()
            st.success("Configuración guardada."); st.rerun()

st.markdown('<div class="jf-section">Resumen actual</div>', unsafe_allow_html=True)
d = get_derived(cfg_actual)
r1, r2, r3, r4 = st.columns(4)
with r1: st.metric("Ingreso base",     f"${d['INGRESO_NETO']:,.0f}")
with r2: st.metric("Límite gastos 80%",f"${d['LIMITE_GASTOS']:,.0f}")
with r3: st.metric("Meta ahorro 10%",  f"${d['META_AHORRO']:,.0f}")
with r4: st.metric("Meta desarrollo",  f"${d['META_DESARROLLO']:,.0f}")

st.markdown('<div class="jf-section">Respaldo de datos</div>', unsafe_allow_html=True)
dl_col, ul_col = st.columns(2)

with dl_col:
    st.markdown("**⬇️ Exportar**")
    st.caption("Descarga tu base de datos antes de cualquier redeploy.")
    st.download_button(
        label="Descargar finanzas.db",
        data=DB_PATH.read_bytes(),
        file_name="finanzas.db",
        mime="application/octet-stream",
        width="stretch",
    )

with ul_col:
    st.markdown("**⬆️ Restaurar**")
    st.caption("Sube tu respaldo después de un redeploy para recuperar tus datos.")
    archivo = st.file_uploader("Selecciona finanzas.db", type=["db"], label_visibility="collapsed")
    if archivo is not None:
        if st.button("Restaurar base de datos", type="primary", width="stretch"):
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            DB_PATH.write_bytes(archivo.read())
            invalidar()
            st.success("Base de datos restaurada correctamente."); st.rerun()
