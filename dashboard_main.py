import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
from itertools import combinations

# --- CONNESSIONE DATABASE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
except KeyError:
    st.error("Configurazione Segreti mancante.")
    st.stop()

supabase = create_client(URL, KEY)

# --- MOTORE TOPOLOGICO ---
def calcola_rugosita(sestina):
    s_ord = sorted(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=600) 
def load_and_analyze_deltas():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(1781).execute()
    data_df = pd.DataFrame(res.data)
    data_df['H'] = data_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    medie = []
    for i in range(13):
        fetta = data_df['H'].iloc[i*137 : (i+1)*137]
        if not fetta.empty: medie.append(fetta.mean())
    
    # Calcolo Delta tra blocchi consecutivi
    deltas = np.diff(medie[::-1]) # Invertiamo per avere l'ordine cronologico
    return data_df, medie, deltas

# --- UI SETUP ---
st.set_page_config(page_title="Parisi-137 Kostante", layout="wide")
st.title("🔬 Generatore di Fase: Kostante dei Delta")

try:
    df, medie_blocchi, deltas = load_and_analyze_deltas()
    
    # 1. DEFINIZIONE KOSTANTE DINAMICA
    H_target_medio = np.mean(medie_blocchi)
    ultimo_h_blocco = medie_blocchi[0]
    squilibrio = ultimo_h_blocco - H_target_medio
    
    # La Kostante corretta: deve compensare lo squilibrio attuale
    Kostante_Operativa = H_target_medio - squilibrio 
    
    # UI Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Squilibrio Attuale", f"{squilibrio:.4f}", delta=f"{squilibrio:.4f}", delta_color="inverse")
    c2.metric("Kostante Target", f"{Kostante_Operativa:.4f}")
    c3.metric("Ultima Estrazione", df['data_estrazione'].iloc[0])
    c4.metric("Delta Medio", f"{np.mean(np.abs(deltas)):.4f}")

    # 2. VISUALIZZAZIONE DELTA
    st.subheader("📉 Analisi delle Tensioni (13 Delta Storici)")
    fig_delta = go.Figure(data=[go.Scatter(y=deltas, mode='lines+markers', line=dict(color='#ff9900'))])
    fig_delta.add_hline(y=0, line_dash="dash", line_color="white")
    fig_delta.update_layout(template="plotly_dark", height=250, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_delta, use_container_width=True)

    st.divider()

    # 3. GENERAZIONE SESTINE IN RISONANZA
    col_sx, col_dx = st.columns([1, 1])

    with col_sx:
        st.subheader("🧩 Selezione Pivot")
        ultima_sestina = df[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].iloc[0].values
        
        # Troviamo i 12 numeri che singolarmente avvicinano il blocco alla Kostante
        candidati = []
        for n in range(1, 91):
            if n not in ultima_sestina:
                test_h = calcola_rugosita(list(ultima_sestina[1:]) + [n])
                dist = abs(test_h - Kostante_Operativa)
                candidati.append((n, dist))
        
        candidati.sort(key=lambda x: x[1])
        pivot_12 = [x[0] for x in candidati[:12]]
        st.write("I 12 numeri con massima forza di richiamo:")
        st.code(pivot_12)

    with col_dx:
        st.subheader("💎 Sestine in Fase (Errore < 0.0001)")
        # Generiamo sestine partendo dai pivot e testiamo l'impatto sul blocco
        sestine_finali = []
        # Prendiamo le combinazioni dei primi 9 pivot per limitare il calcolo a ~84 combinazioni
        for comb in combinations(pivot_12[:9], 6):
            h_sestina = calcola_rugosita(comb)
            # Verifichiamo se questa sestina "atterra" sulla Kostante
            if abs(h_sestina - Kostante_Operativa) < 0.005: # Margine di tolleranza per la visualizzazione
                sestine_finali.append((comb, abs(h_sestina - Kostante_Operativa)))
        
        sestine_finali.sort(key=lambda x: x[1])
        
        if sestine_finali:
            for i, (s, err) in enumerate(sestine_finali[:5]):
                st.success(f"Sestina {i+1} (Scarto: {err:.5f})")
                st.code(sorted(s))
        else:
            st.warning("Nessuna sestina soddisfa il bilancio dei delta. Prova ad allargare i Pivot.")

except Exception as e:
    st.error(f"Errore nel motore di calcolo: {e}")
