import requests
import zipfile
import io
import pandas as pd
import numpy as np
import os

def retrieve_pulse(week, verbose=True):
    """Get Census Pulse Data
    Args:
        week (int): Week number to load

    Returns:
        pd.DataFrame: dataframe of week's data
    """
    year = 2021 if (week >= 22 and week < 41) else 2022 if (week >= 41) else 2020
    base_url = "https://www2.census.gov/programs-surveys/demo/datasets/hhp/"
    zip_url = base_url + f'{year}/wk{week}/HPS_Week{week:02d}_PUF_CSV.zip'
    filename = f"data/pulse_{week}.csv"
    if not os.path.exists(filename):
        if verbose:
            print("Week: ", week)
            print("Retrieving url: ", zip_url)
        response = requests.get(zip_url)
        if verbose:
            print("Unzipping")
        pulse_zip = zipfile.ZipFile(io.BytesIO(response.content))
        if verbose:
            print("Reading into Pandas")
        pulse_csv = pd.read_csv(pulse_zip.open(f'pulse{year}_puf_{week:02d}.csv'))
        dictionary_filename = f'pulse{year}_data.dictionary_CSV_{week:02d}.xlsx'
        if os.path.exists(dictionary_filename):
            dictionary = pd.read_excel(pulse_zip.open(dictionary_filename))
            dictionary.to_excel(f'data/pulse{year}_data.dictionary_CSV_{week}.xlsx')
            del dictionary
        del pulse_zip
        if verbose:
            print("Saving")
        pulse_csv.to_csv(filename)
    else:
        if verbose:
            print(f"Opening local file for pulse week{week}")
        pulse_csv = pd.read_csv(filename)
    return pulse_csv

def build_pulse(week_start, week_end):
    """
    Periods: https://www.census.gov/programs-surveys/household-pulse-survey/datasets.html
    Args:
        week_start (int): first week of pulse to get
        week_end (int): last week of pulse to get

    Returns:
        pd.DataFrame: the final dataset
    """
    df = retrieve_pulse(week_start)
    for week in np.arange(week_start+1, week_end+1, 1):
        df_week = retrieve_pulse(week)
        df = pd.concat([df, df_week])
    return df

def filter_pulse(df, verbose=False):
    # Filter on variables that affect eligibility
    if verbose:
        print("Shape before:", df.shape)
    df = df[~df["INCOME"].isin([-99, -88])]
    df = df[~df["THHLD_NUMKID"].isin([-99, -88])]
    df = df[df['TBIRTH_YEAR'] < 2003]
    df = df[df['ABIRTH_YEAR'] == 2]
    df = df[df['AHHLD_NUMKID'] == 2]
    if verbose:
        print("Shape after:", df.shape)
    return df


def basic_processing(df, trim=True):
    # Basic CTC Eligibility
    has_kids = df["THHLD_NUMKID"] > 0
    income_under_150k = (df['INCOME'] < 7)
    income_under_75k = (df['INCOME'] < 5)
    income_under_100k = (df['INCOME'] < 6)
    married_or_widowed = (df['MS'] == 1) | (df['MS'] == 2)
    eligible = (has_kids & income_under_150k & married_or_widowed |
    has_kids & income_under_75k
    )
    df["Eligible"] = (eligible).astype(int)
    df['Post'] = ((df["WEEK"] > 33) & (df["WEEK"] < 40)).astype(int)
    df['Treat'] = (df['Post'] * df["Eligible"])
    # Check
    df["Received_CTC"] = (df['CTC_YN'] == 1).astype(int)
    # Time
    df['Week'] = df["WEEK"].astype("category")
    # Outcomes / Controls
    df["Number_of_kids"] = df["THHLD_NUMKID"].astype(int)
    df["Number_of_people"] = df["THHLD_NUMPER"].astype(int)
    df["Depressed_or_Anxious"] = ((df["DOWN"] >= 3) | (df["ANXIOUS"] >= 3)).astype(int)
    df["Depressed"] = ((df["DOWN"] >= 3)).astype(int)
    df["Anxious"] = ((df["ANXIOUS"] >= 3)).astype(int)
    df["Difficulty_with_Expenses"] = (df['EXPNS_DIF'] >= 3).astype(int)
    df["Food_Insecurity"] = (df['CURFOODSUF'] >= 3).astype(int)
    df["Rent_Confidence"] = (df['MORTCONF'] >= 3).astype(int)
    df["Vaccinated"] = (df["RECVDVACC"] == 1).astype(int)
    df["Enrolled_in_SNAP"] = (df["SNAP_YN"] == 1).astype(int)
    df["Worked_in_last_week"] = (df["ANYWORK"] == 1).astype(int)
    df["Income"] = df["INCOME"].astype("category")
    df["Education"] = df["EEDUC"].astype("category")
    df["Age"] = (2021 - df["TBIRTH_YEAR"]).astype(int)
    df["Received_EBT_card"] = (df["SCHLFDHLP2"] == 1).astype(int)
    df['Received_Free_Food'] = (df['FREEFOOD'] == 1).astype(int)
    # Weights
    df['Household_Weight'] = df['HWEIGHT'].astype(int)
    if trim == True:
        df_trimmed = df.iloc[:, -22:]
        return df_trimmed
    else:
        return df

    