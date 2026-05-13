import argparse
from .data_loader import load_cost_data
from .costing import resolve_component_cost
from .pricing import price_item
from .models import ChannelFees
def main():
    parser = argparse.ArgumentParser(description='Price a single SKU')
    parser.add_argument('--sku', required=True, help='SKU to price')
    parser.add_argument('--data-dir', default='data', help='Data directory')
    args = parser.parse_args()
    # Load data
    materials, product_recipes, products_df, package_compositions, packages_df = load_cost_data(args.data_dir)
    product_costs = {
        sku: resolve_component_cost(sku, materials, product_recipes, package_compositions)
        for sku in product_recipes
    }
    package_costs = {
        sku: resolve_component_cost(sku, materials, product_recipes, package_compositions)
        for sku in package_compositions
    }
    # Price the SKU
    sku = args.sku
    channel_fees = ChannelFees()
    if sku in product_costs:
        cogs = product_costs[sku]
        breakdown = price_item(sku, cogs, channel_fees, is_package=False)
        print(f"\n=== Product: {sku} ===")
    elif sku in package_costs:
        cogs = package_costs[sku]
        breakdown = price_item(sku, cogs, channel_fees, is_package=True)
        print(f"\n=== Package: {sku} ===")
    else:
        print(f"SKU {sku} not found!")
        return
    print(f"COGS: {breakdown.cogs:.2f} SAR")
    print(f"Net Price (excl VAT): {breakdown.net_price_excl_vat:.2f} SAR")
    print(f"List Price (incl VAT): {breakdown.list_price_incl_vat:.2f} SAR")
    print(f"Net Margin: {breakdown.net_margin_pct:.1f}%")
    print(f"Gross Margin: {breakdown.gross_margin_pct:.1f}%")
if __name__ == "__main__":
    main()
