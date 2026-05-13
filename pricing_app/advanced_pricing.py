import pandas as pd
from typing import Dict

def calculate_breakeven_price(
    cogs: float,
    channel_fees: Dict,
    shipping: float = 0,
    preparation: float = 0,
    discount_rate: float = 0.1,
    vat_rate: float = 0.15,
    free_shipping_threshold: float = 0,
    custom_fees: Dict = None
) -> float:
    """
    حساب نقطة التعادل (السعر الذي يجعل الربح = 0)
    باستخدام Goal Seek logic
    
    المعادلة:
    نريد إيجاد السعر الصافي (D) بحيث:
    D - COGS - شحن - تجهيز - (D × admin%) - (D × marketing%) - (D × payment%) - رسوم مخصصة = 0
    
    D × (1 - admin% - marketing% - payment% - custom%) = COGS + شحن + تجهيز + رسوم مخصصة ثابتة
    
    ثم تحويل السعر الصافي إلى سعر شامل الضريبة قبل الخصم
    """
    
    if custom_fees is None:
        custom_fees = {}
    
    # حساب نسب الرسوم
    admin_pct = channel_fees.get('opex_pct', 0.04)
    marketing_pct = channel_fees.get('marketing_pct', 0.28)
    platform_pct = channel_fees.get('platform_pct', 0.0)
    payment_pct = channel_fees.get('payment_pct', 0.0)
    total_pct = admin_pct + marketing_pct + platform_pct + payment_pct
    
    # حساب الرسوم الثابتة والنسبية المخصصة
    custom_fixed_fees = 0
    custom_pct_fees = 0
    
    if custom_fees:
        for fee_name, fee_data in custom_fees.items():
            if fee_data.get('fee_type') == 'percentage':
                custom_pct_fees += fee_data['amount']
            else:
                custom_fixed_fees += fee_data['amount']
    
    # المجموع الثابت = COGS + شحن + تجهيز + رسوم مخصصة ثابتة
    fixed_costs = cogs + shipping + preparation + custom_fixed_fees
    
    # المجموع النسبي = admin% + marketing% + payment% + custom%
    total_pct_fees = total_pct + custom_pct_fees
    
    # السعر الصافي عند التعادل (D)
    # D × (1 - النسب) = التكاليف الثابتة
    # D = التكاليف الثابتة / (1 - النسب)
    if total_pct_fees >= 1:
        # إذا كانت النسب ≥ 100% لا يمكن الوصول للتعادل
        return 0
    
    breakeven_net = fixed_costs / (1 - total_pct_fees)
    
    # تحويل إلى سعر شامل الضريبة بعد الخصم
    # C = السعر الصافي (D) × (1 + ضريبة%)
    breakeven_with_vat = breakeven_net * (1 + vat_rate)
    
    # تحويل إلى سعر شامل الضريبة قبل الخصم
    # A = C / (1 - discount_rate)
    if discount_rate >= 1:
        breakeven_before_discount = 0
    else:
        breakeven_before_discount = breakeven_with_vat / (1 - discount_rate)
    
    return breakeven_before_discount

