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
            
    valli, sature, antidoto_attivo = [], [], None
    if os.path.exists("mappa_valli_pressione.csv"):
        mappa = pd.read_csv("mappa_valli_pressione.csv")
        for _, row in mappa.iterrows():
            nums = row['fascia'].replace('(', '').replace(']', '').split(',')
            f_range = (float(nums[0]), float(nums[1]))
            if row['stato_zona'] == 'VALLE (TRANSIZIONE)': 
                valli.append(f_range)
            elif row['stato_zona'] == 'SATURA': 
                sature.append(f_range)
                if row.get('antidoto_suggerito') == 'BILANCIARE_CON_ALTI':
                    antidoto_attivo = 'BILANCIARE_CON_ALTI'
            
    return scienza, valli, sature, antidoto_attivo

# --- MODULO RADAR ANOMALIE V22 (NUOVI FILTRI GEOMETRICI) ---
def motore_radar_anomalie(df):
    blocchi_A = list(range(1, 16)) + list(range(31, 46)) + list(range(61, 76))
    blocchi_B = list(range(16, 31)) + list(range(46, 61)) + list(range(76, 91))
    blocchi_C = list(range(1, 16)) + list(range(46, 76))
    blocchi_D = list(range(16, 46)) + list(range(76, 91))

    profili = {
        "Fascia Under 45": lambda s: all(n <= 45 for n in s),
        "Fascia Over 45": lambda s: all(n >= 46 for n in s),
        "Total Even (6 Pari)": lambda s: all(n % 2 == 0 for n in s),
        "Total Odd (6 Dispari)": lambda s: all(n % 2 != 0 for n in s),
        "Fascia Media (20-70)": lambda s: all(20 <= n <= 70 for n in s),
        "Fascia Alternata A": lambda s: all(n in blocchi_A for n in s),
        "Fascia Alternata B": lambda s: all(n in blocchi_B for n in s),
        "Fascia Alternata C": lambda s: all(n in blocchi_C for n in s),
        "Fascia Alternata D": lambda s: all(n in blocchi_D for n in s),
    }
    
    radar_results = []
    for nome, test in profili.items():
        serie = df.apply(lambda r: 1 if test([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]) else 0, axis=1)
        uscite_totali = int(serie.sum())
        freq_storica = serie.mean()
        ritardo = 0
        for val in serie:
            if val == 1: break
            ritardo += 1
        
        attesa = 1/freq_storica if freq_storica > 0 else 500
        tensione = ritardo / attesa
        
        radar_results.append({
            "Profilo Geometrico": nome,
            "Ritardo Attuale": ritardo,
            "Frequenza Storica (Uscite)": uscite_totali,
            "Tensione Elastica": round(tensione, 2),
            "Stato Alert": "🔥 CRITICO" if tensione > 2.0 else "🟡 ALTO" if tensione > 1.3 else "✅ BILANCIATO"
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
st.set_page_config(page_title="Morsa V22 - Target Sincro", layout="wide")

try:
    df_full, blacklist, mappa_ritardi = analizza_dati_freschi()
    scienza, valli, sature, antidoto_attivo = carica_report_motori()

    st.title("🚀 Morsa Scientifica V22: Sincronizzazione Totale & Incastri Geometrici")

    # 1. RADAR ANOMALIE & MONITORAGGIO FREQUENZE
    st.subheader("📡 Radar Casi Rari, Frequenze e Tensione Elastica")
    df_radar = motore_radar_anomalie(df_full)
    
    col_radar, col_valle = st.columns([2, 1])
    with col_radar:
        st.dataframe(df_radar, hide_index=True)
    with col_valle:
        # LOGICA DI SINCRONIZZAZIONE REALE CON L'ANTIDOTO DEL MOTORE DI PRESSIONE
        if valli and not antidoto_attivo:
            valle_target = min(valli, key=lambda x: abs(x[0] - 180))
            st.success(f"🎯 **Wyckoff Valle Attiva**: {valle_target[0]} - {valle_target[1]}")
        else:
            st.warning("⚠️ Valli Medie SATURE rilevate dal Motore 1. Attivazione Antidoto: BILANCIARE CON ALTI.")
            valle_target = (220, 245)
            st.info(f"🎯 **Nuovo Target Sincronizzato Fuori Saturazione**: {valle_target[0]} - {valle_target[1]}")

    # 2. SINCRONIZZAZIONE POOL NOBILTÀ & INTEGRAZIONE NUCLEI ACCELERATI
    st.divider()
    st.subheader("🗂️ Gestione Pool Superstiti & Nuclei di Risonanza")
    
    if scienza["nuclei_accelerati"]:
        st.write("🔥 **Nuclei Accelerati Attivi (Risonanza)**:")
        st.code(f"{scienza['nuclei_accelerati']}")
        
    pool_residuo = [n for n in scienza["pool_eletto"] if n not in blacklist]
    
    filtro_sincro = st.selectbox("🎯 Filtra ed Isola il Pool Eletto per Fascia Geometrica:", 
                                ["Nessuno", "Solo Under 45", "Solo Over 45", "Solo Pari", "Solo Dispari", 
                                 "Solo Media (20-70)", "Solo Alternata A", "Solo Alternata B", "Solo Alternata C", "Solo Alternata D"])
    
    b_A = list(range(1, 16)) + list(range(31, 46)) + list(range(61, 76))
    b_B = list(range(16, 31)) + list(range(46, 61)) + list(range(76, 91))
    b_C = list(range(1, 16)) + list(range(46, 76))
    b_D = list(range(16, 46)) + list(range(76, 91))

    if filtro_sincro == "Solo Under 45": pool_sincro = [n for n in pool_residuo if n <= 45]
    elif filtro_sincro == "Solo Over 45": pool_sincro = [n for n in pool_residuo if n >= 46]
    elif filtro_sincro == "Solo Pari": pool_sincro = [n for n in pool_residuo if n % 2 == 0]
    elif filtro_sincro == "Solo Dispari": pool_sincro = [n for n in pool_residuo if n % 2 != 0]
    elif filtro_sincro == "Solo Media (20-70)": pool_sincro = [n for n in pool_residuo if 20 <= n <= 70]
    elif filtro_sincro == "Solo Alternata A": pool_sincro = [n for n in pool_residuo if n in b_A]
    elif filtro_sincro == "Solo Alternata B": pool_sincro = [n for n in pool_residuo if n in b_B]
    elif filtro_sincro == "Solo Alternata C": pool_sincro = [n for n in pool_residuo if n in b_C]
    elif filtro_sincro == "Solo Alternata D": pool_sincro = [n for n in pool_residuo if n in b_D]
    else: pool_sincro = pool_residuo

    c1, c2 = st.columns(2)
    with c1:
        st.write("**Pool Superstiti Sincronizzati (Usa come fisse/cardini):**")
        st.code(f"{pool_sincro}")
    with c2:
        st.write("**Pool Nobiltà Fuori Target Temporaneo:**")
        st.code(f"{[n for n in pool_residuo if n not in pool_sincro]}")

    # 3. SIDEBAR PARAMETRI CON INTEGRAZIONE COODINATA DEI NUCLEI
    st.sidebar.header("🎯 Parametri di Gioco")
    
    opzioni_nuclei = ["Manuale"]
    if scienza["nuclei_accelerati"]:
        opzioni_nuclei += [f"{n[0]}-{n[1]}" for n in scienza["nuclei_accelerati"] if not any(num in blacklist for num in n)]
        
    scelta_acc = st.sidebar.selectbox("🔥 Carica Coppia Nucleo Accelerato:", opzioni_nuclei)
    fisse_auto = [int(x) for x in scelta_acc.split("-")] if scelta_acc != "Manuale" else []

    cardini = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=fisse_auto if fisse_auto else (pool_sincro[:2] if pool_sincro else []))
    ampiezza_pool = st.sidebar.slider("Potenza di Espansione Popolo (Slider)", 15, 45, 25)
    tipo_riduzione = st.sidebar.selectbox("Filtro Riduttore Ottimizzato", ["Nessuna", "Garanzia 4", "Garanzia 5"])

    # Metriche generali
    target_h = df_full['H'].iloc[0:136].mean() * 0.98
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Bersaglio Rugosità H (Parisi)", f"{target_h:.5f}")
    m2.metric("Cluster Attivo", scienza.get("cluster_attivo", "Non rilevato"))
    m3.metric("Filtro Blacklist (Memoria 3)", f"{len(blacklist)} num")

    # PRE-CALCOLO PREVENTIVO DEI CANDIDATI SUPERSTITI
    somma_fisse = sum(cardini)
    n_mancanti = 6 - len(cardini)
    media_target = (sum(valle_target)/2 - somma_fisse) / n_mancanti if n_mancanti > 0 else 0
    
    tutti_i_numeri = [n for n in range(1, 91) if n not in blacklist and n not in cardini]
    
    # Applica i vincoli geometrici scelti anche al popolo di compensazione
    if "Under 45" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n <= 45]
    elif "Over 45" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n >= 46]
    elif "Media" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if 20 <= n <= 70]
    elif "Alternata A" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n in b_A]
    elif "Alternata B" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n in b_B]
    elif "Alternata C" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n in b_C]
    elif "Alternata D" in filtro_sincro: tutti_i_numeri = [n for n in tutti_i_numeri if n in b_D]
    
    popolo = sorted(tutti_i_numeri, key=lambda x: abs(x - media_target))
    pool_f = sorted(list(set(cardini + pool_sincro + popolo[:ampiezza_pool - len(pool_sincro)])))

    # 4. EVIDENZIAZIONE DEI CANDIDATI SUPERSTITI REALI
    st.subheader("🕵️ Analisi Preventiva dei Candidati Superstiti")
    st.info(f"Prima della generazione, la morsa ha selezionato un set ristretto di **{len(pool_f)} numeri candidati** compatibili con i criteri attuali.")
    st.code(f"Numeri pronti al calcolo combinatorio: {pool_f}")

    # 5. MOTOR COMBINATORIO E GENERAZIONE
    if st.button("🚀 GENERA ARROSTO SINCRONIZZATO V22"):
        sestine_nobili = []
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                if (valle_target[0]-5 < somma_s <= valle_target[1]+5) and not any(sf[0]<somma_s<=sf[1] for sf in sature if sf != valle_target):
                    if abs(calcola_rugosita(s) - target_h) < (target_h * 0.15):
                        sestine_nobili.append(s)
            if i > 1500000: break
            if i % 25000 == 0: prog.progress(min((i+1)/len(combs) if len(combs)>0 else 1, 1.0))
        prog.empty()

        risultato = riduttore_garantito(sestine_nobili, 5 if "5" in tipo_riduzione else 4) if tipo_riduzione != "Nessuna" else sestine_nobili

        st.subheader("📄 Report Strategico di Selezione (V22)")
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown(f"""
            **Configurazione Algoritmica:**
            * **Filtro Sincro Geometrico**: {filtro_sincro}
            * **Cardini Bloccati (Fisse)**: {cardini}
            * **Somma di Riferimento Wyckoff**: {valle_target[0]}-{valle_target[1]}
            * **Media Richiesta per Incastro**: {int(media_target)}
            """)
        with cr2:
            st.metric("Sestine Totali Generate", len(sestine_nobili))
            st.metric("Sestine Superstiti Ottimizzate", len(risultato))

        if risultato:
            df_res = pd.DataFrame(risultato, columns=['N1','N2','N3','N4','N5','N6'])
            st.table(df_res.head(40))
            st.download_button("💾 Esporta per Stampa (CSV)", df_res.to_csv(index=False).encode('utf-8'), "morsa_v22_sincro.csv", "text/csv")
        else:
            st.error("Nessun incastro trovato. Modifica l'ampiezza dello slider o cambia fisse per ricentrare la media target.")

except Exception as e:
    st.error(f"Errore generale: {e}")
