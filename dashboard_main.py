import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAZIONE E CONNESSIONE ---
URL = "TUA_URL_SUPABASE"
KEY = "TUA_ANON_KEY"
supabase = create_client(URL, KEY)

st.set_page_config(page_title="Parisi-137 Dashboard", layout="wide", page_icon="🔬")

# --- 2. LOGICA SCIENTIFICA (MOTORE PARISI) ---
def calcola_rugosita(sestina):
    """Calcola la rugosità superficiale basata sul gap dei numeri."""
    sestina_ordinata = sorted(sestina)
    diffs = np.diff(sestina_ordinata)
    if np.mean(diffs) == 0: return 0
    return np.std(diffs) / np.mean(diffs)

@st.cache_data(ttl=3600) # Aggiorna i dati ogni ora
def get_historical_data():
    # Recuperiamo le ultime 500 estrazioni per l'analisi del trend
    response = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(500).execute()
    df = pd.DataFrame(response.data)
    # Calcolo rugosità H per ogni riga
    df['H'] = df.apply(lambda row: calcola_rugosita([row['n1'], row['n2'], row['n3'], row['n4'], row['n5'], row['n6']]), axis=1)
    return df

# --- 3. INTERFACCIA UTENTE (DASHBOARD) ---
st.title("🔬 Topologia dei Sistemi Complessi: Modello Parisi-137")
st.markdown("""
Questa dashboard analizza la **rugosità superficiale** delle sestine estratte. 
L'obiettivo è identificare configurazioni in prossimità della **Risonanza Quantistica (H = 0.137)**.
""")

try:
    df = get_historical_data()
    ultima_data = df['data_estrazione'].iloc[0]
    
    # KPI Superiori
    h_medio_137 = df['H'].head(137).mean()
    delta_risonanza = abs(h_medio_137 - 0.137)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ultima Estrazione", ultima_data)
    m2.metric("Rugosità Media (H)", f"{h_medio_137:.4f}")
    m3.metric("Delta Risonanza", f"{delta_risonanza:.4f}", delta_color="inverse")

    # Grafico Principale: Oscilloscopio di Fase
    st.divider()
    st.subheader("📈 Oscilloscopio di Fase: Andamento della Rugosità")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['data_estrazione'], y=df['H'], mode='lines', name='H-Rugosity', line=dict(color='#00ffcc', width=2)))
    fig.add_hline(y=0.137, line_dash="dash", line_color="red", annotation_text="Target Risonanza 137")
    
    fig.update_layout(template="plotly_dark", hovermode="x unified", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Analisi Predittiva (Tua Logica originale)
    st.divider()
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🧩 Numeri in Fase")
        st.write("Calcolo dei candidati che minimizzano il Delta di Risonanza rispetto all'ultima configurazione.")
        
        ultima_sestina = df[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].iloc[0].values
        target_numbers = []
        
        # Iterazione per trovare numeri che risuonano con 0.137
        for n in range(1, 91):
            if n not in ultima_sestina:
                test_sestina = list(ultima_sestina[1:]) + [n]
                if abs(calcola_rugosita(test_sestina) - 0.137) < delta_risonanza:
                    target_numbers.append(n)
        
        st.success(f"Trovati {len(target_numbers)} numeri in fase armonica.")
        st.code(sorted(target_numbers), language='python')

    with col_right:
        st.subheader("📊 Distribuzione Topologica")
        # Visualizzazione della densità dei numeri nell'ultimo blocco di 137 estrazioni
        last_137 = df.head(137)[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].values.flatten()
        fig_hist = go.Figure(data=[go.Histogram(x=last_137, nbinsx=90, marker_color='#636EFA')])
        fig_hist.update_layout(template="plotly_dark", height=350, title="Presenza Numeri nello Spazio delle Fasi (137)")
        st.plotly_chart(fig_hist, use_container_width=True)

except Exception as e:
    st.error(f"Errore durante il caricamento dei dati: {e}")
    st.info("Verifica che le credenziali Supabase siano corrette e che la tabella 'estrazioni' sia popolata.")
