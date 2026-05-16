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
    
    # ----------------------------------------------------------------------
    # MOTORE DI SCREMATURA INIZIALE V23 (137 ESTRAZIONI)
    # ----------------------------------------------------------------------
    blacklist_filtro1 = set(df.iloc[0][cols].values.flatten())
    df_137 = df.head(137)
    tutti_i_numeri_137 = df_137[cols].values.flatten()
    
    # FILTRO 2: 14 numeri MENO FREQUENTI nelle ultime 137
    conteggio_frequenze = pd.Series(tutti_i_numeri_137).value_counts()
    for n in range(1, 91):
        if n not in conteggio_frequenze: 
            conteggio_frequenze[n] = 0
    meno_frequenti = set(conteggio_frequenze.nsmallest(14).index)
    
    # FILTRO 3: 14 numeri PIÙ RITARDATARI nelle ultime 137
    ritardi_137 = {}
    for n in range(1, 91):
        found = False
        for i, row in enumerate(df_137[cols].values):
            if n in row:
                ritardi_137[n] = i
                found = True
                break
        if not found: 
            ritardi_137[n] = 137
    piu_ritardatari = set(pd.Series(ritardi_137).nlargest(14).index)
    
    blacklist = blacklist_filtro1.union(meno_frequenti).union(piu_ritardatari)
    
    return df, blacklist, ritardi_137, blacklist_filtro1, meno_frequenti, piu_ritardatari

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
                if str(row.get('antidoto_suggerito')) == 'BILANCIARE_CON_ALTI':
                    antidoto_attivo = 'BILANCIARE_CON_ALTI'
            
    return scienza, valli, sature, antidoto_attivo

# Funzione statistica interna per calcolare ritardi e frequenze correnti delle macro-fasce nelle ultime 137 estrazioni
def calcola_statistiche_macro_fasce(df_137):
    risultati = {"BANCO": {"freq": 0, "rit": 0}, "CUORE": {"freq": 0, "rit": 0}, "TETTO": {"freq": 0, "rit": 0}}
    
    # Calcolo frequenze totali nel blocco
    for _, row in df_137.iterrows():
        somma = row.n1 + row.n2 + row.n3 + row.n4 + row.n5 + row.n6
        if 115 <= somma <= 170: risultati["BANCO"]["freq"] += 1
        elif 170 < somma <= 215: risultati["CUORE"]["freq"] += 1
        elif 215 < somma <= 270: risultati["TETTO"]["freq"] += 1
        
    # Calcolo ritardi attuali
    for chiave, limiti in [("BANCO", (115, 170)), ("CUORE", (170, 215)), ("TETTO", (215, 270))]:
        rit = 0
        for _, row in df_137.iterrows():
            somma = row.n1 + row.n2 + row.n3 + row.n4 + row.n5 + row.n6
            if limiti[0] <= somma <= limiti[1] if chiave == "BANCO" else limiti[0] < somma <= limiti[1]:
                break
            rit += 1
        risultati[chiave]["rit"] = rit
        
    return risultati

# --- MODULO RADAR ANOMALIE V23 ---
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
st.set_page_config(page_title="Morsa V23.1 - Monitor Antidoto", layout="wide")

