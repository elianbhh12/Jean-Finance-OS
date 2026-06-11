# Jean Finance OS

Sistema personal de seguimiento financiero construido con Python y Streamlit.

## Stack

- **Python 3.10+**
- **Streamlit** — interfaz web
- **SQLite** — base de datos local (sin servidor)
- **Pandas** — transformación de datos
- **Plotly** — visualizaciones

## Funcionalidades

- Dashboard con regla 70/20/10 en tiempo real
- Registro rápido de gastos (categoría + método de pago)
- Seguimiento del fondo de emergencia con proyección
- Análisis mensual comparativo por categoría y método de pago
- Exportación CSV por mes
- Alertas de presupuesto automáticas

## Correr en local

```bash
git clone https://github.com/TU_USUARIO/jean-finance-os.git
cd jean-finance-os
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

```
jean-finance-os/
├── app.py                  # Dashboard principal
├── database.py             # Capa de datos (SQLite)
├── pages/
│   ├── 01_registro.py      # Registro de gastos
│   ├── 02_ahorro.py        # Fondo de emergencia
│   └── 03_analisis.py      # Análisis mensual
├── data/
│   └── finanzas.db         # Base de datos (generada automáticamente)
└── requirements.txt
```

## Deploy

Disponible en [Streamlit Community Cloud](https://share.streamlit.io) — gratis, sin servidor.
