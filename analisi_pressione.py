import pandas as pd
import numpy as np
import os
from supabase import create_client

# --- CONFIGURAZIONE SICURA VIA GITHUB SECRETS ---
# Il modulo 'os' pesca le credenziali direttamente dall'ambiente virtuale
URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")

if not URL_SUPABASE or not KEY_SUPABASE:
    raise ValueError("ERRORE: Credenziali non trovate nei GitHub Secrets!")

# Inizializzazione client
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def esegui_analisi_pressione():
    print("Accensione MOTORE 1: Analisi Pressione e Valli di Transizione (Modalità Segreta)...")
    
    # 1. Recupero totale storico
    response = supabase.table("estrazioni").select("*").order("data_estrazione").execute()
    df = pd.DataFrame(response.data)
    
    if df.empty:
        print("Database vuoto o errore di connessione.")
        return

    colonne_n = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    df['somma'] = df[colonne_n].sum(axis=1)
    df['dna_medio'] = df[colonne_n].mean(axis=1)
    
    # 2. Mappatura delle Fasce (Binning ogni 10 unità)
    bins = np.arange(20, 540, 10)
    df['fascia'] = pd.cut(df['somma'], bins=bins)
    
    # 3. Calcolo Saturazione e Sbilanciamento
    mappa = df.groupby('fascia', observed=False).agg(
        frequenza=('somma', 'count'),
        dna_storico=('dna_medio', 'mean')
    ).reset_index()
    
    # 4. Identificazione Valli (Transizione)
    media_freq = mappa['frequenza'].mean()
    mappa['stato_zona'] = mappa['frequenza'].apply(
        lambda x: 'VALLE (TRANSIZIONE)' if 0 < x < (media_freq * 0.7) else ('VUOTA' if x == 0 else 'SATURA')
    )
    
    # 5. Calcolo Antidoto (Compensazione Simmetrica)
    # 45.5 è la media teorica di una sestina (1+90)/2
    mappa['antidoto_suggerito'] = mappa['dna_storico'].apply(
        lambda x: 'BILANCIARE_CON_BASSI' if x > 45.5 else ('BILANCIARE_CON_ALTI' if x > 0 else 'N/A')
    )

    # 6. Salvataggio su File (L'Arrosto)
    mappa.to_csv("mappa_valli_pressione.csv", index=False)
    
    print("\n--- REPORT MOTORE 1 COMPLETATO ---")
    print(f"File generato con successo: mappa_valli_pressione.csv")
    
    # Focus sulla zona calda attuale (vicino all'ultima somma rilevata 182)
    print("\nFocus Zone adiacenti (Fasce Somma 170-240):")
    # Trasformiamo la colonna fascia per il filtraggio visivo
    mappa['left'] = mappa['fascia'].apply(lambda x: x.left)
    focus = mappa[(mappa['left'] >= 170) & (mappa['left'] <= 230)]
    print(focus[['fascia', 'frequenza', 'stato_zona', 'antidoto_suggerito']])

if __name__ == "__main__":
    esegui_analisi_pressione()
