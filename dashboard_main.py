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

# --- NUOVA FUNZIONE DI RIDUZIONE ---
def riduttore_garantito(sestine, garanzia=4):
    """Filtra le sestine per mantenere una copertura minima (Garanzia N)."""
    ridotte = []
    lista_sestine = [list(s) for s in sestine]
    while lista_sestine:
        base = lista_sestine.pop(0)
        ridotte.append(base)
        # Eliminiamo le sestine che hanno già un'intersezione pari alla garanzia
        lista_sestine = [s for s in lista_sestine if len(set(s) & set(base)) < garanzia]
    return ridotte

# --- UI ---
st.set_page_config(page_title="Morsa V20 - Riduttore & Stampa", layout="wide")

try:
    df_full, blacklist, mappa_ritardi = analizza_dati_freschi()
    scienza, valli, sature = carica_report_motori()

    st.title("🚀 Morsa Scientifica V20: Riduzione & Report")

    # 1. ANALISI POOL
    pool_residuo = [n for n in scienza["pool_eletto"] if n not in blacklist]
    valle_target = min(valli, key=lambda x: abs(x[0] - 180)) if valli else (160, 170)

    # 2. SIDEBAR POTENZIATA
    st.sidebar.header("🎯 Parametri di Gioco")
    cardini = st.sidebar.multiselect("Cardini (Fisse)", range(1, 91), default=[17])
    ampiezza_pool = st.sidebar.slider("Potenza Pool (Slider)", 15, 45, 25)
    
    st.sidebar.subheader("📉 Ottimizzazione")
    tipo_riduzione = st.sidebar.selectbox("Tipo di Riduzione", ["Nessuna", "Garanzia 4", "Garanzia 5"])

    # 3. METRICHE
    target_h = df_full['H'].iloc[0:136].mean() * 0.98
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Bersaglio Rugosità H", f"{target_h:.5f}")
    m2.metric("Cluster Attivo", scienza["cluster_attivo"])
    m3.metric("Filtro Valle", f"{valle_target[0]}-{valle_target[1]}")

    # 4. GENERAZIONE E RIDUZIONE
    if st.button("🚀 GENERA ARROSTO E APPLICA FILTRI"):
        somma_fisse = sum(cardini)
        n_mancanti = 6 - len(cardini)
        media_target = (sum(valle_target)/2 - somma_fisse) / n_mancanti if n_mancanti > 0 else 0
        
        # Costruzione Pool Ibrido (Priorità Pool Eletto + Bilanciamento Popolo)
        pool_nobili = [n for n in pool_residuo if n not in cardini]
        tutti_i_numeri = [n for n in range(1, 91) if n not in blacklist and n not in cardini]
        popolo_bilanciato = sorted(tutti_i_numeri, key=lambda x: abs(x - media_target))
        pool_f = sorted(list(set(cardini + pool_nobili[:12] + popolo_bilanciato[:ampiezza_pool - 12])))
        
        sestine_nobili = []
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                if (valle_target[0]-5 < somma_s <= valle_target[1]+5) and not any(sf[0]<somma_s<=sf[1] for sf in sature):
                    h_s = calcola_rugosita(s)
                    if abs(h_s - target_h) < (target_h * 0.15):
                        sestine_nobili.append(s)
            
            if i > 1200000: break # Limite sicurezza
            if i % 20000 == 0: prog.progress(min((i+1)/1200000, 1.0))
        prog.empty()

        # APPLICAZIONE RIDUZIONE
        risultato_finale = sestine_nobili
        if tipo_riduzione != "Nessuna":
            g_val = 5 if tipo_riduzione == "Garanzia 5" else 4
            risultato_finale = riduttore_garantito(sestine_nobili, g_val)

        # 5. REPORT E STAMPA
        st.subheader("📄 Report di Selezione Strategica")
        c_rep1, c_rep2 = st.columns(2)
        with c_rep1:
            st.markdown(f"""
            **Parametri Tecnici:**
            * **Cardini Utilizzati**: {cardini}
            * **Media Numeri Mancanti**: {int(media_target)} (Sotto 45)
            * **Riduzione Applicata**: {tipo_riduzione}
            * **Target Rugosità H**: {target_h:.5f}
            """)
        with c_rep2:
            st.info(f"Sestine Totali Prodotte: {len(sestine_nobili)}\n\nSestine Ottimizzate: {len(risultato_finale)}")

        if risultato_finale:
            df_final = pd.DataFrame(risultato_finale, columns=['N1','N2','N3','N4','N5','N6'])
            st.table(df_final.head(40))
            
            # Esportazione per stampa
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Scarica Arrosto per Stampa (CSV)", csv, "morsa_v20_report.csv", "text/csv")
        else:
            st.error("Nessun incastro trovato. Prova ad allargare lo slider o a ridurre i cardini.")

except Exception as e:
    st.error(f"Errore: {e}")
