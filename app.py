import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# Import yfinance come fallback
try:
    import yfinance as yf
except ImportError:
    yf = None

st.set_page_config(page_title="Test Caricamento Dati", page_icon="📈", layout="wide")
st.title("🧪 Test 1: Caricamento Dati Macro & Forecast")

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

# 1. Verifichiamo se trova il file DataBase.xlsx su GitHub
db_file = find_excel_file("DataBase.xlsx")

if not db_file:
    st.error("❌ File 'DataBase.xlsx' non trovato nella cartella principale di GitHub!")
else:
    st.success(f"✅ File trovato: {db_file}")
    
    try:
        # Carichiamo ed elaboriamo il foglio Macro Paesi 3M
        df_macro = pd.read_excel(db_file, sheet_name="Macro Paesi 3M")
        df_macro_valid = df_macro.dropna(subset=['Voto', 'Country']).copy()
        
        if 'Data' in df_macro_valid.columns:
            df_macro_valid['Data'] = pd.to_datetime(df_macro_valid['Data'])
            df_macro_valid = df_macro_valid.sort_values('Data')
            
        df_latest = df_macro_valid.groupby('Country').last().reset_index()
        
        st.subheader("📊 Dati Macro Estratti dal tuo Excel:")
        pmi_col = [c for c in df_latest.columns if 'pmi' in str(c).lower()][0]
        st.dataframe(df_latest[['Country', 'Data', 'PIL', pmi_col, 'Voto']], use_container_width=True)
        
    except Exception as e:
        st.error(f"Errore durante la lettura dell'Excel: {e}")
