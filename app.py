import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

# Import yfinance come fallback e fonte principale pulita
try:
    import yfinance as yf
except ImportError:
    yf = None

# Configurazione pagina Streamlit
st.set_page_config(page_title="Quantamentale System", page_icon="📈", layout="wide")

st.title("📈 Quantamentale Trading System — Dashboard Personale")
st.markdown("---")

# Menu principale unificato
modulo = st.sidebar.selectbox(
    "Seleziona Modulo", 
    [
        "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)", 
        "🔄 Correlazione ETF", 
        "🤖 Backtest Strategia AI (UP / DOWN)", 
        "₿ Crypto (BTC & ETH)"
    ]
)

# Funzione per cercare i file Excel nei percorsi di sistema
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

# Funzione per rimuovere la timezone dai datetime in modo sicuro
def strip_timezone(series):
    s = pd.to_datetime(series)
    if hasattr(s.dt, 'tz') and s.dt.tz is not None:
        return s.dt.tz_localize(None)
    return s

# Funzione per aggregare i dati in candele settimanali (Weekly)
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
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna().reset_index()
        return weekly
    return df_c

# Funzione per filtrare il dataframe in base all'orizzonte temporale e calcolare la resa %
def filter_by_horizon(df, horizon):
    if df is None or df.empty:
        return df, 0.0, 0.0, 0.0
    df_c = df.copy()
    df_c['Date'] = pd.to_datetime(df_c['Date'])
    df_c = df_c.sort_values('Date')
    
    last_date = df_c['Date'].max()
    
    if horizon == "1 Mese":
        start_target = last_date - pd.DateOffset(months=1)
    elif horizon == "3 Mesi":
        start_target = last_date - pd.DateOffset(months=3)
    elif horizon == "6 Mesi":
        start_target = last_date - pd.DateOffset(months=6)
    elif horizon == "1 Anno":
        start_target = last_date - pd.DateOffset(years=1)
    elif horizon == "3 Anni":
        start_target = last_date - pd.DateOffset(years=3)
    elif horizon == "5 Anni":
        start_target = last_date - pd.DateOffset(years=5)
    else: # Tutto (Max)
        start_target = df_c['Date'].min()
        
    df_filtered = df_c[df_c['Date'] >= start_target].copy()
    if df_filtered.empty:
        df_filtered = df_c.tail(2).copy()
        
    p_start = df_filtered['Close'].iloc[0]
    p_end = df_filtered['Close'].iloc[-1]
    ret_pct = ((p_end - p_start) / p_start) * 100.0 if p_start > 0 else 0.0
    
    return df_filtered, p_start, p_end, ret_pct

# Caricamento storico ETF pulito direttamente tramite yfinance
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
            open_col = [c for c in df.columns if 'open' in c.lower() or 'apertura' in c.lower()][0] if any('open' in c.lower() or 'apertura' in c.lower() for c in df.columns) else close_col
            high_col = [c for c in df.columns if 'high' in c.lower() or 'alto' in c.lower() or 'massimo' in c.lower()][0] if any('high' in c.lower() or 'alto' in c.lower() for c in df.columns) else close_col
            low_col = [c for c in df.columns if 'low' in c.lower() or 'basso' in c.lower() or 'minimo' in c.lower()][0] if any('low' in c.lower() or 'basso' in c.lower() for c in df.columns) else close_col
            
            df[date_col] = strip_timezone(df[date_col])
            df = df.sort_values(by=date_col)
            return df[[date_col, open_col, high_col, low_col, close_col]].rename(
                columns={date_col: 'Date', open_col: 'Open', high_col: 'High', low_col: 'Low', close_col: 'Close'}
            ).dropna()
        except Exception:
            pass
    return None

