import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from database import (
    init_db, get_config, set_config, get_derived,
    insertar_gasto, editar_gasto, eliminar_gasto,
    obtener_gastos_mes, gasto_total_mes,
    gasto_por_categoria_mes, gasto_por_metodo_mes, gastos_ultimos_meses,
    insertar_movimiento_ahorro, obtener_saldo_ahorro,
    obtener_movimientos_ahorro, proyeccion_fondo,
    insertar_ingreso, editar_ingreso, obtener_ingresos_mes,
    total_ingresos_mes, eliminar_ingreso, ingresos_ultimos_meses,
    get_fijos_pagados_mes, set_fijo_estado,
    insertar_pago_tc, total_pagado_tc, total_pagado_tc_mes,
    obtener_pagos_tc, eliminar_pago_tc, total_gastos_tc_historico,
    CATEGORIAS, METODOS_PAGO, TIPOS_INGRESO,
)

# ─── Constantes UI (definidas UNA sola vez) ───────────────────────────────────
CAT_ICON: dict[str, str] = {
    "Alimentación":"🛒","Transporte":"🚗","Vivienda":"🏠","Servicios":"⚡",
    "Suscripción":"📱","Salud":"💊","Educación/Certs":"📚","Deseos":"🎯",
    "Ropa":"👕","Varios":"📦","Tarjeta":"💳",
}
MET_COLOR: dict[str, tuple[str,str]] = {
    "TD Bancolombia": ("#DBEAFE","#2563EB"),
    "TC Nubank":      ("#FCE7F3","#9D174D"),
    "TC Bancolombia": ("#FEF3C7","#92400E"),
}
TIPO_ICON: dict[str, str] = {
    "Quincenal 1":"💵","Quincenal 2":"💵","Bono":"🎁",
    "Prima":"⭐","Extra":"✨","Comisión":"📊","Otros":"💰",
}
GASTOS_FIJOS = [
    ("Alimentación","Mercado"),    ("Salud","Gimnasio"),
    ("Servicios","Peluquería"),    ("Servicios","Celular"),
    ("Suscripción","Apple"),       ("Suscripción","IA"),
    ("Tarjeta","Cuota Tarjeta"),   ("Transporte","Gasolina"),
    ("Servicios","EPM"),           ("Servicios","Internet"),
    ("Vivienda","Arriendo"),
]
MESES_ES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
            7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
BAR_COLORS = ["#6366F1","#8B5CF6","#EC4899","#F59E0B","#10B981","#3B82F6"]

# ─── Configuración Streamlit ──────────────────────────────────────────────────
st.set_page_config(page_title="Jean Finance OS", page_icon="💰",
                   layout="wide", initial_sidebar_state="collapsed")
init_db()

