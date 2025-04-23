# Bitaxe Gamma Overclock Script

This Python script automates overclocking for the Bitaxe Gamma 601 running AxeOS.  
It sweeps through frequency and core voltage combinations while monitoring hashrate, 
stability, and temperature — helping you tune your miner safely and effectively.

> ⚙️ While this script is preconfigured with voltage and frequency ranges optimized for the Gamma 601,
> it can also be adapted for other Bitaxe models like the Supra or Ultra — just update the config section accordingly.

---

## 🔧 What It Does

- Adjusts core voltage (mV) and frequency (MHz) in defined increments
- Measures hashrate and temperature via the AxeOS local REST API
- Detects instability using standard deviation and coefficient of variation
- Performs confirmation checks before increasing voltage
- Stops automatically if temperature exceeds a safe limit
- Logs all results to a clean CSV file for review

---

## ⚙️ Requirements

- Python 3.6 or newer
- `requests` module (`pip install requests`)
- A Bitaxe running AxeOS, accessible on your local network

Tested on:
- Ubuntu/Linux
- Windows Subsystem for Linux (WSL)
- macOS (works with any terminal that supports Python)

---

## 🚀 Quick Start

### Option 1: Clone This Repo
```bash
git clone https://github.com/terminally-challenged/bitaxe-gamma-oc-script.git
cd bitaxe-gamma-oc-script
```

### Option 2: Manual Download
- Click the green **Code** button
- Select **Download ZIP**
- Extract the contents and open the script in any text editor (VS Code, Notepad, nano, vim, etc.)

---

## 🛠 Setup Instructions

1. Open the script and update the IP address for your Bitaxe:
   ```python
   MINER_IP = "REPLACE_WITH_YOUR_BITAXE_IP"
   # Example: MINER_IP = "192.168.1.100"
   ```

2. (Optional) You can customize:
   - Frequency range: `FREQ_START`, `FREQ_END`
   - Core voltage range: `CV_START`, `CV_MAX`
   - Temperature safety limit (e.g., 60°C)
   - Stability thresholds

3. Run the script:
   ```bash
   python3 bitaxe_oc_script.py
   ```

4. Allow a couple of hours for a full sweep. Results will be saved in:
   ```
   bitaxe_tuning_results.csv
   ```

This file will give you a solid understanding of your most efficient and stable configuration — if the final result isn't already the best one.

---

## 📝 Notes

1. Make sure you’re on the correct network and using the correct IP address!
2. You can safely exit the script at any time using `Ctrl+C`
3. If using a board **other than Gamma 601**, update the frequency and voltage ranges appropriately in the config section.

---

⚠️ **Disclaimer**: Due to the nature of the ASIC lottery, results may vary slightly between 
units — even with identical models. Some fine-tuning may be required to dial in the best results 
for your specific hardware. I've personally tested and adjusted parameters across multiple 
Gamma 601's to find what works best.

---

## 🤝 Contributing

Pull requests are welcome!  
If you find a bug, have feedback, or want to improve the script — open an issue or submit a PR.

---

## ⚡ License

MIT License. Use at your own risk.
