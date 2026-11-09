This file serves as the change log for the watershed.
Any time a new version of the watershed is uploaded, there should be an entry in this change log file.
You can add to it manually, or it can prompted to open by a script.



# `NWP\_Willamette` \[10 Mar 2025 09:18 / g2echrc9]

Initial version, ripped from the CWMS watershed provided by Kevin McAllister on 07March2025 here:
Z:\\Engineering\_Division\\CENWP-EC-H\\CENWP-EC-HR\\RES\_REG\\CWMS\\Teamwork\\watershed\\NWP\_Willamette\_ResSimMaster\\watershed
Created a simple daily alternative for testing purposes.

# `NWP\_Willamette` \[11 Mar 2025 07:10 / g2echrc9]

Deleted the ESP\_RFC alternative--it had been hiding in the "study" configuration, since it didn't have a network associated with it.
We will re-create it later to use the "Willamette" network.

# `NWP\_Willamette\_Master\_2025-03-12\_startingPoint` \[12 Mar 2025 11:10 / g2echrc9]

Changed name of watershed, and updated the \~CleanWatershedForArchive.py file

# `NWP\_Willamette\_Master\_2025-03-13\_updatedCGRReleaseCap` \[13 Mar 2025 09:25 / g2echrc9]

Changed Cougar release capacity to match up with tables on the RCC webpage

# `NWP\_Willamette\_Master\_2025-03-13\_Net0\_Alt0\_Op0\_Data0` \[13 Mar 2025 09:42 / g2echrc9]

Changed the naming convention of the watershed.

# `NWP\_Willamette\_Master\_2025-03-27\_Net0\_Alt1\_Op1\_Data0` \[27 Mar 2025 13:48 / g2encjer]

Deleted all alternatives except for the EIS NAA alternative
Deleted all operation sets not in the EIS NAA alternative
Deleted all rules not in EIS NAA alternative operation set rule stacks
Fixed node reference in IF blocks so simulations will run without errors

# `NWP\_Willamette\_Master\_2025-03-28\_Net1\_Alt0\_Op0\_Data0` \[28 Mar 2025 13:42 / g2echrc9]

Changed all operation set names to "Default"
Getting the model ready for more scripted rules/state variables
Created 2 state variables: "Alternative\_Setup" and "ControllerExternalSV"
Put alternative config files in the scripts folder ("alt\_config")
The alt config file for each alternative can be used to make the rules behave
differently without actually touching the scripts themselves.
Added some .jar files to scripts/ExternalModules that are needed to load up json files
Reorganized the "scripts" directory big time and put a readme in
Added 2 dummy scripted rules at Hills Creek to import scripts/modules
Hills Creek is the first reservoir to initialize right now,
but it might not be in the future if we change the compute blocking.
Added ResSimAltCompare.py to the script/utilities folder



# `NWP\_Willamette\_Master\_2025-04-08\_Net1\_Alt0\_Op1\_Data0` \[08 Apr 2025 10:43 / g2echrc9]

Kevin Mcallister removed many of the inflow points and standardized the naming convention.
Ryan added downstream control rules for flood risk management at all reservoirs.
These were taken directly from the Willamette flow-frequency model.
Still need to do a little work on the rule for Salem at Detroit.
Don't want a pure DS control rule, but need a proxy to limit evacuation after an event.



# `NWP\_Willamette\_Master\_2025-04-08\_Net1\_Alt0\_Op2\_Data0` \[08 Apr 2025 15:08 / g2echbms]

Betsy added Flood Min rule to all projects, which was copied from the WFF watershed model.
Added rule for min flow at DET for BCL cavitation of 1050 cfs.



# `nwp\_willamette\_master\_2025-04-09\_net0\_alt0\_op1\_data0` \[09 Apr 2025 14:16 / g2encskk]

Sammy updating special curves rules at all reservoirs to align with Willamette Flow Frequency.



# `NWP\_Willamette\_Master\_2025-04-10\_Net0\_Alt0\_Op1\_Data0` \[10 Apr 2025 06:18 / g2echrc9]

Got rid of Salem max flow rule at Detroit and Green Peter--it wasn't working well.
Can be revisited at a later date.
The rule worked fine if DET/GPR/SLM are in the same compute block, but
we don't want that to occur, since we want LOP to be the only one in the same block as SLM
Taking it out for now, it usually doesn't apply except when limiting evacuation after a flood.
Deleted 50 % FC Pool zone at Cottage Grove and Dorena
Deleted Secondary Flood Control zone at Lookout Point

