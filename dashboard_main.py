import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import random
import json
import os

# --- CONNESSIONE DATABASE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Errore connessione: controlla i secrets.")
    st.stop()

def calcola_rugosita(sestina):
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale_doppia():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    full_df = pd.DataFrame(res.data)
    full_df['H'] = full_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    q_prop, q_delta = [], []
    for i in range(len(full_df) - 137):
        h_137 = full_df['H'].iloc[i]
        h_136_prec = full_df['H'].iloc[i+1]
        media_corpo = full_df['H'].iloc[i+1 : i+137].mean()
        if media_corpo != 0:
            q_prop.append(h_137 / media_corpo)
            q_delta.append(h_137 - h_136_prec)
    return full_df, np.mean(q_prop), np.mean(q_delta)

def carica_dati_scientifici():
    cardini = []
    valli = []
    # Caricamento Cardini Scientifici
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            cardini = json.load(f)
    # Caricamento Valli di Pressione
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        v_df = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)']
        for f in v_df['fascia']:
            nums = f.replace('(', '').replace(']', '').split(',')
            valli.append((float(nums[0]), float(nums[1])))
    return cardini, valli

# --- INTERFACCIA ---
st.set_page_config(page_title="Sistema Parisi-137", layout="wide")
st.title("🔬 Morsa di Pressione Scientifica")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    cardini_auto, valli_target = carica_dati_scientifici()
    
    st.sidebar.header("Parametri Dinamici")
    cardini_finali = st.sidebar.multiselect("Cardini Rilevati (Fisse)", range(1, 91), default=cardini_auto)

    h_136_attuale = df_full['H'].iloc[0]
    target_h = df_full['H'].iloc[0:136].mean() * Q_medio
    morsa_millimetrica = target_h * 0.1

    col1, col2, col3 = st.columns(3)
    col1.metric("Bersaglio H", f"{target_h:.5f}")
    col2.metric("Delta Atteso", f"{Delta_medio:.5f}")
    col3.success(f"Cardini in uso: {cardini_finali}")

    if st.button("🔥 LANCIA MORSA INTEGRATA (4M Cicli)"):
        sestine_risultanti = []
        n_tentativi = 4000000
        prog_bar = st.progress(0)
        
        for batch in range(0, n_tentativi, 100000):
            for _ in range(100000):
                # Include i cardini scientifici
                s_base = random.sample([n for n in range(1, 91) if n not in cardini_finali], 6 - len(cardini_finali))
                s = sorted(s_base + cardini_finali)
                somma_s = sum(s)
                
                # Filtro Valli
                in_valle = any(v[0] < somma_s <= v[1] for v in valli_target) if valli_target else (180 <= somma_s <= 230)
                
                if in_valle:
                    h_s = calcola_rugosita(s)
                    if abs(h_s - target_h) < morsa_millimetrica:
                        err_tot = abs(h_s - target_h) + (abs((h_s - h_136_attuale) - Delta_medio) * 10)
                        sestine_risultanti.append((s, err_tot, h_s, somma_s))
            prog_bar.progress((batch + 100000) / n_tentativi)
        
        prog_bar.empty()
        if sestine_risultanti:
            sestine_risultanti.sort(key=lambda x: x[1])
            st.table(pd.DataFrame(sestine_risultanti[:20], columns=['Sestina', 'Errore', 'Rugosità H', 'Somma']))
        else:
            st.warning("Morsa troppo stretta per i cardini attuali.")

except Exception as e:
    st.error(f"Errore: {e}")
