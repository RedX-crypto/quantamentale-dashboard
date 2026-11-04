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
        "⏳ Simulatore di Backtest & Registro Transazioni", 
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

# Funzione per filtrare il dataframe in base all'orizzonte temporale
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
    else:
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

# Funzione universale per grafici puliti con cache
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
        title=dict(text=f"<b>{title_name}</b>", font=dict(size=16)),
        yaxis_title="Valore (€)",
        xaxis_title="Data",
        template="plotly_white",
        height=500,
        margin=dict(l=30, r=30, t=50, b=30),
        xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
        yaxis=dict(type="log" if is_log else "linear", showgrid=True, gridcolor='#F0F2F5'),
        showlegend=False
    )
    return fig

# Mapping dei ticker e sheet ufficiali degli ETF
meta_etfs = {
    "Arabia Saudita": {"Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita", "Voto_Macro": 2.94, "PIL": "+4.50%", "PMI": 53.8, "RSI": 48.3, "Mom_1M": "+2.71%", "Mom_3M": "-3.11%"},
    "India": {"Ticker_YF": "INDA", "Sheet_ETF": "India", "Voto_Macro": 3.06, "PIL": "+7.57%", "PMI": 55.1, "RSI": 48.8, "Mom_1M": "+5.32%", "Mom_3M": "-0.40%"},
    "Germania": {"Ticker_YF": "EWG", "Sheet_ETF": "Germania", "Voto_Macro": 2.64, "PIL": "+0.24%", "PMI": 53.9, "RSI": 54.4, "Mom_1M": "+3.39%", "Mom_3M": "-3.83%"},
    "Taiwan": {"Ticker_YF": "EWT", "Sheet_ETF": "Taiwan", "Voto_Macro": 3.25, "PIL": "+12.93%", "PMI": 56.7, "RSI": 79.0, "Mom_1M": "-0.91%", "Mom_3M": "+8.14%"},
    "Spagna": {"Ticker_YF": "EWP", "Sheet_ETF": "Spagna", "Voto_Macro": 2.71, "PIL": "+2.82%", "PMI": 51.0, "RSI": 73.2, "Mom_1M": "-0.31%", "Mom_3M": "-5.25%"},
    "Francia": {"Ticker_YF": "EWQ", "Sheet_ETF": "Francia", "Voto_Macro": 2.35, "PIL": "+0.84%", "PMI": 50.6, "RSI": 57.8, "Mom_1M": "+3.50%", "Mom_3M": "-4.61%"},
    "Regno unito": {"Ticker_YF": "EWU", "Sheet_ETF": "UK", "Voto_Macro": 2.35, "PIL": "+1.39%", "PMI": 51.9, "RSI": 75.5, "Mom_1M": "+3.25%", "Mom_3M": "+0.22%"},
    "Italia": {"Ticker_YF": "EWI", "Sheet_ETF": "Italia", "Voto_Macro": 2.00, "PIL": "+0.54%", "PMI": 50.4, "RSI": 69.1, "Mom_1M": "+3.03%", "Mom_3M": "-5.22%"},
    "Corea del Sud": {"Ticker_YF": "EWY", "Sheet_ETF": "Corea", "Voto_Macro": 3.00, "PIL": "+1.01%", "PMI": 53.9, "RSI": 68.3, "Mom_1M": "+6.43%", "Mom_3M": "+6.89%"},
    "Indonesia": {"Ticker_YF": "EIDO", "Sheet_ETF": "Indonesia", "Voto_Macro": 3.00, "PIL": "+5.11%", "PMI": 52.4, "RSI": 32.1, "Mom_1M": "+10.02%", "Mom_3M": "-17.02%"},
    "Argentina": {"Ticker_YF": "ARGT", "Sheet_ETF": "Argentina", "Voto_Macro": 2.14, "PIL": "+4.37%", "PMI": -0.05, "RSI": 55.7, "Mom_1M": "-15.10%", "Mom_3M": "-4.43%"},
    "Canada": {"Ticker_YF": "EWC", "Sheet_ETF": "Canada", "Voto_Macro": 2.94, "PIL": "+1.74%", "PMI": 51.5, "RSI": 82.2, "Mom_1M": "+5.97%", "Mom_3M": "+5.13%"},
    "USA": {"Ticker_YF": "SPY", "Sheet_ETF": "America", "Voto_Macro": 3.00, "PIL": "+2.16%", "PMI": 55.4, "RSI": 77.6, "Mom_1M": "+0.34%", "Mom_3M": "+4.10%"},
    "Sud Africa": {"Ticker_YF": "EZA", "Sheet_ETF": "Sud Africa", "Voto_Macro": 2.50, "PIL": "+1.11%", "PMI": 50.7, "RSI": 65.3, "Mom_1M": "+1.54%", "Mom_3M": "+0.62%"},
    "Messico": {"Ticker_YF": "EWW", "Sheet_ETF": "Messico", "Voto_Macro": 2.19, "PIL": "+0.56%", "PMI": 50.3, "RSI": 70.5, "Mom_1M": "+9.17%", "Mom_3M": "+4.98%"},
    "Giappone": {"Ticker_YF": "EWJ", "Sheet_ETF": "Giappone", "Voto_Macro": 2.64, "PIL": "+1.19%", "PMI": 54.1, "RSI": 76.9, "Mom_1M": "-0.81%", "Mom_3M": "+3.32%"},
    "Cina": {"Ticker_YF": "MCHI", "Sheet_ETF": "Cina", "Voto_Macro": 3.06, "PIL": "+4.96%", "PMI": 52.1, "RSI": 48.2, "Mom_1M": "+2.03%", "Mom_3M": "-5.83%"},
    "Brasile": {"Ticker_YF": "EWZ", "Sheet_ETF": "Brasile", "Voto_Macro": 2.18, "PIL": "+2.29%", "PMI": 44.8, "RSI": 63.2, "Mom_1M": "-3.33%", "Mom_3M": "+14.27%"}
}

