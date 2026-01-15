import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# הגדרות תצוגה - מותאם למסך האייפון
st.set_page_config(
    page_title="My Wealth",
    page_icon="🍏",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS עיצוב APPLE PRO DARK (RTL) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: #000000;
        color: #ffffff;
        direction: rtl;
    }
    
    .stApp { background-color: #000000; }

    /* העלמת אלמנטים של דפדפן למראה אפליקציה נקייה */
    header, footer, .stDeployButton { visibility: hidden; display: none !important; }
    
    /* כרטיס מניה בסגנון iOS */
    .iphone-card {
        background-color: #1c1c1e;
        border-radius: 22px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #2c2c2e;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    .ticker-name { font-size: 1.1rem; font-weight: 700; color: #ffffff; }
    .allocation { background: #3a3a3c; color: #8e8e93; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; margin-right: 8px; }
    .price-main { font-size: 1.6rem; font-weight: 700; color: #ffffff; margin-top: 5px; }
    
    .up { color: #30d158; font-weight: 600; }
    .down { color: #ff453a; font-weight: 600; }
    .label { color: #8e8e93; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 2px; }

    /* בורר מטבע מעוצב */
    .stRadio > div { background: #1c1c1e; border-radius: 15px; padding: 5px; justify-content: center; }
    </style>
""", unsafe_allow_html=True)

# חיבור לגיליון
SHEET_URL = "https://docs.google.com/spreadsheets/d/18TNmHNZK5Z7YAijKz9UuGj8lSXPgyIs5M24xGK5NGKY/edit?usp=sharing"

@st.cache_data(ttl=300)
def fetch_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SHEET_URL)
    return df[df['IsActive'].astype(str).str.upper() == 'TRUE']

try:
    df = fetch_data()
    
    # הבאת שער דולר/שקל
    usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]

    # בורר מטבע בראש המסך
    currency_mode = st.radio("", ["USD", "ILS"], horizontal=True, label_visibility="collapsed")
    m = usd_ils if currency_mode == "ILS" else 1
    sym = "₪" if currency_mode == "ILS" else "$"

    # חישובים גלובליים
    stock_list = []
    total_val_usd = 0
    total_day_usd = 0
    total_cumul_usd = 0

    for _, row in df.iterrows():
        t = yf.Ticker(row['Ticker'])
        h = t.history(period="2d")
        if h.empty: continue
        
        cp = h['Close'].iloc[-1]
        pp = h['Close'].iloc[-2]
        qty = row['Quantity']
        
        d_profit = (cp - pp) * qty
        c_profit = (cp - row['AvgPrice']) * qty
        
        is_usd = row['Currency'] == 'USD'
        v_usd = (cp * qty) if is_usd else (cp * qty / usd_ils)
        total_val_usd += v_usd
        total_day_usd += d_profit if is_usd else (d_profit / usd_ils)
        total_cumul_usd += c_profit if is_usd else (c_profit / usd_ils)

        stock_list.append({
            'row': row, 'cp': cp, 'dp': d_profit, 'cpn': c_profit, 'v_usd': v_usd, 't_obj': t
        })

    # --- באנר סיכום ראשי ---
    d_total_pct = (total_day_usd / (total_val_usd - total_day_usd)) * 100 if total_val_usd else 0
    c_total_pct = (total_cumul_usd / (total_val_usd - total_cumul_usd)) * 100 if total_val_usd else 0

    st.markdown(f"""
        <div style="text-align: center; padding: 30px 0;">
            <div style="color: #8e8e93; font-size: 0.8rem; letter-spacing: 1px;">TOTAL BALANCE</div>
            <div style="font-size: 3.5rem; font-weight: 700; margin: 5px 0;">{sym}{total_val_usd * m:,.0f}</div>
            <div style="display: flex; justify-content: center; gap: 20px;">
                <div class="{'up' if total_day_usd >=0 else 'down'}">יומי: {sym}{total_day_usd * m:,.0f} ({d_total_pct:+.2f}%)</div>
                <div class="{'up' if total_cumul_usd >=0 else 'down'}">מעלות: {sym}{total_cumul_usd * m:,.0f} ({c_total_pct:+.2f}%)</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- רשימת נכסים ---
    for item in stock_list:
        r = item['row']
        # המרה להצגה
        is_orig_usd = r['Currency'] == 'USD'
        conv = (usd_ils if currency_mode == "ILS" and is_orig_usd else 
                (1/usd_ils if currency_mode == "USD" and not is_orig_usd else 1))
        
        st.markdown(f"""
            <div class="iphone-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span class="ticker-name">{r['Name']}</span><span class="allocation">{(item['v_usd']/total_val_usd)*100:.1f}%</span>
                        <div style="color: #8e8e93; font-size: 0.8rem;">{r['Ticker']}</div>
                    </div>
                    <div style="text-align: left;">
                        <div class="label">Price</div>
                        <div class="price-main">{item['cp']:,.2f} <span style="font-size: 0.7rem;">{r['Currency']}</span></div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; margin-top: 20px; border-top: 1px solid #2c2c2e; padding-top: 15px;">
                    <div>
                        <div class="label">תשואה יומית</div>
                        <div class="{'up' if item['dp'] >= 0 else 'down'}">{item['dp']*conv:,.2f} {sym}</div>
                    </div>
                    <div style="text-align: left;">
                        <div class="label">מעלות</div>
                        <div class="{'up' if item['cpn'] >= 0 else 'down'}">{item['cpn']*conv:,.2f} {sym}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("Analytics"):
            rng = st.select_slider("Range", options=["1D", "1W", "1M", "1Y"], key=f"r_{r['Ticker']}")
            p_map = {"1D":"1d", "1W":"5d", "1M":"1mo", "1Y":"1y"}
            ch = item['t_obj'].history(period=p_map[rng])
            fig = go.Figure(data=[go.Scatter(x=ch.index, y=ch['Close'], line=dict(color='#30d158', width=2), hovertemplate='%{y:,.2f}<extra></extra>')])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=200, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Error: {e}")
