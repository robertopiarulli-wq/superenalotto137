import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client
import re

# --- CONFIGURAZIONE ---
URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def formatta_data_ita(testo):
    mesi = {
        'Gennaio': '01', 'Febbraio': '02', 'Marzo': '03', 'Aprile': '04',
        'Maggio': '05', 'Giugno': '06', 'Luglio': '07', 'Agosto': '08',
        'Settembre': '09', 'Ottobre': '10', 'Novembre': '11', 'Dicembre': '12'
    }
    match = re.search(r'(\d{1,2})\s+(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s+(\d{4})', testo)
    if match:
        g, m, a = match.groups()
        return f"{a}-{mesi[m]}-{g.zfill(2)}"
    return None

def update_from_official():
    url = "https://www.superenalotto.it/archivio-estrazioni"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo tutti i blocchi che contengono "Concorso Nº"
        # Usiamo una ricerca testuale per essere sicuri
        blocchi = [div.find_parent() for div in soup.find_all(string=re.compile("Concorso.*Nº"))]
        
        for b in blocchi:
            testo_completo = b.get_text(separator=' ', strip=True)
            
            # 1. Estrazione Data
            data_iso = formatta_data_ita(testo_completo)
            
            # 2. Estrazione Numeri (cerchiamo sequenze di numeri isolati)
            # Prendiamo i primi 6 numeri che troviamo nel blocco
            numeri_potenziali = re.findall(r'\b\d{1,2}\b', testo_completo)
            # Pulizia: escludiamo il numero concorso (che è dopo "Nº")
            # Solitamente i numeri della combinazione sono dopo la data
            numeri = [int(n) for n in numeri_potenziali if 1 <= int(n) <= 90][-8:] # Prendiamo gli ultimi 8 (6+J+SS)
            sestina = numeri[:6]
            
            if data_iso and len(sestina) == 6:
                # 3. Verifica e Inserimento
                check = supabase.table("estrazioni").select("data_estrazione").eq("data_estrazione", data_iso).execute()
                
                if not check.data:
                    dati = {
                        "data_estrazione": data_iso,
                        "n1": sestina[0], "n2": sestina[1], "n3": sestina[2],
                        "n4": sestina[3], "n5": sestina[4], "n6": sestina[5]
                    }
                    supabase.table("estrazioni").insert(dati).execute()
                    print(f"✅ Inserito Concorso del {data_iso}: {sestina}")
                else:
                    print(f"⏩ Data {data_iso} già presente.")
                    
    except Exception as e:
        print(f"❌ Errore durante lo scraping: {e}")

if __name__ == "__main__":
    update_from_official()