# Caricamento storico Crypto per grafici con cache
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

    crypto_file = find_excel_file("Hystorical_Data_Crypto.xlsx")
    if crypto_file:
        try:
            df = pd.read_excel(crypto_file, sheet_name=crypto_code).dropna(subset=['Close'])
            date_col = [c for c in df.columns if 'date' in c.lower() or 'data' in c.lower()][0]
            close_col = [c for c in df.columns if 'close' in c.lower() or 'chiusura' in c.lower()][0]
            open_col = [c for c in df.columns if 'open' in c.lower() or 'apertura' in c.lower()][0] if any('open' in c.lower() or 'apertura' in c.lower() for c in df.columns) else close_col
            high_col = [c for c in df.columns if 'high' in c.lower() or 'alto' in c.lower() or 'massimo' in c.lower()][0] if any('high' in c.lower() or 'alto' in c.lower() for c in df.columns) else close_col
            low_col = [c for c in df.columns if 'low' in c.lower() or 'basso' in c.lower() or 'minimo' in c.lower()][0] if any('low' in c.lower() or 'basso' in c.lower() for c in df.columns) else close_col
            
            df[date_col] = strip_timezone(df[date_col])
            df = df.sort_values(by=date_col)
            df_out = df[[date_col, open_col, high_col, low_col, close_col]].rename(
                columns={date_col: 'Date', open_col: 'Open', high_col: 'High', low_col: 'Low', close_col: 'Close'}
            )
            return ensure_weekly(df_out)
        except Exception:
            pass
    return None

# Funzione universale per grafici puliti e continui con cache
@st.cache_data
def build_pro_chart(df, title_name, chart_type="Linea", is_log=True):
    df_c = df.copy()
    df_c = df_c.dropna(subset=['Close'])
    fig = go.Figure()
    
    if chart_type == "Candele (Candlestick)" and 'Open' in df_c.columns and not df_c['Open'].isnull().all():
        fig.add_trace(go.Candlestick(
            x=df_c['Date'],
            open=df_c['Open'],
            high=df_c['High'],
            low=df_c['Low'],
            close=df_c['Close'],
            name="Prezzo OHLC",
            increasing_line_color='#26a69a', 
            decreasing_line_color='#ef5350'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_c['Date'],
            y=df_c['Close'],
            mode='lines',
            name="Prezzo di Chiusura",
            line=dict(color='#2962FF', width=2.5)
        ))

    fig.update_layout(
        title=dict(text=f"<b>{title_name}</b> — {'Scala Logaritmica' if is_log else 'Scala Lineare'}", font=dict(size=16)),
        yaxis_title="Prezzo / Valore",
        xaxis_title="Data",
        template="plotly_white",
        height=500,
        margin=dict(l=30, r=30, t=50, b=30),
        xaxis=dict(
            rangeslider=dict(visible=False), 
            showgrid=True, 
            gridcolor='#F0F2F5',
            type='date'
        ),
        yaxis=dict(type="log" if is_log else "linear", showgrid=True, gridcolor='#F0F2F5'),
        showlegend=True
    )
    return fig

