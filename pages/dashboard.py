import streamlit as st
from datetime import date
from utils import (
    cfg_derived, q_gastos_mes, q_ingresos_mes, q_saldo_ahorro,
    q_tc_hist, q_tc_pag, q_tc_pag_mes, q_fijos_set, q_gastos_trend, q_ingresos_trend,
    q_saldo_bolsillo, q_neto_bolsillo_mes,
    invalidar, rows_gastos, tc_card_html, budget_card_html, trend_chart,
    MESES_ES, GASTOS_FIJOS, CAT_ICON,
)
from database import set_fijo_estado

hoy = date.today()

CFG             = cfg_derived()
INGRESO_NETO    = CFG["INGRESO_NETO"]
LIMITE_GASTOS   = CFG["LIMITE_GASTOS"]
META_AHORRO     = CFG["META_AHORRO"]
META_DESARROLLO = CFG["META_DESARROLLO"]
META_FONDO      = CFG["META_FONDO_EMERGENCIA"]

anio, mes     = hoy.year, hoy.month
df_gastos     = q_gastos_mes(anio, mes)
df_ing_h      = q_ingresos_mes(anio, mes)
saldo_ahorro  = q_saldo_ahorro()

gasto_mes    = float(df_gastos["monto"].sum())                                               if not df_gastos.empty else 0.0
ingreso_mes  = float(df_ing_h["monto"].sum())                                                if not df_ing_h.empty else 0.0
gasto_td     = float(df_gastos[df_gastos["metodo_pago"] == "TD Bancolombia"]["monto"].sum())
gasto_dev    = float(df_gastos[df_gastos["categoria"]   == "Educación/Certs"]["monto"].sum())

hist_nu  = q_tc_hist("TC Nubank");    hist_bc  = q_tc_hist("TC Bancolombia")
pag_nu   = q_tc_pag("TC Nubank");     pag_bc   = q_tc_pag("TC Bancolombia")
pend_nu  = max(hist_nu - pag_nu, 0);  pend_bc  = max(hist_bc - pag_bc, 0)
pend_tc  = pend_nu + pend_bc
pagos_tc_mes = q_tc_pag_mes(anio, mes)

pct_gasto = gasto_mes / LIMITE_GASTOS   if LIMITE_GASTOS   > 0 else 0
pct_fondo = saldo_ahorro / META_FONDO   if META_FONDO      > 0 else 0
pct_dev   = gasto_dev / META_DESARROLLO if META_DESARROLLO > 0 else 0

saldo_bolsillo = q_saldo_bolsillo()
bolsillo_mes   = q_neto_bolsillo_mes(anio, mes)

balance  = ingreso_mes - gasto_td - pagos_tc_mes
_resto   = max(LIMITE_GASTOS - gasto_mes, 0)
_exceso  = max(gasto_mes - LIMITE_GASTOS, 0)
g_ok     = pct_gasto < 1.0
tc_ok    = pend_tc == 0

