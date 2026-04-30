import os
import requests
import pandas as pd
from supabase import create_client

# 1. Configurazione Credenziali (GitHub le passerà tramite l'ambiente)
URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def fetch_latest_draws():
    """
    Recupera le estrazioni da un archivio CSV affidabile.
    Usiamo un link pubblico che contiene lo storico aggiornato.
    """
    # Esempio di fonte CSV (da verificare/cambiare con la tua preferita)
    # In alternativa si può puntare a un archivio statico che aggiornano regolarmente
    url = "https://raw.githubusercontent.com/michelecoscia/SuperEnalotto/master/data/history.csv" 
    
    try:
        response = requests.get(url)
        with open("temp.csv", "wb") as f:
            f.write(response.content)
        
        # Leggiamo il CSV (adattando i nomi delle colonne)
        df = pd.read_csv("temp.csv")
        
        # Supponiamo che il CSV abbia colonne: date, n1, n2, n3, n4, n5, n6
        # Trasformiamo l'output per Supabase
        return df.tail(10) # Prendiamo le ultime 10 per sicurezza
    except Exception as e:
        print(f"Errore nel recupero dati: {e}")
        return None

def update_supabase():
    df_latest = fetch_latest_draws()
    
    if df_latest is not None:
        for _, row in df_latest.iterrows():
            dati = {
                "data_estrazione": row['date'], # Assicurati che il formato sia YYYY-MM-DD
                "n1": int(row['n1']),
                "n2": int(row['n2']),
                "n3": int(row['n3']),
                "n4": int(row['n4']),
                "n5": int(row['n5']),
                "n6": int(row['n6'])
            }
            
            # L'id del concorso serve per evitare duplicati (Upsert o Try-Except)
            try:
                supabase.table("estrazioni").insert(dati).execute()
                print(f"Inserita estrazione del {row['date']}")
            except:
                print(f"Estrazione del {row['date']} già presente.")

if __name__ == "__main__":
    update_supabase()
