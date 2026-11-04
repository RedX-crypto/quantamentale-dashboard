import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re

try:
    import yfinance as yf
except ImportError:
    yf = None

st.set_page_config(page_title="Quantamentale System", page_icon="📈", layout="wide")
st.title("📈 Quantamentale Trading System — Dashboard Personale")
st.markdown("---")

modulo = st.sidebar.selectbox(
    "Seleziona Modulo", 
    [
        "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)", 
        "🔄 Correlazione ETF", 
        "⏳ Simulatore di Backtest & Registro Transazioni", 
        "₿ Crypto (BTC & ETH)"
    ]
)

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

# Blacklist globale basata sull'analisi OOS di RStudio
BLACKLIST_OOS = ["Argentina", "Cina", "Corea del Sud", "Corea", "Brasile", "Indonesia"]

# Mappatura statica dei soli Ticker e Fogli Excel (I VOTI MACRO VENGONO LETTI DA EXCEL)
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
    "Giappone": {"Ticker_YF": "EWJ", "Sheet_ETF": "Giappone"}
}

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
def load_forecast_from_excel():
    db_file = find_excel_file("DataBase.xlsx")
    records = []
    
    # 1. Caricamento dinamico Voti Macro dal foglio 'Macro Paesi 3M'
    voti_macro_dict = {}
    if db_file:
        try:
            df_macro = pd.read_excel(db_file, sheet_name="Macro Paesi 3M")
            colnames = [str(c).lower() for c in df_macro.columns]
            col_paese = [df_macro.columns[i] for i, c in enumerate(colnames) if 'paese' in c or 'country' in c][0]
            col_voto = [df_macro.columns[i] for i, c in enumerate(colnames) if 'voto' in c or 'score' in c or 'macro' in c][0]
            
            for _, row in df_macro.dropna(subset=[col_paese, col_voto]).iterrows():
                p_name = str(row[col_paese]).strip()
                try:
                    val_voto = float(row[col_voto])
                except ValueError:
                    val_voto = 2.5
                voti_macro_dict[p_name] = val_voto
        except Exception:
            pass
            
    # 2. Caricamento dinamico Previsioni dal foglio 'Forecast'
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
                
                # Prende il voto macro letto dinamicamente da Excel (o 2.50 come fallback)
                voto_macro_dinamico = voti_macro_dict.get(paese, 2.50)
                is_bl = paese in BLACKLIST_OOS
                
                records.append({
                    "Paese": paese, 
                    "Prob_UP": prob, 
                    "Segnale": segnal, 
                    "Esito AI": f"{prob}% ({segnal})",
                    "Stato OOS": "⛔ Escluso (Acc. < 50%)" if is_bl else "✅ Valido",
                    "Ticker_YF": meta["Ticker_YF"], 
                    "Sheet_ETF": meta["Sheet_ETF"], 
                    "Voto_Macro": round(voto_macro_dinamico, 2)
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
def build_pro_chart(df, title_name):
    df_c = df.copy().dropna(subset=['Close'])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_c['Date'], y=df_c['Close'], mode='lines', name="Valore Portafoglio",
        line=dict(color='#2962FF', width=2.5)
    ))
    fig.update_layout(
        title=dict(text=f"<b>{title_name}</b>", font=dict(size=16)),
        yaxis_title="Valore (€)", xaxis_title="Data", template="plotly_white", height=500,
        margin=dict(l=30, r=30, t=50, b=30), xaxis=dict(showgrid=True, gridcolor='#F0F2F5', type='date'),
        yaxis=dict(type="linear", showgrid=True, gridcolor='#F0F2F5'), showlegend=False
    )
    return fig

# --- MODULO 1: ROTAZIONE ETF ---
if modulo == "🏆 Rotazione ETF & Grafici Dettagliati (Unificato)":
    st.subheader("🏆 Rotazione ETF & Previsioni (Voti Macro e Forecast 100% Dinamici)")
    st.info("I voti macro e le previsioni AI vengono letti direttamente in tempo reale dal foglio Excel 'DataBase.xlsx'.")
    st.dataframe(df_all[["Paese", "Esito AI", "Allocazione", "Stato OOS", "Voto_Macro"]], use_container_width=True)

# --- MODULO 3: BACKTEST ---
elif modulo == "⏳ Simulatore di Backtest & Registro Transazioni":
    st.subheader("⏳ Backtest Finanziario AI Top 5 (Reinvestimento + Tassazione 26%)")
    col1, col2 = st.columns(2)
    init_cap = col1.number_input("Capitale Iniziale (€)", min_value=100.0, value=1000.0, step=100.0)
    cutoff = col2.slider("Soglia Minima Probabilità UP (%)", min_value=50.0, max_value=75.0, value=60.0, step=1.0)
    
    col_d1, col_d2 = st.columns(2)
    d_start = col_d1.date_input("Data Inizio", pd.to_datetime("2025-01-01"))
    d_end = col_d2.date_input("Data Fine", pd.to_datetime("2026-11-01"))
    
    if st.button("🚀 Esegui Backtest e Genera Registro"):
        with st.spinner("Elaborazione transazioni in corso..."):
            df_valid = df_all[df_all["Stato OOS"] == "✅ Valido"].copy()
            etf_dfs = {}
            for _, row in df_valid.iterrows():
                df_h = load_etf_history_from_file(row["Sheet_ETF"], ticker=row["Ticker_YF"])
                if df_h is not None and not df_h.empty:
                    df_h['Date'] = strip_timezone(df_h['Date'])
                    etf_dfs[row["Paese"]] = df_h.sort_values('Date').set_index('Date')['Close']
                    
            df_prices = pd.DataFrame(etf_dfs).dropna(how='all').sort_index()
            mask = (df_prices.index >= pd.to_datetime(d_start)) & (df_prices.index <= pd.to_datetime(d_end))
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
                fig_t = build_pro_chart(df_plot, "Evoluzione Portafoglio Rotazione Top 5 (Esclusi Paesi < 50% OOS)")
                st.plotly_chart(fig_t, use_container_width=True)
                st.dataframe(pd.DataFrame(tx_log), use_container_width=True)
