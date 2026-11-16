import sys
import zipfile
import pandas as pd

path = sys.argv[1]

with zipfile.ZipFile(path) as z:
    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
    if not csv_files:
        raise ValueError("No CSV file found in the zip archive.")
    
    csv_name = csv_files[0] 
    print(f"Reading inner file: {csv_name}")
    
    
    with z.open(csv_name) as f:
        df = pd.read_csv(f, nrows=5, low_memory=False)

print("Shape of sample:", df.shape)
print("Total columns:", len(df.columns))
print(df[["FlightDate", "Reporting_Airline", "Tail_Number", "Origin", "Dest",
          "DepDelay", "ArrDelay", "Cancelled"]])