try:
    df_full, blacklist, mappa_ritardi, f1_last, f2_freq, f3_rit = analizza_dati_freschi()
    scienza, valli, sature, antidoto_attivo = carica_report_motori()
    stats_macro = calcola_statistiche_macro_fasce(df_full.head(137))

    st.title("🚀 Morsa Scientifica V23.1: Macro-Fasce Wyckoff & Riduzione Pre-Combinatoria")

    # SPECCHIETTO DETTAGLIATO DEI FILTRI IN TOP PAGE
    with st.expander("🔍 Dettaglio Scrematura Quantitativa V23 (Attiva sulle ultime 137 estrazioni)"):
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            st.error(f"Filtro 1: Ultima Estrazione ({len(f1_last)} num)")
            st.code(f"{sorted(list(f1_last))}")
        with c_f2:
            st.warning(f"Filtro 2: 14 Meno Frequenti ({len(f2_freq)} num)")
            st.code(f"{sorted(list(f2_freq))}")
        with c_f3:
            st.info(f"Filtro 3: 14 Più Ritardatari ({len(f3_rit)} num)")
            st.code(f"{sorted(list(f3_rit))}")
        st.success(f"Massa Critica Blacklist Totale (incluse sovrapposizioni): {len(blacklist)} numeri eliminati alla partenza.")

    # RIPRISTINO INDICATORE AUTOMATICO DELL'ANTIDOTO IN CASO DI SATURAZIONE DELLE VALLI MEDIE
    if antidoto_attivo == 'BILANCIARE_CON_ALTI':
        st.error("🚨 ALERT PRESSIONE SATURE: Il Motore 1 consiglia l'Antidoto attivo -> BILANCIARE_CON_ALTI. Si consiglia di forzare il gioco sulla fascia TETTO.")
    else:
        st.info("ℹ️ Stato Pressione: Nessun Antidoto forzato rilevato nel report valli di pressione.")

    # 1. RADAR ANOMALIE & MONITORAGGIO MACRO-FASCE WYCKOFF
    st.subheader("📡 Radar Casi Rari & Selettore Macro-Fasce Wyckoff")
    df_radar = motore_radar_anomalie(df_full)
    
    col_radar, col_valle = st.columns([2, 1])
    with col_radar:
        st.dataframe(df_radar, hide_index=True)
    with col_valle:
        # INSERIMENTO TABELLA LIVE CON VALORI DI RITARDO E FREQUENZA DELLE 3 FASCE SULLE ULTIME 137 ESTRAZIONI
        st.write("**📊 Metriche Live delle Macro-Fasce (Ultime 137 estrazioni):**")
        df_stats_print = pd.DataFrame([
            {"Macro-Fascia": "BANCO [115, 170]", "Frequenza (Uscite)": stats_macro["BANCO"]["freq"], "Ritardo Attuale": stats_macro["BANCO"]["rit"]},
            {"Macro-Fascia": "CUORE (170, 215]", "Frequenza (Uscite)": stats_macro["CUORE"]["freq"], "Ritardo Attuale": stats_macro["CUORE"]["rit"]},
            {"Macro-Fascia": "TETTO (215, 270]", "Frequenza (Uscite)": stats_macro["TETTO"]["freq"], "Ritardo Attuale": stats_macro["TETTO"]["rit"]},
        ])
        st.dataframe(df_stats_print, hide_index=True)

        st.write("**🎯 Seleziona la Macro-Fascia di Target del calcolo:**")
        scelta_macro = st.radio(
            "Target Wyckoff Compresso:",
            ["BANCO (Somme Basse / Compressione): [115, 170]", 
             "CUORE (Somme Medie / Equilibrio): (170, 215]", 
             "TETTO (Somme Alte / Espansione & Antidoto): (215, 270]"]
        )
        
        if "BANCO" in scelta_macro:
            valle_target = (115, 170)
        elif "CUORE" in scelta_macro:
            valle_target = (170, 215)
        else:
            valle_target = (215, 270)
            
        st.success(f"🎯 **Target Sincronizzato Attivo**: {valle_target[0]} - {valle_target[1]}")

    # 2. SINCRONIZZAZIONE POOL NOBILTÀ & INTEGRAZIONE NUCLEI ACCELERATI
    st.divider()
    st.subheader("🗂 Honor Roll: Pool Superstiti & Nuclei di Risonanza")
    
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

    # 3. SIDEBAR PARAMETRI CON INTEGRAZIONE COORDINATA DEI NUCLEI
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
    m3.metric("Filtro Totale Blacklist (V23)", f"{len(blacklist)} num")

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
    st.info(f"Prima della generazione, la morsa ha selezionato un set ristretto di **{len(pool_f)} numeri candidati** compatibili con i criteri attuali e depurati dai 3 nuovi filtri.")
    st.code(f"Numeri pronti al calcolo combinatorio: {pool_f}")

    # 5. MOTORE COMBINATORIO E GENERAZIONE V23
    if st.button("🚀 GENERA ARROSTO SINCRONIZZATO V23"):
        sestine_nobili = []
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                
                # Controllo Target di Somma Sincronizzato sulla Macro-Fascia Scelta
                if (valle_target[0] <= somma_s <= valle_target[1]):
                    
                    # Esclusione delle sole valli sature inferiori a 220 per non bloccare l'azione sul Tetto
                    check_saturazione = any(sf[0] < somma_s <= sf[1] for sf in sature if sf[0] < 220)
                    
                    if not check_saturazione:
                        # Controllo Rugosità H
                        if abs(calcola_rugosita(s) - target_h) < (target_h * 0.15):
                            sestine_nobili.append(s)
                            
            if i > 1500000: break
            if i % 25000 == 0: prog.progress(min((i+1)/len(combs) if len(combs)>0 else 1, 1.0))
        prog.empty()

        risultato = riduttore_garantito(sestine_nobili, 5 if "5" in tipo_riduzione else 4) if tipo_riduzione != "Nessuna" else sestine_nobili

        st.subheader("📄 Report Strategico di Selezione (V23)")
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown(f"""
            **Configurazione Algoritmica V23:**
            * **Filtro Sincro Geometrico**: {filtro_sincro}
            * **Cardini Bloccati (Fisse)**: {cardini}
            * **Macro-Fascia Selezionata**: {scelta_macro.split(':')[0]}
            * **Intervallo di Somma Effettivo**: {valle_target[0]}-{valle_target[1]}
            * **Media Richiesta per Incastro**: {int(media_target)}
            """)
        with cr2:
            st.metric("Sestine Totali Generate", len(sestine_nobili))
            st.metric("Sestine Superstiti Ottimizzate", len(risultato))

        if risultato:
            df_res = pd.DataFrame(risultato, columns=['N1','N2','N3','N4','N5','N6'])
            st.table(df_res.head(40))
            st.download_button("💾 Esporta per Stampa (CSV)", df_res.to_csv(index=False).encode('utf-8'), "morsa_v23_sincro.csv", "text/csv")
        else:
            st.error("Nessun incastro trovato. Modifica l'ampiezza dello slider o cambia fisse per ricentrare la media target della macro-fascia.")

except Exception as e:
    st.error(f"Errore generale: {e}")
