import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURAZIONE ---
URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def formatta_data(testo_data):
    """Converte '30 Aprile 2026' in '2026-04-30'"""
    mesi = {
        'Gennaio': '01', 'Febbraio': '02', 'Marzo': '03', 'Aprile': '04',
        'Maggio': '05', 'Giugno': '06', 'Luglio': '07', 'Agosto': '08',
        'Settembre': '09', 'Ottobre': '10', 'Novembre': '11', 'Dicembre': '12'
    }
    parti = testo_data.split()
    giorno = parti[0].zfill(2)
    mese = mesi.get(parti[1], '01')
    anno = parti[2]
    return f"{anno}-{mese}-{giorno}"

def update_from_official():
    url_sito = "https://www.superenalotto.it/archivio-estrazioni"
    headers = {'User-Agent': 'Mozilla/5.0'} # Per evitare blocchi dal server
    
    try:
        response = requests.get(url_sito, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Troviamo tutti i blocchi dei concorsi
        concorsi = soup.find_all('div', class_='concorso') # O la classe specifica del sito
        
        # Se la struttura è una tabella o lista, iteriamo sui blocchi
        # Basandoci sul testo che hai fornito, cerchiamo i div o righe rilevanti
        estrazioni_trovate = []
        
        # ESEMPIO DI LOGICA DI SCRAPING BASATA SUL TUO TESTO:
        # Cerchiamo le righe che contengono "Concorso Nº"
        items = soup.select('.archive-table-row') # Selettore ipotetico basato su standard
        
        for item in items:
            try:
                testo_concorso = item.select_one('.date').text # "30 Aprile 2026"
                data_iso = formatta_data(testo_concorso)
                
                # Estraiamo i 6 numeri (solitamente sono in una lista <ul> o span)
                numeri = [int(n.text) for n in item.select('.ball')[:6]]
                
                if len(numeri) == 6:
                    estrazioni_trovate.append({
                        "data_estrazione": data_iso,
                        "n1": numeri[0], "n2": numeri[1], "n3": numeri[2],
                        "n4": numeri[3], "n5": numeri[4], "n6": numeri[5]
                    })
            except:
                continue

        # --- INSERIMENTO NEL DATABASE ---
        for estrazione in estrazioni_trovate:
            # Verifica esistenza
            check = supabase.table("estrazioni").select("data_estrazione").eq("data_estrazione", estrazione["data_estrazione"]).execute()
            
            if not check.data:
                supabase.table("estrazioni").insert(estrazione).execute()
                print(f"✅ Inserita estrazione del {estrazione['data_estrazione']}")
            else:
                print(f"⏩ {estrazione['data_estrazione']} già a sistema.")

    except Exception as e:
        print(f"❌ Errore Scraping: {e}")

if __name__ == "__main__":
    update_from_official()
