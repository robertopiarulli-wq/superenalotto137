import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- CONFIGURAZIONE PROFESSIONALE ---
# Streamlit legge automaticamente da .streamlit/secrets.toml in locale
# o dai "Secrets" nelle impostazioni di GitHub/Streamlit Cloud
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
except KeyError:
    st.error("Configurazione Segreti mancante. Verifica il file secrets.toml.")
    st.stop()

supabase = create_client(URL, KEY)

# --- MOTORE DI CALCOLO (LOGICA PARISI) ---
def calcola_rugosita(sestina):
    """Metrica di Parisi: Variazione dei gap nella distribuzione numerica."""
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=600) # Cache 10 minuti per efficienza su GitHub
def load_and_process():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(500).execute()
    data_df = pd.DataFrame(res.data)
    # Vettorializzazione del calcolo H per massimizzare le performance
    data_df['H'] = data_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    return data_df

# --- INTERFACCIA ---
st.set_page_config(page_title="Parisi-137 Analisi", layout="wide")
st.title("🔬 Modello Topologico di Risonanza 137")

try:
    df = load_and_process()
    
    # Analisi dei blocchi armonici
    h_medio_137 = df['H'].head(137).mean()
    delta_risonanza = abs(h_medio_137 - 0.137)

    # Header Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Data Ultima Osservazione", df['data_estrazione'].iloc[0])
    c2.metric("Rugosità Media (H)", f"{h_medio_137:.4f}")
    c3.metric("Scostamento Armonico", f"{delta_risonanza:.4f}")

    # Oscilloscopio di Fase (Plotly)
    st.subheader("📊 Fluttuazione Superficiale della Rugosità")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['data_estrazione'], y=df['H'], name="H", line=dict(color='#00d1ff')))
    fig.add_hline(y=0.137, line_dash="dash", line_color="red", annotation_text="Punto di Risonanza")
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Calcolo Numeri in Fase (Tua logica di raffinamento)
    st.divider()
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        st.subheader("🧩 Candidati in Fase")
        ultima = df[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].iloc[0].values
        
        # Filtro armonico: cerchiamo i numeri che portano il sistema verso 0.137
        fase_numeri = []
        for n in range(1, 91):
            if n not in ultima:
                # Simuliamo la nuova possibile configurazione
                test_s = list(ultima[1:]) + [n]
                if abs(calcola_rugosita(test_s) - 0.137) < delta_risonanza:
                    fase_numeri.append(n)
        
        st.info(f"Numeri rilevati in interferenza costruttiva: {len(fase_numeri)}")
        st.code(sorted(fase_numeri))

    with col_b:
        st.subheader("🌡️ Mappa Termica delle Frequenze (Blocco 137)")
        all_vals = df.head(137)[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].values.flatten()
        counts = pd.Series(all_vals).value_counts().reindex(range(1, 91), fill_value=0)
        st.bar_chart(counts)

except Exception as e:
    st.error(f"Errore critico di sistema: {e}")
