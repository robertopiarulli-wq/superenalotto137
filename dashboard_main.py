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

# --- MOTORE TOPOLOGICO ADATTIVO ---
def calcola_rugosita(sestina):
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=600) 
def load_and_analyze_adaptive():
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
st.set_page_config(page_title="Parisi-137 Adaptive", layout="wide")
st.title("🔬 Sintesi Complementare: Tolleranza Elastica")

try:
    df, medie_blocchi, deltas = load_and_analyze_adaptive()
    
    # 1. CALCOLO DELLA TOLLERANZA DINAMICA
    h_medio_storico = np.mean(medie_blocchi)
    h_ultimo_blocco = medie_blocchi[0]
    squilibrio = h_ultimo_blocco - h_medio_storico
    target_delta = -squilibrio 
    
    # Usiamo la deviazione standard dei delta storici per definire la "banda di risonanza"
    volatilita_storica = np.std(deltas)
    tolleranza_elastica = volatilita_storica / 3  # Regolazione della sensibilità
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Squilibrio", f"{squilibrio:.4f}")
    c2.metric("Target Δ", f"{target_delta:.4f}")
    c3.metric("Tolleranza (±)", f"{tolleranza_elastica:.4f}")
    c4.metric("Volatilità Sistema", f"{volatilita_storica:.4f}")

    st.divider()

    # 2. MOTORE DI SINTESI PLASMATO SULLA STRUTTURA FINE
    corpo_136 = df['H'].iloc[1:137].tolist()
    sestine_elette = []
    
    with st.spinner("Ricerca in corso nella banda di risonanza..."):
        # Portiamo a 200.000 i tentativi per esplorare meglio lo spazio dopo il rilassamento
        for _ in range(200000):
            s = sorted(random.sample(range(1, 91), 6))
            
            # FILTRO STRUTTURA FINE: Distanza minima e variabilità interna
            diffs = np.diff(s)
            if any(diffs < 2) or np.std(diffs) < 1.5: continue 
            
            h_sest = calcola_rugosita(s)
            nuova_media_blocco = np.mean(corpo_136 + [h_sest])
            nuovo_delta = nuova_media_blocco - medie_blocchi[1]
            
            # FILTRO DINAMICO: La morsa ora "respira" con il sistema
            if abs(nuovo_delta - target_delta) < tolleranza_elastica:
                distanza_equilibrio = abs(nuova_media_blocco - h_medio_storico)
                sestine_elette.append((s, distanza_equilibrio, nuovo_delta))

    # Ordiniamo per chi si avvicina di più al cuore della Kostante
    sestine_elette.sort(key=lambda x: x[1])

    # 3. VISUALIZZAZIONE RISULTATI
    if sestine_elette:
        st.subheader(f"💎 Sestine Complementari in Risonanza (Top {min(len(sestine_elette), 8)})")
        
        for i in range(0, min(len(sestine_elette), 8), 2):
            col_a, col_b = st.columns(2)
            for j, col in enumerate([col_a, col_b]):
                if i+j < len(sestine_elette):
                    s, err, d = sestine_elette[i+j]
                    with col:
                        st.success(f"**Soluzione di Fase {i+j+1}**")
                        st.code(f"{s}")
                        st.caption(f"Scostamento: {err:.6f} | Δ Generato: {d:.5f}")
    else:
        st.warning("Il sistema è in una fase di tensione estrema. Anche con la tolleranza elastica non emergono soluzioni armoniche.")

except Exception as e:
    st.error(f"Errore: {e}")
