"""Shared cache functions, UI helpers and constants for Jean Finance OS."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from database import (
    get_derived,
    obtener_gastos_mes, obtener_ingresos_mes, obtener_saldo_ahorro,
    obtener_pagos_tc, obtener_movimientos_ahorro,
    gastos_ultimos_meses, ingresos_ultimos_meses,
    total_gastos_tc_historico, total_pagado_tc, total_pagado_tc_mes,
    get_fijos_pagados_mes,
    obtener_saldo_bolsillo, obtener_movimientos_bolsillo, neto_bolsillo_mes,
    CATEGORIAS,
)

# ─── Constantes UI ────────────────────────────────────────────────────────────
CAT_ICON: dict[str, str] = {
    "Alimentación": "🛒", "Transporte": "🚗", "Vivienda": "🏠",
    "Servicios": "⚡", "Suscripción": "📱", "Salud": "💊",
    "Educación/Certs": "📚", "Deseos": "🎯", "Ropa": "👕",
    "Varios": "📦", "Tarjeta": "💳",
}
MET_COLOR: dict[str, tuple[str, str]] = {
    "TD Bancolombia": ("#DBEAFE", "#2563EB"),
    "TC Nubank":      ("#FCE7F3", "#9D174D"),
    "TC Bancolombia": ("#FEF3C7", "#92400E"),
}
TIPO_ICON: dict[str, str] = {
    "Quincenal 1": "💵", "Quincenal 2": "💵", "Bono": "🎁",
    "Prima": "⭐", "Extra": "✨", "Comisión": "📊", "Otros": "💰",
}
GASTOS_FIJOS = [
    ("Alimentación", "Mercado"),   ("Salud", "Gimnasio"),
    ("Servicios", "Peluquería"),   ("Servicios", "Celular"),
    ("Suscripción", "Apple"),      ("Suscripción", "IA"),
    ("Tarjeta", "Cuota Tarjeta"),  ("Transporte", "Gasolina"),
    ("Servicios", "EPM"),          ("Servicios", "Internet"),
    ("Vivienda", "Arriendo"),
]
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}
BAR_COLORS = ["#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#3B82F6"]

# ─── Config cacheada ──────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def cfg_derived() -> dict[str, float]:
    return get_derived()

# ─── Queries cacheadas ────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def q_gastos_mes(a: int, m: int):     return obtener_gastos_mes(a, m)

@st.cache_data(ttl=30)
def q_ingresos_mes(a: int, m: int):   return obtener_ingresos_mes(a, m)

@st.cache_data(ttl=30)
def q_saldo_ahorro():                  return obtener_saldo_ahorro()

@st.cache_data(ttl=30)
def q_pagos_tc():                      return obtener_pagos_tc()

@st.cache_data(ttl=30)
def q_movs_ahorro():                   return obtener_movimientos_ahorro()

@st.cache_data(ttl=60)
def q_gastos_trend(n: int = 7):        return gastos_ultimos_meses(n)

@st.cache_data(ttl=60)
def q_ingresos_trend(n: int = 7):      return ingresos_ultimos_meses(n)

@st.cache_data(ttl=30)
def q_tc_hist(tarjeta: str):           return total_gastos_tc_historico(tarjeta)

@st.cache_data(ttl=30)
def q_tc_pag(tarjeta: str):            return total_pagado_tc(tarjeta)

@st.cache_data(ttl=30)
def q_tc_pag_mes(a: int, m: int):      return total_pagado_tc_mes(a, m)

@st.cache_data(ttl=30)
def q_fijos_set(a: int, m: int):       return get_fijos_pagados_mes(a, m)

@st.cache_data(ttl=30)
def q_saldo_bolsillo():                return obtener_saldo_bolsillo()

@st.cache_data(ttl=30)
def q_movs_bolsillo():                 return obtener_movimientos_bolsillo()

@st.cache_data(ttl=30)
def q_neto_bolsillo_mes(a: int, m: int): return neto_bolsillo_mes(a, m)


def invalidar():
    """Limpia todas las caches tras mutaciones."""
    q_gastos_mes.clear();     q_ingresos_mes.clear();  q_saldo_ahorro.clear()
    q_pagos_tc.clear();       q_movs_ahorro.clear();   q_gastos_trend.clear()
    q_ingresos_trend.clear(); q_tc_hist.clear();        q_tc_pag.clear()
    q_tc_pag_mes.clear();     q_fijos_set.clear();      cfg_derived.clear()
    q_saldo_bolsillo.clear(); q_movs_bolsillo.clear();  q_neto_bolsillo_mes.clear()


# ─── Helpers UI ───────────────────────────────────────────────────────────────
def load_css():
    css = (Path(__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def selector_mes(key: str) -> tuple[int, int]:
    hoy = date.today()
    anos = list(range(2024, hoy.year + 3))
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        a = st.selectbox("Año", anos, index=anos.index(hoy.year), key=f"{key}_a")
    with c2:
        m = st.selectbox("Mes", range(1, 13), format_func=lambda x: MESES_ES[x],
                         index=hoy.month - 1, key=f"{key}_m")
    return a, m


def confirmar_eliminar(key: str) -> bool:
    st.caption("⚠️ Esta acción no se puede deshacer.")
    return st.checkbox("Confirmo que quiero eliminar este registro", key=f"conf_{key}")


def rows_gastos(df: pd.DataFrame, limit: int | None = None) -> str:
    rows = ""
    iterable = df.head(limit).iterrows() if limit else df.iterrows()
    for _, row in iterable:
        icon = CAT_ICON.get(row["categoria"], "📦")
        mbg, mc = MET_COLOR.get(row["metodo_pago"], ("#F1F5F9", "#64748B"))
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


def tc_card_html(nombre: str, pendiente: float, gastado: float, pagado: float) -> str:
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
  <div class="jf-tc-detail">Gastado <strong>${gastado:,.0f}</strong> · Pagado <strong>${pagado:,.0f}</strong> · {pct:.0f}% saldado</div>
</div>"""


def tc_hero_html(nombre: str, pendiente: float, gastado: float, pagado: float) -> str:
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


def budget_card_html(titulo: str, regla: str, valor: float, meta: float,
                     pct: float, bar_c: str, st_c: str, st_bg: str,
                     st_txt: str, icon: str) -> str:
    pct_bar = min(pct * 100, 100)
    resto   = max(meta - valor, 0)
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


def trend_chart(df_g: pd.DataFrame, df_i: pd.DataFrame) -> go.Figure:
    df_g = df_g.sort_values("periodo")
    df_i = df_i.sort_values("periodo") if not df_i.empty else df_i
    fig  = go.Figure()
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
        height=240, margin=dict(t=10, b=10, l=0, r=0),
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#F0F4FF",
                   color="#CBD5E1", showgrid=True, zeroline=False),
        xaxis=dict(color="#CBD5E1", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color="#94A3B8", size=11)),
        plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#94A3B8"))
    return fig
