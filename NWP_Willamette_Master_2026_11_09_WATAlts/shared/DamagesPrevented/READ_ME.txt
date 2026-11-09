Damages Prevented Procedure:

1.
Read the READ_ME.txt in the Python_Extract folder. Double click on the USGS_CWMS_Download.bat in the Python_Extract folder and enter the date range when prompted. This will produce an obsData.dss with all your observed data. Make a copy of the obsData.dss in the main DamagesPrevented folder. Edit the DSS records in the copied obsData.dss in the DamagesPrevented folder focusing on the peaks. 
2.
Create the simulation in the watershed with the Obs_NWP_H and unregNWP_H  alternatives - Date range for the water year 01Oct to 30Sep, with some padding on both sides if you can.
3.
Cut and paste the contents of the DP_Menu.py into the script editor for the simulation. Click the Transform Gage Data and Compute Final Water balance Locals buttons on the Damages Prevented Selection Menu.
4.
Re-Run the extract. Run the Obs_NWP_H and unregNWP_H alternatives.
5.
Check the results of the simulation from ResSim or click the Create Verification Plots in the Damages Prevented Selection Menu and review the plots in the Plots folder. Edit data and redo steps 3-5 as necessary. 
6.
Click the Run Mini-Simulations in the Damages Prevented Selection Menu. This produces the FlowReductions.xls file. Look this file over and make a copy of it in the newer excel .XLSX file format and move it into the NWP_Damage_Calculation folder. 
7.
Read the READ_ME.txt in the NWP_Damage_Calculation folder. Double click the Calculate_Damages_From_Flow_Reductions.bat. Review the results in the damages_prevented.csv and dsmages_prevented_ByProject.csv. Flag and discuss large damage results with hydrology SME.
8.
Upload results to the treaty drive "X:\CRT2014\PDT\WAT\DamagesPrevented" water year folder and send the link to the NWP hydrology SME, NWP assigned economist, and NWD Damages Prevented coordinator. NWD is calculating damages prevented below Willamette Falls on the Willamette and below the Willamette on the Columbia, some of which will be attributable to operations on the Willamette. Coordinate with NWD to ensure these values get to the NWP district hydrologist.
9.
Copy records for the Rogue watershed to an obsData.dss file in the Rogue watershed. Edit that data as needed, create a water year simulation with the regulated and observed alternatives. Add the DP_Menu script. Compute final water balance locals. Re-run the extract. Run the alternatives. Run the mini simulations. Check the results. 




