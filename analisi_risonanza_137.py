import os
import pandas as pd
import numpy as np
from supabase import create_client
import json
from itertools import combinations
from sklearn.cluster import KMeans

# --- CONFIGURAZIONE ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def calcola_rugosita(serie):
    """Calcola la regolarità statistica dei ritardi."""
    if len(serie) < 2: return 0
    return np.std(np.diff(serie))

def estrai_features(sestina):
    """ALGORITMO 3: Estrazione parametri di 'forma' per il clustering."""
    s = sorted(sestina)
    return [
        np.mean(s),                # Baricentro della sestina
        np.std(s),                 # Dispersione (concentrata o espansa)
        sum(1 for x in s if x % 2 == 0), # Rapporto Pari/Dispari
        max(s) - min(s)            # Range totale occupato
    ]

def esegui_analisi_trinita():
    # 1. Recupero TUTTE le estrazioni per Baseline e Clustering
    response_all = supabase.table("estrazioni").select("*").order("data_estrazione", desc=True).execute()
    df_all = pd.DataFrame(response_all.data)
    colonne = ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']
    
    estrazioni_full = df_all[colonne].values.tolist()
    estrazioni_137 = estrazioni_full[:137]
    total_estrazioni = len(estrazioni_full)

    # --- ALGORITMO 1: RISONANZA INDIVIDUALE (NOBILTÀ) ---
    risultati_ind = []
    for num in range(1, 91):
        uscite_137 = [i for i, estra in enumerate(estrazioni_137) if num in estra]
        if len(uscite_137) > 1:
            ritardi = np.diff(uscite_137)
            rugosita = calcola_rugosita(ritardi)
            # Indice di Risonanza: premia frequenza e regolarità nelle 137
            risonanza = len(uscite_137) / (rugosita + 1)
            risultati_ind.append({'numero': int(num), 'risonanza': float(risonanza)})
    
    classifica = sorted(risultati_ind, key=lambda x: x['risonanza'], reverse=True)
    pool_eletto = [n['numero'] for n in classifica[:22]] # Pool di 22 numeri nobili

    # --- ALGORITMO 2: ASSOCIAZIONI E RITARDI RELAZIONALI ---
    coppie_storiche = {}
    coppie_137 = {}

    for estra in estrazioni_full:
        nobili = [n for n in estra if n in pool_eletto]
        for c in combinations(sorted(nobili), 2):
            coppie_storiche[c] = coppie_storiche.get(c, 0) + 1

    for estra in estrazioni_137:
        nobili = [n for n in estra if n in pool_eletto]
        for c in combinations(sorted(nobili), 2):
            coppie_137[c] = coppie_137.get(c, 0) + 1

    nuclei_accelerati = []
    nuclei_ritardo = []

    for coppia, freq_s in coppie_storiche.items():
        f_media_storica = freq_s / total_estrazioni
        f_attuale = coppie_137.get(coppia, 0) / 137
        
        # Accelerazione: +50% rispetto allo storico
        if f_attuale > (f_media_storica * 1.5):
            nuclei_accelerati.append({'coppia': list(coppia), 'punteggio': f_attuale})
        # Ritardo Relazionale: -70% rispetto allo storico
        elif f_attuale < (f_media_storica * 0.3) and f_media_storica > 0.05:
            nuclei_ritardo.append({'coppia': list(coppia), 'ritardo': f_media_storica})

    nuclei_acc_final = [n['coppia'] for n in sorted(nuclei_accelerati, key=lambda x: x['punteggio'], reverse=True)[:5]]
    nuclei_rit_final = [n['coppia'] for n in sorted(nuclei_ritardo, key=lambda x: x['ritardo'], reverse=True)[:5]]

    # --- ALGORITMO 3: CLUSTERING K-MEANS (FORMA DEL MOMENTO) ---
    # Creiamo 3 cluster basati sulle caratteristiche geometriche delle estrazioni
    features = [estrai_features(e) for e in estrazioni_full]
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10).fit(features)
    
    # Identifichiamo il cluster dominante nelle ultime 3 estrazioni
    recent_clusters = kmeans.predict([estrai_features(e) for e in estrazioni_full[:3]])
    cluster_attivo = int(np.bincount(recent_clusters).argmax())

    # --- SALVATAGGIO INTEGRATO PER LA DASHBOARD ---
    output = {
        "pool_eletto": pool_eletto,
        "nuclei_accelerati": nuclei_acc_final,
        "nuclei_ritardo": nuclei_rit_final,
        "cluster_attivo": cluster_attivo
    }
    
    with open("cardini_scientifici.json", "w") as f:
        json.dump(output, f)
    
    print(f"✅ Trinità Algoritmica completata su {total_estrazioni} estrazioni.")
    print(f"🚀 Nuclei Accelerati: {nuclei_acc_final}")
    print(f"📊 Cluster di Forma Attivo: {cluster_attivo}")

if __name__ == "__main__":
    esegui_analisi_trinita()
