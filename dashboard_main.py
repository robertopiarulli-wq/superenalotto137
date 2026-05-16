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
    # MOTORE DI SCREMATURA GERARCHICO E CORRETTO V23.2
    # ----------------------------------------------------------------------
    # STEP 1: FILTRO 1 - Esclusione immediata e assoluta dei 6 numeri dell'ultima estrazione
    blacklist_filtro1 = set(df.iloc[0][cols].values.flatten())
    
    # Prendiamo lo storico delle ultime 137 estrazioni
    df_137 = df.head(137)
    tutti_i_numeri_137 = df_137[cols].values.flatten()
    
    # STEP 2: FILTRO 2 - Calcolo frequenze escludendo PRIMA i numeri del Filtro 1
    conteggio_frequenze = pd.Series(tutti_i_numeri_137).value_counts()
    for n in range(1, 91):
        if n not in conteggio_frequenze: 
            conteggio_frequenze[n] = 0
            
    # Rimuoviamo i numeri del filtro 1 prima di prendere i 14 peggiori
    for n in blacklist_filtro1:
        if n in conteggio_frequenze:
            conteggio_frequenze.drop(n, inplace=True)
            
    # Prendiamo i 14 numeri meno frequenti tra quelli rimasti
    meno_frequenti = set(conteggio_frequenze.nsmallest(14).index)
    
    # STEP 3: FILTRO 3 - Calcolo ritardi escludendo PRIMA i numeri del Filtro 1
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
            
    # Trasformiamo in Serie per rimuovere in sicurezza i numeri del filtro 1
    serie_ritardi = pd.Series(ritardi_137)
    for n in blacklist_filtro1:
        if n in serie_ritardi:
            serie_ritardi.drop(n, inplace=True)
            
    # Prendiamo i 14 più ritardatari tra quelli rimasti
    piu_ritardatari = set(serie_ritardi.nlargest(14).index)
    
    # Unione finale blindata gerarchicamente: nessuna sovrapposizione parassita
    blacklist = blacklist_filtro1.union(meno_frequenti).union(piu_ritardatari)
    # ----------------------------------------------------------------------
    
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

def calcola_statistiche_macro_fasce(df_137):
    risultati = {"BANCO": {"freq": 0, "rit": 0}, "CUORE": {"freq": 0, "rit": 0}, "TETTO": {"freq": 0, "rit": 0}}
    
    for _, row in df_137.iterrows():
        somma = row.n1 + row.n2 + row.n3 + row.n4 + row.n5 + row.n6
        if 115 <= somma <= 170: risultati["BANCO"]["freq"] += 1
        elif 170 < somma <= 215: risultati["CUORE"]["freq"] += 1
        elif 215 < somma <= 270: risultati["TETTO"]["freq"] += 1
        
    for chiave, limiti in [("BANCO", (115, 170)), ("CUORE", (170, 215)), ("TETTO", (215, 270))]:
        rit = 0
        for _, row in df_137.iterrows():
            somma = row.n1 + row.n2 + row.n3 + row.n4 + row.n5 + row.n6
            condizione = (limiti[0] <= somma <= limiti[1]) if chiave == "BANCO" else (limiti[0] < somma <= limiti[1])
            if condizione:
                break
            rit += 1
        risultati[chiave]["rit"] = rit
        
    return risultati

# MAPPA DELLE GEOMETRIE COMPLESSE PER IL RADAR E LA VALVOLA DI CODA
blocchi_A = list(range(1, 16)) + list(range(31, 46)) + list(range(61, 76))
blocchi_B = list(range(16, 31)) + list(range(46, 61)) + list(range(76, 91))
blocchi_C = list(range(1, 16)) + list(range(46, 76))
blocchi_D = list(range(16, 46)) + list(range(76, 91))

