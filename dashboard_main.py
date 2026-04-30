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
    """Calcolo vettoriale rapido della rugosità H"""
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale_doppia():
    """Scansione storica per estrarre le costanti Q e ΔQ"""
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
st.set_page_config(page_title="Parisi-137 Ultra-Selettivo", layout="wide")
st.title("🔬 Sistema Parisi-137: Morsa 0.01% & Delta Priority")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    
    h_136_attuale = df_full['H'].iloc[0]
    media_attuale_136 = df_full['H'].iloc[0:136].mean()
    
    # PARAMETRI TARGET
    target_h = media_attuale_136 * Q_medio
    # MORSA MILLIMETRICA: 0.01%
    morsa_millimetrica = target_h * 0.0001 

    st.success(f"Analisi completata. Legge Universale stabilita su {len(df_full)-137} cicli.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Bersaglio H", f"{target_h:.6f}")
    c2.metric("Salto ΔH Storico", f"{Delta_medio:.6f}")
    c3.metric("Morsa (0.01%)", f"±{morsa_millimetrica:.8f}")

    st.divider()

    # --- MOTORE DI SINTESI AD ALTA PRESSIONE (1 MILIONE) ---
    if st.button("Lancia Sintesi Ultra-Selettiva (1M Cicli)"):
        sestine_risultanti = []
        n_tentativi = 1000000
        prog_bar = st.progress(0)
        status_text = st.empty()
        
        # Elaborazione a blocchi per evitare il timeout del server
        batch_size = 50000
        start_time = time.time()

        for batch in range(0, n_tentativi, batch_size):
            for _ in range(batch_size):
                s = sorted(random.sample(range(1, 91), 6))
                h_s = calcola_rugosita(s)
                
                err_h = abs(h_s - target_h)
                
                # FILTRO MORSA MILLIMETRICA
                if err_h < morsa_millimetrica:
                    salto_s = h_s - h_136_attuale
                    err_salto = abs(salto_s - Delta_medio)
                    
                    # PONDERAZIONE DELTA: Il salto deve essere 10 volte più preciso dell'H
                    # Questo stringe l'imbuto sulla coerenza sequenziale
                    err_ponderato = err_h + (err_salto * 10)
                    sestine_risultanti.append((s, err_ponderato, h_s, salto_s))
            
            # Aggiornamento UI
            progress = (batch + batch_size) / n_tentativi
            prog_bar.progress(progress)
            status_text.text(f"Scansione: {batch + batch_size:,} / {n_tentativi:,} combinazioni...")

        prog_bar.empty()
        status_text.empty()
        duration = time.time() - start_time

        # Ordinamento per errore ponderato
        sestine_risultanti.sort(key=lambda x: x[1])

        if sestine_risultanti:
            st.info(f"Sintesi completata in {duration:.1f}s. Trovate {len(sestine_risultanti)} combinazioni dominanti.")
            
            # Visualizzazione risultati
            for idx, (s, err, h_v, d_v) in enumerate(sestine_risultanti):
                # Mostriamo solo quelle con errore veramente basso per non intasare
                with st.expander(f"✨ Sestina Specchio {idx+1} (Errore Ponderato: {err:.10f})"):
                    st.code(f"{s}")
                    st.write(f"**Precisione H:** {abs(h_v - target_h):.10f}")
                    st.write(f"**Coerenza Salto ΔH:** {abs(d_v - Delta_medio):.10f}")
        else:
            st.warning("Nessuna sestina è passata attraverso la morsa millimetrica. La coerenza del sistema è attualmente inaccessibile.")

except Exception as e:
    st.error(f"Errore: {e}")