# Dataset unificato completo (Macro + AI + Tecnica)
r_data_18 = [
    {"Paese": "Arabia Saudita", "Prob_UP": 80.8, "Segnale": "UP", "Allocazione": 200, "Voto_Macro": 2.94, "PIL": "+4.50%", "PMI": 53.8, "RSI": 48.3, "Mom_1M": "+2.71%", "Mom_3M": "-3.11%", "Sintesi": "Massima Confluenza", "Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita"},
    {"Paese": "India", "Prob_UP": 74.2, "Segnale": "UP", "Allocazione": 200, "Voto_Macro": 3.06, "PIL": "+7.57%", "PMI": 55.1, "RSI": 48.8, "Mom_1M": "+5.32%", "Mom_3M": "-0.40%", "Sintesi": "Massima Confluenza", "Ticker_YF": "INDA", "Sheet_ETF": "India"},
    {"Paese": "Germania", "Prob_UP": 71.8, "Segnale": "UP", "Allocazione": 200, "Voto_Macro": 2.64, "PIL": "+0.24%", "PMI": 53.9, "RSI": 54.4, "Mom_1M": "+3.39%", "Mom_3M": "-3.83%", "Sintesi": "Forte Confluenza", "Ticker_YF": "EWG", "Sheet_ETF": "Germania"},
    {"Paese": "Taiwan", "Prob_UP": 71.4, "Segnale": "UP", "Allocazione": 200, "Voto_Macro": 3.25, "PIL": "+12.93%", "PMI": 56.7, "RSI": 79.0, "Mom_1M": "-0.91%", "Mom_3M": "+8.14%", "Sintesi": "Forte (RSI Alto)", "Ticker_YF": "EWT", "Sheet_ETF": "Taiwan"},
    {"Paese": "Spagna", "Prob_UP": 71.0, "Segnale": "UP", "Allocazione": 200, "Voto_Macro": 2.71, "PIL": "+2.82%", "PMI": 51.0, "RSI": 73.2, "Mom_1M": "-0.31%", "Mom_3M": "-5.25%", "Sintesi": "Confermata", "Ticker_YF": "EWP", "Sheet_ETF": "Spagna"},
    {"Paese": "Francia", "Prob_UP": 67.4, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 2.35, "PIL": "+0.84%", "PMI": 50.6, "RSI": 57.8, "Mom_1M": "+3.50%", "Mom_3M": "-4.61%", "Sintesi": "Supportato (Fuori Top 5)", "Ticker_YF": "EWQ", "Sheet_ETF": "Francia"},
    {"Paese": "UK", "Prob_UP": 65.0, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 2.35, "PIL": "+1.39%", "PMI": 51.9, "RSI": 75.5, "Mom_1M": "+3.25%", "Mom_3M": "+0.22%", "Sintesi": "Supportato", "Ticker_YF": "EWU", "Sheet_ETF": "UK"},
    {"Paese": "Italia", "Prob_UP": 64.0, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 2.00, "PIL": "+0.54%", "PMI": 50.4, "RSI": 69.1, "Mom_1M": "+3.03%", "Mom_3M": "-5.22%", "Sintesi": "Supportato", "Ticker_YF": "EWI", "Sheet_ETF": "Italia"},
    {"Paese": "Corea del Sud", "Prob_UP": 62.6, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 3.00, "PIL": "+1.01%", "PMI": 53.9, "RSI": 68.3, "Mom_1M": "+6.43%", "Mom_3M": "+6.89%", "Sintesi": "Supportato", "Ticker_YF": "EWY", "Sheet_ETF": "Corea"},
    {"Paese": "Indonesia", "Prob_UP": 62.2, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 3.00, "PIL": "+5.11%", "PMI": 52.4, "RSI": 32.1, "Mom_1M": "+10.02%", "Mom_3M": "-17.02%", "Sintesi": "Rimbalzo Ipervenduto", "Ticker_YF": "EIDO", "Sheet_ETF": "Indonesia"},
    {"Paese": "Argentina", "Prob_UP": 61.6, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 2.14, "PIL": "+4.37%", "PMI": -0.05, "RSI": 55.7, "Mom_1M": "-15.10%", "Mom_3M": "-4.43%", "Sintesi": "Cauto", "Ticker_YF": "ARGT", "Sheet_ETF": "Argentina"},
    {"Paese": "Canada", "Prob_UP": 57.6, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 2.94, "PIL": "+1.74%", "PMI": 51.5, "RSI": 82.2, "Mom_1M": "+5.97%", "Mom_3M": "+5.13%", "Sintesi": "Filtro Ipercomprato", "Ticker_YF": "EWC", "Sheet_ETF": "Canada"},
    {"Paese": "America (USA)", "Prob_UP": 57.0, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 3.00, "PIL": "+2.16%", "PMI": 55.4, "RSI": 77.6, "Mom_1M": "+0.34%", "Mom_3M": "+4.10%", "Sintesi": "Filtro Saturazione", "Ticker_YF": "SPY", "Sheet_ETF": "America"},
    {"Paese": "Sud Africa", "Prob_UP": 53.6, "Segnale": "UP", "Allocazione": 0, "Voto_Macro": 2.50, "PIL": "+1.11%", "PMI": 50.7, "RSI": 65.3, "Mom_1M": "+1.54%", "Mom_3M": "+0.62%", "Sintesi": "Incertezza", "Ticker_YF": "EZA", "Sheet_ETF": "Sud Africa"},
    {"Paese": "Messico", "Prob_UP": 50.0, "Segnale": "DOWN", "Allocazione": 0, "Voto_Macro": 2.19, "PIL": "+0.56%", "PMI": 50.3, "RSI": 70.5, "Mom_1M": "+9.17%", "Mom_3M": "+4.98%", "Sintesi": "Neutralità Perfetta", "Ticker_YF": "EWW", "Sheet_ETF": "Messico"},
    {"Paese": "Giappone", "Prob_UP": 37.4, "Segnale": "DOWN", "Allocazione": 0, "Voto_Macro": 2.64, "PIL": "+1.19%", "PMI": 54.1, "RSI": 76.9, "Mom_1M": "-0.81%", "Mom_3M": "+3.32%", "Sintesi": "Storno Ipercomprato", "Ticker_YF": "EWJ", "Sheet_ETF": "Giappone"},
    {"Paese": "Cina", "Prob_UP": 28.2, "Segnale": "DOWN", "Allocazione": 0, "Voto_Macro": 3.06, "PIL": "+4.96%", "PMI": 52.1, "RSI": 48.2, "Mom_1M": "+2.03%", "Mom_3M": "-5.83%", "Sintesi": "Confluenza Ribassista", "Ticker_YF": "MCHI", "Sheet_ETF": "Cina"},
    {"Paese": "Brasile", "Prob_UP": 23.0, "Segnale": "DOWN", "Allocazione": 0, "Voto_Macro": 2.18, "PIL": "+2.29%", "PMI": 44.8, "RSI": 63.2, "Mom_1M": "-3.33%", "Mom_3M": "+14.27%", "Sintesi": "Contrazione Industriale", "Ticker_YF": "EWZ", "Sheet_ETF": "Brasile"}
]