# `NWP\_Willamette\_Master\_2025-04-11\_Net0\_Alt0\_Op1\_Data1` \[11 Apr 2025 09:26 / g2echrc9]

Added Jasper flood rule back in to Lookout Point
Added Jasper/Harrisburg flood rule into Hills Creek
Added new alternative that uses 3hour data that is good for historic flood simulations.
Brought in new input data file for flood simulations: MeldedHourlyDaily\_WY1982-2019.dss

# `NWP\_Willamette\_Master\_2025-04-11\_Net0\_Alt1\_Op1\_Data1` \[11 Apr 2025 11:46 / g2echrc9]

Added drawdown scripted rules to Detroit/Green Peter
Edited default alt config file to include drawdown parameters
This is not a complete solution, but it's working enough that Josh can take it and run with it.

# `NWP\_Willamette\_Master\_2025-04-17\_Net1\_Alt1\_Op1\_Data1` \[17 Apr 2025 12:01 / g2encjer]

Added streams Calapooia, Luckiamute, Molalla, Pudding, and Upper McKenzie.
Added all control points to Watershed module and created new configuration Default - Deleted old configuration
Created new network from new configuration and re-drew stream sections.
Updated initialization scripts and drawdown scripts
Updated Config files.

# `NWP\_Willamette\_Master\_2025-04-18\_Net1\_Alt1\_Op1\_Data1` \[18 Apr 2025 07:36 / g2echrc9]

Some of the local inflow names had been changed with the network updates,
brought them back to the naming convention from the April 11 watershed.
Fixed up the implementation of ControllerExternalSV.py and Alternative\_Setup.py
Deleted Calapooia common computation points and junctions/reaches
Minor update to TargetElevation.py
Deleted old DUMMY rules from Hills Creek and Fern Ridge.
They only exist at Big Cliff now (first reservoir to initialize)
Deleted the old "Willamette" network and all associated alternatives.
Brought back the "Temp1Day" and "Temp3Hour" alternatives.
Edited alt config default file to get rid of the warning messages about scripts not matching.
Since our scripts mostly live outside the Ressim GUI, this isn't needed.

# `NWP\_Willamette\_Master\_2025-04-18\_Net1\_Alt1\_Op0\_Data0` \[18 Apr 2025 14:26 / g2encjer]

Fixed locations of new control points and shortened stream sections.
Added option to not do drawdown for a given alternative

# `NWP\_Willamette\_Master\_2025-04-22\_Net0\_Alt0\_Op1\_Data0` \[23 Apr 2025 09:53 / g2echrc9]

Added Harrisburg flood max rule that was missing from COT/DOR.
Deleted all If Blocks from the model.

# `NWP\_Willamette\_Master\_2025-04-25\_Net0\_Alt0\_Op1\_Data0` \[25 Apr 2025 13:02 / g2echrc9]

Added secondary flood control rules at Detroit/Green Peter/Lookout Point (copied from WFF watershed)
This involved changing the default.txt in the alt config folder
Added a .py and a .csv config script to the ../scripts/externalRules folder
Created pass-through scripted rules at Detroit/Green Peter/Lookout Point

# `NWP\_Willamette\_Master\_2025-05-23\_Net1\_Alt0\_Op1\_Data0` \[23 May 2025 13:01 / g2echbms]

