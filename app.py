import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# הגדרות לאייפון
st.set_page_config(page_title="Wealth", page_icon="🍏", layout="centered", initial_sidebar_state="collapsed")

# --- CSS עיצוב פרימיום (RTL) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: -apple-system, sans-serif; background-color: #000000; color: white; direction: rtl; }
    .stApp { background-color: #000000; }
    header, footer, .stDeployButton { visibility: hidden; display: none !important; }

    /* כפתור קפסולה חדשני */
    div[role="radiogroup"] { background-color: #1c1c1e !important; border-radius: 12px; padding: 4px; border: 1px solid #2c2c2e; justify-content: center; }
    div[role="radiogroup"] label { background-color: transparent !important; color: #8e8e93 !important; font-weight: 600; padding: 6px 20px !important; }
    div[role="radiogroup"] label[aria-checked="true"] { background-color: #3a3a3c !important; color: white !important; border-radius: 9px; }
    div[role="radiogroup"] label div:first-child { display: none !important; }

    .iphone-card { background-color: #1c1c1e; border-radius: 22px; padding: 20px; margin-bottom: 12px; border: 1px solid #2c2c2e; }
    .up { color: #30d158; } .down { color: #ff453a; }
    .label { color: #8e8e93; font-size: 0.7rem; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# חיבור לגיליון (כמו שמוגדר ב-Secrets שלך ב-image_9860c6.png)
SHEET_URL = st.secrets["spreadsheet_url"]
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(spreadsheet=SHEET_URL)
active_df = df[df['IsActive'].astype(str).str.upper() == 'TRUE']

# שער דולר
usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]

# בורר מטבע
currency_mode = st.radio("", ["USD", "ILS"], horizontal=True, label_visibility="collapsed")
m = usd_ils if currency_mode == "ILS" else 1
sym = "₪" if currency_mode == "ILS" else "$"

# סיכום תיק ורשימת מניות (לפי הבקשה שלך לאחוזים ותשואות)
total_val_usd = 0
stock_data = []

for _, row in active_df.iterrows():
    t = yf.Ticker(row['Ticker'])
    h = t.history(period="2d")
    if h.empty: continue
    cp, pp, qty, avg = h['Close'].iloc[-1], h['Close'].iloc[-2], row['Quantity'], row['AvgPrice']
    
    # חישובי רווח ואחוזים
    d_profit = (cp - pp) * qty
    d_pct = ((cp - pp) / pp) * 100
    c_profit = (cp - avg) * qty
    c_pct = ((cp - avg) / avg) * 100
    
    val_usd = (cp * qty) if row['Currency'] == 'USD' else (cp * qty / usd_ils)
    total_val_usd += val_usd
    stock_data.append({'row': row, 'cp': cp, 'dp': d_profit, 'dp_pct': d_pct, 'cpn': c_profit, 'cpn_pct': c_pct, 'v_usd': val_usd, 't_obj': t})

# תצוגת שווי כולל
st.markdown(f"<div style='text-align:center; padding:20px;'><div class='label'>PORTFOLIO VALUE</div><div style='font-size:3rem; font-weight:700;'>{sym}{total_val_usd*m:,.0f}</div></div>", unsafe_allow_html=True)

# כרטיסי מניות
for s in stock_data:
    r = s['row']
    conv = (usd_ils if currency_mode == "ILS" and r['Currency'] == 'USD' else (1/usd_ils if currency_mode == "USD" and r['Currency'] == 'ILS' else 1))
    st.markdown(f"""
        <div class="iphone-card">
            <div style="display:flex; justify-content:space-between;">
                <div><b>{r['Name']}</b><br><span class="label">{r['Ticker']}</span></div>
                <div style="text-align:left;">{s['cp']:,.2f} {r['Currency']}</div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; margin-top:15px; border-top:1px solid #2c2c2e; padding-top:10px;">
                <div class="{'up' if s['dp']>=0 else 'down'}">יומי: {sym}{s['dp']*conv:,.0f} ({s['dp_pct']:+.2f}%)</div>
                <div class="{'up' if s['cpn']>=0 else 'down'}" style="text-align:left;">מעלות: {sym}{s['cpn']*conv:,.0f} ({s['cpn_pct']:+.2f}%)</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
