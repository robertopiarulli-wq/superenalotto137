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
    st.error("Configurazione Segreti mancante.")
    st.stop()

supabase = create_client(URL, KEY)

# --- MOTORE TOPOLOGICO AVANZATO ---
def calcola_rugosita(sestina):
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=600) 
def load_and_analyze_physical_limits():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(1781).execute()
    data_df = pd.DataFrame(res.data)
    data_df['H'] = data_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    medie = []
    for i in range(13):
        fetta = data_df['H'].iloc[i*137 : (i+1)*137]
        if not fetta.empty: medie.append(fetta.mean())
    
    deltas = np.diff(medie[::-1])
    return data_df, medie, deltas

# --- INTERFACCIA ---
st.set_page_config(page_title="Parisi-137 Complementary", layout="wide")
st.title("🔬 Motore a Sestine Complementari: Vincolo Delta")

try:
    df, medie_blocchi, deltas = load_and_analyze_physical_limits()
    
    # PARAMETRI DI VINCOLO
    d_max, d_min = np.max(deltas), np.min(deltas)
    h_medio_storico = np.mean(medie_blocchi)
    h_ultimo_blocco = medie_blocchi[0]
    
    # Rappresentazione Grafica dei Vincoli
    c1, c2, c3 = st.columns(3)
    c1.metric("Delta Max Storico", f"{d_max:.4f}")
    c2.metric("Delta Min Storico", f"{d_min:.4f}")
    c3.metric("H Attuale (Blocco 137)", f"{h_ultimo_blocco:.4f}")

    st.subheader("🧬 Ricerca Sestine Complementari (Bilancio Dinamico)")
    
    # Recuperiamo le ultime 136 estrazioni (il "corpo" del blocco attuale)
    corpo_136 = df['H'].iloc[1:137].tolist()
    
    # Simulazione intelligente invece di combinazioni infinite
    sestine_valide = []
    
    # Tentiamo 50.000 combinazioni casuali ma distribuite per trovare le "complementari"
    for _ in range(50000):
        # Generiamo una sestina con spaziatura minima per evitare sequenze "finte"
        s = sorted(random.sample(range(1, 91), 6))
        if any(np.diff(s) < 2): continue # Salta se ci sono numeri consecutivi
        
        h_sestina = calcola_rugosita(s)
        nuova_media_blocco = np.mean(corpo_136 + [h_sestina])
        nuovo_delta = nuova_media_blocco - medie_blocchi[1] # Delta rispetto al blocco precedente
        
        # IL FILTRO DI PARISI: Deve stare nei limiti dei delta storici
        if d_min <= nuovo_delta <= d_max:
            # Calcoliamo quanto questa sestina sposta il sistema verso la media storica
            scostamento = abs(nuova_media_blocco - h_medio_storico)
            sestine_valide.append((s, scostamento, nuovo_delta))

    # Ordiniamo per la massima precisione verso l'equilibrio
    sestine_valide.sort(key=lambda x: x[1])

    if sestine_valide:
        st.success(f"Identificate {len(sestine_valide)} sestine fisicamente compatibili.")
        
        # Mostriamo le top 6 in un formato pulito
        cols = st.columns(2)
        for idx, (s, err, d) in enumerate(sestine_valide[:6]):
            with cols[idx % 2]:
                st.write(f"**Sestina Complementare {idx+1}**")
                st.code(f"{s} | Delta: {d:.5f}")
                st.caption(f"Precisione Equilibrio: {100 - (err*100):.2f}%")
    else:
        st.warning("Nessuna sestina trovata con i parametri di vincolo attuali. Il sistema è in una fase di alta tensione.")

except Exception as e:
    st.error(f"Errore: {e}")
