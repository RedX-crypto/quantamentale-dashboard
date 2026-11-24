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

# ------------------------------------------------------------------------------
# UTILITY PERCORSI & CARICAMENTO DATI
# ------------------------------------------------------------------------------
def find_excel_file(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    user_home = os.path.expanduser("~")
    base_sys = os.path.join(user_home, "Desktop", "System")
    base_scripts = os.path.join(base_sys, "01_Script_RStudio_Pyton_Terminal")

    search_paths = [
        os.path.join(script_dir, filename),
        filename,
        os.path.join(base_scripts, "ETF_Quant_RStudio", filename),
        os.path.join(base_scripts, "Crypto_Quant_RStudio", filename),
        os.path.join(base_sys, "02_Dati", filename),
        os.path.join(user_home, filename),
        os.path.join(user_home, "Desktop", filename),
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p

    if os.path.exists(base_sys):
        for root, _, files in os.walk(base_sys):
            if filename in files:
                return os.path.join(root, filename)
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
        "uk": "regnounito", "unitedkingdom": "regnounito",
        "usa": "america", "unitedstates": "america", "us": "america",
        "southkorea": "coreadelsud", "korea": "coreadelsud", "corea": "coreadelsud",
        "southafrica": "sudafrica",
        "arabia": "arabiasaudita", "saudiarabia": "arabiasaudita",
        "france": "francia"
    }
    return aliases.get(n, n)

fallback_tickers = {
    "Arabia": "IKSA.DE", "India": "NDIA.MI", "Germania": "MD4X.DE", "Taiwan": "DBX5.DE",
    "Spagna": "XESP.DE", "Francia": "IS3U.DE", "UK": "CUKX.L", "Italia": "ITAMID.MI",
    "Canada": "CSCA.MI", "America": "CSSPX.MI", "Sud Africa": "SRSA.MI", "Messico": "D5BI.DE",
    "Giappone": "VJPA.MI", "Argentina": "ALAT.MI", "Brasile": "4BRZ.DE", "Cina": "ICGA.DE",
    "Corea": "KOR.MI", "Indonesia": "INDO.MI"
}

@st.cache_data(ttl=3600)
def load_etf_history(ticker):
    if yf is not None and ticker:
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

@st.cache_data(ttl=3600)
def load_crypto_history(crypto_code, interval="1wk"):
    symbol = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
    if yf is not None:
        try:
            period_arg = "max" if interval == "1wk" else "5y"
            df_yf = yf.Ticker(symbol).history(period=period_arg, interval=interval)
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

    offset_map = {
        "1 Mese": pd.DateOffset(months=1),
        "3 Mesi": pd.DateOffset(months=3),
        "6 Mesi": pd.DateOffset(months=6),
        "1 Anno": pd.DateOffset(years=1),
        "3 Anni": pd.DateOffset(years=3),
        "5 Anni": pd.DateOffset(years=5),
    }
    start_target = last_date - offset_map[horizon] if horizon in offset_map else df_c['Date'].min()
    df_filtered = df_c[df_c['Date'] >= start_target].copy()
    if df_filtered.empty:
        df_filtered = df_c.tail(2).copy()

    p_start = float(df_filtered['Close'].iloc[0])
    p_end = float(df_filtered['Close'].iloc[-1])
    ret_pct = ((p_end - p_start) / p_start) * 100.0 if p_start > 0 else 0.0
    return df_filtered, p_start, p_end, ret_pct

@st.cache_data(ttl=1800)
def load_all_data():
    etf_file = find_excel_file("Archivio_ETF_Definitivo.xlsx")
    db_file = find_excel_file("DataBase.xlsx")
    records = []
    etf_last_month = "N/D"

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
                p_key = clean_country_name(row['Country'])
                voto_v = float(row['Voto']) if pd.notna(row['Voto']) else 2.50
                pil_raw = row['PIL'] if 'PIL' in row and pd.notna(row['PIL']) else None
                pil_v = f"{pil_raw * 100:+.2f}%" if isinstance(pil_raw, (int, float)) and abs(pil_raw) < 1 else (str(pil_raw) if pil_raw is not None else "N/D")
                pmi_cols = [c for c in df_latest.columns if 'pmi' in str(c).lower()]
                pmi_raw = row[pmi_cols[0]] if pmi_cols and pd.notna(row[pmi_cols[0]]) else None
                pmi_v = round(float(pmi_raw), 1) if isinstance(pmi_raw, (int, float)) else "N/D"
                macro_data_dict[p_key] = {"Voto": voto_v, "PIL": pil_v, "PMI": pmi_v}
        except Exception:
            pass

    if etf_file:
        try:
            xls = pd.ExcelFile(etf_file)
            sheet_target = "Classifica_Strutturale" if "Classifica_Strutturale" in xls.sheet_names else xls.sheet_names[0]
            df_etf = pd.read_excel(etf_file, sheet_name=sheet_target)

            if "Storico_Prezzi_EUR" in xls.sheet_names:
                df_st = pd.read_excel(etf_file, sheet_name="Storico_Prezzi_EUR", nrows=1)
                if not df_st.empty and "Mese" in df_st.columns:
                    etf_last_month = str(df_st["Mese"].iloc[0])

            for _, row in df_etf.dropna(subset=['Paese']).iterrows():
                paese = str(row['Paese']).strip()
                ticker = str(row.get('Ticker', fallback_tickers.get(paese, 'CSSPX.MI'))).strip()
                trend_ok = bool(row.get('Trend_OK', False))
                trend_label = "🟢 UP" if trend_ok else "🔴 DOWN"
                stato_azione = str(row.get('Stato_Azione', 'CONFERMATO' if trend_ok else 'FUORI / CASH'))
                score_q = float(row.get('Score_Quant', 0.0)) if pd.notna(row.get('Score_Quant')) else 0.0
                dist_sma10 = float(row.get('Dist_SMA10_pct', 0.0)) if pd.notna(row.get('Dist_SMA10_pct')) else 0.0
                mom12_val = float(row.get('Mom_12M_pct', 0.0)) if pd.notna(row.get('Mom_12M_pct')) else 0.0
                alloc_eur = int(round(float(row.get('Allocazione_EUR', 0)))) if pd.notna(row.get('Allocazione_EUR')) else 0

                p_key = clean_country_name(paese)
                macro_info = macro_data_dict.get(p_key, {"Voto": row.get('Voto_Macro', np.nan), "PIL": "N/D", "PMI": "N/D"})
                voto_macro_val = float(macro_info["Voto"]) if pd.notna(macro_info["Voto"]) else np.nan

                df_h = load_etf_history(ticker)
                rsi_val, mom1m_val, mom3m_val = 50.0, 0.0, 0.0
                if df_h is not None and len(df_h) >= 14:
                    close_s = df_h['Close']
                    delta = close_s.diff()
                    gain = delta.where(delta > 0, 0).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rsi_val = round(float((100 - (100 / (1 + gain / (loss + 1e-9)))).iloc[-1]), 1)
                    if len(df_h) >= 21:
                        mom1m_val = round(((close_s.iloc[-1] - close_s.iloc[-21]) / close_s.iloc[-21]) * 100, 2)
                    if len(df_h) >= 63:
                        mom3m_val = round(((close_s.iloc[-1] - close_s.iloc[-63]) / close_s.iloc[-63]) * 100, 2)

                records.append({
                    "Paese": paese,
                    "Ticker_YF": ticker,
                    "Trend_OK": trend_ok,
                    "Trend": trend_label,
                    "Stato_Azione": stato_azione,
                    "Allocazione": alloc_eur,
                    "Score_Quant": round(score_q, 3),
                    "Dist_SMA10": f"{dist_sma10:+.1f}%",
                    "Mom_12M": f"{mom12_val:+.1f}%",
                    "Voto_Macro": round(voto_macro_val, 2) if pd.notna(voto_macro_val) else "N/D",
                    "PIL": macro_info["PIL"],
                    "PMI": macro_info["PMI"],
                    "RSI": rsi_val,
                    "Mom_1M_num": mom1m_val,
                    "Mom_1M": f"{mom1m_val:+.2f}%",
                    "Mom_3M": f"{mom3m_val:+.2f}%"
                })
        except Exception as e:
            st.error(f"Errore lettura Archivio_ETF_Definitivo.xlsx: {e}")

    if not records:
        return pd.DataFrame(), etf_last_month

    df = pd.DataFrame(records).sort_values(by=["Trend_OK", "Score_Quant"], ascending=[False, False]).reset_index(drop=True)
    df.index = df.index + 1
    return df, etf_last_month

@st.cache_data(ttl=3600)
def get_global_fear_and_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        return int(r.json()['data'][0]['value'])
    except Exception:
        return 50

def load_crypto_archive(crypto_code):
    fname = "Archivio_BTC_Definitivo.xlsx" if crypto_code == "BTC" else "Archivio_ETH_Definitivo.xlsx"
    sheet = "BTC_Segnali_Puliti" if crypto_code == "BTC" else "ETH_Segnali_Puliti"
    fpath = find_excel_file(fname)
    if not fpath:
        return None

    try:
        df_c = pd.read_excel(fpath, sheet_name=sheet)
        if df_c.empty:
            return None
        df_c['Data'] = pd.to_datetime(df_c['Data'])
        df_c = df_c.sort_values('Data', ascending=False).reset_index(drop=True)

        curr = df_c.iloc[0]
        prev = df_c.iloc[1] if len(df_c) > 1 else curr

        w_curr = float(curr.get('W_Def', 0.0))
        w_prev = float(prev.get('W_Def', 0.0))
        delta_w = w_curr - w_prev

        if abs(delta_w) < 0.05:
            azione = "MANTIENI POSIZIONE ATTUALE"
        elif delta_w > 0:
            azione = f"AUMENTA ESPOSIZIONE (+{delta_w:.1f}%)"
        else:
            azione = f"RIDUCI ESPOSIZIONE ({delta_w:.1f}%)"

        regime = str(curr.get('Regime', 'RISK-OFF (CASH)'))
        is_up = w_curr > 0
        trend_label = "🟢 UP (BULL)" if "BULL" in regime.upper() else ("🟡 TRANSIZIONE" if is_up else "🔴 DOWN (RISK-OFF)")

        return {
            "data": curr['Data'].strftime('%Y-%m-%d'),
            "close": float(curr.get('Chiusura', 0.0)),
            "regime": regime,
            "trend_label": trend_label,
            "is_up": is_up,
            "alloc_pct": w_curr,
            "alloc_prev_pct": w_prev,
            "azione": azione,
            "sma10": float(curr.get('SMA_10', np.nan)),
            "sma20": float(curr.get('SMA_20', np.nan)),
            "sma30": float(curr.get('SMA_30', np.nan)),
            "vol_12w": float(curr.get('Ann_Vol_12W', np.nan)),
            "stress_macro": bool(curr.get('Stress_Macro', False)),
            "eth_btc": float(curr.get('ETH_BTC', np.nan)) if 'ETH_BTC' in curr else np.nan
        }
    except Exception:
        return None

@st.cache_data(ttl=3600)
def get_crypto_confluence_auto(crypto_code, fng_val):
    symbol = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
    if yf is None:
        return None
    try:
        df = yf.Ticker(symbol).history(period="1y", interval="1wk")
        if df.empty:
            return None
        close = df['Close']
        current_price = float(close.iloc[-1])
        prev_week_close = float(close.iloc[-2]) if len(close) >= 2 else current_price
        diff_vs_prev_pct = ((current_price - prev_week_close) / prev_week_close) * 100.0 if prev_week_close > 0 else 0.0

        sma_20 = float(close.rolling(window=20).mean().iloc[-1])
        sma_30 = float(close.rolling(window=30).mean().iloc[-1])

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_14 = float((100 - (100 / (1 + gain / (loss + 1e-9)))).iloc[-1])

        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_hist = float((macd - macd.ewm(span=9, adjust=False).mean()).iloc[-1])

        p1_score = int(current_price > sma_20 and current_price > sma_30) + int(macd_hist > 0) + int(50 <= rsi_14 <= 70)
        p2_score = min(3, int(30 <= fng_val <= 65) + int(fng_val < 78) + 1)
        try:
            dxy_df = yf.Ticker("DX-Y.NYB").history(period="3mo", interval="1wk")['Close']
            dxy_weak = 1 if dxy_df.iloc[-1] < dxy_df.iloc[-4] else 0
        except Exception:
            dxy_weak = 1
        p3_score = min(3, dxy_weak + 2)

        df_ind = pd.DataFrame({
            "Indicatore": ["Chiusura Sett. Prec.", "Var. vs Chiusura Prec.", "RSI (14)", "MACD Hist", "SMA 20w", "SMA 30w"],
            "Valore Ufficiale": [
                f"${prev_week_close:,.2f}", f"{diff_vs_prev_pct:+.2f}%",
                f"{rsi_14:.2f}", f"{macd_hist:+.2f}", f"${sma_20:,.2f}", f"${sma_30:,.2f}"
            ]
        })
        df_ind.index = df_ind.index + 1

        return {
            "price": current_price, "p1": p1_score, "p2": p2_score, "p3": p3_score,
            "total": p1_score + p2_score + p3_score, "df_ind": df_ind
        }
    except Exception:
        return None

# ------------------------------------------------------------------------------
# CARICAMENTO DATI GLOBALI & SIDEBAR
# ------------------------------------------------------------------------------
df_all, etf_last_month = load_all_data()
btc_arch_global = load_crypto_archive("BTC")
eth_arch_global = load_crypto_archive("ETH")

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

if st.sidebar.button("🔄 Aggiorna Dati da Excel"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("📅 **Stato Archivi Caricati**")
st.sidebar.caption(f"• ETF Paesi: **{etf_last_month}**" if not df_all.empty else "• ETF Paesi: ⚠️ Mancante")
st.sidebar.caption(f"• Bitcoin: **{btc_arch_global['data']}**" if btc_arch_global else "• Bitcoin: ⚠️ Mancante")
st.sidebar.caption(f"• Ethereum: **{eth_arch_global['data']}**" if eth_arch_global else "• Ethereum: ⚠️ Mancante")

# =============================================================================
# PAGINA 1: ROTAZIONE ETF & GRAFICI DETTAGLIATI
# =============================================================================
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati":
    st.title("🏆 Rotazione Strutturale ETF & Grafici Dettagliati")
    st.markdown("---")

    if df_all.empty:
        st.warning("⚠️ File `Archivio_ETF_Definitivo.xlsx` non trovato. Caricalo su GitHub o lancia `ETF_Predictor.R`.")
        st.stop()

    st.subheader("📊 Tabella Trend Strutturale & Allocazione Mensile")
    solo_up = st.checkbox("Mostra solo ETF in Trend UP (🟢)", value=False)
    df_tab_view = df_all[df_all["Trend_OK"] == True] if solo_up else df_all

    st.dataframe(
        df_tab_view[["Paese", "Trend", "Stato_Azione", "Allocazione", "Score_Quant", "Dist_SMA10", "Mom_12M", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M"]],
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("📌 Nuvolette di Sintesi")
    c1, c2, c3, c4 = st.columns(4)

    up_df = df_all[df_all["Trend_OK"] == True]
    best_up = up_df.iloc[0] if not up_df.empty else df_all.iloc[0]
    c1.metric("🟢 Migliore Trend UP", best_up["Paese"], f"Score: {best_up['Score_Quant']:.3f}", delta_color="off")

    down_df = df_all[df_all["Trend_OK"] == False].sort_values(by="Score_Quant", ascending=True)
    worst_down = down_df.iloc[0] if not down_df.empty else df_all.iloc[-1]
    c2.metric("🔴 Peggiore Trend DOWN", worst_down["Paese"], f"Score: {worst_down['Score_Quant']:.3f}", delta_color="off")

    best_mom = df_all.sort_values(by="Mom_1M_num", ascending=False).iloc[0]
    c3.metric("🚀 Migliore del Mese (Prezzo)", best_mom["Paese"], best_mom["Mom_1M"], delta_color="normal")

    worst_mom = df_all.sort_values(by="Mom_1M_num", ascending=True).iloc[0]
    c4.metric("📉 Peggiore del Mese (Prezzo)", worst_mom["Paese"], worst_mom["Mom_1M"], delta_color="normal")

    st.markdown("---")
    st.subheader("📈 Grafico Storico Avanzato ETF Paese")

    col_sel1, col_sel2 = st.columns([2, 1.5])
    selected_country = col_sel1.selectbox("Seleziona ETF Paese:", df_all["Paese"].tolist())
    chart_type = col_sel2.radio("Tipo Grafico:", ["Linea", "Candele (Candlestick)"], horizontal=True)

    horizon_etf = st.radio(
        "Orizzonte Temporale:",
        ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"],
        index=3, horizontal=True
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
        m_col1.metric(f"Performance ({horizon_etf})", f"{ret_pct:+.2f}%", f"Finale: {p_end:,.2f}", delta_color="off")
        m_col2.metric("Trend Strutturale", row_country["Trend"], f"Score: {row_country['Score_Quant']:.3f} | SMA10: {row_country['Dist_SMA10']}", delta_color="off")
        m_col3.metric("Stato Azione / Allocazione", f"{row_country['Allocazione']} €", row_country["Stato_Azione"], delta_color="off")

        sl_col1, sl_col2 = st.columns(2)
        sl_col1.metric("🛑 Stop Loss del Mese (Consigliato)", f"{stop_loss_price:,.2f}", f"-{sl_dist_pct:.2f}%", delta_color="normal")
        sl_col2.metric("🎯 Take Profit del Mese (Consigliato)", f"{take_profit_price:,.2f}", f"+{tp_dist_pct:.2f}%", delta_color="normal")

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

        fig.add_hline(y=stop_loss_price, line_dash="dash", line_color="#ef5350", line_width=2,
                      annotation_text=f"Stop Loss: {stop_loss_price:,.2f}", annotation_position="bottom right")
        fig.add_hline(y=take_profit_price, line_dash="dash", line_color="#26a69a", line_width=2,
                      annotation_text=f"Take Profit: {take_profit_price:,.2f}", annotation_position="top right")

        fig.update_layout(
            title=dict(text=f"<b>Grafico Prezzi {selected_country} ({row_country['Ticker_YF']}) con Livelli Operativi</b>", font=dict(size=16)),
            yaxis_title="Prezzo", xaxis_title="Data", template="plotly_white", height=520,
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

    if df_all.empty:
        st.warning("⚠️ File `Archivio_ETF_Definitivo.xlsx` non trovato.")
        st.stop()

    st.subheader("⚖️ Confronto Diretto & Finestra Mobile (Rolling Correlation)")
    col1, col2, col_win = st.columns([2, 2, 1.5])
    paesi_disponibili = df_all["Paese"].tolist()
    country1 = col1.selectbox("Seleziona Primo Paese:", paesi_disponibili, index=0)
    country2 = col2.selectbox("Seleziona Secondo Paese:", paesi_disponibili, index=1 if len(paesi_disponibili) > 1 else 0)

    finestre_giorni = {"30 Giorni": 30, "3 Mesi (63g)": 63, "6 Mesi (126g)": 126, "1 Anno (252g)": 252, "Tutto lo Storico": None}
    scelta_finestra = col_win.selectbox("Finestra Analisi / Rolling:", list(finestre_giorni.keys()), index=1)
    win_days = finestre_giorni[scelta_finestra]
    soglia_over = st.slider("Soglia Alert Over-Concentrazione:", min_value=0.60, max_value=0.95, value=0.85, step=0.05)

    row1 = df_all[df_all["Paese"] == country1].iloc[0]
    row2 = df_all[df_all["Paese"] == country2].iloc[0]
    df_h1 = load_etf_history(row1["Ticker_YF"])
    df_h2 = load_etf_history(row2["Ticker_YF"])

    corr_val, corr_3m_check, df_merged, rolling_series = 0.0, None, None, None
    if df_h1 is not None and df_h2 is not None and not df_h1.empty and not df_h2.empty:
        df_merged = pd.merge(
            df_h1[['Date', 'Close']], df_h2[['Date', 'Close']], on='Date',
            suffixes=(f'_{country1}', f'_{country2}')
        ).sort_values('Date').dropna()

        if len(df_merged) > 15:
            rets_df = pd.DataFrame({
                'Date': df_merged['Date'],
                'r1': df_merged[f'Close_{country1}'].pct_change(),
                'r2': df_merged[f'Close_{country2}'].pct_change()
            }).dropna()
            if len(rets_df) >= 63:
                corr_3m_check = float(rets_df['r1'].tail(63).corr(rets_df['r2'].tail(63)))
            sub_rets = rets_df.tail(win_days) if (win_days is not None and len(rets_df) >= win_days) else rets_df
            corr_val = float(sub_rets['r1'].corr(sub_rets['r2']))
            roll_win = win_days if win_days is not None else min(63, max(15, len(rets_df) // 4))
            if len(rets_df) > roll_win:
                rolling_series = pd.DataFrame({
                    'Date': rets_df['Date'],
                    'Rolling_Corr': rets_df['r1'].rolling(window=roll_win).corr(rets_df['r2'])
                }).dropna()

    val_check = corr_3m_check if corr_3m_check is not None else corr_val
    if country1 != country2 and val_check is not None and val_check > soglia_over:
        st.warning(f"⚠️ **Attenzione: stai duplicando il rischio.** Correlazione tra **{country1}** e **{country2}**: **{val_check:.2f}** (soglia {soglia_over:.2f}).")

    st.subheader("📊 Indice di Correlazione")
    corr_label = "Forte Correlazione Positiva 🔴" if corr_val > 0.7 else ("Moderata Correlazione Positiva 🟡" if corr_val > 0.3 else ("Decorrelati 🟢" if corr_val > -0.3 else "Correlazione Inversa 🔵"))
    st.metric(f"Correlazione ({country1} vs {country2}) — {scelta_finestra}", f"{corr_val:.2f}", corr_label, delta_color="off")

    if rolling_series is not None and not rolling_series.empty:
        fig_roll = go.Figure()
        fig_roll.add_trace(go.Scatter(x=rolling_series['Date'], y=rolling_series['Rolling_Corr'], mode='lines', line=dict(color='#7B1FA2', width=2)))
        fig_roll.add_hline(y=soglia_over, line_dash="dash", line_color="#ef5350", annotation_text=f"Soglia {soglia_over:.2f}")
        fig_roll.add_hline(y=0, line_dash="dot", line_color="#888888")
        fig_roll.update_layout(title=f"<b>Rolling Correlation nel Tempo: {country1} vs {country2}</b>", yaxis=dict(range=[-1.05, 1.05]), template="plotly_white", height=340)
        st.plotly_chart(fig_roll, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Confronto Diretto Metriche")
    df_comp = pd.DataFrame([row1, row2])[["Paese", "Trend", "Stato_Azione", "Score_Quant", "Dist_SMA10", "Voto_Macro", "PIL", "PMI", "RSI", "Mom_1M", "Mom_3M"]]
    df_comp.index = range(1, len(df_comp) + 1)
    st.dataframe(df_comp, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Grafico Comparativo dei Prezzi (Base 100)")
    if df_merged is not None and not df_merged.empty:
        df_plot_base = df_merged.tail(win_days).copy() if (win_days is not None and len(df_merged) >= win_days) else df_merged.copy()
        p1_col, p2_col = f'Close_{country1}', f'Close_{country2}'
        df_plot_base['Norm1'] = (df_plot_base[p1_col] / df_plot_base[p1_col].iloc[0]) * 100
        df_plot_base['Norm2'] = (df_plot_base[p2_col] / df_plot_base[p2_col].iloc[0]) * 100
        fig_corr = go.Figure()
        fig_corr.add_trace(go.Scatter(x=df_plot_base['Date'], y=df_plot_base['Norm1'], mode='lines', name=f"{country1} ({row1['Ticker_YF']})", line=dict(color='#2962FF', width=2)))
        fig_corr.add_trace(go.Scatter(x=df_plot_base['Date'], y=df_plot_base['Norm2'], mode='lines', name=f"{country2} ({row2['Ticker_YF']})", line=dict(color='#FF6D00', width=2)))
        fig_corr.update_layout(title=f"<b>Andamento Comparativo (Base 100): {country1} vs {country2}</b>", yaxis_title="Base 100", template="plotly_white", height=460)
        st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("---")
    st.subheader("🗺️ Matrice di Correlazione Dinamica (Heatmap Paniere)")
    default_basket = [p for p in ["America", "Canada", "Giappone", "Taiwan", "Spagna", "Italia"] if p in paesi_disponibili][:6]
    selected_basket = st.multiselect("Paniere Asset (max 10):", options=paesi_disponibili, default=default_basket, max_selections=10)
    if len(selected_basket) >= 2:
        returns_dict = {}
        for p in selected_basket:
            h_df = load_etf_history(df_all[df_all["Paese"] == p].iloc[0]["Ticker_YF"])
            if h_df is not None and not h_df.empty:
                s_c = h_df.sort_values('Date').set_index('Date')['Close'].pct_change()
                returns_dict[p] = s_c.tail(win_days) if win_days is not None else s_c
        if len(returns_dict) >= 2:
            corr_matrix = pd.DataFrame(returns_dict).dropna(how='all').corr()
            fig_heat = go.Figure(data=go.Heatmap(
                z=corr_matrix.values, x=corr_matrix.columns, y=corr_matrix.index, zmin=-1, zmax=1,
                colorscale=[[0.0, "#d32f2f"], [0.5, "#f5f5f5"], [1.0, "#2e7d32"]],
                text=np.round(corr_matrix.values, 2), texttemplate="%{text}"
            ))
            fig_heat.update_layout(title=f"<b>Heatmap Correlazioni ({scelta_finestra})</b>", template="plotly_white", height=520)
            st.plotly_chart(fig_heat, use_container_width=True)

# =============================================================================
# PAGINA 3: PORTAFOGLIO / PAPER TRADING AVANZATO
# =============================================================================
elif modulo == "💼 Portafoglio / Paper Trading":
    st.title("💼 Portafoglio Simulato & Paper Trading")
    st.markdown("---")

    if df_all.empty:
        st.warning("⚠️ File `Archivio_ETF_Definitivo.xlsx` non trovato.")
        st.stop()

    c_top1, c_top2 = st.columns([1.5, 2.5])
    capitale_totale = c_top1.number_input("Capitale Simulato (€):", min_value=100, max_value=1000000, value=1000, step=100)
    orizzonte_ptf = c_top2.radio("Finestra Storica di Calendario:", ["3 Mesi", "6 Mesi", "1 Anno", "3 Anni"], index=2, horizontal=True)
    offset_ptf_map = {
        "3 Mesi": pd.DateOffset(months=3),
        "6 Mesi": pd.DateOffset(months=6),
        "1 Anno": pd.DateOffset(years=1),
        "3 Anni": pd.DateOffset(years=3)
    }
    offset_ptf = offset_ptf_map[orizzonte_ptf]

    st.markdown("---")
    col_hdr, col_btn = st.columns([2.2, 1.3])
    col_hdr.subheader("🧩 1. Selezione Asset & Allocazione Pesi (%)")

    paesi_list = df_all["Paese"].tolist()
    opzioni_asset = [f"ETF: {p}" for p in paesi_list] + ["Crypto: BTC", "Crypto: ETH"]

    if "ptf_asset_scelti" not in st.session_state:
        st.session_state["ptf_asset_scelti"] = [f"ETF: {p}" for p in ["America", "Canada", "Giappone"] if p in paesi_list] + ["Crypto: BTC"]

    # Pulsante rapido: carica gli ETF attivi del modello mensile (Allocazione > 0) a pesi uguali
    if col_btn.button("⚡ Carica Portafoglio Modello (ETF Attivi)", use_container_width=True):
        attivi = df_all[df_all["Allocazione"] > 0]["Paese"].tolist()
        if len(attivi) >= 2:
            scelti_mod = [f"ETF: {p}" for p in attivi]
            st.session_state["ptf_asset_scelti"] = scelti_mod
            p_base = 100 // len(scelti_mod)
            p_rem = 100 - p_base * len(scelti_mod)
            for idx_m, lbl_m in enumerate(scelti_mod):
                st.session_state[f"peso_{lbl_m}"] = p_base + (p_rem if idx_m == 0 else 0)
            st.rerun()
        else:
            st.info("Meno di 2 ETF attivi nel modello questo mese.")

    asset_scelti = st.multiselect("Scegli gli asset da inserire in portafoglio:", options=opzioni_asset, key="ptf_asset_scelti")

    if len(asset_scelti) < 2:
        st.info("Seleziona almeno 2 asset per calcolare correlazione e metriche di portafoglio.")
    else:
        peso_iniziale = int(100 // len(asset_scelti))
        resto = 100 - (peso_iniziale * len(asset_scelti))
        for idx, asset_label in enumerate(asset_scelti):
            k_state = f"peso_{asset_label}"
            if k_state not in st.session_state:
                st.session_state[k_state] = peso_iniziale + (resto if idx == 0 else 0)

        pesi_dict = {}
        cols_w = st.columns(min(5, len(asset_scelti)))
        for idx, asset_label in enumerate(asset_scelti):
            pesi_dict[asset_label] = cols_w[idx % len(cols_w)].number_input(f"{asset_label} (%)", min_value=0, max_value=100, step=5, key=f"peso_{asset_label}")

        somma_pesi = sum(pesi_dict.values())
        if somma_pesi != 100:
            st.error(f"⚠️ La somma attuale dei pesi è **{somma_pesi}%** (deve essere **100%**).")
            if st.button("⚖️ Normalizza al 100%"):
                if somma_pesi > 0:
                    arr = {k: int(round((v / somma_pesi) * 100.0)) for k, v in pesi_dict.items()}
                    diff_100 = 100 - sum(arr.values())
                    if diff_100 != 0:
                        k_max = max(arr.keys(), key=lambda k: arr[k])
                        arr[k_max] = max(0, arr[k_max] + diff_100)
                    for k, val_n in arr.items():
                        st.session_state[f"peso_{k}"] = val_n
                st.rerun()
        else:
            returns_map, dettagli_righe = {}, []
            quota_crypto, quota_trend_up = 0.0, 0.0
            asset_contro_trend = []

            for asset_label, w_pct in pesi_dict.items():
                w = w_pct / 100.0
                if w == 0:
                    continue

                if asset_label.startswith("ETF: "):
                    paese_nome = asset_label.replace("ETF: ", "")
                    r_row = df_all[df_all["Paese"] == paese_nome].iloc[0]
                    ticker_curr = r_row["Ticker_YF"]
                    trend_curr = r_row["Trend"]
                    is_up_curr = bool(r_row["Trend_OK"])
                    alloc_mod = f"{r_row['Allocazione']} € ({r_row['Stato_Azione']})"

                    hist_df = load_etf_history(ticker_curr)
                    if hist_df is not None and not hist_df.empty:
                        returns_map[asset_label] = hist_df.sort_values("Date").set_index("Date")["Close"].pct_change().dropna()
                else:
                    crypto_code = asset_label.replace("Crypto: ", "")
                    quota_crypto += w_pct
                    ticker_curr = "BTC-USD" if crypto_code == "BTC" else "ETH-USD"
                    c_arch = btc_arch_global if crypto_code == "BTC" else eth_arch_global
                    if c_arch:
                        trend_curr = c_arch["trend_label"]
                        is_up_curr = c_arch["is_up"]
                        alloc_mod = f"{c_arch['alloc_pct']:.0f}% ({c_arch['regime']})"
                    else:
                        trend_curr, is_up_curr, alloc_mod = "⚠️ N/D", False, "Archivio mancante"

                    df_c_d = load_crypto_history(crypto_code, interval="1d")
                    if df_c_d is not None and not df_c_d.empty:
                        returns_map[asset_label] = df_c_d.sort_values("Date").set_index("Date")["Close"].pct_change().dropna()

                if is_up_curr:
                    quota_trend_up += w_pct
                else:
                    asset_contro_trend.append(f"{asset_label} ({trend_curr})")

                dettagli_righe.append({
                    "Asset": asset_label, "Ticker": ticker_curr, "Peso": f"{w_pct}%",
                    "Importo (€)": round(capitale_totale * w, 2),
                    "Trend Modello": trend_curr, "Indicazione Modello": alloc_mod
                })

            corr_media_ptf, vol_annua_ptf = 0.0, 0.0
            df_rets_ptf = pd.DataFrame()
            valid_assets = [k for k in returns_map.keys() if pesi_dict[k] > 0]

            if len(valid_assets) >= 2:
                df_rets_full = pd.DataFrame({k: returns_map[k] for k in valid_assets}).dropna()
                if not df_rets_full.empty:
                    end_dt = df_rets_full.index.max()
                    start_dt = end_dt - offset_ptf
                    df_rets_ptf = df_rets_full[df_rets_full.index >= start_dt]

                if len(df_rets_ptf) > 15:
                    w_vec = np.array([pesi_dict[k] / 100.0 for k in valid_assets])
                    w_vec = w_vec / w_vec.sum()
                    corr_mat_ptf = df_rets_ptf.corr()
                    vol_annua_ptf = float(np.sqrt(np.dot(w_vec.T, np.dot((df_rets_ptf.cov() * 252.0).values, w_vec)))) * 100.0
                    num_c = sum(w_vec[i] * w_vec[j] * corr_mat_ptf.iloc[i, j] for i in range(len(valid_assets)) for j in range(i + 1, len(valid_assets)))
                    den_c = sum(w_vec[i] * w_vec[j] for i in range(len(valid_assets)) for j in range(i + 1, len(valid_assets)))
                    corr_media_ptf = float(num_c / den_c) if den_c > 0 else 0.0

            profilo_rischio = "🔴 Aggressivo" if (vol_annua_ptf >= 28 or quota_crypto >= 35) else ("🟠 Dinamico" if (vol_annua_ptf >= 18 or quota_crypto >= 15) else ("🟡 Bilanciato" if vol_annua_ptf >= 11 else "🟢 Conservativo"))

            st.markdown("---")
            st.subheader("📊 2. Metriche Sintetiche di Portafoglio")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Correlazione Complessiva", f"{corr_media_ptf:.2f}", "Ben diversificato" if corr_media_ptf < 0.45 else "Moderata/Alta", delta_color="off")
            m2.metric("Quota in Trend UP", f"{quota_trend_up:.0f}%", "Allineato al trend" if quota_trend_up >= 70 else "Quota in DOWN presente", delta_color="off")
            m3.metric("Profilo di Rischio", profilo_rischio, f"Volatilità annua: {vol_annua_ptf:.1f}%", delta_color="off")
            m4.metric("Esposizione Crypto", f"{quota_crypto:.0f}%", f"ETF: {100 - quota_crypto:.0f}%", delta_color="off")

            if asset_contro_trend:
                st.warning(f"⚠️ **Asset contro-trend nel portafoglio:** {', '.join(asset_contro_trend)}. I modelli strutturali indicano cautela / Cash su questi strumenti.")

            st.markdown("---")
            st.subheader("📋 3. Riepilogo Allocazione & Grafici")
            col_tab, col_pie = st.columns([1.6, 1])
            df_dettagli = pd.DataFrame(dettagli_righe)
            df_dettagli.index = range(1, len(df_dettagli) + 1)
            col_tab.dataframe(df_dettagli, use_container_width=True)

            fig_pie = go.Figure(data=[go.Pie(labels=df_dettagli["Asset"], values=[pesi_dict[a] for a in df_dettagli["Asset"]], hole=0.45, textinfo="label+percent")])
            fig_pie.update_layout(title="<b>Ripartizione Portafoglio</b>", template="plotly_white", height=340, showlegend=False)
            col_pie.plotly_chart(fig_pie, use_container_width=True)

            if len(valid_assets) >= 2 and not df_rets_ptf.empty:
                ptf_daily_ret = df_rets_ptf.dot(w_vec)
                ptf_equity = ((1.0 + ptf_daily_ret).cumprod() / float((1.0 + ptf_daily_ret).cumprod().iloc[0])) * 100.0
                val_finale = float(ptf_equity.iloc[-1])
                perf_pct = val_finale - 100.0
                capitale_finale = capitale_totale * (val_finale / 100.0)
                max_dd_pct = float(((ptf_equity / ptf_equity.cummax()) - 1.0).min()) * 100.0
                sharpe_ratio = ((float(ptf_daily_ret.mean()) * 252.0) / (float(ptf_daily_ret.std()) * np.sqrt(252.0))) if float(ptf_daily_ret.std()) > 0 else 0.0

                st.markdown("---")
                st.subheader(f"📈 4. Performance Storica Simulata ({orizzonte_ptf}: {ptf_equity.index[0].strftime('%Y-%m-%d')} → {ptf_equity.index[-1].strftime('%Y-%m-%d')})")
                p1, p2, p3, p4 = st.columns(4)
                p1.metric(f"Profitto / Perdita ({orizzonte_ptf})", f"{perf_pct:+.2f}%", f"{capitale_finale - capitale_totale:+,.2f} €", delta_color="normal")
                p2.metric("Controvalore Finale", f"{capitale_finale:,.2f} €", f"Iniziale: {capitale_totale:,.0f} €", delta_color="off")
                p3.metric("Max Drawdown", f"{max_dd_pct:.2f}%", "Picco-Fondo nel periodo", delta_color="off")
                p4.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}", "Rendimento / Rischio", delta_color="off")

                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(x=ptf_equity.index, y=ptf_equity.values, mode="lines", name="Portafoglio Simulato", line=dict(color="#2e7d32" if perf_pct >= 0 else "#d32f2f", width=2.5)))
                spy_hist = load_etf_history("CSSPX.MI")
                if spy_hist is not None and not spy_hist.empty:
                    spy_al = spy_hist.sort_values("Date").set_index("Date")["Close"].reindex(ptf_equity.index).ffill().bfill()
                    if len(spy_al) > 1 and float(spy_al.iloc[0]) > 0:
                        fig_eq.add_trace(go.Scatter(x=spy_al.index, y=(spy_al / float(spy_al.iloc[0])) * 100.0, mode="lines", name="Benchmark S&P 500 EUR", line=dict(color="#757575", width=2, dash="dash")))
                fig_eq.add_hline(y=100.0, line_dash="dot", line_color="#888888")
                fig_eq.update_layout(title=f"<b>Andamento Storico Simulato (Base 100 — {orizzonte_ptf})</b>", template="plotly_white", height=400)
                st.plotly_chart(fig_eq, use_container_width=True)

# =============================================================================
# PAGINA 4: CRYPTO (BTC & ETH — REGIME v4 + TRIPLA CONFLUENZA)
# =============================================================================
elif modulo == "₿ Crypto (BTC & ETH)":
    st.title("₿ Quantamentale Crypto — Regime Strutturale v4 & Confluenza")
    st.markdown("---")

    global_fng = get_global_fear_and_greed()
    col_btc, col_eth = st.columns(2)

    for col_box, code, title, arch in [
        (col_btc, "BTC", "### 🟡 Bitcoin (BTC)", btc_arch_global),
        (col_eth, "ETH", "### 🔷 Ethereum (ETH)", eth_arch_global)
    ]:
        with col_box:
            st.markdown(title)
            conf = get_crypto_confluence_auto(code, global_fng)
            price_live = conf["price"] if conf else (arch["close"] if arch else 0.0)

            if arch:
                st.metric(
                    f"Prezzo Attuale {code}",
                    f"${price_live:,.2f}",
                    f"Trend v4: {arch['trend_label']} | Target: {arch['alloc_pct']:.0f}%",
                    delta_color="off"
                )
                if arch["is_up"]:
                    st.success(f"🟢 **REGIME: {arch['regime']} — ALLOCAZIONE TARGET: {arch['alloc_pct']:.0f}%**\n\nAzione settimanale: **{arch['azione']}** *(agg. {arch['data']})*")
                else:
                    st.warning(f"🔴 **REGIME: {arch['regime']} — ALLOCAZIONE TARGET: 0% (100% CASH)**\n\nAzione settimanale: **{arch['azione']}** *(agg. {arch['data']})*")
                st.caption(f"Livelli chiave modello: SMA 20w = **${arch['sma20']:,.2f}** | SMA 30w = **${arch['sma30']:,.2f}** | Vol 12w = **{arch['vol_12w']:.1f}%**")
            else:
                st.warning(f"⚠️ File `Archivio_{code}_Definitivo.xlsx` non trovato. Caricalo su GitHub.")

            if conf:
                st.write("---")
                st.subheader(f"📊 Tripla Confluenza {code}: **{conf['total']} / 9 Punti**")
                st.progress(conf['total'] / 9)
                st.write(f"• Pilastro 1 (Tecnico & Momentum): **{conf['p1']}/3** | • Pilastro 2 (Sentiment): **{conf['p2']}/3** | • Pilastro 3 (Macro DXY): **{conf['p3']}/3**")
                st.dataframe(conf['df_ind'], use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Grafico Settimanale Avanzato Crypto")
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    selected_crypto = col_c1.selectbox("Seleziona Crypto:", ["Bitcoin (BTC)", "Ethereum (ETH)"])
    chart_type_crypto = col_c2.radio("Tipo Grafico Crypto:", ["Linea", "Candele (Candlestick)"], horizontal=True)
    is_log_crypto = col_c3.checkbox("Scala Logaritmica Crypto", value=True)
    horizon_crypto = st.radio("Orizzonte Temporale Crypto:", ["1 Mese", "3 Mesi", "6 Mesi", "1 Anno", "3 Anni", "5 Anni", "Tutto (Max)"], index=6, horizontal=True)

    code_crypto = "BTC" if "BTC" in selected_crypto else "ETH"
    df_crypto_chart = load_crypto_history(code_crypto, interval="1wk")
    curr_arch = btc_arch_global if code_crypto == "BTC" else eth_arch_global

    if df_crypto_chart is not None and not df_crypto_chart.empty:
        df_c_filt, p_c_start, p_c_end, ret_c_pct = filter_by_horizon(df_crypto_chart, horizon_crypto)
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric(f"Performance ({horizon_crypto})", f"{ret_c_pct:+.2f}%", f"Chiusura: ${p_c_end:,.2f}", delta_color="off")
        c_m2.metric("Regime & Allocazione v4", curr_arch["trend_label"] if curr_arch else "N/D", f"Target: {curr_arch['alloc_pct']:.0f}%" if curr_arch else "", delta_color="off")
        c_m3.metric("Crypto Fear & Greed Index", f"{global_fng} / 100")

        fig_c = go.Figure()
        if chart_type_crypto == "Candele (Candlestick)" and 'Open' in df_c_filt.columns:
            fig_c.add_trace(go.Candlestick(x=df_c_filt['Date'], open=df_c_filt['Open'], high=df_c_filt['High'], low=df_c_filt['Low'], close=df_c_filt['Close'],
                                           name=selected_crypto, increasing_line_color='#26a69a', decreasing_line_color='#ef5350'))
        else:
            fig_c.add_trace(go.Scatter(x=df_c_filt['Date'], y=df_c_filt['Close'], mode='lines', name=selected_crypto,
                                       line=dict(color='#F7931A' if code_crypto == "BTC" else '#627EEA', width=2.5)))

        if curr_arch and pd.notna(curr_arch["sma20"]):
            fig_c.add_hline(y=curr_arch["sma20"], line_dash="dash", line_color="#2962FF", annotation_text=f"SMA 20w: ${curr_arch['sma20']:,.0f}")
        if curr_arch and pd.notna(curr_arch["sma30"]):
            fig_c.add_hline(y=curr_arch["sma30"], line_dash="dot", line_color="#7B1FA2", annotation_text=f"SMA 30w: ${curr_arch['sma30']:,.0f}")

        fig_c.update_layout(
            title=f"<b>Grafico Settimanale {selected_crypto} con Livelli SMA 20w / 30w</b>",
            yaxis_title="Prezzo ($)", template="plotly_white", height=500,
            yaxis=dict(type="log" if is_log_crypto else "linear", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
        )
        st.plotly_chart(fig_c, use_container_width=True)
