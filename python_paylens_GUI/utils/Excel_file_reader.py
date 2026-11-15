import pandas as pd
from pathlib import Path

class ExcelFileReader:
    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def read_excel_file(self):
        try:
            df = pd.read_excel(self.file_path)
            return df
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return None
        
    def read_excel_file_with_sheet(self, sheet_name , header=None):
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=header)
            return df
        except Exception as e:
            print(f"Error reading Excel file with sheet '{sheet_name}': {e}")
            return None
