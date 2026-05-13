import pandas as pd
from typing import Dict
from .models import ChannelFees
from .pricing import price_item

def build_full_pricing_table(
    products_df: pd.DataFrame,
    packages_df: pd.DataFrame,
    product_costs: Dict[str, float],
    package_costs: Dict[str, float],
    channel_fees: ChannelFees,
    target_margin: float = 0.09
) -> pd.DataFrame:
    """Build complete pricing table for all SKUs"""
    
    rows = []
    
    # Add products
    for _, row in products_df.iterrows():
        sku = row['Product_SKU']
        name = row['Product_Name']
        cogs = product_costs.get(sku, 0)
        
        breakdown = price_item(sku, cogs, channel_fees, is_package=False, target_margin=target_margin)
        
        rows.append({
            'SKU': sku,
            'Name': name,
            'Type': 'Product',
            'COGS': breakdown.cogs,
            'NetPriceExclVAT': breakdown.net_price_excl_vat,
            'ListPriceInclVAT': breakdown.list_price_incl_vat,
            'NetMarginPct': breakdown.net_margin_pct,
            'GrossMarginPct': breakdown.gross_margin_pct
        })
    
    # Add packages
    for _, row in packages_df.iterrows():
        sku = row['Package_SKU']
        name = row['Package_Name']
        cogs = package_costs.get(sku, 0)
        
        breakdown = price_item(sku, cogs, channel_fees, is_package=True, target_margin=target_margin)
        
        rows.append({
            'SKU': sku,
            'Name': name,
            'Type': 'Package',
            'COGS': breakdown.cogs,
            'NetPriceExclVAT': breakdown.net_price_excl_vat,
            'ListPriceInclVAT': breakdown.list_price_incl_vat,
            'NetMarginPct': breakdown.net_margin_pct,
            'GrossMarginPct': breakdown.gross_margin_pct
        })
    
    return pd.DataFrame(rows)