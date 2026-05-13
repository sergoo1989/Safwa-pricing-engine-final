from .models import ChannelFees, PriceBreakdown

def price_item(
    sku: str,
    cogs: float,
    channel_fees: ChannelFees,
    is_package: bool = False,
    target_margin: float = 0.09
) -> PriceBreakdown:
    """
    Calculate complete price breakdown for an item
    
    Formula:
    1. NetPriceExclVAT = COGS / (1 - fees_pct - target_margin)
    2. PriceBeforeDiscount = NetPriceExclVAT / (1 - discount_rate)
    3. ListPriceInclVAT = PriceBeforeDiscount * (1 + vat_rate)
    """
    
    total_fee_pct = (
        channel_fees.platform_pct +
        channel_fees.payment_pct +
        channel_fees.marketing_pct +
        channel_fees.opex_pct +
        target_margin
    )
    
    fixed_costs = cogs + channel_fees.preparation_fee + channel_fees.shipping_fixed
    net_price_excl_vat = fixed_costs / (1 - total_fee_pct)
    
    preparation_fee = channel_fees.preparation_fee
    shipping_fee = channel_fees.shipping_fixed
    opex_fee = net_price_excl_vat * channel_fees.opex_pct
    marketing_fee = net_price_excl_vat * channel_fees.marketing_pct
    platform_fee = net_price_excl_vat * (channel_fees.platform_pct + channel_fees.payment_pct)
    
    total_costs = cogs + preparation_fee + shipping_fee + opex_fee + marketing_fee + platform_fee
    
    price_before_discount = net_price_excl_vat / (1 - channel_fees.discount_rate)
    list_price_incl_vat = price_before_discount * (1 + channel_fees.vat_rate)
    
    net_profit = net_price_excl_vat - total_costs
    net_margin_pct = (net_profit / net_price_excl_vat * 100) if net_price_excl_vat > 0 else 0
    gross_margin_pct = ((net_price_excl_vat - cogs) / net_price_excl_vat * 100) if net_price_excl_vat > 0 else 0
    
    breakeven_price = total_costs
    
    return PriceBreakdown(
        sku=sku,
        item_type='package' if is_package else 'product',
        cogs=cogs,
        preparation_fee=preparation_fee,
        shipping_fee=shipping_fee,
        opex_fee=opex_fee,
        marketing_fee=marketing_fee,
        platform_fee=platform_fee,
        total_costs=total_costs,
        net_price_excl_vat=net_price_excl_vat,
        price_before_discount=price_before_discount,
        list_price_incl_vat=list_price_incl_vat,
        net_profit=net_profit,
        net_margin_pct=net_margin_pct,
        gross_margin_pct=gross_margin_pct,
        breakeven_price=breakeven_price
    )

def calculate_price_at_margin(
    total_costs: float,
    target_margin_pct: float,
    discount_rate: float,
    vat_rate: float
) -> float:
    """Calculate list price (incl VAT) at a specific target margin"""
    net_price = total_costs / (1 - target_margin_pct / 100)
    price_before_discount = net_price / (1 - discount_rate)
    list_price = price_before_discount * (1 + vat_rate)
    return list_price
