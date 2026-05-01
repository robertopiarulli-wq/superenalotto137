import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import random
import time

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

# --- INTERFACCIA ---
st.set_page_config(page_title="Parisi-137 Cardini", layout="wide")
st.title("🔬 Sistema Parisi-137: Analisi dei Cardini")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    h_136_attuale = df_full['H'].iloc[0]
    target_h = df_full['H'].iloc[0:136].mean() * Q_medio
    # Manteniamo la morsa allo 0.01% per avere un campione statistico valido
    morsa_millimetrica = target_h * 0.9 

    st.success(f"Bersaglio H: {target_h:.6f} | Delta Atteso: {Delta_medio:.6f}")

    if st.button("Esegui Sintesi e Analizza Cardini (1M Cicli)"):
        sestine_risultanti = []
        n_tentativi = 4000000
        prog_bar = st.progress(0)
        
        batch_size = 50000
        for batch in range(0, n_tentativi, batch_size):
            for _ in range(batch_size):
                s = sorted(random.sample(range(1, 91), 6))
                h_s = calcola_rugosita(s)
                if abs(h_s - target_h) < morsa_millimetrica:
                    salto_s = h_s - h_136_attuale
                    err_tot = abs(h_s - target_h) + (abs(salto_s - Delta_medio) * 10)
                    sestine_risultanti.append((s, err_tot, h_s, salto_s))
            prog_bar.progress((batch + batch_size) / n_tentativi)

        prog_bar.empty()

        if sestine_risultanti:
            # --- 1. ANALISI DEI CARDINI (NOVITÀ) ---
            st.subheader("🎯 I Numeri Cardine della Risonanza")
            st.write("Questi numeri compaiono con frequenza anomala nelle combinazioni che rispettano il Quid.")
            
            tutti_i_numeri = [n for s, _, _, _ in sestine_risultanti for n in s]
            frequenze = pd.Series(tutti_i_numeri).value_counts().head(20)
            
            cols = st.columns(6)
            for i, (num, freq) in enumerate(frequenze.items()):
                cols[i % 6].metric(f"Top {i+1}", f"N. {num}", f"{freq} volte")
            
            st.divider()

            # --- 2. LISTA DELLE ELETTE ---
            st.subheader(f"✨ Le {len(sestine_risultanti)} Sestine Specchio")
            sestine_risultanti.sort(key=lambda x: x[1])
            
            c1, c2 = st.columns(2)
            for idx, (s, err, h_v, d_v) in enumerate(sestine_risultanti[:50]): # Top 50 per leggibilità
                with (c1 if idx % 2 == 0 else c2):
                    with st.expander(f"Eletta {idx+1} - Errore: {err:.8f}"):
                        st.code(s)
                        st.caption(f"H: {h_v:.5f} | Salto: {d_v:.5f}")
        else:
            st.warning("Nessuna risonanza trovata. Prova a rilanciare.")

except Exception as e:
    st.error(f"Errore: {e}")
