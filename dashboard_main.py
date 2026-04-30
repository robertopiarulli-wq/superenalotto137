import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
import random

# --- CONNESSIONE DATABASE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
except KeyError:
    st.error("Configurazione Segreti mancante nei secrets di Streamlit.")
    st.stop()

supabase = create_client(URL, KEY)

# --- MOTORE TOPOLOGICO E SCANSIONE QUID ---
def calcola_rugosita(sestina):
    """Calcola la rugosità H basata sulla deviazione standard dei gap."""
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale():
    """Scansiona il DB con finestra mobile di 137 estrazioni."""
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    full_df = pd.DataFrame(res.data)
    
    # Pre-calcolo rugosità per tutto il database
    full_df['H'] = full_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    quid_universali = []
    
    # IL CUORE DEL RAGIONAMENTO: 
    # Ci fermiamo a len(df) - 137 per avere solo blocchi integri 136+1.
    for i in range(len(full_df) - 137):
        h_chiusura = full_df['H'].iloc[i]             # La "137-esima" del ciclo i
        h_precedenti = full_df['H'].iloc[i+1 : i+137]   # Il corpo di 136 estrazioni
        
        media_corpo = h_precedenti.mean()
        if media_corpo != 0:
            quid_universali.append(h_chiusura / media_corpo)
            
    return full_df, np.mean(quid_universali), np.std(quid_universali)

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Parisi-137 Universal Law", layout="wide")
st.title("🔬 Sistema Parisi-137: Legge del Quid Universale")

try:
    with st.spinner("Scansione della memoria storica totale (Finestra Mobile 137)..."):
        df_full, Q_medio, Q_std = analizza_legge_universale()
    
    # 1. ANALISI DELLE ULTIME 136 REALI (Il Presente)
    # Prendiamo le estrazioni da 0 a 135 (le ultime 136 uscite).
    corpo_attuale_136 = df_full['H'].iloc[0:136]
    media_attuale = corpo_attuale_136.mean()
    
    # Calcolo del Bersaglio per la prossima estrazione (la numero 137)
    h_target_prossima = media_attuale * Q_medio
    tolleranza_reale = Q_std * media_attuale
    
    # Dashboard Metriche
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quid Medio Universale (Q)", f"{Q_medio:.4f}")
    c2.metric("Target Rugosità (H)", f"{h_target_prossima:.4f}")
    c3.metric("Banda di Risonanza (±)", f"{tolleranza_reale:.4f}")
    c4.metric("Cicli Analizzati", f"{len(df_full)-137}")

    st.divider()

    # 2. MOTORE DI SINTESI DELLE SESTINE SPECCHIO
    st.subheader("🧬 Generazione Sestine di Chiusura Ciclo")
    
    sestine_risultanti = []
    
    with st.spinner("Sintetizzando configurazioni compatibili con la legge Q..."):
        # Tentativi massicci per trovare la precisione millimetrica
        for _ in range(250000):
            s = sorted(random.sample(range(1, 91), 6))
            
            # Filtro Struttura Fine (evitiamo numeri consecutivi e troppa simmetria)
            diffs = np.diff(s)
            if any(diffs < 2) or np.std(diffs) < 1.5: continue 
            
            h_sestina = calcola_rugosita(s)
            
            # La sestina deve "fittare" perfettamente nel bersaglio Q.
            if abs(h_sestina - h_target_prossima) < tolleranza_reale:
                errore = abs(h_sestina - h_target_prossima)
                sestine_risultanti.append((s, errore, h_sestina))

    # Ordiniamo per la minima distanza dal target ideale
    sestine_risultanti.sort(key=lambda x: x[1])

    # 3. VISUALIZZAZIONE RISULTATI
    if sestine_risultanti:
        cols = st.columns(2)
        for idx, (s, err, h_val) in enumerate(sestine_risultanti[:8]):
            with cols[idx % 2]:
                st.success(f"**Sestina Specchio {idx+1}**")
                st.code(f"{s}")
                st.caption(f"H Sestina: {h_val:.5f} | Deviazione dal Q: {err:.6f}")
    else:
        st.warning("Nessuna sestina trovata. Il sistema richiede una precisione di rientro superiore. Prova a ricaricare.")

except Exception as e:
    st.error(f"Errore critico nel calcolo della finestra mobile: {e}")
