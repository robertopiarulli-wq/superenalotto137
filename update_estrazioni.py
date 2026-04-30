import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# --- CONFIGURAZIONE ---
URL_SUPABASE = os.environ.get("SUPABASE_URL")
KEY_SUPABASE = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

def formatta_data_italiana(testo):
    mesi = {
        'Gennaio': '01', 'Febbraio': '02', 'Marzo': '03', 'Aprile': '04',
        'Maggio': '05', 'Giugno': '06', 'Luglio': '07', 'Agosto': '08',
        'Settembre': '09', 'Ottobre': '10', 'Novembre': '11', 'Dicembre': '12'
    }
    parti = testo.replace("Concorso", "").split()
    # Cerchiamo l'anno (es: 2026) e il mese
    giorno = next(p for p in parti if p.isdigit() and len(p) <= 2).zfill(2)
    anno = next(p for p in parti if p.isdigit() and len(p) == 4)
    mese_nome = next(m for m in mesi if m in testo)
    return f"{anno}-{mesi[mese_nome]}-{giorno}"

def update_from_official():
    url_sito = "https://www.superenalotto.it/archivio-estrazioni"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url_sito, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo le righe della tabella o i blocchi estrazione
        # I selettori seguenti puntano ai numeri nelle palline
        blocchi = soup.find_all('tr') # Molte estrazioni sono in tabelle <tr>
        
        for riga in blocchi:
            testo = riga.get_text(strip=True)
            if "Concorso" in testo:
                # Estrazione numeri: cerchiamo i div o span con classe che contiene 'ball'
                balls = riga.select('.ball, .smallBall, .ball-six') 
                numeri = [int(b.text) for b in balls if b.text.isdigit()][:6]
                
                if len(numeri) == 6:
                    data_raw = riga.find_previous('h2') or riga.select_one('.date')
                    # Se non trova la data specifica, cerchiamo nel testo della riga
                    data_iso = formatta_data_italiana(testo)
                    
                    dati = {
                        "data_estrazione": data_iso,
                        "n1": numeri[0], "n2": numeri[1], "n3": numeri[2],
                        "n4": numeri[3], "n5": numeri[4], "n6": numeri[5]
                    }
                    
                    # Controllo ed Inserimento
                    check = supabase.table("estrazioni").select("data_estrazione").eq("data_estrazione", data_iso).execute()
                    if not check.data:
                        supabase.table("estrazioni").insert(dati).execute()
                        print(f"✅ Inserito: {data_iso} -> {numeri}")
                    else:
                        print(f"⏩ Già presente: {data_iso}")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    update_from_official()
