# laboratorio_segnale/motore_lineare_137.py
import os
import json
import numpy as np
import pandas as pd
import scipy.stats as stats
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.stattools import acf
from supabase import create_client

# --- ARCHITETTURA DI MAPPATURA ENVIROMENT AD ADATTAMENTO DINAMICO ---
# Cerchiamo tutte le possibili varianti di nome comunemente usate nei Secret YAML o in Streamlit
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

# Se i tentativi su os.environ falliscono (es: test locale o fallback), intercettiamo Streamlit secrets
if not URL or not KEY:
    try:
        import streamlit as st
        URL = st.secrets.get("URL_SUPABASE") or st.secrets.get("SUPABASE_URL")
        KEY = st.secrets.get("KEY_SUPABASE") or st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

# Controllo finale di blocco prima del crash
if not URL or not KEY:
    print("❌ ERRORE CRITICO: Credenziali Supabase non rilevate.")
    print("Mappatura attuale rilevata nel Runner Linux:")
    print(f" - URL Trovato: {True if URL else False}")
    print(f" - KEY Trovata: {True if KEY else False}")
    print("\n👉 Verifica che nel file 'estrazioni_cron.yml' sotto la voce 'env:' del laboratorio ci sia scritto:")
    print("env:\n  URL_SUPABASE: ${{ secrets.URL_SUPABASE }}\n  KEY_SUPABASE: ${{ secrets.KEY_SUPABASE }}")
    exit(1)

try:
    supabase = create_client(URL, KEY)
except Exception as e:
    print(f"Errore inizializzazione client Supabase: {e}")
    exit(1)


def esegui_analisi_fasi_unidimensionale():
    print("🛰️ Estrazione archivio storico per srotolamento lineare...")
    res = supabase.table("estrazioni").select("n1,n2,n3,n4,n5,n6,data_estrazione").order("data_estrazione", desc=False).execute()
    df = pd.DataFrame(res.data)
    
    # Srotolamento lineare delle sestine in un unico vettore continuo
    colonne = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    flusso_completo = df[colonne].values.flatten()
    
    total_elementi = len(flusso_completo)
    print(f"📊 Flusso srotolato: {total_elementi} numeri consecutivi totali.")
    
    # Finestra mobile di esattamente 137 singoli numeri consecutivi (Logica 137x1)
    finestra_singoli_passi = 137
    flusso_finestra = flusso_completo[-finestra_singoli_passi:]
    print(f"⏱️ Finestra dinamica agganciata sugli ultimi {len(flusso_finestra)} singoli numeri emessi.")
    
    # Struttura dati per il report JSON isolato
    report = {
        "Configurazione_Segnale": {
            "Passi_Totali_Archivio": total_elementi,
            "Finestra_Analisi_Passi": finestra_singoli_passi
        },
        "Flusso_Globale_44k": {},
        "Finestra_Stretta_137": {},
        "Verdetto_Struttura": "RUMORE_BIANCO_PURO"
    }
    
    # --- PUNTO 1: CARATTERIZZAZIONE DI BASE (Stazionarietà ed Entropia) ---
    print("🧬 Verifica stazionarietà (ADF & KPSS)...")
    try:
        report["Flusso_Globale_44k"]["ADF_pvalue"] = round(float(adfuller(flusso_completo)[1]), 5)
        report["Flusso_Globale_44k"]["KPSS_pvalue"] = round(float(kpss(flusso_completo, regression='c', nlags="auto")[1]), 5)
        
        report["Finestra_Stretta_137"]["ADF_pvalue"] = round(float(adfuller(flusso_finestra)[1]), 5)
        report["Finestra_Stretta_137"]["KPSS_pvalue"] = round(float(kpss(flusso_finestra, regression='c', nlags="auto")[1]), 5)
    except Exception as e:
        print(f"Avviso computazione test stazionarietà: {e}")
        
    # Calcolo dell'Entropia di Shannon
    counts_44k, _ = np.histogram(flusso_completo, bins=90, range=(1, 91), density=True)
    counts_137, _ = np.histogram(flusso_finestra, bins=90, range=(1, 91), density=True)
    
    report["Flusso_Globale_44k"]["Entropia_Shannon"] = round(float(stats.entropy(counts_44k[counts_44k > 0])), 4)
    report["Finestra_Stretta_137"]["Entropia_Shannon"] = round(float(stats.entropy(counts_137[counts_137 > 0])), 4)
    
    # --- PUNTO 2: DIPENDENZE LINEARI (ACF Passo-Passo) ---
    print("📉 Calcolo dell'autocorrelazione a lag singolo...")
    try:
        acf_44k = acf(flusso_completo, nlags=5)
        acf_137 = acf(flusso_finestra, nlags=5)
        
        report["Flusso_Globale_44k"]["Autocorrelazione_Lag1"] = round(float(acf_44k[1]), 5)
        report["Flusso_Globale_44k"]["Autocorrelazione_Lag2"] = round(float(acf_44k[2]), 5)
        
        report["Finestra_Stretta_137"]["Autocorrelazione_Lag1"] = round(float(acf_137[1]), 5)
        report["Finestra_Stretta_137"]["Autocorrelazione_Lag2"] = round(float(acf_137[2]), 5)
        
        # --- VALIDAZIONE DEL RUMORE ---
        soglia_confidenza_137 = 2.0 / np.sqrt(finestra_singoli_passi)
        
        if abs(acf_137[1]) > soglia_confidenza_137:
            report["Verdetto_Struttura"] = "🚨 ANOMALIA REGISTRATA: La finestra degli ultimi 137 numeri rompe la barriera del rumore bianco!"
        elif report["Flusso_Globale_44k"]["ADF_pvalue"] > 0.05:
            report["Verdetto_Struttura"] = "⚠️ REGIME SWITCH: Rilevati segnali di non-stazionarietà nel lungo periodo."
    except Exception as e:
        print(f"Avviso computazione ACF: {e}")
        
    # --- SCRITTURA DENTRO IL FILE JSON DEDICATO ---
    cartella_corrente = os.path.dirname(__file__)
    percorso_json = os.path.join(cartella_corrente, "report_fasi.json")
    
    with open(percorso_json, "w") as f:
        json.dump(report, f, indent=4)
    print(f"✅ Analisi lineare conclusa. File aggiornato con successo: {percorso_json}")

if __name__ == "__main__":
    esegui_analisi_fasi_unidimensionale()
