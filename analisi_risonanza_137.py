import os
import pandas as pd
import numpy as np
from supabase import create_client
import json

# --- CONFIGURAZIONE ---
# Assicurati che queste variabili siano impostate nei Secrets di GitHub
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def calcola_rugosita(serie):
    """Calcola la rugosità (regolarità) dei ritardi tra le uscite."""
    if len(serie) < 2: return 0
    return np.std(np.diff(serie))

def esegui_analisi():
    # Recupero le ultime 137 estrazioni dal database Supabase
    response = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(137).execute()
    df = pd.DataFrame(response.data)
    
    colonne_numeri = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    risultati = []
    
    for num in range(1, 91):
        uscite = []
        # Identifichiamo dove il numero è apparso nelle ultime 137 estrazioni
        for i, row in df.iterrows():
            if num in row[colonne_numeri].values:
                uscite.append(i)
        
        if len(uscite) > 1:
            ritardi = np.diff(uscite)
            rugosita = calcola_rugosita(ritardi)
            frequenza = len(uscite)
            # Indice di Risonanza: premia chi esce spesso e con regolarità
            # Più è alto, più il numero è "armonico"
            risonanza = frequenza / (rugosita + 1)
            risultati.append({'numero': int(num), 'risonanza': float(risonanza)})

    # Ordiniamo i numeri dal più risonante al meno risonante
    classifica = sorted(risultati, key=lambda x: x['risonanza'], reverse=True)
    
    # --- MODIFICA FONDAMENTALE PER IL POOL ELETTO ---
    # Invece di salvare solo i primi 2, salviamo i primi 22 numeri nobili.
    # Questo permette alla Dashboard di avere abbastanza materiale per la combinatoria.
    top_risonanza = [n['numero'] for n in classifica[:22]]
    
    with open("cardini_scientifici.json", "w") as f:
        json.dump(top_risonanza, f)
    
    print(f"✅ Pool Risonanza (22 numeri) salvato con successo: {top_risonanza}")

if __name__ == "__main__":
    esegui_analisi()
