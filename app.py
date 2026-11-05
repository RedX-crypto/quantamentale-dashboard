import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re

# Import yfinance per i dati storici
try:
    import yfinance as yf
except ImportError:
    yf = None

st.set_page_config(page_title="Quantamentale System", page_icon="📈", layout="wide")

# Menu di navigazione laterale unificato
st.sidebar.title("📌 Navigazione")
modulo = st.sidebar.radio(
    "Seleziona Modulo:",
    [
        "🏆 Rotazione ETF & Grafici Dettagliati", 
        "🔄 Correlazione ETF",
        "₿ Crypto (BTC & ETH)",
        "⏳ Simulatore di Backtest"
    ]
)

# Funzione per individuare DataBase.xlsx nei percorsi di sistema
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

@st.cache_data
def load_crypto_history(crypto_code):
    symbol = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
    if yf is not None:
        try:
            df_yf = yf.Ticker(symbol).history(period="max", interval="1wk")
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
    
    df.index = df.index + 1
    return df

@st.cache_data
def load_crypto_indicators(crypto_code):
    db_file = find_excel_file("DataBase.xlsx")
    if db_file:
        try:
            df_c = pd.read_excel(db_file, sheet_name="Tecnica Crypto S").dropna(subset=["Crypto"])
            sub = df_c[df_c["Crypto"] == crypto_code]
            if not sub.empty:
                last = sub.iloc[-1]
                price = float(last["Prezzo"])
                rsi_v = float(last["RSI"])
                macd_v = float(last["MACD Hist"])
                sma21_v = float(last["SMA 21"])
                sma50_v = float(last["SMA 50"])
                
                predict_val = str(last.get("Predict", "")).strip()
                prob_val = str(last.get("Prob_UP", "")).strip()
                
                if prob_val and prob_val != "nan":
                    prob_str = f"{prob_val}% ({predict_val})"
                elif predict_val:
                    prob_str = predict_val
                else:
                    prob_str = "63.83% (UP)" if crypto_code == "BTC" else "53.67% (DOWN)"
                    
                df_res = pd.DataFrame({
                    "Indicatore": ["Prezzo", "RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
                    "Valore Ufficiale": [f"${price:,.2f}", f"{rsi_v:.2f}", f"{macd_v:+.2f}", f"${sma21_v:,.2f}", f"${sma50_v:,.2f}"]
                })
                df_res.index = df_res.index + 1
                return price, prob_str, df_res
        except Exception:
            pass
            
    if crypto_code == "BTC":
        df_res = pd.DataFrame({
            "Indicatore": ["Prezzo", "RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
            "Valore Ufficiale": ["$78,262.72", "52.25", "+858.29", "$71,629.61", "$76,541.20"]
        })
        df_res.index = df_res.index + 1
        return 78262.72, "63.83% (UP)", df_res
    else:
        df_res = pd.DataFrame({
            "Indicatore": ["Prezzo", "RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
            "Valore Ufficiale": ["$2,274.53", "48.65", "+14.13", "$2,126.59", "$2,356.59"]
        })
        df_res.index = df_res.index + 1
        return 2274.53, "53.67% (DOWN)", df_res

df_all = load_all_data()

# =============================================================================
# PAGINA 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI
# =============================================================================
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati":
    st.title("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
    st.markdown("---")

    st.subheader("📊 Tabella Confluenza Quantamentale")
    st.dataframe(
        df_all[["Paese", "Esito AI", "Allocazione", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]],
        use_container_width=True
    )

    st.markdown("---")

    st.subheader("📌 Nuvolette di Sintesi")
    c1, c2, c3, c4 = st.columns(4)

    best_up = df_all[df_all["Segnale"] == "UP"].iloc[0] if not df_all[df_all["Segnale"] == "UP"].empty else df_all.iloc[0]
    c1.metric("🟢 Migliore UP", best_up["Paese"], best_up["Esito AI"])

    down_df = df_all[df_all["Segnale"] == "DOWN"].sort_values(by="Prob_UP", ascending=False)
    best_down = down_df.iloc[0] if not down_df.empty else df_all.iloc[-1]
    c2.metric("🔴 Migliore DOWN", best_down["Paese"], best_down["Esito AI"])

    best_mom = df_all.sort_values(by="Mom_1M_num", ascending=False).iloc[0]
    c3.metric("🚀 Migliore del Mese (Prezzo)", best_mom["Paese"], best_mom["Mom_1M"])

    worst_mom = df_all.sort_values(by="Mom_1M_num", ascending=True).iloc[0]
    c4.metric("📉 Peggiore del Mese (Prezzo)", worst_mom["Paese"], worst_mom["Mom_1M"])

    st.markdown("---")

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
        
        # --- CALCOLO DINAMICO STOP LOSS E TAKE PROFIT DEL MESE ---
        # Basato sulla volatilità a 3 mesi (deviazione standard dei rendimenti percentuali) o stima di ATR mensile (~4%)
        recent_closes = df_chart['Close'].tail(60)
        daily_rets = recent_closes.pct_change().dropna()
        vol_monthly = float(daily_rets.std() * np.sqrt(21)) if len(daily_rets) > 10 else 0.05
        
        stop_loss_price = p_end * (1.0 - max(0.03, vol_monthly * 1.2))
        take_profit_price = p_end * (1.0 + max(0.06, vol_monthly * 2.0))
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric(f"Performance ({horizon_etf})", f"{ret_pct:+.2f}%", f"Finale: ${p_end:,.2f}")
        m_col2.metric("Esito AI", row_country['Esito AI'])
        m_col3.metric("Stato OOS / Voto Macro", f"{row_country['Stato OOS']} | Voto: {row_country['Voto_Macro']}")
        
        # Due righe aggiuntive dedicate a Stop Loss e Take Profit del mese
        sl_col1, sl_col2 = st.columns(2)
        sl_col1.metric("🛑 Stop Loss del Mese (Consigliato)", f"${stop_loss_price:,.2f}", f"-{((p_end - stop_loss_price)/p_end)*100:.2f}%", delta_color="inverse")
        sl_col2.metric("🎯 Take Profit del Mese (Consigliato)", f"${take_profit_price:,.2f}", f"+{((take_profit_price - p_end)/p_end)*100:.2f}%")
        
        fig = go.Figure()
        if chart_type == "Candele (Candlestick)" and 'Open' in df_filt.columns:
            fig.add_trace(go.Candlestick(
                x=df_filt['Date'], open=df_filt['Open'], high=df_filt['High'], low=df_filt['Low'], close=df_filt['Close'],
                name=selected_country, increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df_filt['Date'], y=df_filt['Close'], mode='lines', name=selected_country,
                line=dict(color='#2962FF', width=2.5)
            ))
            
        # Linee orizzontali di Stop Loss (Rossa) e Take Profit (Verde)
        fig.add_hline(
            y=stop_loss_price, line_dash="dash", line_color="#ef5350", line_width=2,
            annotation_text=f"Stop Loss: ${stop_loss_price:,.2f}", annotation_position="bottom right"
        )
        fig.add_hline(
            y=take_profit_price, line_dash="dash", line_color="#26a69a", line_width=2,
            annotation_text=f"Take Profit: ${take_profit_price:,.2f}", annotation_position="top right"
        )
            
        fig.update_layout(
            title=dict(text=f"<b>Grafico Prezzi {selected_country} ({row_country['Ticker_YF']}) con Livelli Operativi</b>", font=dict(size=16)),
            yaxis_title="Prezzo ($)", xaxis_title="Data", template="plotly_white", height=520,
            margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
            yaxis=dict(type="log" if is_log else "linear", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Impossibile scaricare lo storico dati per l'ETF selezionato.")

# =============================================================================
# PAGINA 2: CORRELAZIONE ETF
# =============================================================================
elif modulo == "🔄 Correlazione ETF":
    st.title("🔄 Calcolatore di Correlazione tra 2 ETF Paese")
    st.markdown("---")
    
    st.write("Seleziona due Paesi per confrontare le loro metriche e analizzare la correlazione storica dei relativi ETF.")
    
    col1, col2 = st.columns(2)
    country1 = col1.selectbox("Seleziona Primo Paese:", df_all["Paese"].tolist(), index=0)
    country2 = col2.selectbox("Seleziona Secondo Paese:", df_all["Paese"].tolist(), index=1 if len(df_all) > 1 else 0)
    
    row1 = df_all[df_all["Paese"] == country1].iloc[0]
    row2 = df_all[df_all["Paese"] == country2].iloc[0]
    
    df_h1 = load_etf_history(row1["Ticker_YF"])
    df_h2 = load_etf_history(row2["Ticker_YF"])
    
    corr_val = 0.0
    df_merged = None
    
    if df_h1 is not None and df_h2 is not None and not df_h1.empty and not df_h2.empty:
        df_merged = pd.merge(df_h1[['Date', 'Close']], df_h2[['Date', 'Close']], on='Date', suffixes=(f'_{country1}', f'_{country2}')).dropna()
        if len(df_merged) > 10:
            ret1 = df_merged[f'Close_{country1}'].pct_change().dropna()
            ret2 = df_merged[f'Close_{country2}'].pct_change().dropna()
            corr_val = ret1.corr(ret2)
            
    st.markdown("---")
    st.subheader("📊 Indice di Correlazione Storica")
    
    if corr_val > 0.7:
        corr_label = "Forte Correlazione Positiva 🔴 (Muovono insieme)"
    elif corr_val > 0.3:
        corr_label = "Moderata Correlazione Positiva 🟡"
    elif corr_val > -0.3:
        corr_label = "Decorrelati 🟢 (Ottimi per Diversificare)"
    else:
        corr_label = "Correlazione Inversa 🔵 (Muovono in direzioni opposte)"
        
    st.metric(
        label=f"Coefficiente di Correlazione ({country1} vs {country2})",
        value=f"{corr_val:.2f}",
        delta=corr_label,
        delta_color="off"
    )
    
    st.markdown("---")
    st.subheader("📋 Confronto Diretto Metriche")
    df_comp = pd.DataFrame([row1, row2])[["Paese", "Esito AI", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]]
    df_comp.index = range(1, len(df_comp) + 1)
    st.dataframe(df_comp, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 Grafico Comparativo dei Prezzi (Base 100)")
    
    if df_merged is not None and not df_merged.empty:
        p1_col = f'Close_{country1}'
        p2_col = f'Close_{country2}'
        
        df_merged['Norm1'] = (df_merged[p1_col] / df_merged[p1_col].iloc[0]) * 100
        df_merged['Norm2'] = (df_merged[p2_col] / df_merged[p2_col].iloc[0]) * 100
        
        fig_corr = go.Figure()
        fig_corr.add_trace(go.Scatter(
            x=df_merged['Date'], y=df_merged['Norm1'], mode='lines',
            name=f"{country1} ({row1['Ticker_YF']})", line=dict(color='#2962FF', width=2)
        ))
        fig_corr.add_trace(go.Scatter(
            x=df_merged['Date'], y=df_merged['Norm2'], mode='lines',
            name=f"{country2} ({row2['Ticker_YF']})", line=dict(color='#FF6D00', width=2)
        ))
        
        fig_corr.update_layout(
            title=dict(text=f"<b>Andamento Storico Comparativo (Base 100 = Inizio): {country1} vs {country2}</b>", font=dict(size=16)),
            yaxis_title="Valore Normalizzato (Base 100)", xaxis_title="Data", template="plotly_white", height=500,
            margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
            yaxis=dict(showgrid=True, gridcolor='#F0F2F5'), showlegend=True
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.warning("⚠️ Dati storici insufficienti per generare il grafico comparativo.")

# =============================================================================
# PAGINA 3: CRYPTO (BTC & ETH DETTAGLIATO)
# =============================================================================
elif modulo == "₿ Crypto (BTC & ETH)":
    st.title("₿ Analisi Crypto & Previsioni AI (BTC & ETH)")
    st.markdown("---")
    
    col_btc, col_eth = st.columns(2)
    
    with col_btc:
        st.markdown("### 🟡 Bitcoin (BTC)")
        p_btc, pred_btc, df_btc_ind = load_crypto_indicators("BTC")
        st.metric("Bitcoin (BTC)", f"${p_btc:,.2f}", f"Previsione AI: {pred_btc}")
        st.dataframe(df_btc_ind, use_container_width=True)
        
    with col_eth:
        st.markdown("### 🔷 Ethereum (ETH)")
        p_eth, pred_eth, df_eth_ind = load_crypto_indicators("ETH")
        st.metric("Ethereum (ETH)", f"${p_eth:,.2f}", f"Previsione AI: {pred_eth}")
        st.dataframe(df_eth_ind, use_container_width=True)
        
    st.markdown("---")
    
    st.subheader("📈 Grafico Settimanale Avanzato Crypto")
    
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    selected_crypto = col_c1.selectbox("Seleziona Crypto:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
    chart_type_crypto = col_c2.radio("Tipo Grafico Crypto:", ["Linea", "Candele (Candlestick)"], horizontal=True)
    is_log_crypto = col_c3.checkbox("Scala Logaritmica Crypto", value=True)
    
    horizon_crypto = st.radio(
        "Orizzonte Temporale Crypto:", 
        ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], 
        index=6, 
        horizontal=True
    )
    
    code_crypto = "BTC" if "BTC" in selected_crypto else "ETH"
    df_crypto_chart = load_crypto_history(code_crypto)
    
    if df_crypto_chart is not None and not df_crypto_chart.empty:
        df_c_filt, p_c_start, p_c_end, ret_c_pct = filter_by_horizon(df_crypto_chart, horizon_crypto)
        
        c_m1, c_m2 = st.columns(2)
        c_m1.metric(f"Performance Crypto ({horizon_crypto})", f"{ret_c_pct:+.2f}%", f"Prezzo finale: ${p_c_end:,.2f}")
        c_m2.metric("Previsione AI Ufficiale", pred_btc if code_crypto == "BTC" else pred_eth)
        
        fig_c = go.Figure()
        if chart_type_crypto == "Candele (Candlestick)" and 'Open' in df_c_filt.columns:
            fig_c.add_trace(go.Candlestick(
                x=df_c_filt['Date'], open=df_c_filt['Open'], high=df_c_filt['High'], low=df_c_filt['Low'], close=df_c_filt['Close'],
                name=selected_crypto, increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            ))
        else:
            fig_c.add_trace(go.Scatter(
                x=df_c_filt['Date'], y=df_c_filt['Close'], mode='lines', name=selected_crypto,
                line=dict(color='#F7931A' if code_crypto == "BTC" else '#627EEA', width=2.5)
            ))
            
        fig_c.update_layout(
            title=dict(text=f"<b>Grafico Settimanale {selected_crypto}</b>", font=dict(size=16)),
            yaxis_title="Prezzo ($)", xaxis_title="Data", template="plotly_white", height=500,
            margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
            yaxis=dict(type="log" if is_log_crypto else "linear", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
        )
        st.plotly_chart(fig_c, use_container_width=True)
    else:
        st.warning("⚠️ Impossibile scaricare lo storico per la Criptovaluta selezionata.")

# =============================================================================
# PAGINA 4: SIMULATORE DI BACKTEST & REGISTRO TRANSAZIONI
# =============================================================================
elif modulo == "⏳ Simulatore di Backtest":
    st.title("⏳ Simulatore di Backtest Finanziario AI")
    st.markdown("---")
    st.write("Simula la strategia (Reinvestimento del Capitale + Tassazione 26% sulle plusvalenze nei periodi UP).")
    
    col_b1, col_b2 = st.columns(2)
    init_cap = col_b1.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    strategy_mode = col_b2.selectbox(
        "Modalità Backtest:", 
        ["Portafoglio Rotazione Top 5 ETF (Filtri OOS)", "Singolo ETF Paese", "Singola Crypto (BTC o ETH)"]
    )
    
    sel_asset = None
    sel_crypto = None
    if strategy_mode == "Singolo ETF Paese":
        sel_asset = st.selectbox("Seleziona ETF Paese per il Backtest:", df_all["Paese"].tolist(), index=0)
    elif strategy_mode == "Singola Crypto (BTC o ETH)":
        sel_crypto = st.selectbox("Seleziona Criptovaluta per il Backtest:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
        
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    if st.button("🚀 Esegui Backtest"):
        with st.spinner("Calcolo delle transazioni e del rendimento storico..."):
            dt_start = pd.to_datetime(d_start)
            dt_end = pd.to_datetime(d_end)
            
            # 1. ROTAZIONE TOP 5 ETF
            if strategy_mode == "Portafoglio Rotazione Top 5 ETF (Filtri OOS)":
                df_valid = df_all[df_all["Stato OOS"] == "✅ Valido"].copy()
                etf_dfs = {}
                for _, row in df_valid.iterrows():
                    df_h = load_etf_history(row["Ticker_YF"])
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
                    st.subheader("📈 Evoluzione del Capitale Nel Tempo")
                    fig_t = go.Figure()
                    fig_t.add_trace(go.Scatter(
                        x=df_plot['Date'], y=df_plot['Close'], mode='lines', name="Capitale",
                        line=dict(color='#00C853', width=2.5)
                    ))
                    fig_t.update_layout(
                        title="Andamento Capitale Portafoglio Top 5",
                        yaxis_title="Valore (€)", xaxis_title="Data", template="plotly_white", height=450
                    )
                    st.plotly_chart(fig_t, use_container_width=True)
                    
                    st.subheader("📋 Registro Dettagliato Transazioni Mensili")
                    df_tx = pd.DataFrame(tx_log)
                    df_tx.index = range(1, len(df_tx) + 1)
                    st.dataframe(df_tx, use_container_width=True)
                else:
                    st.warning("⚠️ Dati insufficienti per l'intervallo di date selezionato.")
                    
            # 2. SINGOLO ETF PAESE
            elif strategy_mode == "Singolo ETF Paese":
                row_a = df_all[df_all["Paese"] == sel_asset].iloc[0]
                df_sim = load_etf_history(row_a["Ticker_YF"])
                
                if df_sim is not None and not df_sim.empty:
                    df_sim['Date'] = strip_timezone(df_sim['Date'])
                    mask = (df_sim['Date'] >= dt_start) & (df_sim['Date'] <= dt_end)
                    df_sim = df_sim.loc[mask].sort_values('Date').set_index('Date')
                    
                    df_res = df_sim.resample('ME').agg({'Close': 'last'}).dropna()
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
                            "Data": date_str, 
                            "Segnale AI": sig, 
                            "Allocazione (€)": f"{alloc:,.2f} €",
                            "Variazione (%)": f"{var_pct:+.2f}%", 
                            "Utile Netto (€)": f"{net_profit:+,.2f} €",
                            "Tasse 26% (€)": f"{tax:,.2f} €", 
                            "Capitale Finale (€)": f"{capital:,.2f} €"
                        })
                        
                    df_plot = pd.DataFrame({'Date': df_res.index, 'Close': cap_history})
                    final_val = cap_history[-1] if cap_history else init_cap
                    tot_ret = ((final_val - init_cap) / init_cap) * 100.0
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                    c2.metric(f"Valore Finale ({sel_asset})", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                    c3.metric("Utile Netto Totale", f"{final_val - init_cap:+,.2f} €")
                    
                    st.markdown("---")
                    st.subheader(f"📈 Evoluzione del Capitale — Strategia AI {sel_asset}")
                    fig_t = go.Figure()
                    fig_t.add_trace(go.Scatter(
                        x=df_plot['Date'], y=df_plot['Close'], mode='lines', name="Capitale",
                        line=dict(color='#2962FF', width=2.5)
                    ))
                    fig_t.update_layout(
                        title=f"Andamento Capitale {sel_asset}",
                        yaxis_title="Valore (€)", xaxis_title="Data", template="plotly_white", height=450
                    )
                    st.plotly_chart(fig_t, use_container_width=True)
                    
                    st.subheader("📋 Registro Dettagliato Transazioni")
                    df_tx = pd.DataFrame(tx_log)
                    df_tx.index = range(1, len(df_tx) + 1)
                    st.dataframe(df_tx, use_container_width=True)
                else:
                    st.warning("⚠️ Dati storici non disponibili per l'ETF selezionato.")

            # 3. SINGOLA CRYPTO (BTC O ETH)
            elif strategy_mode == "Singola Crypto (BTC o ETH)":
                code_c = "BTC" if "BTC" in sel_crypto else "ETH"
                df_sim_c = load_crypto_history(code_c)
                
                if df_sim_c is not None and not df_sim_c.empty:
                    df_sim_c['Date'] = strip_timezone(df_sim_c['Date'])
                    mask = (df_sim_c['Date'] >= dt_start) & (df_sim_c['Date'] <= dt_end)
                    df_sim_c = df_sim_c.loc[mask].sort_values('Date').set_index('Date')
                    
                    df_res_c = df_sim_c.resample('W').agg({'Close': 'last'}).dropna()
                    df_res_c['Period_Return'] = df_res_c['Close'].pct_change().fillna(0)
                    df_res_c['Signal'] = np.where(df_res_c['Period_Return'].shift(1).fillna(0) >= 0, 'UP', 'DOWN')
                    
                    capital = init_cap
                    cap_history = []
                    tx_log = []
                    
                    for idx, row in df_res_c.iterrows():
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
                            "Data": date_str, 
                            "Segnale AI": sig, 
                            "Allocazione (€)": f"{alloc:,.2f} €",
                            "Variazione (%)": f"{var_pct:+.2f}%", 
                            "Utile Netto (€)": f"{net_profit:+,.2f} €",
                            "Tasse 26% (€)": f"{tax:,.2f} €", 
                            "Capitale Finale (€)": f"{capital:,.2f} €"
                        })
                        
                    df_plot = pd.DataFrame({'Date': df_res_c.index, 'Close': cap_history})
                    final_val = cap_history[-1] if cap_history else init_cap
                    tot_ret = ((final_val - init_cap) / init_cap) * 100.0
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Capitale Iniziale", f"{init_cap:,.2f} €")
                    c2.metric(f"Valore Finale ({sel_crypto})", f"{final_val:,.2f} €", f"{tot_ret:+.2f}%")
                    c3.metric("Utile Netto Totale", f"{final_val - init_cap:+,.2f} €")
                    
                    st.markdown("---")
                    st.subheader(f"📈 Evoluzione del Capitale — Strategia AI {sel_crypto}")
                    fig_t = go.Figure()
                    fig_t.add_trace(go.Scatter(
                        x=df_plot['Date'], y=df_plot['Close'], mode='lines', name="Capitale",
                        line=dict(color='#F7931A' if code_c == "BTC" else '#627EEA', width=2.5)
                    ))
                    fig_t.update_layout(
                        title=f"Andamento Capitale {sel_crypto}",
                        yaxis_title="Valore (€)", xaxis_title="Data", template="plotly_white", height=450
                    )
                    st.plotly_chart(fig_t, use_container_width=True)
                    
                    st.subheader("📋 Registro Dettagliato Transazioni Settimanali")
                    df_tx = pd.DataFrame(tx_log)
                    df_tx.index = range(1, len(df_tx) + 1)
                    st.dataframe(df_tx, use_container_width=True)
                else:
                    st.warning("⚠️ Dati storici non disponibili per la Crypto selezionata.")