def test_geometria_valvola(profilo, sestina):
    if profilo == "Solo Under 45": return all(n <= 45 for n in sestina)
    if profilo == "Solo Over 45": return all(n >= 46 for n in sestina)
    if profilo == "Solo Pari": return all(n % 2 == 0 for n in sestina)
    if profilo == "Solo Dispari": return all(n % 2 != 0 for n in sestina)
    if profilo == "Solo Media (20-70)": return all(20 <= n <= 70 for n in sestina)
    if profilo == "Solo Alternata A": return all(n in blocchi_A for n in sestina)
    if profilo == "Solo Alternata B": return all(n in blocchi_B for n in sestina)
    if profilo == "Solo Alternata C": return all(n in blocchi_C for n in sestina)
    if profilo == "Solo Alternata D": return all(n in blocchi_D for n in sestina)
    return True

# --- MODULO RADAR ANOMALIE V23 ---
def motore_radar_anomalie(df):
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

# --- UI INTERFACCIA ---
st.set_page_config(page_title="Morsa V23.3 - Valvola Energetica", layout="wide")

try:
    df_full, blacklist, mappa_ritardi, f1_last, f2_freq, f3_rit = analizza_dati_freschi()
    scienza, valli, sature, antidoto_attivo = carica_report_motori()
    stats_macro = calcola_statistiche_macro_fasce(df_full.head(137))

    st.title("🚀 Morsa Scientifica V23.3: Valvola Selettiva Post-Combinatoria")

    # SPECCHIETTO DETTAGLIATO DEI FILTRI IN TOP PAGE
    with st.expander("🔍 Dettaglio Scrematura Quantitativa V23.2 (Anticipazione Filtro 1 Garantita)"):
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            st.error(f"Filtro 1: Ultima Estrazione ({len(f1_last)} num - PRIORITARIO)")
            st.code(f"{sorted(list(f1_last))}")
        with c_f2:
            st.warning(f"Filtro 2: 14 Meno Frequenti ({len(f2_freq)} num - Esclusi i num del Filtro 1)")
            st.code(f"{sorted(list(f2_freq))}")
        with c_f3:
            st.info(f"Filtro 3: 14 Più Ritardatari ({len(f3_rit)} num - Esclusi i num del Filtro 1)")
            st.code(f"{sorted(list(f3_rit))}")
        st.success(f"Massa Critica Blacklist Totale Effettiva: {len(blacklist)} numeri eliminati alla partenza.")

    # INDICATORE DELL'ANTIDOTO
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
    
    # MODIFICA V23.3: Diventa una valvola di scarico post-calcolo! I numeri rimangono liberi alla partenza.
    filtro_sincro = st.selectbox("🎯 APPLICA VALVOLA GEOMETRICA (Sincronizza il profilo Critico del Radar stasera):", 
                                ["Nessuno", "Solo Under 45", "Solo Over 45", "Solo Pari", "Solo Dispari", 
                                 "Solo Media (20-70)", "Solo Alternata A", "Solo Alternata B", "Solo Alternata C", "Solo Alternata D"])

    st.write("**Pool Superstiti Nobili Completi (Usa come fisse/cardini):**")
    st.code(f"{pool_residuo}")

    # 3. SIDEBAR PARAMETRI CON INTEGRAZIONE COORDINATA DEI NUCLEI
    st.sidebar.header("🎯 Parametri di Gioco")
    
    opzioni_nuclei = ["Manuale"]
    if scienza["nuclei_accelerati"]:
        opzioni_nuclei += [f"{n[0]}-{n[1]}" for n in scienza["nuclei_accelerati"] if not any(num in blacklist for num in n)]
        
    scelta_acc = st.sidebar.selectbox("🔥 Carica Coppia Nucleo Accelerato:", opzioni_nuclei)
    fisse_auto = [int(x) for x in scelta_acc.split("-")] if scelta_acc != "Manuale" else []

    cardini = st.sidebar.multiselect("Cardini Attivi (Fisse)", range(1, 91), default=fisse_auto if fisse_auto else (pool_residuo[:2] if pool_residuo else []))
    ampiezza_pool = st.sidebar.slider("Potenza di Espansione Popolo (Slider)", 15, 45, 25)
    tipo_riduzione = st.sidebar.selectbox("Filtro Riduttore Ottimizzato", ["Nessuna", "Garanzia 4", "Garanzia 5"])

    target_h = df_full['H'].iloc[0:136].mean() * 0.98
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Bersaglio Rugosità H (Parisi)", f"{target_h:.5f}")
    m2.metric("Cluster Attivo", scienza.get("cluster_attivo", "Non rilevato"))
    m3.metric("Filtro Totale Blacklist (V23.2)", f"{len(blacklist)} num")

    # PRE-CALCOLO PREVENTIVO DEI CANDIDATI SUPERSTITI (COMPLETO E BILANCIATO PER LE SOMME)
    somma_fisse = sum(cardini)
    n_mancanti = 6 - len(cardini)
    media_target = (sum(valle_target)/2 - somma_fisse) / n_mancanti if n_mancanti > 0 else 0
    
    tutti_i_numeri = [n for n in range(1, 91) if n not in blacklist and n not in cardini]
    popolo = sorted(tutti_i_numeri, key=lambda x: abs(x - media_target))
    
    # Il pool finale si compone liberamente garantendo che l'algoritmo possa far incastrare la Somma Wyckoff
    pool_f = sorted(list(set(cardini + pool_residuo + popolo[:ampiezza_pool - len(pool_residuo)])))

    # 4. EVIDENZIAZIONE DEI CANDIDATI SUPERSTITI REALI
    st.subheader("🕵️ Analisi Preventiva dei Candidati Superstiti")
    st.info(f"Prima della generazione, la morsa ha selezionato un set di **{len(pool_f)} numeri candidati** bilanciati per le medie Wyckoff.")
    st.code(f"Numeri pronti al calcolo combinatorio: {pool_f}")

    # 5. MOTORE COMBINATORIO E GENERAZIONE V23.3 CON VALVOLA DI SCARICO
    if st.button("🚀 GENERA ARROSTO SINCRONIZZATO V23"):
        sestine_nobili = []
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                
                # VINCOLO 1: LA STRUTTURA ENERGETICA WYCKOFF (LA SOMMA COMANDA)
                if (valle_target[0] <= somma_s <= valle_target[1]):
                    check_saturazione = any(sf[0] < somma_s <= sf[1] for sf in sature if sf[0] < 220)
                    
                    if not check_saturazione:
                        # VINCOLO 2: RUGOSITÀ H (PARISI)
                        if abs(calcola_rugosita(s) - target_h) < (target_h * 0.15):
                            
                            # 🚨 SELEZIONE CHIRURGICA: Applica la Valvola Geometrica Post-Generazione!
                            if test_geometria_valvola(filtro_sincro, s):
                                sestine_nobili.append(s)
                            
            if i > 2500000: break # Alzato a 2.5 Mln per dare respiro al calcolo e non strozzare le combinazioni
            if i % 50000 == 0: prog.progress(min((i+1)/len(combs) if len(combs)>0 else 1, 1.0))
        prog.empty()

        risultato = riduttore_garantito(sestine_nobili, 5 if "5" in tipo_riduzione else 4) if tipo_riduzione != "Nessuna" else sestine_nobili

        st.subheader("📄 Report Strategico di Selezione (V23.3)")
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown(f"""
            **Configurazione Algoritmica V23.3:**
            * **Valvola Geometrica Attiva (Post-Calcolo)**: {filtro_sincro}
            * **Cardini Bloccati (Fisse)**: {cardini}
            * **Macro-Fascia Selezionata**: {scelta_macro.split(':')[0]}
            * **Intervallo di Somma Effettivo**: {valle_target[0]}-{valle_target[1]}
            """)
        with cr2:
            st.metric("Sestine Passate dalla Valvola", len(sestine_nobili))
            st.metric("Sestine Superstiti Ottimizzate", len(risultato))

        if risultato:
            df_res = pd.DataFrame(risultato, columns=['N1','N2','N3','N4','N5','N6'])
            st.table(df_res.head(40))
            st.download_button("💾 Esporta per Stampa (CSV)", df_res.to_csv(index=False).encode('utf-8'), "morsa_v23_sincro.csv", "text/csv")
        else:
            st.error("Nessun incastro trovato. Modifica l'ampiezza dello slider della potenza o seleziona una macro-fascia Wyckoff più armonica con il profilo scelto.")

except Exception as e:
    st.error(f"Errore generale: {e}")
