import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import json
import os
import itertools

# --- 1. CONNESSIONE SUPABASE (FASE 0) ---
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

# --- 2. FASE 1 & FASE 2: ESTRAZIONE DATI E BLACKLIST (137 PASSI) ---
@st.cache_data(ttl=3600) 
def analizza_dati_freschi():
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    df = pd.DataFrame(res.data)
    df['H'] = df.apply(lambda r: calcola_rugosita([r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]), axis=1)
    
    cols = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    blacklist_filtro1 = set(df.iloc[0][cols].values.flatten())
    df_137 = df.head(137).copy()
    
    pesi_temporali = np.exp(-np.linspace(0, 3.5, len(df_137)))
    energia_numeri = {n: 0.0 for n in range(1, 91)}
    
    for idx, row in enumerate(df_137[cols].values):
        peso_corrente = pesi_temporali[idx]
        for num in row:
            if num in energia_numeri:
                energia_numeri[num] += peso_corrente

    conteggio_frequenze = pd.Series(energia_numeri)
    for n in blacklist_filtro1:
        if n in conteggio_frequenze:
            conteggio_frequenze.drop(n, inplace=True)
            
    meno_frequenti = set(conteggio_frequenze.nsmallest(14).index)
    
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
            
    serie_ritardi = pd.Series(ritardi_137)
    for n in blacklist_filtro1:
        if n in serie_ritardi:
            serie_ritardi.drop(n, inplace=True)
            
    punteggio_tossicita = {}
    for num, rit in serie_ritardi.items():
        if 15 <= rit <= 26:
            punteggio_tossicita[num] = -100 
        elif rit > 30:
            punteggio_tossicita[num] = rit * 2
        else:
            punteggio_tossicita[num] = rit

    serie_tossicita = pd.Series(punteggio_tossicita)
    piu_ritardatari = set(serie_tossicita.nlargest(14).index)
    
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

# --- 3. DIZIONARIO SEQUENZIALE DELLE FASCE ALTERNATE ---
FASCE_GEOMETRICHE = {
    "Solo Under 45": list(range(1, 46)),
    "Solo Over 45": list(range(46, 91)),
    "Solo Pari": [n for n in range(1, 91) if n % 2 == 0],
    "Solo Dispari": [n for n in range(1, 91) if n % 2 != 0],
    "Solo Media (20-70)": list(range(20, 71)),
    "Solo Alternata A": list(range(1, 16)) + list(range(31, 46)) + list(range(61, 76)),
    "Solo Alternata B": list(range(16, 31)) + list(range(46, 61)) + list(range(76, 91)),
    "Solo Alternata C": list(range(1, 16)) + list(range(46, 76)),
    "Solo Alternata D": list(range(16, 46)) + list(range(76, 91))
}

def test_geometria_valvola(profilo, sestina):
    if profilo == "Nessuno": return True
    numeri_validi = FASCE_GEOMETRICHE.get(profilo, [])
    return all(n in numeri_validi for n in sestina)