# ══════════════════════════════════════════════════════════════════════════════
# ALERTA DE PRESUPUESTO — solo aparece cuando supera el umbral
# ══════════════════════════════════════════════════════════════════════════════
if pct_gasto >= 1.0:
    st.markdown(f"""
<div class="jf-alert jf-alert--critical">
  <span class="jf-alert__icon">🚨</span>
  <div class="jf-alert__body">
    <div class="jf-alert__title">Presupuesto agotado — {pct_gasto*100:.0f}% ejecutado</div>
    <div class="jf-alert__sub">Gastaste <strong>${gasto_mes:,.0f}</strong> de un límite de ${LIMITE_GASTOS:,.0f} · Exceso: <strong>${_exceso:,.0f}</strong></div>
  </div>
  <div class="jf-alert__badge jf-alert__badge--critical">−${_exceso:,.0f} sobre límite</div>
</div>""", unsafe_allow_html=True)
elif pct_gasto >= 0.90:
    st.markdown(f"""
<div class="jf-alert jf-alert--danger">
  <span class="jf-alert__icon">🔴</span>
  <div class="jf-alert__body">
    <div class="jf-alert__title">Presupuesto crítico — {pct_gasto*100:.0f}% ejecutado</div>
    <div class="jf-alert__sub">Gastaste ${gasto_mes:,.0f} · Solo quedan <strong>${_resto:,.0f}</strong> disponibles este mes</div>
  </div>
  <div class="jf-alert__badge jf-alert__badge--danger">${_resto:,.0f} restantes</div>
</div>""", unsafe_allow_html=True)
elif pct_gasto >= 0.75:
    st.markdown(f"""
<div class="jf-alert jf-alert--warn">
  <span class="jf-alert__icon">⚡</span>
  <div class="jf-alert__body">
    <div class="jf-alert__title">Atención — {pct_gasto*100:.0f}% del presupuesto ejecutado</div>
    <div class="jf-alert__sub">Gastaste ${gasto_mes:,.0f} de ${LIMITE_GASTOS:,.0f} · Quedan <strong>${_resto:,.0f}</strong></div>
  </div>
  <div class="jf-alert__badge jf-alert__badge--warn">${_resto:,.0f} disponibles</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HERO — saldo de caja con flujo de dinero visual
# ══════════════════════════════════════════════════════════════════════════════
_neg      = balance < 0
_pct_disp = (balance / ingreso_mes * 100) if ingreso_mes > 0 else 0
_bar_w    = min(abs(_pct_disp), 100)
_bar_c    = "#EF4444" if _neg else ("#10B981" if _pct_disp > 40 else "#F59E0B")

# Bloques de flujo (ingresos → gastos → balance)
_bloques = ""
_items = [
    ("💵", "Ingresos", ingreso_mes, "#10B981"),
    ("🏧", "Débito TD", gasto_td, "#6366F1"),
    ("💳", "Pago TC", pagos_tc_mes, "#F43F5E"),
]
if saldo_bolsillo > 0:
    _items.append(("💼", "Bolsillo", saldo_bolsillo, "#F59E0B"))

for _ico, _lbl, _val, _col in _items:
    _bloques += f"""
<div class="jf-hero-flow-item">
  <div class="jf-hero-flow-icon">{_ico}</div>
  <div class="jf-hero-flow-val" style="color:{_col};">${_val:,.0f}</div>
  <div class="jf-hero-flow-lbl">{_lbl}</div>
</div>"""

st.markdown(f"""
<div class="jf-hero">
  <div class="jf-hero__eyebrow">
    {'⚠ Déficit' if _neg else 'Saldo de caja'} · {MESES_ES[mes]} {anio}
  </div>
  <div class="jf-hero__main">
    <div class="jf-hero__amount {'jf-hero__amount--neg' if _neg else ''}">
      {'−' if _neg else '+'}${abs(balance):,.0f}
      <span class="jf-hero__cop">COP</span>
    </div>
    <div class="jf-hero__badge {'jf-hero__badge--neg' if _neg else ''}">
      {'déficit' if _neg else f'{_pct_disp:.0f}% disponible'}
    </div>
  </div>
  <div class="jf-hero__bar-wrap">
    <div class="jf-hero__bar-bg">
      <div class="jf-hero__bar-fill" style="width:{_bar_w:.1f}%;background:{_bar_c};"></div>
    </div>
    <span class="jf-hero__bar-label">{'Déficit' if _neg else f'{_pct_disp:.0f}% del ingreso disponible'}</span>
  </div>
  <div class="jf-hero__flow">
    {_bloques}
  </div>
</div>""", unsafe_allow_html=True)

# Sin ingresos — aviso amable
if ingreso_mes == 0:
    st.info(f"Sin ingresos registrados este mes. Base de referencia: **${INGRESO_NETO:,.0f} COP**")

# ══════════════════════════════════════════════════════════════════════════════
# KPI STRIP — 4 tarjetas
# ══════════════════════════════════════════════════════════════════════════════
dg     = gasto_mes - LIMITE_GASTOS
td_pct = (gasto_td / ingreso_mes * 100) if ingreso_mes > 0 else 0
tc_pct = (pend_tc / (hist_nu + hist_bc) * 100) if (hist_nu + hist_bc) > 0 else 0

st.markdown(f"""
<div class="jf-kpi-grid">
  <div class="jf-kpi-card" style="--accent:#10B981;">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">💵</span><span class="jf-kpi-label">Ingresos mes</span></div>
    <div class="jf-kpi-val">${ingreso_mes:,.0f}</div>
    <div class="jf-kpi-sub" style="background:#F0FDF4;color:#059669;">{len(df_ing_h)} movimiento(s)</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(ingreso_mes/max(INGRESO_NETO,1)*100,100):.0f}%;background:#10B981;"></div></div>
  </div>
  <div class="jf-kpi-card" style="--accent:{'#10B981' if g_ok else '#EF4444'};">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">💸</span><span class="jf-kpi-label">Gastos del mes</span></div>
    <div class="jf-kpi-val">${gasto_mes:,.0f}</div>
    <div class="jf-kpi-sub" style="background:{'#F0FDF4' if g_ok else '#FEF2F2'};color:{'#059669' if g_ok else '#DC2626'};">${abs(dg):,.0f} {'bajo límite' if g_ok else 'sobre límite'}</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(pct_gasto*100,100):.0f}%;background:{'#10B981' if g_ok else '#EF4444'};"></div></div>
  </div>
  <div class="jf-kpi-card" style="--accent:#6366F1;">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">🏧</span><span class="jf-kpi-label">Débito TD</span></div>
    <div class="jf-kpi-val">${gasto_td:,.0f}</div>
    <div class="jf-kpi-sub" style="background:#EEF2FF;color:#4F46E5;">Salida real de caja</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(td_pct,100):.0f}%;background:#6366F1;"></div></div>
  </div>
  <div class="jf-kpi-card" style="--accent:{'#10B981' if tc_ok else '#F43F5E'};">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">💳</span><span class="jf-kpi-label">TC pendiente</span></div>
    <div class="jf-kpi-val">${pend_tc:,.0f}</div>
    <div class="jf-kpi-sub" style="background:{'#F0FDF4' if tc_ok else '#FEF2F2'};color:{'#059669' if tc_ok else '#DC2626'};"> {'Al día ✓' if tc_ok else 'Por saldar'}</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(tc_pct,100):.0f}%;background:{'#10B981' if tc_ok else '#F43F5E'};"></div></div>
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# REGLA 80/10/10 — 3 budget cards
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="jf-section">Regla 80 / 10 / 10</div>', unsafe_allow_html=True)

