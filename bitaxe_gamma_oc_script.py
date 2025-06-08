import requests
import time
import csv
import statistics
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored terminal output
init(autoreset=True)

# -----------------------
# Configuration
# -----------------------

# Replace this with your Bitaxe device's local network IP address
MINER_IP = "192.168.5.206"

# REST API endpoints exposed by AxeOS
PATCH_URL = f"http://{MINER_IP}/api/system"         # For setting frequency/voltage
STATS_URL = f"http://{MINER_IP}/api/system/info"    # For reading miner stats

# --- Overclocking Sweep Ranges ---

# Frequency sweep (MHz)
FREQ_START = 525         # Starting frequency
FREQ_END   = 700           # Ending frequency
FREQ_STEP = 5            # Step size for frequency

# Core voltage sweep (mV)
CV_START = 1100          # Starting voltage
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

TEMP_LIMIT = 61                 # Abort if temp exceeds this (°C)
HASHRATE_TOLERANCE = 0.90       # Allow drop of up to 10% from best
COEF_VARIATION_THRESHOLD = 0.12 # Reject unstable hashrate samples

# --- Output File ---
RESULTS_CSV = "bitaxe_tuning_results.csv"

# --- Console Colors & Icons ---
COLORS = {
    'INFO': Fore.CYAN,
    'SUCCESS': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'DEBUG': Fore.MAGENTA,
    'RESULT': Fore.BLUE + Style.BRIGHT
}

ICONS = {
    'INFO': '📝',
    'SUCCESS': '✅',
    'WARNING': '⚠️',
    'ERROR': '❌',
    'DEBUG': '🔍',
    'RESULT': '📊',
    'PROGRESS': '⚡',
    'TEMP': '🌡️',
    'VOLTAGE': '⚡',
    'FREQUENCY': '📡'
}

def colored_print(message, msg_type='INFO', icon=True):
    """Print colored message with optional icon."""
    color = COLORS.get(msg_type, Fore.WHITE)
    icon_str = f"{ICONS.get(msg_type, '')} " if icon else ""
    print(f"{color}{icon_str}{message}{Style.RESET_ALL}", flush=True)

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
    colored_print(f"Patching: URL:{PATCH_URL} freq={freq} MHz, cv={cv} mV...", 'INFO')
    try:
        response = requests.patch(PATCH_URL, json=payload, timeout=10)
        response.raise_for_status()
        colored_print(f"PATCH success: freq={freq}, cv={cv}", 'SUCCESS')
    except requests.exceptions.RequestException as e:
        colored_print(f"PATCH failed: freq={freq}, cv={cv}, error={e}", 'ERROR')

def get_miner_stats():
    """Send GET request to fetch current hashrate and temperature."""
    try:
        response = requests.get(STATS_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("hashRate", 0)), float(data.get("temp", 0))
    except requests.exceptions.RequestException as e:
        colored_print(f"GET {STATS_URL} failed: {e}", 'ERROR')
        return None, None

def measure_hashrate_stats(duration, interval):
    """
    Measure hashrate for a duration, sampling at the specified interval.
    Returns (average, stddev, last temp, aborted).
    """
    steps = duration // interval
    samples = []
    last_temp = 0

    colored_print(f"Measuring for {duration}s (interval: {interval}s)...", 'INFO')
    for i in range(steps):
        time.sleep(interval)
        hr, temp = get_miner_stats()
        hr = hr if hr is not None else 0
        temp = temp if temp is not None else last_temp

        samples.append(hr)
        last_temp = temp

        if (i + 1) % 30 == 0 or i == steps - 1:
            colored_print(f"Sample {i+1}/{steps}: {ICONS['PROGRESS']} hr={hr:.2f}, {ICONS['TEMP']} temp={temp:.2f}", 'DEBUG')

        if temp >= TEMP_LIMIT:
            colored_print(f"Temperature reached {temp}°C. Aborting...", 'WARNING')
            return None, None, temp, True

    avg = sum(samples) / len(samples)
    std = statistics.stdev(samples) if len(samples) > 1 else 0
    return avg, std, last_temp, False

