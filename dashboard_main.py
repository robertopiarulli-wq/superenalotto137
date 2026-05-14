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

# --- MODULO RADAR ANOMALIE V21 ---
def motore_radar_anomalie(df):
    profili = {
        "Fascia Under 45": lambda s: all(n <= 45 for n in s),
        "Fascia Over 45": lambda s: all(n >= 46 for n in s),
        "Total Even (6 Pari)": lambda s: all(n % 2 == 0 for n in s),
        "Total Odd (6 Dispari)": lambda s: all(n % 2 != 0 for n in s),
        "Small (1-30)": lambda s: all(n <= 30 for n in s),
        "High (61-90)": lambda s: all(n >= 61 for n in s),
        "Zona Fredda (Somma <110)": lambda s: sum(s) < 110,
        "Zona Bollente (Somma >210)": lambda s: sum(s) > 210,
    }
    
    radar_results = []
    for nome, test in profili.items():
        serie = df.apply(lambda r: 1 if test([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]) else 0, axis=1)
        freq_storica = serie.mean()
        ritardo = 0
        for val in serie:
            if val == 1: break
            ritardo += 1
        
        # Tensione elastica (Z-Score semplificato)
        attesa = 1/freq_storica if freq_storica > 0 else 500
        tensione = ritardo / attesa
        
        radar_results.append({
            "Profilo": nome,
            "Ritardo": ritardo,
            "Tensione": round(tensione, 2),
            "Alert": "🔥 CRITICO" if tensione > 2.0 else "🟡 ALTO" if tensione > 1.3 else "✅ OK"
        })
    return pd.DataFrame(radar_results)

def riduttore_garantito(sestine, garanzia=4):
    ridotte = []
    lista_sestine = [list(s) for s in sestine]
    while lista_sestine:
        base = lista_sestine.pop(0)
        ridotte.append(base)
        lista_sestine = [s for s in lista_sestine if len(set(s) & set(base)) < garanzia]
    return ridotte

# --- UI ---
st.set_page_config(page_title="Morsa V21 - Radar & Sincro", layout="wide")

try:
    df_full, blacklist, mappa_ritardi = analizza_dati_freschi()
    scienza, valli, sature = carica_report_motori()

    st.title("🚀 Morsa Scientifica V21: Radar Sincronizzato")

    # 1. RADAR ANOMALIE
    st.subheader("📡 Radar Casi Rari & Tensione Elastica")
    df_radar = motore_radar_anomalie(df_full)
    
    col_radar, col_valle = st.columns([2, 1])
    with col_radar:
        st.table(df_radar)
    with col_valle:
        valle_target = min(valli, key=lambda x: abs(x[0] - 180)) if valli else (160, 170)
        st.success(f"🎯 **Wyckoff Target**: {valle_target[0]} - {valle_target[1]}")
        st.info("Incrocia l'alert del Radar con la Valle Target per scegliere i Cardini.")

    # 2. SINCRONIZZAZIONE POOL NOBILTÀ
    st.divider()
    st.subheader("🗂️ Gestione Pool Superstiti (Nobiltà)")
    pool_residuo = [n for n in scienza["pool_eletto"] if n not in blacklist]
    
    filtro_sincro = st.selectbox("🎯 Sincronizza Pool Eletto con Anomalia:", 
                                ["Nessuno", "Solo Under 45", "Solo Over 45", "Solo Pari", "Solo Dispari", "Solo Small (1-30)", "Solo High (61-90)"])
    
    # Isola i superstiti in base alla scelta
    if filtro_sincro == "Solo Under 45": pool_sincro = [n for n in pool_residuo if n <= 45]
    elif filtro_sincro == "Solo Over 45": pool_sincro = [n for n in pool_residuo if n >= 46]
    elif filtro_sincro == "Solo Pari": pool_sincro = [n for n in pool_residuo if n % 2 == 0]
    elif filtro_sincro == "Solo Dispari": pool_sincro = [n for n in pool_residuo if n % 2 != 0]
    elif filtro_sincro == "Solo Small (1-30)": pool_sincro = [n for n in pool_residuo if n <= 30]
    elif filtro_sincro == "Solo High (61-90)": pool_sincro = [n for n in pool_residuo if n >= 61]
    else: pool_sincro = pool_residuo

    c1, c2 = st.columns(2)
    with c1:
        st.write("**Pool Nobiltà Sincronizzato (Cardini Ideali):**")
        st.code(f"{pool_sincro}")
    with c2:
        st.write("**Pool Nobiltà Escluso (Fuori Target):**")
        st.code(f"{[n for n in pool_residuo if n not in pool_sincro]}")

    # 3. SIDEBAR E PARAMETRI
    st.sidebar.header("🎯 Selezione")
    cardini = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=pool_sincro[:2] if pool_sincro else [])
    ampiezza_pool = st.sidebar.slider("Potenza Pool (Slider)", 15, 45, 25)
    tipo_riduzione = st.sidebar.selectbox("Riduzione Garanzia", ["Nessuna", "Garanzia 4", "Garanzia 5"])

    # 4. GENERAZIONE
    target_h = df_full['H'].iloc[0:136].mean() * 0.98
    
    if st.button("🚀 GENERA ARROSTO SINCRONIZZATO"):
        somma_fisse = sum(cardini)
        n_mancanti = 6 - len(cardini)
        media_target = (sum(valle_target)/2 - somma_fisse) / n_mancanti if n_mancanti > 0 else 0
        
        # Filtro Popolo coerente con la sincronizzazione
        tutti_i_numeri = [n for n in range(1, 91) if n not in blacklist and n not in cardini]
        if "Under 45" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n <= 45]
        elif "Over 45" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n >= 46]
        
        popolo = sorted(tutti_i_numeri, key=lambda x: abs(x - media_target))
        pool_f = sorted(list(set(cardini + pool_sincro + popolo[:ampiezza_pool - len(pool_sincro)])))
        
        sestine_nobili = []
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                if (valle_target[0]-5 < somma_s <= valle_target[1]+5) and not any(sf[0]<somma_s<=sf[1] for sf in sature):
                    if abs(calcola_rugosita(s) - target_h) < (target_h * 0.15):
                        sestine_nobili.append(s)
            if i > 1200000: break
            if i % 20000 == 0: prog.progress(min((i+1)/1200000, 1.0))
        prog.empty()

        # Riduzione e Report
        risultato = riduttore_garantito(sestine_nobili, 5 if "5" in tipo_riduzione else 4) if tipo_riduzione != "Nessuna" else sestine_nobili

        st.subheader("📄 Report Strategico V21")
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown(f"**Criteri**: {filtro_sincro} | **Cardini**: {cardini} | **Target H**: {target_h:.4f}")
        with cr2:
            st.info(f"Sestine: {len(sestine_nobili)} integrali -> {len(risultato)} ottimizzate")

        if risultato:
            df_res = pd.DataFrame(risultato, columns=['N1','N2','N3','N4','N5','N6'])
            st.table(df_res.head(40))
            st.download_button("💾 Stampa Report (CSV)", df_res.to_csv(index=False).encode('utf-8'), "morsa_v21.csv", "text/csv")

except Exception as e:
    st.error(f"Errore: {e}")
