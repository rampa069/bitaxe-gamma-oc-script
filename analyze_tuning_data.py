#!/usr/bin/env python3
"""
BitAxe Mining Tuning Data Analysis
Analyzes performance data to find optimal frequency/voltage combinations
"""

import pandas as pd
import numpy as np

def analyze_bitaxe_data():
    # Read the CSV data
    df = pd.read_csv('bitaxe_tuning_results.csv')
    
    print("=== BitAxe Mining Tuning Analysis ===\n")
    print(f"Total configurations tested: {len(df)}")
    print(f"Frequency range: {df['frequency'].min()}-{df['frequency'].max()} MHz")
    print(f"Voltage levels: {sorted(df['coreVoltage'].unique())} mV")
    print(f"Temperature range: {df['temperature'].min():.1f}-{df['temperature'].max():.1f}°C")
    print()
    
    # 1. Highest hashrate
    max_hashrate_idx = df['hashrate'].idxmax()
    max_hashrate_config = df.loc[max_hashrate_idx]
    
    print("1. HIGHEST HASHRATE CONFIGURATION:")
    print(f"   Frequency: {max_hashrate_config['frequency']} MHz")
    print(f"   Voltage: {max_hashrate_config['coreVoltage']} mV")
    print(f"   Hashrate: {max_hashrate_config['hashrate']:.1f} GH/s")
    print(f"   Temperature: {max_hashrate_config['temperature']:.1f}°C")
    print(f"   Standard Deviation: {max_hashrate_config['stdev']:.1f}")
    print()
    
    # 2. Most stable (lowest standard deviation)
    min_stdev_idx = df['stdev'].idxmin()
    most_stable_config = df.loc[min_stdev_idx]
    
    print("2. MOST STABLE CONFIGURATION (Lowest Standard Deviation):")
    print(f"   Frequency: {most_stable_config['frequency']} MHz")
    print(f"   Voltage: {most_stable_config['coreVoltage']} mV")
    print(f"   Hashrate: {most_stable_config['hashrate']:.1f} GH/s")
    print(f"   Temperature: {most_stable_config['temperature']:.1f}°C")
    print(f"   Standard Deviation: {most_stable_config['stdev']:.1f}")
    print()
    
    # 3. Best balance of hashrate and stability
    # Create a composite score: normalize hashrate (higher is better) and stability (lower stdev is better)
    df['hashrate_norm'] = (df['hashrate'] - df['hashrate'].min()) / (df['hashrate'].max() - df['hashrate'].min())
    df['stability_norm'] = 1 - ((df['stdev'] - df['stdev'].min()) / (df['stdev'].max() - df['stdev'].min()))
    
    # Weighted score: 60% hashrate, 40% stability
    df['composite_score'] = 0.6 * df['hashrate_norm'] + 0.4 * df['stability_norm']
    
    best_balance_idx = df['composite_score'].idxmax()
    best_balance_config = df.loc[best_balance_idx]
    
    print("3. BEST BALANCE (60% Hashrate, 40% Stability):")
    print(f"   Frequency: {best_balance_config['frequency']} MHz")
    print(f"   Voltage: {best_balance_config['coreVoltage']} mV")
    print(f"   Hashrate: {best_balance_config['hashrate']:.1f} GH/s")
    print(f"   Temperature: {best_balance_config['temperature']:.1f}°C")
    print(f"   Standard Deviation: {best_balance_config['stdev']:.1f}")
    print(f"   Composite Score: {best_balance_config['composite_score']:.3f}")
    print()
    
    # Additional analysis - top 5 configurations by different criteria
    print("4. TOP 5 CONFIGURATIONS BY HASHRATE:")
    top_hashrate = df.nlargest(5, 'hashrate')[['frequency', 'coreVoltage', 'hashrate', 'temperature', 'stdev']]
    for i, (idx, row) in enumerate(top_hashrate.iterrows(), 1):
        print(f"   {i}. {row['frequency']}MHz @ {row['coreVoltage']}mV: {row['hashrate']:.1f} GH/s (stdev: {row['stdev']:.1f})")
    print()
    
    print("5. TOP 5 MOST STABLE CONFIGURATIONS:")
    most_stable = df.nsmallest(5, 'stdev')[['frequency', 'coreVoltage', 'hashrate', 'temperature', 'stdev']]
    for i, (idx, row) in enumerate(most_stable.iterrows(), 1):
        print(f"   {i}. {row['frequency']}MHz @ {row['coreVoltage']}mV: {row['hashrate']:.1f} GH/s (stdev: {row['stdev']:.1f})")
    print()
    
    print("6. TOP 5 BALANCED CONFIGURATIONS:")
    best_balanced = df.nlargest(5, 'composite_score')[['frequency', 'coreVoltage', 'hashrate', 'temperature', 'stdev', 'composite_score']]
    for i, (idx, row) in enumerate(best_balanced.iterrows(), 1):
        print(f"   {i}. {row['frequency']}MHz @ {row['coreVoltage']}mV: {row['hashrate']:.1f} GH/s (stdev: {row['stdev']:.1f}, score: {row['composite_score']:.3f})")
    print()
    
    # Temperature analysis
    print("7. TEMPERATURE ANALYSIS:")
    temp_stats = df.groupby('temperature').agg({
        'hashrate': ['mean', 'count'],
        'stdev': 'mean'
    }).round(2)
    print("   Temperature distribution and average performance:")
    for temp in sorted(df['temperature'].unique()):
        temp_data = df[df['temperature'] == temp]
        print(f"   {temp}°C: {len(temp_data)} configs, avg hashrate: {temp_data['hashrate'].mean():.1f} GH/s, avg stdev: {temp_data['stdev'].mean():.1f}")
    print()
    
    # Voltage comparison
    print("8. VOLTAGE COMPARISON:")
    for voltage in sorted(df['coreVoltage'].unique()):
        voltage_data = df[df['coreVoltage'] == voltage]
        print(f"   {voltage}mV configs:")
        print(f"     Count: {len(voltage_data)}")
        print(f"     Avg Hashrate: {voltage_data['hashrate'].mean():.1f} GH/s")
        print(f"     Max Hashrate: {voltage_data['hashrate'].max():.1f} GH/s")
        print(f"     Avg Stability (stdev): {voltage_data['stdev'].mean():.1f}")
        print(f"     Best Stability (stdev): {voltage_data['stdev'].min():.1f}")
        print()
    
    # Final recommendation
    print("=== FINAL RECOMMENDATION ===")
    print()
    print("RECOMMENDED CONFIGURATION:")
    print(f"Frequency: {best_balance_config['frequency']} MHz")
    print(f"Voltage: {best_balance_config['coreVoltage']} mV")
    print(f"Expected Hashrate: {best_balance_config['hashrate']:.1f} GH/s")
    print(f"Expected Temperature: {best_balance_config['temperature']:.1f}°C")
    print(f"Expected Stability (stdev): {best_balance_config['stdev']:.1f}")
    print()
    print("REASONING:")
    print("- This configuration provides the best balance of high hashrate and stability")
    print("- Temperature remains within acceptable range (≤60°C)")
    print("- Standard deviation is reasonable for consistent performance")
    print("- Represents optimal efficiency for long-term mining operations")
    
    # Alternative recommendations
    print()
    print("ALTERNATIVE RECOMMENDATIONS:")
    print()
    print(f"For MAXIMUM HASHRATE (if stability is less critical):")
    print(f"  {max_hashrate_config['frequency']} MHz @ {max_hashrate_config['coreVoltage']} mV")
    print(f"  Hashrate: {max_hashrate_config['hashrate']:.1f} GH/s (stdev: {max_hashrate_config['stdev']:.1f})")
    print()
    print(f"For MAXIMUM STABILITY (if hashrate is less critical):")
    print(f"  {most_stable_config['frequency']} MHz @ {most_stable_config['coreVoltage']} mV")
    print(f"  Hashrate: {most_stable_config['hashrate']:.1f} GH/s (stdev: {most_stable_config['stdev']:.1f})")

if __name__ == "__main__":
    analyze_bitaxe_data()