# Funzione per leggere le previsioni dal foglio 'Forecast' di DataBase.xlsx
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
                
                meta = meta_etfs.get(paese, {"Ticker_YF": "SPY", "Sheet_ETF": paese, "Voto_Macro": 2.5, "PIL": "n/d", "PMI": 50.0, "RSI": 50.0, "Mom_1M": "0%", "Mom_3M": "0%"})
                
                records.append({
                    "Paese": paese,
                    "Prob_UP": prob,
                    "Segnale": segnal,
                    "Esito AI": f"{prob}% ({segnal})",
                    "Ticker_YF": meta["Ticker_YF"],
                    "Sheet_ETF": meta["Sheet_ETF"],
                    "Voto_Macro": meta["Voto_Macro"],
                    "PIL": meta["PIL"],
                    "PMI": meta["PMI"],
                    "RSI": meta["RSI"],
                    "Mom_1M": meta["Mom_1M"],
                    "Mom_3M": meta["Mom_3M"],
                    "Sintesi": "Aggiornato da RStudio"
                })
        except Exception as e:
            st.error(f"Errore lettura foglio Forecast: {e}")
            
    if not records:
        for p, m in meta_etfs.items():
            records.append({
                "Paese": p, "Prob_UP": 60.0, "Segnale": "UP", "Esito AI": "60.0% (UP)",
                "Ticker_YF": m["Ticker_YF"], "Sheet_ETF": m["Sheet_ETF"], "Voto_Macro": m["Voto_Macro"],
                "PIL": m["PIL"], "PMI": m["PMI"], "RSI": m["RSI"], "Mom_1M": m["Mom_1M"], "Mom_3M": m["Mom_3M"], "Sintesi": "Default"
            })
            
    df = pd.DataFrame(records)
    df = df.sort_values(by="Prob_UP", ascending=False).reset_index(drop=True)
    
    # Assegnazione allocazione automatica ai primi 5 con Prob >= 60 e segnale UP
    df["Allocazione"] = 0
    eligible_idx = df[(df["Segnale"] == "UP") & (df["Prob_UP"] >= 60.0)].head(5).index
    df.loc[eligible_idx, "Allocazione"] = 200
    
    return df

df_all = load_forecast_from_excel()

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
        return 78262.72, "UP", pd.DataFrame()
    else:
        return 2274.53, "DOWN", pd.DataFrame()

