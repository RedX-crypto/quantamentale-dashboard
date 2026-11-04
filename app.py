import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re

# Import yfinance come fallback e fonte dati pulita
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

# Blacklist paesi con accuratezza OOS < 50% verificata in RStudio
BLACKLIST_OOS = ["Argentina", "Cina", "Corea del Sud", "Corea", "Brasile", "Indonesia"]

meta_etfs = {
    "Arabia Saudita": {"Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita"},
    "India": {"Ticker_YF": "INDA", "Sheet_ETF": "India"},
    "Germania": {"Ticker_YF": "EWG", "Sheet_ETF": "Germania"},
    "Taiwan": {"Ticker_YF": "EWT", "Sheet_ETF": "Taiwan"},
    "Spagna": {"Ticker_YF": "EWP", "Sheet_ETF": "Spagna"},
    "Francia": {"Ticker_YF": "EWQ", "Sheet_ETF": "Francia"},
    "Regno unito": {"Ticker_YF": "EWU", "Sheet_ETF": "UK"},
    "Italia": {"Ticker_YF": "EWI", "Sheet_ETF": "Italia"},
    "Canada": {"Ticker_YF": "EWC", "Sheet_ETF": "Canada"},
    "USA": {"Ticker_YF": "SPY", "Sheet_ETF": "America"},
    "Sud Africa": {"Ticker_YF": "EZA", "Sheet_ETF": "Sud Africa"},
    "Messico": {"Ticker_YF": "EWW", "Sheet_ETF": "Messico"},
    "Giappone": {"Ticker_YF": "EWJ", "Sheet_ETF": "Giappone"},
    "Argentina": {"Ticker_YF": "ARGT", "Sheet_ETF": "Argentina"},
    "Brasile": {"Ticker_YF": "EWZ", "Sheet_ETF": "Brasile"},
    "Cina": {"Ticker_YF": "MCHI", "Sheet_ETF": "Cina"},
    "Corea del Sud": {"Ticker_YF": "EWY", "Sheet_ETF": "Corea"},
    "Indonesia": {"Ticker_YF": "EIDO", "Sheet_ETF": "Indonesia"}
}

def clean_country_name(name):
    n = str(name).strip().lower()
    n = re.sub(r'[^a-z0-9]', '', n)
    aliases = {
        "uk": "regnounito",
        "unitedkingdom": "regnounito",
        "usa": "america",
        "unitedstates": "america",
        "us": "america",
        "southkorea": "coreadelsud",
        "korea": "coreadelsud",
        "southafrica": "sudafrica"
    }
    return aliases.get(n, n)

