import pandas as pd

def inspect_excel(file_path):
    print(f"--- Inspecting {file_path} ---")
    try:
        xl = pd.ExcelFile(file_path)
        print(f"Sheet names: {xl.sheet_names}")
        for sheet in xl.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet)
            print(f"\nSheet: {sheet}")
            print(f"Columns: {df.columns.tolist()}")
            print("Sample data (first 3 rows):")
            print(df.head(3))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if __name__ == "__main__":
    inspect_excel("final output.xlsx")
    inspect_excel("Infiniti Specification.xlsx")