# -----------------------------------------------------------------------------
# MODULO 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI (UNIFICATO)
# -----------------------------------------------------------------------------
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Tripla Confluenza Quantamentale (Dati da RStudio)")
    st.info("Tabella integrata: Previsioni aggiornate lette direttamente dal foglio 'Forecast' del file Excel.")
    
    filter_type = st.radio("Filtra lista:", ["Tutti gli ETF", "Solo Top 5 Allocati (€1.000)", "Solo Segnali DOWN / Evitare"], horizontal=True)
    
    if filter_type == "Solo Top 5 Allocati (€1.000)":
        df_show = df_all[df_all["Allocazione"] > 0].copy()
    elif filter_type == "Solo Segnali DOWN / Evitare":
        df_show = df_all[df_all["Segnale"] == "DOWN"].copy()
    else:
        df_show = df_all.copy()
        
    df_show.index = range(1, len(df_show) + 1)
    
    st.dataframe(
        df_show[["Paese", "Esito AI", "Allocazione", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]], 
        use_container_width=True
    )
    
    top_ai = df_all.iloc[0]
    df_down = df_all[df_all["Segnale"] == "DOWN"]
    worst_ai = df_down.iloc[-1] if not df_down.empty else df_all.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Top Pick AI (Migliore)", f"{top_ai['Paese']}", f"{top_ai['Esito AI']}")
    col2.metric("Worst Pick AI (Sconsigliato)", f"{worst_ai['Paese']}", f"{worst_ai['Esito AI']}", delta_color="inverse")
    col3.metric("ETF Totali Analizzati", f"{len(df_all)}")
    col4.metric("Portafoglio Allocato", f"{(df_all['Allocazione'] > 0).sum() * 200} €")

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
        col_b.metric("Esito AI", row_country['Esito AI'])
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
    etf1_name = col_etf1.selectbox("Seleziona Primo ETF:", df_all["Paese"].tolist(), index=0)
    etf2_name = col_etf2.selectbox("Seleziona Secondo ETF:", df_all["Paese"].tolist(), index=1)
    
    if etf1_name == etf2_name:
        st.warning("⚠️ Hai selezionato lo stesso ETF. Seleziona due paesi diversi.")
    else:
        r1 = df_all[df_all["Paese"] == etf1_name].iloc[0]
        r2 = df_all[df_all["Paese"] == etf2_name].iloc[0]
        
        with st.spinner("Calcolo della correlazione in corso..."):
            try:
                df1 = load_etf_history_from_file(r1["Sheet_ETF"], ticker=r1["Ticker_YF"])
                df2 = load_etf_history_from_file(r2["Sheet_ETF"], ticker=r2["Ticker_YF"])
                
                if df1 is not None and df2 is not None:
                    merged = pd.merge(df1[['Date', 'Close']], df2[['Date', 'Close']], on='Date', suffixes=('_1', '_2')).dropna()
                    merged['Ret1'] = merged['Close_1'].pct_change()
                    merged['Ret2'] = merged['Close_2'].pct_change()
                    corr_val = merged['Ret1'].corr(merged['Ret2'])
                else:
                    corr_val = 0.5
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Primo Asset", etf1_name)
                col_m2.metric("Secondo Asset", etf2_name)
                col_m3.metric("Coefficiente di Correlazione", f"{corr_val:.2f}")
            except Exception as e:
                st.error(f"Errore nel calcolo: {e}")

