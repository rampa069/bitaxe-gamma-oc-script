import requests
import time
import csv
import statistics

# -----------------------
# Configuration
# -----------------------

# Replace this with your Bitaxe device's local network IP address
MINER_IP = "REPLACE_WITH_YOUR_BITAXE_IP"

# REST API endpoints exposed by AxeOS
PATCH_URL = f"http://{MINER_IP}/api/system"         # For setting frequency/voltage
STATS_URL = f"http://{MINER_IP}/api/system/info"    # For reading miner stats

# --- Overclocking Sweep Ranges ---

# Frequency sweep (MHz)
FREQ_START = 525         # Starting frequency
FREQ_END = 875           # Ending frequency
FREQ_STEP = 5            # Step size for frequency

# Core voltage sweep (mV)
CV_START = 1150          # Starting voltage
CV_MAX = 1250            # Max allowed voltage
CV_STEP = 10             # Step size for voltage

# --- Timing Controls ---

SETTLE_TIME = 180        # Wait time after each setting change (seconds)
MEASURE_DURATION = 180   # Duration to collect stats (seconds)
MEASURE_INTERVAL = 1     # Sampling interval (seconds)

# --- Confirmation Parameters ---

CONFIRM_DURATION = 60    # Time to confirm a stable drop (seconds)
CONFIRM_INTERVAL = 1     # Sampling interval during confirmation
CONFIRM_ATTEMPTS = 2     # Number of confirmations required

# --- Stability & Safety ---

TEMP_LIMIT = 60                  # Abort if temp exceeds this (°C)
HASHRATE_TOLERANCE = 0.90       # Allow drop of up to 10% from best
COEF_VARIATION_THRESHOLD = 0.12 # Reject unstable hashrate samples

# --- Output File ---
RESULTS_CSV = "bitaxe_tuning_results.csv"

# -----------------------
# Function Definitions
# -----------------------

def set_miner_settings(freq, cv):
    """Send PATCH request to update frequency and voltage on the miner."""
    payload = {
        "frequency": freq,
        "coreVoltage": cv,
        "autoFanSpeed": True,
        "flipScreen": True,
        "invertFanPolarity": True,
    }
    print(f"[INFO] Patching: freq={freq} MHz, cv={cv} mV...", flush=True)
    try:
        response = requests.patch(PATCH_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"[INFO] PATCH success: freq={freq}, cv={cv}", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] PATCH failed: freq={freq}, cv={cv}, error={e}", flush=True)

def get_miner_stats():
    """Send GET request to fetch current hashrate and temperature."""
    try:
        response = requests.get(STATS_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("hashRate", 0)), float(data.get("temp", 0))
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] GET {STATS_URL} failed: {e}", flush=True)
        return None, None

def measure_hashrate_stats(duration, interval):
    """
    Measure hashrate for a duration, sampling at the specified interval.
    Returns (average, stddev, last temp, aborted).
    """
    steps = duration // interval
    samples = []
    last_temp = 0

    print(f"[INFO] Measuring for {duration}s (interval: {interval}s)...", flush=True)
    for i in range(steps):
        time.sleep(interval)
        hr, temp = get_miner_stats()
        hr = hr if hr is not None else 0
        temp = temp if temp is not None else last_temp

        samples.append(hr)
        last_temp = temp

        if (i + 1) % 30 == 0 or i == steps - 1:
            print(f"  [DEBUG] Sample {i+1}/{steps}: hr={hr:.2f}, temp={temp:.2f}", flush=True)

        if temp >= TEMP_LIMIT:
            print(f"[WARNING] Temperature reached {temp}°C. Aborting...", flush=True)
            return None, None, temp, True

    avg = sum(samples) / len(samples)
    std = statistics.stdev(samples) if len(samples) > 1 else 0
    return avg, std, last_temp, False

def confirm_drop(threshold, attempts, freq, cv, best_hashrate):
    """Double-confirm hashrate drop before increasing voltage."""
    for attempt in range(1, attempts + 1):
        print(f"[INFO] Confirming drop ({attempt}/{attempts}) for freq={freq} MHz, cv={cv} mV...", flush=True)
        avg, std, temp, aborted = measure_hashrate_stats(CONFIRM_DURATION, CONFIRM_INTERVAL)
        if aborted:
            return None, None, True

        coef = (std / avg) if avg > 0 else 0
        print(f"[INFO] Confirm #{attempt}: avg={avg:.2f}, stdev={std:.2f}, coef={coef:.2f}", flush=True)

        if coef > COEF_VARIATION_THRESHOLD or avg >= best_hashrate * threshold:
            return avg, coef, False

    return avg, coef, False

