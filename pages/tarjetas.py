import streamlit as st
from datetime import date
from utils import (
    q_tc_hist, q_tc_pag, q_pagos_tc, invalidar,
    confirmar_eliminar, tc_hero_html,
    q_saldo_bolsillo, q_movs_bolsillo,
)
from database import insertar_pago_tc, eliminar_pago_tc, insertar_bolsillo, eliminar_bolsillo

hoy = date.today()

_h_nu   = q_tc_hist("TC Nubank");    _h_bc   = q_tc_hist("TC Bancolombia")
_p_nu   = q_tc_pag("TC Nubank");     _p_bc   = q_tc_pag("TC Bancolombia")
_pnd_nu = max(_h_nu - _p_nu, 0);     _pnd_bc = max(_h_bc - _p_bc, 0)
_pnd_tot = _pnd_nu + _pnd_bc
saldo_b  = q_saldo_bolsillo()
cubre    = saldo_b >= _pnd_tot

# ── Banner ────────────────────────────────────────────────────────────────────
banner_c = "linear-gradient(135deg,#059669,#10B981)" if _pnd_tot == 0 else "linear-gradient(135deg,#0A0E1A,#1E1B4B)"
st.markdown(f"""
<div class="jf-tc-banner" style="background:{banner_c};">
  <div>
    <div class="jf-tc-banner-label">{'✓ Todas las tarjetas al día' if _pnd_tot==0 else 'Deuda total por saldar'}</div>
    <div class="jf-tc-banner-val">${_pnd_tot:,.0f} <span class="jf-tc-banner-sub">COP pendiente</span></div>
  </div>
  <div class="jf-tc-banner-right">
    <div class="jf-tc-banner-stat"><span>${_p_nu+_p_bc:,.0f}</span><small>Pagado histórico</small></div>
    <div class="jf-tc-banner-stat"><span>${_h_nu+_h_bc:,.0f}</span><small>Gastado total</small></div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Estado por tarjeta ────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Estado por tarjeta</div>', unsafe_allow_html=True)
h1, h2, h3 = st.columns([2, 2, 1])
with h1: st.markdown(tc_hero_html("TC Nubank",      _pnd_nu, _h_nu, _p_nu), unsafe_allow_html=True)
with h2: st.markdown(tc_hero_html("TC Bancolombia", _pnd_bc, _h_bc, _p_bc), unsafe_allow_html=True)
with h3:
    st.markdown(f"""
<div class="jf-tc-total">
  <div class="jf-tc-total-label">Total pendiente</div>
  <div class="jf-tc-total-monto" style="color:{'#10B981' if _pnd_tot==0 else '#F43F5E'};">${_pnd_tot:,.0f}</div>
  <div class="jf-tc-total-sub">{"✓ Sin deudas" if _pnd_tot==0 else "Pendiente"}</div>
  <hr style="margin:12px 0;border-color:#E2E8F0;">
  <div class="jf-tc-total-label">Pagado histórico</div>
  <div class="jf-tc-total-hist">${_p_nu+_p_bc:,.0f}</div>
</div>""", unsafe_allow_html=True)

# ── Bolsillo TC ───────────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">💼 Bolsillo TC</div>', unsafe_allow_html=True)

b_color  = "#10B981" if cubre else ("#F59E0B" if saldo_b > 0 else "#94A3B8")
b_status = "✓ Cubre la deuda" if cubre else ("⚠ Insuficiente" if saldo_b > 0 else "→ Sin fondos")
falta    = max(_pnd_tot - saldo_b, 0)

bl1, bl2, bl3 = st.columns(3)
with bl1:
    st.markdown(f"""
<div style="background:#F8FAFF;border:1.5px solid #E0E7FF;border-radius:14px;padding:20px 18px;">
  <div style="font-size:0.72rem;font-weight:600;color:#6366F1;text-transform:uppercase;letter-spacing:.5px;">Bolsillo disponible</div>
  <div style="font-size:1.8rem;font-weight:800;color:{b_color};margin:6px 0;">${saldo_b:,.0f}</div>
  <div style="font-size:0.78rem;padding:3px 10px;border-radius:20px;display:inline-block;
              background:{'#F0FDF4' if cubre else '#FFFBEB'};color:{b_color};font-weight:600;">{b_status}</div>
</div>""", unsafe_allow_html=True)
with bl2:
    st.markdown(f"""
<div style="background:#FFF1F2;border:1.5px solid #FECDD3;border-radius:14px;padding:20px 18px;">
  <div style="font-size:0.72rem;font-weight:600;color:#F43F5E;text-transform:uppercase;letter-spacing:.5px;">TC pendiente</div>
  <div style="font-size:1.8rem;font-weight:800;color:#F43F5E;margin:6px 0;">${_pnd_tot:,.0f}</div>
  <div style="font-size:0.78rem;color:#94A3B8;">{'Al día ✓' if _pnd_tot == 0 else f'Falta apartar ${falta:,.0f}'}</div>
</div>""", unsafe_allow_html=True)
with bl3:
    diferencia = saldo_b - _pnd_tot
    d_color = "#10B981" if diferencia >= 0 else "#F43F5E"
    st.markdown(f"""
<div style="background:#F8FAFC;border:1.5px solid #E2E8F0;border-radius:14px;padding:20px 18px;">
  <div style="font-size:0.72rem;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:.5px;">Diferencia</div>
  <div style="font-size:1.8rem;font-weight:800;color:{d_color};margin:6px 0;">{'+'if diferencia>=0 else ''}{diferencia:,.0f}</div>
  <div style="font-size:0.78rem;color:#94A3B8;">{'Sobra en bolsillo' if diferencia >= 0 else 'Falta en bolsillo'}</div>
</div>""", unsafe_allow_html=True)

tab_dep, tab_hist = st.tabs(["➕ Depositar / Retirar", "📋 Historial"])

with tab_dep:
    with st.form("form_bolsillo", clear_on_submit=True):
        fb1, fb2 = st.columns(2)
        with fb1:
            concepto_b = st.text_input("Concepto *", placeholder="Ej: Quincena 1 para TC, Prima...")
            monto_b    = st.number_input("Monto (COP) *", min_value=0, max_value=20_000_000, value=0, step=10_000, format="%d")
            fecha_b    = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
        with fb2:
            tipo_b = st.radio("Tipo *", ["deposito", "retiro"],
                              format_func=lambda x: "💰 Depositar (apartar del banco)" if x == "deposito" else "💸 Retirar (pagar extracto)")
            if tipo_b == "retiro":
                st.info("Al retirar del bolsillo, registra también el pago en **Pago de extracto** abajo.")
        if st.form_submit_button("Registrar", type="primary", width="stretch"):
            if monto_b <= 0:
                st.error("El monto debe ser mayor a $0.")
            elif not concepto_b.strip():
                st.error("Escribe un concepto.")
            else:
                insertar_bolsillo(fecha_b, concepto_b, monto_b, tipo_b)
                invalidar(); st.success(f"{'Depósito' if tipo_b=='deposito' else 'Retiro'} de **${monto_b:,.0f}** registrado."); st.rerun()

with tab_hist:
    df_b = q_movs_bolsillo()
    if df_b.empty:
        st.info("Sin movimientos en el bolsillo.")
    else:
        rows_b = ""
        for _, row in df_b.iterrows():
            es_dep = row["tipo"] == "deposito"
            rows_b += f"""
<div class="jf-gasto-row">
  <div class="jf-gasto-icon" style="background:{'#EEF2FF' if es_dep else '#FFF1F2'};">{'💰' if es_dep else '💸'}</div>
  <div class="jf-gasto-info">
    <div class="jf-gasto-desc">{row['concepto']}</div>
    <div class="jf-gasto-cat">{'Depósito' if es_dep else 'Retiro'} · {row['fecha']} · ID #{int(row['id'])}</div>
  </div>
  <div class="jf-gasto-right">
    <div style="font-size:0.95rem;font-weight:800;color:{'#6366F1' if es_dep else '#EF4444'};">
      {'+'if es_dep else '−'}${row['monto']:,.0f}
    </div>
  </div>
</div>"""
        st.markdown(f'<div class="jf-gasto-list">{rows_b}</div>', unsafe_allow_html=True)
        total_dep = float(df_b[df_b["tipo"] == "deposito"]["monto"].sum())
        total_ret = float(df_b[df_b["tipo"] == "retiro"]["monto"].sum())
        st.caption(f"Depositado: **${total_dep:,.0f}** · Retirado: **${total_ret:,.0f}** · Saldo: **${total_dep-total_ret:,.0f}**")

        with st.expander("🗑️ Eliminar un movimiento"):
            opts_b = {
                f"#{int(r['id'])} — {r['concepto']} · ${r['monto']:,.0f}": int(r['id'])
                for _, r in df_b.iterrows()
            }
            sel_b = st.selectbox("Selecciona", list(opts_b.keys()), key="sel_del_b")
            if confirmar_eliminar("bol") and st.button("Eliminar", type="secondary", key="btn_del_b"):
                eliminar_bolsillo(opts_b[sel_b]); invalidar()
                st.success("Movimiento eliminado."); st.rerun()

# ── Registrar pago de extracto ────────────────────────────────────────────────
st.markdown('<div class="jf-section">Registrar pago de extracto</div>', unsafe_allow_html=True)
st.caption("El pago del extracto salda la deuda acumulada y afecta el balance del mes.")
with st.form("form_pago_tc", clear_on_submit=True):
    pt1, pt2, pt3 = st.columns(3)
    with pt1: tarjeta_tc = st.radio("Tarjeta", ["TC Nubank", "TC Bancolombia"])
    with pt2: monto_tc   = st.number_input("Monto (COP)", min_value=0, max_value=20_000_000, value=0, step=10_000, format="%d")
    with pt3: fecha_tc   = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
    concepto_tc = st.text_input("Concepto (opcional)", placeholder="Ej: Pago extracto mayo Nubank")
    if st.form_submit_button("Registrar pago", type="primary", width="stretch"):
        if monto_tc <= 0:
            st.error("El monto debe ser mayor a $0.")
        else:
            insertar_pago_tc(fecha_tc, tarjeta_tc, monto_tc, concepto_tc)
            invalidar(); st.success(f"Pago de **${monto_tc:,.0f}** a {tarjeta_tc} registrado."); st.rerun()

# ── Historial pagos ───────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Historial de pagos</div>', unsafe_allow_html=True)
df_ptc = q_pagos_tc()
if df_ptc.empty:
    st.info("Aún no hay pagos registrados.")
else:
    _TC_CLR = {"TC Nubank": ("#FCE7F3", "#9D174D"), "TC Bancolombia": ("#FEF3C7", "#92400E")}
    rows_tc = ""
    for _, row in df_ptc.iterrows():
        tbg, tc_ = _TC_CLR.get(row["tarjeta"], ("#F1F5F9", "#64748B"))
        conc_tc  = row["concepto"] if row["concepto"] else "Pago de extracto"
        rows_tc += f"""
<div class="jf-gasto-row">
  <div class="jf-gasto-icon" style="background:#F0FDF4;">💳</div>
  <div class="jf-gasto-info">
    <div class="jf-gasto-desc">{conc_tc}</div>
    <div class="jf-gasto-cat">{row['fecha']} · ID #{int(row['id'])}</div>
  </div>
  <div class="jf-gasto-right">
    <div class="jf-ing-monto">+${row['monto']:,.0f}</div>
    <div class="jf-gasto-met" style="background:{tbg};color:{tc_};">{row['tarjeta']}</div>
  </div>
</div>"""
    st.markdown(f'<div class="jf-gasto-list">{rows_tc}</div>', unsafe_allow_html=True)
    st.caption(f"Total pagado: **${df_ptc['monto'].sum():,.0f} COP** · {len(df_ptc)} pago(s)")
    with st.expander("🗑️ Eliminar un pago"):
        id_dtc = st.number_input("ID", min_value=1, step=1, format="%d", key="del_ptc")
        if confirmar_eliminar("tc") and st.button("Eliminar", type="secondary", key="btn_del_ptc"):
            if id_dtc in df_ptc["id"].tolist():
                eliminar_pago_tc(int(id_dtc)); invalidar()
                st.success(f"Pago #{id_dtc} eliminado."); st.rerun()
            else:
                st.error(f"ID {id_dtc} no existe.")