_css = (Path(__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

hoy = date.today()

# ─── Config dinámica (cacheada 60 s) ─────────────────────────────────────────
@st.cache_data(ttl=60)
def _cfg() -> dict[str, float]:
    return get_derived()

CFG            = _cfg()
INGRESO_NETO   = CFG["INGRESO_NETO"]
LIMITE_GASTOS  = CFG["LIMITE_GASTOS"]
META_AHORRO    = CFG["META_AHORRO"]
META_DESARROLLO= CFG["META_DESARROLLO"]
META_FONDO     = CFG["META_FONDO_EMERGENCIA"]

# ─── Queries cacheadas ────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _gastos_mes(a: int, m: int):      return obtener_gastos_mes(a, m)

@st.cache_data(ttl=30)
def _ingresos_mes(a: int, m: int):    return obtener_ingresos_mes(a, m)

@st.cache_data(ttl=30)
def _saldo_ahorro():                   return obtener_saldo_ahorro()

@st.cache_data(ttl=30)
def _pagos_tc():                       return obtener_pagos_tc()

@st.cache_data(ttl=30)
def _movs_ahorro():                    return obtener_movimientos_ahorro()

@st.cache_data(ttl=60)
def _gastos_trend(n: int = 7):         return gastos_ultimos_meses(n)

@st.cache_data(ttl=60)
def _ingresos_trend(n: int = 7):       return ingresos_ultimos_meses(n)

@st.cache_data(ttl=30)
def _tc_hist(tarjeta: str):            return total_gastos_tc_historico(tarjeta)

@st.cache_data(ttl=30)
def _tc_pag(tarjeta: str):             return total_pagado_tc(tarjeta)

@st.cache_data(ttl=30)
def _tc_pag_mes(a: int, m: int):       return total_pagado_tc_mes(a, m)

@st.cache_data(ttl=30)
def _fijos_set(a: int, m: int):        return get_fijos_pagados_mes(a, m)


def _invalidar():
    """Limpia todas las caches tras mutaciones."""
    _gastos_mes.clear(); _ingresos_mes.clear(); _saldo_ahorro.clear()
    _pagos_tc.clear();   _movs_ahorro.clear();  _gastos_trend.clear()
    _ingresos_trend.clear(); _tc_hist.clear(); _tc_pag.clear()
    _tc_pag_mes.clear(); _fijos_set.clear()


# ─── Helpers UI ──────────────────────────────────────────────────────────────

def _selector_mes(key: str) -> tuple[int, int]:
    anos = list(range(2024, hoy.year + 3))
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        a = st.selectbox("Año", anos, index=anos.index(hoy.year), key=f"{key}_a")
    with c2:
        m = st.selectbox("Mes", range(1,13), format_func=lambda x: MESES_ES[x],
                         index=hoy.month-1, key=f"{key}_m")
    return a, m


def _rows_gastos(df, limit: int | None = None) -> str:
    rows = ""
    iterable = df.head(limit).iterrows() if limit else df.iterrows()
    for _, row in iterable:
        icon = CAT_ICON.get(row["categoria"], "📦")
        mbg, mc = MET_COLOR.get(row["metodo_pago"], ("#F1F5F9","#64748B"))
        desc = row["descripcion"] if row.get("descripcion") else row["categoria"]
        nota_html = f'<div class="jf-gasto-nota">📝 {row["nota"]}</div>' if row.get("nota") else ""
        rows += f"""
<div class="jf-gasto-row">
  <div class="jf-gasto-icon">{icon}</div>
  <div class="jf-gasto-info">
    <div class="jf-gasto-desc">{desc}</div>
    <div class="jf-gasto-cat">{row['categoria']} · {row['fecha']} · ID #{int(row['id'])}</div>
    {nota_html}
  </div>
  <div class="jf-gasto-right">
    <div class="jf-gasto-monto">−${row['monto']:,.0f}</div>
    <div class="jf-gasto-met" style="background:{mbg};color:{mc};">{row['metodo_pago']}</div>
  </div>
</div>"""
    return rows


def _tc_card_html(nombre: str, pendiente: float, gastado: float, pagado: float) -> str:
    al_dia = pendiente == 0
    pct    = (pagado / gastado * 100) if gastado > 0 else 0
    color  = "#10B981" if al_dia else "#F43F5E"
    bg     = "#F0FDF4" if al_dia else "#FFF1F2"
    border = "#BBF7D0" if al_dia else "#FECDD3"
    estado = "Al día ✓" if al_dia else f"${pendiente:,.0f} por pagar"
    return f"""
<div class="jf-tc-card">
  <div class="jf-tc-top">
    <span class="jf-tc-nombre">{nombre}</span>
    <span class="jf-tc-badge" style="background:{bg};color:{color};border-color:{border};">{estado}</span>
  </div>
  <div class="jf-tc-monto" style="color:{'#0F172A' if al_dia else color};">${pendiente:,.0f}</div>
  <div class="jf-tc-bar-bg"><div class="jf-tc-bar-fill" style="width:{min(pct,100):.1f}%;background:{color};"></div></div>
  <div class="jf-tc-detail">Gastado <strong>${gastado:,.0f}</strong> &nbsp;·&nbsp; Pagado <strong>${pagado:,.0f}</strong> &nbsp;·&nbsp; {pct:.0f}% saldado</div>
</div>"""


def _tc_hero_html(nombre: str, pendiente: float, gastado: float, pagado: float) -> str:
    al_dia = pendiente == 0
    pct    = (pagado / gastado * 100) if gastado > 0 else 0
    hdr    = "linear-gradient(135deg,#059669,#10B981)" if al_dia else "linear-gradient(135deg,#BE123C,#F43F5E)"
    return f"""
<div class="jf-tc-hero">
  <div class="jf-tc-hero-header" style="background:{hdr};">
    <div>
      <div class="jf-tc-hero-label">Tarjeta de crédito</div>
      <div class="jf-tc-hero-name">{nombre}</div>
    </div>
    <div class="jf-tc-hero-estado">
      <span class="jf-tc-hero-icono">{'✓' if al_dia else '!'}</span>
      <span>{'AL DÍA' if al_dia else 'PENDIENTE'}</span>
    </div>
  </div>
  <div class="jf-tc-hero-body">
    <div class="jf-tc-hero-sublabel">{'Saldo al día' if al_dia else 'Por pagar'}</div>
    <div class="jf-tc-hero-monto" style="color:{'#10B981' if al_dia else '#F43F5E'};">${pendiente:,.0f}</div>
    <div class="jf-tc-bar-bg" style="margin:12px 0 8px;">
      <div class="jf-tc-bar-fill" style="width:{min(pct,100):.1f}%;background:{'#10B981' if al_dia else '#6366F1'};"></div>
    </div>
    <div class="jf-tc-hero-row"><span>Gastado total</span><strong>${gastado:,.0f}</strong></div>
    <div class="jf-tc-hero-row"><span>Pagado</span><strong style="color:#10B981;">${pagado:,.0f}</strong></div>
    <div class="jf-tc-hero-row"><span>% saldado</span><strong>{pct:.0f}%</strong></div>
  </div>
</div>"""


def _budget_card_html(titulo: str, regla: str, valor: float, meta: float,
                      pct: float, bar_c: str, st_c: str, st_bg: str,
                      st_txt: str, icon: str) -> str:
    pct_bar  = min(pct * 100, 100)
    resto    = max(meta - valor, 0)
    return f"""
<div class="jf-budget-card">
  <div class="jf-budget-header">
    <div class="jf-budget-icon">{icon}</div>
    <div class="jf-budget-rule">{regla}</div>
    <div class="jf-budget-status" style="background:{st_bg};color:{st_c};">{st_txt}</div>
  </div>
  <div class="jf-budget-pct" style="color:{bar_c};">{pct*100:.0f}<span class="jf-budget-sym">%</span></div>
  <div class="jf-budget-titulo">{titulo}</div>
  <div class="jf-budget-bar-bg">
    <div class="jf-budget-bar-fill" style="width:{pct_bar:.1f}%;background:{bar_c};"></div>
  </div>
  <div class="jf-budget-foot">
    <span class="jf-budget-val">${valor:,.0f}</span>
    <span class="jf-budget-sep">/</span>
    <span class="jf-budget-meta">${meta:,.0f}</span>
  </div>
  <div class="jf-budget-resto">Quedan <strong>${resto:,.0f}</strong></div>
</div>"""


def _confirmar_eliminar(key: str) -> bool:
    """Retorna True solo cuando el usuario confirmó y presionó eliminar."""
    st.caption("⚠️ Esta acción no se puede deshacer.")
    confirmado = st.checkbox("Confirmo que quiero eliminar este registro", key=f"conf_{key}")
    return confirmado


def _trend_chart(df_g: "pd.DataFrame", df_i: "pd.DataFrame") -> go.Figure:
    df_g  = df_g.sort_values("periodo")
    df_i  = df_i.sort_values("periodo") if not df_i.empty else df_i
    meses = df_g["periodo"].tolist() if not df_g.empty else []
    if df_i.empty is False:
        meses = sorted(set(meses) | set(df_i["periodo"].tolist()))
    fig = go.Figure()
    if not df_g.empty:
        fig.add_trace(go.Scatter(
            x=df_g["periodo"], y=df_g["total"], name="Gastos",
            line=dict(color="#F43F5E", width=2.5), fill="tozeroy",
            fillcolor="rgba(244,63,94,0.08)",
            mode="lines+markers", marker=dict(size=6, color="#F43F5E")))
    if not df_i.empty:
        fig.add_trace(go.Scatter(
            x=df_i["periodo"], y=df_i["total"], name="Ingresos",
            line=dict(color="#10B981", width=2.5),
            mode="lines+markers", marker=dict(size=6, color="#10B981")))
    fig.update_layout(
        height=240, margin=dict(t=10,b=10,l=0,r=0),
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#F0F4FF",
                   color="#CBD5E1", showgrid=True, zeroline=False),
        xaxis=dict(color="#CBD5E1", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color="#94A3B8", size=11)),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#94A3B8"))
    return fig


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="jf-header">
  <div class="jf-logo">💰</div>
  <div>
    <div class="jf-title">Jean Finance OS</div>
    <div class="jf-subtitle">Regla 80 / 10 / 20</div>
  </div>
  <div class="jf-header-badge">Base mensual &nbsp;<span>${INGRESO_NETO:,.0f} COP</span></div>
</div>
""", unsafe_allow_html=True)

(tab_home, tab_ingresos, tab_registro, tab_tc,
 tab_ahorro, tab_analisis, tab_config) = st.tabs([
    "📊 Dashboard", "💵 Ingresos", "➕ Registro",
    "💳 Tarjetas", "🐷 Ahorro", "📈 Análisis", "⚙️ Config",
])

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_home:
    anio, mes    = hoy.year, hoy.month
    df_gastos    = _gastos_mes(anio, mes)
    df_ing_h     = _ingresos_mes(anio, mes)
    saldo_ahorro = _saldo_ahorro()

    gasto_mes    = float(df_gastos["monto"].sum()) if not df_gastos.empty else 0.0
    ingreso_mes  = float(df_ing_h["monto"].sum())  if not df_ing_h.empty else 0.0
    gasto_td     = float(df_gastos[df_gastos["metodo_pago"]=="TD Bancolombia"]["monto"].sum())

    hist_nu  = _tc_hist("TC Nubank");    hist_bc  = _tc_hist("TC Bancolombia")
    pag_nu   = _tc_pag("TC Nubank");    pag_bc   = _tc_pag("TC Bancolombia")
    pend_nu  = max(hist_nu - pag_nu, 0); pend_bc  = max(hist_bc - pag_bc, 0)
    pend_tc  = pend_nu + pend_bc
    pagos_tc_mes = _tc_pag_mes(anio, mes)

    pct_gasto = gasto_mes / LIMITE_GASTOS  if LIMITE_GASTOS > 0  else 0
    pct_fondo = saldo_ahorro / META_FONDO  if META_FONDO > 0     else 0

    # Balance hero
    if ingreso_mes > 0:
        balance  = ingreso_mes - gasto_td - pagos_tc_mes
        neg      = balance < 0
        pct_disp = balance / ingreso_mes * 100
        sub      = f"Ingresos ${ingreso_mes:,.0f} · TD ${gasto_td:,.0f}"
        if pagos_tc_mes > 0: sub += f" · Pago TC ${pagos_tc_mes:,.0f}"
        st.markdown(f"""
<div class="jf-balance-card {'negative' if neg else ''}">
  <div class="jf-balance-left">
    <div class="jf-balance-label">{'Déficit' if neg else 'Saldo de caja'} — {MESES_ES[mes]} {anio}</div>
    <div class="jf-balance-value">{'−' if neg else '+'}${abs(balance):,.0f} COP</div>
    <div class="jf-balance-sub">{sub}</div>
  </div>
  <div class="jf-balance-badge">{'déficit' if neg else f'{pct_disp:.0f}% disponible'}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.info(f"Sin ingresos registrados este mes. Base de referencia: **${INGRESO_NETO:,.0f} COP**")

    # KPI cards
    dg = gasto_mes - LIMITE_GASTOS
    g_ok  = dg <= 0
    tc_ok = pend_tc == 0
    td_pct = (gasto_td / ingreso_mes * 100) if ingreso_mes > 0 else 0
    tc_pct = (pend_tc / (hist_nu+hist_bc) * 100) if (hist_nu+hist_bc) > 0 else 0

    st.markdown(f"""
<div class="jf-kpi-grid">
  <div class="jf-kpi-card" style="--accent:#10B981;">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">💵</span><span class="jf-kpi-label">Ingresos</span></div>
    <div class="jf-kpi-val">${ingreso_mes:,.0f}</div>
    <div class="jf-kpi-sub" style="background:#F0FDF4;color:#059669;">{len(df_ing_h)} movimiento(s)</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(ingreso_mes/INGRESO_NETO*100,100):.0f}%;background:#10B981;"></div></div>
  </div>
  <div class="jf-kpi-card" style="--accent:{'#10B981' if g_ok else '#EF4444'};">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">💸</span><span class="jf-kpi-label">Gastos del mes</span></div>
    <div class="jf-kpi-val">${gasto_mes:,.0f}</div>
    <div class="jf-kpi-sub" style="background:{'#F0FDF4' if g_ok else '#FEF2F2'};color:{'#059669' if g_ok else '#DC2626'};">${abs(dg):,.0f} {'bajo' if g_ok else 'sobre'} límite</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(pct_gasto*100,100):.0f}%;background:{'#10B981' if g_ok else '#EF4444'};"></div></div>
  </div>
  <div class="jf-kpi-card" style="--accent:#6366F1;">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">🏦</span><span class="jf-kpi-label">Débito (TD)</span></div>
    <div class="jf-kpi-val">${gasto_td:,.0f}</div>
    <div class="jf-kpi-sub" style="background:#EEF2FF;color:#4F46E5;">Salida real de caja</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(td_pct,100):.0f}%;background:#6366F1;"></div></div>
  </div>
  <div class="jf-kpi-card" style="--accent:{'#10B981' if tc_ok else '#F43F5E'};">
    <div class="jf-kpi-top"><span class="jf-kpi-icon">💳</span><span class="jf-kpi-label">TC pendiente</span></div>
    <div class="jf-kpi-val">${pend_tc:,.0f}</div>
    <div class="jf-kpi-sub" style="background:{'#F0FDF4' if tc_ok else '#FEF2F2'};color:{'#059669' if tc_ok else '#DC2626'};">{'Al día ✓' if tc_ok else 'Por saldar'}</div>
    <div class="jf-kpi-bar-bg"><div class="jf-kpi-bar" style="width:{min(tc_pct,100):.0f}%;background:{'#10B981' if tc_ok else '#F43F5E'};"></div></div>
  </div>
</div>""", unsafe_allow_html=True)

    # TC cards
    st.markdown('<div class="jf-section">Tarjetas de crédito</div>', unsafe_allow_html=True)
    t1, t2 = st.columns(2)
    with t1: st.markdown(_tc_card_html("TC Nubank",      pend_nu, hist_nu, pag_nu), unsafe_allow_html=True)
    with t2: st.markdown(_tc_card_html("TC Bancolombia", pend_bc, hist_bc, pag_bc), unsafe_allow_html=True)

    # Budget cards 80/10/20
    st.markdown('<div class="jf-section">Regla 80 / 10 / 20</div>', unsafe_allow_html=True)
    pagados_set   = _fijos_set(anio, mes)
    pagados_count = sum(1 for _, c in GASTOS_FIJOS if c in pagados_set)

    def _on_fijo(concepto: str, _a: int, _m: int):
        set_fijo_estado(concepto, _a, _m, st.session_state[f"fijo_{concepto}_{_a}_{_m}"])
        _fijos_set.clear()

    if pct_gasto >= 0.85:   g_c,g_bg,g_tc,g_st = "#EF4444","#FEF2F2","#DC2626","⚠ Límite próximo"
    elif pct_gasto >= 0.70: g_c,g_bg,g_tc,g_st = "#F59E0B","#FFFBEB","#D97706","~ Atención"
    else:                   g_c,g_bg,g_tc,g_st = "#10B981","#F0FDF4","#059669","✓ Bajo control"

    if pct_fondo >= 1.0:    f_c,f_bg,f_tc,f_st = "#10B981","#F0FDF4","#059669","✓ Completado"
    elif pct_fondo >= 0.5:  f_c,f_bg,f_tc,f_st = "#6366F1","#EEF2FF","#4F46E5","↑ Progresando"
    else:                   f_c,f_bg,f_tc,f_st = "#8B5CF6","#F5F3FF","#7C3AED","→ En curso"

    bc1, bc2, bc3 = st.columns(3)
    with bc1: st.markdown(_budget_card_html("Gastos del mes","Regla · 80%",gasto_mes,LIMITE_GASTOS,pct_gasto,g_c,g_tc,g_bg,g_st,"💸"), unsafe_allow_html=True)
    with bc2: st.markdown(_budget_card_html("Fondo emergencia","Meta · 6 meses",saldo_ahorro,META_FONDO,pct_fondo,f_c,f_tc,f_bg,f_st,"🏦"), unsafe_allow_html=True)
    with bc3: st.markdown(_budget_card_html("Desarrollo / inversión","Regla · 20%",0,META_DESARROLLO,0.0,"#94A3B8","#64748B","#F8FAFC","→ Sin registrar","🚀"), unsafe_allow_html=True)

    # Fijos checklist
    st.markdown(f"""
<div class="jf-fijos-header">
  <span class="jf-fijos-title">Gastos fijos — {MESES_ES[mes]} {anio}</span>
  <span class="jf-fijos-badge">{pagados_count} / {len(GASTOS_FIJOS)} pagados</span>
</div>""", unsafe_allow_html=True)
    fj1, fj2, fj3, fj4 = st.columns(4)
    for i, (_, concepto) in enumerate(GASTOS_FIJOS):
        with [fj1,fj2,fj3,fj4][i % 4]:
            st.checkbox(concepto, value=concepto in pagados_set,
                        key=f"fijo_{concepto}_{anio}_{mes}",
                        on_change=_on_fijo, args=(concepto, anio, mes))

    # Últimos gastos
    st.markdown('<div class="jf-section">Últimos gastos</div>', unsafe_allow_html=True)
    if df_gastos.empty:
        st.info("Sin gastos este mes.")
    else:
        st.markdown(f'<div class="jf-gasto-list">{_rows_gastos(df_gastos, 8)}</div>', unsafe_allow_html=True)
        if len(df_gastos) > 8:
            st.caption(f"Mostrando 8 de {len(df_gastos)} · Ver todos en **➕ Registro**")

    # Tendencia rápida
    df_gt = _gastos_trend(7)
    df_it = _ingresos_trend(7)
    if not df_gt.empty:
        st.markdown('<div class="jf-section">Tendencia 6 meses</div>', unsafe_allow_html=True)
        st.plotly_chart(_trend_chart(df_gt, df_it), use_container_width=True, key="trend_home")


# ══════════════════════════════════════════════════════════════════════════════
#  INGRESOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ingresos:
    anio_i, mes_i = _selector_mes("ing")
    df_ing    = _ingresos_mes(anio_i, mes_i)
    total_ing = float(df_ing["monto"].sum()) if not df_ing.empty else 0.0
    diff_i    = total_ing - INGRESO_NETO
    pct_ing   = (total_ing / INGRESO_NETO * 100) if INGRESO_NETO > 0 else 0
    q_sum     = float(df_ing[df_ing["tipo"].isin(["Quincenal 1","Quincenal 2"])]["monto"].sum()) if not df_ing.empty else 0.0

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

    st.markdown('<div class="jf-section">Registrar ingreso</div>', unsafe_allow_html=True)
    with st.form("form_ingreso", clear_on_submit=True):
        fi1, fi2 = st.columns(2)
        with fi1:
            concepto_i = st.text_input("Concepto *", placeholder="Ej: Quincena 1, Prima...")
            monto_i    = st.number_input("Monto (COP) *", min_value=0, max_value=50_000_000, value=0, step=50_000, format="%d")
            fecha_i    = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
            nota_i     = st.text_input("Nota (opcional)", placeholder="Ej: con comisión de ventas incluida")
        with fi2:
            tipo_i = st.radio("Tipo *", TIPOS_INGRESO)
        if st.form_submit_button("Registrar ingreso", use_container_width=True, type="primary"):
            if monto_i <= 0: st.error("El monto debe ser mayor a $0.")
            elif not concepto_i.strip(): st.error("Escribe un concepto.")
            else:
                insertar_ingreso(fecha_i, concepto_i, monto_i, tipo_i, nota_i)
                _invalidar(); st.success(f"Ingreso de **${monto_i:,.0f}** registrado."); st.rerun()

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
            opts_i = {
                f"#{int(r['id'])} — {r['concepto']} · ${r['monto']:,.0f}": int(r['id'])
                for _, r in df_ing.iterrows()
            }
            sel_i = st.selectbox("Selecciona el ingreso", list(opts_i.keys()), key="sel_ei")
            fe = df_ing[df_ing["id"] == opts_i[sel_i]].iloc[0]
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
                _invalidar(); st.success("Ingreso actualizado."); st.rerun()

        with st.expander("🗑️ Eliminar un ingreso"):
            opts_di = {
                f"#{int(r['id'])} — {r['concepto']} · ${r['monto']:,.0f}": int(r['id'])
                for _, r in df_ing.iterrows()
            }
            sel_di = st.selectbox("Selecciona el ingreso a eliminar", list(opts_di.keys()), key="sel_del_i")
            if _confirmar_eliminar("ing") and st.button("Eliminar", type="secondary", key="btn_del_i"):
                eliminar_ingreso(opts_di[sel_di]); _invalidar()
                st.success(f"Ingreso eliminado."); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRO DE GASTOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_registro:
    st.markdown('<div class="jf-section">Nuevo gasto</div>', unsafe_allow_html=True)
    with st.form("form_gasto", clear_on_submit=True):
        rg1, rg2 = st.columns(2)
        with rg1:
            monto_g     = st.number_input("Monto (COP) *", min_value=0, max_value=10_000_000, value=0, step=1000, format="%d")
            descripcion = st.text_input("Descripción", placeholder="Ej: Éxito Laureles, gasolina...")
            nota_g      = st.text_input("Nota (opcional)", placeholder="Ej: cumpleaños de mamá, vuelo a Bogotá")
            fecha_g     = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
            metodo_pago = st.radio("Método de pago *", METODOS_PAGO, horizontal=True)
        with rg2:
            categoria = st.selectbox("Categoría *", CATEGORIAS)
            st.markdown("&nbsp;")
            st.info("Compras con TC no descuentan de caja hasta pagar el extracto en **💳 Tarjetas**.")
        if st.form_submit_button("Registrar gasto", use_container_width=True, type="primary"):
            if monto_g <= 0: st.error("El monto debe ser mayor a $0.")
            else:
                insertar_gasto(fecha_g, descripcion, categoria, monto_g, metodo_pago, nota_g)
                _invalidar(); st.success(f"Gasto de **${monto_g:,.0f}** en **{categoria}** registrado.")

    st.markdown('<div class="jf-section">Historial</div>', unsafe_allow_html=True)
    anio_r, mes_r = _selector_mes("reg")
    df_r = _gastos_mes(anio_r, mes_r)
    if df_r.empty:
        st.info(f"Sin gastos en {MESES_ES[mes_r]} {anio_r}.")
    else:
        rf1, rf2 = st.columns(2)
        with rf1: filtro_cat = st.multiselect("Categoría", sorted(df_r["categoria"].unique()), key="fc_r")
        with rf2: filtro_met = st.multiselect("Método",    sorted(df_r["metodo_pago"].unique()), key="fm_r")
        df_f = df_r.copy()
        if filtro_cat: df_f = df_f[df_f["categoria"].isin(filtro_cat)]
        if filtro_met: df_f = df_f[df_f["metodo_pago"].isin(filtro_met)]
        st.markdown(f'<div class="jf-gasto-list">{_rows_gastos(df_f)}</div>', unsafe_allow_html=True)
        st.caption(f"Total: **${df_f['monto'].sum():,.0f} COP** · {len(df_f)} de {len(df_r)} transacciones")

        with st.expander("✏️ Editar un gasto"):
            opts_g = {
                f"#{int(r['id'])} — {r['categoria']} · {r['descripcion'] or '(sin desc)'} · ${r['monto']:,.0f}": int(r['id'])
                for _, r in df_r.iterrows()
            }
            sel_g = st.selectbox("Selecciona el gasto", list(opts_g.keys()), key="sel_eg")
            fg = df_r[df_r["id"] == opts_g[sel_g]].iloc[0]
            gg1, gg2 = st.columns(2)
            with gg1:
                new_desc = st.text_input("Descripción", value=fg["descripcion"], key="eg_desc")
                new_nota = st.text_input("Nota",         value=fg.get("nota", ""), key="eg_nota")
                new_mont = st.number_input("Monto", value=float(fg.get("monto", 0)), step=1000.0, format="%.0f", key="eg_monto")
                new_fech = st.date_input("Fecha", value=date.fromisoformat(str(fg.get("fecha", str(date.today())))), key="eg_fecha")
            with gg2:
                new_cat = st.selectbox("Categoría", CATEGORIAS,
                                        index=CATEGORIAS.index(fg["categoria"]) if fg["categoria"] in CATEGORIAS else 0,
                                        key="eg_cat")
                new_met = st.radio("Método", METODOS_PAGO,
                                    index=METODOS_PAGO.index(fg["metodo_pago"]) if fg["metodo_pago"] in METODOS_PAGO else 0,
                                    key="eg_met")
            if st.button("Guardar cambios", key="btn_eg", type="primary"):
                editar_gasto(opts_g[sel_g], new_fech, new_desc or "", new_cat, new_mont, new_met or "", new_nota or "")
                _invalidar(); st.success("Gasto actualizado."); st.rerun()

        with st.expander("🗑️ Eliminar un gasto"):
            opts_dg = {
                f"#{int(r['id'])} — {r['categoria']} · {r['descripcion'] or '(sin desc)'} · ${r['monto']:,.0f}": int(r['id'])
                for _, r in df_r.iterrows()
            }
            sel_dg = st.selectbox("Selecciona el gasto a eliminar", list(opts_dg.keys()), key="sel_del_g")
            if _confirmar_eliminar("gasto") and st.button("Eliminar", type="secondary", key="btn_del_g"):
                eliminar_gasto(opts_dg[sel_dg]); _invalidar()
                st.success("Gasto eliminado."); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TARJETAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_tc:
    _h_nu   = _tc_hist("TC Nubank");    _h_bc   = _tc_hist("TC Bancolombia")
    _p_nu   = _tc_pag("TC Nubank");     _p_bc   = _tc_pag("TC Bancolombia")
    _pnd_nu = max(_h_nu - _p_nu, 0);    _pnd_bc = max(_h_bc - _p_bc, 0)
    _pnd_tot= _pnd_nu + _pnd_bc

    banner_c = "linear-gradient(135deg,#059669,#10B981)" if _pnd_tot==0 else "linear-gradient(135deg,#0A0E1A,#1E1B4B)"
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

    st.markdown('<div class="jf-section">Estado por tarjeta</div>', unsafe_allow_html=True)
    h1, h2, h3 = st.columns([2,2,1])
    with h1: st.markdown(_tc_hero_html("TC Nubank",      _pnd_nu, _h_nu, _p_nu), unsafe_allow_html=True)
    with h2: st.markdown(_tc_hero_html("TC Bancolombia", _pnd_bc, _h_bc, _p_bc), unsafe_allow_html=True)
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

    st.markdown('<div class="jf-section">Registrar pago de extracto</div>', unsafe_allow_html=True)
    st.caption("El pago del extracto salda la deuda acumulada y afecta el balance del mes — sin crear gasto duplicado.")
    with st.form("form_pago_tc", clear_on_submit=True):
        pt1, pt2, pt3 = st.columns(3)
        with pt1: tarjeta_tc = st.radio("Tarjeta", ["TC Nubank","TC Bancolombia"])
        with pt2: monto_tc   = st.number_input("Monto (COP)", min_value=0, max_value=20_000_000, value=0, step=10_000, format="%d")
        with pt3: fecha_tc   = st.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
        concepto_tc = st.text_input("Concepto (opcional)", placeholder="Ej: Pago extracto mayo Nubank")
        if st.form_submit_button("Registrar pago", type="primary", use_container_width=True):
            if monto_tc <= 0: st.error("El monto debe ser mayor a $0.")
            else:
                insertar_pago_tc(fecha_tc, tarjeta_tc, monto_tc, concepto_tc)
                _invalidar(); st.success(f"Pago de **${monto_tc:,.0f}** a {tarjeta_tc} registrado."); st.rerun()

    st.markdown('<div class="jf-section">Historial de pagos</div>', unsafe_allow_html=True)
    df_ptc = _pagos_tc()
    if df_ptc.empty:
        st.info("Aún no hay pagos registrados.")
    else:
        _TC_CLR = {"TC Nubank":("#FCE7F3","#9D174D"),"TC Bancolombia":("#FEF3C7","#92400E")}
        rows_tc = ""
        for _, row in df_ptc.iterrows():
            tbg, tc_ = _TC_CLR.get(row["tarjeta"], ("#F1F5F9","#64748B"))
            conc_tc = row["concepto"] if row["concepto"] else "Pago de extracto"
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
            if _confirmar_eliminar("tc") and st.button("Eliminar", type="secondary", key="btn_del_ptc"):
                if id_dtc in df_ptc["id"].tolist():
                    eliminar_pago_tc(int(id_dtc)); _invalidar()
                    st.success(f"Pago #{id_dtc} eliminado."); st.rerun()
                else: st.error(f"ID {id_dtc} no existe.")


# ══════════════════════════════════════════════════════════════════════════════
#  AHORRO
# ══════════════════════════════════════════════════════════════════════════════
with tab_ahorro:
    saldo_a  = _saldo_ahorro()
    faltante = max(META_FONDO - saldo_a, 0)
    pct_a    = min(saldo_a / META_FONDO, 1.0) if META_FONDO > 0 else 0
    meses_r  = proyeccion_fondo(saldo_a, META_AHORRO, META_FONDO)

    try:
        from dateutil.relativedelta import relativedelta
        prox_fecha = (hoy + relativedelta(months=meses_r)).strftime("%b %Y") if meses_r > 0 else "—"
    except Exception:
        prox_fecha = f"~{meses_r}m" if meses_r > 0 else "—"

    color_fondo = "#10B981" if pct_a >= 1.0 else ("#6366F1" if pct_a >= 0.5 else "#8B5CF6")
    estado_fondo= "Completado ✓" if pct_a >= 1.0 else ("Muy cerca" if pct_a >= 0.75 else "En progreso")

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
            tipo_a = st.radio("Tipo *", ["ingreso","retiro"],
                              format_func=lambda x: "Ingreso (ahorro)" if x=="ingreso" else "Retiro")
            if tipo_a == "retiro": st.warning("Solo en emergencia real.")
        if st.form_submit_button("Registrar", use_container_width=True, type="primary"):
            if monto_a <= 0: st.error("El monto debe ser mayor a $0.")
            elif not concepto_a.strip(): st.error("Escribe un concepto.")
            else:
                insertar_movimiento_ahorro(fecha_a, concepto_a, monto_a, tipo_a)
                _invalidar(); st.success(f"{'Ahorro' if tipo_a=='ingreso' else 'Retiro'} de **${monto_a:,.0f}** registrado."); st.rerun()

    st.markdown('<div class="jf-section">Historial de movimientos</div>', unsafe_allow_html=True)
    df_mov = _movs_ahorro()
    if df_mov.empty:
        st.info("Sin movimientos registrados.")
    else:
        ti = float(df_mov[df_mov["tipo"]=="ingreso"]["monto"].sum())
        tr = float(df_mov[df_mov["tipo"]=="retiro"]["monto"].sum())
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


# ══════════════════════════════════════════════════════════════════════════════
#  ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analisis:
    anio_sel, mes_sel = _selector_mes("anal")
    mes_ant  = mes_sel - 1 if mes_sel > 1 else 12
    anio_ant = anio_sel     if mes_sel > 1 else anio_sel - 1

    df_cat_act = gasto_por_categoria_mes(anio_sel, mes_sel)
    df_cat_ant = gasto_por_categoria_mes(anio_ant, mes_ant)
    df_met_act = gasto_por_metodo_mes(anio_sel, mes_sel)
    total_act  = gasto_total_mes(anio_sel, mes_sel)
    total_ant  = gasto_total_mes(anio_ant, mes_ant)
    ing_sel    = total_ingresos_mes(anio_sel, mes_sel)
    pct_lim    = total_act / LIMITE_GASTOS if LIMITE_GASTOS > 0 else 0
    dif_meses  = total_act - total_ant

    banner_c = "#10B981" if dif_meses <= 0 else "#F43F5E"
    dif_txt  = (f"−${abs(dif_meses):,.0f} menos que {MESES_ES[mes_ant]}"
                if dif_meses <= 0 else f"+${abs(dif_meses):,.0f} más que {MESES_ES[mes_ant]}")
    st.markdown(f"""
<div class="jf-anal-banner">
  <div class="jf-anal-banner-item">
    <div class="jf-anal-banner-val">${total_act:,.0f}</div>
    <div class="jf-anal-banner-lbl">Gasto total · {MESES_ES[mes_sel]}</div>
  </div>
  <div class="jf-anal-banner-divider"></div>
  <div class="jf-anal-banner-item">
    <div class="jf-anal-banner-val">${ing_sel:,.0f}</div>
    <div class="jf-anal-banner-lbl">Ingresos registrados</div>
  </div>
  <div class="jf-anal-banner-divider"></div>
  <div class="jf-anal-banner-item">
    <div class="jf-anal-banner-val" style="color:{banner_c};">{dif_txt}</div>
    <div class="jf-anal-banner-lbl">vs {MESES_ES[mes_ant]} {anio_ant}</div>
  </div>
  <div class="jf-anal-banner-divider"></div>
  <div class="jf-anal-banner-item">
    <div class="jf-anal-banner-val" style="color:{'#EF4444' if pct_lim>1 else '#6366F1'};">{pct_lim:.0%}</div>
    <div class="jf-anal-banner-lbl">del límite mensual</div>
  </div>
</div>""", unsafe_allow_html=True)

    if not df_cat_act.empty:
        row_d = df_cat_act[df_cat_act["categoria"]=="Deseos"]
        if not row_d.empty:
            gd = row_d["monto"].values[0]
            if gd / META_DESARROLLO >= 0.70:
                st.warning(f"**Deseos** lleva ${gd:,.0f} — {gd/META_DESARROLLO:.0%} del límite (${META_DESARROLLO:,.0f}).")

    # Gráfica comparativa + pie
    st.markdown('<div class="jf-section">Distribución por categoría</div>', unsafe_allow_html=True)
    ga, gb = st.columns([3,1])
    with ga:
        if df_cat_act.empty and df_cat_ant.empty:
            st.info("Sin datos para este período.")
        else:
            cats = sorted((set(df_cat_act["categoria"].tolist()) | set(df_cat_ant["categoria"].tolist())),
                          key=lambda c: CATEGORIAS.index(c) if c in CATEGORIAS else 99)
            def _m(df, c): return df[df["categoria"]==c]["monto"].values[0] if not df[df["categoria"]==c].empty else 0
            fig = go.Figure()
            fig.add_trace(go.Bar(name=MESES_ES[mes_sel], x=cats, y=[_m(df_cat_act,c) for c in cats],
                marker_color="#6366F1", marker_line_width=0,
                text=[f"${_m(df_cat_act,c):,.0f}" if _m(df_cat_act,c)>0 else "" for c in cats],
                textposition="outside", textfont=dict(size=9,color="#94A3B8")))
            fig.add_trace(go.Bar(name=MESES_ES[mes_ant], x=cats, y=[_m(df_cat_ant,c) for c in cats],
                marker_color="#C7D2FE", marker_line_width=0,
                text=[f"${_m(df_cat_ant,c):,.0f}" if _m(df_cat_ant,c)>0 else "" for c in cats],
                textposition="outside", textfont=dict(size=9,color="#94A3B8")))
            fig.update_layout(barmode="group", height=320,
                margin=dict(t=30,b=10,l=0,r=0),
                yaxis=dict(tickprefix="$",tickformat=",.0f",gridcolor="#F0F4FF",color="#CBD5E1",showgrid=True,zeroline=False),
                xaxis=dict(tickangle=-30,color="#CBD5E1",showgrid=False),
                legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0,font=dict(color="#94A3B8",size=11)),
                plot_bgcolor="#FFFFFF",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11,color="#94A3B8"),bargap=0.25,bargroupgap=0.08)
            st.plotly_chart(fig, use_container_width=True, key="anal_bar")
    with gb:
        if not df_met_act.empty:
            fig_pie = go.Figure(go.Pie(
                labels=df_met_act["metodo_pago"], values=df_met_act["monto"], hole=0.55,
                marker=dict(colors=["#6366F1","#EC4899","#F59E0B"],line=dict(color="#F0F4FF",width=3)),
                textinfo="label+percent", textfont=dict(size=10,color="#374151"),
                insidetextorientation="radial"))
            fig_pie.update_layout(height=320,margin=dict(t=10,b=10,l=0,r=0),
                showlegend=False,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True, key="anal_pie")

    # Tendencia 6 meses
    st.markdown('<div class="jf-section">Tendencia 6 meses</div>', unsafe_allow_html=True)
    df_gt2 = _gastos_trend(7); df_it2 = _ingresos_trend(7)
    if df_gt2.empty: st.info("Aún no hay datos históricos suficientes.")
    else: st.plotly_chart(_trend_chart(df_gt2, df_it2), use_container_width=True, key="anal_trend")

    # Top categorías ranking
    if not df_cat_act.empty:
        st.markdown('<div class="jf-section">Top categorías</div>', unsafe_allow_html=True)
        max_cat = df_cat_act["monto"].max()
        rank_html = ""
        for i, (_, row) in enumerate(df_cat_act.head(6).iterrows()):
            pct_b = (row["monto"] / max_cat * 100) if max_cat > 0 else 0
            rank_html += f"""
<div class="jf-rank-row">
  <div class="jf-rank-num">#{i+1}</div>
  <div class="jf-rank-icon">{CAT_ICON.get(row['categoria'],'📦')}</div>
  <div class="jf-rank-info">
    <div class="jf-rank-name">{row['categoria']}</div>
    <div class="jf-rank-bar-bg"><div class="jf-rank-bar" style="width:{pct_b:.1f}%;background:{BAR_COLORS[i%6]};"></div></div>
  </div>
  <div class="jf-rank-monto">${row['monto']:,.0f}</div>
</div>"""
        st.markdown(f'<div class="jf-rank-list">{rank_html}</div>', unsafe_allow_html=True)

    # Transacciones
    st.markdown('<div class="jf-section">Transacciones</div>', unsafe_allow_html=True)
    df_raw = obtener_gastos_mes(anio_sel, mes_sel)
    if df_raw.empty: st.info("Sin transacciones en este período.")
    else:
        st.markdown(f'<div class="jf-gasto-list">{_rows_gastos(df_raw)}</div>', unsafe_allow_html=True)
        csv = df_raw.to_csv(index=False).encode("utf-8")
        st.download_button("Exportar CSV", csv,
            file_name=f"gastos_{anio_sel}_{mes_sel:02d}.csv", mime="text/csv")


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
with tab_config:
    cfg_actual = get_config()
    st.markdown(f"""
<div class="jf-balance-card">
  <div class="jf-balance-left">
    <div class="jf-balance-label">⚙️ Configuración personal</div>
    <div class="jf-balance-value" style="font-size:1.4rem;">Ajusta tu base mensual</div>
    <div class="jf-balance-sub">Los cambios se aplican a todos los cálculos del dashboard al instante.</div>
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
            st.markdown("**Regla 80 / 10 / 20**")
            new_gastos_pct = st.slider("% máximo en gastos", 50, 95,
                                       int(cfg_actual["limite_gastos_pct"]*100), 5,
                                       help="Porcentaje del ingreso destinado a gastos")
            new_ahorro_pct = st.slider("% destinado a ahorro", 5, 40,
                                       int(cfg_actual["meta_ahorro_pct"]*100), 5)
            new_dev_pct    = st.slider("% para desarrollo/inversión", 5, 40,
                                       int(cfg_actual["meta_desarrollo_pct"]*100), 5)
            total_pct = new_gastos_pct + new_ahorro_pct + new_dev_pct
            if total_pct != 100:
                st.warning(f"Los porcentajes suman {total_pct}% (deben ser 100%)")

            st.markdown("**Preview con nuevo ingreso:**")
            st.caption(f"Gastos: ${new_ingreso * new_gastos_pct/100:,.0f}")
            st.caption(f"Ahorro: ${new_ingreso * new_ahorro_pct/100:,.0f}")
            st.caption(f"Desarrollo: ${new_ingreso * new_dev_pct/100:,.0f}")

        if st.form_submit_button("Guardar configuración", type="primary", use_container_width=True):
            if total_pct != 100:
                st.error("Los porcentajes deben sumar 100%.")
            else:
                set_config("ingreso_neto",        float(new_ingreso))
                set_config("meta_fondo",           float(new_fondo))
                set_config("limite_gastos_pct",    new_gastos_pct / 100)
                set_config("meta_ahorro_pct",      new_ahorro_pct / 100)
                set_config("meta_desarrollo_pct",  new_dev_pct / 100)
                _cfg.clear()
                _invalidar()
                st.success("Configuración guardada. Recargando...")
                st.rerun()

    st.markdown('<div class="jf-section">Resumen actual</div>', unsafe_allow_html=True)
    d = get_derived(cfg_actual)
    r1, r2, r3, r4 = st.columns(4)
    with r1: st.metric("Ingreso base", f"${d['INGRESO_NETO']:,.0f}")
    with r2: st.metric("Límite gastos 80%", f"${d['LIMITE_GASTOS']:,.0f}")
    with r3: st.metric("Meta ahorro 10%",   f"${d['META_AHORRO']:,.0f}")
    with r4: st.metric("Meta desarrollo",   f"${d['META_DESARROLLO']:,.0f}")
