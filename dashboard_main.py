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

# --- MOTORE TOPOLOGICO A STRUTTURA FINE ---
def calcola_rugosita(sestina):
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=600) 
def load_and_analyze_precision():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(1781).execute()
    data_df = pd.DataFrame(res.data)
    data_df['H'] = data_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    medie = []
    for i in range(13):
        fetta = data_df['H'].iloc[i*137 : (i+1)*137]
        if not fetta.empty: medie.append(fetta.mean())
    
    deltas = np.diff(medie[::-1])
    return data_df, medie, deltas

# --- UI SETUP ---
st.set_page_config(page_title="Parisi-137 Fine Structure", layout="wide")
st.title("🔬 Sintesi Complementare: Struttura Fine")

try:
    df, medie_blocchi, deltas = load_and_analyze_precision()
    
    # 1. IL VETTORE DI RIENTRO
    h_medio_storico = np.mean(medie_blocchi)
    h_ultimo_blocco = medie_blocchi[0] # Media attuale delle ultime 136+1
    squilibrio = h_ultimo_blocco - h_medio_storico
    
    # Il Delta ideale per annullare lo squilibrio
    target_delta = -squilibrio 
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Squilibrio da Sanare", f"{squilibrio:.4f}", delta_color="inverse")
    c2.metric("Vettore di Rientro (Target Δ)", f"{target_delta:.4f}")
    c3.metric("Kostante di Risonanza", f"{h_medio_storico:.4f}")

    st.divider()

    # 2. MOTORE DI SINTESI (Filtro a 3 Livelli)
    corpo_136 = df['H'].iloc[1:137].tolist()
    sestine_elette = []
    
    # Aumentiamo i tentativi per trovare la "perfezione"
    with st.spinner("Plasmando la struttura fine..."):
        for _ in range(100000):
            s = sorted(random.sample(range(1, 91), 6))
            
            # FILTRO A: Struttura Fine (No numeri vicini, No simmetrie banali)
            diffs = np.diff(s)
            if any(diffs < 3) or np.std(diffs) < 2: continue 
            
            h_sest = calcola_rugosita(s)
            nuova_media_blocco = np.mean(corpo_136 + [h_sest])
            nuovo_delta = nuova_media_blocco - medie_blocchi[1]
            
            # FILTRO B: Precisione sul Vettore di Rientro (Morsa stretta)
            if abs(nuovo_delta - target_delta) < 0.0005: 
                # FILTRO C: Scostamento dalla Kostante
                err_finale = abs(nuova_media_blocco - h_medio_storico)
                sestine_elette.append((s, err_finale, nuovo_delta))

    sestine_elette.sort(key=lambda x: x[1])

    # 3. OUTPUT DEI RISULTATI
    if sestine_elette:
        st.subheader(f"💎 Sestine Elette: Solo {len(sestine_elette[:10])} config. compatibili")
        
        # Visualizzazione a griglia per le top sestine
        for i in range(0, min(len(sestine_elette), 6), 2):
            col_left, col_right = st.columns(2)
            for j, col in enumerate([col_left, col_right]):
                if i+j < len(sestine_elette):
                    s, err, d = sestine_elette[i+j]
                    with col:
                        st.info(f"**Configurazione Complementare {i+j+1}**")
                        st.code(f"{s}")
                        st.caption(f"Precisione: {100-(err*100):.4f}% | Delta Prodotto: {d:.5f}")
    else:
        st.warning("La morsa è troppo stretta. Il sistema non trova una soluzione armonica perfetta.")

except Exception as e:
    st.error(f"Errore critico nella sintesi: {e}")
