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

# --- MOTORE TOPOLOGICO AVANZATO ---
def calcola_rugosita(sestina):
    """Calcola la rugosità H basata sulla deviazione standard dei gap."""
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale_doppia():
    """Scansiona il DB estraendo il Quid (Rapporto) e il Delta Quid (Salto)."""
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    full_df = pd.DataFrame(res.data)
    
    full_df['H'] = full_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    quid_proporzionali = [] # Costante A (Rapporto)
    quid_delta = []        # Costante B (Salto energetico)
    
    # Analisi dei cicli da 137 estrazioni
    for i in range(len(full_df) - 137):
        h_137 = full_df['H'].iloc[i]              # Chiusura ciclo
        h_136_prec = full_df['H'].iloc[i+1]       # L'estrazione subito precedente
        h_corpo_136 = full_df['H'].iloc[i+1 : i+137]
        
        media_corpo = h_corpo_136.mean()
        if media_corpo != 0:
            quid_proporzionali.append(h_137 / media_corpo)
            quid_delta.append(h_137 - h_136_prec)
            
    return full_df, np.mean(quid_proporzionali), np.mean(quid_delta), np.std(quid_proporzionali)

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Parisi-137 Double Constraint", layout="wide")
st.title("🔬 Sistema Parisi-137: Doppia Morsa Universale")

try:
    with st.spinner("Analisi della dinamica dei flussi (H + ΔH)..."):
        df_full, Q_medio, Delta_medio, Q_std = analizza_legge_universale_doppia()
    
    # 1. PARAMETRI DI CHIUSURA ATTUALE
    h_136_attuale = df_full['H'].iloc[0] # L'ultima rugosità uscita realmente
    media_attuale_136 = df_full['H'].iloc[0:136].mean()
    
    # Target combinati
    target_h = media_attuale_136 * Q_medio
    target_salto = Delta_medio
    tolleranza = Q_std * media_attuale_136
    
    # Dashboard Metriche
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quid Universale (Q)", f"{Q_medio:.4f}")
    c2.metric("Delta Quid (ΔQ)", f"{Delta_medio:.4f}")
    c3.metric("Target Rugosità (H)", f"{target_h:.4f}")
    c4.metric("Banda Risonanza", f"±{tolleranza:.4f}")

    st.divider()

    # 2. MOTORE DI SINTESI A DOPPIO VINCOLO (1.000.000 TENTATIVI)
    st.subheader("🧬 Sintesi ad Alta Pressione Topologica")
    
    sestine_risultanti = []
    numero_tentativi = 1000000
    
    with st.spinner(f"Filtrando {numero_tentativi} combinazioni..."):
        for _ in range(numero_tentativi):
            s = sorted(random.sample(range(1, 91), 6))
            
            # Libertà Entropica (nessun filtro su consecutivi)
            if np.std(np.diff(s)) < 0.5: continue 
            
            h_s = calcola_rugosita(s)
            salto_s = h_s - h_136_attuale
            
            # ERRORE COMBINATO: 
            # Valutiamo quanto la sestina rispetta ENTRAMBE le costanti universali
            err_h = abs(h_s - target_h)
            err_salto = abs(salto_s - target_salto)
            
            # Filtro di ammissione: deve rientrare nella banda di risonanza per H
            if err_h < tolleranza:
                # L'errore totale è la sintesi dei due vettori
                errore_totale = err_h + err_salto
                sestine_risultanti.append((s, errore_totale, h_s, salto_s))

    # ORDINAMENTO PER MINIMO ERRORE COMBINATO (Il bandolo della matassa)
    sestine_risultanti.sort(key=lambda x: x[1])

    # 3. VISUALIZZAZIONE RISULTATI
    if sestine_risultanti:
        st.info(f"Risonanza trovata: {len(sestine_risultanti)} configurazioni compatibili.")
        
        cols = st.columns(2)
        for idx, (s, err_tot, h_val, salto_val) in enumerate(sestine_risultanti):
            with cols[idx % 2]:
                st.success(f"**Sestina Eletta {idx+1}**")
                st.code(f"{s}")
                st.caption(f"H: {h_val:.5f} | Salto ΔH: {salto_val:.5f} | Errore Combinato: {err_tot:.8f}")
    else:
        st.error("La doppia morsa non ha permesso il passaggio di alcuna combinazione. Il sistema è in saturazione.")

except Exception as e:
    st.error(f"Errore critico: {e}")
