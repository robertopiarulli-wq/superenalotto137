import os
import pandas as pd
import numpy as np
from supabase import create_client
import json
from itertools import combinations

# --- CONFIGURAZIONE ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def calcola_rugosita(serie):
    if len(serie) < 2: return 0
    return np.std(np.diff(serie))

def esegui_analisi_totale_incrociata():
    # 1. Recupero TUTTE le estrazioni per la Baseline Storica
    response_all = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    df_all = pd.DataFrame(response_all.data)
    colonne = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    
    # Dati storici e Focus 137
    estrazioni_full = df_all[colonne].values.tolist()
    estrazioni_137 = estrazioni_full[:137]
    total_estrazioni = len(estrazioni_full)

    # 2. Analisi Risonanza Individuale (Nobiltà nelle ultime 137)
    risultati_ind = []
    for num in range(1, 91):
        uscite_137 = [i for i, estra in enumerate(estrazioni_137) if num in estra]
        if len(uscite_137) > 1:
            ritardi = np.diff(uscite_137)
            rugosita = calcola_rugosita(ritardi)
            # Indice di risonanza attuale
            risonanza = len(uscite_137) / (rugosita + 1)
            risultati_ind.append({'numero': int(num), 'risonanza': float(risonanza)})
    
    classifica = sorted(risultati_ind, key=lambda x: x['risonanza'], reverse=True)
    pool_eletto = [n['numero'] for n in classifica[:22]]

    # 3. Frequent Pattern Mining: Storico vs Attuale
    coppie_storiche = {}
    coppie_137 = {}

    # Calcolo frequenze storiche (Baseline)
    for estra in estrazioni_full:
        nobili = [n for n in estra if n in pool_eletto]
        for c in combinations(sorted(nobili), 2):
            coppie_storiche[c] = coppie_storiche.get(c, 0) + 1

    # Calcolo frequenze attuali (Focus 137)
    for estra in estrazioni_137:
        nobili = [n for n in estra if n in pool_eletto]
        for c in combinations(sorted(nobili), 2):
            coppie_137[c] = coppie_137.get(c, 0) + 1

    # 4. Individuazione Accelerazioni e Ritardi
    nuclei_accelerati = []
    nuclei_ritardo = []

    for coppia, freq_s in coppie_storiche.items():
        f_media_storica = freq_s / total_estrazioni
        f_attuale = coppie_137.get(coppia, 0) / 137
        
        # Indice di Sbilanciamento
        # Se esce più della media storica -> Accelerazione
        # Se esce meno del 30% della media storica -> Ritardo Relazionale
        if f_attuale > (f_media_storica * 1.5):
            nuclei_accelerati.append({'coppia': list(coppia), 'punteggio': f_attuale})
        elif f_attuale < (f_media_storica * 0.3) and f_media_storica > 0.05:
            nuclei_ritardo.append({'coppia': list(coppia), 'ritardo': f_media_storica})

    # Ordinamento e selezione
    nuclei_accelerati = [n['coppia'] for n in sorted(nuclei_accelerati, key=lambda x: x['punteggio'], reverse=True)[:5]]
    nuclei_ritardo = [n['coppia'] for n in sorted(nuclei_ritardo, key=lambda x: x['ritardo'], reverse=True)[:5]]

    # 5. Salvataggio Strutturato per la Dashboard
    output = {
        "pool_eletto": pool_eletto,
        "nuclei_accelerati": nuclei_accelerati,
        "nuclei_ritardo": nuclei_ritardo
    }
    
    with open("cardini_scientifici.json", "w") as f:
        json.dump(output, f)
    
    print(f"✅ Analisi completata su {total_estrazioni} estrazioni.")
    print(f"🚀 Nuclei in Accelerazione: {nuclei_accelerati}")
    print(f"⏳ Nuclei in Ritardo Relazionale: {nuclei_ritardo}")

if __name__ == "__main__":
    esegui_analisi_totale_incrociata()
