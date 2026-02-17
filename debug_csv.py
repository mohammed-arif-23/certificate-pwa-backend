import pandas as pd
import os

# Use current dir
CSV_PATH = os.path.join(os.getcwd(), "data", "data.csv")

try:
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        # Normalize column names
        df.columns = [c.strip() for c in df.columns]
        
        email_col = next((c for c in df.columns if "email" in c.lower()), None)
        name_col = next((c for c in df.columns if "name" in c.lower()), None)

        with open("debug_output.txt", "w", encoding="utf-8") as f:
            if email_col and name_col:
                loaded_emails = []
                for _, row in df.iterrows():
                    # Handle NaN
                    val = row[email_col]
                    if pd.isna(val): continue
                    
                    email = str(val).strip().lower()
                    name = str(row[name_col]).strip()
                    if email and email != "nan":
                        loaded_emails.append(f"{email} -> {name}")
                
                f.write(f"Total Loaded: {len(loaded_emails)}\n")
                f.write("Loaded Emails:\n")
                for e in loaded_emails:
                    f.write(e + "\n")
                print("Success")
            else:
                f.write(f"Columns not found. Email: {email_col}, Name: {name_col}")
                print("Columns missing")
    else:
        print("CSV not found.")
except Exception as e:
        print(f"Error: {e}")
