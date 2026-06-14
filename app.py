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
CFG             = cfg_derived()
INGRESO_NETO    = CFG["INGRESO_NETO"]
META_AHORRO     = CFG["META_AHORRO"]
META_DESARROLLO = CFG["META_DESARROLLO"]
PCT_G           = int(CFG["PCT_GASTOS"])
PCT_A           = int(CFG["PCT_AHORRO"])
PCT_D           = int(CFG["PCT_DESARROLLO"])
quincenal       = INGRESO_NETO / 2
ahorro_q        = META_AHORRO / 2
desarrollo_q    = META_DESARROLLO / 2
gastos_q        = (INGRESO_NETO - META_AHORRO - META_DESARROLLO) / 2
hoy             = date.today()
mes_label       = MESES_ES[hoy.month]
regla_label     = f"{PCT_G} · {PCT_A} · {PCT_D}"

with st.sidebar:
    # ── Header: logo + mes + quincenas + regla 80/10/10 ──────────────────────
    st.markdown(f"""
<div style="padding:18px 2px 14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
    <div style="width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#6366F1,#8B5CF6);display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">💰</div>
    <div>
      <div style="font-size:1.1rem;font-weight:800;color:#0F172A;letter-spacing:-0.3px;line-height:1.1;">Jean Finance</div>
      <div style="font-size:0.68rem;color:#94A3B8;letter-spacing:.3px;">OS · Regla {regla_label}</div>
    </div>
  </div>
  <div style="font-size:0.68rem;color:#94A3B8;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">{mes_label} {hoy.year}</div>
  <div style="background:#F8FAFF;border:1.5px solid #E0E7FF;border-radius:12px;overflow:hidden;margin-bottom:6px;">
    <div style="padding:10px 14px;border-bottom:1px solid #E8EDFF;">
      <div style="font-size:0.63rem;color:#6366F1;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:2px;">Base mensual</div>
      <div style="font-size:1.25rem;font-weight:800;color:#1E1B4B;letter-spacing:-.3px;">&#36;{INGRESO_NETO:,.0f} <span style="font-size:0.65rem;font-weight:500;color:#94A3B8;">COP</span></div>
    </div>
    <div style="display:flex;">
      <div style="flex:1;padding:8px 14px;border-right:1px solid #E8EDFF;">
        <div style="font-size:0.6rem;color:#94A3B8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px;">Quincena 1</div>
        <div style="font-size:1rem;font-weight:700;color:#4F46E5;">&#36;{quincenal:,.0f}</div>
      </div>
      <div style="flex:1;padding:8px 14px;">
        <div style="font-size:0.6rem;color:#94A3B8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;margin-bottom:2px;">Quincena 2</div>
        <div style="font-size:1rem;font-weight:700;color:#4F46E5;">&#36;{quincenal:,.0f}</div>
      </div>
    </div>
  </div>
  <div style="margin-top:8px;">
    <div style="font-size:0.6rem;color:#94A3B8;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;">Distribución objetivo</div>
    <div style="display:flex;height:6px;border-radius:4px;overflow:hidden;gap:2px;">
      <div style="flex:{PCT_G};background:#6366F1;border-radius:4px 0 0 4px;"></div>
      <div style="flex:{PCT_A};background:#10B981;"></div>
      <div style="flex:{PCT_D};background:#F59E0B;border-radius:0 4px 4px 0;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:5px;">
      <span style="font-size:0.6rem;color:#6366F1;font-weight:600;">{PCT_G}% Gastos</span>
      <span style="font-size:0.6rem;color:#10B981;font-weight:600;">{PCT_A}% Ahorro</span>
      <span style="font-size:0.6rem;color:#F59E0B;font-weight:600;">{PCT_D}% Desarrollo</span>
    </div>
  </div>
</div>
<div style="border-top:1px solid #F1F5F9;margin:0 -4px;"></div>
""", unsafe_allow_html=True)

    # ── Recomendación de ahorro — call separado para evitar parsing issues ────
    st.markdown(
        f'<div style="margin:10px 2px 6px;background:linear-gradient(135deg,#F0FDF4,#ECFDF5);border:1.5px solid #A7F3D0;border-radius:12px;padding:12px 14px;">'
        f'<div style="font-size:0.6rem;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;">&#128161; Ahorro por quincena</div>'
        f'<div style="display:flex;gap:8px;margin-bottom:8px;">'
        f'<div style="flex:1;background:#fff;border:1px solid #D1FAE5;border-radius:9px;padding:8px 10px;text-align:center;">'
        f'<div style="font-size:0.58rem;font-weight:700;color:#10B981;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px;">Ahorro {PCT_A}%</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:#059669;letter-spacing:-.5px;">&#36;{ahorro_q:,.0f}</div>'
        f'</div>'
        f'<div style="flex:1;background:#fff;border:1px solid #FDE68A;border-radius:9px;padding:8px 10px;text-align:center;">'
        f'<div style="font-size:0.58rem;font-weight:700;color:#D97706;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px;">Desarrollo {PCT_D}%</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:#D97706;letter-spacing:-.5px;">&#36;{desarrollo_q:,.0f}</div>'
        f'</div>'
        f'</div>'
        f'<div style="background:#fff;border:1px solid #C7D2FE;border-radius:9px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;">'
        f'<div>'
        f'<div style="font-size:0.58rem;font-weight:700;color:#6366F1;text-transform:uppercase;letter-spacing:.4px;">Disponible gastos {PCT_G}%</div>'
        f'<div style="font-size:0.68rem;color:#94A3B8;margin-top:1px;">Lo que puedes gastar libre</div>'
        f'</div>'
        f'<div style="font-size:1.05rem;font-weight:800;color:#4F46E5;letter-spacing:-.5px;">&#36;{gastos_q:,.0f}</div>'
        f'</div>'
        f'<div style="font-size:0.62rem;color:#34D399;margin-top:9px;text-align:center;font-weight:500;">Al recibir cada quincena, aparta primero</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

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
