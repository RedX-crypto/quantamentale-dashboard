import streamlit as st
import pandas as pd
import numpy as np
import os
import re

try:
    import yfinance as yf
except ImportError:
    yf = None

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
