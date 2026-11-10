You could conceivably use this process to create a required records dictionary (used for DP download script) from the ResSim observed and timeseries tabs.
This is probably a legacy script for when we were using the Damages Prevented model with the whole Columbia, but keeping it here for posterity. 

Step 1 -  Cut and past the Observed and Timeseries tabs from your Damages Prevented ResSim alternatives into the Modified_ResSim_input_tables.xlsx. The TS is for timeseries and Obs is for Observed. Delete out everything except the headers and then paste in the lines from your alternatives. The ForTransformedLocal tab is for additional timeseries indicated in your districts specific transformed locals config file. The B_Part must be the USGS gauge number, as that is what the script is looking for.

Step 2 - Open the CreateRequiredRecordsDict.py and make sure your Modified_ResSim_input_tables.xlsx is shown as the referenced file in the script and run it.

Step 3 - Open the output file (default name is RequiredRecords.csv) and enter either a CWMS-Vue path or a USGS gauge number in the Download_Key column and identify if the record is USGS or CWMS in the Source column.

Step 4 - Run the DP_Download.