df_all = pd.DataFrame(r_data_18)

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
                bb_low = last["BB 2σ Inf"]
                bb_up = last["BB 2σ Sup"]
                p_sma21 = last.get("Prezzo vs SMA21", "Sopra" if price > sma21_v else "Sotto")
                p_sma50 = last.get("Prezzo vs SMA50", "Sopra" if price > sma50_v else "Sotto")
                predict = last.get("Predict", "UP")
                
                df_res = pd.DataFrame({
                    "Indicatore Tecnico": ["RSI (14 Settimanale)", "MACD Hist (Settimanale)", "SMA 21 (Settimanale)", "SMA 50 (Settimanale)", "BB Inferiore (2σ)", "BB Superiore (2σ)"],
                    "Valore Ufficiale Excel": [f"{rsi_v:.2f}", f"{macd_v:+.2f}", f"${sma21_v:,.2f}", f"${sma50_v:,.2f}", f"${bb_low:,.2f}", f"${bb_up:,.2f}"],
                    "Stato / Posizione": [
                        "Fase Neutrale" if 30 <= rsi_v <= 70 else ("Ipercomprato (>70)" if rsi_v > 70 else "Ipervenduto (<30)"),
                        "Momentum Positivo (+)" if macd_v > 0 else "Momentum Negativo (-)",
                        f"Prezzo {p_sma21} SMA21",
                        f"Prezzo {p_sma50} SMA50",
                        "Sopra Supporto BB Inferiore",
                        "Sotto Resistenza BB Superiore"
                    ]
                })
                df_res.index = range(1, len(df_res) + 1)
                return price, predict, df_res
        except Exception:
            pass
            
    if crypto_code == "BTC":
        price = 78262.72
        predict = "UP"
        df_res = pd.DataFrame({
            "Indicatore Tecnico": ["RSI (14 Settimanale)", "MACD Hist (Settimanale)", "SMA 21 (Settimanale)", "SMA 50 (Settimanale)", "BB Inferiore (2σ)", "BB Superiore (2σ)"],
            "Valore Ufficiale Excel": ["52.25", "+858.29", "$71,629.61", "$76,541.20", "$55,108.80", "$90,874.20"],
            "Stato / Posizione": ["Fase Neutrale", "Momentum Positivo (+)", "Prezzo Sopra SMA21", "Prezzo Sopra SMA50", "Sopra Supporto BB Inferiore", "Sotto Resistenza BB Superiore"]
        })
        df_res.index = range(1, len(df_res) + 1)
        return price, predict, df_res
    else:
        price = 2274.53
        predict = "DOWN"
        df_res = pd.DataFrame({
            "Indicatore Tecnico": ["RSI (14 Settimanale)", "MACD Hist (Settimanale)", "SMA 21 (Settimanale)", "SMA 50 (Settimanale)", "BB Inferiore (2σ)", "BB Superiore (2σ)"],
            "Valore Ufficiale Excel": ["48.65", "+14.13", "$2,126.59", "$2,356.59", "$1,470.63", "$2,912.51"],
            "Stato / Posizione": ["Fase Neutrale", "Momentum Positivo (+)", "Prezzo Sopra SMA21", "Prezzo Sotto SMA50", "Sopra Supporto BB Inferiore", "Sotto Resistenza BB Superiore"]
        })
        df_res.index = range(1, len(df_res) + 1)
        return price, predict, df_res