def calculate_price_breakdown(
    cogs: float,
    channel_fees: Dict,
    shipping: float = 0,
    preparation: float = 0,
    discount_rate: float = 0.1,
    vat_rate: float = 0.15,
    free_shipping_threshold: float = 0,
    custom_fees: Dict = None,
    price_with_vat: float = None,
    target_margin: float = 0.10
) -> Dict:
    """
    حساب السعر الكامل مع تفاصيل التكاليف والرسوم
    
    إذا تم تمرير price_with_vat:
    - نستخدم السعر المدخل مباشرة ونحسب العناصر بناءً عليه
    
    وإلا:
    - نحسب السعر بناءً على COGS والهامش المستهدف
    
    ملاحظة: رسوم المنصات لا تُحسب (تم إزالتها)
    """
    
    if custom_fees is None:
        custom_fees = {}
    
    # حساب نسبة الرسوم الإجمالية
    admin_pct = channel_fees.get('opex_pct', 0.04)  # مصاريف إدارية (H)
    marketing_pct = channel_fees.get('marketing_pct', 0.28)  # مصاريف تسويق (I)
    platform_pct = channel_fees.get('platform_pct', 0.0)  # رسوم المنصة (K)
    payment_pct = channel_fees.get('payment_pct', 0.0)  # رسوم الدفع
    
    # Step 1: حساب السعر الصافي بدون ضريبة وبدون خصم
    if price_with_vat is not None and price_with_vat > 0:
        # استخدام السعر المدخل من قبل المستخدم
        # A = سعر البيع شامل الضريبة قبل الخصم (المدخل)
        price_before_discount = price_with_vat
        
        # B = نسبة الخصم (بالفعل محسوبة في discount_rate)
        discount_amount = price_before_discount * discount_rate
        
        # C = السعر بعد الخصم شامل الضريبة
        price_after_discount = price_before_discount - discount_amount
        
        # D = السعر الصافي بدون ضريبة بعد الخصم
        net_price_excl_vat_and_discount = price_after_discount / (1 + vat_rate)
    else:
        # حساب السعر الذكي: نجرب تحقيق الهامش المستهدف تحت حد 98 أولاً
        total_fees_pct = admin_pct + marketing_pct + platform_pct + payment_pct
        
        # نجرب: هل يمكن تحقيق الهامش بدون شحن/تحضير؟
        def calc_price_for_margin(margin: float, include_shipping: bool) -> float:
            """حساب السعر المطلوب لتحقيق هامش معين"""
            fixed_costs = cogs
            if include_shipping:
                fixed_costs += shipping + preparation
            
            denom = 1 - total_fees_pct - margin
            if denom <= 0:
                return 0
            
            net_required = fixed_costs / denom
            price_with_vat_calc = net_required * (1 + vat_rate)
            return price_with_vat_calc / (1 - discount_rate)
        
        # نجرب السعر بدون شحن/تحضير
        price_without_shipping = calc_price_for_margin(target_margin, False)
        
        # إذا السعر بدون شحن < 98 → نستخدمه (شحن مجاني!)
        if free_shipping_threshold > 0 and price_without_shipping > 0 and price_without_shipping < free_shipping_threshold:
            price_before_discount = price_without_shipping
            net_price_excl_vat_and_discount = cogs / (1 - total_fees_pct - target_margin)
        else:
            # السعر >= 98 أو غير قابل للتحقيق → نضيف الشحن والتحضير
            price_with_shipping = calc_price_for_margin(target_margin, True)
            price_before_discount = price_with_shipping if price_with_shipping > 0 else price_without_shipping
            net_price_excl_vat_and_discount = (cogs + shipping + preparation) / (1 - total_fees_pct - target_margin)
        
        discount_amount = price_before_discount * discount_rate
        price_after_discount = price_before_discount - discount_amount
    
    # حساب الرسوم على السعر الصافي (D) أولاً
    admin_fee = net_price_excl_vat_and_discount * admin_pct      # H = D × نسبة
    marketing_fee = net_price_excl_vat_and_discount * marketing_pct  # I = D × نسبة
    platform_fee = net_price_excl_vat_and_discount * platform_pct    # K = D × نسبة
    payment_fee = net_price_excl_vat_and_discount * payment_pct

    total_fees = admin_fee + marketing_fee + platform_fee + payment_fee  # مجموع الرسوم النسبية
    
    # حساب الرسوم الإضافية المخصصة مع تتبع الثابت والنِسبي
    custom_fees_dict = {}
    custom_fees_total = 0
    custom_fixed_fees = 0
    custom_pct_fees = 0
    if custom_fees:
        for fee_name, fee_data in custom_fees.items():
            if fee_data.get('fee_type') == 'percentage':
                # نسبة من السعر بعد الخصم بدون ضريبة
                fee_amount = net_price_excl_vat_and_discount * fee_data['amount']
                custom_pct_fees += fee_data['amount']
            else:
                # مبلغ ثابت
                fee_amount = fee_data['amount']
                custom_fixed_fees += fee_amount
            custom_fees_dict[fee_name] = fee_amount
            custom_fees_total += fee_amount
    
    # تحديد ما إذا كان الشحن والتجهيز مجاني بناءً على حد القناة.
    # إذا كان السعر أقل من الحد، تتحمل القناة الشحن والتحضير حسب الإعداد.
    # إذا كان السعر أعلى من الحد أو لا يوجد حد، تضاف الرسوم كاملة.
    
    if free_shipping_threshold > 0 and price_before_discount < free_shipping_threshold:
        # السعر أقل من الحد → شحن وتحضير مجاني حسب سياسة المنصة
        actual_shipping = 0
        actual_preparation = 0
    else:
        # السعر أعلى من الحد أو لا يوجد حد → نضيف الرسوم كاملة
        actual_shipping = shipping
        actual_preparation = preparation

    # Step 3: حساب الربح ونقاط التسعير للهوامش المختلفة
    total_pct_fees = admin_pct + marketing_pct + platform_pct + payment_pct + custom_pct_fees  # مجموع النسب

    def price_for_margin(target_margin: float) -> float:
        """سعر البيع شامل الضريبة قبل الخصم لتحقيق هامش مستهدف مع احترام شرط الشحن المجاني.
        
        المنطق الجديد:
        1. نحاول أولاً حساب السعر بدون شحن/تحضير
        2. إذا كان هذا السعر < حد الشحن المجاني (98) ويحقق الهامش المطلوب → نستخدمه
        3. وإلا نضيف الشحن والتحضير ونحسب السعر الذي يحقق الهامش
        """

        denom = 1 - total_pct_fees - target_margin
        if denom <= 0 or discount_rate >= 1:
            return 0

        def calc_price(fixed_costs: float) -> float:
            net_required = fixed_costs / denom
            return (net_required * (1 + vat_rate)) / (1 - discount_rate)

        if free_shipping_threshold > 0:
            # أولاً: نجرب السعر بدون شحن/تحضير
            price_free_fees = calc_price(cogs + custom_fixed_fees)
            
            # إذا السعر بدون رسوم يقع تحت العتبة ويحقق الهامش المطلوب
            if price_free_fees > 0 and price_free_fees < free_shipping_threshold:
                # هذا يعني أن العميل سيحصل على شحن مجاني
                # والسعر هذا يحقق الهامش المطلوب بدون إضافة تكاليف شحن/تحضير
                return price_free_fees
            
            # ثانياً: إذا السعر >= العتبة أو لا يحقق الهامش، نضيف الشحن والتحضير
            price_with_fees = calc_price(cogs + shipping + preparation + custom_fixed_fees)
            return price_with_fees if price_with_fees > 0 else price_free_fees

        # لا توجد عتبة للشحن المجاني → دائماً نضيف الرسوم
        return calc_price(cogs + shipping + preparation + custom_fixed_fees)

    margin_prices = {
        0.00: price_for_margin(0.00),
        0.05: price_for_margin(0.05),
        0.10: price_for_margin(0.10),
        0.15: price_for_margin(0.15),
        0.20: price_for_margin(0.20),
    }

    breakeven_price = margin_prices[0.00]
    
    profit = net_price_excl_vat_and_discount - cogs - actual_shipping - actual_preparation - total_fees - custom_fees_total
    margin_pct = (profit / net_price_excl_vat_and_discount) if net_price_excl_vat_and_discount > 0 else 0
    
    return {
        # السعر
        'sale_price': price_before_discount,  # A - سعر البيع
        'discount_amount': discount_amount,  # B - مبلغ الخصم
        'discount_rate': discount_rate,  # نسبة الخصم
        'price_after_discount': price_after_discount,  # C - السعر بعد الخصم
        'vat_rate': vat_rate,  # نسبة الضريبة
        'net_price': net_price_excl_vat_and_discount,  # D - السعر الصافي بدون ضريبة
        
        # الرسوم الإضافية
        'custom_fees': custom_fees_dict,
        'custom_fees_total': custom_fees_total,
        
        # التكاليف
        'cogs': cogs,  # E - تكلفة البضاعة
        'preparation_fee': actual_preparation,  # F - رسوم التحضير (قد تكون 0 إذا تم تجاوز الحد)
        'shipping_fee': actual_shipping,  # G - رسوم الشحن (قد تكون 0 إذا تم تجاوز الحد)
        'admin_fee': admin_fee,  # H - مصاريف إدارية
        'marketing_fee': marketing_fee,  # I - مصاريف تسويق
        'payment_fee': payment_fee,
        'platform_fee': platform_fee,  # K - رسوم المنصات
        
        # الإجمالي والربح
        'total_costs_fees': cogs + actual_shipping + actual_preparation + total_fees + custom_fees_total,  # L - إجمالي التكاليف
        'profit': profit,  # M - الربح
        'margin_pct': margin_pct,  # N - نسبة الهامش
        'breakeven_price': breakeven_price,  # نقطة التعادل (سعر شامل الضريبة قبل الخصم)
        'margin_prices': margin_prices  # أسعار البيع المطلوبة لهوامش 0%/5%/10%/15%/20%
    }

