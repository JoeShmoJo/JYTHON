# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 13:00:45 2024
# Change Log
- 04Oct2024
Removed Timestep as a variable and now resample to hourly or daily based on defined ResSim path in the process USGS and process CWMS functions 
Added df = df.apply(pd.to_numeric,errors='coerce') to process CWMS function to catch odd format values downloading from CWMS  

- 05Dec2025
Replaced wincertstore-based SSL handling with a combined CA bundle built
from certifi + Windows ROOT store using ssl.enum_certificates (Py3.9+).
Falls back to certifi only if Windows store access is unavailable.

@author: g2encjer
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import date, datetime

import numpy as np
import pandas as pd
import dataretrieval.nwis as nwis
import cwms
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer

import ssl
import certifi


# Base folder where the script/EXE lives
if getattr(sys, "frozen", False):
    # Running as PyInstaller EXE
    BASE_DIR = Path(sys.argv[0]).resolve().parent
else:
    # Running as a normal .py script
    BASE_DIR = Path(__file__).resolve().parent

# CSV file with required records information
RequiredRecordsDictPath = BASE_DIR / 'RequiredRecordsDict.csv'
# DSS file with final results
ObsDataWrite = str(BASE_DIR / 'obsData.dss')


# --- SSL Certificate Setup (Auto Trust USACE/DoD Internal CAs) ---

# Temp path for combined CA bundle (certifi + Windows ROOT store)
pem_path = os.path.join(tempfile.gettempdir(), "corp_plus_certifi.pem")


def build_windows_ca_bundle(target_pem: str) -> str:
    """
    Build a CA bundle that combines certifi's bundle with
    Windows 'ROOT' store certificates (corp CAs, etc.).
    Returns the path to the bundle.
    """
    base_bundle = certifi.where()

    with open(base_bundle, "rb") as src, open(target_pem, "wb") as dst:
        # Start with certifi roots
        dst.write(src.read())

        # Try to append Windows ROOT store certs (if available)
        try:
            # This is Windows-only and available on Python 3.9+ on Windows
            for cert_tuple in ssl.enum_certificates("ROOT"):
                der_bytes = cert_tuple[0]  # DER-encoded cert
                pem_str = ssl.DER_cert_to_PEM_cert(der_bytes)
                dst.write(pem_str.encode("ascii"))
        except AttributeError:
            # ssl.enum_certificates not available (older/non-Windows builds)
            print("[WARNING] ssl.enum_certificates not available; using certifi only.")
        except Exception as e:
            print(f"[WARNING] Error reading Windows ROOT store: {e}")

    return target_pem


# Only build once per user/session
if not os.path.exists(pem_path):
    try:
        bundle_path = build_windows_ca_bundle(pem_path)
        print(f"[INFO] Built combined CA bundle: {bundle_path}")
    except Exception as e:
        print(f"[WARNING] Failed to build combined CA bundle: {e}")
        bundle_path = certifi.where()
else:
    bundle_path = pem_path

# Point requests/cwms/python at the bundle we actually have
os.environ["REQUESTS_CA_BUNDLE"] = bundle_path
print(f"[INFO] Using CA bundle: {bundle_path}")

# --- End SSL Setup ---


# Functions

def ask_date(prompt, default):
    while True:
        user_input = input(f"{prompt} (YYYY-MM-DD) [{default}]: ").strip()
        if not user_input:
            return default
        try:
            datetime.strptime(user_input, "%Y-%m-%d")
            return user_input
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.\n")


def NWIS_dl(sites_dict, service, startDate, endDate, parameterCD):
    NWIS = {}
    for site, name in sites_dict.items():
        try:
            data = nwis.get_record(
                sites=site,
                service=service,
                start=startDate,
                end=endDate,
                parameterCd=parameterCD
            )
            if data.empty:
                print(f"Downloaded data for {site} is empty.")
            else:
                NWIS[name] = data
                print(f"Successfully downloaded data for {site}.")
        except Exception as e:
            print(f"Failed to download data for {site}: {e}")
    return NWIS


