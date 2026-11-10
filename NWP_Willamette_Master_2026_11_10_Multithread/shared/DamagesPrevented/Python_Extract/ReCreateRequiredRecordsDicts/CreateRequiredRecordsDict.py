# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 12:13:57 2024

@author: g2encjer
"""

import pandas as pd
import dataretrieval.nwis as nwis
import datetime
import cwms
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer
import numpy as np
import time


ResSim_Alternative_Input_Tables = 'Modified_ResSim_input_tables_02sep2024.xlsx'

def Create_New_Required_ResSim_Records(Updated_ResSimRecords_Formatted):

    # 1. Combine the DataFrames in the dictionary into a single DataFrame
    df = pd.concat(Updated_ResSimRecords_Formatted.values(), ignore_index=True)
    
    # 2. Filter the DataFrame to only include rows where DSSfile == 'shared/obsData.dss'
    df = df[df['DSSfile'] == 'shared/obsData.dss']
    
    # Make sure all gage numbers are formatted as string 
    df['Bpart'] = df['Bpart'].astype(str)
    
    df = df.fillna('')
    
    parts = ['Apart', 'Bpart', 'Cpart', 'Epart', 'Fpart']
    for part in parts:
        df[part] = df[part].astype(str).str.strip()
    
    # 4. Add a column called ResSimPath based on the A-F parts
    df['ResSimPath'] = '/' + df['Apart'] + '/' + df['Bpart'] + '/' + df['Cpart'] + '//' + df['Epart'] + '/' + df['Fpart'] + '/'

    df = df.drop_duplicates('ResSimPath')
    
    df['Download_Key']=''
    df['Source']=''
    
    df = df[['ResSimPath','Download_Key','Source']]

    return df

ResSimRecords_Formatted = pd.read_excel(ResSim_Alternative_Input_Tables, sheet_name=None)

RequiredRecords = Create_New_Required_ResSim_Records(ResSimRecords_Formatted)

RequiredRecords.to_csv('RequiredRecords.csv', index=False)



