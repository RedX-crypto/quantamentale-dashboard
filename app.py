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
                    "Paese": paese, "Prob_UP": prob, "Segnale": segnal, "Esito AI": f"{prob}% ({segnal})",
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
def build_pro_chart(df, title_name, chart_type="Linea", is_log=True):
    df_c = df.copy().dropna(subset=['Close'])
    fig = go.Figure()
    if chart_type == "Candele (Candlestick)" and 'Open' in df_c.columns:
        fig.add_trace(go.Candlestick(
            x=df_c['Date'], open=df_c['Open'], high=df_c['High'], low=df_c['Low'], close=df_c['Close'],
            name="Candele", increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_c['Date'], y=df_c['Close'], mode='lines', name="Chiusura",
            line=dict(color='#2962FF', width=2.5)
        ))
    fig.update_layout(
        title=dict(text=f"<b>{title_name}</b>", font=dict(size=16)),
        yaxis_title="Prezzo / Valore (€)", xaxis_title="Data", template="plotly_white", height=500,
        margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
        yaxis=dict(type="log" if is_log else "linear", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
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

# -----------------------------------------------------------------------------
# MODULO 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI (RIPRISTINATO)
# -----------------------------------------------------------------------------
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Previsioni (Dati da Excel Forecast)")
    st.dataframe(df_all[["Paese", "Esito AI", "Allocazione", "Voto_Macro"]], use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 Grafico Storico Avanzato ETF")
    
    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
    selected_country = col_sel1.selectbox("Seleziona ETF Paese:", df_all["Paese"].tolist())
    chart_type = col_sel2.radio("Tipo Grafico:", ["Linea", "Candele (Candlestick)"], horizontal=True)
    is_log = col_sel3.checkbox("Scala Logaritmica", value=True)
    
    horizon_etf = st.radio("Orizzonte:", ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], index=6, horizontal=True)
    
    row_country = df_all[df_all["Paese"] == selected_country].iloc[0]
    df_chart = load_etf_history_from_file(row_country["Sheet_ETF"], ticker=row_country["Ticker_YF"])
    
    if df_chart is not None and not df_chart.empty:
        df_filt, p_start, p_end, ret_pct = filter_by_horizon(df_chart, horizon_etf)
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Performance ({horizon_etf})", f"{ret_pct:+.2f}%", f"Prezzo finale: ${p_end:,.2f}")
        c2.metric("Esito AI", row_country['Esito AI'])
        c3.metric("Voto Macro", row_country['Voto_Macro'])
        
        fig_p = build_pro_chart(df_filt, f"Grafico Prezzi {selected_country} ({row_country['Ticker_YF']})", chart_type=chart_type, is_log=is_log)
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.warning("Dati storici non disponibili per questo ETF.")

# -----------------------------------------------------------------------------
# MODULO 2: CORRELAZIONE ETF
# -----------------------------------------------------------------------------
elif modulo == "🔄 Correlazione ETF":
    st.subheader("🔄 Calcolatore di Correlazione tra 2 ETF")
    col1, col2 = st.columns(2)
    e1 = col1.selectbox("Primo ETF:", df_all["Paese"].tolist(), index=0)
    e2 = col2.selectbox("Secondo ETF:", df_all["Paese"].tolist(), index=1)
    if e1 != e2:
        r1 = df_all[df_all["Paese"] == e1].iloc[0]
        r2 = df_all[df_all["Paese"] == e2].iloc[0]
        df1 = load_etf_history_from_file(r1["Sheet_ETF"], ticker=r1["Ticker_YF"])
        df2 = load_etf_history_from_file(r2["Sheet_ETF"], ticker=r2["Ticker_YF"])
        if df1 is not None and df2 is not None:
            merged = pd.merge(df1[['Date', 'Close']], df2[['Date', 'Close']], on='Date', suffixes=('_1', '_2')).dropna()
            corr = merged['Close_1'].pct_change().corr(merged['Close_2'].pct_change())
            st.metric("Coefficiente di Correlazione", f"{corr:.2f}")

# -----------------------------------------------------------------------------
# MODULO 3: BACKTEST & REGISTRO TRANSAZIONI (DINAMICO STORICO)
# -----------------------------------------------------------------------------
elif modulo == "⏳ Simulatore di Backtest & Registro Transazioni":
    st.subheader("⏳ Backtest Strategia AI con Segnali Storici Mensili & Tassazione 26%")
    st.write("Simula l'operatività valutando mese per mese i segnali dinamici di trend (UP/DOWN), con reinvestimento e tasse al 26% sugli utili.")
    
    col_s1, col_s2 = st.columns(2)
    init_cap = col_s1.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    all_assets = df_all["Paese"].tolist() + ["Bitcoin (BTC)", "Ethereum (ETH)"]
    sel_asset = col_s2.selectbox("Seleziona Asset per Backtest:", all_assets, index=2)
    
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    if st.button("🚀 Esegui Backtest e Registro Transazioni"):
        with st.spinner("Elaborazione backtest storico in corso..."):
            try:
                is_crypto = sel_asset in ["Bitcoin (BTC)", "Ethereum (ETH)"]
                if is_crypto:
                    df_sim = load_crypto_history_from_file("BTC" if "BTC" in sel_asset else "ETH")
                else:
                    row_a = df_all[df_all["Paese"] == sel_asset].iloc[0]
                    df_sim = load_etf_history_from_file(row_a["Sheet_ETF"], ticker=row_a["Ticker_YF"])
                
                if df_sim is not None and not df_sim.empty:
                    df_sim['Date'] = strip_timezone(df_sim['Date'])
                    mask = (df_sim['Date'] >= pd.to_datetime(d_start)) & (df_sim['Date'] <= pd.to_datetime(d_end))
                    df_sim = df_sim.loc[mask].sort_values('Date').set_index('Date')
                    
                    rule = 'W-MON' if is_crypto else 'ME'
                    df_res = df_sim.resample(rule).agg({'Close': 'last'}).dropna()
                    df_res['Period_Return'] = df_res['Close'].pct_change().fillna(0)
                    
                    # Segnale storico basato sul momentum del periodo precedente (evita look-ahead bias)
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
                            tax = gross_profit * 0.26 if gross_profit > 0 else 0.0
                            net_profit = gross_profit - tax
                            capital += net_profit
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
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                    c2.metric("Valore Finale Portafoglio", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                    c3.metric("Utile Netto Totale", f"{final_val - init_cap:+,.2f} €")
                    
                    st.markdown("---")
                    df_plot = pd.DataFrame({'Date': df_res.index, 'Close': df_res['Portfolio_Value']})
                    fig_t = build_pro_chart(df_plot, f"Backtest Strategia AI (UP/DOWN) — {sel_asset}")
                    st.plotly_chart(fig_t, use_container_width=True)
                    
                    st.markdown("### 📋 Registro Dettagliato delle Transazioni")
                    st.dataframe(pd.DataFrame(tx_log), use_container_width=True)
                else:
                    st.warning("Dati insufficienti per l'intervallo selezionato.")
            except Exception as e:
                st.error(f"Errore: {e}")

# -----------------------------------------------------------------------------
# MODULO 4: CRYPTO (GRAFICI RIPRISTINATI)
# -----------------------------------------------------------------------------
elif modulo == "₿ Crypto (BTC & ETH)":
    st.subheader("₿ Analisi Crypto & Grafici Storici")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟡 Bitcoin (BTC)")
        p_btc, pred_btc, df_b = get_official_crypto_indicators("BTC")
        st.metric("Prezzo", f"${p_btc:,.2f}")
        if not df_b.empty: st.dataframe(df_b, use_container_width=True)
    with col2:
        st.markdown("### 🔷 Ethereum (ETH)")
        p_eth, pred_eth, df_e = get_official_crypto_indicators("ETH")
        st.metric("Prezzo", f"${p_eth:,.2f}")
        if not df_e.empty: st.dataframe(df_e, use_container_width=True)
        
    st.markdown("---")
    sel_cr = st.selectbox("Seleziona Crypto per Grafico:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
    code_c = "BTC" if "BTC" in sel_cr else "ETH"
    df_c_chart = load_crypto_history_from_file(code_c)
    if df_c_chart is not None and not df_c_chart.empty:
        fig_cr = build_pro_chart(df_c_chart, f"Grafico Settimanale {sel_cr}")
        st.plotly_chart(fig_cr, use_container_width=True)
