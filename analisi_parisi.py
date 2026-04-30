import pandas as pd
from supabase import create_client
import numpy as np

# Configurazione
URL = "TUA_URL_SUPABASE"
KEY = "TUA_ANON_KEY"
supabase = create_client(URL, KEY)

def calcola_rugosita(sestina):
    # Algoritmo di Parisi semplificato: variazione media dei gap
    sestina_ordinata = sorted(sestina)
    diffs = np.diff(sestina_ordinata)
    return np.std(diffs) / np.mean(diffs)

def analisi_risonanza_137():
    # 1. Recupero dati ordinati per data decrescente (dal più recente)
    response = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    df = pd.DataFrame(response.data)
    
    if len(df) < 137:
        print("Dati insufficienti per il blocco armonico 137")
        return

    print(f"Analisi su {len(df)} estrazioni totali.")

    # 2. Analisi a ritroso per blocchi armonici
    # Il numero 137 rappresenta la costante di struttura fine (1/alpha)
    blocco_recente = df.head(137)
    sestine = blocco_recente[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].values
    
    rugosita_totale = [calcola_rugosita(s) for s in sestine]
    h_medio = np.mean(rugosita_totale)
    
    # 3. Calcolo della Risonanza
    # Se H tende a 0.137, il sistema è in massima risonanza quantistica
    delta_risonanza = abs(h_medio - 0.137)
    
    print(f"--- RISULTATI ANALISI ---")
    print(f"Rugosità Media (H): {h_medio:.4f}")
    print(f"Scostamento dalla Risonanza 137: {delta_risonanza:.4f}")
    
    # 4. Generazione Range di Avvaloramento
    # Filtriamo i numeri che "risuonano" con l'ultima estrazione
    ultima_estrazione = sestine[0]
    target_numbers = []
    
    for n in range(1, 91):
        test_sestina = list(ultima_estrazione[1:]) + [n]
        if abs(calcola_rugosita(test_sestina) - 0.137) < delta_risonanza:
            target_numbers.append(n)
            
    print(f"Numeri in Fase Armonica: {sorted(list(set(target_numbers)))}")

if __name__ == "__main__":
    analisi_risonanza_137()
