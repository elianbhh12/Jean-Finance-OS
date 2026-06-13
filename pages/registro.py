import streamlit as st
from datetime import date
from utils import (
    q_gastos_mes, invalidar, selector_mes, confirmar_eliminar, rows_gastos,
    MESES_ES,
)
from database import insertar_gasto, editar_gasto, eliminar_gasto, CATEGORIAS, METODOS_PAGO

hoy = date.today()

st.markdown('<div class="jf-section">Nuevo gasto</div>', unsafe_allow_html=True)
with st.form("form_gasto", clear_on_submit=True):
    rg1, rg2 = st.columns(2)
    with rg1:
        monto_g     = st.number_input("Monto (COP) *", min_value=0, max_value=10_000_000, value=0, step=1000, format="%d")
        descripcion = st.text_input("Descripción", placeholder="Ej: Éxito Laureles, gasolina...")
        nota_g      = st.text_input("Nota (opcional)", placeholder="Ej: cumpleaños de mamá")
        fecha_g     = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
        metodo_pago = st.radio("Método de pago *", METODOS_PAGO, horizontal=True)
    with rg2:
        categoria = st.selectbox("Categoría *", CATEGORIAS)
        st.markdown("&nbsp;")
        st.info("Compras con TC no descuentan de caja hasta pagar el extracto en **💳 Tarjetas**.")
    if st.form_submit_button("Registrar gasto", width="stretch", type="primary"):
        if monto_g <= 0:
            st.error("El monto debe ser mayor a $0.")
        else:
            insertar_gasto(fecha_g, descripcion, categoria, monto_g, metodo_pago, nota_g)
            invalidar(); st.success(f"Gasto de **${monto_g:,.0f}** en **{categoria}** registrado."); st.rerun()

# ── Historial ─────────────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Historial</div>', unsafe_allow_html=True)
anio_r, mes_r = selector_mes("reg")
df_r = q_gastos_mes(anio_r, mes_r)

if df_r.empty:
    st.info(f"Sin gastos en {MESES_ES[mes_r]} {anio_r}.")
else:
    rf1, rf2 = st.columns(2)
    with rf1: filtro_cat = st.multiselect("Categoría", sorted(df_r["categoria"].unique()), key="fc_r")
    with rf2: filtro_met = st.multiselect("Método",    sorted(df_r["metodo_pago"].unique()), key="fm_r")
    df_f = df_r.copy()
    if filtro_cat: df_f = df_f[df_f["categoria"].isin(filtro_cat)]
    if filtro_met: df_f = df_f[df_f["metodo_pago"].isin(filtro_met)]
    st.markdown(f'<div class="jf-gasto-list">{rows_gastos(df_f)}</div>', unsafe_allow_html=True)
    st.caption(f"Total: **${df_f['monto'].sum():,.0f} COP** · {len(df_f)} de {len(df_r)} transacciones")

    with st.expander("✏️ Editar un gasto"):
        opts_g = {
            f"#{int(r['id'])} — {r['categoria']} · {r['descripcion'] or '(sin desc)'} · ${r['monto']:,.0f}": int(r['id'])
            for _, r in df_r.iterrows()
        }
        sel_g = st.selectbox("Selecciona el gasto", list(opts_g.keys()), key="sel_eg")
        fg    = df_r[df_r["id"] == opts_g[sel_g]].iloc[0]
        gg1, gg2 = st.columns(2)
        with gg1:
            new_desc = st.text_input("Descripción", value=fg["descripcion"], key="eg_desc")
            new_nota = st.text_input("Nota",         value=fg.get("nota", ""), key="eg_nota")
            new_mont = st.number_input("Monto", value=float(fg.get("monto", 0)), step=1000.0, format="%.0f", key="eg_monto")
            new_fech = st.date_input("Fecha", value=date.fromisoformat(str(fg.get("fecha", str(hoy)))), key="eg_fecha")
        with gg2:
            new_cat = st.selectbox("Categoría", CATEGORIAS,
                                   index=CATEGORIAS.index(fg["categoria"]) if fg["categoria"] in CATEGORIAS else 0,
                                   key="eg_cat")
            new_met = st.radio("Método", METODOS_PAGO,
                               index=METODOS_PAGO.index(fg["metodo_pago"]) if fg["metodo_pago"] in METODOS_PAGO else 0,
                               key="eg_met")
        if st.button("Guardar cambios", key="btn_eg", type="primary"):
            editar_gasto(opts_g[sel_g], new_fech, new_desc or "", new_cat, new_mont, new_met or "", new_nota or "")
            invalidar(); st.success("Gasto actualizado."); st.rerun()

    with st.expander("🗑️ Eliminar un gasto"):
        opts_dg = {
            f"#{int(r['id'])} — {r['categoria']} · {r['descripcion'] or '(sin desc)'} · ${r['monto']:,.0f}": int(r['id'])
            for _, r in df_r.iterrows()
        }
        sel_dg = st.selectbox("Selecciona el gasto a eliminar", list(opts_dg.keys()), key="sel_del_g")
        if confirmar_eliminar("gasto") and st.button("Eliminar", type="secondary", key="btn_del_g"):
            eliminar_gasto(opts_dg[sel_dg]); invalidar()
            st.success("Gasto eliminado."); st.rerun()
