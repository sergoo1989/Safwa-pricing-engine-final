"""
محرك التسعير المتقدم - Advanced Pricing Engine
Professional pricing calculation with comprehensive analysis
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class PricingResult:
    """نتيجة حساب التسعير الشاملة"""
    # Basic Info
    sku: str
    item_name: str
    item_type: str
    channel: str
    
    # Costs
    cogs: float
    shipping_fee: float
    preparation_fee: float
    platform_fee: float
    payment_fee: float
    marketing_fee: float
    admin_fee: float
    custom_fees: Dict[str, float]
    total_costs: float
    
    # Pricing
    net_price: float
    price_with_vat: float
    discount_rate: float
    price_after_discount: float
    
    # Profitability
    gross_profit: float
    net_profit: float
    profit_margin: float
    markup_percentage: float
    roi: float
    
    # Break-even Analysis
    breakeven_price: float
    breakeven_units: float
    safety_margin: float
    
    # Competitive Analysis
    market_price_min: Optional[float] = None
    market_price_max: Optional[float] = None
    price_positioning: Optional[str] = None  # 'low', 'medium', 'high', 'premium'
    
    # Recommendations
    recommended_price: Optional[float] = None
    price_alerts: List[str] = None
    
    def __post_init__(self):
        if self.price_alerts is None:
            self.price_alerts = []


class AdvancedPricingEngine:
    """محرك التسعير الاحترافي المتقدم"""
    
    def __init__(self):
        self.vat_rate = 0.15
        self.min_profit_margin = 0.05
        self.recommended_margin = 0.15
        self.excellent_margin = 0.25
    
    def calculate_comprehensive_pricing(
        self,
        sku: str,
        item_name: str,
        item_type: str,
        channel: str,
        cogs: float,
        channel_fees: Dict[str, float],
        shipping: float = 0,
        preparation: float = 0,
        price_with_vat: float = 0,
        discount_rate: float = 0,
        custom_fees: Optional[Dict[str, float]] = None,
        free_shipping_threshold: float = 0
    ) -> PricingResult:
        """حساب تسعير شامل مع تحليل متقدم"""
        
        if custom_fees is None:
            custom_fees = {}
        
        # Apply free shipping/preparation if applicable
        if price_with_vat >= free_shipping_threshold > 0:
            shipping = 0
            preparation = 0
        
        # price_with_vat = السعر شامل الضريبة قبل الخصم (A)
        price_before_discount = price_with_vat
        
        # حساب مبلغ الخصم ثم السعر بعد الخصم
        # مبلغ الخصم = A * نسبة_الخصم
        discount_amount = price_before_discount * discount_rate
        
        # السعر شامل الضريبة بعد الخصم = A - مبلغ_الخصم
        price_after_discount = price_before_discount - discount_amount
        
        # السعر غير شامل الضريبة بعد الخصم = السعر_شامل_بعد_الخصم / 1.15
        net_price = price_after_discount / (1 + self.vat_rate)
        
        # Calculate fees
        platform_fee = net_price * channel_fees.get('platform_pct', 0)
        payment_fee = net_price * channel_fees.get('payment_pct', 0)
        marketing_fee = net_price * channel_fees.get('marketing_pct', 0)
        admin_fee = net_price * channel_fees.get('opex_pct', 0)
        
        # Calculate custom fees
        custom_fees_total = {}
        for fee_name, fee_data in custom_fees.items():
            if fee_data.get('fee_type') == 'percentage':
                custom_fees_total[fee_name] = net_price * fee_data.get('amount', 0)
            else:
                custom_fees_total[fee_name] = fee_data.get('amount', 0)
        
        # Total costs
        total_costs = (
            cogs + shipping + preparation + platform_fee + payment_fee +
            marketing_fee + admin_fee + 
            sum(custom_fees_total.values())
        )
        
        # Profitability calculations
        gross_profit = net_price - cogs
        net_profit = net_price - total_costs
        profit_margin = net_profit / net_price if net_price > 0 else 0
        markup_percentage = net_profit / cogs if cogs > 0 else 0
        roi = net_profit / total_costs if total_costs > 0 else 0
        
        # Break-even analysis
        breakeven_price = total_costs * (1 + self.vat_rate)
        breakeven_units = total_costs / (net_price - cogs) if (net_price - cogs) > 0 else float('inf')
        safety_margin = (price_with_vat - breakeven_price) / price_with_vat if price_with_vat > 0 else 0
        
        # Generate alerts
        alerts = self._generate_price_alerts(
            profit_margin, price_with_vat, breakeven_price, cogs, net_price
        )
        
        # Recommended price
        recommended_price = self._calculate_recommended_price(
            cogs, channel_fees, shipping, preparation, custom_fees
        )
        
        return PricingResult(
            sku=sku,
            item_name=item_name,
            item_type=item_type,
            channel=channel,
            cogs=cogs,
            shipping_fee=shipping,
            preparation_fee=preparation,
            platform_fee=platform_fee,
            payment_fee=payment_fee,
            marketing_fee=marketing_fee,
            admin_fee=admin_fee,
            custom_fees=custom_fees_total,
            total_costs=total_costs,
            net_price=net_price,
            price_with_vat=price_with_vat,
            discount_rate=discount_rate,
            price_after_discount=price_after_discount,
            gross_profit=gross_profit,
            net_profit=net_profit,
            profit_margin=profit_margin,
            markup_percentage=markup_percentage,
            roi=roi,
            breakeven_price=breakeven_price,
            breakeven_units=breakeven_units,
            safety_margin=safety_margin,
            recommended_price=recommended_price,
            price_alerts=alerts
        )
    
    def _generate_price_alerts(
        self,
        profit_margin: float,
        price_with_vat: float,
        breakeven_price: float,
        cogs: float,
        net_price: float
    ) -> List[str]:
        """توليد تنبيهات التسعير"""
        alerts = []
        
        if profit_margin < 0:
            alerts.append("⛔ تحذير: السعر الحالي يحقق خسارة!")
        elif profit_margin < self.min_profit_margin:
            alerts.append(f"⚠️ تحذير: هامش الربح أقل من الحد الأدنى المقبول ({self.min_profit_margin*100}%)")
        elif profit_margin < self.recommended_margin:
            alerts.append(f"💡 ملاحظة: هامش الربح أقل من الموصى به ({self.recommended_margin*100}%)")
        elif profit_margin >= self.excellent_margin:
            alerts.append(f"✅ ممتاز: هامش ربح ممتاز ({profit_margin*100:.1f}%)")
        
        if price_with_vat < breakeven_price:
            alerts.append(f"🔴 خطر: السعر أقل من نقطة التعادل ({breakeven_price:.2f} SAR)")
        
        if net_price < cogs * 1.5:
            alerts.append("📊 ملاحظة: السعر قريب جداً من التكلفة، قد يكون هناك مجال لزيادة السعر")
        
        return alerts
    
    def _calculate_recommended_price(
        self,
        cogs: float,
        channel_fees: Dict[str, float],
        shipping: float,
        preparation: float,
        custom_fees: Optional[Dict[str, float]] = None
    ) -> float:
        """حساب السعر الموصى به"""
        
        # Calculate total percentage fees
        total_pct = (
            channel_fees.get('platform_pct', 0) +
            channel_fees.get('payment_pct', 0) +
            channel_fees.get('marketing_pct', 0) +
            channel_fees.get('opex_pct', 0)
        )
        
        # Fixed costs
        fixed_costs = cogs + shipping + preparation
        
        # Add custom fixed fees
        if custom_fees:
            for fee_name, fee_data in custom_fees.items():
                if fee_data.get('fee_type') == 'fixed':
                    fixed_costs += fee_data.get('amount', 0)
        
        # Calculate recommended net price (15% margin)
        denominator = 1 - total_pct - self.recommended_margin
        
        if denominator <= 0:
            return float('inf')
        
        net_price = fixed_costs / denominator
        
        # Return price with VAT
        return net_price * (1 + self.vat_rate)
    
    def calculate_price_at_margin(
        self,
        cogs: float,
        target_margin: float,
        channel_fees: Dict[str, float],
        shipping: float = 0,
        preparation: float = 0,
        custom_fees: Optional[Dict[str, float]] = None
    ) -> float:
        """حساب السعر المطلوب لتحقيق هامش ربح معين"""
        
        if custom_fees is None:
            custom_fees = {}
        
        # Calculate total percentage fees
        total_pct = (
            channel_fees.get('platform_pct', 0) +
            channel_fees.get('payment_pct', 0) +
            channel_fees.get('marketing_pct', 0) +
            channel_fees.get('opex_pct', 0)
        )
        
        # Fixed costs
        fixed_costs = cogs + shipping + preparation
        
        # Add custom fixed fees
        for fee_name, fee_data in custom_fees.items():
            if fee_data.get('fee_type') == 'fixed':
                fixed_costs += fee_data.get('amount', 0)
        
        # Calculate net price for target margin
        denominator = 1 - total_pct - target_margin
        
        if denominator <= 0:
            return float('inf')
        
        net_price = fixed_costs / denominator
        
        # Return price with VAT
        return net_price * (1 + self.vat_rate)
    
    def calculate_margin_scenarios(
        self,
        cogs: float,
        channel_fees: Dict[str, float],
        shipping: float = 0,
        preparation: float = 0,
        custom_fees: Optional[Dict[str, float]] = None
    ) -> Dict[float, float]:
        """حساب سيناريوهات هوامش ربح مختلفة"""
        
        scenarios = {}
        margins = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
        
        for margin in margins:
            price = self.calculate_price_at_margin(
                cogs, margin, channel_fees, shipping, preparation, custom_fees
            )
            if price != float('inf'):
                scenarios[margin] = price
        
        return scenarios
    
    def perform_sensitivity_analysis(
        self,
        base_cogs: float,
        base_price: float,
        channel_fees: Dict[str, float],
        shipping: float = 0,
        preparation: float = 0
    ) -> Dict[str, List[Dict[str, float]]]:
        """تحليل الحساسية للتغيرات في التكلفة والسعر"""
        
        results = {
            'cogs_sensitivity': [],
            'price_sensitivity': []
        }
        
        # COGS sensitivity (-20% to +20%)
        for change_pct in np.arange(-0.2, 0.21, 0.05):
            new_cogs = base_cogs * (1 + change_pct)
            net_price = base_price / (1 + self.vat_rate)
            
            total_pct = sum([
                channel_fees.get('platform_pct', 0),
                channel_fees.get('payment_pct', 0),
                channel_fees.get('marketing_pct', 0),
                channel_fees.get('opex_pct', 0)
            ])
            
            fees = net_price * total_pct
            total_costs = new_cogs + shipping + preparation + fees
            profit = net_price - total_costs
            margin = profit / net_price if net_price > 0 else 0
            
            results['cogs_sensitivity'].append({
                'change_pct': change_pct * 100,
                'cogs': new_cogs,
                'profit': profit,
                'margin': margin * 100
            })
        
        # Price sensitivity (-20% to +20%)
        for change_pct in np.arange(-0.2, 0.21, 0.05):
            new_price = base_price * (1 + change_pct)
            net_price = new_price / (1 + self.vat_rate)
            
            total_pct = sum([
                channel_fees.get('platform_pct', 0),
                channel_fees.get('payment_pct', 0),
                channel_fees.get('marketing_pct', 0),
                channel_fees.get('opex_pct', 0)
            ])
            
            fees = net_price * total_pct
            total_costs = base_cogs + shipping + preparation + fees
            profit = net_price - total_costs
            margin = profit / net_price if net_price > 0 else 0
            
            results['price_sensitivity'].append({
                'change_pct': change_pct * 100,
                'price': new_price,
                'profit': profit,
                'margin': margin * 100
            })
        
        return results
