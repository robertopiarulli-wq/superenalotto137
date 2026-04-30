import os
import requests
import pandas as pd
from supabase import create_client

URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def update_supabase():
    # Usiamo una sorgente alternativa affidabile o verifichiamo la corrente
    url = "https://raw.githubusercontent.com/michelecoscia/SuperEnalotto/master/data/history.csv"
    
    try:
        df = pd.read_csv(url)
        print("Colonne trovate nel CSV:", df.columns.tolist())
        
        # Prendiamo le ultime 10 righe
        latest = df.tail(10)
        
        for _, row in latest.iterrows():
            # MAPPATURA COLONNE: Adattiamo i nomi del CSV a quelli di Supabase
            # Se il CSV ha 'date', 'n1', etc., usali qui:
            dati = {
                "data_estrazione": str(row['date']), 
                "n1": int(row['n1']),
                "n2": int(row['n2']),
                "n3": int(row['n3']),
                "n4": int(row['n4']),
                "n5": int(row['n5']),
                "n6": int(row['n6'])
            }
            
            res = supabase.table("estrazioni").insert(dati).execute()
            print(f"Inserito: {dati['data_estrazione']}")
            
    except Exception as e:
        print(f"ERRORE CRITICO: {e}")

if __name__ == "__main__":
    update_supabase()
