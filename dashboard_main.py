import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import json
import os
import itertools

# --- CONNESSIONE E LOGICA BASE ---
try:
    URL = st.secrets["URL_SUPABASE"]
    KEY = st.secrets["KEY_SUPABASE"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Errore di connessione a Supabase.")
    st.stop()

def calcola_rugosita(sestina):
    s_ord = np.sort(sestina)
    diffs = np.diff(s_ord)
    mu = np.mean(diffs)
    return np.std(diffs) / mu if mu != 0 else 0

@st.cache_data(ttl=3600) 
def analizza_dati_freschi():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    df = pd.DataFrame(res.data)
    df['H'] = df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    cols = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    blacklist = set(df.head(3)[cols].values.flatten())
    
    ritardi = {}
    for n in range(1, 91):
        found = False
        for i, row in enumerate(df[cols].values):
            if n in row:
                ritardi[n] = i
                found = True
                break
        if not found: ritardi[n] = len(df)
    
    return df, blacklist, ritardi

def carica_report_motori():
    scienza = {"pool_eletto": [], "nuclei_accelerati": [], "cluster_attivo": None}
    if os.path.exists("cardini_scientifici.json"):
        with open("cardini_scientifici.json", "r") as f:
            scienza.update(json.load(f))
    
    valli, sature = [], []
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        for _, row in mappa.iterrows():
            nums = row['fascia'].replace('(', '').replace(']', '').split(',')
            f_range = (float(nums[0]), float(nums[1]))
            if row['stato_zona'] == 'VALLE (TRANSIZIONE)': valli.append(f_range)
            elif row['stato_zona'] == 'SATURA': sature.append(f_range)
            
    return scienza, valli, sature

# --- UI ---
st.set_page_config(page_title="Morsa V18 - Sblocca Morsa", layout="wide")

try:
    df_full, blacklist, mappa_ritardi = analizza_dati_freschi()
    scienza, valli, sature = carica_report_motori()

    st.title("🚀 Morsa Scientifica V18: Bilanciamento Forzato")

    # 1. ANALISI POOL
    pool_residuo = [n for n in scienza["pool_eletto"] if n not in blacklist]
    
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        st.subheader("📋 Superstiti Pool")
        dati_pool = [{"Numero": n, "Ritardo": mappa_ritardi.get(n, 0)} for n in pool_residuo]
        st.dataframe(pd.DataFrame(dati_pool).sort_values("Ritardo", ascending=False), hide_index=True)
    
    with col_p2:
        if valli:
            valle_target = min(valli, key=lambda x: abs(x[0] - 180))
            st.success(f"🎯 **Bersaglio Somma**: {valle_target[0]} - {valle_target[1]}")
        else:
            valle_target = (150, 250)
            st.warning("Target standard: 150-250")

    # 2. SIDEBAR
    st.sidebar.header("🎯 Selezione Guidata")
    vivi_acc = [n for n in scienza["nuclei_accelerati"] if not any(num in blacklist for num in n)]
    scelta_acc = st.sidebar.selectbox("🔥 Nuclei Dominanti", ["Manuale"] + [f"{n[0]}-{n[1]}" for n in vivi_acc])
    fisse_auto = [int(x) for x in scelta_acc.split("-")] if scelta_acc != "Manuale" else []

    cardini = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=fisse_auto)
    ampiezza_pool = st.sidebar.slider("Potenza di Calcolo (Pool)", 12, 35, 22)

    # 3. METRICHE
    target_h = df_full['H'].iloc[0:136].mean() * 0.98
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Rugosità H", f"{target_h:.5f}")
    m2.metric("Cluster", scienza["cluster_attivo"])
    m3.metric("Blacklist", f"{len(blacklist)} num")

    # 4. GENERAZIONE SBLOCCA-MORSA
    if st.button("🚀 GENERA ARROSTO DETERMINISTICO"):
        somma_fisse = sum(cardini)
        n_mancanti = 6 - len(cardini)
        
        if n_mancanti > 0:
            centro_valle = (valle_target[0] + valle_target[1]) / 2
            media_target = (centro_valle - somma_fisse) / n_mancanti
            
            # --- LOGICA V18: SELEZIONE FORZATA DEI PESI ---
            # Prendiamo i numeri dal pool residuo più vicini alla media necessaria
            pool_bilanciato = sorted(pool_residuo, key=lambda x: abs(x - media_target))
            # Integriamo con i più piccoli assoluti del pool se la media è bassa
            if media_target < 30:
                extra_small = sorted(pool_residuo)[:10]
                pool_f = sorted(list(set(cardini + pool_bilanciato[:ampiezza_pool] + extra_small)))
            else:
                pool_f = sorted(list(set(cardini + pool_bilanciato[:ampiezza_pool])))
            
            st.info(f"🛠️ Bilanciamento: Media necessaria {int(media_target)}. Pool esteso a {len(pool_f)} numeri.")
        else:
            pool_f = sorted(cardini)

        sestine_nobili = []
        # Calcolo combinatorio
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                # Tolleranza sulla valle di 5 punti per sbloccare l'incastro
                if (valle_target[0]-5 < somma_s <= valle_target[1]+5):
                    if not any(s_f[0] < somma_s <= s_f[1] for s_f in sature):
                        h_s = calcola_rugosita(s)
                        # Tolleranza H elastica al 12%
                        if abs(h_s - target_h) < (target_h * 0.12):
                            err = abs(h_s - target_h)
                            sestine_nobili.append((s, err, h_s, somma_s))
            
            if i % 10000 == 0: prog.progress((i+1)/len(combs))
        prog.empty()
        
        if sestine_nobili:
            st.subheader(f"✨ L'Arrosto: {len(sestine_nobili)} Sestine Trovate")
            st.table(pd.DataFrame(sorted(sestine_nobili, key=lambda x: x[1])[:30], 
                                 columns=['Sestina', 'Errore', 'Rugosità', 'Somma']))
        else:
            st.error("Incastro ancora assente. Suggerimento: usa solo 1 cardine o aumenta la slider a 35.")

except Exception as e:
    st.error(f"Errore: {e}")
