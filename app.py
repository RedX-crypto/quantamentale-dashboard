import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    
    fig.add_trace(go.Scatter(
        x=df_c['Date'],
        y=df_c['Close'],
        mode='lines',
        name="Valore Portafoglio",
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

# Dataset 18 ETF
r_data_18 = [
    {"Paese": "Arabia Saudita", "Prob_UP": 80.8, "Segnale": "UP", "Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita"},
    {"Paese": "India", "Prob_UP": 74.2, "Segnale": "UP", "Ticker_YF": "INDA", "Sheet_ETF": "India"},
    {"Paese": "Germania", "Prob_UP": 71.8, "Segnale": "UP", "Ticker_YF": "EWG", "Sheet_ETF": "Germania"},
    {"Paese": "Taiwan", "Prob_UP": 71.4, "Segnale": "UP", "Ticker_YF": "EWT", "Sheet_ETF": "Taiwan"},
    {"Paese": "Spagna", "Prob_UP": 71.0, "Segnale": "UP", "Ticker_YF": "EWP", "Sheet_ETF": "Spagna"},
    {"Paese": "Francia", "Prob_UP": 67.4, "Segnale": "UP", "Ticker_YF": "EWQ", "Sheet_ETF": "Francia"},
    {"Paese": "UK", "Prob_UP": 65.0, "Segnale": "UP", "Ticker_YF": "EWU", "Sheet_ETF": "UK"},
    {"Paese": "Italia", "Prob_UP": 64.0, "Segnale": "UP", "Ticker_YF": "EWI", "Sheet_ETF": "Italia"},
    {"Paese": "Corea del Sud", "Prob_UP": 62.6, "Segnale": "UP", "Ticker_YF": "EWY", "Sheet_ETF": "Corea"},
    {"Paese": "Indonesia", "Prob_UP": 62.2, "Segnale": "UP", "Ticker_YF": "EIDO", "Sheet_ETF": "Indonesia"},
    {"Paese": "Argentina", "Prob_UP": 61.6, "Segnale": "UP", "Ticker_YF": "ARGT", "Sheet_ETF": "Argentina"},
    {"Paese": "Canada", "Prob_UP": 57.6, "Segnale": "UP", "Ticker_YF": "EWC", "Sheet_ETF": "Canada"},
    {"Paese": "America (USA)", "Prob_UP": 57.0, "Segnale": "UP", "Ticker_YF": "SPY", "Sheet_ETF": "America"},
    {"Paese": "Sud Africa", "Prob_UP": 53.6, "Segnale": "UP", "Ticker_YF": "EZA", "Sheet_ETF": "Sud Africa"},
    {"Paese": "Messico", "Prob_UP": 50.0, "Segnale": "DOWN", "Ticker_YF": "EWW", "Sheet_ETF": "Messico"},
    {"Paese": "Giappone", "Prob_UP": 37.4, "Segnale": "DOWN", "Ticker_YF": "EWJ", "Sheet_ETF": "Giappone"},
    {"Paese": "Cina", "Prob_UP": 28.2, "Segnale": "DOWN", "Ticker_YF": "MCHI", "Sheet_ETF": "Cina"},
    {"Paese": "Brasile", "Prob_UP": 23.0, "Segnale": "DOWN", "Ticker_YF": "EWZ", "Sheet_ETF": "Brasile"}
]
df_all = pd.DataFrame(r_data_18)

# -----------------------------------------------------------------------------
# MODULI 1 & 2
# -----------------------------------------------------------------------------
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
    st.write("Seleziona i moduli dal menu laterale.")
elif modulo == "🔄 Correlazione ETF":
    st.subheader("🔄 Calcolatore di Correlazione")

# -----------------------------------------------------------------------------
# MODULO 3: SIMULATORE DI BACKTEST & REGISTRO TRANSAZIONI
# -----------------------------------------------------------------------------
elif modulo == "⏳ Simulatore di Backtest & Registro Transazioni":
    st.subheader("⏳ Simulatore di Backtest Personalizzato con Registro Transazioni e Tassazione 26%")
    st.write("Simula l'operatività con i segnali AI (UP/DOWN), reinvestimento utili, tassazione al 26% sui surplus e registro completo delle transazioni.")
    
    all_assets = df_all["Paese"].tolist() + ["Bitcoin (BTC)", "Ethereum (ETH)"]
    
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    sel_asset = col_s1.selectbox("Seleziona Asset:", all_assets, index=2)
    init_cap = col_s2.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    if st.button("🚀 Esegui Backtest e Genera Transazioni"):
        with st.spinner("Elaborazione transazioni e calcolo fiscale in corso..."):
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
                    
                    dt_start = pd.to_datetime(d_start)
                    dt_end = pd.to_datetime(d_end)
                    mask = (df_sim['Date'] >= dt_start) & (df_sim['Date'] <= dt_end)
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
                        st.info("In basso trovi lo storico di ogni transazione: se il segnale era **DOWN**, l'allocazione è stata 0 (liquidità protetta); se era **UP**, il capitale ha partecipato al mercato con reinvestimento e tassazione al 26% sugli utili.")
                        
                        df_table = pd.DataFrame(tx_log)
                        df_table.index = range(1, len(df_table) + 1)
                        st.dataframe(df_table, use_container_width=True)
                        
                    else:
                        st.warning("Dati insufficienti per l'intervallo di date selezionato.")
                else:
                    st.warning("Impossibile caricare i dati per l'asset selezionato.")
            except Exception as e:
                st.error(f"Errore durante l'esecuzione: {e}")

# -----------------------------------------------------------------------------
# MODULO 4: CRYPTO
# -----------------------------------------------------------------------------
elif modulo == "₿ Crypto (BTC & ETH)":
    st.subheader("₿ Analisi Crypto")
