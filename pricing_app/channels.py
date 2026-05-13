import json
import os
from typing import Dict, List
from dataclasses import dataclass, asdict, field

@dataclass
class CustomFee:
    """Custom fee for a channel"""
    name: str  # اسم الرسم
    amount: float  # المبلغ أو النسبة
    fee_type: str  # 'percentage' أو 'fixed'

@dataclass
class ChannelFees:
    """Channel fee structure"""
    channel_name: str = ""
    platform_pct: float = 0.03    # منصة %
    payment_pct: float = 0.025    # دفع %
    marketing_pct: float = 0.28   # تسويق %
    opex_pct: float = 0.04        # تشغيل %
    vat_rate: float = 0.15        # ضريبة %
    discount_rate: float = 0.10   # خصم %
    shipping_fixed: float = 20.0  # شحن ثابت
    preparation_fee: float = 6.0  # تحضير
    free_shipping_threshold: float = 0.0  # الحد الأدنى للشحن والتجهيز مجاني
    custom_fees: Dict[str, Dict] = field(default_factory=dict)  # رسوم إضافية مخصصة

def load_channels(filepath: str) -> Dict[str, ChannelFees]:
    """Load all channels from JSON file"""
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        channels = {}
        for channel_name, fees_dict in data.items():
            channels[channel_name] = ChannelFees(**fees_dict)
        return channels
    except Exception as e:
        print(f"Error loading channels: {e}")
        return {}

def save_channels(channels: Dict[str, ChannelFees], filepath: str):
    """Save all channels to JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    data = {}
    for channel_name, fees in channels.items():
        data[channel_name] = asdict(fees)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_channel_fees(channel_name: str, channels_file: str) -> ChannelFees:
    """Get fees for a specific channel"""
    channels = load_channels(channels_file)
    if channel_name in channels:
        return channels[channel_name]
    return None

def calculate_price_with_fees(cogs: float, channel_fees: ChannelFees, target_margin: float) -> Dict:
    """
    Calculate price with all fees
    
    الصيغة:
    السعر = COGS / (1 - (رسوم + هامش))
    """
    # Calculate total fees percentage
    total_fees_pct = (
        channel_fees.platform_pct +
        channel_fees.payment_pct +
        channel_fees.marketing_pct +
        channel_fees.opex_pct
    )
    
    # Calculate net price (before VAT)
    net_price_excl_vat = cogs / (1 - total_fees_pct - target_margin)
    
    # Calculate fees amounts
    platform_fee = net_price_excl_vat * channel_fees.platform_pct
    payment_fee = net_price_excl_vat * channel_fees.payment_pct
    marketing_fee = net_price_excl_vat * channel_fees.marketing_pct
    opex_fee = net_price_excl_vat * channel_fees.opex_pct
    
    # Apply discount
    discounted_price = net_price_excl_vat * (1 - channel_fees.discount_rate)
    
    # Add VAT
    price_with_vat = discounted_price * (1 + channel_fees.vat_rate)
    
    # Calculate profit
    profit = price_with_vat - cogs - (platform_fee + payment_fee + marketing_fee + opex_fee)
    
    return {
        'cogs': cogs,
        'platform_fee': platform_fee,
        'payment_fee': payment_fee,
        'marketing_fee': marketing_fee,
        'opex_fee': opex_fee,
        'total_fees': platform_fee + payment_fee + marketing_fee + opex_fee,
        'shipping_fee': channel_fees.shipping_fixed,
        'preparation_fee': channel_fees.preparation_fee,
        'net_price_excl_vat': net_price_excl_vat,
        'discount_rate': channel_fees.discount_rate,
        'discounted_price': discounted_price,
        'vat_amount': discounted_price * channel_fees.vat_rate,
        'price_with_vat': price_with_vat,
        'profit': profit,
        'margin_pct': (profit / price_with_vat * 100) if price_with_vat > 0 else 0
    }
