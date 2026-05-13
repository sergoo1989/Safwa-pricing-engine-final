import pandas as pd
from typing import Dict, Tuple
from .zoho_loader import has_zoho_files, load_zoho_cost_data

def load_cost_data(data_dir: str) -> Tuple[Dict, Dict, pd.DataFrame, Dict, pd.DataFrame]:
    """Load all cost-related data from Zoho exports only."""
    if has_zoho_files(data_dir):
        return load_zoho_cost_data(data_dir)

    raise FileNotFoundError(
        "ملفات Zoho المطلوبة غير موجودة. ارفع zoho_items.csv و "
        "zoho_composite_items.csv و zoho_inventory_valuation.csv من صفحة رفع الملفات."
    )
