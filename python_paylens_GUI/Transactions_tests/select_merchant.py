from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def select_merchant(cursor, merchant_id):
    cursor.execute("SELECT * FROM merchants where merchant_id = ?", merchant_id)
    merchant = cursor.fetchone()
    return merchant