def create_pricing_table(item_sku: str, item_type: str, cogs: float, channel_fees: Dict, 
                         shipping: float = 0, preparation: float = 0, target_margin: float = 0.10) -> pd.DataFrame:
    """إنشاء جدول تفاصيل التسعير الكامل"""
    
    breakdown = calculate_price_breakdown(
        cogs=cogs,
        channel_fees=channel_fees,
        shipping=shipping,
        preparation=preparation,
        target_margin=target_margin
    )
    
    # بناء الجدول حسب الصورة
    data = {
        'الحركات': [
            '',  # سعر البيع
            '',  # خصم
            '',  # سعر بعد خصم
            '',  # سعر صافي
            '',  # التكاليف والرسوم
            '',  # تكلفة البضاعة
            '',  # تجهيز
            '',  # شحن
            '',  # مصاريف إدارية
            '',  # مصاريف تسويق
            '',  # رسوم الدفع
            '',  # رسوم منصات
            '',  # إجمالي التكاليف
            '',  # الربح
            '',  # هامش الربح
            '',  # نقطة التعادل
        ],
        'البند': [
            'سعر البيع',
            'نسبة الخصم',
            'سعر بعد الخصم',
            'السعر الصافي (بدون ضريبة)',
            'التكاليف والرسوم',
            'تكلفة البضاعة (COGS)',
            'رسوم التحضير',
            'رسوم الشحن',
            'المصاريف الإدارية',
            'مصاريف التسويق',
            'رسوم الدفع',
            'رسوم المنصات',
            'إجمالي التكاليف والرسوم',
            'الربح',
            'هامش الربح',
            'نقطة التعادل',
        ],
        'المبلغ (SAR)': [
            f"{breakdown['sale_price']:.2f}",
            f"{breakdown['discount_amount']:.2f}",
            f"{breakdown['price_after_discount']:.2f}",
            f"{breakdown['net_price']:.2f}",
            '',
            f"{breakdown['cogs']:.2f}",
            f"{breakdown['preparation_fee']:.2f}",
            f"{breakdown['shipping_fee']:.2f}",
            f"{breakdown['admin_fee']:.2f}",
            f"{breakdown['marketing_fee']:.2f}",
            f"{breakdown.get('payment_fee', 0):.2f}",
            f"{breakdown['platform_fee']:.2f}",
            f"{breakdown['total_costs_fees']:.2f}",
            f"{breakdown['profit']:.2f}",
            f"{breakdown['margin_pct']*100:.1f}%",
            f"{breakdown['breakeven_price']:.2f}",
        ]
    }
    
    return pd.DataFrame(data), breakdown
