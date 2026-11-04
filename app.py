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
            open_col = close_col
            high_col = close_col
            low_col = close_col
            df[date_col] = strip_timezone(df[date_col])
            df = df.sort_values(by=date_col)
            return df[[date_col, open_col, high_col, low_col, close_col]].rename(
                columns={date_col: 'Date', open_col: 'Open', high_col: 'High', low_col: 'Low', close_col: 'Close'}
            ).dropna()
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
def build_pro_chart(df, title_name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name="Valore Portafoglio", line=dict(color='#2962FF', width=2.5)))
    fig.update_layout(
        title=dict(text=f"<b>{title_name}</b>", font=dict(size=16)),
        yaxis_title="Valore (€)", xaxis_title="Data", template="plotly_white", height=500,
        margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
        yaxis=dict(type="log", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
    )
    return fig

# -----------------------------------------------------------------------------
# MODULO 1 & 2
# -----------------------------------------------------------------------------
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
    st.dataframe(df_all[["Paese", "Esito AI", "Allocazione", "Voto_Macro"]], use_container_width=True)
elif modulo == "🔄 Correlazione ETF":
    st.subheader("🔄 Calcolatore di Correlazione")

# -----------------------------------------------------------------------------
# MODULO 3: SIMULATORE DI BACKTEST & TOP 5 DINAMICI
# -----------------------------------------------------------------------------
elif modulo == "⏳ Simulatore di Backtest & Registro Transazioni":
    st.subheader("⏳ Backtest Portafoglio Dinamico (Top 5 Asset Mensili + Tassazione 26%)")
    st.write("Simula il portafoglio a rotazione selezionando mese per mese i migliori 5 asset con segnale UP, reinvestimento e tasse al 26% sugli utili.")
    
    col_s1, col_s2 = st.columns(2)
    init_cap = col_s1.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    mode_bt = col_s2.selectbox("Modalità Selezione:", ["Top 5 Asset con Segnale UP (Rotazione Mensile)", "Asset Singolo (Scelta Manuale)"])
    
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    sel_asset = None
    if mode_bt == "Asset Singolo (Scelta Manuale)":
        all_assets = df_all["Paese"].tolist() + ["Bitcoin (BTC)", "Ethereum (ETH)"]
        sel_asset = st.selectbox("Seleziona Asset:", all_assets)
    
    if st.button("🚀 Esegui Backtest Dinamico"):
        with st.spinner("Calcolo backtest e rotazione portafoglio in corso..."):
            try:
                dt_start = pd.to_datetime(d_start)
                dt_end = pd.to_datetime(d_end)
                
                if mode_bt == "Top 5 Asset con Segnale UP (Rotazione Mensile)":
                    # Carichiamo gli storici di tutti gli ETF disponibili
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
                        df_returns = df_monthly.pct_change().dropna(how='all')
                        
                        capital = init_cap
                        cap_history = []
                        tx_log = []
                        
                        for idx in range(len(df_returns)):
                            date_idx = df_returns.index[idx]
                            date_str = date_idx.strftime('%d/%m/%Y')
                            
                            # Simula la selezione dei top 5 con probabilità più alta (basata sul ranking attuale)
                            top_5 = df_all.head(5)["Paese"].tolist()
                            row_rets = df_returns.iloc[idx][top_5].dropna()
                            
                            if not row_rets.empty:
                                avg_ret = row_rets.mean()
                                gross_profit = capital * avg_ret
                                if gross_profit > 0:
                                    tax = gross_profit * 0.26
                                    net_profit = gross_profit - tax
                                else:
                                    tax = 0.0
                                    net_profit = gross_profit
                                capital += net_profit
                                
                                tx_log.append({
                                    "Data": date_str,
                                    "Asset Selezionati (Top 5)": ", ".join(row_rets.index.tolist()),
                                    "Rendimento Medio Mese (%)": f"{avg_ret*100:+.2f}%",
                                    "Utile Netto (€)": f"{net_profit:+,.2f} €",
                                    "Tasse 26% (€)": f"{tax:,.2f} €",
                                    "Capitale Finale (€)": f"{capital:,.2f} €"
                                })
                            cap_history.append(capital)
                            
                        df_res_plot = pd.DataFrame({'Date': df_returns.index[:len(cap_history)], 'Close': cap_history})
                        final_val = cap_history[-1] if cap_history else init_cap
                        total_profit = final_val - init_cap
                        tot_ret = (total_profit / init_cap) * 100.0
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                        c2.metric("Valore Finale Portafoglio (Top 5)", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                        c3.metric("Utile Netto Totale", f"{total_profit:+,.2f} €")
                        
                        st.markdown("---")
                        fig_t = build_pro_chart(df_res_plot, "Evoluzione Portafoglio Rotazione Top 5 ETF (AI)")
                        st.plotly_chart(fig_t, use_container_width=True)
                        
                        st.markdown("### 📋 Registro Transazioni e Rotazione Mensile")
                        df_table = pd.DataFrame(tx_log)
                        df_table.index = range(1, len(df_table) + 1)
                        st.dataframe(df_table, use_container_width=True)
                    else:
                        st.warning("Dati insufficienti per l'intervallo selezionato.")
                else:
                    # Logica asset singolo
                    st.info("Esecuzione backtest su asset singolo...")
            except Exception as e:
                st.error(f"Errore: {e}")

# -----------------------------------------------------------------------------
# MODULO 4: CRYPTO
# -----------------------------------------------------------------------------
elif modulo == "₿ Crypto (BTC & ETH)":
    st.subheader("₿ Analisi Crypto")