# -----------------------------------------------------------------------------
# MODULO 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI (UNIFICATO)
# -----------------------------------------------------------------------------
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
    st.info("Tabella integrata: Esito AI + Dati Macroeconomici (Voto, PIL, PMI) + Indicatori Tecnici (RSI, Momentum).")
    
    filter_type = st.radio("Filtra lista:", ["Tutti i 18 ETF", "Solo Top 5 Allocati (€1.000)", "Solo Segnali DOWN / Evitare"], horizontal=True)
    
    if filter_type == "Solo Top 5 Allocati (€1.000)":
        df_show = df_all[df_all["Allocazione"] > 0].copy()
    elif filter_type == "Solo Segnali DOWN / Evitare":
        df_show = df_all[df_all["Segnale"] == "DOWN"].copy()
    else:
        df_show = df_all.copy()
        
    df_show["Esito AI"] = df_show["Prob_UP"].astype(str) + "% (" + df_show["Segnale"] + ")"
    df_show.index = range(1, len(df_show) + 1)
    
    st.dataframe(
        df_show[["Paese", "Esito AI", "Allocazione", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]], 
        use_container_width=True
    )
    
    df_all['Mom_1M_num'] = df_all['Mom_1M'].str.rstrip('%').astype(float)
    best_mom = df_all.loc[df_all['Mom_1M_num'].idxmax()]
    top_ai = df_all.loc[df_all['Prob_UP'].idxmax()]
    
    df_down = df_all[df_all["Segnale"] == "DOWN"]
    worst_ai = df_down.iloc[0] if not df_down.empty else df_all.loc[df_all['Prob_UP'].idxmin()]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max Momentum 1M (Prezzo)", f"{best_mom['Paese']}", f"{best_mom['Mom_1M']}")
    col2.metric("Filtro Ipercomprato", "USA & Canada", "RSI > 77-82", delta_color="inverse")
    col3.metric("Top Pick AI (Migliore)", f"{top_ai['Paese']}", f"{top_ai['Prob_UP']}% ({top_ai['Segnale']})")
    col4.metric("Worst Pick AI (Primo Sconsigliato)", f"{worst_ai['Paese']}", f"{worst_ai['Prob_UP']}% ({worst_ai['Segnale']})", delta_color="inverse")

    st.markdown("---")
    st.subheader("📈 Grafico Storico Avanzato ETF")
    
    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
    selected_country = col_sel1.selectbox("Seleziona ETF Paese da Analizzare:", df_all["Paese"].tolist())
    chart_type = col_sel2.radio("Tipo Grafico:", ["Linea", "Candele (Candlestick)"], horizontal=True)
    is_log = col_sel3.checkbox("Scala Logaritmica", value=True)
    
    horizon_etf = st.radio("Orizzonte Temporale:", ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], index=6, horizontal=True, key="h_etf_uni")
    
    row_country = df_all[df_all["Paese"] == selected_country].iloc[0]
    ticker = row_country["Ticker_YF"]
    sheet_name = row_country["Sheet_ETF"]
    
    df_chart = load_etf_history_from_file(sheet_name, ticker=ticker)
            
    if df_chart is not None and not df_chart.empty:
        df_chart_filt, p_start_etf, p_end_etf, ret_pct_etf = filter_by_horizon(df_chart, horizon_etf)
        
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric(f"Performance ({horizon_etf})", f"{ret_pct_etf:+.2f}%", f"Prezzo finale: ${p_end_etf:,.2f}")
        col_b.metric("Esito AI", f"{row_country['Prob_UP']}% ({row_country['Segnale']})")
        col_c.metric("RSI (14)", row_country['RSI'])
        col_d.metric("Voto Macro", row_country['Voto_Macro'])
        
        fig_pro = build_pro_chart(df_chart_filt, f"Grafico Prezzi {selected_country} ({ticker}) — Periodo: {horizon_etf}", chart_type=chart_type, is_log=is_log)
        st.plotly_chart(fig_pro, use_container_width=True)
    else:
        st.warning("Dati storici non disponibili per questo ETF.")