def motore_radar_anomalie(df):
    profili = {
        "Fascia Under 45": lambda s: all(n <= 45 for n in s),
        "Fascia Over 45": lambda s: all(n >= 46 for n in s),
        "Total Even (6 Pari)": lambda s: all(n % 2 == 0 for n in s),
        "Total Odd (6 Dispari)": lambda s: all(n % 2 != 0 for n in s),
        "Fascia Media (20-70)": lambda s: all(20 <= n <= 70 for n in s),
        "Fascia Alternata A": lambda s: all(n in FASCE_GEOMETRICHE["Solo Alternata A"] for n in s),
        "Fascia Alternata B": lambda s: all(n in FASCE_GEOMETRICHE["Solo Alternata B"] for n in s),
        "Fascia Alternata C": lambda s: all(n in FASCE_GEOMETRICHE["Solo Alternata C"] for n in s),
        "Fascia Alternata D": lambda s: all(n in FASCE_GEOMETRICHE["Solo Alternata D"] for n in s),
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

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Morsa V24.2 RC - Golden Window Delay & Simpatia", layout="wide")

try:
    df_full, blacklist, mappa_ritardi, f1_last, f2_freq, f3_rit = analizza_dati_freschi()
    scienza, valli, sature, antidoto_attivo = carica_report_motori()
    stats_macro = calcola_statistiche_macro_fasce(df_full.head(137))

    st.title("🚀 Morsa Predittiva V24.2 (RC): Protezione Fascia d'Oro & Matrice Simpatie")

    with st.expander("🔍 Dettaglio Scrematura Quantitative V24.2 (Ritardi Selettivi a Tossicità)"):
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            st.error(f"Filtro 1: Ultima Estrazione ({len(f1_last)} num - PRIORITARIO)")
            st.code(f"{sorted(list(f1_last))}")
        with c_f2:
            st.warning(f"Filtro 2: 14 Meno Energetici ({len(f2_freq)} num)")
            st.code(f"{sorted(list(f2_freq))}")
        with c_f3:
            st.info(f"Filtro 3: 14 a Massima Tossicità ({len(f3_rit)} num)")
            st.code(f"{sorted(list(f3_rit))}")
        st.success(f"Massa Critica Blacklist Totale Effettiva: {len(blacklist)} numeri eliminati alla partenza.")

    # ==========================================
    # AREA CONFIGURAZIONE 1: LE MACRO-FASCE WYCKOFF
    # ==========================================
    st.header("📦 AREA 1: Target di Bilanciamento Wyckoff & Radar Anomalie")
    
    if antidoto_attivo == 'BILANCIARE_CON_ALTI':
        st.error("🚨 ALERT PRESSIONE SATURE: Antidoto consigliato -> BILANCIARE_CON_ALTI (Forzare su fascia TETTO).")
    else:
        st.info("ℹ️ Stato Pressione: Nessun Antidoto forzato rilevato nel report.")

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

        scelta_macro = st.radio(
            "Seleziona Target Wyckoff:",
            ["BANCO (Somme Basse / Compressione): [115, 170]", 
             "CUORE (Somme Medie / Equilibrio): (170, 215]", 
             "TETTO (Somme Alte / Espansione & Antidoto): (215, 270]"],
            index=1
        )
        valle_target = (115, 170) if "BANCO" in scelta_macro else (170, 215) if "CUORE" in scelta_macro else (215, 270)
        st.success(f"🎯 **Target Sincronizzato Active**: {valle_target[0]} - {valle_target[1]}")

    # ==========================================
    # AREA CONFIGURAZIONE 2: FILTRI GEOMETRICI (FASCE ALTERNATE)
    # ==========================================
    st.header("📐 AREA 2: Valvola Geometrica & Fasce Alternate")
    
    filtro_sincro = st.selectbox(
        "Seleziona la Valvola Geometrica (Sincronizza il profilo Critico del Radar):", 
        ["Nessuno", "Solo Under 45", "Solo Over 45", "Solo Pari", "Solo Dispari", 
         "Solo Media (20-70)", "Solo Alternata A", "Solo Alternata B", "Solo Alternata C", "Solo Alternata D"]
    )

    # --- CARICAMENTO ASINCRONO DATI LABORATORIO SEGNALE ---
    file_json = "laboratorio_segnale/report_fasi.json"
    numeri_anomalia = []
    coppie_anomalia = []
    if os.path.exists(file_json):
        with open(file_json, "r") as f:
            dati_fasi = json.load(f)
        contenuto_imbuto = dati_fasi.get("Contenuto_Imbuto", {})
        numeri_anomalia = [int(n) for n in contenuto_imbuto.get("Numeri_Dominanti_Imbuto", [])]
        coppie_anomalia = contenuto_imbuto.get("Coppie_Trascinamento_Lag1", [])

    # ==========================================
    # AREA CONFIGURAZIONE 3: CARDINI, CORRELATI E SUGGERIMENTI SALVAVITA
    # ==========================================
    st.header("🎯 AREA 3: Sincronizzazione Cardini & Suggerimento Ponderato")
    
    st.sidebar.header("🎯 Parametri di Gioco")
    sorgente_cardini = st.sidebar.radio(
        "Sorgente Punti di Ancoraggio (Cardini):", 
        ["Fisse Classiche (Morsa)", "Usa Numeri dell'Imbuto (Anomalia 137x1)"]
    )
    ampiezza_pool = st.sidebar.slider("Potenza di Espansione Popolo (Slider)", 15, 45, 25)
    tipo_riduzione = st.sidebar.selectbox("Filtro Riduttore Ottimizzato", ["Nessuna", "Garanzia 4", "Garanzia 5"])

    # --- MOTORE DI PRE-CALCOLO E BILANCIAMENTO SALVAVITA ---
    i_12_prescelti = numeri_anomalia[:12]
    media_geometrica_obiettivo = sum(valle_target) / 2 / 6  
    Numeri_Validati_Geometria = FASCE_GEOMETRICHE.get(filtro_sincro, list(range(1, 91)))

    # Ordiniamo i correlati validi per vicinanza al baricentro della fascia
    correlati_filtrati_ordinati = sorted(
        [n for n in i_12_prescelti if n in Numeri_Validati_Geometria],
        key=lambda x: abs(x - media_geometrica_obiettivo)
    )

    # Estrazione della coppia salvavita ottimale (un bilanciamento alto/basso interno al set filtrato)
    default_cardini = []
    if sorgente_cardini == "Usa Numeri dell'Imbuto (Anomalia 137x1)" and correlati_filtrati_ordinati:
        if len(correlati_filtrati_ordinati) >= 2:
            default_cardini = [correlati_filtrati_ordinati[0], correlati_filtrati_ordinati[-1]]
        else:
            default_cardini = correlati_filtrati_ordinati[:1]
    else:
        pool_residuo_statico = [n for n in scienza["pool_eletto"] if n not in blacklist and n in Numeri_Validati_Geometria]
        if len(pool_residuo_statico) >= 2:
            default_cardini = [pool_residuo_statico[0], pool_residuo_statico[-1]]

    # Messaggio di Alert Intelligente per guidare l'utente
    if default_cardini:
        st.success(f"💡 **SUGGERIMENTO PONDERATO DEL MOTORE:** Per l'incastro attuale (Wyckoff + Fascia Geometrica), i migliori punti di aggancio per evitare 0 sestine sono: `{default_cardini}`")
    else:
        st.warning("⚠️ **ATTENZIONE INCASTRO CRITICO:** Nessun elemento utile rientra nella combinazione di filtri scelta. Per evitare 0 sestine, allarga il Popolo o cambia la Fascia Alternata.")

    cardini = st.multiselect("Cardini Attivi (Modifica o mantieni il consiglio salvavita):", range(1, 91), default=default_cardini)

    # --- LOGICA INTEGRATA DI COMPOSIZIONE GENERALE DEL POOL (25) ---
    somma_fisse = sum(cardini)
    n_mancanti = 6 - len(cardini)
    media_target = (sum(valle_target)/2 - somma_fisse) / n_mancanti if n_mancanti > 0 else 0

    if sorgente_cardini == "Usa Numeri dell'Imbuto (Anomalia 137x1)" and i_12_prescelti:
        # Fissiamo i 12 immuni dalla blacklist come base prioritaria
        base_immune = i_12_prescelti.copy()
        
        # Il popolo di completamento esterno deve rispettare la Blacklist E la Fascia Alternata!
        tutti_i_numeri = [n for n in range(1, 91) if n not in base_immune and n not in cardini and n not in blacklist and n in Numeri_Validati_Geometria]
        
        simpatia_punteggi = {n: 0 for n in tutti_i_numeri}
        df_137_values = df_full.head(137)[['n1','n2','n3','n4','n5','n6']].values
        for row in df_137_values:
            presenza = [b for b in base_immune if b in row]
            if presenza:
                for n in row:
                    if n in simpatia_punteggi:
                        simpatia_punteggi[n] += len(presenza)
                        
        popolo = sorted(tutti_i_numeri, key=lambda x: (abs(x - media_target) * 1.5) - (simpatia_punteggi[x] * 2.0))
        spazio_rimanente = max(0, ampiezza_pool - len(cardini) - len(base_immune))
        pool_f = sorted(list(set(cardini + base_immune + popolo[:spazio_rimanente])))
    else:
        pool_residuo = [n for n in scienza["pool_eletto"] if n not in blacklist]
        tutti_i_numeri = [n for n in range(1, 91) if n not in blacklist and n not in cardini and n in Numeri_Validati_Geometria]
        
        bersagli_simpatia = cardini if cardini else pool_residuo
        simpatia_punteggi = {n: 0 for n in tutti_i_numeri}
        df_137_values = df_full.head(137)[['n1','n2','n3','n4','n5','n6']].values
        if bersagli_simpatia:
            for row in df_137_values:
                presenza = [b for b in bersagli_simpatia if b in row]
                if presenza:
                    for n in row:
                        if n in simpatia_punteggi:
                            simpatia_punteggi[n] += len(presenza)

        popolo = sorted(tutti_i_numeri, key=lambda x: (abs(x - media_target) * 1.5) - (simpatia_punteggi[x] * 2.0))
        pool_f = sorted(list(set(cardini + pool_residuo + popolo[:ampiezza_pool - len(pool_residuo)])))

    st.subheader("🕵️ Pool Pronto per il Calcolo Combinatorio")
    st.code(f"Morsa Attiva (Ampiezza Reale {len(pool_f)} elementi): {pool_f}")

    # ==========================================
    # AREA 4: ELABORAZIONE FINALE ARROSTO
    # ==========================================
    st.header("🔥 AREA 4: Elaborazione Finale")
    
    target_h = df_full['H'].iloc[0:136].mean() * 0.985
    m1, m2, m3 = st.columns(3)
    m1.metric("Bersaglio Rugosità H (Parisi)", f"{target_h:.5f}")
    m2.metric("Cluster Attivo", scienza.get("cluster_attivo", "Non rilevato"))
    m3.metric("Filtro Totale Blacklist", f"{len(blacklist)} num")

    if st.button("🚀 GENERA ARROSTO SINCRONIZZATO V24"):
        sestine_nobili = []
        combs = list(itertools.combinations(pool_f, 6))
        prog = st.progress(0)
        
        for i, comb in enumerate(combs):
            s = sorted(list(comb))
            if all(f in s for f in cardini):
                somma_s = sum(s)
                
                # Controllo sequenziale 1: Range Somma Wyckoff
                if (valle_target[0] <= somma_s <= valle_target[1]):
                    check_saturazione = any(sf[0] < somma_s <= sf[1] for sf in sature if sf[0] < 220)
                    
                    # Controllo sequenziale 2: Esclusione Zone Sature
                    if not check_saturazione:
                        # Controllo sequenziale 3: Rugosità H di Parisi
                        if abs(calcola_rugosita(s) - target_h) < (target_h * 0.12):
                            # Controllo sequenziale 4: Vincolo della Fascia Geometrica Alternata
                            if test_geometria_valvola(filtro_sincro, s):
                                sestine_nobili.append(s)
                            
            if i > 1500000: break
            if i % 25000 == 0: prog.progress(min((i+1)/len(combs) if len(combs)>0 else 1, 1.0))
        prog.empty()

        risultato = riduttore_garantito(sestine_nobili, 5 if "5" in tipo_riduzione else 4) if tipo_riduzione != "Nessuna" else sestine_nobili

        st.subheader("📄 Report Strategico di Selezione (V24.2)")
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown(f"""
            **Configurazione Sequenziale Applicata:**
            * **Fascia Alternata / Valvola**: {filtro_sincro}
            * **Cardini Bloccati Fissi**: {cardini}
            * **Intervallo di Somma Wyckoff Target**: {valle_target[0]}-{valle_target[1]}
            """)
        with cr2:
            st.metric("Sestine Passate dai Filtri", len(sestine_nobili))
            st.metric("Sestine Ridotte Finali", len(risultato))

        if risultato:
            df_res = pd.DataFrame(risultato, columns=['N1','N2','N3','N4','N5','N6'])
            st.table(df_res.head(40))
            st.download_button("💾 Esporta CSV", df_res.to_csv(index=False).encode('utf-8'), "morsa_v24_2.csv", "text/csv")
        else:
            st.error("Nessun incastro trovato. Segui i suggerimenti ponderati nell'Area 3 dei Cardini per non fare zero.")

except Exception as e:
    st.error(f"Errore generale: {e}")

# ==========================================
# SEZIONE ISOLATA IN CODA: IL LABORATORIO 137
# ==========================================
st.divider()
st.subheader("🔬 Laboratorio Quantistico: Analisi del Flusso Lineare (137x1)")
if os.path.exists(file_json) and dati_fasi:
    c_an_1, c_an_2 = st.columns(2)
    with c_an_1:
        st.markdown("🎯 **Imbuto dei Correlati (Top Frequenze 137x1 Puri):**")
        st.code(f"{numeri_anomalia[:12]}")
    with c_an_2:
        st.markdown("🔄 **Coppie a Trascinamento Lineare Attivo (Lag 1):**")
        st.code(f"{coppie_anomalia}")
