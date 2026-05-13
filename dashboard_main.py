import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import json
import os
import itertools

# --- CONNESSIONE DATABASE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Errore connessione: controlla i secrets.")
    st.stop()

def calcola_rugosita(sestina):
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale_doppia():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    full_df = pd.DataFrame(res.data)
    full_df['H'] = full_df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    q_prop, q_delta = [], []
    for i in range(len(full_df) - 137):
        h_137 = full_df['H'].iloc[i]
        h_136_prec = full_df['H'].iloc[i+1]
        media_corpo = full_df['H'].iloc[i+1 : i+137].mean()
        if media_corpo != 0:
            q_prop.append(h_137 / media_corpo)
            q_delta.append(h_137 - h_136_prec)
    return full_df, np.mean(q_prop), np.mean(q_delta)

def carica_dati_scientifici():
    cardini = []
    valli = []
    pool_completo = []
    
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            pool_completo = json.load(f)
            cardini = pool_completo[:2] if len(pool_completo) >= 2 else pool_completo
            
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        v_df = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)']
        for f in v_df['fascia']:
            nums = f.replace('(', '').replace(']', '').split(',')
            valli.append((float(nums[0]), float(nums[1])))
            
    return cardini, valli, pool_completo

# --- INTERFACCIA ---
st.set_page_config(page_title="Morsa Deterministica Parisi-137", layout="wide")
st.title("🔬 Morsa Scientifica: Generazione da Pool Eletto")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    cardini_auto, valli_target, pool_risonanza = carica_dati_scientifici()
    
    st.sidebar.header("Parametri Motore")
    # Se il pool è vuoto, fallback su cardini manuali
    default_cardini = cardini_auto if cardini_auto else [70, 80]
    cardini_finali = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=default_cardini)
    
    dim_pool = st.sidebar.slider("Ampiezza Pool Eletto", 12, 22, 18)

    h_136_attuale = df_full['H'].iloc[0]
    target_h = df_full['H'].iloc[0:136].mean() * Q_medio
    morsa_millimetrica = target_h * 0.1 

    col1, col2, col3 = st.columns(3)
    col1.metric("Bersaglio Rugosità H", f"{target_h:.5f}")
    col2.metric("Delta Atteso", f"{Delta_medio:.5f}")
    
    if valli_target:
        col3.success(f"{len(valli_target)} Valli di Pressione Attive")
    else:
        col3.warning("Filtro Somma: Wyckoff Standard (150-250)")

    if st.button("🚀 GENERA ARROSTO DETERMINISTICO"):
        # Costruzione del Pool Eletto (Cardini + Top Risonanza)
        pool_eletto = sorted(list(set(cardini_finali + pool_risonanza[:dim_pool])))
        st.write(f"Analisi di tutte le combinazioni possibili dal pool: `{pool_eletto}`")
        
        # Generazione combinatoria C(n, 6)
        tutte_le_sestine = list(itertools.combinations(pool_eletto, 6))
        sestine_risultanti = []
        
        prog_bar = st.progress(0)
        total_comb = len(tutte_le_sestine)
        
        for i, s_tuple in enumerate(tutte_le_sestine):
            s = sorted(list(s_tuple))
            
            # 1. Controllo Fisse (Cardini)
            if all(c in s for c in cardini_finali):
                somma_s = sum(s)
                
                # 2. Filtro Pressione (Valli)
                in_valle = any(v[0] < somma_s <= v[1] for v in valli_target) if valli_target else (150 <= somma_s <= 250)
                
                if in_valle:
                    # 3. Morsa di Parisi (Rugosità)
                    h_s = calcola_rugosita(s)
                    if abs(h_s - target_h) < morsa_millimetrica:
                        err_tot = abs(h_s - target_h) + (abs((h_s - h_136_attuale) - Delta_medio) * 10)
                        sestine_risultanti.append((s, err_tot, h_s, somma_s))
            
            if i % 1000 == 0:
                prog_bar.progress((i + 1) / total_comb)
        
        prog_bar.empty()
        
        if sestine_risultanti:
            sestine_risultanti.sort(key=lambda x: x[1])
            st.subheader(f"✨ L'Arrosto: {len(sestine_risultanti)} Sestine Nobili")
            df_final = pd.DataFrame(sestine_risultanti[:30], columns=['Sestina', 'Errore', 'Rugosità H', 'Somma Totale'])
            st.table(df_final)
        else:
            st.error("Nessuna combinazione del pool rispetta la morsa. Prova ad aumentare l'ampiezza del pool o a cambiare cardini.")

except Exception as e:
    st.error(f"Errore: {e}")