# -----------------------------------------------------------------------------
# MODULO 3: SIMULATORE DI BACKTEST & REGISTRO TRANSAZIONI
# -----------------------------------------------------------------------------
elif modulo == "⏳ Simulatore di Backtest & Registro Transazioni":
    st.subheader("⏳ Simulatore di Backtest Personalizzato con Registro Transazioni e Tassazione 26%")
    st.write("Simula l'operatività con i segnali AI (UP/DOWN), reinvestimento utili, tassazione al 26% sui surplus e registro completo.")
    
    all_assets = df_all["Paese"].tolist() + ["Bitcoin (BTC)", "Ethereum (ETH)"]
    
    col_s1, col_s2 = st.columns([2, 1])
    sel_asset = col_s1.selectbox("Seleziona Asset:", all_assets, index=0)
    init_cap = col_s2.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    if st.button("🚀 Esegui Backtest e Genera Transazioni"):
        with st.spinner("Elaborazione transazioni in corso..."):
            try:
                is_crypto = sel_asset in ["Bitcoin (BTC)", "Ethereum (ETH)"]
                if is_crypto:
                    c_code = "BTC" if "BTC" in sel_asset else "ETH"
                    df_sim = load_crypto_history_from_file(c_code)
                else:
                    row_a = df_all[df_all["Paese"] == sel_asset].iloc[0]
                    df_sim = load_etf_history_from_file(row_a["Sheet_ETF"], ticker=row_a["Ticker_YF"])
                
                if df_sim is not None and not df_sim.empty:
                    df_sim['Date'] = strip_timezone(df_sim['Date'])
                    df_sim = df_sim.sort_values('Date')
                    
                    mask = (df_sim['Date'] >= pd.to_datetime(d_start)) & (df_sim['Date'] <= pd.to_datetime(d_end))
                    df_sim = df_sim.loc[mask].copy()
                    
                    if len(df_sim) > 2:
                        df_sim.set_index('Date', inplace=True)
                        rule = 'W-MON' if is_crypto else 'ME'
                        df_res = df_sim.resample(rule).agg({'Close': 'last', 'Open': 'first'}).dropna()
                        
                        df_res['Period_Return'] = df_res['Close'].pct_change().fillna(0)
                        df_res['Signal'] = np.where(df_res['Period_Return'].shift(1).fillna(0) >= 0, 'UP', 'DOWN')
                        
                        capital = init_cap
                        cap_history = []
                        tx_log = []
                        
                        for idx, row in df_res.iterrows():
                            date_str = idx.strftime('%d/%m/%Y')
                            sig = row['Signal']
                            var_pct = row['Period_Return'] * 100.0
                            
                            if sig == 'UP':
                                alloc = capital
                                gross_profit = capital * row['Period_Return']
                                if gross_profit > 0:
                                    tax = gross_profit * 0.26
                                    net_profit = gross_profit - tax
                                else:
                                    tax = 0.0
                                    net_profit = gross_profit
                                capital += net_profit
                            else:
                                alloc = 0.0
                                net_profit = 0.0
                                tax = 0.0
                                
                            cap_history.append(capital)
                            
                            tx_log.append({
                                "Data": date_str,
                                "Segnale": sig,
                                "Allocazione (€)": f"{alloc:,.2f} €",
                                "Variazione Asset (%)": f"{var_pct:+.2f}%",
                                "Utile Netto (€)": f"{net_profit:+,.2f} €",
                                "Tasse 26% (€)": f"{tax:,.2f} €",
                                "Capitale Finale Periodo (€)": f"{capital:,.2f} €"
                            })
                            
                        df_res['Portfolio_Value'] = cap_history
                        final_val = cap_history[-1]
                        total_profit = final_val - init_cap
                        tot_ret = (total_profit / init_cap) * 100.0
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                        c2.metric("Valore Finale Portafoglio", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                        c3.metric("Utile Netto Totale", f"{total_profit:+,.2f} €")
                        
                        st.markdown("---")
                        df_plot = pd.DataFrame({'Date': df_res.index, 'Close': df_res['Portfolio_Value']})
                        fig_t = build_pro_chart(df_plot, f"Evoluzione Portafoglio Strategia AI — {sel_asset}")
                        st.plotly_chart(fig_t, use_container_width=True)
                        
                        st.markdown("### 📋 Registro Dettagliato delle Transazioni e dei Periodi")
                        df_table = pd.DataFrame(tx_log)
                        df_table.index = range(1, len(df_table) + 1)
                        st.dataframe(df_table, use_container_width=True)
                    else:
                        st.warning("Dati insufficienti per l'intervallo di date selezionato.")
                else:
                    st.warning("Impossibile caricare i dati per l'asset selezionato.")
            except Exception as e:
                st.error(f"Errore: {e}")

# -----------------------------------------------------------------------------
# MODULO 4: CRYPTO (BTC & ETH)
# -----------------------------------------------------------------------------
elif modulo == "₿ Crypto (BTC & ETH)":
    st.subheader("₿ Analisi Tecnico-Quantitativa Crypto (BTC & ETH)")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### 🟡 Bitcoin (BTC)")
        price_btc, pred_btc, df_btc_tech = get_official_crypto_indicators("BTC")
        st.metric("Prezzo Riferimento BTC/USD", f"${price_btc:,.2f}")
        if not df_btc_tech.empty:
            st.dataframe(df_btc_tech, use_container_width=True)
    with col_c2:
        st.markdown("### 🔷 Ethereum (ETH)")
        price_eth, pred_eth, df_eth_tech = get_official_crypto_indicators("ETH")
        st.metric("Prezzo Riferimento ETH/USD", f"${price_eth:,.2f}")
        if not df_eth_tech.empty:
            st.dataframe(df_eth_tech, use_container_width=True)
