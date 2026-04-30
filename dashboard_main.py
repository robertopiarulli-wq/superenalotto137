import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import random

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
    return full_df, np.mean(q_prop), np.mean(q_delta), np.std(q_prop)

st.set_page_config(page_title="Parisi-137 Optimized", layout="wide")
st.title("🔬 Sistema Parisi-137: Motore Ottimizzato")

try:
    df_full, Q_medio, Delta_medio, Q_std = analizza_legge_universale_doppia()
    
    h_136_attuale = df_full['H'].iloc[0]
    media_attuale_136 = df_full['H'].iloc[0:136].mean()
    target_h = media_attuale_136 * Q_medio
    tolleranza = Q_std * media_attuale_136

    st.success(f"Dati pronti. Target H: {target_h:.4f} | Target ΔH: {Delta_medio:.4f}")

    # --- MOTORE DI SINTESI ALLEGGERITO ---
    sestine_risultanti = []
    # 200k è il "dolce stil novo" per Streamlit: veloce e preciso.
    n_tentativi = 200000 
    
    if st.button("Avvia Sintesi Profonda (200k cicli)"):
        prog_bar = st.progress(0)
        for i in range(n_tentativi):
            # Update barra ogni 10k per non rallentare
            if i % 10000 == 0: prog_bar.progress(i / n_tentativi)
            
            s = sorted(random.sample(range(1, 91), 6))
            h_s = calcola_rugosita(s)
            
            err_h = abs(h_s - target_h)
            if err_h < tolleranza:
                salto_s = h_s - h_136_attuale
                err_tot = err_h + abs(salto_s - Delta_medio)
                sestine_risultanti.append((s, err_tot, h_s, salto_s))

        prog_bar.empty()
        sestine_risultanti.sort(key=lambda x: x[1])

        if sestine_risultanti:
            st.info(f"Trovate {len(sestine_risultanti)} combinazioni.")
            # Mostriamo le top 20 per sicurezza del browser
            for s, err, h_v, d_v in sestine_risultanti[:50]:
                with st.expander(f"Sestina Errore: {err:.8f}"):
                    st.code(s)
                    st.write(f"H: {h_v:.5f} | ΔH: {d_v:.5f}")
        else:
            st.warning("Nessuna risonanza. Riprova.")

except Exception as e:
    st.error(f"Errore: {e}")
