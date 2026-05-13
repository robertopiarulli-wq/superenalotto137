import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import json
import os
import itertools

# --- CONFIGURAZIONE E CONNESSIONE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Errore di connessione a Supabase. Verifica i Secrets.")
    st.stop()

def calcola_rugosita(sestina):
    """Calcola l'indice di rugosità H di Parisi per una sestina."""
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_legge_universale_doppia():
    """Analizza l'andamento storico della rugosità."""
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
    """Carica i risultati della Trinità Algoritmica."""
    dati = {"pool_eletto": [], "nuclei_accelerati": [], "nuclei_ritardo": [], "cluster_attivo": None}
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            dati.update(json.load(f))
            
    valli = []
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        v_df = mappa[mappa['stato_zona'] == 'VALLE (TRANSIZIONE)']
        for f in v_df['fascia']:
            nums = f.replace('(', '').replace(']', '').split(',')
            valli.append((float(nums[0]), float(nums[1])))
    return dati, valli

def filtro_memoria_atomico(df, nuclei):
    """
    IMPLEMENTAZIONE VETO ATOMICO: 
    Esclude nuclei se ALMENO UNO dei numeri è uscito nelle ultime 3 estrazioni.
    """
    ultime_3 = df.head(3)
    cols = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    
    # Creiamo la Blacklist atomica dei numeri usciti
    numeri_usciti = set(ultime_3[cols].values.flatten())
    
    vivi, cold = [], []
    for n in nuclei:
        # Il nucleo è 'vissuto' solo se nessuno dei suoi numeri è nella Blacklist
        if any(num in numeri_usciti for num in n):
            cold.append(n)
        else:
            vivi.append(n)
    return vivi, cold

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Morsa Trinità - Veto Atomico", layout="wide")
st.title("🔬 Morsa Scientifica Integrale: Filtro Nuclei Consolidati")

try:
    df_full, Q_medio, Delta_medio = analizza_legge_universale_doppia()
    scienza, valli_target = carica_dati_scientifici()
    
    # Applicazione del NUOVO Filtro Memoria Atomico
    vivi_acc, cold_acc = filtro_memoria_atomico(df_full, scienza["nuclei_accelerati"])
    
    # SIDEBAR
    st.sidebar.header("🎯 Target Algoritmici")
    scelta_acc = st.sidebar.selectbox("🔥 Nuclei Dominanti Vivi (Consolidati)", 
                                      ["Manuale"] + [f"{n[0]}-{n[1]}" for n in vivi_acc])
    fisse_auto = [int(x) for x in scelta_acc.split("-")] if scelta_acc != "Manuale" else []
    
    if cold_acc:
        st.sidebar.warning(f"❄️ In Raffreddamento Atomico: {cold_acc}")
        
    cardini_finali = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=fisse_auto)
    ampiezza_pool = st.sidebar.slider("Numeri dal Pool Eletto", 10, 22, 18)
    
    # METRICHE PRINCIPALI
    target_h = df_full['H'].iloc[0:136].mean() * Q_medio
    morsa_val = target_h * 0.1 
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Bersaglio Rugosità H", f"{target_h:.5f}")
    c2.metric("Cluster di Forma", f"ID: {scienza['cluster_attivo']}")
    c3.metric("Delta Atteso", f"{Delta_medio:.5f}")

    # GENERAZIONE
    if st.button("🚀 GENERA ARROSTO DETERMINISTICO"):
        pool_puro = [n for n in scienza["pool_eletto"] if n not in cardini_finali]
        pool_finale = sorted(cardini_finali + pool_puro[:ampiezza_pool - len(cardini_finali)])
        
        st.write(f"Analisi Combinatoria su Pool: `{pool_finale}`")
        
        sestine_valide = []
        combs = list(itertools.combinations(pool_finale, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini_finali):
                somma_s = sum(s)
                if any(v[0] < somma_s <= v[1] for v in valli_target) if valli_target else (150 <= somma_s <= 250):
                    h_s = calcola_rugosita(s)
                    if abs(h_s - target_h) < morsa_val:
                        errore = abs(h_s - target_h) + abs((h_s - df_full['H'].iloc[0]) - Delta_medio) * 5
                        sestine_valide.append((s, errore, h_s, somma_s))
            
            if i % 2000 == 0: prog.progress((i+1)/len(combs))
        
        prog.empty()
        
        if sestine_valide:
            sestine_valide.sort(key=lambda x: x[1])
            st.subheader(f"✨ L'Arrosto: {len(sestine_valide)} Sestine Nobili")
            st.table(pd.DataFrame(sestine_valide[:30], columns=['Sestina', 'Errore', 'Rugosità', 'Somma']))
        else:
            st.error("Nessuna combinazione valida. Riduci le fisse o amplia il pool.")

except Exception as e:
    st.error(f"Errore critico: {e}")
