import streamlit as st
import plotly.graph_objects as go
from utils import (
    cfg_derived, q_gastos_trend, q_ingresos_trend,
    selector_mes, rows_gastos, trend_chart,
    MESES_ES, CATEGORIAS, CAT_ICON, BAR_COLORS,
)
from database import (
    gasto_por_categoria_mes, gasto_por_metodo_mes,
    gasto_total_mes, total_ingresos_mes, obtener_gastos_mes,
)

CFG          = cfg_derived()
LIMITE_GASTOS = CFG["LIMITE_GASTOS"]

anio_sel, mes_sel = selector_mes("anal")
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
    row_d = df_cat_act[df_cat_act["categoria"] == "Deseos"]
    if not row_d.empty:
        gd = row_d["monto"].values[0]
        pct_deseos = gd / LIMITE_GASTOS if LIMITE_GASTOS > 0 else 0
        if pct_deseos >= 0.20:
            st.error(f"🎯 **Deseos** lleva **${gd:,.0f}** — {pct_deseos:.0%} de tus gastos totales. Considera reducir.")
        elif pct_deseos >= 0.10:
            st.warning(f"🎯 **Deseos** lleva **${gd:,.0f}** — {pct_deseos:.0%} de tus gastos totales.")

# ── Gráfica + pie ─────────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Distribución por categoría</div>', unsafe_allow_html=True)
ga, gb = st.columns([3, 1])
with ga:
    if df_cat_act.empty and df_cat_ant.empty:
        st.info("Sin datos para este período.")
    else:
        cats = sorted(
            set(df_cat_act["categoria"].tolist()) | set(df_cat_ant["categoria"].tolist()),
            key=lambda c: CATEGORIAS.index(c) if c in CATEGORIAS else 99,
        )
        def _m(df, c): return df[df["categoria"] == c]["monto"].values[0] if not df[df["categoria"] == c].empty else 0
        fig = go.Figure()
        fig.add_trace(go.Bar(name=MESES_ES[mes_sel], x=cats, y=[_m(df_cat_act, c) for c in cats],
            marker_color="#6366F1", marker_line_width=0,
            text=[f"${_m(df_cat_act,c):,.0f}" if _m(df_cat_act, c) > 0 else "" for c in cats],
            textposition="outside", textfont=dict(size=9, color="#94A3B8")))
        fig.add_trace(go.Bar(name=MESES_ES[mes_ant], x=cats, y=[_m(df_cat_ant, c) for c in cats],
            marker_color="#C7D2FE", marker_line_width=0,
            text=[f"${_m(df_cat_ant,c):,.0f}" if _m(df_cat_ant, c) > 0 else "" for c in cats],
            textposition="outside", textfont=dict(size=9, color="#94A3B8")))
        fig.update_layout(
            barmode="group", height=320, margin=dict(t=30, b=10, l=0, r=0),
            yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#F0F4FF", color="#CBD5E1", showgrid=True, zeroline=False),
            xaxis=dict(tickangle=-30, color="#CBD5E1", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color="#94A3B8", size=11)),
            plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#94A3B8"), bargap=0.25, bargroupgap=0.08)
        st.plotly_chart(fig, width="stretch", key="anal_bar")
with gb:
    if not df_met_act.empty:
        fig_pie = go.Figure(go.Pie(
            labels=df_met_act["metodo_pago"], values=df_met_act["monto"], hole=0.55,
            marker=dict(colors=["#6366F1", "#EC4899", "#F59E0B"], line=dict(color="#F0F4FF", width=3)),
            textinfo="label+percent", textfont=dict(size=10, color="#374151"),
            insidetextorientation="radial"))
        fig_pie.update_layout(height=320, margin=dict(t=10, b=10, l=0, r=0),
            showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, width="stretch", key="anal_pie")

# ── Tendencia ─────────────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Tendencia 6 meses</div>', unsafe_allow_html=True)
df_gt2 = q_gastos_trend(7); df_it2 = q_ingresos_trend(7)
if df_gt2.empty:
    st.info("Aún no hay datos históricos suficientes.")
else:
    st.plotly_chart(trend_chart(df_gt2, df_it2), width="stretch", key="anal_trend")

# ── Top categorías ────────────────────────────────────────────────────────────
if not df_cat_act.empty:
    st.markdown('<div class="jf-section">Top categorías</div>', unsafe_allow_html=True)
    max_cat  = df_cat_act["monto"].max()
    rank_html = ""
    for i, (_, row) in enumerate(df_cat_act.head(6).iterrows()):
        pct_b = (row["monto"] / max_cat * 100) if max_cat > 0 else 0
        rank_html += f"""
<div class="jf-rank-row">
  <div class="jf-rank-num">#{i+1}</div>
  <div class="jf-rank-icon">{CAT_ICON.get(row['categoria'], '📦')}</div>
  <div class="jf-rank-info">
    <div class="jf-rank-name">{row['categoria']}</div>
    <div class="jf-rank-bar-bg"><div class="jf-rank-bar" style="width:{pct_b:.1f}%;background:{BAR_COLORS[i%6]};"></div></div>
  </div>
  <div class="jf-rank-monto">${row['monto']:,.0f}</div>
</div>"""
    st.markdown(f'<div class="jf-rank-list">{rank_html}</div>', unsafe_allow_html=True)

# ── Transacciones ─────────────────────────────────────────────────────────────
st.markdown('<div class="jf-section">Transacciones</div>', unsafe_allow_html=True)
df_raw = obtener_gastos_mes(anio_sel, mes_sel)
if df_raw.empty:
    st.info("Sin transacciones en este período.")
else:
    st.markdown(f'<div class="jf-gasto-list">{rows_gastos(df_raw)}</div>', unsafe_allow_html=True)
    csv = df_raw.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv,
                       file_name=f"gastos_{anio_sel}_{mes_sel:02d}.csv", mime="text/csv")
