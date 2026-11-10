
The USGS_CWMS_Download.bat will download the USGS and CWMS data defined in the RequiredRecordsDict.csv returning Hourly or Daily average data.

The RequiredRecordsDict.csv is pretty self explanatory. and the only file you should need to edit.
One column is for either a USGS gauge number or a cwms formatted string, 
one column has the string that defines the path written to the dss file, and
the last column indicates if the path is USGS or CWMS.
If you use 1DAY for the DSS record it will return daily average. 1HOUR will return hourly average. 
The script will prompt you for a start date and end date.

The only thing you have to do for initial setup is make sure anaconda or miniconda is installed. If it isn't you can install it using the executable
provided in the project folder. *** Make sure you install it for "this user only" and NOT all users or system.

The .bat file will check to see if you have miniconda or anaconda. If you don't it will tell you where it looked. It looks in the normal places. 
Then, it checks to see if you have the environment loaded that works with the script. If you don't, it will load it. The environment is a little
fragile because pydsstools needs an old version of numpy. You should be able to edit the script or the environment and the .bat should still work,
but at your own risk.