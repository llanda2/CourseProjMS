import pandas as pd
import requests

# === Step 1: Prepare the batch file ===

# Read your original data
df = pd.read_csv('data/MassShootingIncidnets.csv')

# Optional: Check your columns
print(df.columns)

# Prepare the Census API batch format
# We'll use 'Incident ID' as the unique identifier
batch_df = pd.DataFrame({
    'id': df['Incident ID'],
    'address': df['Address'],
    'city': df['City Or County'],
    'state': df['State'],
    'zip': ''  # Leave zip blank if not available
})

# Save to CSV (no header, no index) as required by Census API
batch_df.to_csv('census_batch.csv', index=False, header=False)

print("Step 1 complete: Prepared 'census_batch.csv' for upload.")

# === Step 2: Submit batch to Census API ===

files = {'addressFile': open('census_batch.csv', 'rb')}
payload = {
    'benchmark': 'Public_AR_Current',
    'vintage': 'Current_Current',
    'returntype': 'locations'
}

print("Submitting batch to Census API...")
response = requests.post('https://geocoding.geo.census.gov/geocoder/locations/addressbatch', files=files, data=payload)

# Check if the request was successful
if response.status_code == 200:
    print("Batch geocode successful.")
else:
    print(f"Error: Status code {response.status_code}")
    exit()

# Save the response content to a text file
with open('census_results.csv', 'w') as f:
    f.write(response.text)

print("Step 2 complete: Received response and saved to 'census_results.csv'.")

# === Step 3: Parse the results and merge back ===

# Census result columns:
# ID, input address, matched address, match type, matched longitude, matched latitude, TIGER line ID, side
results_df = pd.read_csv('census_results.csv', header=None)

# Assign column names for clarity
results_df.columns = [
    'id', 'input_address', 'matched_address', 'match_type',
    'longitude', 'latitude', 'tiger_line_id', 'side'
]

# Merge back to original dataframe
merged_df = df.merge(results_df[['id', 'latitude', 'longitude']], left_on='Incident ID', right_on='id', how='left')

# Save the final dataframe with lat/lon
merged_df.to_csv('mass_shootings_geocoded.csv', index=False)

print("Step 3 complete: Merged geocoded data saved to 'mass_shootings_geocoded.csv'.")
