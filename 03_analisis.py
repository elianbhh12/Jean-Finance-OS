import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import (
    init_db, obtener_gastos_mes, gasto_por_categoria_mes,
    gasto_por_metodo_mes, gasto_total_mes,
    CATEGORIAS, METODOS_PAGO, LIMITE_GASTOS, META_DESARROLLO
)

st.set_page_config(page_title="Análisis — Jean Finance OS", page_icon="📊", layout="wide")
init_db()

st.markdown("## Análisis mensual")
st.divider()

# ─── SELECTOR DE MES ──────────────────────────────────────────────────────────
hoy = date.today()
col_s1, col_s2, _ = st.columns([1, 1, 2])
with col_s1:
    anio_sel = st.selectbox("Año", options=[2024, 2025, 2026, 2027], index=2)
with col_s2:
    mes_sel = st.selectbox(
        "Mes", options=list(range(1, 13)),
        format_func=lambda m: date(2000, m, 1).strftime("%B"),
        index=hoy.month - 1
    )

mes_ant = mes_sel - 1 if mes_sel > 1 else 12
anio_ant = anio_sel if mes_sel > 1 else anio_sel - 1

st.divider()

# ─── DATOS ────────────────────────────────────────────────────────────────────
df_cat_actual = gasto_por_categoria_mes(anio_sel, mes_sel)
df_cat_anterior = gasto_por_categoria_mes(anio_ant, mes_ant)
df_metodo = gasto_por_metodo_mes(anio_sel, mes_sel)
total_actual = gasto_total_mes(anio_sel, mes_sel)
total_anterior = gasto_total_mes(anio_ant, mes_ant)

# ─── ALERTA DE CATEGORÍAS ─────────────────────────────────────────────────────
if not df_cat_actual.empty:
    limite_cat_deseos = META_DESARROLLO
    deseos_row = df_cat_actual[df_cat_actual["categoria"] == "Deseos"]
    if not deseos_row.empty:
        gasto_deseos = deseos_row["monto"].values[0]
        pct_deseos = gasto_deseos / limite_cat_deseos if limite_cat_deseos > 0 else 0
        if pct_deseos >= 0.70:
            st.warning(
                f"⚠️ Deseos lleva **${gasto_deseos:,.0f}** — {pct_deseos:.0%} del límite sugerido "
                f"(${limite_cat_deseos:,.0f}). Revisa antes de fin de mes."
            )

# ─── COMPARATIVO GENERAL ──────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    delta_total = total_actual - total_anterior
    st.metric(
        f"Gasto total — mes sel.",
        f"${total_actual:,.0f}",
        delta=f"${abs(delta_total):,.0f} {'más' if delta_total > 0 else 'menos'} que mes anterior",
        delta_color="inverse"
    )
with col2:
    st.metric("Mes anterior", f"${total_anterior:,.0f}", delta_color="off")
with col3:
    pct_limite = total_actual / LIMITE_GASTOS if LIMITE_GASTOS > 0 else 0
    st.metric("% del límite 70%", f"{pct_limite:.0%}", delta=f"Límite: ${LIMITE_GASTOS:,.0f}", delta_color="off")

st.divider()

# ─── GRÁFICA POR CATEGORÍA ────────────────────────────────────────────────────
st.markdown("#### Gasto por categoría — mes actual vs anterior")

if df_cat_actual.empty and df_cat_anterior.empty:
    st.info("Sin datos para mostrar en este período.")
else:
    todas_cats = list(dict.fromkeys(
        list(df_cat_actual["categoria"]) + list(df_cat_anterior["categoria"]) + CATEGORIAS
    ))

    montos_actual = []
    montos_anterior = []
    for cat in todas_cats:
        row_a = df_cat_actual[df_cat_actual["categoria"] == cat]
        row_p = df_cat_anterior[df_cat_anterior["categoria"] == cat]
        montos_actual.append(row_a["monto"].values[0] if not row_a.empty else 0)
        montos_anterior.append(row_p["monto"].values[0] if not row_p.empty else 0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"Mes actual",
        x=todas_cats,
        y=montos_actual,
        marker_color="#378ADD",
        text=[f"${v:,.0f}" if v > 0 else "" for v in montos_actual],
        textposition="outside",
        textfont=dict(size=10)
    ))
    fig.add_trace(go.Bar(
        name=f"Mes anterior",
        x=todas_cats,
        y=montos_anterior,
        marker_color="#B5D4F4",
        text=[f"${v:,.0f}" if v > 0 else "" for v in montos_anterior],
        textposition="outside",
        textfont=dict(size=10)
    ))
    fig.update_layout(
        barmode="group",
        height=380,
        margin=dict(t=20, b=20, l=0, r=0),
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        xaxis=dict(tickangle=-30)
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ─── DESGLOSE POR MÉTODO DE PAGO ──────────────────────────────────────────────
st.markdown("#### Gasto por método de pago")

if df_metodo.empty:
    st.info("Sin datos de métodos de pago este mes.")
else:
    cols_m = st.columns(len(df_metodo))
    for i, (_, row) in enumerate(df_metodo.iterrows()):
        pct_m = row["monto"] / total_actual if total_actual > 0 else 0
        with cols_m[i]:
            st.metric(row["metodo_pago"], f"${row['monto']:,.0f}", delta=f"{pct_m:.0%} del total", delta_color="off")

    fig_pie = go.Figure(go.Pie(
        labels=df_metodo["metodo_pago"],
        values=df_metodo["monto"],
        hole=0.5,
        marker_colors=["#378ADD", "#7F77DD", "#1D9E75"],
        textinfo="label+percent",
        textfont=dict(size=12)
    ))
    fig_pie.update_layout(
        height=280,
        margin=dict(t=10, b=10, l=0, r=0),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ─── TABLA DETALLE ────────────────────────────────────────────────────────────
st.markdown("#### Detalle de transacciones")
df_raw = obtener_gastos_mes(anio_sel, mes_sel)

if df_raw.empty:
    st.info("Sin transacciones en este período.")
else:
    df_raw["monto_fmt"] = df_raw["monto"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(
        df_raw.rename(columns={
            "fecha": "Fecha", "descripcion": "Descripción",
            "categoria": "Categoría", "monto_fmt": "Monto",
            "metodo_pago": "Método de pago"
        })[["Fecha", "Descripción", "Categoría", "Monto", "Método de pago"]],
        use_container_width=True,
        hide_index=True
    )

    csv = df_raw.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Exportar CSV",
        data=csv,
        file_name=f"gastos_{anio_sel}_{mes_sel:02d}.csv",
        mime="text/csv"
    )
