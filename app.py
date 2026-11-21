import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re
import requests

# Import yfinance per i dati storici
try:
    import yfinance as yf
except ImportError:
    yf = None

st.set_page_config(page_title="Quantamentale System", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stMetricDelta"] svg {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Menu di navigazione laterale
st.sidebar.title("📌 Navigazione")
modulo = st.sidebar.radio(
    "Seleziona Modulo:",
    [
        "🏆 Rotazione ETF & Grafici Dettagliati",
        "🔄 Correlazione ETF",
        "💼 Portafoglio / Paper Trading",
        "₿ Crypto (BTC & ETH)"
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
        "southafrica": "sudafrica",
        "arabia": "arabiasaudita",
        "saudiarabia": "arabiasaudita"
    }
    return aliases.get(n, n)

BLACKLIST_OOS = ["Argentina", "Cina", "Corea del Sud", "Corea", "Brasile", "Indonesia"]

meta_etfs = {
    "Arabia Saudita": {"Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita"},
    "Arabia": {"Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita"},
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

def get_etf_meta(paese):
    if paese in meta_etfs:
        return meta_etfs[paese]
    p_clean = clean_country_name(paese)
    if p_clean == "arabiasaudita":
        return {"Ticker_YF": "KSA", "Sheet_ETF": "Arabia Saudita"}
    return {"Ticker_YF": "SPY", "Sheet_ETF": paese}

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
            # LETTURA RIGOROSA DAL FOGLIO MENSILE (Forecast Month)
            df_fc = pd.read_excel(db_file, sheet_name="Forecast Month")

            if 'Data' in df_fc.columns:
                df_fc['Data'] = pd.to_datetime(df_fc['Data'])
                latest_date = df_fc['Data'].max()
                df_fc = df_fc[df_fc['Data'] == latest_date]

            for _, row in df_fc.dropna(subset=['Country', 'Previsione']).iterrows():
                paese = str(row['Country']).strip()
                fc_str = str(row['Previsione']).strip()

                match = re.search(r'([\d\.,]+)', fc_str)
                if match:
                    num_str = match.group(1).replace('.', '').replace(',', '.')
                    try:
                        prob = float(num_str)
                    except ValueError:
                        prob = 50.0
                else:
                    prob = 50.0

                segnal = "DOWN" if "DOWN" in fc_str.upper() else "UP"

                meta = get_etf_meta(paese)
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

@st.cache_data(ttl=3600)
def get_global_fear_and_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        return int(r.json()['data'][0]['value'])
    except Exception:
        return 50

@st.cache_data(ttl=3600)
def get_crypto_confluence_auto(crypto_code, fng_val):
    symbol = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
    if yf is None:
        return None

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1wk")
        if df.empty:
            return None

        close = df['Close']
        current_price = float(close.iloc[-1])
        prev_week_close = float(close.iloc[-2]) if len(close) >= 2 else current_price
        diff_vs_prev_pct = ((current_price - prev_week_close) / prev_week_close) * 100.0 if prev_week_close > 0 else 0.0

        sma_21 = float(close.rolling(window=21).mean().iloc[-1])
        sma_50 = float(close.rolling(window=50).mean().iloc[-1])

        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])

        # MACD Hist
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = float((macd - signal).iloc[-1])

        # Pilastro 1: Tecnico (0-3 Punti)
        p1_sma = 1 if (current_price > sma_21 and current_price > sma_50) else 0
        p1_macd = 1 if macd_hist > 0 else 0
        p1_rsi = 1 if (50 <= rsi_14 <= 70) else 0
        p1_score = p1_sma + p1_macd + p1_rsi

        # Pilastro 2: Sentiment (0-3 Punti)
        p2_fng = 1 if (30 <= fng_val <= 65) else 0
        p2_not_greed = 1 if fng_val < 78 else 0
        p2_score = min(3, p2_fng + p2_not_greed + 1)

        # Pilastro 3: Macro (DXY Index) (0-3 Punti)
        try:
            dxy_df = yf.Ticker("^NYICDX").history(period="3m", interval="1wk")['Close']
            dxy_weak = 1 if dxy_df.iloc[-1] < dxy_df.iloc[-4] else 0
        except Exception:
            dxy_weak = 1
        p3_score = min(3, dxy_weak + 2)

        total_score = p1_score + p2_score + p3_score

        df_ind = pd.DataFrame({
            "Indicatore": ["Chiusura Sett. Prec.", "Var. vs Chiusura Prec.", "RSI (14)", "MACD Hist", "SMA 21", "SMA 50"],
            "Valore Ufficiale": [
                f"${prev_week_close:,.2f}",
                f"{diff_vs_prev_pct:+.2f}%",
                f"{rsi_14:.2f}",
                f"{macd_hist:+.2f}",
                f"${sma_21:,.2f}",
                f"${sma_50:,.2f}"
            ]
        })
        df_ind.index = df_ind.index + 1

        return {
            "price": current_price,
            "prev_week_close": prev_week_close,
            "rsi": rsi_14,
            "p1": p1_score,
            "p2": p2_score,
            "p3": p3_score,
            "total": total_score,
            "df_ind": df_ind
        }
    except Exception:
        return None

# SENZA CACHE per leggere sempre i dati aggiornati dal foglio Excel
def load_crypto_indicators(crypto_code):
    db_file = find_excel_file("DataBase.xlsx")

    if db_file:
        try:
            df_c = pd.read_excel(db_file, sheet_name="Tecnica Crypto S").dropna(subset=["Crypto"])
            sub = df_c[df_c["Crypto"] == crypto_code].copy()

            if not sub.empty:
                if 'Data' in sub.columns:
                    sub['Data'] = pd.to_datetime(sub['Data'])
                    sub = sub.sort_values(by='Data', ascending=False)

                for _, row in sub.iterrows():
                    predict_val = str(row.get("Predict", "")).strip()
                    if predict_val and predict_val != "nan":
                        match = re.search(r'([\d\.,]+)', predict_val)
                        if match:
                            num_str = match.group(1).replace('.', '').replace(',', '.')
                            try:
                                prob_num = float(num_str)
                            except ValueError:
                                prob_num = 50.0
                        else:
                            prob_num = 60.0 if "UP" in predict_val.upper() else 40.0

                        return prob_num, predict_val
        except Exception:
            pass

    return 0.0, "⚠️ In attesa di aggiornamento DB"

df_all = load_all_data()

# =============================================================================
# PAGINA 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI
# =============================================================================
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati":
    st.title("🏆 Rotazione ETF & Tripla Confluenza Quantamentale")
    st.markdown("---")

    st.subheader("📊 Tabella Confluenza Quantamentale")
    solo_validati = st.checkbox("Mostra solo segnali Validati (✅)", value=False)
    df_tab_view = df_all[df_all["Stato OOS"] == "✅ Valido"] if solo_validati else df_all

    st.dataframe(
        df_tab_view[["Paese", "Esito AI", "Allocazione", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]],
        use_container_width=True
    )

    st.markdown("---")

    st.subheader("📌 Nuvolette di Sintesi")
    c1, c2, c3, c4 = st.columns(4)

    best_up = df_all[df_all["Segnale"] == "UP"].iloc[0] if not df_all[df_all["Segnale"] == "UP"].empty else df_all.iloc[0]
    c1.metric("🟢 Migliore UP", best_up["Paese"], best_up["Esito AI"])

    down_df = df_all[df_all["Segnale"] == "DOWN"].sort_values(by="Prob_UP", ascending=False)
    best_down = down_df.iloc[0] if not down_df.empty else df_all.iloc[-1]
    c2.metric("🔴 Migliore DOWN", best_down["Paese"], best_down["Esito AI"], delta_color="inverse")

    best_mom = df_all.sort_values(by="Mom_1M_num", ascending=False).iloc[0]
    c3.metric("🚀 Migliore del Mese (Prezzo)", best_mom["Paese"], best_mom["Mom_1M"])

    worst_mom = df_all.sort_values(by="Mom_1M_num", ascending=True).iloc[0]
    c4.metric(
        "📉 Peggiore del Mese (Prezzo)",
        worst_mom["Paese"],
        worst_mom["Mom_1M"],
        delta_color="inverse" if worst_mom["Mom_1M_num"] < 0 else "normal"
    )

    st.markdown("---")

    st.subheader("📈 Grafico Storico Avanzato ETF Paese")

    col_sel1, col_sel2 = st.columns([2, 1.5])
    selected_country = col_sel1.selectbox("Seleziona ETF Paese:", df_all["Paese"].tolist())
    chart_type = col_sel2.radio("Tipo Grafico:", ["Linea", "Candele (Candlestick)"], horizontal=True)

    horizon_etf = st.radio(
        "Orizzonte Temporale:",
        ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"],
        index=3,
        horizontal=True
    )

    row_country = df_all[df_all["Paese"] == selected_country].iloc[0]
    df_chart = load_etf_history(row_country["Ticker_YF"])

    if df_chart is not None and not df_chart.empty:
        df_filt, p_start, p_end, ret_pct = filter_by_horizon(df_chart, horizon_etf)

        recent_closes = df_chart['Close'].tail(60)
        daily_rets = recent_closes.pct_change().dropna()
        vol_monthly = float(daily_rets.std() * np.sqrt(21)) if len(daily_rets) > 10 else 0.05

        stop_loss_price = p_end * (1.0 - max(0.03, vol_monthly * 1.2))
        take_profit_price = p_end * (1.0 + max(0.06, vol_monthly * 2.0))
        sl_dist_pct = ((p_end - stop_loss_price) / p_end) * 100.0 if p_end > 0 else 0.0
        tp_dist_pct = ((take_profit_price - p_end) / p_end) * 100.0 if p_end > 0 else 0.0

        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric(
            f"Performance ({horizon_etf})",
            f"{ret_pct:+.2f}%",
            f"Finale: ${p_end:,.2f}",
            delta_color="inverse" if ret_pct < 0 else "normal"
        )
        m_col2.metric(
            "Esito AI",
            row_country['Esito AI'],
            delta_color="inverse" if row_country['Segnale'] == "DOWN" else "normal"
        )
        m_col3.metric("Stato OOS / Voto Macro", f"{row_country['Stato OOS']} | Voto: {row_country['Voto_Macro']}")

        sl_col1, sl_col2 = st.columns(2)
        sl_col1.metric("🛑 Stop Loss del Mese (Consigliato)", f"${stop_loss_price:,.2f}", f"-{sl_dist_pct:.2f}%", delta_color="inverse")
        sl_col2.metric("🎯 Take Profit del Mese (Consigliato)", f"${take_profit_price:,.2f}", f"+{tp_dist_pct:.2f}%")

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

        fig.add_hline(
            y=stop_loss_price, line_dash="dash", line_color="#ef5350", line_width=2,
            annotation_text=f"Stop Loss: ${stop_loss_price:,.2f}", annotation_position="bottom right"
        )
        fig.add_hline(
            y=take_profit_price, line_dash="dash", line_color="#ef5350", line_width=2,
            annotation_text=f"Take Profit: ${take_profit_price:,.2f}", annotation_position="top right"
        )

        fig.update_layout(
            title=dict(text=f"<b>Grafico Prezzi {selected_country} ({row_country['Ticker_YF']}) con Livelli Operativi</b>", font=dict(size=16)),
            yaxis_title="Prezzo ($)", xaxis_title="Data", template="plotly_white", height=520,
            margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
            yaxis=dict(type="linear", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Impossibile scaricare lo storico dati per l'ETF selezionato.")

# =============================================================================
# PAGINA 2: CORRELAZIONE ETF
# =============================================================================
elif modulo == "🔄 Correlazione ETF":
    st.title("🔄 Correlazione & Diversificazione ETF")
    st.markdown("---")

    # --- 1. CONFRONTO A 2 PAESI + ROLLING CORRELATION + ALERT ---
    st.subheader("⚖️ Confronto Diretto & Finestra Mobile (Rolling Correlation)")
    st.write("Seleziona due Paesi e una finestra temporale per analizzare correlazione, cambi di regime e rischio di concentrazione.")

    col1, col2, col_win = st.columns([2, 2, 1.5])
    paesi_disponibili = df_all["Paese"].tolist()
    country1 = col1.selectbox("Seleziona Primo Paese:", paesi_disponibili, index=0)
    country2 = col2.selectbox("Seleziona Secondo Paese:", paesi_disponibili, index=1 if len(paesi_disponibili) > 1 else 0)

    finestre_giorni = {
        "30 Giorni": 30,
        "3 Mesi (63g)": 63,
        "6 Mesi (126g)": 126,
        "1 Anno (252g)": 252,
        "Tutto lo Storico": None
    }
    scelta_finestra = col_win.selectbox("Finestra Analisi / Rolling:", list(finestre_giorni.keys()), index=1)
    win_days = finestre_giorni[scelta_finestra]

    soglia_over = st.slider("Soglia Alert Over-Concentrazione:", min_value=0.60, max_value=0.95, value=0.85, step=0.05)

    row1 = df_all[df_all["Paese"] == country1].iloc[0]
    row2 = df_all[df_all["Paese"] == country2].iloc[0]

    df_h1 = load_etf_history(row1["Ticker_YF"])
    df_h2 = load_etf_history(row2["Ticker_YF"])

    corr_val = 0.0
    corr_3m_check = None
    df_merged = None
    rolling_series = None

    if df_h1 is not None and df_h2 is not None and not df_h1.empty and not df_h2.empty:
        df_merged = pd.merge(
            df_h1[['Date', 'Close']],
            df_h2[['Date', 'Close']],
            on='Date',
            suffixes=(f'_{country1}', f'_{country2}')
        ).sort_values('Date').dropna()

        if len(df_merged) > 15:
            ret1 = df_merged[f'Close_{country1}'].pct_change()
            ret2 = df_merged[f'Close_{country2}'].pct_change()
            rets_df = pd.DataFrame({'Date': df_merged['Date'], 'r1': ret1, 'r2': ret2}).dropna()

            # Controllo specifico a ~3 mesi (63 giorni) per l'alert di concentrazione
            if len(rets_df) >= 63:
                corr_3m_check = float(rets_df['r1'].tail(63).corr(rets_df['r2'].tail(63)))

            if win_days is not None and len(rets_df) >= win_days:
                sub_rets = rets_df.tail(win_days)
                corr_val = float(sub_rets['r1'].corr(sub_rets['r2']))
            else:
                corr_val = float(rets_df['r1'].corr(rets_df['r2']))

            roll_win = win_days if win_days is not None else min(63, max(15, len(rets_df) // 4))
            if len(rets_df) > roll_win:
                rolling_series = pd.DataFrame({
                    'Date': rets_df['Date'],
                    'Rolling_Corr': rets_df['r1'].rolling(window=roll_win).corr(rets_df['r2'])
                }).dropna()

    # Alert di Over-Concentrazione
    val_da_controllare = corr_3m_check if corr_3m_check is not None else corr_val
    if country1 != country2 and val_da_controllare is not None and val_da_controllare > soglia_over:
        st.warning(
            f"⚠️ **Attenzione: stai duplicando il rischio geografico/fattoriale.** "
            f"La correlazione tra **{country1}** e **{country2}** è **{val_da_controllare:.2f}** "
            f"(sopra la soglia critica di {soglia_over:.2f})."
        )

    st.subheader("📊 Indice di Correlazione")
    if corr_val > 0.7:
        corr_label = "Forte Correlazione Positiva 🔴 (Muovono insieme)"
    elif corr_val > 0.3:
        corr_label = "Moderata Correlazione Positiva 🟡"
    elif corr_val > -0.3:
        corr_label = "Decorrelati 🟢 (Ottimi per Diversificare)"
    else:
        corr_label = "Correlazione Inversa 🔵 (Muovono in direzioni opposte)"

    st.metric(
        label=f"Correlazione ({country1} vs {country2}) — {scelta_finestra}",
        value=f"{corr_val:.2f}",
        delta=corr_label,
        delta_color="off"
    )

    if rolling_series is not None and not rolling_series.empty:
        fig_roll = go.Figure()
        fig_roll.add_trace(go.Scatter(
            x=rolling_series['Date'],
            y=rolling_series['Rolling_Corr'],
            mode='lines',
            name=f"Rolling Corr ({scelta_finestra})",
            line=dict(color='#7B1FA2', width=2)
        ))
        fig_roll.add_hline(y=soglia_over, line_dash="dash", line_color="#ef5350", annotation_text=f"Soglia {soglia_over:.2f}")
        fig_roll.add_hline(y=0, line_dash="dot", line_color="#888888")
        fig_roll.update_layout(
            title=dict(text=f"<b>Rolling Correlation nel Tempo: {country1} vs {country2}</b>", font=dict(size=15)),
            yaxis_title="Correlazione",
            yaxis=dict(range=[-1.05, 1.05], showgrid=True, gridcolor='#F0F2F5'),
            xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
            template="plotly_white",
            height=340,
            margin=dict(l=30, r=30, t=45, b=30)
        )
        st.plotly_chart(fig_roll, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Confronto Diretto Metriche")
    df_comp = pd.DataFrame([row1, row2])[["Paese", "Esito AI", "Stato OOS", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M", "Sintesi"]]
    df_comp.index = range(1, len(df_comp) + 1)
    st.dataframe(df_comp, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Grafico Comparativo dei Prezzi (Base 100)")

    if df_merged is not None and not df_merged.empty:
        df_plot_base = df_merged.tail(win_days).copy() if (win_days is not None and len(df_merged) >= win_days) else df_merged.copy()
        p1_col = f'Close_{country1}'
        p2_col = f'Close_{country2}'

        df_plot_base['Norm1'] = (df_plot_base[p1_col] / df_plot_base[p1_col].iloc[0]) * 100
        df_plot_base['Norm2'] = (df_plot_base[p2_col] / df_plot_base[p2_col].iloc[0]) * 100

        fig_corr = go.Figure()
        fig_corr.add_trace(go.Scatter(
            x=df_plot_base['Date'], y=df_plot_base['Norm1'], mode='lines',
            name=f"{country1} ({row1['Ticker_YF']})", line=dict(color='#2962FF', width=2)
        ))
        fig_corr.add_trace(go.Scatter(
            x=df_plot_base['Date'], y=df_plot_base['Norm2'], mode='lines',
            name=f"{country2} ({row2['Ticker_YF']})", line=dict(color='#FF6D00', width=2)
        ))

        fig_corr.update_layout(
            title=dict(text=f"<b>Andamento Comparativo (Base 100): {country1} vs {country2}</b>", font=dict(size=16)),
            yaxis_title="Valore Normalizzato (Base 100)", xaxis_title="Data", template="plotly_white", height=460,
            margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
            yaxis=dict(showgrid=True, gridcolor='#F0F2F5'), showlegend=True
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.warning("⚠️ Dati storici insufficienti per generare il grafico comparativo.")

    # --- 2. MATRICE DI CORRELAZIONE DINAMICA (HEATMAP PANIERE) ---
    st.markdown("---")
    st.subheader("🗺️ Matrice di Correlazione Dinamica (Heatmap Paniere)")
    st.write("Seleziona da 2 a 10 ETF/Paesi per visualizzare la matrice delle correlazioni sui rendimenti nella finestra scelta.")

    default_basket = [p for p in ["USA", "Germania", "Giappone", "India", "Brasile", "Regno unito"] if p in paesi_disponibili]
    if not default_basket:
        default_basket = paesi_disponibili[:min(6, len(paesi_disponibili))]

    selected_basket = st.multiselect(
        "Paniere Asset (max 10 consigliati):",
        options=paesi_disponibili,
        default=default_basket,
        max_selections=10
    )

    if len(selected_basket) >= 2:
        returns_dict = {}
        for p in selected_basket:
            r_info = df_all[df_all["Paese"] == p].iloc[0]
            h_df = load_etf_history(r_info["Ticker_YF"])
            if h_df is not None and not h_df.empty:
                s_close = h_df.sort_values('Date').set_index('Date')['Close'].pct_change()
                if win_days is not None:
                    s_close = s_close.tail(win_days)
                returns_dict[p] = s_close

        if len(returns_dict) >= 2:
            df_basket_rets = pd.DataFrame(returns_dict).dropna(how='all')
            corr_matrix = df_basket_rets.corr()

            # Controllo coppie sopra soglia nella matrice
            high_pairs = []
            cols_m = corr_matrix.columns.tolist()
            for i in range(len(cols_m)):
                for j in range(i + 1, len(cols_m)):
                    v = corr_matrix.iloc[i, j]
                    if pd.notna(v) and v > soglia_over:
                        high_pairs.append(f"{cols_m[i]} – {cols_m[j]} ({v:.2f})")

            if high_pairs:
                st.warning(
                    f"⚠️ **Over-Concentrazione rilevata nel paniere (>{soglia_over:.2f}):** "
                    + ", ".join(high_pairs)
                )

            fig_heat = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                zmin=-1,
                zmax=1,
                colorscale=[
                    [0.0, "#d32f2f"],   # Rosso per correlazione negativa forte
                    [0.5, "#f5f5f5"],   # Neutro vicino a 0
                    [1.0, "#2e7d32"]    # Verde per correlazione positiva forte
                ],
                text=np.round(corr_matrix.values, 2),
                texttemplate="%{text}",
                textfont={"size": 11},
                hovertemplate="<b>%{y}</b> vs <b>%{x}</b><br>Correlazione: %{z:.2f}<extra></extra>"
            ))

            fig_heat.update_layout(
                title=dict(text=f"<b>Heatmap Correlazioni ({scelta_finestra})</b>", font=dict(size=16)),
                template="plotly_white",
                height=520,
                margin=dict(l=40, r=30, t=55, b=40)
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Dati storici insufficienti per calcolare la matrice del paniere selezionato.")
    else:
        st.info("Seleziona almeno 2 Paesi/ETF per generare la matrice di correlazione.")

# =============================================================================
# PAGINA 3: PORTAFOGLIO / PAPER TRADING AVANZATO
# =============================================================================
elif modulo == "💼 Portafoglio / Paper Trading":
    st.title("💼 Portafoglio Simulato & Paper Trading")
    st.markdown("---")
    st.write("Componi un portafoglio fittizio combinando ETF Paese e Crypto per stimare correlazione complessiva, spinta statistica AI e profilo di rischio.")

    # 1. Capitale simulato e orizzonte di analisi
    c_top1, c_top2 = st.columns([1.5, 2.5])
    capitale_totale = c_top1.number_input("Capitale Simulato (€):", min_value=100, max_value=1000000, value=1000, step=100)
    orizzonte_ptf = c_top2.radio(
        "Finestra Storica per Rischio & Correlazione:",
        ["3 Mesi (63g)", "6 Mesi (126g)", "1 Anno (252g)", "3 Anni (756g)"],
        index=2,
        horizontal=True
    )
    map_days_ptf = {
        "3 Mesi (63g)": 63,
        "6 Mesi (126g)": 126,
        "1 Anno (252g)": 252,
        "3 Anni (756g)": 756
    }
    days_ptf = map_days_ptf[orizzonte_ptf]

    st.markdown("---")
    st.subheader("🧩 1. Selezione Asset & Allocazione Pesi (%)")

    # Prepara catalogo unificato (ETF da df_all + Crypto)
    paesi_list = df_all["Paese"].tolist()
    opzioni_asset = [f"ETF: {p}" for p in paesi_list] + ["Crypto: BTC", "Crypto: ETH"]

    default_ptf = []
    for p_def in ["USA", "Germania", "India"]:
        if p_def in paesi_list:
            default_ptf.append(f"ETF: {p_def}")
    default_ptf.append("Crypto: BTC")

    asset_scelti = st.multiselect(
        "Scegli gli asset da inserire in portafoglio:",
        options=opzioni_asset,
        default=default_ptf
    )

    if len(asset_scelti) < 2:
        st.info("Seleziona almeno 2 asset per calcolare correlazione e metriche di portafoglio.")
    else:
        peso_iniziale = int(100 // len(asset_scelti))
        resto = 100 - (peso_iniziale * len(asset_scelti))

        # Inizializza pesi in session_state per consentire anche la normalizzazione con un clic
        for idx, asset_label in enumerate(asset_scelti):
            k_state = f"peso_{asset_label}"
            if k_state not in st.session_state:
                st.session_state[k_state] = peso_iniziale + (resto if idx == 0 else 0)

        st.write("Imposta i pesi percentuali per ciascun asset (la somma deve essere **100%**):")
        pesi_dict = {}
        cols_w = st.columns(min(4, len(asset_scelti)))

        for idx, asset_label in enumerate(asset_scelti):
            col_curr = cols_w[idx % len(cols_w)]
            k_state = f"peso_{asset_label}"
            pesi_dict[asset_label] = col_curr.number_input(
                f"{asset_label} (%)",
                min_value=0,
                max_value=100,
                step=5,
                key=k_state
            )

        somma_pesi = sum(pesi_dict.values())

        if somma_pesi != 100:
            st.error(f"⚠️ La somma attuale dei pesi è **{somma_pesi}%**. Regola i valori affinché il totale sia esattamente **100%**.")
            if st.button("⚖️ Normalizza al 100%"):
                if somma_pesi > 0:
                    grezzi = {k: (v / somma_pesi) * 100.0 for k, v in pesi_dict.items()}
                    arrotondati = {k: int(round(v)) for k, v in grezzi.items()}
                    diff_100 = 100 - sum(arrotondati.values())
                    if diff_100 != 0 and len(arrotondati) > 0:
                        chiave_max = max(arrotondati.keys(), key=lambda k: arrotondati[k])
                        arrotondati[chiave_max] = max(0, arrotondati[chiave_max] + diff_100)
                    for k, val_norm in arrotondati.items():
                        st.session_state[f"peso_{k}"] = val_norm
                else:
                    for idx_n, k in enumerate(pesi_dict.keys()):
                        st.session_state[f"peso_{k}"] = peso_iniziale + (resto if idx_n == 0 else 0)
                st.rerun()
        else:
            # Raccolta probabilità AI, segnali e serie storiche dei rendimenti
            prob_num_btc, prob_str_btc = load_crypto_indicators("BTC")
            prob_num_eth, prob_str_eth = load_crypto_indicators("ETH")

            returns_map = {}
            dettagli_righe = []
            quota_crypto = 0.0
            prob_up_ponderata = 0.0

            for asset_label, w_pct in pesi_dict.items():
                w = w_pct / 100.0
                if w == 0:
                    continue

                if asset_label.startswith("ETF: "):
                    paese_nome = asset_label.replace("ETF: ", "")
                    r_row = df_all[df_all["Paese"] == paese_nome].iloc[0]
                    ticker_curr = r_row["Ticker_YF"]
                    segnale_curr = r_row["Segnale"]
                    prob_raw = float(r_row["Prob_UP"])
                    prob_up_eff = prob_raw if segnale_curr == "UP" else (100.0 - prob_raw)
                    stato_curr = r_row["Stato OOS"]

                    hist_df = load_etf_history(ticker_curr)
                    if hist_df is not None and not hist_df.empty:
                        s_ret = hist_df.sort_values("Date").set_index("Date")["Close"].pct_change().dropna().tail(days_ptf)
                        returns_map[asset_label] = s_ret

                else:
                    crypto_code = asset_label.replace("Crypto: ", "")
                    quota_crypto += w_pct
                    ticker_curr = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
                    prob_raw = prob_num_btc if crypto_code == "BTC" else prob_num_eth
                    prob_str_c = prob_str_btc if crypto_code == "BTC" else prob_str_eth
                    segnale_curr = "DOWN" if "DOWN" in prob_str_c.upper() else ("UP" if "UP" in prob_str_c.upper() else "NEUTRO")

                    if prob_raw > 0:
                        prob_up_eff = prob_raw if segnale_curr == "UP" else (100.0 - prob_raw if segnale_curr == "DOWN" else 50.0)
                    else:
                        prob_up_eff = 50.0
                    stato_curr = "Settimanale"

                    if yf is not None:
                        try:
                            df_c_daily = yf.Ticker(ticker_curr).history(period="5y")
                            if not df_c_daily.empty:
                                df_c_daily = df_c_daily.reset_index()
                                d_col = [c for c in df_c_daily.columns if "date" in c.lower()][0]
                                df_c_daily[d_col] = strip_timezone(df_c_daily[d_col])
                                s_ret = df_c_daily.sort_values(d_col).set_index(d_col)["Close"].pct_change().dropna().tail(days_ptf)
                                returns_map[asset_label] = s_ret
                        except Exception:
                            pass

                prob_up_ponderata += w * prob_up_eff
                dettagli_righe.append({
                    "Asset": asset_label,
                    "Ticker": ticker_curr,
                    "Peso": f"{w_pct}%",
                    "Importo (€)": round(capitale_totale * w, 2),
                    "Segnale AI": segnale_curr,
                    "Prob. Rialzo Stimata": f"{prob_up_eff:.1f}%",
                    "Note / Filtro": stato_curr
                })

            corr_media_ptf = 0.0
            vol_annua_ptf = 0.0
            corr_mat_ptf = None

            valid_assets = [k for k in returns_map.keys() if pesi_dict[k] > 0]
            if len(valid_assets) >= 2:
                df_rets_ptf = pd.DataFrame({k: returns_map[k] for k in valid_assets}).dropna()
                if len(df_rets_ptf) > 15:
                    w_vec = np.array([pesi_dict[k] / 100.0 for k in valid_assets])
                    w_vec = w_vec / w_vec.sum()

                    corr_mat_ptf = df_rets_ptf.corr()
                    cov_mat_ann = df_rets_ptf.cov() * 252.0

                    vol_annua_ptf = float(np.sqrt(np.dot(w_vec.T, np.dot(cov_mat_ann.values, w_vec)))) * 100.0

                    num_corr = 0.0
                    den_corr = 0.0
                    for i in range(len(valid_assets)):
                        for j in range(i + 1, len(valid_assets)):
                            wij = w_vec[i] * w_vec[j]
                            num_corr += wij * corr_mat_ptf.iloc[i, j]
                            den_corr += wij
                    corr_media_ptf = float(num_corr / den_corr) if den_corr > 0 else 0.0

            if vol_annua_ptf >= 28.0 or quota_crypto >= 35.0:
                profilo_rischio = "🔴 Aggressivo"
                desc_rischio = "Alta volatilità / forte esposizione crypto"
            elif vol_annua_ptf >= 18.0 or quota_crypto >= 15.0:
                profilo_rischio = "🟠 Dinamico"
                desc_rischio = "Crescita con oscillazioni marcate"
            elif vol_annua_ptf >= 11.0:
                profilo_rischio = "🟡 Bilanciato / Moderato"
                desc_rischio = "Buon equilibrio rischio/diversificazione"
            else:
                profilo_rischio = "🟢 Conservativo"
                desc_rischio = "Bassa volatilità storica"

            st.markdown("---")
            st.subheader("📊 2. Metriche Sintetiche di Portafoglio")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                "Correlazione Complessiva",
                f"{corr_media_ptf:.2f}",
                "Ben diversificato" if corr_media_ptf < 0.45 else ("Moderata" if corr_media_ptf < 0.70 else "Alta concentrazione")
            )
            m2.metric(
                "Prob. Media Ponderata UP",
                f"{prob_up_ponderata:.1f}%",
                "Spinta rialzista" if prob_up_ponderata >= 55.0 else "Cautela / Difensivo"
            )
            m3.metric(
                "Profilo di Rischio",
                profilo_rischio,
                f"Volatilità annua: {vol_annua_ptf:.1f}%"
            )
            m4.metric(
                "Esposizione Crypto",
                f"{quota_crypto:.0f}%",
                desc_rischio,
                delta_color="off"
            )

            esclusi_in_ptf = [r["Asset"] for r in dettagli_righe if "Escluso" in str(r["Note / Filtro"])]
            if esclusi_in_ptf:
                st.warning(
                    f"⚠️ **Nota Filtro OOS:** Hai inserito asset esclusi per bassa accuratezza storica ({', '.join(esclusi_in_ptf)}). "
                    "Valuta se ridurne il peso o sostituirli con paesi validati."
                )

            st.markdown("---")
            st.subheader("📋 3. Riepilogo Allocazione & Grafici")

            col_tab, col_pie = st.columns([1.6, 1])
            df_dettagli = pd.DataFrame(dettagli_righe)
            df_dettagli.index = range(1, len(df_dettagli) + 1)
            col_tab.dataframe(df_dettagli, use_container_width=True)

            fig_pie = go.Figure(data=[go.Pie(
                labels=df_dettagli["Asset"],
                values=[pesi_dict[a] for a in df_dettagli["Asset"]],
                hole=0.45,
                textinfo="label+percent"
            )])
            fig_pie.update_layout(
                title=dict(text="<b>Ripartizione Portafoglio</b>", font=dict(size=14)),
                template="plotly_white",
                height=340,
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False
            )
            col_pie.plotly_chart(fig_pie, use_container_width=True)

            # Grafico storico simulato del portafoglio (Base 100) + Max DD + Sharpe + Benchmark SPY
            if len(valid_assets) >= 2 and 'df_rets_ptf' in locals() and not df_rets_ptf.empty:
                ptf_daily_ret = df_rets_ptf.dot(w_vec)
                ptf_equity_raw = (1.0 + ptf_daily_ret).cumprod() * 100.0
                # Normalizza esattamente a 100 alla prima data utile della finestra scelta
                ptf_equity = (ptf_equity_raw / float(ptf_equity_raw.iloc[0])) * 100.0

                val_iniziale = float(ptf_equity.iloc[0])
                val_finale = float(ptf_equity.iloc[-1])
                perf_pct = ((val_finale - val_iniziale) / val_iniziale) * 100.0 if val_iniziale > 0 else 0.0
                capitale_finale = capitale_totale * (val_finale / val_iniziale) if val_iniziale > 0 else capitale_totale
                pnl_euro = capitale_finale - capitale_totale

                # Maximum Drawdown (%)
                roll_max = ptf_equity.cummax()
                drawdown_series = (ptf_equity / roll_max) - 1.0
                max_dd_pct = float(drawdown_series.min()) * 100.0

                # Sharpe Ratio annualizzato (rf = 0% per semplicità)
                ret_std_daily = float(ptf_daily_ret.std())
                ret_mean_daily = float(ptf_daily_ret.mean())
                sharpe_ratio = ((ret_mean_daily * 252.0) / (ret_std_daily * np.sqrt(252.0))) if ret_std_daily > 0 else 0.0

                st.markdown("---")
                st.subheader(f"📈 4. Performance Storica Simulata ({orizzonte_ptf})")

                p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
                p_col1.metric(
                    f"Profitto / Perdita ({orizzonte_ptf})",
                    f"{perf_pct:+.2f}%",
                    f"{pnl_euro:+,.2f} €",
                    delta_color="inverse" if perf_pct < 0 else "normal"
                )
                p_col2.metric(
                    "Controvalore Finale",
                    f"{capitale_finale:,.2f} €",
                    f"Iniziale: {capitale_totale:,.0f} €",
                    delta_color="off"
                )
                p_col3.metric(
                    "Max Drawdown",
                    f"{max_dd_pct:.2f}%",
                    "Picco-Fondo nel periodo",
                    delta_color="inverse"
                )
                p_col4.metric(
                    "Sharpe Ratio (rf=0%)",
                    f"{sharpe_ratio:.2f}",
                    "Rendimento / Rischio",
                    delta_color="off"
                )
                p_col5.metric(
                    "Indice Finale (Base 100)",
                    f"{val_finale:.2f}",
                    f"Start: {val_iniziale:.1f}",
                    delta_color="off"
                )

                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    x=ptf_equity.index,
                    y=ptf_equity.values,
                    mode="lines",
                    name="Portafoglio Simulato",
                    line=dict(color="#2e7d32" if perf_pct >= 0 else "#d32f2f", width=2.5)
                ))

                # Benchmark SPY (S&P 500) allineato alle stesse date e normalizzato esattamente a 100 all'inizio
                spy_hist = load_etf_history("SPY")
                if spy_hist is not None and not spy_hist.empty:
                    spy_s = spy_hist.sort_values("Date").set_index("Date")["Close"]
                    spy_aligned = spy_s.reindex(ptf_equity.index).ffill().bfill()
                    if len(spy_aligned) > 1 and float(spy_aligned.iloc[0]) > 0:
                        spy_equity = (spy_aligned / float(spy_aligned.iloc[0])) * 100.0
                        fig_eq.add_trace(go.Scatter(
                            x=spy_equity.index,
                            y=spy_equity.values,
                            mode="lines",
                            name="Benchmark SPY (Base 100)",
                            line=dict(color="#757575", width=2, dash="dash")
                        ))

                fig_eq.add_hline(y=100.0, line_dash="dot", line_color="#888888", annotation_text="Base 100")
                fig_eq.update_layout(
                    title=dict(text=f"<b>Andamento Storico Simulato vs Benchmark SPY (Base 100 — {orizzonte_ptf})</b>", font=dict(size=15)),
                    yaxis_title="Valore (Base 100)",
                    xaxis_title="Data",
                    template="plotly_white",
                    height=400,
                    margin=dict(l=30, r=30, t=45, b=30),
                    xaxis=dict(showgrid=True, gridcolor="#F0F2F5", type="date"),
                    yaxis=dict(showgrid=True, gridcolor="#F0F2F5"),
                    showlegend=True
                )
                st.plotly_chart(fig_eq, use_container_width=True)

# =============================================================================
# PAGINA 4: CRYPTO (BTC & ETH DETTAGLIATO + TRIPLA CONFLUENZA AUTOMATICA)
# =============================================================================
elif modulo == "₿ Crypto (BTC & ETH)":
    st.title("₿ Quantamentale Crypto — Tripla Confluenza & AI")
    st.markdown("---")

    global_fng = get_global_fear_and_greed()

    prob_num_btc, prob_str_btc = load_crypto_indicators("BTC")
    prob_num_eth, prob_str_eth = load_crypto_indicators("ETH")

    col_btc, col_eth = st.columns(2)

    with col_btc:
        st.markdown("### 🟡 Bitcoin (BTC)")
        btc_conf = get_crypto_confluence_auto("BTC", global_fng)

        if btc_conf:
            is_btc_down = "DOWN" in str(prob_str_btc).upper()
            st.metric(
                "Prezzo Attuale BTC",
                f"${btc_conf['price']:,.2f}",
                f"Previsione AI (DB): {prob_str_btc}",
                delta_color="inverse" if is_btc_down else "normal"
            )

            st.write("---")
            st.subheader(f"📊 Tripla Confluenza BTC: **{btc_conf['total']} / 9 Punti**")
            st.progress(btc_conf['total'] / 9)

            st.write(f"• Pilastro 1 (Tecnico & Momentum): **{btc_conf['p1']}/3**")
            st.write(f"• Pilastro 2 (Sentiment & On-Chain): **{btc_conf['p2']}/3**")
            st.write(f"• Pilastro 3 (Macro & Liquidità/DXY): **{btc_conf['p3']}/3**")

            if btc_conf['total'] >= 6 and prob_num_btc >= 60.0 and not is_btc_down:
                st.success(f"🟢 **SEGNALE OPERATIVO: COMPRA / UP**\n(AI: {prob_num_btc}% | Confluenza: {btc_conf['total']}/9)")
            else:
                st.warning(f"🔴 **SEGNALE OPERATIVO: LIQUIDITÀ / NEUTRO**\n(AI: {prob_str_btc} | Confluenza: {btc_conf['total']}/9)")

            st.write("---")
            st.dataframe(btc_conf['df_ind'], use_container_width=True)

    with col_eth:
        st.markdown("### 🔷 Ethereum (ETH)")
        eth_conf = get_crypto_confluence_auto("ETH", global_fng)

        if eth_conf:
            is_eth_down = "DOWN" in str(prob_str_eth).upper()
            st.metric(
                "Prezzo Attuale ETH",
                f"${eth_conf['price']:,.2f}",
                f"Previsione AI (DB): {prob_str_eth}",
                delta_color="inverse" if is_eth_down else "normal"
            )

            st.write("---")
            st.subheader(f"📊 Tripla Confluenza ETH: **{eth_conf['total']} / 9 Punti**")
            st.progress(eth_conf['total'] / 9)

            st.write(f"• Pilastro 1 (Tecnico & Momentum): **{eth_conf['p1']}/3**")
            st.write(f"• Pilastro 2 (Sentiment & On-Chain): **{eth_conf['p2']}/3**")
            st.write(f"• Pilastro 3 (Macro & Liquidità/DXY): **{eth_conf['p3']}/3**")

            if eth_conf['total'] >= 6 and prob_num_eth >= 60.0 and not is_eth_down:
                st.success(f"🟢 **SEGNALE OPERATIVO: COMPRA / UP**\n(AI: {prob_num_eth}% | Confluenza: {eth_conf['total']}/9)")
            else:
                st.warning(f"🔴 **SEGNALE OPERATIVO: LIQUIDITÀ / NEUTRO**\n(AI: {prob_str_eth} | Confluenza: {eth_conf['total']}/9)")

            st.write("---")
            st.dataframe(eth_conf['df_ind'], use_container_width=True)

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
        curr_prob_str = prob_str_btc if code_crypto == "BTC" else prob_str_eth
        is_curr_down = "DOWN" in str(curr_prob_str).upper()

        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric(f"Performance ({horizon_crypto})", f"{ret_c_pct:+.2f}%", f"Chiusura Settimanale: ${p_c_end:,.2f}")
        c_m2.metric(
            "Previsione AI Ufficiale (DB)",
            curr_prob_str,
            delta_color="inverse" if is_curr_down else "normal"
        )
        c_m3.metric("Crypto Fear & Greed Index", f"{global_fng} / 100")

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
