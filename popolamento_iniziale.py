import pandas as pd
from supabase import create_client

# Sostituisci con i tuoi dati reali
URL = "TUA_URL_SUPABASE"
KEY = "TUA_ANON_KEY"
supabase = create_client(URL, KEY)

def carica_storico():
    # Carichiamo lo storico ufficiale (formato comune CSV)
    # Nota: Puoi scaricare il file storico aggiornato dal sito ufficiale
    # o usare un link diretto se disponibile.
    url_csv = "https://www.estrazionidellotto.it/download/storico-superenalotto.csv" # Esempio
    
    try:
        df = pd.read_csv(url_csv, sep=';') # Controlla il separatore del file
        
        # Pulizia dati: adatta i nomi delle colonne al tuo DB
        # Supponiamo che il CSV abbia: Data, N1, N2, N3, N4, N5, N6
        for index, row in df.tail(2000).iterrows(): # Prendiamo le ultime 2000
            dati = {
                "data_estrazione": row['Data'],
                "n1": int(row['N1']),
                "n2": int(row['N2']),
                "n3": int(row['N3']),
                "n4": int(row['N4']),
                "n5": int(row['N5']),
                "n6": int(row['N6'])
            }
            supabase.table("estrazioni").insert(dati).execute()
            
        print("Popolamento completato con successo!")
    except Exception as e:
        print(f"Errore durante il caricamento: {e}")

if __name__ == "__main__":
    carica_storico()
