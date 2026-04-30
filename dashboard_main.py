import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- CONFIGURAZIONE PROFESSIONALE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
except KeyError:
    st.error("Configurazione Segreti mancante. Verifica i Secrets su Streamlit Cloud.")
    st.stop()

supabase = create_client(URL, KEY)

# --- MOTORE DI CALCOLO (LOGICA PARISI) ---
def calcola_rugosita(sestina):
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=600) 
def load_and_process_multi_block():
    # Carichiamo 13 blocchi da 137 estrazioni (totale 1781)
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(1781).execute()
    data_df = pd.DataFrame(res.data)
    
    # Calcolo rugosità H per ogni estrazione
    data_df['H'] = data_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    # Calcolo della rugosità media per ciascuno dei 13 blocchi
    medie_blocchi = []
    for i in range(13):
        inizio = i * 137
        fine = (i + 1) * 137
        fetta = data_df['H'].iloc[inizio:fine]
        if not fetta.empty:
            medie_blocchi.append(fetta.mean())
            
    return data_df, medie_blocchi

# --- INTERFACCIA ---
st.set_page_config(page_title="Parisi-137 Multi-Block", layout="wide", page_icon="🔬")
st.title("🔬 Analisi Topologica: Costante dei 13 Blocchi")

try:
    df, medie_blocchi = load_and_process_multi_block()
    
    # CALCOLO DELLA BANDA DI RISONANZA (COSTANTE OPERATIVA)
    H_costante = np.mean(medie_blocchi)
    H_sigma = np.std(medie_blocchi)
    H_min = H_costante - H_sigma
    H_max = H_costante + H_sigma
    
    # Rugosità attuale (ultimo blocco)
    h_attuale = df['H'].head(137).mean()

    # Layout Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ultima Osservazione", df['data_estrazione'].iloc[0])
    m2.metric("H Costante (Media 13)", f"{H_costante:.4f}")
    m3.metric("Range Min", f"{H_min:.4f}")
    m4.metric("Range Max", f"{H_max:.4f}")

    # Oscilloscopio con Banda di Risonanza
    st.subheader("📊 Oscilloscopio Multi-Fase (13 Blocchi)")
    fig = go.Figure()
    # Linea Rugosità
    fig.add_trace(go.Scatter(x=df['data_estrazione'], y=df['H'], name="H", line=dict(color='#00d1ff', width=1)))
    # Fascia di Risonanza (Min/Max)
    fig.add_hrect(y0=H_min, y1=H_max, fillcolor="rgba(0, 255, 204, 0.1)", line_width=0, annotation_text="Banda di Risonanza")
    # Linea Media Costante
    fig.add_hline(y=H_costante, line_dash="dash", line_color="yellow", annotation_text="H Costante")
    
    fig.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.subheader("🧩 Candidati in Risonanza")
        st.write(f"Numeri che portano il sistema nel range: **[{H_min:.3f} - {H_max:.3f}]**")
        
        ultima_sestina = df[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].iloc[0].values
        candidati_fase = []
        
        for n in range(1, 91):
            if n not in ultima_sestina:
                # Test di configurazione 136 + ?
                test_s = list(ultima_sestina[1:]) + [n]
                h_test = calcola_rugosita(test_s)
                
                # Accettiamo il numero se la sua rugosità cade nella banda dei 13 blocchi
                if H_min <= h_test <= H_max:
                    # Calcoliamo la distanza dal "cuore" della costante
                    distanza = abs(h_test - H_costante)
                    candidati_fase.append((n, distanza))
        
        # Ordiniamo per chi è più vicino al centro esatto della costante
        candidati_fase.sort(key=lambda x: x[1])
        finali = [x[0] for x in candidati_fase[:12]]
        
        if finali:
            st.success(f"Trovate {len(finali)} assonanze nel range")
            st.code(sorted(finali))
        else:
            st.warning("Nessun numero cade nel range di risonanza attuale.")

    with col_b:
        st.subheader("🌡️ Analisi Ciclica (I 13 Blocchi)")
        # Istogramma delle medie dei 13 blocchi per vedere la stabilità
        fig_blocchi = go.Figure(data=[go.Bar(x=[f"B{i+1}" for i in range(13)], y=medie_blocchi, marker_color='#636EFA')])
        fig_blocchi.add_hline(y=H_costante, line_color="yellow", line_dash="dot")
        fig_blocchi.update_layout(template="plotly_dark", height=300, title="Rugosità Media per Ciclo")
        st.plotly_chart(fig_blocchi, use_container_width=True)

except Exception as e:
    st.error(f"Errore Critico: {e}")