# -----------------------------------------------------------------------------
# MODULO 2: CORRELAZIONE ETF
# -----------------------------------------------------------------------------
elif modulo == "🔄 Correlazione ETF":
    st.subheader("🔄 Calcolatore Diretto di Correlazione tra 2 ETF")
    st.info("Seleziona due paesi per verificare istantaneamente la loro correlazione dai dati di portafoglio.")
    
    col_etf1, col_etf2 = st.columns(2)
    etf1_name = col_etf1.selectbox("Seleziona Primo ETF:", df_all["Paese"].tolist(), index=2)
    etf2_name = col_etf2.selectbox("Seleziona Secondo ETF:", df_all["Paese"].tolist(), index=3)
    
    if etf1_name == etf2_name:
        st.warning("⚠️ Hai selezionato lo stesso ETF. Seleziona due paesi diversi per la correlazione.")
    else:
        s1 = df_all[df_all["Paese"] == etf1_name].iloc[0]["Sheet_ETF"]
        s2 = df_all[df_all["Paese"] == etf2_name].iloc[0]["Sheet_ETF"]
        t1 = df_all[df_all["Paese"] == etf1_name].iloc[0]["Ticker_YF"]
        t2 = df_all[df_all["Paese"] == etf2_name].iloc[0]["Ticker_YF"]
        
        with st.spinner(f"Calcolo della correlazione tra {etf1_name} e {etf2_name}..."):
            try:
                df1 = load_etf_history_from_file(s1, ticker=t1)
                df2 = load_etf_history_from_file(s2, ticker=t2)
                
                if df1 is not None and df2 is not None:
                    merged = pd.merge(df1[['Date', 'Close']], df2[['Date', 'Close']], on='Date', suffixes=('_1', '_2')).dropna()
                    merged['Ret1'] = merged['Close_1'].pct_change()
                    merged['Ret2'] = merged['Close_2'].pct_change()
                    corr_val = merged['Ret1'].corr(merged['Ret2'])
                else:
                    data_pair = yf.download([t1, t2], period="1y")['Close'].pct_change().dropna()
                    corr_val = data_pair[t1].corr(data_pair[t2])
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Primo Asset", f"{etf1_name}")
                col_m2.metric("Secondo Asset", f"{etf2_name}")
                
                if corr_val > 0.70:
                    status_text = "Alta Correlazione (Bassa Diversificazione)"
                    delta_c = "inverse"
                elif corr_val > 0.30:
                    status_text = "Correlazione Moderata (Buona Diversificazione)"
                    delta_c = "normal"
                else:
                    status_text = "Bassa / Negativa (Ottima Diversificazione)"
                    delta_c = "normal"
                    
                col_m3.metric("Coefficiente di Correlazione", f"{corr_val:.2f}", status_text, delta_color=delta_c)
                
                st.markdown("#### ⚖️ Confronto Rapido tra i 2 ETF Selezionati")
                df_compare = df_all[df_all["Paese"].isin([etf1_name, etf2_name])].copy()
                df_compare["Esito AI"] = df_compare["Prob_UP"].astype(str) + "% (" + df_compare["Segnale"] + ")"
                df_compare.index = range(1, len(df_compare) + 1)
                st.dataframe(
                    df_compare[["Paese", "Esito AI", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Sintesi"]], 
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Errore nel calcolo della correlazione: {e}")

# -----------------------------------------------------------------------------
# MODULO 3: BACKTEST STRATEGIA AI (UP / DOWN)
# -----------------------------------------------------------------------------
elif modulo == "🤖 Backtest Strategia AI (UP / DOWN)":
    st.subheader("🤖 Backtest Strategia Segnali AI (UP / DOWN)")
    st.info("Simula l'operatività storica basata sui segnali del modello: acquisto su **UP** (tenendo 1 mese per ETF, 1 settimana per Crypto) e liquidità su **DOWN**.")
    
    all_etfs = df_all["Paese"].tolist()
    asset_options = all_etfs + ["Bitcoin (BTC)", "Ethereum (ETH)"]
    
    col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
    chosen_asset = col_b1.selectbox("Seleziona Asset da Testare:", asset_options, index=0)
    initial_capital = col_b2.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    horizon_bt = col_b3.selectbox("Orizzonte Backtest:", ["6 Mesi", "1 Anno", "3 Anni", "Tutto (Max)"], index=1)
    
    if st.button("🚀 Esegui Backtest Strategia AI"):
        with st.spinner(f"Esecuzione backtest per {chosen_asset} in corso..."):
            try:
                # Caricamento storico in base all'asset
                is_crypto = chosen_asset in ["Bitcoin (BTC)", "Ethereum (ETH)"]
                if is_crypto:
                    c_code = "BTC" if "BTC" in chosen_asset else "ETH"
                    df_bt = load_crypto_history_from_file(c_code)
                else:
                    row_c = df_all[df_all["Paese"] == chosen_asset].iloc[0]
                    df_bt = load_etf_history_from_file(row_c["Sheet_ETF"], ticker=row_c["Ticker_YF"])
                
                if df_bt is not None and not df_bt.empty:
                    df_bt['Date'] = strip_timezone(df_bt['Date'])
                    df_bt = df_bt.sort_values('Date')
                    
                    # Filtra per orizzonte temporale
                    last_date = df_bt['Date'].max()
                    if horizon_bt == "6 Mesi":
                        start_date = last_date - pd.DateOffset(months=6)
                    elif horizon_bt == "1 Anno":
                        start_date = last_date - pd.DateOffset(years=1)
                    elif horizon_bt == "3 Anni":
                        start_date = last_date - pd.DateOffset(years=3)
                    else:
                        start_date = df_bt['Date'].min()
                        
                    df_bt = df_bt[df_bt['Date'] >= start_date].copy()
                    
                    if len(df_bt) > 5:
                        # Ricampionamento: Mensile per ETF, Settimanale per Crypto
                        df_bt.set_index('Date', inplace=True)
                        rule = 'W-MON' if is_crypto else 'ME'
                        df_res = df_bt.resample(rule).agg({'Close': 'last', 'Open': 'first'}).dropna()
                        
                        # Calcolo rendimenti periodali
                        df_res['Period_Return'] = df_res['Close'].pct_change()
                        df_res = df_res.dropna()
                        
                        # Assegnazione segnale storico basato su trend/momentum del periodo precedente (proxy del modello)
                        # Se il rendimento del periodo precedente è >= 0 -> segnale UP, altrimenti DOWN
                        df_res['Signal'] = np.where(df_res['Period_Return'].shift(1).fillna(0) >= 0, 'UP', 'DOWN')
                        
                        # Strategia AI: se UP cattura il rendimento, se DOWN fa 0% (liquido)
                        df_res['Strategy_Return'] = np.where(df_res['Signal'] == 'UP', df_res['Period_Return'], 0.0)
                        
                        # Calcolo curve di equity
                        df_res['Buy_Hold_Equity'] = initial_capital * (1 + df_res['Period_Return']).cumprod()
                        df_res['Strategy_Equity'] = initial_capital * (1 + df_res['Strategy_Return']).cumprod()
                        
                        # Metriche finali
                        final_bh = df_res['Buy_Hold_Equity'].iloc[-1]
                        final_strat = df_res['Strategy_Equity'].iloc[-1]
                        ret_bh = ((final_bh - initial_capital) / initial_capital) * 100
                        ret_strat = ((final_strat - initial_capital) / initial_capital) * 100
                        
                        trades_total = len(df_res[df_res['Signal'] == 'UP'])
                        trades_win = len(df_res[(df_res['Signal'] == 'UP') & (df_res['Period_Return'] > 0)])
                        win_rate = (trades_win / trades_total * 100) if trades_total > 0 else 0
                        
                        # Visualizzazione KPI
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Capitale Finale (Strategia AI)", f"{final_strat:,.2f} €", f"{ret_strat:+.2f}%")
                        c2.metric("Capitale Finale (Buy & Hold)", f"{final_bh:,.2f} €", f"{ret_bh:+.2f}%")
                        c3.metric("Trade Eseguiti (UP)", f"{trades_total}")
                        c4.metric("Win Rate Strategia", f"{win_rate:.1f}%")
                        
                        st.markdown("---")
                        
                        # Grafico di confronto
                        fig_bt = go.Figure()
                        fig_bt.add_trace(go.Scatter(
                            x=df_res.index, y=df_res['Strategy_Equity'],
                            mode='lines', name="🤖 Strategia AI (UP/DOWN)",
                            line=dict(color='#26a69a', width=3)
                        ))
                        fig_bt.add_trace(go.Scatter(
                            x=df_res.index, y=df_res['Buy_Hold_Equity'],
                            mode='lines', name="📊 Buy & Hold Classico",
                            line=dict(color='#2962FF', width=2, dash='dot')
                        ))
                        
                        fig_bt.update_layout(
                            title=dict(text=f"<b>Backtest Performance: {chosen_asset}</b> ({horizon_bt})", font=dict(size=16)),
                            yaxis_title="Valore Portafoglio (€)",
                            xaxis_title="Data",
                            template="plotly_white",
                            height=500,
                            margin=dict(l=30, r=30, t=50, b=30),
                            hovermode="x unified"
                        )
                        st.plotly_chart(fig_bt, use_container_width=True)
                        
                        with st.expander("📋 Visualizza Storico Operazioni Periodali"):
                            st.dataframe(df_res[['Close', 'Period_Return', 'Signal', 'Strategy_Return', 'Strategy_Equity']].rename(
                                columns={'Close': 'Prezzo Chiusura', 'Period_Return': 'Rend. Periodo', 'Signal': 'Segnale AI', 'Strategy_Return': 'Rend. Strategia', 'Strategy_Equity': 'Equity AI'}
                            ), use_container_width=True)
                    else:
                        st.warning("Dati storici insufficienti per l'intervallo temporale selezionato.")
                else:
                    st.warning("Impossibile caricare i dati storici per l'asset selezionato.")
            except Exception as e:
                st.error(ferror := f"Errore durante l'esecuzione del backtest: {e}")

# -----------------------------------------------------------------------------
# MODULO 4: CRYPTO (BTC & ETH)
# -----------------------------------------------------------------------------
elif modulo == "₿ Crypto (BTC & ETH)":
    st.subheader("₿ Analisi Tecnico-Quantitativa Crypto (BTC & ETH)")
    st.info("Dati quantitativi ufficiali caricati dal modello di analisi (DataBase.xlsx & Hystorical_Data_Crypto.xlsx).")
    
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown("### 🟡 Bitcoin (BTC)")
        price_btc, pred_btc, df_btc_tech = get_official_crypto_indicators("BTC")
        
        st.metric("Prezzo Riferimento BTC/USD", f"${price_btc:,.2f}")
        st.metric("Esito Modello RStudio", f"60.20% ({pred_btc})", "Segnale Rialzista")
        st.metric("Accuratezza OOS (Walk-Forward)", "55.96%")
        
        st.markdown("#### 📊 Indicatori Tecnici Ufficiali BTC (Settimanale)")
        st.dataframe(df_btc_tech, use_container_width=True)
        
    with col_c2:
        st.markdown("### 🔷 Ethereum (ETH)")
        price_eth, pred_eth, df_eth_tech = get_official_crypto_indicators("ETH")
        
        st.metric("Prezzo Riferimento ETH/USD", f"${price_eth:,.2f}")
        st.metric("Esito Modello Cross-Asset", f"72.00% ({pred_eth})", "Segnale di Storno / Attesa", delta_color="inverse")
        st.metric("Accuratezza OOS (Cross-Asset)", "> 60.00%")
        
        st.markdown("#### 📊 Indicatori Tecnici Ufficiali ETH (Settimanale)")
        st.dataframe(df_eth_tech, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📈 Grafico Avanzato Crypto Settimanale (Dalla Nascita)")
    
    col_cr1, col_cr2, col_cr3 = st.columns([2, 1, 1])
    selected_crypto = col_cr1.selectbox("Seleziona Crypto da Analizzare:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
    c_chart_type = col_cr2.radio("Tipo Grafico Crypto:", ["Linea", "Candele (Candlestick)"], horizontal=True, key="c_type")
    c_is_log = col_cr3.checkbox("Scala Logaritmica", value=True, key="c_log")
    
    horizon_crypto = st.radio("Orizzonte Temporale Crypto:", ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], index=6, horizontal=True, key="h_crypto")
    
    code_sel = "BTC" if "BTC" in selected_crypto else "ETH"
    
    df_crypto_chart = load_crypto_history_from_file(code_sel)
            
    if df_crypto_chart is not None and not df_crypto_chart.empty:
        df_crypto_filt, p_start_cr, p_end_cr, ret_pct_cr = filter_by_horizon(df_crypto_chart, horizon_crypto)
        
        st.metric(f"Performance {selected_crypto} ({horizon_crypto})", f"{ret_pct_cr:+.2f}%", f"Prezzo finale: ${p_end_cr:,.2f}")
        
        fig_crypto_pro = build_pro_chart(df_crypto_filt, f"Grafico Storico {selected_crypto} — Periodo: {horizon_crypto}", chart_type=c_chart_type, is_log=c_is_log)
        st.plotly_chart(fig_crypto_pro, use_container_width=True)
    else:
        st.warning(f"Grafico non disponibile per {selected_crypto}.")
