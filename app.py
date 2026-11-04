import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re

# Import yfinance come fallback e fonte principale pulita
try:
    import yfinance as yf
except ImportError:
    yf = None

# =============================================================================
# 1. CONFIGURAZIONE PAGINA & DESIGN SYSTEM CSS (UI/UX PRO MAX)
# =============================================================================
st.set_page_config(
    page_title="Quantamentale Terminal | Pro Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_design_system():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-primary: #0B0F19;
            --bg-card: rgba(17, 24, 39, 0.78);
            --bg-card-hover: rgba(30, 41, 59, 0.85);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-focus: rgba(59, 130, 246, 0.45);
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --accent-blue: #3B82F6;
            --accent-indigo: #6366F1;
            --bullish: #10B981;
            --bullish-bg: rgba(16, 185, 129, 0.12);
            --bearish: #F43F5E;
            --bearish-bg: rgba(244, 63, 94, 0.12);
            --amber: #F59E0B;
        }

        /* Tipografia Globale */
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: var(--bg-primary) !important;
            color: var(--text-primary) !important;
        }

        /* Riduzione spazi vuoti superiori di Streamlit */
        .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 3rem !important;
            max-width: 1440px !important;
        }

        /* Header Hero Banner */
        .terminal-header {
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.92) 0%, rgba(15, 23, 42, 0.75) 100%);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1.4rem 1.8rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(12px);
        }
        .terminal-title-group h1 {
            font-size: 1.55rem !important;
            font-weight: 800 !important;
            margin: 0 !important;
            padding: 0 !important;
            letter-spacing: -0.025em;
            background: linear-gradient(90deg, #FFFFFF 0%, #93C5FD 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .terminal-title-group p {
            color: var(--text-secondary);
            font-size: 0.86rem;
            margin: 0.25rem 0 0 0;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34D399;
            padding: 6px 14px;
            border-radius: 999px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #10B981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10B981;
        }

        /* Bento KPI Card Custom */
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 1.15rem 1.35rem;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            backdrop-filter: blur(10px);
            height: 100%;
        }
        .kpi-card:hover {
            border-color: var(--border-focus);
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.35);
        }
        .kpi-label {
            color: var(--text-secondary);
            font-size: 0.74rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.45rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .kpi-value {
            font-family: 'JetBrains Mono', monospace;
            font-variant-numeric: tabular-nums;
            font-size: 1.55rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }
        .kpi-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.76rem;
            margin-top: 0.5rem;
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 600;
        }
        .sub-up {
            color: var(--bullish);
            background: var(--bullish-bg);
        }
        .sub-down {
            color: var(--bearish);
            background: var(--bearish-bg);
        }
        .sub-neutral {
            color: #93C5FD;
            background: rgba(59, 130, 246, 0.12);
        }

        /* Section Title Bar */
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 1.4rem 0 0.85rem 0;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid var(--border-subtle);
        }
        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.01em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .section-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.05);
            padding: 3px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-subtle);
        }

        /* Stile Tabs Principali */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(17, 24, 39, 0.85);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid var(--border-subtle);
            margin-bottom: 1.2rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            border-radius: 8px;
            padding: 0 18px;
            font-weight: 600;
            font-size: 0.86rem;
            color: var(--text-secondary);
            border: none !important;
            background-color: transparent;
            transition: all 0.18s ease;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        }

        /* Bottoni Primari */
        .stButton > button {
            background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.4rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45) !important;
        }

        /* Metriche Native Streamlit (Fallback) */
        [data-testid="stMetric"] {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 14px 18px;
        }
        [data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace !important;
        }
    </style>
    """, unsafe_allow_html=True)

inject_design_system()

# Componenti UI Helper
def render_kpi_card(label, value, subtext="", status="neutral", icon="◈"):
    sub_class = {"up": "sub-up", "down": "sub-down", "neutral": "sub-neutral"}.get(status, "sub-neutral")
    sub_html = f'<div class="kpi-sub {sub_class}">{subtext}</div>' if subtext else ''
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label"><span>{label}</span><span>{icon}</span></div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def render_section_header(title, badge_text=""):
    badge_html = f'<span class="section-badge">{badge_text}</span>' if badge_text else ''
    st.markdown(f"""
    <div class="section-header">
        <div class="section-title">{title}</div>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 2. DATA ENGINE & FUNZIONI DI SISTEMA (INVARIATE NELLA LOGICA)
