import os
import json
import numpy as np
import pandas as pd
from scipy.signal import lombscargle
from supabase import create_client

def run_analysis():
    # Caricamento credenziali da environment (GitHub Secrets)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(url, key)

    # 1. Fetch dati
    res = supabase.table("il_tuo_tavolo").select("n1,n2,n3,n4,n5,n6").order("id").execute()
    df = pd.DataFrame(res.data)
    data = df.values.flatten().astype(float)
    
    # Normalizzazione (Z-score) per evitare bias di ampiezza
    data_norm = (data - np.mean(data)) / np.std(data)
    t = np.arange(len(data))

    # 2. Analisi Spettrale focalizzata sul lag 137
    # Investighiamo un intorno del lag per vedere se il picco è centrato
    target_lag = 137
    periods = np.linspace(target_lag - 20, target_lag + 20, 500)
    freqs = 2 * np.pi / periods
    pgram = lombscargle(t, data_norm, freqs, normalization='psd')

    # 3. Test di significatività (Surrogati rapido)
    n_surrogates = 50
    max_noise = []
    for _ in range(n_surrogates):
        surr_data = np.random.permutation(data_norm)
        surr_pgram = lombscargle(t, surr_data, freqs, normalization='psd')
        max_noise.append(np.max(surr_pgram))
    
    threshold = float(np.percentile(max_noise, 95))
    peak_power = float(np.max(pgram))
    peak_period = float(periods[np.argmax(pgram)])

    # 4. Preparazione JSON
    results = {
        "last_updated": pd.Timestamp.now().isoformat(),
        "total_points": len(data),
        "target_lag": target_lag,
        "peak_found_at": round(peak_period, 2),
        "peak_power": round(peak_power, 4),
        "noise_threshold_95": round(threshold, 4),
        "has_structure": peak_power > threshold,
        "is_137_prominent": abs(peak_period - 137) < 0.5 and peak_power > threshold
    }

    with open("analysis_results.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_analysis()
