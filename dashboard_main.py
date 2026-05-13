import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import random
import json
import os

# --- CONNESSIONE E LOGICA ---
try:
    supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])
except:
    st.error("Errore Secrets Supabase")

def calcola_rugosita(sestina):
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

def carica_dati_scientifici():
    cardini = [22, 66] # Fallback
    valli = []
    
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            cardini = json.load(f)
            
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        valli_df = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)']
        for f in valli_df['fascia']:
            nums = f.replace('(', '').replace(']', '').split(',')
            valli.append((float(nums[0]), float(nums[1])))
            
    return cardini, valli

# --- INTERFACCIA ---
st.set_page_config(page_title="Sistema Parisi-137", layout="wide")
st.title("🔬 Morsa di Pressione Scientifica")

cardini_auto, valli_target = carica_dati_scientifici()

st.sidebar.header("Parametri Dinamici")
cardini_scelti = st.sidebar.multiselect("Cardini Rilevati", range(1, 91), default=cardini_auto)

# ... (Qui inserisci la logica della morsa che usa cardini_scelti e valli_target)
st.success(f"Sistema pronto. Cardini attuali: {cardini_scelti}")
if valli_target:
    st.info(f"Valli di pressione caricate: {len(valli_target)} zone individuate.")
