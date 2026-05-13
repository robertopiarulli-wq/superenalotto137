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
    pool_eletto, nuclei_acc, nuclei_rit = [], [], []
    valli = []
    
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            data = json.load(f)
            # Gestione nuova struttura JSON o fallback vecchia lista
            if isinstance(data, dict):
                pool_eletto = data.get("pool_eletto", [])
                nuclei_acc = data.get("nuclei_accelerati", [])
                nuclei_rit = data.get("nuclei_ritardo", [])
            else:
                pool_eletto = data
            
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        v_df = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)']
        for f in v_df['fascia']:
            nums = f.replace('(', '').replace(']', '').split(',')
            valli.append((float(nums[0]), float(nums[1])))
            
    return pool_eletto, nuclei_acc, nuclei_rit, valli

def analizza_memoria_recente(df_estrazioni, nuclei):
    """Filtra i nuclei apparsi nelle ultime 3 estrazioni."""
    ultime_3 = df_estrazioni.head(3)
    colonne = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    vivi, raffreddamento = [], []
    
    for n in nuclei:
        uscito = False
        for _, row in ultime_3.iterrows():
            if n[0] in row[colonne].values and n[1] in row[colonne].values:
                uscito = True
                break
        if uscito: raffreddamento.append(n)
        else: vivi.append(n)
    return vivi, raffreddamento

# --- INTERFACCIA ---
st.set_page_config(page_title="Morsa Deterministica Memoria-137", layout="wide")
st.title("🔬 Morsa Scientifica: Memoria Ciclica e Nuclei Dominanti")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    pool_risonanza, nuclei_acc, nuclei_rit, valli_target = carica_dati_scientifici()
    
    # 1. Filtro Memoria (Ultime 3)
    vivi_acc, cold_acc = analizza_memoria_recente(df_full, nuclei_acc)
    vivi_rit, cold_rit = analizza_memoria_recente(df_full, nuclei_rit)

    st.sidebar.header("🎯 Suggerimenti IA (Cardini)")
    
    fisse_auto = []
    if vivi_acc:
        scelta = st.sidebar.selectbox("🔥 Nuclei Accelerati (Vivi)", 
                                      ["Manuale"] + [f"{c[0]} - {c[1]}" for c in vivi_acc])
        if scelta != "Manuale":
            fisse_auto = [int(x) for x in scelta.split(" - ")]

    if cold_acc or cold_rit:
        st.sidebar.info(f"❄️ In Raffreddamento (ultime 3): {cold_acc + cold_rit}")

    cardini_finali = st.sidebar.multiselect("Cardini Attivi", range(1, 91), default=fisse_auto)
    dim_pool = st.sidebar.slider("Ampiezza Pool Eletto", 12, 22, 18)

    # Parametri Morsa
    h_136_attuale = df_full['H'].iloc[0]
    target_h = df_full['H'].iloc[0:136].mean() * Q_medio
    morsa_millimetrica = target_h * 0.1 

    # Visualizzazione Metriche
    col1, col2, col3 = st.columns(3)
    col1.metric("Bersaglio Rugosità H", f"{target_h:.5f}")
    col2.metric("Delta Atteso", f"{Delta_medio:.5f}")
    col3.success(f"{len(valli_target)} Valli Attive") if valli_target else col3.warning("Filtro Standard 150-250")

    if st.button("🚀 GENERA ARROSTO DETERMINISTICO"):
        pool_eletto = sorted(list(set(cardini_finali + pool_risonanza[:dim_pool])))
        st.write(f"Analisi pool: `{pool_eletto}` (Fisse: {cardini_finali})")
        
        tutte_le_sestine = list(itertools.combinations(pool_eletto, 6))
        sestine_risultanti = []
        
        prog_bar = st.progress(0)
        total_comb = len(tutte_le_sestine)
        
        for i, s_tuple in enumerate(tutte_le_sestine):
            s = sorted(list(s_tuple))
            if all(c in s for c in cardini_finali):
                somma_s = sum(s)
                in_valle = any(v[0] < somma_s <= v[1] for v in valli_target) if valli_target else (150 <= somma_s <= 250)
                
                if in_valle:
                    h_s = calcola_rugosita(s)
                    if abs(h_s - target_h) < morsa_millimetrica:
                        err_tot = abs(h_s - target_h) + (abs((h_s - h_136_attuale) - Delta_medio) * 10)
                        sestine_risultanti.append((s, err_tot, h_s, somma_s))
            
            if i % 2000 == 0: prog_bar.progress((i + 1) / total_comb)
        
        prog_bar.empty()
        
        if sestine_risultanti:
            sestine_risultanti.sort(key=lambda x: x[1])
            st.subheader(f"✨ L'Arrosto: {len(sestine_risultanti)} Sestine Nobili")
            df_final = pd.DataFrame(sestine_risultanti[:30], columns=['Sestina', 'Errore', 'Rugosità H', 'Somma Totale'])
            st.table(df_final)
        else:
            st.error("Nessuna combinazione valida. Espandi il pool o cambia cardini.")

except Exception as e:
    st.error(f"Errore: {e}")