if pct_gasto >= 0.90:   g_c, g_bg, g_tc, g_st = "#EF4444", "#FEF2F2", "#DC2626", "⚠ Límite próximo"
elif pct_gasto >= 0.75: g_c, g_bg, g_tc, g_st = "#F59E0B", "#FFFBEB", "#D97706", "~ Atención"
else:                   g_c, g_bg, g_tc, g_st = "#10B981", "#F0FDF4", "#059669", "✓ Bajo control"

if pct_fondo >= 1.0:    f_c, f_bg, f_tc, f_st = "#10B981", "#F0FDF4", "#059669", "✓ Completado"
elif pct_fondo >= 0.5:  f_c, f_bg, f_tc, f_st = "#6366F1", "#EEF2FF", "#4F46E5", "↑ Progresando"
else:                   f_c, f_bg, f_tc, f_st = "#8B5CF6", "#F5F3FF", "#7C3AED", "→ En curso"

if pct_dev >= 1.0:      d_c, d_bg, d_tc, d_st = "#10B981", "#F0FDF4", "#059669", "✓ Meta cumplida"
elif pct_dev >= 0.5:    d_c, d_bg, d_tc, d_st = "#6366F1", "#EEF2FF", "#4F46E5", "↑ En progreso"
elif gasto_dev > 0:     d_c, d_bg, d_tc, d_st = "#F59E0B", "#FFFBEB", "#D97706", "→ Iniciando"
else:                   d_c, d_bg, d_tc, d_st = "#94A3B8", "#F8FAFC", "#64748B", "→ Sin registrar"