# -----------------------
# Main Tuning Logic
# -----------------------

def main():
    print("[INFO] Starting Bitaxe overclock tuning...", flush=True)

    current_freq = FREQ_START
    current_cv = CV_START

    set_miner_settings(current_freq, current_cv)
    print(f"[INFO] Waiting {SETTLE_TIME}s to settle...", flush=True)
    time.sleep(SETTLE_TIME)
    
    baseline, std_base, temp, aborted = measure_hashrate_stats(MEASURE_DURATION, MEASURE_INTERVAL)
    if aborted or baseline is None:
        print("[INFO] Aborted: baseline failed or temp too high.", flush=True)
        return

    best_hashrate = baseline
    print(f"[INFO] Baseline hashrate: {baseline:.2f} H/s", flush=True)

    results = [{
        "frequency": current_freq,
        "coreVoltage": current_cv,
        "hashrate": baseline,
        "temperature": temp,
        "stdev": std_base
    }]

    for freq in range(FREQ_START + FREQ_STEP, FREQ_END + 1, FREQ_STEP):
        print(f"\n[INFO] Testing freq={freq} MHz at cv={current_cv} mV...", flush=True)
        set_miner_settings(freq, current_cv)
        print(f"[INFO] Waiting {SETTLE_TIME}s...", flush=True)
        time.sleep(SETTLE_TIME)

        avg, std, temp, aborted = measure_hashrate_stats(MEASURE_DURATION, MEASURE_INTERVAL)
        if aborted:
            break

        coef = (std / avg) if avg > 0 else 0
        print(f"[INFO] Result: avg={avg:.2f}, stdev={std:.2f}, coef={coef:.2f}", flush=True)

        # Check for possible undervoltage
        if coef <= COEF_VARIATION_THRESHOLD and avg < best_hashrate * HASHRATE_TOLERANCE:
            print("[INFO] Suspected undervoltage — confirming...", flush=True)
            confirm_avg, confirm_coef, confirm_abort = confirm_drop(HASHRATE_TOLERANCE, CONFIRM_ATTEMPTS, freq, current_cv, best_hashrate)

            if confirm_abort or confirm_avg is None:
                continue

            if confirm_avg < best_hashrate * HASHRATE_TOLERANCE:
                print("[INFO] Confirmed drop — increasing voltage...", flush=True)
                while current_cv < CV_MAX and confirm_avg < best_hashrate * HASHRATE_TOLERANCE:
                    current_cv += CV_STEP
                    print(f"  [INFO] Bumping voltage to {current_cv} mV", flush=True)
                    set_miner_settings(freq, current_cv)
                    time.sleep(SETTLE_TIME)

                    confirm_avg, std_temp, temp, aborted_voltage = measure_hashrate_stats(MEASURE_DURATION, MEASURE_INTERVAL)
                    if aborted_voltage:
                        break

                    confirm_avg, confirm_coef, confirm_abort = confirm_drop(HASHRATE_TOLERANCE, CONFIRM_ATTEMPTS, freq, current_cv, best_hashrate)
                    if confirm_abort or confirm_avg is None:
                        break

        results.append({
            "frequency": freq,
            "coreVoltage": current_cv,
            "hashrate": avg,
            "temperature": temp,
            "stdev": std
        })

        if coef <= COEF_VARIATION_THRESHOLD and avg > best_hashrate:
            best_hashrate = avg
            print(f"[INFO] New best hashrate: {best_hashrate:.2f}", flush=True)

        if temp >= TEMP_LIMIT:
            print("[INFO] Stopping — temp limit reached.", flush=True)
            break

    print("[INFO] Writing results to CSV...", flush=True)
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["frequency", "coreVoltage", "hashrate", "temperature", "stdev"])
        writer.writeheader()
        writer.writerows(results)

    print(f"[INFO] Done! Results saved to {RESULTS_CSV}", flush=True)

# -----------------------
# Entry Point
# -----------------------

if __name__ == "__main__":
    main()