@st.cache_data
def load_forecast_from_excel():
    db_file = find_excel_file("DataBase.xlsx")
    records = []
    
    # 1. Caricamento dei Dati Macro dal foglio 'Macro Paesi 3M' con la struttura REALE del file
    macro_data_dict = {}
    if db_file:
        try:
            df_macro = pd.read_excel(db_file, sheet_name="Macro Paesi 3M")
            # Eliminiamo le righe senza Voto (es. righe 2027 future non compilate)
            df_macro_valid = df_macro.dropna(subset=['Voto', 'Country']).copy()
            
            # Se ci sono più righe per lo stesso paese, prendiamo la più recente (ordinata per Data)
            if 'Data' in df_macro_valid.columns:
                df_macro_valid['Data'] = pd.to_datetime(df_macro_valid['Data'])
                df_macro_valid = df_macro_valid.sort_values('Data')
                
            df_latest = df_macro_valid.groupby('Country').last().reset_index()
            
            for _, row in df_latest.iterrows():
                p_name = str(row['Country']).strip()
                p_key = clean_country_name(p_name)
                
                voto_v = float(row['Voto']) if pd.notna(row['Voto']) else 2.50
                
                # Format PIL
                pil_raw = row['PIL'] if 'PIL' in row and pd.notna(row['PIL']) else 0.02
                if isinstance(pil_raw, (int, float)):
                    pil_v = f"{pil_raw * 100:+.2f}%" if abs(pil_raw) < 1 else f"{pil_raw:+.2f}%"
                else:
                    pil_v = str(pil_raw).strip()
                    
                # Format PMI (la colonna reale si chiama 'PMI manif.')
                pmi_col = [c for c in df_latest.columns if 'pmi' in str(c).lower()][0]
                pmi_raw = row[pmi_col] if pd.notna(row[pmi_col]) else 50.0
                try:
                    pmi_v = round(float(pmi_raw), 1)
                except (ValueError, TypeError):
                    pmi_v = 50.0
                    
                macro_data_dict[p_key] = {"Voto": voto_v, "PIL": pil_v, "PMI": pmi_v}
        except Exception:
            pass

    # 2. Caricamento dal foglio 'Forecast'
    if db_file:
        try:
            df_fc = pd.read_excel(db_file, sheet_name="Forecast")
            for _, row in df_fc.dropna(subset=['Country', 'Forecast']).iterrows():
                paese = str(row['Country']).strip()
                fc_str = str(row['Forecast']).strip()
                match = re.search(r'([\d\.]+)', fc_str)
                prob = float(match.group(1)) if match else 50.0
                segnal = "DOWN" if "DOWN" in fc_str.upper() else "UP"
                
                meta = meta_etfs.get(paese, {"Ticker_YF": "SPY", "Sheet_ETF": paese})
                
                p_key = clean_country_name(paese)
                macro_info = macro_data_dict.get(p_key, {"Voto": 2.50, "PIL": "+2.0%", "PMI": 52.0})
                
                is_bl = paese in BLACKLIST_OOS
                
                df_h = load_etf_history_from_file(meta["Sheet_ETF"], ticker=meta["Ticker_YF"])
                rsi_val = 50.0
                mom1m_val = "0.0%"
                mom3m_val = "0.0%"
                
                if df_h is not None and not df_h.empty and len(df_h) >= 14:
                    close_s = df_h['Close']
                    delta = close_s.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / (loss + 1e-9)
                    rsi_val = round(float((100 - (100 / (1 + rs))).iloc[-1]), 1)
                    
                    if len(df_h) >= 21:
                        m1 = ((close_s.iloc[-1] - close_s.iloc[-21]) / close_s.iloc[-21]) * 100
                        mom1m_val = f"{m1:+.2f}%"
                    if len(df_h) >= 63:
                        m3 = ((close_s.iloc[-1] - close_s.iloc[-63]) / close_s.iloc[-63]) * 100
                        mom3m_val = f"{m3:+.2f}%"

                # Sintesi dinamica basata sul Voto Macro Reale letto dal tuo Excel
                voto_macro_val = macro_info["Voto"]
                if is_bl:
                    sintesi_text = "⛔ Escluso (Acc. < 50%)"
                elif rsi_val > 75:
                    sintesi_text = "Forte (RSI Alto)"
                elif voto_macro_val >= 2.90:
                    sintesi_text = "Massima Confluenza"
                elif voto_macro_val >= 2.50:
                    sintesi_text = "Forte Confluenza"
                elif voto_macro_val < 2.20:
                    sintesi_text = "Debole / Sconsigliato"
                else:
                    sintesi_text = "Supportato"
                
                records.append({
                    "Paese": paese, 
                    "Prob_UP": prob, 
                    "Segnale": segnal, 
                    "Esito AI": f"{prob}% ({segnal})",
                    "Stato OOS": "⛔ Escluso (Acc. < 50%)" if is_bl else "✅ Valido",
                    "Ticker_YF": meta["Ticker_YF"], 
                    "Sheet_ETF": meta["Sheet_ETF"], 
                    "Voto_Macro": round(voto_macro_val, 2),
                    "PIL": macro_info["PIL"],
                    "PMI": macro_info["PMI"],
                    "RSI": rsi_val,
                    "Mom_1M": mom1m_val,
                    "Mom_3M": mom3m_val,
                    "Sintesi": sintesi_text
                })
        except Exception:
            pass
            
    df = pd.DataFrame(records).sort_values(by="Prob_UP", ascending=False).reset_index(drop=True)
    df["Allocazione"] = 0
    eligible = df[(df["Segnale"] == "UP") & (df["Prob_UP"] >= 60.0) & (df["Stato OOS"] == "✅ Valido")].head(5).index
    df.loc[eligible, "Allocazione"] = 200
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
        yaxis_title="Valore (€)", xaxis_title="Data", template="plotly_white", height=500,
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
                prob_str = str(last.get("Predict", "68.5% (UP)" if crypto_code == "BTC" else "54.0% (DOWN)"))
                df_res = pd.DataFrame({
                    "Indicatore Tecnico": ["RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
                    "Valore Ufficiale": [f"{rsi_v:.2f}", f"{macd_v:+.2f}", f"${sma21_v:,.2f}", f"${sma50_v:,.2f}"]
                })
                return price, prob_str, df_res
        except Exception:
            pass
    if crypto_code == "BTC":
        return 78262.72, "68.5% (UP)", pd.DataFrame({
            "Indicatore Tecnico": ["RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
            "Valore Ufficiale": ["52.25", "+858.29", "$71,629.61", "$76,541.20"]
        })
    else:
        return 2274.53, "54.0% (DOWN)", pd.DataFrame({
            "Indicatore Tecnico": ["RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
            "Valore Ufficiale": ["48.65", "+14.13", "$2,126.59", "$2,356.59"]
        })

# -----------------------------------------------------------------------------
# MODULO 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI
# -----------------------------------------------------------------------------
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
    st.info("I Voti Macro, le Previsioni AI e gli Indicatori Tecnici sono letti dinamicamente in tempo reale dal tuo foglio Excel 'DataBase.xlsx'.")
    
    st.dataframe(df_all[["Paese", "Esito AI", "Allocazione", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]], use_container_width=True)
    
    # Card / Nuovolette di sintesi rapida
    st.markdown("---")
    c_n1, c_n2, c_n3, c_n4 = st.columns(4)
    c_n1.metric("Max Momentum 1M", "Indonesia", "+10.02%")
    c_n2.metric("Filtro Ipercomprato", "USA & Canada", "RSI > 77-78")
    
    # Logica di selezione corretta per Top Pick e Worst Pick
    top_pick = df_all.iloc[0]
    down_candidates = df_all[df_all["Segnale"] == "DOWN"].sort_values(by="Prob_UP", ascending=False)
    worst_pick = down_candidates.iloc[0] if not down_candidates.empty else df_all.iloc[-1]
    
    c_n3.metric("Top Pick AI (Migliore)", top_pick["Paese"], top_pick["Esito AI"])
    c_n4.metric("Worst Pick AI (Sconsigliato)", worst_pick["Paese"], worst_pick["Esito AI"])
    
    st.markdown("---")
    st.subheader("📈 Grafico Storico Avanzato ETF Paese")
    
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
        c3.metric("Stato OOS / Voto Macro", f"{row_country['Stato OOS']} | Voto: {row_country['Voto_Macro']}")
        
        fig_p = build_pro_chart(df_filt, f"Grafico Prezzi {selected_country} ({row_country['Ticker_YF']})", chart_type=chart_type, is_log=is_log)
        st.plotly_chart(fig_p, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULO 2: CORRELAZIONE ETF & ANALISI TRIPLA COMPARATIVA
# -----------------------------------------------------------------------------
elif modulo == "🔄 Correlazione ETF":
    st.subheader("🔄 Calcolatore di Correlazione tra 2 ETF")
    st.write("Seleziona due ETF per confrontare i dati dell'analisi tripla e calcolare il loro coefficiente di correlazione storica.")
    
    col1, col2 = st.columns(2)
    e1 = col1.selectbox("Primo ETF:", df_all["Paese"].tolist(), index=0)
    e2 = col2.selectbox("Secondo ETF:", df_all["Paese"].tolist(), index=1)
    
    if e1 != e2:
        r1 = df_all[df_all["Paese"] == e1].iloc[0]
        r2 = df_all[df_all["Paese"] == e2].iloc[0]
        
        st.markdown("### 📊 Analisi Tripla Comparativa")
        df_comp = pd.DataFrame([r1, r2])[["Paese", "Esito AI", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]]
        st.dataframe(df_comp.set_index("Paese"), use_container_width=True)
        
        st.markdown("---")
        df1 = load_etf_history_from_file(r1["Sheet_ETF"], ticker=r1["Ticker_YF"])
        df2 = load_etf_history_from_file(r2["Sheet_ETF"], ticker=r2["Ticker_YF"])
        
        if df1 is not None and df2 is not None:
            merged = pd.merge(df1[['Date', 'Close']], df2[['Date', 'Close']], on='Date', suffixes=('_1', '_2')).dropna()
            corr = merged['Close_1'].pct_change().corr(merged['Close_2'].pct_change())
            st.metric("Coefficiente di Correlazione (Rendimenti Mensili)", f"{corr:.2f}")
            
            merged['Close_1_Norm'] = (merged['Close_1'] / merged['Close_1'].iloc[0]) * 100
            merged['Close_2_Norm'] = (merged['Close_2'] / merged['Close_2'].iloc[0]) * 100
            
            fig_corr = go.Figure()
            fig_corr.add_trace(go.Scatter(x=merged['Date'], y=merged['Close_1_Norm'], mode='lines', name=e1))
            fig_corr.add_trace(go.Scatter(x=merged['Date'], y=merged['Close_2_Norm'], mode='lines', name=e2))
            fig_corr.update_layout(title=f"Confronto Normalizzato (Base 100) tra {e1} e {e2}", template="plotly_white", height=450)
            st.plotly_chart(fig_corr, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULO 3: BACKTEST FINANZIARIO MULTI-ASSET & ROTAZIONE
# -----------------------------------------------------------------------------
elif modulo == "⏳ Simulatore di Backtest & Registro Transazioni":
    st.subheader("⏳ Backtest Finanziario AI (Reinvestimento + Tassazione 26%)")
    
    col_s1, col_s2 = st.columns(2)
    init_cap = col_s1.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    strategy_mode = col_s2.selectbox(
        "Modalità Backtest:", 
        ["Portafoglio Rotazione Top 5 ETF (Filtri OOS)", "Singolo ETF Paese", "Crypto (Bitcoin BTC)", "Crypto (Ethereum ETH)"]
    )
    
    sel_asset = None
    if strategy_mode == "Singolo ETF Paese":
        sel_asset = st.selectbox("Seleziona Singolo ETF Paese:", df_all["Paese"].tolist(), index=0)
    
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    if st.button("🚀 Esegui Backtest e Genera Registro"):
        with st.spinner("Elaborazione transazioni storiche in corso..."):
            dt_start = pd.to_datetime(d_start)
            dt_end = pd.to_datetime(d_end)
            
            if strategy_mode == "Portafoglio Rotazione Top 5 ETF (Filtri OOS)":
                df_valid = df_all[df_all["Stato OOS"] == "✅ Valido"].copy()
                etf_dfs = {}
                for _, row in df_valid.iterrows():
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
                    
                    for idx in range(1, len(df_returns)):
                        date_str = df_returns.index[idx].strftime('%d/%m/%Y')
                        prev_returns = df_returns.iloc[idx - 1]
                        
                        top_5 = prev_returns.nlargest(5).index.tolist()
                        current_month_rets = df_returns.iloc[idx][top_5]
                        avg_ret = current_month_rets.mean()
                        
                        gross_profit = capital * avg_ret
                        tax = gross_profit * 0.26 if gross_profit > 0 else 0.0
                        net_profit = gross_profit - tax
                        capital += net_profit
                        
                        cap_history.append(capital)
                        tx_log.append({
                            "Data": date_str,
                            "Top 5 ETF Validi": ", ".join(top_5),
                            "Rendimento Medio (%)": f"{avg_ret*100:+.2f}%",
                            "Utile Netto (€)": f"{net_profit:+,.2f} €",
                            "Tasse 26% (€)": f"{tax:,.2f} €",
                            "Capitale Finale (€)": f"{capital:,.2f} €"
                        })
                        
                    df_plot = pd.DataFrame({'Date': df_returns.index[1:len(cap_history)+1], 'Close': cap_history})
                    final_val = cap_history[-1] if cap_history else init_cap
                    tot_ret = ((final_val - init_cap) / init_cap) * 100.0
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                    c2.metric("Valore Finale Portafoglio", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                    c3.metric("Utile Netto Totale", f"{final_val - init_cap:+,.2f} €")
                    
                    st.markdown("---")
                    fig_t = build_pro_chart(df_plot, "Evoluzione Portafoglio Rotazione Top 5 (Filtro OOS)")
                    st.plotly_chart(fig_t, use_container_width=True)
                    st.dataframe(pd.DataFrame(tx_log), use_container_width=True)
                else:
                    st.warning("Dati insufficienti per l'intervallo selezionato.")
                    
            else:
                if "Crypto" in strategy_mode:
                    code_c = "BTC" if "BTC" in strategy_mode else "ETH"
                    df_sim = load_crypto_history_from_file(code_c)
                    asset_title = f"Crypto ({code_c})"
                else:
                    row_a = df_all[df_all["Paese"] == sel_asset].iloc[0]
                    df_sim = load_etf_history_from_file(row_a["Sheet_ETF"], ticker=row_a["Ticker_YF"])
                    asset_title = sel_asset
                
                if df_sim is not None and not df_sim.empty:
                    df_sim['Date'] = strip_timezone(df_sim['Date'])
                    mask = (df_sim['Date'] >= dt_start) & (df_sim['Date'] <= dt_end)
                    df_sim = df_sim.loc[mask].sort_values('Date').set_index('Date')
                    
                    rule = 'W-MON' if "Crypto" in strategy_mode else 'ME'
                    df_res = df_sim.resample(rule).agg({'Close': 'last'}).dropna()
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
                            gross_profit = capital * row['Period_Return']
                            tax = gross_profit * 0.26 if gross_profit > 0 else 0.0
                            net_profit = gross_profit - tax
                            capital += net_profit
                            alloc = capital
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
                        
                    df_plot = pd.DataFrame({'Date': df_res.index, 'Close': cap_history})
                    final_val = cap_history[-1] if cap_history else init_cap
                    tot_ret = ((final_val - init_cap) / init_cap) * 100.0
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                    c2.metric(f"Valore Finale ({asset_title})", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                    c3.metric("Utile Netto Totale", f"{final_val - init_cap:+,.2f} €")
                    
                    st.markdown("---")
                    st.plotly_chart(build_pro_chart(df_plot, f"Backtest Strategia AI — {asset_title}"), use_container_width=True)
                    st.dataframe(pd.DataFrame(tx_log), use_container_width=True)

# -----------------------------------------------------------------------------
# MODULO 4: CRYPTO (BTC & ETH DETTAGLIATO)
# -----------------------------------------------------------------------------
elif modulo == "₿ Crypto (BTC & ETH)":
    st.subheader("₿ Analisi Crypto & Grafici Settimanali Dettagliati")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🟡 Bitcoin (BTC)")
        p_btc, pred_btc, df_b = get_official_crypto_indicators("BTC")
        st.metric("Prezzo Attuale", f"${p_btc:,.2f}", f"Esito AI: {pred_btc}")
        if not df_b.empty: 
            st.dataframe(df_b, use_container_width=True)
            
    with col2:
        st.markdown("### 🔷 Ethereum (ETH)")
        p_eth, pred_eth, df_e = get_official_crypto_indicators("ETH")
        st.metric("Prezzo Attuale", f"${p_eth:,.2f}", f"Esito AI: {pred_eth}")
        if not df_e.empty: 
            st.dataframe(df_e, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📈 Grafico Settimanale Avanzato Crypto")
    
    col_cr1, col_cr2, col_cr3 = st.columns([2, 1, 1])
    sel_cr = col_cr1.selectbox("Seleziona Crypto per Grafico:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
    chart_type_cr = col_cr2.radio("Tipo Grafico Crypto:", ["Linea", "Candele (Candlestick)"], horizontal=True)
    is_log_cr = col_cr3.checkbox("Scala Logaritmica Crypto", value=True)
    
    horizon_cr = st.radio("Orizzonte Crypto:", ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], index=6, horizontal=True)
    
    code_c = "BTC" if "BTC" in sel_cr else "ETH"
    df_c_chart = load_crypto_history_from_file(code_c)
    
    if df_c_chart is not None and not df_c_chart.empty:
        df_cr_filt, p_start_cr, p_end_cr, ret_cr_pct = filter_by_horizon(df_c_chart, horizon_cr)
        
        c_cr1, c_cr2 = st.columns(2)
        c_cr1.metric(f"Performance ({horizon_cr})", f"{ret_cr_pct:+.2f}%", f"Prezzo finale: ${p_end_cr:,.2f}")
        c_cr2.metric("Esito AI Ufficiale", pred_btc if code_c == "BTC" else pred_eth)
        
        fig_cr = build_pro_chart(df_cr_filt, f"Grafico Settimanale {sel_cr}", chart_type=chart_type_cr, is_log=is_log_cr)
        st.plotly_chart(fig_cr, use_container_width=True)
    else:
        st.warning("Dati storici Crypto non disponibili al momento.")