def CWMS_Download(sites_dict, StartDate, EndDate, office='nws'):
    # Convert StartDate and EndDate to datetime objects
    StartDate = pd.to_datetime(StartDate)
    EndDate = pd.to_datetime(EndDate)

    # Initialize CWMS API session
    apiRoot = "https://wm." + office + ".ds.usace.army.mil:8243/nwdp-data/"
    api = cwms.api.init_session(api_root=apiRoot)

    # Initialize empty dictionary to store data for each tsid
    CWMS_data = {}
    # Loop through each tsid
    for site, name in sites_dict.items():
        try:
            # Try to download data and store the dataframe for the tsid
            data = cwms.get_timeseries(
                site,
                office_id='NWDP',
                begin=StartDate,
                end=EndDate
            ).df
            # Check if the data is empty
            if data.empty:
                print(f"Downloaded data for {site} is empty.")
            else:
                CWMS_data[name] = data
                print(f"Successfully downloaded data for {site}.")
        except Exception as e:
            # Print the failed tsid and the error message
            print(f"Failed to download data for {site}: {e}")
    return CWMS_data


def process_usgs_data(DataDict):
    # Create an empty list to store the summary stats
    results = []
    for df_name, df in DataDict.items():
        if not df.empty and df.shape[1] > 0:
            # Keep only the first column and clean missing values
            df = df.iloc[:, [0]].copy()
            df[df < -9000] = np.nan
            df[df == -902] = np.nan
            df[df == -901] = np.nan
            df = df.dropna()
            # Create SummaryStats
            first_timestamp = df.index.min().strftime('%Y-%m-%d %H:%M')
            last_timestamp = df.index.max().strftime('%Y-%m-%d %H:%M')
            # Calculate the maximum gap between consecutive timestamps
            time_diffs = df.index.to_series().diff().dropna()
            max_gap = time_diffs.max()
            max_gap_hours = max_gap.total_seconds() / 3600.0
            # Append the results for this dataframe to the list
            results.append({
                'DataFrame': df_name,
                'First Timestamp': first_timestamp,
                'Last Timestamp': last_timestamp,
                'Max Gap': max_gap,
                'Max Gap Hours': max_gap_hours
            })
            # Resample to hourly or daily and replace nan with dss nan
            if '1HOUR' in df_name:
                t = 'h'
            elif '1DAY' in df_name:
                t = 'D'
            else:
                print('timestep of ResSim path not 1HOUR or 1DAY')
                continue
            df = df.resample(t).mean()
            df = df.fillna(-902)
            DataDict[df_name] = df
        else:
            print(f"DataFrame {df_name} is either empty or does not have any columns.")
    results_df = pd.DataFrame(results)
    return results_df


def process_cwms_data(DataDict):
    # Create an empty list to store the summary stats
    results = []
    for df_name, df in DataDict.items():
        # Set 'date-time' as index if it exists
        if 'date-time' in df.columns:
            df = df.set_index('date-time')
            DataDict[df_name] = df
        if not df.empty and df.shape[1] > 0:
            # Keep only the first column and clean missing value stand-ins
            df = df.iloc[:, [0]].copy()
            df = df.apply(pd.to_numeric, errors='coerce')
            df[df < -9000] = np.nan
            df[df == -902] = np.nan
            df[df == -901] = np.nan
            df = df.dropna()
            # Create SummaryStats
            first_timestamp = df.index.min().strftime('%Y-%m-%d %H:%M')
            last_timestamp = df.index.max().strftime('%Y-%m-%d %H:%M')
            # Calculate the maximum gap between consecutive timestamps
            time_diffs = df.index.to_series().diff().dropna()
            max_gap = time_diffs.max()
            max_gap_hours = max_gap.total_seconds() / 3600.0
            # Append the results for this dataframe to the list
            results.append({
                'DataFrame': df_name,
                'First Timestamp': first_timestamp,
                'Last Timestamp': last_timestamp,
                'Max Gap': max_gap,
                'Max Gap Hours': max_gap_hours
            })
            # Resample to hourly or daily, fill missing value stand-ins
            if '1HOUR' in df_name:
                t = 'h'
            elif '1DAY' in df_name:
                t = 'D'
            else:
                print('timestep of ResSim path not 1HOUR or 1DAY')
                continue
            df = df.resample(t).mean()
            df = df.fillna(-902)
            DataDict[df_name] = df
        else:
            print(f"DataFrame {df_name} is either empty or does not have any columns.")
    # Convert the list of results into a DataFrame
    results_df = pd.DataFrame(results)
    return results_df


