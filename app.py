import streamlit as st
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from database import init_db
from utils import load_css, cfg_derived, MESES_ES

st.set_page_config(
    page_title="Jean Finance OS",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
load_css()

# ── Datos sidebar ─────────────────────────────────────────────────────────────
CFG          = cfg_derived()
INGRESO_NETO = CFG["INGRESO_NETO"]
quincenal    = INGRESO_NETO / 2
hoy          = date.today()
mes_label    = MESES_ES[hoy.month]

with st.sidebar:
    st.markdown(f"""
<div style="padding:18px 2px 14px;">

  <!-- Logo / brand -->
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
    <div style="width:38px;height:38px;border-radius:10px;
                background:linear-gradient(135deg,#6366F1,#8B5CF6);
                display:flex;align-items:center;justify-content:center;
                font-size:1.2rem;flex-shrink:0;">💰</div>
    <div>
      <div style="font-size:1.1rem;font-weight:800;color:#0F172A;letter-spacing:-0.3px;line-height:1.1;">
        Jean Finance
      </div>
      <div style="font-size:0.68rem;color:#94A3B8;letter-spacing:.3px;">OS · Regla 80 · 10 · 10</div>
    </div>
  </div>

  <!-- Mes actual -->
  <div style="font-size:0.68rem;color:#94A3B8;font-weight:600;text-transform:uppercase;
              letter-spacing:.5px;margin-bottom:6px;">{mes_label} {hoy.year}</div>

  <!-- Card base mensual + quincenas -->
  <div style="background:#F8FAFF;border:1.5px solid #E0E7FF;border-radius:12px;overflow:hidden;margin-bottom:6px;">
    <div style="padding:10px 14px;border-bottom:1px solid #E8EDFF;">
      <div style="font-size:0.63rem;color:#6366F1;font-weight:700;text-transform:uppercase;
                  letter-spacing:.6px;margin-bottom:2px;">Base mensual</div>
      <div style="font-size:1.25rem;font-weight:800;color:#1E1B4B;letter-spacing:-.3px;">
        ${INGRESO_NETO:,.0f}
        <span style="font-size:0.65rem;font-weight:500;color:#94A3B8;margin-left:3px;">COP</span>
      </div>
    </div>
    <div style="display:flex;">
      <div style="flex:1;padding:8px 14px;border-right:1px solid #E8EDFF;">
        <div style="font-size:0.6rem;color:#94A3B8;font-weight:600;text-transform:uppercase;
                    letter-spacing:.4px;margin-bottom:2px;">Quincena 1</div>
        <div style="font-size:1rem;font-weight:700;color:#4F46E5;">${quincenal:,.0f}</div>
      </div>
      <div style="flex:1;padding:8px 14px;">
        <div style="font-size:0.6rem;color:#94A3B8;font-weight:600;text-transform:uppercase;
                    letter-spacing:.4px;margin-bottom:2px;">Quincena 2</div>
        <div style="font-size:1rem;font-weight:700;color:#4F46E5;">${quincenal:,.0f}</div>
      </div>
    </div>
  </div>

  <!-- Regla visual 80/10/10 -->
  <div style="margin-top:8px;">
    <div style="font-size:0.6rem;color:#94A3B8;font-weight:600;text-transform:uppercase;
                letter-spacing:.5px;margin-bottom:5px;">Distribución objetivo</div>
    <div style="display:flex;height:6px;border-radius:4px;overflow:hidden;gap:2px;">
      <div style="flex:80;background:#6366F1;border-radius:4px 0 0 4px;"></div>
      <div style="flex:10;background:#10B981;"></div>
      <div style="flex:10;background:#F59E0B;border-radius:0 4px 4px 0;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:5px;">
      <span style="font-size:0.6rem;color:#6366F1;font-weight:600;">80% Gastos</span>
      <span style="font-size:0.6rem;color:#10B981;font-weight:600;">10% Ahorro</span>
      <span style="font-size:0.6rem;color:#F59E0B;font-weight:600;">10% Desarrollo</span>
    </div>
  </div>

</div>
<div style="border-top:1px solid #F1F5F9;margin:0 -4px;"></div>
""", unsafe_allow_html=True)

# ── Navegación ────────────────────────────────────────────────────────────────
pg = st.navigation(
    {
        "Principal": [
            st.Page("pages/dashboard.py",     title="Dashboard",     icon="📊"),
            st.Page("pages/ingresos.py",       title="Ingresos",      icon="💵"),
            st.Page("pages/registro.py",       title="Registro",      icon="➕"),
        ],
        "Finanzas": [
            st.Page("pages/tarjetas.py",       title="Tarjetas",      icon="💳"),
            st.Page("pages/ahorro.py",          title="Ahorro",        icon="🏦"),
            st.Page("pages/analisis.py",        title="Análisis",      icon="📈"),
        ],
        "Sistema": [
            st.Page("pages/configuracion.py",  title="Configuración", icon="⚙️"),
        ],
    }
)
pg.run()
