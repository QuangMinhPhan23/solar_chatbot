import pandas as pd
import numpy as np

def preprocess_data():
    data = pd.read_csv('5-Site_DG-PV1-DB-DG-M1A.csv')

    # Step 1: Remove negative power values
    data = data[data['Active_Power'] >= 0]

    # Step 2: Filter nighttime generation (irradiance < 10 W/m²)
    data = data[data['Global_Horizontal_Radiation'] >= 10]
    data = data[data['Pyranometer_1'] >= 10]
    # Step 3: Handle missing values (50k missing, < 5% total, fine!)
    data.dropna(inplace=True)

    # Step 4: Remove duplicate timestamps
    data = data.drop_duplicates(subset=['timestamp'])

    # Step 5: Remove temperature outliers
    lower_percentile = 1
    upper_percentile = 99

    lower_threshold = np.percentile(data['Weather_Temperature_Celsius'].dropna(), lower_percentile)
    upper_threshold = np.percentile(data['Weather_Temperature_Celsius'].dropna(), upper_percentile)

    data = data[(data['Weather_Temperature_Celsius'] >= lower_threshold) &
                (data['Weather_Temperature_Celsius'] <= upper_threshold)]
    data = data[
        (data['Temperature_Probe_1'].between(0, 120)) &
        (data['Temperature_Probe_2'].between(0, 120)) &
        (data['Weather_Temperature_Celsius'].between(-5, 45))
    ]

    # ensure timestamp is in datetime format
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    # data = data.set_index('timestamp')
    # # Trim data to only include rows from 2024-01-01 to 2025-08-31
    data = data[(data['timestamp'] >= '2024-01-01') & (data['timestamp'] <= '2025-08-31')]
    # Energy = Power * Time (5 minutes = 5/60 hours)
    data['Energy_kWh'] = data['Active_Power'] * (5 / 60)
    return data

freq_map = {
        'hourly': 'h',
        'daily': 'D',
        'monthly': 'M',
        'yearly': 'Y'
    }

def calculate_total_energy(data, aggregation='default'):
    """
    Calculate cumulative AC energy output for the specified period.

    Parameters:
        data (DataFrame): The input data containing 'timestamp' and 'Active_Power'.
        aggregation (str): Aggregation level - 'default', 'hourly', 'daily', 'monthly', 'yearly'.

    Returns:
        float or DataFrame: Total energy in kWh, with breakdown if requested.
    """
    if aggregation == 'default':
        total_energy = data['Energy_kWh'].sum()
        return round(total_energy, 2)
    freq = freq_map[aggregation]
    return data['Energy_kWh'].resample(freq).sum().round(2)

def calculate_specific_yield(data, P_STC=1058.4, aggregation='default'):
    """
    Calculate Specific Yield (kWh/kWp) for the specified period.

    Parameters:
        data (DataFrame): The input data containing 'timestamp' and 'Active_Power'.
        installed_capacity_kWp (float): The installed capacity of the system in kWp.
        aggregation (str): Aggregation level - 'default', 'hourly', 'daily', 'monthly', 'yearly'.

    Returns:
        float or DataFrame: Specific Yield (kWh/kWp) for the time period, with breakdown if requested.
    """
    result = calculate_total_energy(data, aggregation) / P_STC
    if isinstance(result, (float, int)):
        return round(result, 2)
    elif hasattr(result, 'round'):
        return result.round(2)
    return result

def calculate_temperature_corrected_pr(data, P_STC=1058.4, gamma=-0.004, aggregation='default'):
    """
    Calculate Temperature-Corrected Performance Ratio (PR) for the specified period.

    Parameters:
        data (DataFrame): Must include 'timestamp', 'Active_Power',
                          'Global_Horizontal_Radiation', and 'Weather_Temperature_Celsius'.
        P_STC (float): Rated DC capacity at STC (kW).
        gamma (float): Temperature coefficient (-0.004/°C for poly-Si).
        aggregation (str): 'default', 'hourly', 'daily', 'monthly', or 'yearly'.

    Returns:
        float or DataFrame: Temperature-corrected PR as percentage.
    """
    data['Temp_Correction'] = 1 + gamma * (data['Temperature_Probe_1'] - 25)
    data['PR_Denominator'] = 1058.4 * (data['Pyranometer_1'] / 1000) * data['Temp_Correction']
    data['PR'] = (data['Energy_kWh'] / data['PR_Denominator']) * 100

    if aggregation == 'default':
        total_energy = data['Energy_kWh'].sum()
        total_denominator = data['PR_Denominator'].sum()
        pr = (total_energy / total_denominator) * 100 if total_denominator > 0 else np.nan
        return round(pr, 2)
    
    freq = freq_map.get(aggregation, 'D')

    energy_agg = data['Energy_kWh'].resample(freq).sum()
    denom_agg = data['PR_Denominator'].resample(freq).sum()
    pr_series = (energy_agg / denom_agg) * 100
    return pr_series.round(2)