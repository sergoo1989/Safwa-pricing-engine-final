"""
نظام المساعدات والأدوات المشتركة
Professional Utilities Module
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """التحقق من صحة البيانات"""
    
    @staticmethod
    def validate_csv_structure(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """التحقق من هيكل ملف CSV"""
        missing_columns = [col for col in required_columns if col not in df.columns]
        return len(missing_columns) == 0, missing_columns
    
    @staticmethod
    def validate_numeric_column(df: pd.DataFrame, column: str) -> Tuple[bool, List[int]]:
        """التحقق من الأعمدة الرقمية"""
        try:
            invalid_rows = df[pd.to_numeric(df[column], errors='coerce').isna()].index.tolist()
            return len(invalid_rows) == 0, invalid_rows
        except Exception:
            return False, []
    
    @staticmethod
    def validate_unique_column(df: pd.DataFrame, column: str) -> Tuple[bool, List[Any]]:
        """التحقق من عدم تكرار القيم"""
        duplicates = df[df.duplicated(column, keep=False)][column].unique().tolist()
        return len(duplicates) == 0, duplicates


class PricingCalculator:
    """حاسبة التسعير المتقدمة"""
    
    @staticmethod
    def calculate_net_price(price_with_vat: float, vat_rate: float = 0.15) -> float:
        """حساب السعر الصافي من السعر شامل الضريبة"""
        return price_with_vat / (1 + vat_rate)
    
    @staticmethod
    def calculate_price_with_vat(net_price: float, vat_rate: float = 0.15) -> float:
        """حساب السعر شامل الضريبة"""
        return net_price * (1 + vat_rate)
    
    @staticmethod
    def calculate_price_after_discount(price: float, discount_rate: float) -> float:
        """حساب السعر بعد الخصم"""
        return price * (1 - discount_rate)
    
    @staticmethod
    def calculate_profit_margin(revenue: float, costs: float) -> float:
        """حساب هامش الربح"""
        if revenue == 0:
            return 0
        return (revenue - costs) / revenue
    
    @staticmethod
    def calculate_markup(costs: float, profit: float) -> float:
        """حساب نسبة الزيادة على التكلفة"""
        if costs == 0:
            return 0
        return profit / costs
    
    @staticmethod
    def calculate_breakeven_price(costs: float, vat_rate: float = 0.15) -> float:
        """حساب نقطة التعادل"""
        return costs * (1 + vat_rate)
    
    @staticmethod
    def calculate_target_price(costs: float, target_margin: float, vat_rate: float = 0.15) -> float:
        """حساب السعر المطلوب لتحقيق هامش ربح معين"""
        if target_margin >= 1:
            return float('inf')
        net_price = costs / (1 - target_margin)
        return net_price * (1 + vat_rate)


class ExportManager:
    """مدير التصدير للملفات"""
    
    @staticmethod
    def export_to_csv(df: pd.DataFrame, filename: str) -> bytes:
        """تصدير إلى CSV"""
        return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    
    @staticmethod
    def export_to_excel(df: pd.DataFrame, filename: str, sheet_name: str = 'Sheet1') -> bytes:
        """تصدير إلى Excel"""
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        return output.getvalue()
    
    @staticmethod
    def export_to_json(df: pd.DataFrame) -> str:
        """تصدير إلى JSON"""
        return df.to_json(orient='records', force_ascii=False, indent=2)


class ReportGenerator:
    """مولد التقارير الاحترافية"""
    
    @staticmethod
    def generate_summary_stats(df: pd.DataFrame, numeric_columns: List[str]) -> Dict[str, Dict[str, float]]:
        """توليد إحصائيات ملخصة"""
        stats = {}
        for col in numeric_columns:
            if col in df.columns:
                stats[col] = {
                    'mean': df[col].mean(),
                    'median': df[col].median(),
                    'std': df[col].std(),
                    'min': df[col].min(),
                    'max': df[col].max(),
                    'sum': df[col].sum(),
                    'count': df[col].count()
                }
        return stats
    
    @staticmethod
    def generate_profit_analysis(pricing_df: pd.DataFrame) -> Dict[str, Any]:
        """تحليل الربحية"""
        if pricing_df.empty:
            return {}
        
        return {
            'total_revenue': pricing_df['سعر البيع'].sum() if 'سعر البيع' in pricing_df.columns else 0,
            'total_costs': pricing_df['التكلفة'].sum() if 'التكلفة' in pricing_df.columns else 0,
            'total_profit': pricing_df['الربح'].sum() if 'الربح' in pricing_df.columns else 0,
            'avg_margin': pricing_df['هامش الربح %'].mean() if 'هامش الربح %' in pricing_df.columns else 0,
            'item_count': len(pricing_df),
            'profitable_items': len(pricing_df[pricing_df['الربح'] > 0]) if 'الربح' in pricing_df.columns else 0,
            'loss_items': len(pricing_df[pricing_df['الربح'] < 0]) if 'الربح' in pricing_df.columns else 0
        }


class DateTimeHelper:
    """مساعدات التاريخ والوقت"""
    
    @staticmethod
    def get_current_timestamp() -> str:
        """الحصول على الطابع الزمني الحالي"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def get_date_string() -> str:
        """الحصول على التاريخ الحالي"""
        return datetime.now().strftime('%Y-%m-%d')
    
    @staticmethod
    def parse_arabic_date(date_str: str) -> Optional[datetime]:
        """تحليل التاريخ بالعربي"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None


class FormatHelper:
    """مساعدات التنسيق"""
    
    @staticmethod
    def format_currency(amount: float, currency: str = 'SAR') -> str:
        """تنسيق العملة"""
        return f"{amount:,.2f} {currency}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 2) -> str:
        """تنسيق النسبة المئوية"""
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def format_number(number: float, decimals: int = 2) -> str:
        """تنسيق الأرقام"""
        return f"{number:,.{decimals}f}"


class ColorScheme:
    """نظام الألوان الاحترافي"""
    
    PRIMARY = "#0F766E"
    SECONDARY = "#475467"
    SUCCESS = "#15803D"
    WARNING = "#B45309"
    DANGER = "#B91C1C"
    INFO = "#2563EB"
    LIGHT = "#F6F7F9"
    DARK = "#111827"
    
    CHART_COLORS = [
        "#0F766E", "#2563EB", "#B45309", "#15803D", "#7C3AED",
        "#B91C1C", "#0891B2", "#9333EA", "#475467", "#CA8A04"
    ]
    
    @staticmethod
    def get_status_color(value: float, thresholds: Dict[str, float]) -> str:
        """الحصول على لون حسب القيمة"""
        if value >= thresholds.get('excellent', 0.20):
            return ColorScheme.SUCCESS
        elif value >= thresholds.get('good', 0.10):
            return ColorScheme.INFO
        elif value >= thresholds.get('acceptable', 0.05):
            return ColorScheme.WARNING
        else:
            return ColorScheme.DANGER