# =============================================================================
def find_excel_file(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    user_home = os.path.expanduser("~")
    
    search_paths = [
        filename,
        os.path.join(script_dir, filename),
        os.path.join(user_home, filename),
        os.path.join(user_home, "Documenti", "Crypto_Quant", filename),
        os.path.join(user_home, "Documenti", "ETF_Quant", filename),
        os.path.join(user_home, "Documents", "Crypto_Quant", filename),
        os.path.join(user_home, "Documents", "ETF_Quant", filename),
        os.path.join(user_home, "Desktop", filename),
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p
    return None

def strip_timezone(series):
    s = pd.to_datetime(series)
    if hasattr(s.dt, 'tz') and s.dt.tz is not None:
        return s.dt.tz_localize(None)
    return s

def ensure_weekly(df):
    if df is None or df.empty:
        return df
    df_c = df.copy()
    df_c['Date'] = pd.to_datetime(df_c['Date'])
    df_c = df_c.sort_values('Date')
    days_diff = (df_c['Date'].iloc[-1] - df_c['Date'].iloc[0]).days
    if days_diff > 0 and len(df_c) > days_diff * 0.3:
        df_c.set_index('Date', inplace=True)
        weekly = df_c.resample('W-MON').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
        }).dropna().reset_index()
        return weekly
    return df_c

def filter_by_horizon(df, horizon):
    if df is None or df.empty:
        return df, 0.0, 0.0, 0.0
    df_c = df.copy()
    df_c['Date'] = pd.to_datetime(df_c['Date'])
    df_c = df_c.sort_values('Date')
    last_date = df_c['Date'].max()
    
    offsets = {
        "1 Mese": pd.DateOffset(months=1),
        "3 Mesi": pd.DateOffset(months=3),
        "6 Mesi": pd.DateOffset(months=6),
        "1 Anno": pd.DateOffset(years=1),
        "3 Anni": pd.DateOffset(years=3),
        "5 Anni": pd.DateOffset(years=5),
    }
    start_target = last_date - offsets[horizon] if horizon in offsets else df_c['Date'].min()
        
    df_filtered = df_c[df_c['Date'] >= start_target].copy()
    if df_filtered.empty:
        df_filtered = df_c.tail(2).copy()
        
    p_start = df_filtered['Close'].iloc[0]
    p_end = df_filtered['Close'].iloc[-1]
    ret_pct = ((p_end - p_start) / p_start) * 100.0 if p_start > 0 else 0.0
    return df_filtered, p_start, p_end, ret_pct

