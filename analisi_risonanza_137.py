import os
import pandas as pd
import numpy as np
from supabase import create_client
import json

# --- CONFIGURAZIONE SICURA ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def calcola_rugosita(serie):
    if len(serie) < 2: return 0
    return np.std(np.diff(serie))

def esegui_analisi():
    response = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(137).execute()
    df = pd.DataFrame(response.data)
    
    colonne_numeri = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    risultati = []
    
    for num in range(1, 91): # Ciclo su numeri da 1 a 90
        uscite = []
        for i, row in df.iterrows():
            if num in row[colonne_numeri].values:
                uscite.append(i)
        
        if len(uscite) > 1:
            ritardi = np.diff(uscite)
            rugosita = calcola_rugosita(ritardi)
            frequenza = len(uscite)
            risonanza = frequenza / (rugosita + 1)
            risultati.append({'numero': int(num), 'risonanza': float(risonanza)})

    classifica = sorted(risultati, key=lambda x: x['risonanza'], reverse=True)
    
    # --- SALVATAGGIO CARDINI SCIENTIFICI ---
    # Prendiamo i primi 2 numeri con la risonanza più alta
    top_cardini = [n['numero'] for n in classifica[:2]]
    
    with open("cardini_scientifici.json", "w") as f:
        json.dump(top_cardini, f)
    
    print(f"Cardini scientifici rilevati e salvati: {top_cardini}")

if __name__ == "__main__":
    esegui_analisi()
