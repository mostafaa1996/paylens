from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from utils.Excel_file_reader import ExcelFileReader

class TestCasesFromExcelReader(ExcelFileReader): 
    def __init__(self, file_path):
        super().__init__(file_path)
        self.TestCases = []
        self.TestStepsPerTestCase = []
        
    def read_test_cases(self):
        df = self.read_excel_file_with_sheet(sheet_name="Selected" , header=7)
        if df is not None:
            df.columns = df.columns.str.strip()
            self.TestCases = df.to_dict(orient="records")
        return self.TestCases

    def read_test_steps(self):
        df = self.read_excel_file_with_sheet(sheet_name="Steps" , header=5)
        if df is not None:
            df.columns = df.columns.str.strip()
            self.TestStepsPerTestCase = df.to_dict(orient="records")
        return self.TestStepsPerTestCase