bc1, bc2, bc3 = st.columns(3)
with bc1: st.markdown(budget_card_html("Gastos del mes",       "Regla · 80%",    gasto_mes,    LIMITE_GASTOS,   pct_gasto, g_c, g_tc, g_bg, g_st, "💸"), unsafe_allow_html=True)
with bc2: st.markdown(budget_card_html("Fondo emergencia",     "Meta · 6 meses", saldo_ahorro, META_FONDO,      pct_fondo, f_c, f_tc, f_bg, f_st, "🏦"), unsafe_allow_html=True)
with bc3: st.markdown(budget_card_html("Desarrollo/inversión", "Regla · 10%",    gasto_dev,    META_DESARROLLO, pct_dev,   d_c, d_tc, d_bg, d_st, "🚀"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# BOLSILLO TC + TARJETAS — 2 cols (relacionados entre sí)
# ══════════════════════════════════════════════════════════════════════════════
col_bol, col_tc2 = st.columns([1, 1], gap="medium")

with col_bol:
    st.markdown('<div class="jf-section">💼 Bolsillo TC</div>', unsafe_allow_html=True)

    _falta  = max(pend_tc - saldo_bolsillo, 0)
    _sobra  = max(saldo_bolsillo - pend_tc, 0)
    _cobert = (saldo_bolsillo / pend_tc * 100) if pend_tc > 0 else 100.0
    _b_ok   = saldo_bolsillo >= pend_tc and pend_tc > 0
    _bc     = "#10B981" if _b_ok else ("#F59E0B" if saldo_bolsillo > 0 else "#94A3B8")
    _blbl   = "✓ Cubre la deuda" if _b_ok else ("⚠ Insuficiente" if saldo_bolsillo > 0 else ("✓ Sin deuda TC" if pend_tc == 0 else "→ Sin fondos"))
    _bdelta = (f"+${bolsillo_mes:,.0f} apartado este mes" if bolsillo_mes > 0
               else (f"−${abs(bolsillo_mes):,.0f} retirado este mes" if bolsillo_mes < 0
               else "Sin movimientos este mes"))

    if pend_tc == 0:
        _cv, _cc, _cbg, _cbdr, _cs = "Sin deuda", "#10B981", "#F0FDF4", "#BBF7D0", "✓ Tarjetas al día"
    elif saldo_bolsillo >= pend_tc:
        _cv, _cc, _cbg, _cbdr, _cs = f"{_cobert:.0f}%", "#10B981", "#F0FDF4", "#BBF7D0", f"+${_sobra:,.0f} sobra"
    else:
        _cv, _cc, _cbg, _cbdr, _cs = f"{_cobert:.0f}%", "#F59E0B", "#FFFBEB", "#FDE68A", f"Falta ${_falta:,.0f}"

    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(f"""
<div class="jf-mini-card" style="border-color:#E0E7FF;">
  <div class="jf-mini-card__label" style="color:#6366F1;">Bolsillo TC</div>
  <div class="jf-mini-card__val" style="color:{_bc};">${saldo_bolsillo:,.0f}</div>
  <div class="jf-mini-card__sub">{_bdelta}</div>
  <div class="jf-mini-card__badge" style="background:{'#F0FDF4' if _b_ok else '#FFFBEB' if saldo_bolsillo>0 else '#F8FAFC'};color:{_bc};">{_blbl}</div>
</div>""", unsafe_allow_html=True)
    with b2:
        _tcc = "#10B981" if pend_tc == 0 else "#F43F5E"
        st.markdown(f"""
<div class="jf-mini-card" style="border-color:#FECDD3;background:#FFF8F8;">
  <div class="jf-mini-card__label" style="color:#F43F5E;">TC Pendiente</div>
  <div class="jf-mini-card__val" style="color:{_tcc};">${pend_tc:,.0f}</div>
  <div class="jf-mini-card__sub">{'Al día ✓' if pend_tc==0 else 'Total por saldar'}</div>
</div>""", unsafe_allow_html=True)
    with b3:
        st.markdown(f"""
<div class="jf-mini-card" style="background:{_cbg};border-color:{_cbdr};">
  <div class="jf-mini-card__label" style="color:{_cc};">Cobertura</div>
  <div class="jf-mini-card__val" style="color:{_cc};">{_cv}</div>
  <div class="jf-mini-card__sub">{_cs}</div>
</div>""", unsafe_allow_html=True)

    if pend_tc > 0 and saldo_bolsillo < pend_tc:
        st.caption(f"💡 Faltan **${_falta:,.0f}** — ve a **💳 Tarjetas** para depositar.")

with col_tc2:
    st.markdown('<div class="jf-section">💳 Tarjetas de crédito</div>', unsafe_allow_html=True)
    t1, t2 = st.columns(2)
    with t1: st.markdown(tc_card_html("TC Nubank",      pend_nu, hist_nu, pag_nu), unsafe_allow_html=True)
    with t2: st.markdown(tc_card_html("TC Bancolombia", pend_bc, hist_bc, pag_bc), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GASTOS FIJOS — checklist mensual
# ══════════════════════════════════════════════════════════════════════════════
pagados_set   = q_fijos_set(anio, mes)
pagados_count = sum(1 for _, c in GASTOS_FIJOS if c in pagados_set)
pct_fijos     = pagados_count / len(GASTOS_FIJOS) if GASTOS_FIJOS else 0
_fbar_c       = "#10B981" if pct_fijos >= 0.8 else ("#F59E0B" if pct_fijos >= 0.5 else "#6366F1")

def _on_fijo(concepto: str, _a: int, _m: int):
    set_fijo_estado(concepto, _a, _m, st.session_state[f"fijo_{concepto}_{_a}_{_m}"])
    q_fijos_set.clear()

st.markdown(f"""
<div class="jf-fijos-header">
  <span class="jf-fijos-title">✓ Gastos fijos — {MESES_ES[mes]} {anio}</span>
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="width:120px;background:#E8EDFF;border-radius:99px;height:6px;overflow:hidden;">
      <div style="width:{pct_fijos*100:.0f}%;height:100%;background:{_fbar_c};border-radius:99px;transition:width .4s;"></div>
    </div>
    <span class="jf-fijos-badge">{pagados_count} / {len(GASTOS_FIJOS)}</span>
  </div>
</div>""", unsafe_allow_html=True)

fj1, fj2, fj3, fj4 = st.columns(4)
for i, (_, concepto) in enumerate(GASTOS_FIJOS):
    with [fj1, fj2, fj3, fj4][i % 4]:
        st.checkbox(concepto, value=concepto in pagados_set,
                    key=f"fijo_{concepto}_{anio}_{mes}",
                    on_change=_on_fijo, args=(concepto, anio, mes))

# ══════════════════════════════════════════════════════════════════════════════
# ÚLTIMOS GASTOS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="jf-section">Últimos gastos</div>', unsafe_allow_html=True)
if df_gastos.empty:
    st.info("Sin gastos registrados este mes.")
else:
    st.markdown(f'<div class="jf-gasto-list">{rows_gastos(df_gastos, 8)}</div>', unsafe_allow_html=True)
    if len(df_gastos) > 8:
        st.caption(f"Mostrando 8 de {len(df_gastos)} — ver todos en **➕ Registro**")

# ══════════════════════════════════════════════════════════════════════════════
# TENDENCIA 6 MESES
# ══════════════════════════════════════════════════════════════════════════════
df_gt = q_gastos_trend(7)
df_it = q_ingresos_trend(7)
if not df_gt.empty:
    st.markdown('<div class="jf-section">Tendencia 6 meses</div>', unsafe_allow_html=True)
    st.plotly_chart(trend_chart(df_gt, df_it), width="stretch", key="trend_home")
