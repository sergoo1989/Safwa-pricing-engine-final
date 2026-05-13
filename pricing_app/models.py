from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class Material:
    """Raw material with SKU and cost per unit"""
    material_sku: str
    material_name: str
    category: str
    unit: str
    cost_per_unit: float

@dataclass
class Product:
    """Product with SKU and calculated COGS"""
    product_sku: str
    product_name: str
    cogs: float

@dataclass
class Package:
    """Package with SKU, components, and calculated COGS"""
    package_sku: str
    package_name: str
    cogs: float
    components: list  # List of (sku, quantity, type)

@dataclass
class CustomFee:
    """Custom fee for a channel"""
    name: str  # اسم الرسم
    amount: float  # المبلغ أو النسبة
    fee_type: str  # 'percentage' أو 'fixed' (نسبة من السعر أو مبلغ ثابت)
    # percentage: من السعر بعد الخصم بدون ضريبة
    # fixed: مبلغ ثابت بالريال

@dataclass
class ChannelFees:
    """Channel fees and parameters for pricing"""
    shipping_fixed: float = 20.0  # SAR
    platform_pct: float = 0.03    # 3%
    payment_pct: float = 0.025    # 2.5%
    vat_rate: float = 0.15        # 15%
    discount_rate: float = 0.10   # 10%
    marketing_pct: float = 0.28   # 28% (from PL)
    opex_pct: float = 0.04        # 4% (from PL)
    preparation_fee: float = 6.0  # SAR
    free_shipping_threshold: float = 0.0  # الحد الأدنى للشحن والتجهيز مجاني
    custom_fees: Dict[str, CustomFee] = None  # رسوم إضافية مخصصة
    
    def __post_init__(self):
        if self.custom_fees is None:
            self.custom_fees = {}

@dataclass
class PriceBreakdown:
    """Complete price breakdown for an item"""
    sku: str
    item_type: str  # 'product' or 'package'
    cogs: float
    preparation_fee: float
    shipping_fee: float
    opex_fee: float
    marketing_fee: float
    platform_fee: float
    total_costs: float
    net_price_excl_vat: float
    price_before_discount: float
    list_price_incl_vat: float
    net_profit: float
    net_margin_pct: float
    gross_margin_pct: float
    breakeven_price: float
