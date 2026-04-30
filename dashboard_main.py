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
    st.error("Configurazione Segreti mancante. Verifica il file secrets.toml o i Secrets su Streamlit Cloud.")
    st.stop()

supabase = create_client(URL, KEY)

# --- MOTORE DI CALCOLO (LOGICA PARISI RAFFINATA) ---
def calcola_rugosita(sestina):
    """Metrica di Parisi: Variazione dei gap nella distribuzione numerica."""
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    # Calcolo della deviazione standard relativa (Rugosità H)
    return np.std(diffs) / mu if mu != 0 else 0[cite: 1]

@st.cache_data(ttl=600) 
def load_and_process():
    # Recupero delle ultime 500 estrazioni per l'analisi topologica
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(500).execute()
    data_df = pd.DataFrame(res.data)
    # Vettorializzazione del calcolo H su tutto lo storico caricato
    data_df['H'] = data_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    return data_df

# --- INTERFACCIA ---
st.set_page_config(page_title="Parisi-137 Dashboard", layout="wide", page_icon="🔬")
st.title("🔬 Modello Topologico di Risonanza 137")
st.markdown("Analisi della rottura di simmetria basata sulla costante di struttura fine ($1/137$).")

try:
    df = load_and_process()
    
    # Analisi dei blocchi armonici (137 estrazioni come finestra di riferimento)
    h_medio_137 = df['H'].head(137).mean()[cite: 1]
    delta_risonanza = abs(h_medio_137 - 0.137)[cite: 1]

    # Header Metrics con i dati reali da Supabase
    c1, c2, c3 = st.columns(3)
    c1.metric("Ultima Osservazione", df['data_estrazione'].iloc[0])[cite: 1]
    c2.metric("Rugosità Media (H)", f"{h_medio_137:.4f}")[cite: 1]
    c3.metric("Scostamento Armonico", f"{delta_risonanza:.4f}")[cite: 1]

    # Oscilloscopio di Fase
    st.subheader("📊 Fluttuazione Superficiale della Rugosità")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['data_estrazione'], y=df['H'], name="H (Rugosità)", line=dict(color='#00d1ff', width=1.5)))
    # Linea target basata sulla costante fisica
    fig.add_hline(y=0.137, line_dash="dash", line_color="red", annotation_text="Punto di Risonanza")[cite: 1]
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # SEZIONE RAFFINATA: CALCOLO CANDIDATI
    st.divider()
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.subheader("🧩 Candidati in Fase")
        ultima_sestina = df[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].iloc[0].values[cite: 1]
        candidati_potenziali = []
        
        # Iterazione per minimizzazione dello scostamento
        for n in range(1, 91):
            if n not in ultima_sestina:
                # Test di inserimento nella finestra mobile
                test_s = list(ultima_sestina[1:]) + [n][cite: 1]
                h_test = calcola_rugosita(test_s)
                
                # Filtro di qualità: cerchiamo numeri che riducano l'entropia attuale[cite: 1]
                if abs(h_test - 0.137) < (delta_risonanza * 0.5):[cite: 1]
                    candidati_potenziali.append((n, h_test))
        
        # Ordinamento dei candidati per merito (chi è più vicino allo 0.137)[cite: 1]
        candidati_potenziali.sort(key=lambda x: abs(x[1] - 0.137))[cite: 1]
        finali = [x[0] for x in candidati_potenziali[:12]] # Top 12 interferenze costruttive[cite: 1]
        
        if finali:
            st.success(f"Rilevate {len(finali)} interferenze dominanti")
            st.code(sorted(finali)) # Visualizzazione ordinata per facilità di lettura[cite: 1]
        else:
            st.warning("Nessuna interferenza critica rilevata.")

    with col_b:
        st.subheader("🌡️ Distribuzione nel Blocco 137")
        # Visualizzazione della saturazione numerica nelle ultime 137 estrazioni[cite: 1]
        all_vals = df.head(137)[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].values.flatten()
        counts = pd.Series(all_vals).value_counts().reindex(range(1, 91), fill_value=0)
        st.bar_chart(counts, color="#636EFA")

except Exception as e:
    st.error(f"Errore durante l'esecuzione: {e}")[cite: 1]
