import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import random
import time
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

# --- NUOVA FUNZIONE: CARICAMENTO PRESSIONE ---
def carica_mappa_pressione():
    try:
        # Carica il file generato dal Motore 1 via GitHub Artifacts o locale
        if os.path.exists("mappa_valli_pressione.csv"):
            mappa = pd.read_csv("mappa_valli_pressione.csv")
            # Estraiamo i range delle valli (stato_zona == 'VALLE (TRANSIZIONE)')
            valli = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)']
            # Convertiamo le stringhe fascia (es. "(190, 200]") in tuple numeriche
            intervalli = []
            for f in valli['fascia']:
                nums = f.replace('(', '').replace(']', '').split(',')
                intervalli.append((float(nums[0]), float(nums[1])))
            return intervalli
        else:
            return None
    except:
        return None

# --- INTERFACCIA ---
st.set_page_config(page_title="Parisi-137 Pressione", layout="wide")
st.title("🔬 Sistema Parisi-137: Morsa di Pressione")

# Sidebar per i Cardini
st.sidebar.header("Parametri Cardine")
cardini = st.sidebar.multiselect("Numeri Cardine (Obbligatori)", range(1, 91), default=[22, 66])

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    valli_target = carica_mappa_pressione()
    
    h_136_attuale = df_full['H'].iloc[0]
    target_h = df_full['H'].iloc[0:136].mean() * Q_medio
    morsa_millimetrica = target_h * 0.1 # Stringiamo la morsa al 10% per qualità

    # Layout Dashboard
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.metric("Bersaglio Rugosità H", f"{target_h:.5f}")
    col_info2.metric("Delta Atteso", f"{Delta_medio:.5f}")
    
    if valli_target:
        valli_str = " | ".join([f"{v[0]}-{v[1]}" for v in valli_target])
        col_info3.success(f"Valli di Pressione: {valli_str}")
    else:
        col_info3.warning("Mappa Pressione non trovata. Caricamento Wyckoff standard.")

    if st.button("🔥 LANCIA MORSA INTEGRATA (4M Cicli)"):
        sestine_risultanti = []
        n_tentativi = 4000000
        prog_bar = st.progress(0)
        
        batch_size = 100000
        for batch in range(0, n_tentativi, batch_size):
            for _ in range(batch_size):
                # Generazione con inclusione cardini
                s_base = random.sample([n for n in range(1, 91) if n not in cardini], 6 - len(cardini))
                s = sorted(s_base + cardini)
                
                somma_s = sum(s)
                
                # FILTRO 1: Pressione (Deve cadere in una Valle)
                in_valle = False
                if valli_target:
                    for v in valli_target:
                        if v[0] < somma_s <= v[1]:
                            in_valle = True
                            break
                else:
                    # Fallback se manca il file: range statistico ampio
                    if 180 <= somma_s <= 230: in_valle = True
                
                if in_valle:
                    # FILTRO 2: Rugosità Parisi
                    h_s = calcola_rugosita(s)
                    if abs(h_s - target_h) < morsa_millimetrica:
                        salto_s = h_s - h_136_attuale
                        err_tot = abs(h_s - target_h) + (abs(salto_s - Delta_medio) * 10)
                        sestine_risultanti.append((s, err_tot, h_s, salto_s, somma_s))
            
            prog_bar.progress((batch + batch_size) / n_tentativi)

        prog_bar.empty()

        if sestine_risultanti:
            st.subheader(f"✨ L'Arrosto: {len(sestine_risultanti)} Sestine in Compressione")
            # Ordiniamo per errore minimo
            sestine_risultanti.sort(key=lambda x: x[1])
            
            df_ris = pd.DataFrame([
                {'Sestina': s, 'Errore': e, 'Rugosità H': h, 'Somma': sm} 
                for s, e, h, sa, sm in sestine_risultanti[:20]
            ])
            st.table(df_ris)
        else:
            st.warning("La morsa è troppo stretta. Nessuna risonanza rilevata nelle valli di pressione.")

except Exception as e:
    st.error(f"Errore: {e}")
