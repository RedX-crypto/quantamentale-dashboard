import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re

# Import yfinance per i grafici storici degli ETF
try:
    import yfinance as yf
except ImportError:
    yf = None

st.set_page_config(page_title="Rotazione ETF & Grafici", page_icon="📈", layout="wide")

st.title("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
st.markdown("---")

# Funzione per individuare DataBase.xlsx
def find_excel_file(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    user_home = os.path.expanduser("~")
    search_paths = [
        filename,
        os.path.join(script_dir, filename),
        os.path.join(user_home, filename),
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

@st.cache_data
def load_etf_history(ticker):
    if yf is not None:
        try:
            df_yf = yf.Ticker(ticker).history(period="max")
            if not df_yf.empty:
                df_yf = df_yf.reset_index()
                date_col = [c for c in df_yf.columns if 'date' in c.lower() or 'data' in c.lower()][0]
                df_yf[date_col] = strip_timezone(df_yf[date_col])
                df_yf = df_yf.sort_values(by=date_col)
                return df_yf[[date_col, 'Open', 'High', 'Low', 'Close']].rename(
                    columns={date_col: 'Date'}
                ).dropna()
        except Exception:
            pass
    return None

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
def load_all_data():
    db_file = find_excel_file("DataBase.xlsx")
    records = []
    
    macro_data_dict = {}
    if db_file:
        try:
            df_macro = pd.read_excel(db_file, sheet_name="Macro Paesi 3M")
            df_macro_valid = df_macro.dropna(subset=['Voto', 'Country']).copy()
            if 'Data' in df_macro_valid.columns:
                df_macro_valid['Data'] = pd.to_datetime(df_macro_valid['Data'])
                df_macro_valid = df_macro_valid.sort_values('Data')
                
            df_latest = df_macro_valid.groupby('Country').last().reset_index()
            
            for _, row in df_latest.iterrows():
                p_name = str(row['Country']).strip()
                p_key = clean_country_name(p_name)
                voto_v = float(row['Voto']) if pd.notna(row['Voto']) else 2.50
                
                pil_raw = row['PIL'] if 'PIL' in row and pd.notna(row['PIL']) else 0.02
                pil_v = f"{pil_raw * 100:+.2f}%" if isinstance(pil_raw, (int, float)) and abs(pil_raw) < 1 else str(pil_raw)
                
                pmi_col = [c for c in df_latest.columns if 'pmi' in str(c).lower()][0]
                pmi_raw = row[pmi_col] if pd.notna(row[pmi_col]) else 50.0
                pmi_v = round(float(pmi_raw), 1) if isinstance(pmi_raw, (int, float)) else 50.0
                
                macro_data_dict[p_key] = {"Voto": voto_v, "PIL": pil_v, "PMI": pmi_v}
        except Exception:
            pass

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
                
                df_h = load_etf_history(meta["Ticker_YF"])
                rsi_val = 50.0
                mom1m_val = 0.0
                mom3m_val = 0.0
                
                if df_h is not None and not df_h.empty and len(df_h) >= 14:
                    close_s = df_h['Close']
                    delta = close_s.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / (loss + 1e-9)
                    rsi_val = round(float((100 - (100 / (1 + rs))).iloc[-1]), 1)
                    
                    if len(df_h) >= 21:
                        mom1m_val = round(((close_s.iloc[-1] - close_s.iloc[-21]) / close_s.iloc[-21]) * 100, 2)
                    if len(df_h) >= 63:
                        mom3m_val = round(((close_s.iloc[-1] - close_s.iloc[-63]) / close_s.iloc[-63]) * 100, 2)

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
                    "Mom_1M_num": mom1m_val,
                    "Mom_1M": f"{mom1m_val:+.2f}%",
                    "Mom_3M": f"{mom3m_val:+.2f}%",
                    "Sintesi": sintesi_text
                })
        except Exception:
            pass
            
    df = pd.DataFrame(records).sort_values(by="Prob_UP", ascending=False).reset_index(drop=True)
    df["Allocazione"] = 0
    eligible = df[(df["Segnale"] == "UP") & (df["Prob_UP"] >= 60.0) & (df["Stato OOS"] == "✅ Valido")].head(5).index
    df.loc[eligible, "Allocazione"] = 200
    return df

df_all = load_all_data()

# 1. Tabella principale
st.subheader("📊 Tabella Confluenza Quantamentale")
st.dataframe(
    df_all[["Paese", "Esito AI", "Allocazione", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]],
    use_container_width=True
)

st.markdown("---")

# 2. Nuvolette di Sintesi (Le 4 metriche richieste)
st.subheader("📌 Nuvolette di Sintesi")
c1, c2, c3, c4 = st.columns(4)

# - Migliore UP (Top Pick AI)
best_up = df_all[df_all["Segnale"] == "UP"].iloc[0] if not df_all[df_all["Segnale"] == "UP"].empty else df_all.iloc[0]
c1.metric("🟢 Migliore UP", best_up["Paese"], best_up["Esito AI"])

# - Migliore DOWN (Worst Pick AI sconsigliato)
down_df = df_all[df_all["Segnale"] == "DOWN"].sort_values(by="Prob_UP", ascending=False)
best_down = down_df.iloc[0] if not down_df.empty else df_all.iloc[-1]
c2.metric("🔴 Migliore DOWN", best_down["Paese"], best_down["Esito AI"])

# - Migliore del Mese (% prezzo)
best_mom = df_all.sort_values(by="Mom_1M_num", ascending=False).iloc[0]
c3.metric("🚀 Migliore del Mese (Prezzo)", best_mom["Paese"], best_mom["Mom_1M"])

# - Peggiore del Mese (% prezzo)
worst_mom = df_all.sort_values(by="Mom_1M_num", ascending=True).iloc[0]
c4.metric("📉 Peggiore del Mese (Prezzo)", worst_mom["Paese"], worst_mom["Mom_1M"])

st.markdown("---")

# 3. Grafico Interattivo con Candele e Selezione Orizzonte Temporale
st.subheader("📈 Grafico Storico Avanzato ETF Paese")

col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
selected_country = col_sel1.selectbox("Seleziona ETF Paese:", df_all["Paese"].tolist())
chart_type = col_sel2.radio("Tipo Grafico:", ["Linea", "Candele (Candlestick)"], horizontal=True)
is_log = col_sel3.checkbox("Scala Logaritmica", value=True)

horizon_etf = st.radio(
    "Orizzonte Temporale:", 
    ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], 
    index=6, 
    horizontal=True
)

