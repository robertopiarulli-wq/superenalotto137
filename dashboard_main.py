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
    
    # Calcolo Blacklist (Ultime 3 estrazioni)
    cols = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    blacklist = set(df.head(3)[cols].values.flatten())
    
    # Calcolo Ritardi per tutto il pool (1-90)
    ritardi = {}
    for n in range(1, 91):
        for i, row in enumerate(df[cols].values):
            if n in row:
                ritardi[n] = i
                break
    
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
st.set_page_config(page_title="Morsa V15 - Automazione Totale", layout="wide")
df_full, blacklist, mappa_ritardi = analizza_dati_freschi()
scienza, valli, sature = carica_report_motori()

st.title("🚀 Morsa Scientifica V15: Automazione & Pressione")

# 1. VISUALIZZAZIONE POOL RESIDUO (I "SANI")
st.subheader("📋 Pool Eletto: Analisi Superstiti (Ordinati per Ritardo)")
pool_residuo = [n for n in scienza["pool_eletto"] if n not in blacklist]
dati_pool = [{"Numero": n, "Ritardo": mappa_ritardi.get(n, 0)} for n in pool_residuo]
df_pool = pd.DataFrame(dati_pool).sort_values("Ritardo", ascending=False)

c1, c2 = st.columns([1, 3])
with c1:
    st.dataframe(df_pool, hide_index=True)
with c2:
    st.info(f"**Veto Atomico Attivo**: Esclusi {len(blacklist)} numeri usciti recentemente. Questi {len(pool_residuo)} numeri sono i più solidi per stasera.")

# 2. AUTOMAZIONE FASCE
st.sidebar.header("⚖️ Bilanciamento Pressione")
st.sidebar.write("**Valli Attive (Target):**")
for v in valli: st.sidebar.success(f"Somma tra {v[0]} e {v[1]}")
st.sidebar.write("**Zone Sature (Scartate):**")
for s in sature: st.sidebar.error(f"Fascia {s[0]}-{s[1]}")

# 3. SELEZIONE CARDINI
vivi_acc = [n for n in scienza["nuclei_accelerati"] if not any(num in blacklist for num in n)]
scelta_acc = st.sidebar.selectbox("🔥 Nuclei Dominanti Vivi", ["Manuale"] + [f"{n[0]}-{n[1]}" for n in vivi_acc])
fisse_auto = [int(x) for x in scelta_acc.split("-")] if scelta_acc != "Manuale" else []

cardini = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=fisse_auto)

# METRICHE
res_h = df_full['H'].iloc[0:136].mean()
target_h = res_h * 0.98 # Calibrato su trend attuale
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Bersaglio Rugosità H", f"{target_h:.5f}")
m2.metric("Cluster Attivo", scienza["cluster_attivo"])
m3.metric("Numeri in Blacklist", len(blacklist))

# 4. GENERAZIONE CON FILTRI AUTOMATICI
if st.button("🚀 GENERA ARROSTO AUTOMATIZZATO"):
    pool_f = sorted(list(set(cardini + pool_residuo[:15])))
    st.write(f"Analisi su Pool Nobiltà: `{pool_f}`")
    
    sestine_nobili = []
    combs = list(itertools.combinations(pool_f, 6))
    prog = st.progress(0)
    
    for i, comb in enumerate(combs):
        s = sorted(list(comb))
        if all(f in s for f in cardini):
            somma_s = sum(s)
            # FILTRO AUTOMATICO: Deve essere in una Valle E NON in una zona Satura
            check_valle = any(v[0] < somma_s <= v[1] for v in valli)
            check_satura = any(s_z[0] < somma_s <= s_z[1] for s in sature)
            
            if check_valle and not check_satura:
                h_s = calcola_rugosita(s)
                if abs(h_s - target_h) < (target_h * 0.08):
                    err = abs(h_s - target_h)
                    sestine_nobili.append((s, err, h_s, somma_s))
        
        if i % 2000 == 0: prog.progress((i+1)/len(combs))
    prog.empty()
    
    if sestine_nobili:
        st.subheader(f"✨ L'Arrosto (Filtrato per Pressione e Rugosità): {len(sestine_nobili)}")
        st.table(pd.DataFrame(sorted(sestine_nobili, key=lambda x: x[1])[:30], 
                             columns=['Sestina', 'Errore', 'Rugosità', 'Somma']))
    else:
        st.error("Morsa troppo stretta. Cambia i cardini tra quelli con maggior ritardo.")
