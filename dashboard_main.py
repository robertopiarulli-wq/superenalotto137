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

# --- MOTORE TOPOLOGICO E SCANSIONE QUID UNIVERSALE ---
def calcola_rugosita(sestina):
    """Calcola la rugosità H basata sulla deviazione standard dei gap."""
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale():
    """Scansiona il DB con finestra mobile di 137 estrazioni per estrarre il Quid."""
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    full_df = pd.DataFrame(res.data)
    
    # Pre-calcolo rugosità H per tutto il database
    full_df['H'] = full_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    quid_universali = []
    
    # FRENO A MANO 137: Ci fermiamo prima che i dati diventino insufficienti per un blocco integro.
    for i in range(len(full_df) - 137):
        h_chiusura = full_df['H'].iloc[i]             # La "137-esima" di quel ciclo storico
        h_precedenti = full_df['H'].iloc[i+1 : i+137]   # Il corpo di 136 estrazioni precedenti
        
        media_corpo = h_precedenti.mean()
        if media_corpo != 0:
            quid_universali.append(h_chiusura / media_corpo)
            
    return full_df, np.mean(quid_universali), np.std(quid_universali)

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Parisi-137 Deep Scan", layout="wide")
st.title("🔬 Sistema Parisi-137: Sintesi Totale in Libertà Entropica")

try:
    with st.spinner("Scansione della memoria storica totale (Finestra Mobile 137)..."):
        df_full, Q_medio, Q_std = analizza_legge_universale()
    
    # 1. ANALISI DELLE ULTIME 136 REALI (Il Presente)
    # Prendiamo le estrazioni da 0 a 135 (le 136 effettive caricate di tensione).
    corpo_attuale_136 = df_full['H'].iloc[0:136]
    media_attuale = corpo_attuale_136.mean()
    
    # Calcolo del Bersaglio Fisico (Quid Universale applicato al presente)
    h_target_prossima = media_attuale * Q_medio
    tolleranza_reale = Q_std * media_attuale
    
    # Dashboard Metriche
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quid Medio (Q)", f"{Q_medio:.4f}")
    c2.metric("Target Rugosità (H)", f"{h_target_prossima:.4f}")
    c3.metric("Banda Risonanza (±)", f"{tolleranza_reale:.4f}")
    c4.metric("Cicli Analizzati", f"{len(df_full)-137}")

    st.divider()

    # 2. MOTORE DI SINTESI PROFONDA (1.000.000 DI TENTATIVI)
    st.subheader(f"🧬 Esplorazione Spazio delle Fasi: 1.000.000 di campioni")
    
    sestine_risultanti = []
    numero_tentativi = 1000000
    
    with st.spinner("Elaborazione in corso..."):
        for _ in range(numero_tentativi):
            s = sorted(random.sample(range(1, 91), 6))
            
            # LIBERTÀ ENTROPICA: Nessun filtro sui numeri consecutivi.
            # Unico vincolo: variabilità minima per evitare sestine matematicamente piatte.
            if np.std(np.diff(s)) < 0.5: continue 
            
            h_sestina = calcola_rugosita(s)
            
            # La sestina deve entrare nella risonanza del Quid Universale
            if abs(h_sestina - h_target_prossima) < tolleranza_reale:
                errore = abs(h_sestina - h_target_prossima)
                sestine_risultanti.append((s, errore, h_sestina))

    # ORDINAMENTO CHIRURGICO: Le soluzioni più precise in cima alla lista[cite: 1, 2].
    sestine_risultanti.sort(key=lambda x: x[1])

    # 3. VISUALIZZAZIONE RISULTATI TOTALI
    if sestine_risultanti:
        st.info(f"Trovate {len(sestine_risultanti)} combinazioni armoniche su {numero_tentativi} tentativi.")
        
        cols = st.columns(2)
        # Mostriamo tutte le soluzioni senza il limite di 10
        for idx, (s, err, h_val) in enumerate(sestine_risultanti):
            with cols[idx % 2]:
                st.success(f"**Sestina Specchio {idx+1}**")
                st.code(f"{s}")
                st.caption(f"Rugosità H: {h_val:.6f} | Errore Assoluto: {err:.8f}")
    else:
        st.error("Nessun punto di risonanza trovato. La morsa del sistema è attualmente impenetrabile.")

except Exception as e:
    st.error(f"Errore durante la sintesi profonda: {e}")
