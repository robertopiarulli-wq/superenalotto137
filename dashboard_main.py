import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import random
import json
import os

# --- CONNESSIONE ---
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def calcola_rugosita(sestina):
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

def carica_dati_motore():
    cardini = []
    valli = []
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            cardini = json.load(f)
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        valli_df = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)'] # Cerca i vuoti
        for f in valli_df['fascia']:
            nums = f.replace('(', '').replace(']', '').split(',')
            valli.append((float(nums[0]), float(nums[1])))
    return cardini, valli

st.set_page_config(page_title="Parisi-137 Morsa", layout="wide")
st.title("🔬 Morsa di Pressione Scientifica")

cardini_auto, valli_target = carica_dati_motore()
st.sidebar.header("Parametri Motore")
cardini_finali = st.sidebar.multiselect("Cardini (Fisse)", range(1, 91), default=cardini_auto)

try:
    # Calcolo target Parisi
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    df_full = pd.DataFrame(res.data)
    # Logica di calcolo Q_medio e Delta_medio come da precedenti versioni
    # ... (inserire qui la funzione analizza_legge_universale_doppia)
    
    st.info(f"Cardini scientifici rilevati: {cardini_finali}")
    
    if st.button("🔥 GENERA ARROSTO (Morsa Integrata)"):
        # Logica di generazione sestine includendo cardini_finali e filtrando per valli_target
        st.write("Generazione in corso sulle valli rilevate...")
        # ... (Logica morsa filtrata)
except Exception as e:
    st.error(f"Errore: {e}")
