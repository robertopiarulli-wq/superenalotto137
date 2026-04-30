import pandas as pd
from supabase import create_client
import numpy as np

# --- CONFIGURAZIONE ---
URL_SUPABASE = "TUA_URL_SUPABASE"
KEY_SUPABASE = "TUA_ANON_KEY"
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def calcola_rugosita(serie):
    """Calcola la rugosità statistica di una serie temporale."""
    if len(serie) < 2: return 0
    return np.std(np.diff(serie))

def esegui_analisi():
    print("Recupero ultime 137 estrazioni per calcolo di risonanza...")
    
    # Preleviamo le ultime 137 estrazioni ordinate per data
    response = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).limit(137).execute()
    data = response.data
    
    if len(data) < 137:
        print(f"Attenzione: Trovate solo {len(data)} estrazioni. L'analisi potrebbe essere meno precisa.")
    
    df = pd.DataFrame(data)
    
    # Trasformiamo i dati in una lista piatta di numeri usciti
    colonne_numeri = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    
    # Analisi per ogni numero da 1 a 90
    risultati = []
    
    for num in range(1, 91):
        # Troviamo le posizioni (ritardi) in cui è uscito il numero
        uscite = []
        for i, row in df.iterrows():
            if num in row[colonne_numeri].values:
                uscite.append(i) # Indice di distanza temporale
        
        if len(uscite) > 1:
            # Calcolo della Rugosità di Parisi (variazione dei ritardi)
            ritardi = np.diff(uscite)
            rugosita = calcola_rugosita(ritardi)
            frequenza = len(uscite)
            
            # Calcoliamo l'indice di Risonanza
            # Più la rugosità è bassa, più il numero è "armonico" e pronto ad uscire
            risonanza = frequenza / (rugosita + 1)
            
            risultati.append({'numero': num, 'risonanza': risonanza, 'frequenza': frequenza})

    # Ordiniamo i numeri per il più alto indice di risonanza
    classifica = sorted(risultati, key=lambda x: x['risonanza'], reverse=True)
    
    print("\n--- RISULTATI ANALISI DI RISONANZA 137 ---")
    print(f"Ultima estrazione analizzata: {df['data_estrazione'].iloc[0]}")
    print("-" * 40)
    
    top_6 = classifica[:6]
    sestina = [str(x['numero']) for x in top_6]
    
    print(f"SESTINA SUGGERITA: {' - '.join(sestina)}")
    print("-" * 40)
    for i, n in enumerate(top_6, 1):
        print(f"{i}° Numero: {n['numero']} (Indice Risonanza: {n['risonanza']:.4f})")

if __name__ == "__main__":
    esegui_analisi()
