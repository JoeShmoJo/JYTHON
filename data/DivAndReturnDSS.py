from pathlib import Path
import pandas as pd
from pydsstools.heclib.dss import HecDss
from pydsstools.core import TimeSeriesContainer
import numpy as np

# =============================================================================
# USER INPUTS
# =============================================================================
DIV_RETURN_SPREADSHEET = "BA_ReEval_Ag plus MI Diversion_Base and PA.xlsx"
BASE_SHEET = "Div-Return Paste_Base"
ALT_SHEET = "Div-Return Paste"
BASE_FPART = "BA_BASE"
ALT_FPART = "BA_ALT"

DSS_FILE = "BA_DIV_AND_RETURN.dss"

SCENARIOS = [
    {
        "name": "BASE",
        "sheet_name": BASE_SHEET,
        "fpart": BASE_FPART,
    },
    {
        "name": "ALT",
        "sheet_name": ALT_SHEET,
        "fpart": ALT_FPART,
    },
]


# =============================================================================
# FILE PATH
# =============================================================================
xlsx_path = Path(__file__).resolve().parent / DIV_RETURN_SPREADSHEET

# =============================================================================
# HELPERS
# =============================================================================
def clean_monthly_table(df):
    out = df.copy()

    # Clean column names
    out.columns = [str(c).strip() for c in out.columns]

    # Clean index labels
    out.index = [str(i).strip().upper() for i in out.index]

    # Convert values to numeric where possible; leave non-numeric as NaN
    out = out.replace(["N/A", "n/a", ""], pd.NA)
    out = out.apply(pd.to_numeric, errors="coerce")

    return out


def _write_series_v6(
    fid,
    pathname: str,
    series: pd.Series,
    units: str,
    interval_min: int,
    dss_type: str,
    decimals: int = 2,
):
    if series is None or series.empty:
        return False

    series = series.sort_index()
    start_dt = series.index[0].strftime("%d%b%Y %H%M").upper()

    tsc = TimeSeriesContainer()
    tsc.pathname = pathname
    tsc.startDateTime = start_dt
    tsc.numberValues = len(series)
    tsc.units = units
    tsc.type = dss_type
    tsc.interval = interval_min
    tsc.values = np.round(series.to_numpy(dtype="float64"), decimals)

    fid.put_ts(tsc)
    return True


def read_div_return_tables(xlsx_path, sheet_name):
    """
    Read the diversion and return monthly tables from one worksheet.

    Diversions:
        headings = C5:N5
        index    = A8:A23
        values   = C8:N23

    Returns:
        headings = C27:N27
        index    = A30:A45
        values   = C30:N45
    """
    # --- Diversions ---
    div_headings = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        usecols="C:N",
        skiprows=4,
        nrows=1,
    ).iloc[0].tolist()

    div_index = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        usecols="A",
        skiprows=7,
        nrows=16,
    ).iloc[:, 0].tolist()

    div_values = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        usecols="C:N",
        skiprows=7,
        nrows=16,
    )

    diversions = pd.DataFrame(div_values.values, index=div_index, columns=div_headings)

    # --- Returns ---
    ret_headings = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        usecols="C:N",
        skiprows=26,
        nrows=1,
    ).iloc[0].tolist()

    ret_index = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        usecols="A",
        skiprows=29,
        nrows=16,
    ).iloc[:, 0].tolist()

    ret_values = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        usecols="C:N",
        skiprows=29,
        nrows=16,
    )

    returns = pd.DataFrame(ret_values.values, index=ret_index, columns=ret_headings)

    diversions = clean_monthly_table(diversions)
    returns = clean_monthly_table(returns)

    return diversions, returns


month_map = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def monthly_table_to_daily(df_monthly, prefix, daily_index, fpart):
    """
    Convert a monthly table indexed by reach and with Jan-Dec columns
    into a daily dataframe where each monthly value is applied to every
    day in that month for the full period of record.
    """
    out = pd.DataFrame(index=daily_index)

    # Rename month columns from Jan, Feb, ... to 1, 2, ...
    monthly_values = df_monthly.rename(columns=month_map)

    for reach in monthly_values.index:
        reach_str = str(reach).strip().upper()
        pathname = f"//{prefix} {reach_str}/FLOW//1DAY/{fpart}"

        series = pd.Series(index=daily_index, dtype=float)

        for month_num in range(1, 13):
            if month_num not in monthly_values.columns:
                continue

            value = monthly_values.loc[reach, month_num]

            if pd.isna(value):
                continue

            series.loc[daily_index.month == month_num] = float(value)

        out[pathname] = series

    return out


# =============================================================================
# BUILD DAILY DATAFRAME
# =============================================================================
daily_index = pd.date_range(start="1934-10-01", end="2020-10-01", freq="D")

# =============================================================================
# PROCESS EACH SCENARIO
# =============================================================================
for scenario in SCENARIOS:
    scenario_name = scenario["name"]
    sheet_name = scenario["sheet_name"]
    fpart = scenario["fpart"]
    dss_path = Path(__file__).resolve().parent / DSS_FILE

    print("=" * 80)
    print(f"PROCESSING {scenario_name}")
    print(f"Sheet: {sheet_name}")
    print(f"F-part: {fpart}")
    print(f"DSS: {dss_path}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # READ MONTHLY TABLES
    # -------------------------------------------------------------------------
    Diversions, Returns = read_div_return_tables(xlsx_path, sheet_name)

    # -------------------------------------------------------------------------
    # BUILD DAILY TABLES
    # -------------------------------------------------------------------------
    daily_diversions = monthly_table_to_daily(
        Diversions,
        prefix="DIVERSION",
        daily_index=daily_index,
        fpart=fpart,
    )

    daily_returns = monthly_table_to_daily(
        Returns,
        prefix="RETURN",
        daily_index=daily_index,
        fpart=fpart,
    )

    daily_df = pd.concat([daily_diversions, daily_returns], axis=1)

    # Round to the nearest whole number but keep float dtype
    daily_df = daily_df.round(0)

    # -------------------------------------------------------------------------
    # OPTIONAL OUTPUTS
    # -------------------------------------------------------------------------
    print("Diversions monthly table:")
    print(Diversions)
    print()

    print("Returns monthly table:")
    print(Returns)
    print()

    print("Daily dataframe:")
    print(daily_df)
    print()

    print("Daily dataframe columns:")
    for c in daily_df.columns:
        print(c)

    # -------------------------------------------------------------------------
    # WRITE DAILY RECORDS TO DSS
    # -------------------------------------------------------------------------
    fid = HecDss.Open(str(dss_path))
    try:
        write_count = 0

        for pathname in daily_df.columns:
            series = daily_df[pathname].copy()

            # Keep only valid values
            series = series.dropna()
            if series.empty:
                continue

            _write_series_v6(
                fid=fid,
                pathname=pathname,
                series=series,
                units="CFS",
                interval_min=1440,   # daily
                dss_type="PER-AVER", # daily average flow
                decimals=0,
            )
            write_count += 1

    finally:
        fid.close()

    print()
    print(f"Wrote {write_count} daily records to: {dss_path}")
    print()

    # Optional CSV export per scenario
    # out_csv = Path(__file__).resolve().parent / f"daily_diversions_returns_{scenario_name}.csv"
    # daily_df.to_csv(out_csv, index=True)
    # print(f"Wrote: {out_csv}")