def write_to_dss(dss_file, DataDict):
    for pathname, df in DataDict.items():
        if df.empty:
            print(f"[WARNING] {pathname} is empty; skipping DSS write.")
            continue

        # Create the time series container
        tsc = TimeSeriesContainer()
        tsc.pathname = pathname
        tsc.startDateTime = str(df.index[0])
        tsc.numberValues = df.shape[0]
        tsc.values = df.iloc[:, 0].copy().to_numpy()
        tsc.interval = 1  # Assuming this is the interval (hours or days depending on pathname)

        # Set units based on the path
        if "ELEV" in pathname.upper():
            tsc.units = "FEET"
        elif "FLOW" in pathname.upper():
            tsc.units = "CFS"
        else:
            tsc.units = 'Unknown'
            print(f'[WARNING] Path {pathname} is not Flow or Elev!')

        # Set the type
        tsc.type = "INST-VAL"  # Assuming this is always the type

        # Write the data to the DSS file
        with HecDss.Open(dss_file, version=6) as fid:
            fid.put_ts(tsc)


# --- Build dynamic defaults based on today's date ---
today = date.today()
current_year = today.year

default_start = date(current_year - 1, 9, 21).strftime("%Y-%m-%d")
default_end = date(current_year, 10, 7).strftime("%Y-%m-%d")

print("\nEnter date range for data download:")

startDate = ask_date("Start date", default_start)
endDate = ask_date("End date", default_end)

print(f"\nUsing StartDate = {startDate}, EndDate = {endDate}\n")


# Read in the CSV that maps required Damages Prevented inputs with download keys (USGS or CWMS).
# Create this csv with the CreateRequiredRecordsDict.py script.
RequiredRecordsDict = pd.read_csv(RequiredRecordsDictPath)

# Create the required USGS and CWMS dictionaries. USGS needs one for Elev and one for Flow because the parameterCD code for each is different.
USGS_df = RequiredRecordsDict[RequiredRecordsDict['Source'] == 'USGS']

USGS_Elev_df = USGS_df[USGS_df['ResSimPath'].str.contains('ELEV', na=False)]
USGS_Elev_dict = dict(zip(USGS_Elev_df['Download_Key'], USGS_Elev_df['ResSimPath']))

USGS_Flow_df = USGS_df[USGS_df['ResSimPath'].str.contains('FLOW', na=False)]
USGS_Flow_dict = dict(zip(USGS_Flow_df['Download_Key'], USGS_Flow_df['ResSimPath']))

CWMS_df = RequiredRecordsDict[RequiredRecordsDict['Source'] == 'CWMS']
CWMS_dict = dict(zip(CWMS_df['Download_Key'], CWMS_df['ResSimPath']))

# Download the data. All data is downloaded as instant. The processing later makes it hourly or daily.
# You could also set the service to 'dv' for daily if you don't need hourly.

USGS_Elev_Data_Dict = NWIS_dl(
    sites_dict=USGS_Elev_dict,
    service='iv',
    startDate=startDate,
    endDate=endDate,
    parameterCD='62614'
)
USGS_Flow_Data_Dict = NWIS_dl(
    sites_dict=USGS_Flow_dict,
    service='iv',
    startDate=startDate,
    endDate=endDate,
    parameterCD='00060'
)
CWMS_Data_Dict = CWMS_Download(
    sites_dict=CWMS_dict,
    StartDate=startDate,
    EndDate=endDate
)

# Process Data and create summary stats
CWMS_Summary_Stats = process_cwms_data(CWMS_Data_Dict)
USGS_Flow_Summary_Stats = process_usgs_data(USGS_Flow_Data_Dict)
USGS_Elev_Summary_Stats = process_usgs_data(USGS_Elev_Data_Dict)

Combined_Summary_Stats = pd.concat(
    [CWMS_Summary_Stats, USGS_Flow_Summary_Stats, USGS_Elev_Summary_Stats],
    ignore_index=True
)
Combined_Summary_Stats['Max Gap Hours'] = Combined_Summary_Stats['Max Gap Hours'].astype(float).round(2)
Combined_Summary_Stats.sort_values(by='Max Gap Hours', ascending=False, inplace=True)
Combined_Summary_Stats.reset_index(drop=True, inplace=True)
Combined_Summary_Stats.to_csv('Combined_Summary_Stats.csv', index=None)

# Write obsdata . This writes the final dss file your ResSim alternatives will reference.
write_to_dss(dss_file=ObsDataWrite, DataDict=USGS_Flow_Data_Dict)
write_to_dss(dss_file=ObsDataWrite, DataDict=USGS_Elev_Data_Dict)
write_to_dss(dss_file=ObsDataWrite, DataDict=CWMS_Data_Dict)
