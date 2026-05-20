# laboratorio_segnale/motore_lineare_137.py
import os
import json
import numpy as np
import pandas as pd
import scipy.stats as stats
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.stattools import acf
from supabase import create_client

# --- REPERIMENTO CREDENZIALI ---
URL = (
    os.environ.get("URL_SUPABASE") or 
    os.environ.get("SUPABASE_URL") or 
    os.environ.get("url_supabase") or 
    os.environ.get("supabase_url")
)

KEY = (
    os.environ.get("KEY_SUPABASE") or 
    os.environ.get("SUPABASE_KEY") or 
    os.environ.get("key_supabase") or 
    os.environ.get("supabase_key")
)

if not URL or not KEY:
    try:
        import streamlit as st
        URL = st.secrets.get("URL_SUPABASE") or st.secrets.get("SUPABASE_URL")
        KEY = st.secrets.get("KEY_SUPABASE") or st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

if not URL or not KEY:
    print("❌ ERRORE CRITICO: Credenziali Supabase mancanti.")
    exit(1)

supabase = create_client(URL, KEY)

def esegui_laboratorio():
    print("🔬 Avvio Laboratorio Quantistico: Morsa Sequenziale a Cascata Lag-1...")
    
    # Scarichiamo tutto l'archivio storico per mappare le transizioni reali
    res = supabase.table("estrazioni").select("*").order("data_estrazione", desc=False).execute()
    df_storico = pd.DataFrame(res.data)
    
    if df_storico.empty or len(df_storico) < 138:
        print("❌ Dati insufficienti per l'analisi.")
        exit(1)
        
    cols = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    sestine_cronologiche = df_storico[cols].values
    
    # ----------------------------------------------------------------------
    # FASE 1: COSTRUZIONE MATRICE DI TRASCINAMENTO DI TUTTI I 90 NUMERI (LAG-1)
    # ----------------------------------------------------------------------
    # Struttura per tracciare quante volte il numero Y è uscito subito dopo il numero X
    matrice_trascinamento = {x: {y: 0 for y in range(1, 91)} for x in range(1, 91)}
    
    for i in range(len(sestine_cronologiche) - 1):
        sestina_attuale = sestine_cronologiche[i]
        sestina_successiva = sestine_cronologiche[i+1]
        
        for n_attuale in sestina_attuale:
            for n_successivo in sestina_successiva:
                matrice_trascinamento[n_attuale][n_successivo] += 1

    # ----------------------------------------------------------------------
    # FASE 2: APPLICAZIONE DELL'IMBUTO SULL'ULTIMA ESTRAZIONE REALE
    # ----------------------------------------------------------------------
    ultima_sestina = sestine_cronologiche[-1]
    print(f"🎯 Ultima estrazione rilevata come innesco: {list(ultima_sestina)}")
    
    # Estrarre i correlati diretti condizionati dall'ultima estrazione
    punteggi_diretti = {n: 0 for n in range(1, 91)}
    for n_ancora in ultima_sestina:
        for corr, peso in matrice_trascinamento[n_ancora].items():
            punteggi_diretti[corr] += peso
            
    # Escludiamo i numeri dell'ultima estrazione stessa dai correlati per evitare loop statici
    for n in ultima_sestina:
        if n in punteggi_diretti:
            punteggi_diretti[n] = 0
            
    serie_diretti = pd.Series(punteggi_diretti)
    # Identifichiamo i Correlati Diretti Dominanti (I primi 6 estratti dall'imbuto di primo livello)
    correlati_diretti_prescelti = list(serie_diretti.nlargest(6).index)
    print(f"🔗 Correlati Diretti Prescelti (Livello 1): {correlati_diretti_prescelti}")

    # ----------------------------------------------------------------------
    # FASE 3: LA CASCATA CONTINUATIVA - INIEZIONE CORRELATI DEI PRESCELTI
    # ----------------------------------------------------------------------
    punteggi_secondo_livello = {n: 0 for n in range(1, 91)}
    for n_prescelto in correlati_diretti_prescelti:
        for corr_2, peso_2 in matrice_trascinamento[n_prescelto].items():
            punteggi_secondo_livello[corr_2] += peso_2
            
    # Pulizia da sovrascritture logiche (eliminiamo l'innesco di partenza)
    for n in ultima_sestina:
        if n in punteggi_secondo_livello:
            punteggi_secondo_livello[n] = 0
            
    serie_secondo_livello = pd.Series(punteggi_secondo_livello)
    # Isoliaino i correlati dei prescelti (Livello 2)
    correlati_dei_prescelti = list(serie_secondo_livello.nlargest(6).index)
    print(f"🌊 Correlati dei Prescelti Iniettati (Livello 2): {correlati_dei_prescelti}")

    # Unione atomica finale mantenendo rigorosamente la memoria del correlato attivo
    imbuto_finale_espanso = sorted(list(set(correlati_diretti_prescelti + correlati_dei_prescelti)))

    # ----------------------------------------------------------------------
    # FASE 4: CALCOLO DELLE METRICHE DI SEGNALE SU FINESTRA STRETTA 137
    # ----------------------------------------------------------------------
    df_137 = df_storico.tail(137).copy()
    flusso_completo = df_storico[cols].values.flatten()
    flusso_finestra = df_137[cols].values.flatten()
    
    report = {
        "Configurazione_Segnale": {
            "Passi_Totali_Archivio": len(flusso_completo),
            "Finestra_Analisi_Passi": 137
        },
        "Contenuto_Imbuto": {
            "Numeri_Dominanti_Imbuto": imbuto_finale_espanso,
            "Coppie_Trascinamento_Lag1": [f"{correlati_diretti_prescelti[i]}-{correlati_dei_prescelti[i]}" for i in range(min(len(correlati_diretti_prescelti), len(correlati_dei_prescelti)))]
        },
        "Verdetto_Struttura": "✅ SEGNALE ARMONICO BILANCIATO: Catena di trascinamento espansa attiva.",
        "Flusso_Globale_44k": {},
        "Finestra_Stretta_137": {}
    }
    
    try:
        # Analisi ADF (Augmented Dickey-Fuller) per la stazionarietà del flusso nel tempo
        adf_res = adfuller(flusso_completo)
        report["Flusso_Globale_44k"]["ADF_Stat"] = round(float(adf_res[0]), 5)
        report["Flusso_Globale_44k"]["ADF_pvalue"] = round(float(adf_res[1]), 5)
        
        # Calcolo Autocorrelazioni sequenziali (ACF)
        acf_44k = acf(flusso_completo, nlags=5)
        acf_137 = acf(flusso_finestra, nlags=5)
        
        report["Flusso_Globale_44k"]["Autocorrelazione_Lag1"] = round(float(acf_44k[1]), 5)
        report["Flusso_Globale_44k"]["Autocorrelazione_Lag2"] = round(float(acf_44k[2]), 5)
        
        report["Finestra_Stretta_137"]["Autocorrelazione_Lag1"] = round(float(acf_137[1]), 5)
        report["Finestra_Stretta_137"]["Autocorrelazione_Lag2"] = round(float(acf_137[2]), 5)
        
        soglia_confidenza_137 = 2.0 / np.sqrt(137 * 6)
        if abs(acf_137[1]) > soglia_confidenza_137:
            report["Verdetto_Struttura"] = "🚨 ANOMALIA REGISTRATA: La memoria a cascata di Lag-1 rompe la barriera del rumore caotico!"
    except Exception as e:
        print(f"⚠️ Errore calcolo metriche ausiliarie: {e}")

    # Salvataggio del report unificato per Streamlit
    cartella = "laboratorio_segnale"
    if not os.path.exists(cartella):
        os.makedirs(cartella)
        
    file_path = os.path.join(cartella, "report_fasi.json")
    with open(file_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"💾 Report salvato con successo in {file_path}. Righe imbuto espanso: {imbuto_finale_espanso}")

if __name__ == "__main__":
    esegui_laboratorio()