Removing rate of change rules (task #29) and updating routing (task #4).



# `NWP\_Willamette\_Master\_2025-06-03\_Net0\_Alt0\_Op1\_Data0` \[03 Jun 2025 15:46 / g2encjer]

Replaced Rule Curves with curves from Willamette Flow Frequency model.

# `NWP\_Willamette\_Master\_2025-06-10\_Net0\_Alt0\_Op1\_Data0` \[10 Jun 2025 15:09 / g2echrc9]

Added scripted rule for MainstemFlowAug to Blue River, Cougar, Fall Creek, Hills Creek, Dorena, Cottage Grove
Left the native downstream control rule at Lookout Point
Added MainstemFlowAugSV.py file to ../scripts/externalSVs
And also changed the \_externalSV\_Compute\_Options.csv file to add in the new SV
Added new state variable to ResSim model "MainstemFlowAugSV"
This serves as the brains for all the Salem/Albany flow aug
Changed state variable script in ResSim (init and cleanup module) of ControllerExternalSV
Slightly changed ControllerExternalSV to be able to handle more SV's beyond Alternative\_Setup
Changed cFile.py to handle weird UTC encoding characters ('\\xef\\xbb\\xbf') in some csv file reading
Added new alt config variables to ../scripts/alt\_config/\_default.txt
Deleted "Fish Spill" rule at Foster, it had erroneously been referencing Dorena outflow
Deleted "Temp Spill" rule at Foster. Release allocations will be handled as a post-process.
Added "Deep Drawdown" rule to Fall Creek.

# `NWP\_Willamette\_Master\_2025-06-11\_Net0\_Alt0\_Op1\_Data0` \[11 Jun 2025 08:03 / g2echrc9]

Changed mainstem flow aug rules at Lookout Point to reference state variables instead of having a table in the ResSim editor.
This means that if the mainstem flow-aug targets are changed, you only need to do it in one place--the CSV file rather than ResSim GUI.
Had to change MainstemFlowAugSV.py file in ../scripts/externalSVs
So that it spit out the Salem/Albany flow targets to two new dummy state variables



# `NWP\_Willamette\_Master\_2025-07-01\_Net0\_Alt0\_Op1\_Data0` \[01 Jul 2025 12:46 / g2encjer]

Added IRRM scripted rule and did some minor cleanup to the drawdown rule.
Found some conflicts with the IRRM rule and the downstream control rule at CGR. The downstream
control rule is over constraining the IRRM. Not really a problem with the IRRM rule, more a problem
with the downstream control rule.

# `NWP\_Willamette\_Master\_2025-07-10\_Net0\_Alt0\_Op1\_Data0` \[10 Jul 2025 15:23 / g2encjer]

Updated Max Evac rules from WFF
Double checked zone elevations from WFF
Added HCR Refill LOP First Script



# `NWP\_Willamette\_Master\_2025-08-18\_Net1\_Alt0\_Op1\_Data0` \[18 Aug 2025 08:54 / g2encjer]

Added delyaed refill scripted rule (for LOP spillway spill and CGR delayed refill)
Fixed broken network by coburg (got help from Amanda Walsh - May have introduced ghost node, but everything works)
Renamed so that all spillways are named Spillway and regulating outlets are named Regulating Outlet.
Redefined Penstocks as controlled outlets.
updated all outlet rating tables.
Re-ordered rules in rule stacks closer to what they should be. Testing still required.



# `NWP\_Willamette\_Master\_2025-08-28\_Net0\_Alt0\_Op1\_Data0` \[28 Aug 2025 08:18 / g2encjer]

Added No Draft script - define an elevation timeseries below which the reservoir will pass inflow
Added Draft to Date script - uses average of next 10 day inflows to set release to hit drawdown target by a date
Updated some scripts to use a csv config instead of text file to make configs easier to read and write
Updated some scripts that were failing with edge cases (IRRM, for example)

# `NWP\_Willamette\_Master\_2025-08-29\_Net0\_Alt0\_Op1\_Data0` \[29 Aug 2025 07:47 / g2echrc9]

Updated FRM rules at Hills Creek and Lookout Point
ResSim was getting too confused with all the DS control rules at LOP/HCR, and not evacuating storage well after an event (e.g. WY1997)
-New dummy rule at Hills Creek to tie into Lookout Point and make sure in the same compute block
-Removed ResSim native DS control rules at Hills Creek
-Added new simplified FRM rule for Harrisburg at Hills Creek
-Didn't do anything for Jasper at Hills Creek, Harrisburg is usually pretty controlling
-Removed ResSim native DS control rule for Harrisburg at Lookout Point
-Replaced it with a simplified rule to try to manage Harrisburg (similar to DOR/FAL)
-Improved the cLoadModules.py file to make sure that all scripts are reloaded every time you hit compute and throw errors if not.
-Also slightly changed the "\[DUMMY] Initialize ControllerExternalSV" rule at Big Cliff

# `NWP\_Willamette\_Master\_2025-09-18\_Net1\_Alt1\_Op1\_Data1` \[18 Sep 2025 11:59 / g2encjer]

Added 3 (or 2) step process for Salem augmentation. Script for processing flows is in config folder. Script rule is in external rules folder.
Added Salem observed flow, but it doesn't show up.



# `NWP\_Willamette\_Master\_2025-10-15\_Net0\_Alt0\_Op1\_Data0` \[15 Oct 2025 14:21 / g2encjer]

Changes to FRM scripting and rule stacks to help FRM simulation, specifically Foster and Green Peter.
Model provided to NWD as template for inclusion into NWD FDR model.



# `NWP\_Willamette\_Master\_2025-11-26\_Net1\_Alt1\_Op1\_Data1` \[26 Nov 2025 12:07 / g2encjer]

Updated to include damages prevented alternatives. There is a Damages Prevented folder in the Shared folder that has the extract.
Renamed the Jefferson local so it doesn't have the same name as the junction.
Changed spillways at COT and DOR to gated outlets with a rule that sets the ungated spill as a min. This was needed to run Unreg alternative of Damages Prevented.
Modified rule stacks to test scripted rules and get alternatives functioning

# `NWP\_Willamette\_Master\_2025-12-01\_Net1\_Alt1\_Op0\_Data1` \[01 Dec 2025 13:38 / g2echrc9]

Updated Damages prevented scripts--they now live in scripts/NWDJyLib/AFDR
Removed a few big files from shared/DamagesPrevented.
e.g. Miniconda 3 executable, updated readme files to point to a place outside the watershed.
This was done to save space when zipping up the model.
Added West Linn timeseries input (and Pudding at Aurora) to Damages Prevented alternatives: "Obs\_NWP\_H" and "UnregNWP\_H"

# `NWP\_Willamette\_Master\_2025-12-06\_Net1\_Alt1\_Op0\_Data1` \[05 Dec 2025 09:56 / g2echrc9]

Removed 2 alternatives (Step1of2 and Step2of2), and associated operation sets.
Using "default" instead to reduce duplication
Changed alt config flags in \_default.txt for new flow-aug options, "mainstemFlowAugMethod"
Brought back "MainstemFlowAug" rule at all reservoirs, deleted SLMOAug rule.
Moved Salem flow aug rule to folder: "scripts/SalemAugScript"
Made changes to that script and the config file, which will eventually be eliminated and replaced with the existing .csv files.
Made the WY\_Type state variable function again to just mirror the input timeseries.



# `NWP\_Willamette\_Master\_2025-12-05\_DP\_and\_2Step` \[05 Dec 2025 14:12 / g2encjer]

Updated Damages Prevented folder in shared folder and some of the damages prevented scrips in NWDJyLib to change DP\_Menu actions
Tested 2 step process.



# `NWP\_Willamette\_Master\_2025-12-08-cleaned` \[08 Dec 2025 09:35 / g2encjer]

Removed (mostly from Damages Prevented) that was increasing the file size. Had mini conda, the Rogue watershed, and damages xlsx spreadsheet. Also removed simulation files.
Watershed is back down to \~350 MB



# `NWP\_Willamette\_Master\_2025-12-08-HillsCreek\_Balancing` \[08 Dec 2025 10:39 / g2echrc9]

Added new rule at Hills Creek to balance with LOP, "HCR\_LOP\_Balance"
Changed spring spill config file to go to April 30, not April 31st
Updated IRRM script to better achieve the IRRM elevation, needed to look at current inflow to determine release target.

# `NWP\_Willamette\_Master\_2025-12-08-SalemAugImprovements` \[08 Dec 2025 14:55 / g2encjer]

Chipping away at Ryan's comments for improvements to the Salem Augmentation 2step process.



# `NWP\_Willamette\_Master\_2025-12-08-DeepDrawdownSimplify` \[08 Dec 2025 15:01 / g2echrc9]

At LOP/CGR/GPR/DET/FAL
Revised DeepDrawdown rule and config file.
Removed ForecastDrawdown rule.
Put Deep Drawdown rule up in Top of Dam zone at LOP (in case simulation starts Oct 1 at rule curve)
Updated rule name in "HCR\_LOP\_Balance" script
Updated "DraftToRC" rule slighly to make sure it doesn't overshoot rule curve.
Delete rule "Con Max" from Fall Creek. It was constraining the deep drawdown a lot.
Removing it messes up the mainstem flow-aug,
but the max release for flow-aug should be taken care of in that rule which is being worked on.

# `NWP\_Willamette\_Master\_2025-12-10-SalemAlbanyAug` \[10 Dec 2025 15:55 / g2encjer]

Updated Salem 2 Step. Now use TwoStepSalemAlbanyAug.py
The script hits the Salem and Albany targets well, but severely constrained by
other rules in the rule stack. Ideally, script would account for difference between what is
being asked of a reservoir and what it's max is and re-allocate to where a reservoir has room below it's max.



# `NWP\_Willamette\_Master\_2025-12-11-FOS\_NoOvertop` \[11 Dec 2025 07:22 / g2echrc9]

Changed Waterloo Flood Simple rule at Foster to make sure it just tries to keep Waterloo at bankfull until it runs out of storage.
Had to edit physical data so ResSim didn't get confused in Dec 1964.
Added arbitrarily large points to elev-stor table, release capacity tables, and edited top of dam elevation.
Changed folder name from "SalemAugScript" to "SalemAlbanyAugScript"
Moved RunControl.csv from ExternalSVs to "SalemAlbanyAugScript", since it's only used by the external python script. And changed back to .py
Also moved median\_remaining\_by\_day.pkl
Changed MinFlowAlbany\_2008BiOp.csv to have the same date format as Jython expecting (e.g. 01Apr, not 1-Apr),
And reverted WY\_Type back to units of maf, since the timeseries in ResSim is in maf and other rules think the units are maf.
Changed DraftToRC rule, had a conversion from cfs to ac-ft backwards
Added observed data records to "Temp1Day" alternative, can be deleted at will if you don't want to see them.
Removed the "Con Max" rule from BLU, CGR, COT, DOR, LOP, HCR
Changed MinFlowSalemAlbanyConfig.csv so that only LOP/FAL/COT/DOR/CGR/BLU support the mainstem targets.
Brought in the max release limits
Added 2 new alternatives, "HCR1531" and "HCR1511"
Draft results are in "HCR\_IRRM\_POR\_1" simulation. The trial has the results with flow aug, the sim that's not a trial has no flow aug.

# `NWP\_Willamette\_Master\_09Mar2026\_RFC\_Update` \[09 Mar 2026 10:07 / g2encjer]

Added RFC extract and ensemble plotting capabilites



# `NWP\_Willamette\_Master\_2026\_03\_11\_RFC\_Script\_Update` \[11 Mar 2026 15:22 / g2encjer]

Updated ensemble and legacy daily percentile simulations and plotting scripts.



# `NWP\_Willamette\_Master\_2026-04-09\_3HourTesting` \[09 Apr 2026 11:37 / g2echrc9]

Tuned up the 3-hour alternative "Temp3Hour"
Fixed up the inflow timeseries in the alternative editor.
Changed special curve envelope curve at Cottage Grove and Dorena so it didn't oscillate so badly for small events.
Swapped out the "No Dummy Outlet" rule at COT/DOR for an "Uncontrolled Spill" rule to force the ungated spill.
Added comments to the "NoDraft.py" file.
Made rule priorities a little more consistent at CGR and HCR



# `NWP\_Willamette\_Master\_2026-04-10\_3HourContinued` \[10 Apr 2026 15:06 / g2echrc9]

Removed spawning flow rules at Detroit and Cougar. They were producing instabilities and weren't well documented. Can be added back in later if really desired.
Changed Temp3Hour.txt to do the one-step flow-aug in the alt config file
SecondaryFloodDraftLimitConfig.csv changed to FALSE for HCR/CGR/BLU

# `NWP\_Willamette\_Master\_2026-04-29\_ConModelScripts` \[29 Apr 2026 15:00 / g2encjer]

Updated con model plotting scripts

# `NWP\_Willamette\_Master\_2026-08-11\_Ensemble3Hour` \[11 Aug 2026 08:44 / g2echrc9]

Created new alternative: "FRM\_Base\_E"
Made for running ensembles of flood events, similar to Willamette flow-frequency
But building it this time to test out storage swaps between Blue River/Cougar
Created new config files in ..scripts/externalRules to be able to shut off certain operations for an FRM baseline run
-SpringSpillConfigNone.csv
-DeepDrawdownConfigNone.csv
Removed "DraftToDate" from default alt config, since it's not being used anymore.
Brought in new input dss file to be used in this simulation into shared directory: "shared/Ensemble\_Inputs/ResSimInputsEnsemble.dss"
Changed the rule curve zone definition at all reservoirs to be a function of time series instead of directly input.
This is needed for ensemble runs, since we want to vary not only the starting pool, but also the rule curve.
But ensemble runs have to be run in the same period (e.g. Jan 1 through Jan 16), and a rule curve fixed by date is too limiting.
No change for the POR simulations, but just getting rule curves from a DSS file instead of directly embedded in ResSim.
Added new state variable to post-process results (peaks for ensemble, time-series for POR) and spit out to CSV





# `NWP\_Willamette\_Master\_2026-09\_10\_FIRO\_space` \[10 Sep 2026 16:32 / g2encjer]

Added FIRO\_SPACE.py and config CSV - Also added a CWMS\_RULE\_CURVES.csv

FIRO\_SPACE.csv contains modified rule curves that the script targets. Blank days identify days when no target is enforced. 

Should work with 3-hour, but only tested with daily. 



# `NWP_Willamette_Master_2026_09_24_ResSim41` [24 Sep 2026 13:07 / g2encjer]
Updated to work with ResSim 4.1 so scripted diversions could be used. Worked, but scripted diversions roughly double a 10 year simulation time.


# `NWP_Willamette_Master_2026_09_24_ScriptCleanup` [24 Sep 2026 13:15 / g2encjer]
Clean up scripts with focus on consistency across scripts and test 


# `NWP_Willamette_Master_2026_10_05_DamagesPrevented` [05 Oct 2026 13:12 / g2encjer]

Added Damages Prevented functionality (DamagesPreveted folder in scripts) . The ReadMe functions as the SOP

# `NWP_Willamette_Master_2026_10_19_RTS_V1` [19 Oct 2026 09:31 / g2encjer]
Added GUI for Con Season runs in RTS and Standalone ResSim 4.1.2


# `NWP_Willamette_Master_2026_10_21_RTS_V2` [21 Oct 2026 08:01 / g2encjer]
Added model check to RTS and reconfigured documentation


# `NWP_Willamette_Master_2026_10_21_Parallel` [21 Oct 2026 13:10 / g2encjer]
Made some edits to get Parallel compute to work. Not 100% robust, but it does work, usually.


# `NWP_Willamette_Master_2026_10_21_Config_Redo` [21 Oct 2026 13:56 / g2encjer]
Updating config options so external python is not required for basic computes.



# `NWP_Willamette_Master_2026_10_23_FIRO_Updates` [23 Oct 2026 08:29 / g2echrc9]
Updated HCR IRRM to be 1511
Removed CGR seismic IRRM (never was actually in-place according to Andy), though it doesn't matter with deep drawdowns
Deleted HCR 1511 and 1531 alternatives
Turned off all secondary flood pool draft limits:
	Secondary flood storage draft limits are currently in the model at LOP/DET/GPR. 
	While this was useful for the Willamette flow-frequency study, 
	it could interfere with FIRO pre-draft operations and doesn't seem to be implemented in real-time the way the model does it. 
Changed all FRM downstream control rules to just target bankfull or regulation goal:
	Max flow targets during floods at downstream points are on a sliding scale 
	from bankfull when pool elevations are low to flood stage when pool elevations are high. 
	This could pose problems for FIRO since it could introduce inconsistencies 
	where a FIRO alternative actually targets a higher downstream stage than the baseline, 
	but it's not a real difference, just a modeling artifact. 
	I propose just having the downstream targets use a single number (bankfull). 
	If this needs to be adjusted in real-time CWMS, that number can be easily changed.
Changed all max evac rate rules:
	The max evac rates in the model appear to be a little old, and should be updated. 
	The max evac rules are a function of reservoir elevation 
	(lower releases at lower pools, higher at higher pools). 
	There's a lot of judgment in these rules, 
	and they kind of try to serve two purposes by 
	(1) including the true max evac rate from WCM, with the 
	(2) lower values being that included to prevent the pool from 
	draining too quickly after we've gone into the flood pool. 
	However, we have another rule that now meets purpose #2: the "Draft to RC" rule. 
	That rule tries to avoid spiking releases to get back to rule curve too quickly, 
	instead targeting a more gentle return to the rule curve after a flood (about 5 days or so). 
	I'd propose changing the "Max Evac Release" rules in the model 
	to be a true max evac rate that only has values 
	between normal evacuation rate and max evac rate (no low values). 
	FIRO pre-releases will not call for releases above normal evacuation rate, 
	so there should be no conflict there
Put Draft to RC rule in all zones. Put FIRO Space rule higher priority than this
Rearranged some rule priorities to be consistent between Top of Dam and Rule Curve zones
Updated DeepDrawdownConfig.csv to align with current state of practice supplied by ResReg
The bankfull flow numbers in the model for the flood rules were updated recently by NWRFC (very minor)

Created 3 new alternatives:
ALL_D (all ops, daily timestep)
FRM_H (FRM-only ops, 3-hour timestep)
FRM_E (ensemble version of FRM-only ops)

Deleted Temp1Day, Temp3Hour, FRM_Base_E alternatives.
Updated SecondaryFloodDraftLimit.py to be able to handle turning off secondary draft limits



# `NWP_Willamette_Master_2026_10_30_FallFIRO` [29 Oct 2026 13:13 / g2echrc9]
Edited cLoadModules.py so that all scripts are reloaded with each press of the compute button
otherwise script changes weren't being picked up.
Edited FIRO_SPACE to make it always a max rule, and allow for fall firo operations that want to stay below a threshold flow
Added new alt config to be able to shut FIRO completely off if desired.
Edited Deep Drawdown config .csv files and .py files to incorporate an upper flow limit when determining min release
	so that deep drawdown doesn't call for a really big release.
	Checked these numbers with ResReg, but in the model now so that I could delete the separate "Drawdown max" rule at FAL,
	which was interfering with other rules since it was specified as a "max" and not a maximum limit to a minimum flow rule.
	
Added two new state variables: MinFlowTribsSV and ResidualVolumeRegressionsSV
MinFlowTribsSV loads up the min trib flows from the config CSV one time instead of each rule doing it separately
This saves a little time and allow the trib min flows to be accessed by other scripts if desired
The rules MinFlowPlusWithdrawal.py was also edited to hook up to the SV.
This probably also needs to be done for the withdrawals (move them to a SV)
ResidualVolumeRegressionsSV predicts the volume from the current date through 30Sep by 
	doing a regression based on the last 30 days of unreg volume
Used when figuring out when we need to cut releases to avoid draining the reservoirs in the spring/summer
Added new alt config flag: residualVolumeRegressionsCSV
Added new alt config flag: cutMinFlowsActive
Added new scripted rule: "MinFlowCuts" that tries to cut releases in the spring/summer if the reservoir is draining too fast
Did this at all reservoirs except Hills Creek, since the interaction with Lookout Point should be handled with the HCR_LOP_Balance script
Added new SV "BasicProjectDataSV" that should be where all scripts look if they want things like min con elevation

# `NWP_Willamette_Master_2026_11_03_WATCapable` [03 Nov 2026 14:50 / g2echrc9]
Allowing watershed to be opened in WAT
Added new alt config layer, so it goes default, then ResSim alternative name, then WAT alternative name


# `NWP_Willamette_Master_2026_11_09_WATAlts` [09 Nov 2026 08:03 / g2echrc9]
Added WithdrawalConfigNone.csv to be able to model no additional consumptive use withdrawals from reservoirs
Added softMin fall flow at Fern Ridge per andy martin
Added new wat alternative "FIRO_Test_FIROSpaceNoWithdrawals" with FIRO but no withdrawals to show how often we hit rule curve in the fall
Added new wat alt "FIRO_Base_NoWithdrawals" to show what that looks like.

# Repository update [09 Nov 2026 / Codex]

Added scripts/module-load-settings.json with force_reload=false by default.
The module loader logs warnings for cached and reload modes. Requested reloads
are overridden OFF for the native ensemble launcher, parallel metadata, or
unrecognized compute modes; ON requires an explicit serial indication.
The setting is reread at initialization using Java NIO. Restart ResSim after
script edits whenever reload is effectively OFF. This follows the observed
parallel PySystemState.unregisterCloser failure in the old explicit-file loader.
Loader unit checks run under desktop Python and Jython 2.7.3; native HEC mode
detection and full model/parallel result validation remain outstanding.

## Reload diagnostic follow-up [09 Nov 2026 / Codex]

Write module reload mode messages explicitly through network.printLogMessage
as well as the UI warning API so native worker logs retain the decision.
Desktop Python and Jython 2.7.3 loader tests passed; native log persistence
requires confirmation on the next compute.
