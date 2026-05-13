from pricing_app.data_loader import load_cost_data
from pricing_app.costing import resolve_component_cost
from pricing_app.reports import build_full_pricing_table
from pricing_app.models import ChannelFees
def main():
    # Load data
    materials, product_recipes, products_df, package_compositions, packages_df = load_cost_data('data')
    # Compute costs
    product_costs = {
        sku: resolve_component_cost(sku, materials, product_recipes, package_compositions)
        for sku in product_recipes
    }
    package_costs = {
        sku: resolve_component_cost(sku, materials, product_recipes, package_compositions)
        for sku in package_compositions
    }
    # Build pricing table
    channel_fees = ChannelFees()
    pricing_table = build_full_pricing_table(
        products_df, packages_df,
        product_costs, package_costs,
        channel_fees
    )
    # Display
    print("\n=== Full Pricing Table ===")
    print(pricing_table.to_string(index=False))
    # Save to CSV
    pricing_table.to_csv('output_pricing_table.csv', index=False, encoding='utf-8-sig')
    print("\nSaved to output_pricing_table.csv")
if __name__ == "__main__":
    main()
