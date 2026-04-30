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
    """Calcolo vettoriale della rugosità H"""
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale_doppia():
    """Scansione storica per estrarre le costanti Q e ΔQ"""
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    full_df = pd.DataFrame(res.data)
    
    # Calcolo H massivo
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
st.set_page_config(page_title="Parisi-137 Elite", layout="wide")
st.title("🔬 Sistema Parisi-137: Morsa Dinamica 0.5%")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    
    h_136_attuale = df_full['H'].iloc[0]
    media_attuale_136 = df_full['H'].iloc[0:136].mean()
    
    # DEFINIZIONE TARGET
    target_h = media_attuale_136 * Q_medio
    # MORSA D'ÉLITE: Restringiamo allo 0.5% del valore target
    morsa_selettiva = target_h * 0.005 

    st.success(f"Analisi completata su {len(df_full)-137} cicli.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Bersaglio H", f"{target_h:.6f}")
    col2.metric("Salto ΔH Atteso", f"{Delta_medio:.6f}")
    col3.metric("Morsa Selettiva", f"±{morsa_selettiva:.6f}")

    st.divider()

    # --- MOTORE DI SINTESI AD ALTA PRESSIONE ---
    if st.button("Esegui Sintesi d'Élite (200.000 cicli)"):
        sestine_risultanti = []
        n_tentativi = 200000
        prog_bar = st.progress(0)
        
        for i in range(n_tentativi):
            if i % 5000 == 0: prog_bar.progress(i / n_tentativi)
            
            s = sorted(random.sample(range(1, 91), 6))
            h_s = calcola_rugosita(s)
            
            err_h = abs(h_s - target_h)
            
            # APPLICAZIONE MORSA
            if err_h < morsa_selettiva:
                salto_s = h_s - h_136_attuale
                err_salto = abs(salto_s - Delta_medio)
                
                # Errore Combinato (Vettoriale)
                err_tot = np.sqrt(err_h**2 + err_salto**2)
                sestine_risultanti.append((s, err_tot, h_s, salto_s))

        prog_bar.empty()
        
        # Ordinamento per errore totale minimo
        sestine_risultanti.sort(key=lambda x: x[1])

        if sestine_risultanti:
            st.info(f"Trovate {len(sestine_risultanti)} combinazioni superstiti.")
            
            # Visualizzazione a griglia per scorrere velocemente
            cols = st.columns(2)
            for idx, (s, err, h_v, d_v) in enumerate(sestine_risultanti):
                with cols[idx % 2]:
                    with st.expander(f"🏆 Eletta {idx+1} (Errore: {err:.8f})"):
                        st.code(f"{s}")
                        st.write(f"**H:** {h_v:.6f} | **ΔH:** {d_v:.6f}")
        else:
            st.warning("Nessuna sestina è riuscita a passare attraverso la morsa dello 0.5%. Prova a rilanciare.")

except Exception as e:
    st.error(f"Errore: {e}")
