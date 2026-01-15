import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# הגדרות מערכת Pro Dark
st.set_page_config(page_title="Wealth Pro Admin", page_icon="🌑", layout="centered")

# --- CSS עיצוב BLACK MODE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #000000; color: #ffffff; direction: rtl; }
    .stApp { background-color: #000000; }
    .dark-card { background-color: #1c1c1e; border-radius: 20px; padding: 22px; margin-bottom: 16px; border: 1px solid #2c2c2e; }
    .profit-up { color: #30d158; font-weight: 600; }
    .profit-down { color: #ff453a; font-weight: 600; }
    .secondary-text { color: #8e8e93; font-size: 0.8rem; }
    input { background-color: #1c1c1e !important; color: white !important; border-radius: 10px !important; }
    </style>
""", unsafe_allow_status=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/18TNmHNZK5Z7YAijKz9UuGj8lSXPgyIs5M24xGK5NGKY/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- פונקציות ניהול משתמשים ---
def get_users():
    return conn.read(spreadsheet=SHEET_URL, worksheet="Users")

def add_user(new_u, new_p, new_e, new_r):
    df_users = get_users()
    new_data = pd.DataFrame([[new_u, new_p, new_e, new_r]], columns=df_users.columns)
    updated_df = pd.concat([df_users, new_data], ignore_index=True)
    conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=updated_df)
    st.success(f"משתמש {new_u} נוסף בהצלחה!")

# --- לוגיקת כניסה ---
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = "Viewer"

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; margin-top: 30px;'>Wealth Pro</h1>", unsafe_allow_status=True)
    tab_login, tab_reset = st.tabs(["כניסה", "איפוס סיסמה"])
    
    with tab_login:
        u_input = st.text_input("שם משתמש")
        p_input = st.text_input("סיסמה", type="password")
        if st.button("כניסה למערכת", use_container_width=True):
            users = get_users()
            user_match = users[(users['Username'] == u_input) & (users['Password'].astype(str) == p_input)]
            if not user_match.empty:
                st.session_state.auth = True
                st.session_state.user = u_input
                st.session_state.role = user_match.iloc[0]['Role']
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")
    
    with tab_reset:
        st.write("נשלח קוד אימות לאמצעי הזיהוי שלך")
        email_reset = st.text_input("הכנס אימייל רשום")
        if st.button("שלח לינק לאיפוס"):
            users = get_users()
            if email_reset in users['Email'].values:
                st.info(f"הוראות איפוס נשלחו ל-{email_reset}")
            else:
                st.error("אימייל לא נמצא במערכת")

else:
    # --- ממשק אפליקציה ---
    st.sidebar.markdown(f"### שלום, {st.session_state.user} 🌑")
    st.sidebar.caption(f"Status: {st.session_state.role}")
    
    # חלון הגדרות אדמין
    if st.session_state.role == "Admin":
        with st.sidebar.expander("⚙️ הגדרות אדמין - ניהול משתמשים"):
            with st.form("add_user_form"):
                n_u = st.text_input("שם משתמש חדש")
                n_p = st.text_input("סיסמה ראשונית")
                n_e = st.text_input("אימייל")
                n_r = st.selectbox("תפקיד", ["Viewer", "Admin"])
                if st.form_submit_button("הוסף משתמש"):
                    add_user(n_u, n_p, n_e, n_r)

    currency_mode = st.sidebar.radio("מטבע", ["USD", "ILS"])
    if st.sidebar.button("התנתק"):
        st.session_state.auth = False
        st.rerun()

    # --- טעינת נתונים וחישובים ---
    portfolio = conn.read(spreadsheet=SHEET_URL, worksheet="Portfolio")
    active = portfolio[portfolio['IsActive'].astype(str).str.upper() == 'TRUE']
    usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]
    m = usd_ils if currency_mode == "ILS" else 1
    sym = "₪" if currency_mode == "ILS" else "$"

    total_val_usd = 0
    total_day_usd = 0
    total_cum_usd = 0
    display_list = []

    for _, row in active.iterrows():
        stock = yf.Ticker(row['Ticker'])
        h = stock.history(period="2d")
        if h.empty: continue
        
        c_p = h['Close'].iloc[-1]
        p_p = h['Close'].iloc[-2]
        q = row['Quantity']
        
        # חישובים
        d_profit = (c_p - p_p) * q
        c_profit = (c_p - row['AvgPrice']) * q
        
        is_u = row['Currency'] == 'USD'
        v_usd = c_p * q if is_u else (c_p * q / usd_ils)
        total_val_usd += v_usd
        total_day_usd += d_profit if is_u else (d_profit / usd_ils)
        total_cum_usd += c_profit if is_u else (c_profit / usd_ils)
        
        display_list.append({'row': row, 'cp': c_p, 'dp': d_profit, 'cpn': c_profit, 'v_usd': v_usd, 'pp': p_p})

    # באנר שווי כולל
    d_p_total = (total_day_usd / (total_val_usd - total_day_usd)) * 100 if total_val_usd !=0 else 0
    c_p_total = (total_cum_usd / (total_val_usd - total_cum_usd)) * 100 if total_val_usd !=0 else 0

    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0; border-bottom: 1px solid #2c2c2e; margin-bottom: 25px;">
            <div class="secondary-text">Net Worth</div>
            <div style="font-size: 3rem; font-weight: 700;">{sym}{total_val_usd * m:,.0f}</div>
            <div style="display: flex; justify-content: center; gap: 20px; margin-top: 10px;">
                <div class="{'profit-up' if total_day_usd >=0 else 'profit-down'}">יומי: {sym}{total_day_usd * m:,.0f} ({d_p_total:+.2f}%)</div>
                <div class="{'profit-up' if total_cum_usd >=0 else 'profit-down'}">מעלות: {sym}{total_cum_usd * m:,.0f} ({c_p_total:+.2f}%)</div>
            </div>
        </div>
    """, unsafe_allow_status=True)

    # כרטיסי מניות
    for item in display_list:
        r = item['row']
        cur_sym = "$" if r['Currency'] == "USD" else "₪"
        
        # המרה לרווחים מוצגים
        disp_d = item['dp'] * (usd_ils if r['Currency'] == 'USD' and currency_mode == 'ILS' else (1/usd_ils if r['Currency'] == 'ILS' and currency_mode == 'USD' else 1))
        disp_c = item['cpn'] * (usd_ils if r['Currency'] == 'USD' and currency_mode == 'ILS' else (1/usd_ils if r['Currency'] == 'ILS' and currency_mode == 'USD' else 1))

        st.markdown(f"""
            <div class="dark-card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 600;">{r['Name']}</div>
                        <div class="secondary-text">{r['Ticker']} | {(item['v_usd']/total_val_usd)*100:.1f}%</div>
                    </div>
                    <div style="text-align: left;">
                        <div class="secondary-text">Live Price</div>
                        <div style="font-size: 1.4rem; font-weight: 700;">{item['cp']:,.2f} {r['Currency']}</div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 15px; border-top: 1px solid #2c2c2e; padding-top: 15px;">
                    <div>
                        <div class="secondary-text">תשואה יומית</div>
                        <div class="{'profit-up' if item['dp'] >= 0 else 'profit-down'}">{disp_d:,.2f} {sym}</div>
                    </div>
                    <div style="text-align: left;">
                        <div class="secondary-text">מעלות</div>
                        <div class="{'profit-up' if item['cpn'] >= 0 else 'profit-down'}">{disp_c:,.2f} {sym}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_status=True)

        with st.expander("Analysis & Chart"):
            tkr = yf.Ticker(r['Ticker'])
            rng = st.radio("Range", ["1D", "1W", "1M", "1Y"], key=f"r_{r['Ticker']}", horizontal=True)
            p_map = {"1D":"1d", "1W":"5d", "1M":"1mo", "1Y":"1y"}
            ch_d = tkr.history(period=p_map[rng])
            fig = go.Figure(data=[go.Scatter(x=ch_d.index, y=ch_d['Close'], line=dict(color='#30d158', width=2), hovertemplate='Price: %{y:,.2f}<br>Date: %{x}<extra></extra>')])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