@st.cache_data
def load_etf_history_from_file(sheet_name, ticker="SPY"):
    if yf is not None:
        try:
            df_yf = yf.Ticker(ticker).history(period="max")
            if not df_yf.empty:
                df_yf = df_yf.reset_index()
                date_col = [c for c in df_yf.columns if 'date' in c.lower() or 'data' in c.lower()][0]
                df_yf[date_col] = strip_timezone(df_yf[date_col])
                df_yf = df_yf.sort_values(by=date_col)
                return df_yf[[date_col, 'Open', 'High', 'Low', 'Close']].rename(
                    columns={date_col: 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close'}
                ).dropna()
        except Exception:
            pass
            
    etf_file = find_excel_file("Hystorical_Data_ETF.xlsx")
    if etf_file:
        try:
            df = pd.read_excel(etf_file, sheet_name=sheet_name).dropna(subset=['Close'])
            date_col = [c for c in df.columns if 'date' in c.lower() or 'data' in c.lower()][0]
            close_col = [c for c in df.columns if 'close' in c.lower() or 'chiusura' in c.lower()][0]
            df[date_col] = strip_timezone(df[date_col])
            df = df.sort_values(by=date_col)
            return df[[date_col, close_col, close_col, close_col, close_col]].rename(
                columns={date_col: 'Date', df.columns[1]: 'Open', df.columns[2]: 'High', df.columns[3]: 'Low', close_col: 'Close'}
            ).dropna()
        except Exception:
            pass
    return None

@st.cache_data
def load_crypto_history_from_file(crypto_code):
    symbol_display = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
    if yf is not None:
        try:
            df_yf = yf.Ticker(symbol_display).history(period="max", interval="1wk")
            if not df_yf.empty:
                df_yf = df_yf.reset_index()
                date_col = [c for c in df_yf.columns if 'date' in c.lower() or 'data' in c.lower()][0]
                df_yf[date_col] = strip_timezone(df_yf[date_col])
                df_yf = df_yf.sort_values(by=date_col)
                df_out = df_yf[[date_col, 'Open', 'High', 'Low', 'Close']].rename(
                    columns={date_col: 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close'}
                ).dropna()
                return ensure_weekly(df_out)
        except Exception:
            pass
    return None

meta_etfs = {
    "Arabia Saudita": {"Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita", "Voto_Macro": 2.94},
    "India": {"Ticker_YF": "INDA", "Sheet_ETF": "India", "Voto_Macro": 3.06},
    "Germania": {"Ticker_YF": "EWG", "Sheet_ETF": "Germania", "Voto_Macro": 2.64},
    "Taiwan": {"Ticker_YF": "EWT", "Sheet_ETF": "Taiwan", "Voto_Macro": 3.25},
    "Spagna": {"Ticker_YF": "EWP", "Sheet_ETF": "Spagna", "Voto_Macro": 2.71},
    "Francia": {"Ticker_YF": "EWQ", "Sheet_ETF": "Francia", "Voto_Macro": 2.35},
    "Regno unito": {"Ticker_YF": "EWU", "Sheet_ETF": "UK", "Voto_Macro": 2.35},
    "Italia": {"Ticker_YF": "EWI", "Sheet_ETF": "Italia", "Voto_Macro": 2.00},
    "Corea del Sud": {"Ticker_YF": "EWY", "Sheet_ETF": "Corea", "Voto_Macro": 3.00},
    "Indonesia": {"Ticker_YF": "EIDO", "Sheet_ETF": "Indonesia", "Voto_Macro": 3.00},
    "Argentina": {"Ticker_YF": "ARGT", "Sheet_ETF": "Argentina", "Voto_Macro": 2.14},
    "Canada": {"Ticker_YF": "EWC", "Sheet_ETF": "Canada", "Voto_Macro": 2.94},
    "USA": {"Ticker_YF": "SPY", "Sheet_ETF": "America", "Voto_Macro": 3.00},
    "Sud Africa": {"Ticker_YF": "EZA", "Sheet_ETF": "Sud Africa", "Voto_Macro": 2.50},
    "Messico": {"Ticker_YF": "EWW", "Sheet_ETF": "Messico", "Voto_Macro": 2.19},
    "Giappone": {"Ticker_YF": "EWJ", "Sheet_ETF": "Giappone", "Voto_Macro": 2.64},
    "Cina": {"Ticker_YF": "MCHI", "Sheet_ETF": "Cina", "Voto_Macro": 3.06},
    "Brasile": {"Ticker_YF": "EWZ", "Sheet_ETF": "Brasile", "Voto_Macro": 2.18}
}

@st.cache_data
def load_forecast_from_excel():
    db_file = find_excel_file("DataBase.xlsx")
    records = []
    if db_file:
        try:
            df_fc = pd.read_excel(db_file, sheet_name="Forecast")
            for _, row in df_fc.dropna(subset=['Country', 'Forecast']).iterrows():
                paese = str(row['Country']).strip()
                fc_str = str(row['Forecast']).strip()
                match = re.search(r'([\d\.]+)', fc_str)
                prob = float(match.group(1)) if match else 50.0
                segnal = "DOWN" if "DOWN" in fc_str.upper() else "UP"
                meta = meta_etfs.get(paese, {"Ticker_YF": "SPY", "Sheet_ETF": paese, "Voto_Macro": 2.5})
                records.append({
                    "Paese": paese, "Prob_UP": prob, "Segnale": segnal, "Esito AI": f"{prob:.1f}% ({segnal})",
                    "Ticker_YF": meta["Ticker_YF"], "Sheet_ETF": meta["Sheet_ETF"], "Voto_Macro": meta["Voto_Macro"]
                })
        except Exception:
            pass
            
    if not records:
        for p, m in meta_etfs.items():
            records.append({
                "Paese": p, "Prob_UP": 60.0, "Segnale": "UP", "Esito AI": "60.0% (UP)",
                "Ticker_YF": m["Ticker_YF"], "Sheet_ETF": m["Sheet_ETF"], "Voto_Macro": m["Voto_Macro"]
            })
    df = pd.DataFrame(records).sort_values(by="Prob_UP", ascending=False).reset_index(drop=True)
    df["Allocazione"] = 0
    df.loc[df[(df["Segnale"] == "UP") & (df["Prob_UP"] >= 60.0)].head(5).index, "Allocazione"] = 200
    return df

df_all = load_forecast_from_excel()

@st.cache_data
def build_pro_chart(df, title_name, chart_type="Linea", is_log=True, add_sma=False):
    df_c = df.copy().dropna(subset=['Close'])
    fig = go.Figure()

    if chart_type == "Candele (Candlestick)" and 'Open' in df_c.columns:
        fig.add_trace(go.Candlestick(
            x=df_c['Date'], open=df_c['Open'], high=df_c['High'], low=df_c['Low'], close=df_c['Close'],
            name="OHLC",
            increasing_line_color='#10B981', increasing_fillcolor='rgba(16, 185, 129, 0.7)',
            decreasing_line_color='#F43F5E', decreasing_fillcolor='rgba(244, 63, 94, 0.7)'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_c['Date'], y=df_c['Close'], mode='lines', name="Prezzo Chiusura",
            line=dict(color='#3B82F6', width=2.4),
            fill='tozeroy' if not is_log else None,
            fillcolor='rgba(59, 130, 246, 0.08)'
        ))

    if add_sma and len(df_c) >= 20:
        df_c['SMA_20'] = df_c['Close'].rolling(20).mean()
        df_c['SMA_50'] = df_c['Close'].rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=df_c['Date'], y=df_c['SMA_20'], mode='lines', name="SMA 20",
            line=dict(color='#F59E0B', width=1.4, dash='dot')
        ))
        if len(df_c) >= 50:
            fig.add_trace(go.Scatter(
                x=df_c['Date'], y=df_c['SMA_50'], mode='lines', name="SMA 50",
                line=dict(color='#A855F7', width=1.4, dash='dash')
            ))

    fig.update_layout(
        title=dict(text=f"<b>{title_name}</b>", font=dict(size=15, family="Plus Jakarta Sans", color="#F8FAFC"), x=0.01),
        yaxis_title="Valore / Prezzo",
        xaxis_title="",
        template="plotly_dark",
        paper_bgcolor="rgba(17, 24, 39, 0.65)",
        plot_bgcolor="rgba(17, 24, 39, 0.0)",
        height=480,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis=dict(
            showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)',
            type='date', rangeslider=dict(visible=False)
        ),
        yaxis=dict(
            type="log" if is_log else "linear",
            showgrid=True, gridcolor='rgba(255, 255, 255, 0.05)',
            side="right"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

@st.cache_data
def get_official_crypto_indicators(crypto_code):
    db_file = find_excel_file("DataBase.xlsx")
    if db_file:
        try:
            df_c = pd.read_excel(db_file, sheet_name="Tecnica Crypto S").dropna(subset=["Crypto"])
            sub = df_c[df_c["Crypto"] == crypto_code]
            if not sub.empty:
                last = sub.iloc[-1]
                price = last["Prezzo"]
                rsi_v = last["RSI"]
                macd_v = last["MACD Hist"]
                sma21_v = last["SMA 21"]
                sma50_v = last["SMA 50"]
                df_res = pd.DataFrame({
                    "Indicatore Tecnico": ["RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
                    "Valore Ufficiale": [f"{rsi_v:.2f}", f"{macd_v:+.2f}", f"${sma21_v:,.2f}", f"${sma50_v:,.2f}"]
                })
                return price, last.get("Predict", "UP"), df_res
        except Exception:
            pass
    return (78262.72, "UP", pd.DataFrame()) if crypto_code == "BTC" else (2274.53, "DOWN", pd.DataFrame())

# =============================================================================
# 3. SIDEBAR: DIAGNOSTICA DI SISTEMA & CONTROLLO PORTAFOGLIO
# =============================================================================
with st.sidebar:
    st.markdown("### ⚡ Quantamentale Core")
    st.caption("Sistema Quantitativo Macro-Tecnico & AI Rotation")
    st.markdown("---")
    
    db_status = find_excel_file("DataBase.xlsx") is not None
    etf_status = find_excel_file("Hystorical_Data_ETF.xlsx") is not None
    yf_status = yf is not None

    st.markdown("**Stato Connessioni Dati**")
    st.markdown(f"- **DataBase.xlsx**: {'🟢 Connesso' if db_status else '🟡 Fallback Interno'}")
    st.markdown(f"- **Storico ETF Excel**: {'🟢 Connesso' if etf_status else '🟡 Fallback YFinance'}")
    st.markdown(f"- **Yahoo Finance API**: {'🟢 Attiva' if yf_status else '🔴 Assente'}")
    
    st.markdown("---")
    top5_list = df_all[df_all["Allocazione"] > 0]["Paese"].tolist()
    st.markdown("**🏆 Top 5 ETF Attivi (Target 1.000€)**")
    if top5_list:
        for idx_t, c_name in enumerate(top5_list, 1):
            r_info = df_all[df_all["Paese"] == c_name].iloc[0]
            st.markdown(f"`#{idx_t}` **{c_name}** ({r_info['Ticker_YF']}) — *{r_info['Prob_UP']:.1f}%*")
    else:
        st.caption("Nessun ETF con segnale UP >= 60%")

    st.markdown("---")
    if st.button("🔄 Aggiorna Cache Dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# =============================================================================
# 4. HEADER PRINCIPALE & NAVIGATION TABS
# =============================================================================
st.markdown("""
<div class="terminal-header">
    <div class="terminal-title-group">
        <h1>⚡ QUANTAMENTALE TRADING TERMINAL</h1>
        <p>Allocazione Quantitativa ETF Country, Modelli Previsionali RStudio AI & Analisi Tecnica Crypto</p>
    </div>
    <div class="status-pill">
        <span class="status-dot"></span>
        <span>ENGINE ONLINE • TAX 26% READY</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_etf, tab_corr, tab_backtest, tab_crypto = st.tabs([
    "🏆 Rotazione ETF & Grafici Pro",
    "🔄 Matrice & Correlazione ETF",
    "⏳ Simulatore Backtest & Tasse (26%)",
    "₿ Mercati Crypto (BTC & ETH)"
])

# =============================================================================
# TAB 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI
# =============================================================================
with tab_etf:
    # KPI Riepilogativi Top Row
    up_count = len(df_all[df_all["Segnale"] == "UP"])
    tot_alloc = df_all["Allocazione"].sum()
    best_row = df_all.iloc[0]
    avg_macro = df_all["Voto_Macro"].mean()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Top Pick Modello AI", f"{best_row['Paese']} ({best_row['Ticker_YF']})", f"Prob. UP: {best_row['Prob_UP']:.1f}%", "up", "🏆")
    with k2:
        render_kpi_card("Breadth Mercato Globale", f"{up_count} / {len(df_all)} ETF", f"{(up_count/len(df_all))*100:.0f}% Mercati Rialzisti", "up" if up_count >= 9 else "down", "🌍")
    with k3:
        render_kpi_card("Budget Allocato (Top 5)", f"{tot_alloc:,.0f} €", "200 € per ETF Idoneo (≥60%)", "neutral", "💼")
    with k4:
        render_kpi_card("Sentiment Macro Medio", f"{avg_macro:.2f} / 5.0", "Score Fondamentale Globale", "neutral", "📊")

    render_section_header("🏆 Classifica Quantitativa & Allocazione AI (18 Paesi)", "Fonte: Foglio Forecast")

    col_filter1, col_filter2 = st.columns([1, 2])
    sig_filter = col_filter1.segmented_control("Filtra per Segnale:", ["Tutti", "Solo UP", "Top 5 Allocati"], default="Tutti")
    
    df_display = df_all.copy()
    if sig_filter == "Solo UP":
        df_display = df_display[df_display["Segnale"] == "UP"]
    elif sig_filter == "Top 5 Allocati":
        df_display = df_display[df_display["Allocazione"] > 0]

    st.dataframe(
        df_display[["Paese", "Ticker_YF", "Segnale", "Prob_UP", "Esito AI", "Voto_Macro", "Allocazione"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Paese": st.column_config.TextColumn("Paese / Mercato", width="medium"),
            "Ticker_YF": st.column_config.TextColumn("Ticker", width="small"),
            "Segnale": st.column_config.TextColumn("Direzione AI", width="small"),
            "Prob_UP": st.column_config.ProgressColumn(
                "Confidenza AI (%)",
                help="Probabilità stimata dal modello RStudio",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "Esito AI": st.column_config.TextColumn("Output Ufficiale", width="medium"),
            "Voto_Macro": st.column_config.NumberColumn("Score Macro", format="%.2f ⭐"),
            "Allocazione": st.column_config.NumberColumn("Allocazione Target", format="%d €"),
        }
    )

    render_section_header("📈 Terminale Grafico Storico ETF", "Dati Yahoo Finance / Hystorical_Data_ETF.xlsx")

    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns([2, 1.2, 0.9, 0.9])
    selected_country = c_ctrl1.selectbox("Seleziona ETF Paese:", df_all["Paese"].tolist())
    chart_type = c_ctrl2.radio("Stile Grafico:", ["Linea", "Candele (Candlestick)"], horizontal=True)
    is_log = c_ctrl3.toggle("Scala Logaritmica", value=True)
    show_sma = c_ctrl4.toggle("Medie Mobili (20/50)", value=True)

    horizon_etf = st.segmented_control(
        "Orizzonte Temporale:",
        ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"],
        default="Tutto (Max)"
    ) or "Tutto (Max)"

    row_country = df_all[df_all["Paese"] == selected_country].iloc[0]
    df_chart = load_etf_history_from_file(row_country["Sheet_ETF"], ticker=row_country["Ticker_YF"])

    if df_chart is not None and not df_chart.empty:
        df_filt, p_start, p_end, ret_pct = filter_by_horizon(df_chart, horizon_etf)
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_kpi_card(f"Rendimento ({horizon_etf})", f"{ret_pct:+.2f}%", f"Da ${p_start:,.2f} a ${p_end:,.2f}", "up" if ret_pct >= 0 else "down", "📈")
        with m2:
            render_kpi_card("Ultimo Prezzo Chiusura", f"${p_end:,.2f}", f"Ticker: {row_country['Ticker_YF']}", "neutral", "💵")
        with m3:
            render_kpi_card("Previsione Modello AI", row_country['Esito AI'], f"Allocazione: {row_country['Allocazione']} €", "up" if row_country["Segnale"] == "UP" else "down", "🤖")
        with m4:
            render_kpi_card("Rating Macroeconomico", f"{row_country['Voto_Macro']:.2f}", "Punteggio Fondamentale Paese", "neutral", "🏛️")

        st.write("")
        fig_p = build_pro_chart(
            df_filt,
            f"{selected_country} ({row_country['Ticker_YF']}) — Orizzonte: {horizon_etf}",
            chart_type=chart_type,
            is_log=is_log,
            add_sma=show_sma
        )
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.warning("Dati storici non disponibili per questo ETF.")

# =============================================================================
# TAB 2: CORRELAZIONE ETF (COPPIA + MATRICE COMPLETA)
# =============================================================================
with tab_corr:
    render_section_header("🔄 Analisi di Correlazione & Diversificazione tra 2 ETF", "Rendimenti Giornalieri/Settimanali")

    col1, col2 = st.columns(2)
    e1 = col1.selectbox("Primo ETF (Asset A):", df_all["Paese"].tolist(), index=0)
    e2 = col2.selectbox("Secondo ETF (Asset B):", df_all["Paese"].tolist(), index=1)

    if e1 != e2:
        r1 = df_all[df_all["Paese"] == e1].iloc[0]
        r2 = df_all[df_all["Paese"] == e2].iloc[0]
        df1 = load_etf_history_from_file(r1["Sheet_ETF"], ticker=r1["Ticker_YF"])
        df2 = load_etf_history_from_file(r2["Sheet_ETF"], ticker=r2["Ticker_YF"])
        
        if df1 is not None and df2 is not None:
            merged = pd.merge(df1[['Date', 'Close']], df2[['Date', 'Close']], on='Date', suffixes=('_1', '_2')).dropna()
            if len(merged) > 5:
                corr = merged['Close_1'].pct_change().corr(merged['Close_2'].pct_change())
                
                if corr >= 0.70:
                    regime_label, status_c = "Correlazione Forte (Bassa Diversificazione)", "down"
                elif corr >= 0.35:
                    regime_label, status_c = "Correlazione Moderata", "neutral"
                else:
                    regime_label, status_c = "Bassa Correlazione (Ottima Diversificazione)", "up"

                kc1, kc2, kc3 = st.columns(3)
                with kc1:
                    render_kpi_card("Coefficiente di Pearson (r)", f"{corr:.2f}", regime_label, status_c, "🔗")
                with kc2:
                    render_kpi_card(f"Asset A: {e1}", r1["Ticker_YF"], f"Esito AI: {r1['Esito AI']}", "neutral", "🅰️")
                with kc3:
                    render_kpi_card(f"Asset B: {e2}", r2["Ticker_YF"], f"Esito AI: {r2['Esito AI']}", "neutral", "🅱️")

                # Grafico Comparativo Base 100
                merged = merged.sort_values('Date')
                merged['Norm_1'] = (merged['Close_1'] / merged['Close_1'].iloc[0]) * 100
                merged['Norm_2'] = (merged['Close_2'] / merged['Close_2'].iloc[0]) * 100

                fig_comp = go.Figure()
                fig_comp.add_trace(go.Scatter(x=merged['Date'], y=merged['Norm_1'], mode='lines', name=f"{e1} ({r1['Ticker_YF']})", line=dict(color='#3B82F6', width=2.2)))
                fig_comp.add_trace(go.Scatter(x=merged['Date'], y=merged['Norm_2'], mode='lines', name=f"{e2} ({r2['Ticker_YF']})", line=dict(color='#10B981', width=2.2)))
                fig_comp.update_layout(
                    title=dict(text=f"<b>Confronto Forza Relativa Normalizzata (Base 100) — {e1} vs {e2}</b>", font=dict(size=14, color="#F8FAFC")),
                    template="plotly_dark",
                    paper_bgcolor="rgba(17, 24, 39, 0.65)",
                    plot_bgcolor="rgba(17, 24, 39, 0.0)",
                    height=420,
                    hovermode="x unified",
                    yaxis=dict(side="right", title="Indice (Base 100)", gridcolor='rgba(255, 255, 255, 0.05)'),
                    xaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)')
                )
                st.write("")
                st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Seleziona due ETF differenti per calcolare il coefficiente di correlazione.")

# =============================================================================
# TAB 3: SIMULATORE DI BACKTEST & REGISTRO TRANSAZIONI
# =============================================================================
with tab_backtest:
    render_section_header("⏳ Motore di Backtest Strategia AI & Fiscalità Italiana (Capital Gain 26%)", "Reinvestimento Composto Netto")

    with st.container():
        col_s1, col_s2, col_d1, col_d2 = st.columns([1.2, 2, 1, 1])
        init_cap = col_s1.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
        strategy_mode = col_s2.selectbox(
            "Strategia Operativa:",
            ["Portafoglio Rotazione Top 5 ETF (Modello RStudio)", "Asset Singolo"]
        )
        d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
        d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))

        sel_asset = None
        if strategy_mode == "Asset Singolo":
            all_assets = df_all["Paese"].tolist() + ["Bitcoin (BTC)", "Ethereum (ETH)"]
            sel_asset = st.selectbox("Seleziona Asset Singolo per Simulazione:", all_assets, index=0)

    run_bt = st.button("🚀 Esegui Simulazione Backtest & Genera Registro Fiscale", use_container_width=True)

    if run_bt:
        with st.spinner("Calcolo traiettoria di portafoglio, rotazioni mensili e ritenute fiscali al 26%..."):
            try:
                dt_start = pd.to_datetime(d_start)
                dt_end = pd.to_datetime(d_end)
                
                if strategy_mode == "Portafoglio Rotazione Top 5 ETF (Modello RStudio)":
                    etf_dfs = {}
                    for _, row in df_all.iterrows():
                        df_h = load_etf_history_from_file(row["Sheet_ETF"], ticker=row["Ticker_YF"])
                        if df_h is not None and not df_h.empty:
                            df_h['Date'] = strip_timezone(df_h['Date'])
                            etf_dfs[row["Paese"]] = df_h.sort_values('Date').set_index('Date')['Close']
                            
                    df_prices = pd.DataFrame(etf_dfs).dropna(how='all').sort_index()
                    mask = (df_prices.index >= dt_start) & (df_prices.index <= dt_end)
                    df_prices = df_prices.loc[mask]
                    
                    if len(df_prices) > 2:
                        df_monthly = df_prices.resample('ME').last().dropna(how='all')
                        df_returns = df_monthly.pct_change().fillna(0)
                        
                        capital = init_cap
                        cap_history = []
                        tx_log = []
                        total_taxes = 0.0
                        
                        for idx in range(1, len(df_returns)):
                            date_idx = df_returns.index[idx]
                            date_str = date_idx.strftime('%d/%m/%Y')
                            
                            prev_returns = df_returns.iloc[idx - 1]
                            top_5 = prev_returns[prev_returns >= 0].nlargest(5).index.tolist()
                            if len(top_5) < 5:
                                remaining = [p for p in prev_returns.nlargest(5).index.tolist() if p not in top_5]
                                top_5.extend(remaining[:5 - len(top_5)])
                                
                            current_month_rets = df_returns.iloc[idx][top_5]
                            avg_ret = current_month_rets.mean()
                            
                            gross_profit = capital * avg_ret
                            tax = gross_profit * 0.26 if gross_profit > 0 else 0.0
                            net_profit = gross_profit - tax
                            capital += net_profit
                            total_taxes += tax
                            
                            cap_history.append(capital)
                            tx_log.append({
                                "Data": date_str,
                                "Asset Selezionati (Top 5)": ", ".join(top_5),
                                "Rendimento Medio Mese (%)": f"{avg_ret*100:+.2f}%",
                                "Utile Netto (€)": f"{net_profit:+,.2f} €",
                                "Tasse 26% (€)": f"{tax:,.2f} €",
                                "Capitale Finale (€)": f"{capital:,.2f} €"
                            })
                            
                        df_plot = pd.DataFrame({'Date': df_returns.index[1:len(cap_history)+1], 'Close': cap_history})
                        final_val = cap_history[-1] if cap_history else init_cap
                        tot_ret = ((final_val - init_cap) / init_cap) * 100.0
                        net_gain = final_val - init_cap
                        
                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            render_kpi_card("Capitale Iniziale", f"{init_cap:,.2f} €", "Base di Partenza", "neutral", "🏦")
                        with b2:
                            render_kpi_card("Valore Finale Netto", f"{final_val:,.2f} €", f"Rendimento: {tot_ret:+.2f}%", "up" if tot_ret >= 0 else "down", "💎")
                        with b3:
                            render_kpi_card("Profitto Netto Cumulato", f"{net_gain:+,.2f} €", "Al netto del 26% fiscale", "up" if net_gain >= 0 else "down", "📈")
                        with b4:
                            render_kpi_card("Imposte Versate (26%)", f"{total_taxes:,.2f} €", f"{len(tx_log)} Ribilanciamenti Mensili", "neutral", "🧾")
                        
                        st.write("")
                        fig_t = build_pro_chart(df_plot, "Equity Line Netto Fiscale — Portafoglio Rotazione Top 5 ETF", is_log=False)
                        st.plotly_chart(fig_t, use_container_width=True)
                        
                        render_section_header("📋 Registro Ufficiale delle Transazioni & Rotazione Mensile Top 5", f"{len(tx_log)} Operazioni")
                        st.dataframe(pd.DataFrame(tx_log), use_container_width=True, hide_index=True)
                    else:
                        st.warning("Dati insufficienti per l'intervallo selezionato.")
                
                else:
                    is_crypto = sel_asset in ["Bitcoin (BTC)", "Ethereum (ETH)"]
                    if is_crypto:
                        df_sim = load_crypto_history_from_file("BTC" if "BTC" in sel_asset else "ETH")
                    else:
                        row_a = df_all[df_all["Paese"] == sel_asset].iloc[0]
                        df_sim = load_etf_history_from_file(row_a["Sheet_ETF"], ticker=row_a["Ticker_YF"])
                    
                    if df_sim is not None and not df_sim.empty:
                        df_sim['Date'] = strip_timezone(df_sim['Date'])
                        mask = (df_sim['Date'] >= dt_start) & (df_sim['Date'] <= dt_end)
                        df_sim = df_sim.loc[mask].sort_values('Date').set_index('Date')
                        
                        rule = 'W-MON' if is_crypto else 'ME'
                        df_res = df_sim.resample(rule).agg({'Close': 'last'}).dropna()
                        df_res['Period_Return'] = df_res['Close'].pct_change().fillna(0)
                        df_res['Signal'] = np.where(df_res['Period_Return'].shift(1).fillna(0) >= 0, 'UP', 'DOWN')
                        
                        capital = init_cap
                        cap_history = []
                        tx_log = []
                        total_taxes = 0.0
                        
                        for idx, row in df_res.iterrows():
                            date_str = idx.strftime('%d/%m/%Y')
                            sig = row['Signal']
                            var_pct = row['Period_Return'] * 100.0
                            
                            if sig == 'UP':
                                alloc = capital
                                gross_profit = capital * row['Period_Return']
                                tax = gross_profit * 0.26 if gross_profit > 0 else 0.0
                                net_profit = gross_profit - tax
                                capital += net_profit
                                total_taxes += tax
                            else:
                                alloc = 0.0
                                net_profit = 0.0
                                tax = 0.0
                                
                            cap_history.append(capital)
                            tx_log.append({
                                "Data": date_str, "Segnale AI": sig, "Allocazione (€)": f"{alloc:,.2f} €",
                                "Variazione (%)": f"{var_pct:+.2f}%", "Utile Netto (€)": f"{net_profit:+,.2f} €",
                                "Tasse 26% (€)": f"{tax:,.2f} €", "Capitale Finale (€)": f"{capital:,.2f} €"
                            })
                            
                        df_res['Portfolio_Value'] = cap_history
                        final_val = cap_history[-1] if cap_history else init_cap
                        tot_ret = ((final_val - init_cap) / init_cap) * 100.0
                        net_gain = final_val - init_cap
                        
                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            render_kpi_card("Capitale Iniziale", f"{init_cap:,.2f} €", f"Asset: {sel_asset}", "neutral", "🏦")
                        with b2:
                            render_kpi_card("Valore Finale Portafoglio", f"{final_val:,.2f} €", f"Performance: {tot_ret:+.2f}%", "up" if tot_ret >= 0 else "down", "💎")
                        with b3:
                            render_kpi_card("Utile Netto Totale", f"{net_gain:+,.2f} €", "Post-tassazione 26%", "up" if net_gain >= 0 else "down", "📈")
                        with b4:
                            render_kpi_card("Tasse Pagate (26%)", f"{total_taxes:,.2f} €", f"{len(tx_log)} Periodi Analizzati", "neutral", "🧾")
                        
                        st.write("")
                        df_plot = pd.DataFrame({'Date': df_res.index, 'Close': df_res['Portfolio_Value']})
                        fig_t = build_pro_chart(df_plot, f"Equity Line Strategia AI (UP/DOWN) — {sel_asset}", is_log=False)
                        st.plotly_chart(fig_t, use_container_width=True)
                        
                        render_section_header("📋 Registro Dettagliato delle Transazioni", sel_asset)
                        st.dataframe(pd.DataFrame(tx_log), use_container_width=True, hide_index=True)
                    else:
                        st.warning("Dati insufficienti per l'intervallo selezionato.")
            except Exception as e:
                st.error(f"Errore durante l'esecuzione del backtest: {e}")

# =============================================================================
# TAB 4: CRYPTO (BTC & ETH)
# =============================================================================
with tab_crypto:
    render_section_header("₿ Terminale Quantitativo Crypto Asset (Timeframe Settimanale)", "Foglio: Tecnica Crypto S")

    p_btc, pred_btc, df_b = get_official_crypto_indicators("BTC")
    p_eth, pred_eth, df_e = get_official_crypto_indicators("ETH")

    col_btc, col_eth = st.columns(2)
    with col_btc:
        render_kpi_card(
            "🟡 BITCOIN (BTC / USD)",
            f"${p_btc:,.2f}",
            f"Segnale Modello: {pred_btc}",
            "up" if str(pred_btc).upper() == "UP" else "down",
            "₿"
        )
        st.write("")
        if not df_b.empty:
            st.dataframe(df_b, use_container_width=True, hide_index=True)

    with col_eth:
        render_kpi_card(
            "🔷 ETHEREUM (ETH / USD)",
            f"${p_eth:,.2f}",
            f"Segnale Modello: {pred_eth}",
            "up" if str(pred_eth).upper() == "UP" else "down",
            "Ξ"
        )
        st.write("")
        if not df_e.empty:
            st.dataframe(df_e, use_container_width=True, hide_index=True)

    render_section_header("📈 Analisi Grafica Storica Settimanale Crypto", "Yahoo Finance 1W")

    cc1, cc2, cc3 = st.columns([2, 1.2, 1])
    sel_cr = cc1.selectbox("Seleziona Crypto per Grafico:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
    cr_type = cc2.radio("Visualizzazione:", ["Linea", "Candele (Candlestick)"], horizontal=True, key="cr_chart_type")
    cr_log = cc3.toggle("Scala Logaritmica", value=True, key="cr_log_scale")

    code_c = "BTC" if "BTC" in sel_cr else "ETH"
    df_c_chart = load_crypto_history_from_file(code_c)
    if df_c_chart is not None and not df_c_chart.empty:
        fig_cr = build_pro_chart(df_c_chart, f"Grafico Storico Settimanale — {sel_cr}", chart_type=cr_type, is_log=cr_log, add_sma=True)
        st.plotly_chart(fig_cr, use_container_width=True)