def confirm_drop(threshold, attempts, freq, cv, best_hashrate):
    """Double-confirm hashrate drop before increasing voltage."""
    for attempt in range(1, attempts + 1):
        colored_print(f"Confirming drop ({attempt}/{attempts}) for {ICONS['FREQUENCY']} freq={freq} MHz, {ICONS['VOLTAGE']} cv={cv} mV...", 'INFO')
        avg, std, temp, aborted = measure_hashrate_stats(CONFIRM_DURATION, CONFIRM_INTERVAL)
        if aborted:
            return None, None, True

        coef = (std / avg) if avg > 0 else 0
        colored_print(f"Confirm #{attempt}: avg={avg:.2f}, stdev={std:.2f}, coef={coef:.2f}", 'RESULT')

        if coef > COEF_VARIATION_THRESHOLD or avg >= best_hashrate * threshold:
            return avg, coef, False

    return avg, coef, False

# -----------------------
# Main Tuning Logic
# -----------------------

def main():
    colored_print("Starting Bitaxe overclock tuning...", 'INFO')

    current_freq = FREQ_START
    current_cv = CV_START

    set_miner_settings(current_freq, current_cv)
    colored_print(f"Waiting {SETTLE_TIME}s to settle...", 'INFO')
    time.sleep(SETTLE_TIME)
    
    baseline, std_base, temp, aborted = measure_hashrate_stats(MEASURE_DURATION, MEASURE_INTERVAL)
    if aborted or baseline is None:
        colored_print("Aborted: baseline failed or temp too high.", 'ERROR')
        return

    best_hashrate = baseline
    colored_print(f"Baseline hashrate: {baseline:.2f} H/s", 'SUCCESS')

    results = [{
        "frequency": current_freq,
        "coreVoltage": current_cv,
        "hashrate": baseline,
        "temperature": temp,
        "stdev": std_base
    }]

    for freq in range(FREQ_START + FREQ_STEP, FREQ_END + 1, FREQ_STEP):
        colored_print(f"\nTesting {ICONS['FREQUENCY']} freq={freq} MHz at {ICONS['VOLTAGE']} cv={current_cv} mV...", 'INFO')
        set_miner_settings(freq, current_cv)
        colored_print(f"Waiting {SETTLE_TIME}s...", 'INFO')
        time.sleep(SETTLE_TIME)

        avg, std, temp, aborted = measure_hashrate_stats(MEASURE_DURATION, MEASURE_INTERVAL)
        if aborted:
            break

        coef = (std / avg) if avg > 0 else 0
        colored_print(f"Result: avg={avg:.2f}, stdev={std:.2f}, coef={coef:.2f}", 'RESULT')

        # Check for possible undervoltage
        if coef <= COEF_VARIATION_THRESHOLD and avg < best_hashrate * HASHRATE_TOLERANCE:
            colored_print("Suspected undervoltage — confirming...", 'WARNING')
            confirm_avg, confirm_coef, confirm_abort = confirm_drop(HASHRATE_TOLERANCE, CONFIRM_ATTEMPTS, freq, current_cv, best_hashrate)

            if confirm_abort or confirm_avg is None:
                continue

            if confirm_avg < best_hashrate * HASHRATE_TOLERANCE:
                colored_print("Confirmed drop — increasing voltage...", 'WARNING')
                while current_cv < CV_MAX and confirm_avg < best_hashrate * HASHRATE_TOLERANCE:
                    current_cv += CV_STEP
                    colored_print(f"Bumping {ICONS['VOLTAGE']} voltage to {current_cv} mV", 'INFO')
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
            colored_print(f"New best hashrate: {best_hashrate:.2f}", 'SUCCESS')

        if temp >= TEMP_LIMIT:
            colored_print("Stopping — temp limit reached.", 'WARNING')
            break

    colored_print("Writing results to CSV...", 'INFO')
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["frequency", "coreVoltage", "hashrate", "temperature", "stdev"])
        writer.writeheader()
        writer.writerows(results)

    colored_print(f"Done! Results saved to {RESULTS_CSV}", 'SUCCESS')

# -----------------------
# Entry Point
# -----------------------

if __name__ == "__main__":
    main()
