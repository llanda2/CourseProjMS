import pandas as pd
import requests
import csv

# === Step 1: Prepare the batch file ===

# Read your original data
df = pd.read_csv('data/MassShootings.csv')

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

# First, we need to handle the inconsistent format
result_data = []
with open('census_results.csv', 'r') as f:
    csv_reader = csv.reader(f, quotechar='"')
    for row in csv_reader:
        result_data.append(row)

# Create a clean dataframe with consistent columns
clean_results = []
for row in result_data:
    incident_id = row[0]
    input_address = row[1]
    match_status = row[2]

    # Initialize lat/lon as None
    latitude = None
    longitude = None

    # If it's a match, extract lat/lon from the coordinates field
    if match_status == 'Match' and len(row) >= 6:
        coords = row[5]
        if ',' in coords:
            try:
                lon, lat = coords.split(',')
                longitude = float(lon)
                latitude = float(lat)
            except (ValueError, IndexError):
                pass  # Keep as None if parsing fails

    clean_results.append({
        'id': incident_id,
        'latitude': latitude,
        'longitude': longitude
    })

# Convert to DataFrame
results_df = pd.DataFrame(clean_results)

# Important: Check and convert data types before merging
print(f"Original df['Incident ID'] dtype: {df['Incident ID'].dtype}")
print(f"Results df['id'] dtype: {results_df['id'].dtype}")

# Convert id columns to the same type (strings)
df['Incident ID'] = df['Incident ID'].astype(str)
results_df['id'] = results_df['id'].astype(str)

print(f"After conversion - Original df['Incident ID'] dtype: {df['Incident ID'].dtype}")
print(f"After conversion - Results df['id'] dtype: {results_df['id'].dtype}")

# Now merge with consistent data types
merged_df = df.merge(results_df, left_on='Incident ID', right_on='id', how='left')

# Remove redundant id column from results
if 'id' in merged_df.columns:
    merged_df = merged_df.drop('id', axis=1)

# Save the final dataframe with lat/lon
merged_df.to_csv('mass_shootings_geocoded.csv', index=False)

print("Step 3 complete: Merged geocoded data saved to 'mass_shootings_geocoded.csv'.")