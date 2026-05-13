import pandas as pd
import numpy as np
from supabase import create_client

# 1. CONFIGURAZIONE MOTORE
URL = "IL_TUO_URL_SUPABASE"
KEY = "LA_TUA_KEY_SUPABASE"
supabase = create_client(URL, KEY)

def sviluppa_motori():
    # --- ASPIRAZIONE DATI ---
    print("Accensione... Aspirazione dati da Supabase...")
    res = supabase.table("estrazioni").select("*").order("data_estrazione").execute()
    df = pd.DataFrame(res.data)
    
    # Calcolo Somma e Media (DNA)
    colonne_n = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    df['somma'] = df[colonne_n].sum(axis=1)
    df['dna_medio'] = df[colonne_n].mean(axis=1)
    
    # --- MOTORE 1: MAPPATURA VALLI ---
    print("Mappatura valli di transizione in corso...")
    # Creiamo fasce di somma ogni 10 unità
    bins = np.arange(20, 540, 10)
    df['fascia'] = pd.cut(df['somma'], bins=bins)
    
    # Analisi Saturazione
    mappa = df.groupby('fascia').agg(
        frequenza=('somma', 'count'),
        dna_storico=('dna_medio', 'mean')
    ).reset_index()
    
    # --- MOTORE 2: CALCOLO COMPENSAZIONE (ANTIDOTO) ---
    # Media teorica di una sestina bilanciata è 45.5
    # Se dna_storico > 45.5 la zona è "Satura di Alti" -> serve Antidoto BASSO
    # Se dna_storico < 45.5 la zona è "Satura di Bassi" -> serve Antidoto ALTO
    mappa['antidoto'] = mappa['dna_storico'].apply(lambda x: 'USA_BASSI' if x > 45.5 else 'USA_ALTI')
    
    # Identifichiamo le Valli (Frequenza sotto la media del 30%)
    soglia_vuoto = mappa['frequenza'].mean() * 0.7
    mappa['tipo_zona'] = mappa['frequenza'].apply(lambda x: 'TRANSIZIONE (VUOTO)' if x < soglia_vuoto else 'SATURA')
    
    return mappa

# ESECUZIONE
mappa_definitiva = sviluppa_motori()

# FILTRO PER LA TUA OPERATIVITÀ (Zona intorno all'ultimo 182)
target = mappa_definitiva[(mappa_definitiva['frequenza'] > 0)]
print("\n--- REPORT MOTORE: ZONE DI INTERESSE PROSSIME ---")
print(target.tail(10)) # Mostra le ultime fasce analizzate
