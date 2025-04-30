# === utils.py ===
import pandas as pd

def load_data():
    gun_laws_df = pd.read_csv('./data/stateLaws.csv')
    gun_laws_df.columns = gun_laws_df.columns.str.strip()
    gun_laws_df = gun_laws_df.rename(columns={
        'Label': 'State',
        'Strength of Gun Laws (out of 100 points)': 'Law Strength',
        'Gun Deaths per 100,000 Residents': 'Gun Deaths'
    })
    gun_laws_df['Law Strength'] = pd.to_numeric(gun_laws_df['Law Strength'], errors='coerce')
    gun_laws_df['Gun Deaths'] = pd.to_numeric(gun_laws_df['Gun Deaths'], errors='coerce')

    # Load SCOTUS data
    sc_cases_df = pd.read_csv('./data/SCDeci.csv', index_col=0)
    sc_cases_df.columns = sc_cases_df.columns.str.strip()
    sc_cases_df = sc_cases_df.rename(columns={
        'Second Amendment Supreme Court Cases': 'Case',
        'Quick Summary': 'Summary',
        'Brief Synopsis of Case': 'Synopsis',
        'Year of Decision': 'Year',
        'Court Justices': 'Justice',
        'Justice Decision': 'Decision Type',
        '0 - Advocacy for Gun Rights; 1 - Advocacy for Gun Control': 'Stance'
    })
    sc_cases_df['Year'] = pd.to_numeric(sc_cases_df['Year'], errors='coerce')
    sc_cases_df['Stance'] = pd.to_numeric(sc_cases_df['Stance'], errors='coerce')

    shootings_df = pd.read_csv('mass_shootings_geocoded.csv')
    shootings_df['latitude'] = pd.to_numeric(shootings_df['latitude'], errors='coerce')
    shootings_df['longitude'] = pd.to_numeric(shootings_df['longitude'], errors='coerce')
    shootings_df['Year'] = pd.to_numeric(shootings_df['Incident Date'].str.extract(r'(\d{4})')[0], errors='coerce')
    shootings_df['Total Victims'] = shootings_df['Victims Killed'] + shootings_df['Victims Injured']
    shootings_df['Full Location'] = shootings_df.apply(
        lambda row: f"{row['Address']}, {row['City Or County']}, {row['State']}, USA", axis=1)
    shootings_df.dropna(subset=['latitude', 'longitude'], inplace=True)

    # Load LL1–LL10 public opinion data
    opinion_paths = {f"LL{i}": f"./data/LL{i}.csv" for i in range(1, 11)}

    def clean_opinion_df(df):
        df = df.copy()
        df = df[~df.apply(lambda row: all(str(x).strip() in ['%', 'nan', '*'] for x in row), axis=1)]
        df.dropna(how='all', inplace=True)
        if not str(df.columns[0]).lower().startswith("date") and "X.1" in df.columns[0]:
            df.columns = df.iloc[0]
            df = df.drop(df.index[0])
        df = df[df.iloc[:, 0].astype(str).str.contains(r"\d{4}", na=False)]
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)
        df_melted = df.melt(id_vars="Date", var_name="Response", value_name="Percent")
        df_melted['Percent'] = df_melted['Percent'].astype(str).str.replace('%', '', regex=False).str.replace('*', '', regex=False).str.strip()
        df_melted['Percent'] = pd.to_numeric(df_melted['Percent'], errors='coerce')
        df_melted['Date'] = pd.to_datetime(df_melted['Date'], format="%m/%d/%Y", errors='coerce')
        df_melted = df_melted.dropna(subset=['Date', 'Percent'])
        return df_melted

    opinion_data = {key: clean_opinion_df(pd.read_csv(path)) for key, path in opinion_paths.items()}

    return {
        'gun_laws_df': gun_laws_df,
        'sc_cases_df': sc_cases_df,
        'shootings_df': shootings_df,
        'opinion_data': opinion_data
    }

def load_cleaned_opinion_data():
    df = pd.read_csv('./data/Cleaned_Public_Opinion_Data.csv')
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    df.dropna(subset=['Year', 'Value'], inplace=True)
    df = df[df['Question_Text'] != "Do you have a gun in your home? (version 2)"]
    return df