row_country = df_all[df_all["Paese"] == selected_country].iloc[0]
df_chart = load_etf_history(row_country["Ticker_YF"])

if df_chart is not None and not df_chart.empty:
    df_filt, p_start, p_end, ret_pct = filter_by_horizon(df_chart, horizon_etf)
    
    # Card di dettaglio prezzo sopra il grafico
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(f"Performance ({horizon_etf})", f"{ret_pct:+.2f}%", f"Finale: ${p_end:,.2f}")
    m_col2.metric("Esito AI", row_country['Esito AI'])
    m_col3.metric("Stato OOS / Voto Macro", f"{row_country['Stato OOS']} | Voto: {row_country['Voto_Macro']}")
    
    # Costruzione Grafico Plotly
    fig = go.Figure()
    if chart_type == "Candele (Candlestick)" and 'Open' in df_filt.columns:
        fig.add_trace(go.Candlestick(
            x=df_filt['Date'],
            open=df_filt['Open'],
            high=df_filt['High'],
            low=df_filt['Low'],
            close=df_filt['Close'],
            name=selected_country,
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_filt['Date'],
            y=df_filt['Close'],
            mode='lines',
            name=selected_country,
            line=dict(color='#2962FF', width=2.5)
        ))
        
    fig.update_layout(
        title=dict(text=f"<b>Grafico Prezzi {selected_country} ({row_country['Ticker_YF']})</b>", font=dict(size=16)),
        yaxis_title="Prezzo ($)",
        xaxis_title="Data",
        template="plotly_white",
        height=500,
        margin=dict(l=30, r=30, t=50, b=30),
        xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
        yaxis=dict(type="log" if is_log else "linear", showgrid=True, gridcolor='#F0F2F5'),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ Impossibile scaricare lo storico dati per l'ETF selezionato.")
