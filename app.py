import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# הגדרות עמוד מותאמות לאייפון
st.set_page_config(
    page_title="Portfolio", 
    page_icon="🍏", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- CSS מותאם אישית ל-Safari באייפון (מראה Native) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* עיצוב כללי - שחור עמוק */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #000000;
        color: #ffffff;
        direction: rtl;
    }
    
    .stApp { background-color: #000000; }

    /* הסתרת אלמנטים של דפדפן ו-Streamlit כדי שיראה כמו אפליקציה */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}

    /* כרטיסי מניה בסגנון Apple Dark Mode */
    .iphone-card {
        background-color: #1c1c1e;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 12px;
        border: 1px solid #2c2c2e;
    }

    .ticker-header { font-size: 1.1rem; font-weight: 700; color: #ffffff; }
    .allocation-badge { 
        background-color: #3a3a3c; color: #8e8e93; font-size: 0.75rem; 
        padding: 3px 8px; border-radius: 8px; 
    }
    
    .live-price { font-size: 1.5rem; font-weight: 700; color: #ffffff; }
    
    .profit-up { color: #30d158; font-weight: 600; }
    .profit-down { color: #ff453a; font-weight: 600; }
    .label { color: #8e8e93; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 2px; }

    /* כפתורי בחירת מטבע מותאמים לאייפון */
    .stRadio > div { 
        background-color: #1c1c1e; border-radius: 12px; padding: 5px; 
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)

# חיבור לגיליון הגוגל
SHEET_URL = "https://docs.google.com/spreadsheets/d/18TNmHNZK5Z7YAijKz9UuGj8lSXPgyIs5M24xGK5NGKY/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # קריאת המניות מהגיליון (לוקח את הטאב הראשון כברירת מחדל)
    df = conn.read(spreadsheet=SHEET_URL)
    return df[df['IsActive'].astype(str).str.upper() == 'TRUE']

try:
    df = load_data()
    
    # הבאת שער דולר/שקל
    with st.spinner('מעדכן נתונים...'):
        usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]

    # בחירת מטבע (מוצג בראש המסך בצורה נקייה)
    currency_mode = st.radio("", ["USD", "ILS"], horizontal=True)
    m = usd_ils if currency_mode == "ILS" else 1
    sym = "₪" if currency_mode == "ILS" else "$"

    # --- חישובים ונתוני שוק ---
    total_val_usd = 0
    total_day_profit_usd = 0
    total_cumul_profit_usd = 0
    stock_list = []

    for _, row in df.iterrows():
        ticker = yf.Ticker(row['Ticker'])
        hist = ticker.history(period="2d")
        if hist.empty: continue
        
        curr_p = hist['Close'].iloc[-1]
        prev_p = hist['Close'].iloc[-2]
        qty = row['Quantity']
        
        # רווחים
        d_profit = (curr_p - prev_p) * qty
        c_profit = (curr_p - row['AvgPrice']) * qty
        
        # נרמול לדולר
        is_usd = row['Currency'] == 'USD'
        v_usd = (curr_p * qty) if is_usd else (curr_p * qty / usd_ils)
        d_p_usd = d_profit if is_usd else (d_profit / usd_ils)
        c_p_usd = c_profit if is_usd else (c_profit / usd_ils)

        total_val_usd += v_usd
        total_day_profit_usd += d_p_usd
        total_cumul_profit_usd += c_p_usd

        stock_list.append({
            'row': row, 'cp': curr_p, 'dp': d_profit, 'cpn': c_profit, 'v_usd': v_usd, 'ticker_obj': ticker
        })

    # --- באנר סיכום תיק (Header) ---
    d_total_pct = (total_day_profit_usd / (total_val_usd - total_day_profit_usd)) * 100
    c_total_pct = (total_cumul_profit_usd / (total_val_usd - total_cumul_profit_usd)) * 100

    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
            <div style="color: #8e8e93; font-size: 0.9rem;">סה"כ שווי התיק</div>
            <div style="font-size: 3rem; font-weight: 700;">{sym}{total_val_usd * m:,.0f}</div>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 10px;">
                <div class="{'profit-up' if total_day_profit_usd >=0 else 'profit-down'}">
                    יומי: {sym}{total_day_profit_usd * m:,.0f} ({d_total_pct:+.2f}%)
                </div>
                <div class="{'profit-up' if total_cumul_profit_usd >=0 else 'profit-down'}">
                    מעלות: {sym}{total_cumul_profit_usd * m:,.0f} ({c_total_pct:+.2f}%)
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- רשימת המניות (Cards) ---
    for item in stock_list:
        r = item['row']
        # המרה להצגה לפי בחירת המשתמש
        disp_d = item['dp'] * (usd_ils if r['Currency'] == 'USD' and currency_mode == 'ILS' else (1/usd_ils if r['Currency'] == 'ILS' and currency_mode == 'USD' else 1))
        disp_c = item['cpn'] * (usd_ils if r['Currency'] == 'USD' and currency_mode == 'ILS' else (1/usd_ils if r['Currency'] == 'ILS' and currency_mode == 'USD' else 1))
        
        d_class = "profit-up" if item['dp'] >= 0 else "profit-down"
        c_class = "profit-up" if item['cpn'] >= 0 else "profit-down"

        st.markdown(f"""
            <div class="iphone-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="ticker-header">{r['Name']}</span> <span class="allocation-badge">{(item['v_usd']/total_val_usd)*100:.1f}%</span>
                        <div style="color: #8e8e93; font-size: 0.8rem;">{r['Ticker']}</div>
                    </div>
                    <div style="text-align: left;">
                        <div class="label">LIVE PRICE</div>
                        <div class="live-price">{item['cp']:,.2f} <span style="font-size: 0.8rem;">{r['Currency']}</span></div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 18px; border-top: 1px solid #2c2c2e; padding-top: 12px;">
                    <div>
                        <div class="label">תשואה יומית</div>
                        <div class="{d_class}">{disp_d:,.2f} {sym}</div>
                    </div>
                    <div style="text-align: left;">
                        <div class="label">מעלות</div>
                        <div class="{c_class}">{disp_c:,.2f} {sym}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # גרף וניתוח (נפתח בלחיצה)
        with st.expander("Analytics & News"):
            rng = st.select_slider("Range", options=["1D", "1W", "1M", "1Y"], key=f"r_{r['Ticker']}")
            p_map = {"1D":"1d", "1W":"5d", "1M":"1mo", "1Y":"1y"}
            ch_data = item['ticker_obj'].history(period=p_map[rng])
            
            fig = go.Figure(data=[go.Scatter(
                x=ch_data.index, y=ch_data['Close'], 
                line=dict(color='#30d158', width=2),
                hovertemplate='Price: %{y:,.2f}<br>Date: %{x}<extra></extra>'
            )])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                              height=220, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            for news in item['ticker_obj'].news[:2]:
                st.markdown(f"• [{news['title']}]({news['link']})")

except Exception as e:
    st.error("החיבור לגיליון נכשל. וודא שהגיליון מוגדר כ-Anyone with the link can view.")
