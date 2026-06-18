import streamlit as st
import pandas as pd
from datetime import datetime
from pricing_app.costing import resolve_component_cost
from pricing_app.models import ChannelFees
from pricing_app.channels import load_channels, save_channels, ChannelFees as ChannelFeesData
from pricing_app.advanced_pricing import calculate_price_breakdown, create_pricing_table
from pricing_app.ui_components import UIComponents, ChartBuilder, TableFormatter
from pricing_app.utils import ExportManager, FormatHelper, ColorScheme, DateTimeHelper
from pricing_app.advanced_pricing_engine import AdvancedPricingEngine
from pricing_app.zoho_loader import load_zoho_cost_data_from_frames, validate_zoho_export_frames
from pricing_app.quality import validate_commercial_readiness
from pricing_app.audit import append_audit_event, append_audit_events
from pricing_app.salla_prices import (
    FINAL_EXCL_VAT_COL,
    FINAL_INCL_VAT_COL,
    PRICE_SOURCE_COL,
    SALLA_MATCH_SKU_COL,
    SALLA_OUTPUT_FILE_NAME,
    add_customer_final_price_columns,
    build_cost_catalog,
    calculate_salla_price_review,
    count_valid_sku_values,
    detect_salla_sku_column,
    load_salla_export,
    set_salla_match_sku_column,
)
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# Page Configuration
st.set_page_config(
    page_title="محرك تسعير صفوة",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "محرك تسعير صفوة الاحترافي"
    }
)

# تحسين التخزين المؤقت
if 'cache_ttl' not in st.session_state:
    st.session_state.cache_ttl = 3600  # ساعة واحدة

# Commercial CSS Styling
st.markdown(
    """
<style>
    :root {
        --app-bg: #f6f7f9;
        --surface: #ffffff;
        --surface-muted: #f2f4f7;
        --border: #d9dee7;
        --text: #111827;
        --muted: #667085;
        --primary: #0f766e;
        --primary-hover: #115e59;
        --accent: #b45309;
        --success: #15803d;
        --warning: #b45309;
        --danger: #b91c1c;
        --info: #2563eb;
        --shadow: 0 1px 2px rgba(16, 24, 40, 0.06);
    }

    html, body, [class*="css"] {
        font-family: "Segoe UI", Tahoma, Arial, sans-serif;
        letter-spacing: 0;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--text);
    }

    .main .block-container {
        max-width: 1440px;
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        direction: rtl;
        background: var(--surface);
        border-left: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        background: var(--surface);
        padding-top: 1.25rem;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: var(--text);
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        justify-content: flex-start;
        background: transparent;
        color: #344054 !important;
        border: 1px solid transparent;
        border-radius: 8px;
        box-shadow: none;
        padding: 0.62rem 0.75rem;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: #eef7f6;
        border-color: #c8e2df;
        color: var(--primary) !important;
    }

    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--primary);
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 22px;
        box-shadow: var(--shadow);
    }

    .app-header h1 {
        margin: 0;
        color: var(--text);
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: 0;
    }

    .app-header p {
        margin: 6px 0 0;
        color: var(--muted);
        font-size: 0.95rem;
    }

    .app-kicker {
        color: var(--primary);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .app-header-meta {
        min-width: 150px;
        text-align: left;
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.5;
    }

    .app-header-meta strong {
        display: block;
        color: var(--primary);
        font-size: 0.9rem;
    }

    h1, h2, h3 {
        color: var(--text);
        font-weight: 700;
        letter-spacing: 0;
    }

    h1 {
        font-size: 1.75rem;
    }

    h2 {
        font-size: 1.35rem;
    }

    h3 {
        font-size: 1.1rem;
    }

    [data-testid="stMetric"] {
        background: var(--surface);
        padding: 14px 16px;
        border-radius: 8px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
    }

    .stButton > button {
        background: var(--surface);
        color: var(--text);
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        font-weight: 600;
        box-shadow: none;
        transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }

    .stButton > button:hover {
        background: #f8fafc;
        border-color: var(--primary);
        color: var(--primary);
    }

    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: var(--primary);
        border-color: var(--primary);
        color: #ffffff;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        background: var(--primary-hover);
        border-color: var(--primary-hover);
        color: #ffffff;
    }

    [data-testid="stDataFrame"] {
        border-radius: 8px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        overflow: hidden;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        color: var(--muted);
        padding: 8px 12px;
    }

    .stTabs [aria-selected="true"] {
        color: var(--primary);
        background: #eef7f6;
    }

    .stAlert {
        border-radius: 8px;
        border: 1px solid var(--border);
        box-shadow: none;
    }

    .stSuccess {
        background-color: #ecfdf3;
        border-right: 4px solid var(--success);
    }

    .stWarning {
        background-color: #fffbeb;
        border-right: 4px solid var(--warning);
    }

    .stError {
        background-color: #fef2f2;
        border-right: 4px solid var(--danger);
    }

    .stInfo {
        background-color: #eff6ff;
        border-right: 4px solid var(--info);
    }

    div[data-testid="stExpander"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        box-shadow: var(--shadow);
    }

    input, textarea, [data-baseweb="select"] > div {
        border-radius: 8px !important;
    }

    @media (max-width: 768px) {
        .app-header {
            align-items: flex-start;
            flex-direction: column;
        }

        .app-header-meta {
            text-align: right;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)
# ========== دوال محسّنة للأداء ==========

@st.cache_data(ttl=3600, show_spinner=False)
def load_pricing_data_cached(products_file, packages_file):
    """تحميل بيانات التسعير مع تخزين مؤقت"""
    products_df = None
    packages_df = None
    
    if os.path.exists(products_file):
        products_df = pd.read_csv(products_file, low_memory=False)
    if os.path.exists(packages_file):
        packages_df = pd.read_csv(packages_file, low_memory=False)
    
    return products_df, packages_df

# Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state.page = "main"

ALLOWED_PAGES = {
    "main",
    "upload",
    "cogs",
    "settings",
    "pricing",
    "salla_review",
    "profit_margins",
    "custom_package",
    "history",
}
if st.session_state.page not in ALLOWED_PAGES:
    st.session_state.page = "main"

# Commercial Header
st.markdown(
    """
<div class="app-header" dir="rtl">
    <div>
        <div class="app-kicker">Safwa Pricing Engine</div>
        <h1>محرك تسعير صفوة</h1>
        <p>تسعير تجاري مبني على تكلفة Zoho ومتوسط تقييم المخزون</p>
    </div>
    <div class="app-header-meta">
        <span>Zoho Costing</span>
        <strong>وضع تجاري</strong>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


def load_all_data():
    upload_frames = st.session_state.get("zoho_upload_frames")
    if not upload_frames:
        raise FileNotFoundError("ارفع ملفات Zoho في هذه الجلسة قبل استخدام صفحات التسعير.")

    materials, product_recipes, products_summary, package_compositions, packages_summary = load_zoho_cost_data_from_frames(
        upload_frames["items"],
        upload_frames["composites"],
        upload_frames["valuation"],
    )
    return materials, product_recipes, products_summary, package_compositions, packages_summary


def load_quality_report(materials, product_recipes, products_summary, package_compositions, packages_summary):
    return validate_commercial_readiness(
        materials,
        product_recipes,
        products_summary,
        package_compositions,
        packages_summary,
    )


try:
    materials, product_recipes, products_summary, package_compositions, packages_summary = load_all_data()
    quality_report = load_quality_report(
        materials,
        product_recipes,
        products_summary,
        package_compositions,
        packages_summary,
    )
except Exception as e:
    materials = product_recipes = products_summary = package_compositions = packages_summary = None
    quality_report = None
    # إذا كان المستخدم قد طلب صفحة الرفع، انتقل إليها بدون إيقاف
    if st.session_state.get("page") not in {"upload", "salla_review"}:
        # رسالة ترحيبية بدلاً من رسالة خطأ
        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-top: 3px solid #0f766e;
                    padding: 24px; border-radius: 8px; text-align: right; color: #111827; margin: 20px 0;
                    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <h1 style="margin: 0; font-size: 1.8rem; color: #111827;">مرحباً بك في محرك تسعير صفوة</h1>
            <p style="font-size: 1rem; margin: 10px 0 0 0; color: #667085;">لنبدأ بإعداد البيانات الأساسية</p>
        </div>
        """, unsafe_allow_html=True)

        st.info("""
### ملفات Zoho المطلوبة

1. **Item** - ملف البنود.
2. **Composite Item** - ملف البكجات والتجميعات.
3. **Inventory Valuation Summary** - ملف تقييم المخزون.

انتقل إلى صفحة **رفع الملفات** وارفع الملفات الثلاثة ليتم تحديث التكلفة مباشرة من Zoho.
        """)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("فتح صفحة رفع ملفات Zoho", type="primary", use_container_width=True):
                st.session_state.page = "upload"
                st.rerun()

        st.stop()



def render_commercial_readiness(report, key_prefix: str = "readiness", compact: bool = False):
    if report is None:
        st.warning("ارفع ملفات Zoho الثلاثة أولا حتى يتم إنشاء تقرير جاهزية البيانات.")
        if st.button("فتح صفحة رفع ملفات Zoho", type="primary", width="stretch", key=f"{key_prefix}_open_upload"):
            st.session_state.page = "upload"
            st.rerun()
        return

    status_text = "جاهز للتشغيل التجاري" if report.is_ready else "يحتاج مراجعة قبل التشغيل"
    if report.is_ready:
        st.success(f"{status_text} - آخر فحص: {report.checked_at}")
    else:
        st.error(f"{status_text} - يوجد {report.critical_count} مشكلة حرجة قبل اعتماد الأسعار")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("مواد بتكلفة", report.total_materials)
    col2.metric("منتجات", report.total_products)
    col3.metric("بكجات", report.total_packages)
    col4.metric("ملاحظات", report.issue_count)

    if not report.issues.empty:
        container = st.expander("تفاصيل ملاحظات الجاهزية", expanded=not compact)
        with container:
            st.dataframe(report.issues, width="stretch", hide_index=True)
            st.download_button(
                "تنزيل تقرير الجاهزية CSV",
                data=report.issues.to_csv(index=False, encoding="utf-8-sig"),
                file_name="commercial_readiness_report.csv",
                mime="text/csv",
                width="stretch",
                key=f"{key_prefix}_download",
            )


# Initialize advanced pricing engine
pricing_engine = AdvancedPricingEngine()

# Sidebar Navigation
with st.sidebar:
    st.markdown("### القائمة الرئيسية")

    # Navigation buttons - vertical layout
    if st.button("رفع الملفات", help="رفع الملفات", key="btn_upload", width="stretch"):
        st.session_state.page = "upload"

    if st.button("تكلفة البضاعة", help="تكلفة البضاعة", key="btn_cogs", width="stretch"):
        st.session_state.page = "cogs"

    if st.button("المنصات", help="إعدادات المنصات", key="btn_settings", width="stretch"):
        st.session_state.page = "settings"

    if st.button(
        "تسعير منتج/بكج فردي", help="التسعير للمنتج أو البكج الفردي", key="btn_pricing", width="stretch"
    ):
        st.session_state.page = "pricing"

    if st.button("مقارنة اسعار سلة بالتكلفة", help="سعر بيع سلة ناقص تكلفة البضاعة ورسوم المنصة", key="btn_salla_review", width="stretch"):
        st.session_state.page = "salla_review"

    if st.button("تسعير منصة كاملة", help="تسعير منصة كاملة", key="btn_profit_margins", width="stretch"):
        st.session_state.page = "profit_margins"
    
    if st.button("بكجات جديدة", help="إنشاء بكج مخصص جديد", key="btn_custom_package", width="stretch"):
        st.session_state.page = "custom_package"

    if st.button("السجلات المحفوظة", help="عرض وتحميل السجلات المحفوظة", key="btn_history", width="stretch"):
        st.session_state.page = "history"


# Page: Upload Files
if st.session_state.page == "upload":
    st.header("رفع الملفات")
    st.markdown("---")

    # Clear data button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ مسح جميع البيانات", type="secondary", width="stretch"):
            # Confirm deletion
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = True
                st.rerun()

    # Show confirmation dialog
    if st.session_state.get("confirm_delete", False):
        st.warning("⚠️ هل أنت متأكد من حذف جميع البيانات؟ هذا الإجراء لا يمكن التراجع عنه!")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ نعم، حذف الكل"):
                try:
                    data_files = [
                        "data/zoho_items.csv",
                        "data/zoho_composite_items.csv",
                        "data/zoho_inventory_valuation.csv",
                        f"data/{SALLA_OUTPUT_FILE_NAME}",
                        "data/pricing_history.csv",
                        "data/pricing_audit_log.csv",
                        "data/pricing_history_test.csv",
                    ]
                    deleted_files = []

                    for file in data_files:
                        if os.path.exists(file):
                            os.remove(file)
                            deleted_files.append(file)

                    st.session_state.pop("zoho_upload_frames", None)
                    st.session_state.pop("salla_prices_df", None)
                    st.session_state.pop("current_pricing_result", None)
                    st.session_state.pop("priced_results", None)

                    if deleted_files:
                        st.success(f"✅ تم حذف {len(deleted_files)} ملف بنجاح")
                        st.cache_data.clear()
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.info("لا توجد ملفات للحذف")
                        st.session_state.confirm_delete = False
                except Exception as e:
                    st.error(f"خطأ في حذف البيانات: {e}")
                    st.session_state.confirm_delete = False

        with col2:
            if st.button("❌ لا، إلغاء"):
                st.session_state.confirm_delete = False
                st.rerun()

    st.markdown("---")

    st.subheader("رفع ملفات Zoho")
    st.info(
        "ارفع ملفات Zoho الثلاثة: Item، Composite Item، و Inventory Valuation Summary. "
        "يمكن رفع ملف تقييم المخزون كما ينزل من Zoho بدون تعديل. "
        "سيتم اعتماد متوسط تقييم المخزون أولا، ثم Purchase Rate عند عدم وجود متوسط صالح."
    )

    def read_uploaded_table(uploaded_file):
        if uploaded_file.name.lower().endswith(".csv"):
            return pd.read_csv(uploaded_file, encoding="utf-8-sig", low_memory=False)
        return pd.read_excel(uploaded_file, dtype=object)

    zoho_items_file = st.file_uploader("ملف البنود Item", type=["csv", "xlsx"], key="upload_zoho_items")
    zoho_composites_file = st.file_uploader(
        "ملف البكجات Composite Item", type=["csv", "xlsx"], key="upload_zoho_composites"
    )
    zoho_valuation_file = st.file_uploader(
        "ملف تقييم المخزون Inventory Valuation Summary", type=["csv", "xlsx"], key="upload_zoho_valuation"
    )

    if zoho_items_file and zoho_composites_file and zoho_valuation_file:
        try:
            zoho_items_df = read_uploaded_table(zoho_items_file)
            zoho_composites_df = read_uploaded_table(zoho_composites_file)
            zoho_valuation_df = read_uploaded_table(zoho_valuation_file)
            upload_validation = validate_zoho_export_frames(zoho_items_df, zoho_composites_df, zoho_valuation_df)

            invalid_uploads = upload_validation[upload_validation["status"] != "valid"]
            if not invalid_uploads.empty:
                st.error("ملفات Zoho غير مكتملة. لن يتم الحفظ قبل إصلاح الأعمدة الناقصة.")
                st.dataframe(upload_validation, width="stretch", hide_index=True)
                st.stop()

            c1, c2, c3 = st.columns(3)
            c1.metric("Item rows", len(zoho_items_df))
            c2.metric("Composite rows", len(zoho_composites_df))
            c3.metric("Valuation rows", len(zoho_valuation_df))

            st.dataframe(zoho_items_df.head(20), width="stretch")

            if st.button("استخدام ملفات Zoho في هذه الجلسة", type="primary", width="stretch"):
                st.session_state["zoho_upload_frames"] = {
                    "items": zoho_items_df.copy(),
                    "composites": zoho_composites_df.copy(),
                    "valuation": zoho_valuation_df.copy(),
                }
                st.cache_data.clear()
                st.success("تم تحميل ملفات Zoho لهذه الجلسة. لن يتم حفظ الملفات، وستحتاج رفعها مرة أخرى عند فتح التطبيق من جديد.")
                st.rerun()
        except Exception as e:
            st.error(f"خطأ في قراءة ملفات Zoho: {e}")
    else:
        if st.session_state.get("zoho_upload_frames"):
            st.success("ملفات Zoho محملة في هذه الجلسة وسيتم استخدامها في حساب التكلفة.")
        else:
            st.warning("ارفع الملفات الثلاثة لحساب التكلفة. لا يتم استخدام أي ملفات محفوظة.")

    st.markdown("---")
    st.subheader("رفع ملف أسعار سلة")
    st.info(
        "ارفع ملف Products Prices من سلة بصيغة Excel أو CSV. سيتم استخراج السعر الفعلي للعميل من "
        "سعر المنتج والسعر المخفض، ثم استخدامه في هذه الجلسة فقط داخل صفحة مقارنة اسعار سلة بالتكلفة."
    )

    salla_prices_file = st.file_uploader(
        "ملف أسعار المنتجات من سلة",
        type=["csv", "xlsx", "xls"],
        key="upload_salla_prices",
    )
    if salla_prices_file:
        try:
            salla_raw_df = load_salla_export(salla_prices_file)
            salla_result_df, salla_summary = add_customer_final_price_columns(salla_raw_df)

            detected_sku_col = detect_salla_sku_column(salla_result_df)
            sku_options = list(salla_result_df.columns)
            default_sku_index = sku_options.index(detected_sku_col) if detected_sku_col in sku_options else 0
            selected_salla_sku_col = st.selectbox(
                "اختر عمود SKU من ملف سلة للمطابقة مع Zoho",
                options=sku_options,
                index=default_sku_index,
                key="upload_salla_sku_column",
                help="المقارنة تعتمد على هذا العمود فقط. اسم المنتج لا يستخدم في المطابقة.",
            )
            salla_result_df = set_salla_match_sku_column(salla_result_df, selected_salla_sku_col)
            valid_sku_count = count_valid_sku_values(salla_result_df, SALLA_MATCH_SKU_COL)
            if valid_sku_count == 0:
                st.warning("العمود المختار لا يحتوي SKU صالح. اختر عمود SKU الصحيح قبل الاستخدام.")
            else:
                st.success(f"تم العثور على {valid_sku_count} قيمة SKU صالحة في العمود المختار.")
                st.session_state["salla_prices_df"] = salla_result_df.copy()
                st.caption("تم ربط ملف سلة بهذه الجلسة تلقائياً. افتح صفحة المقارنة وسيظهر الجدول مباشرة.")

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("إجمالي الصفوف", salla_summary["total_rows"])
            s2.metric("باستخدام السعر المخفض", salla_summary["discount_rows"])
            s3.metric("باستخدام سعر المنتج", salla_summary["regular_rows"])
            s4.metric("سعر نهائي مفقود", salla_summary["missing_final_price_rows"])

            preview_cols = [
                col
                for col in [
                    "No.",
                    "أسم المنتج",
                    "اسم المنتج",
                    "رمز المنتج sku",
                    SALLA_MATCH_SKU_COL,
                    "سعر المنتج",
                    "السعر المخفض",
                    FINAL_EXCL_VAT_COL,
                    FINAL_INCL_VAT_COL,
                    PRICE_SOURCE_COL,
                ]
                if col in salla_result_df.columns
            ]
            st.dataframe(salla_result_df[preview_cols].head(30), width="stretch", hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("فتح صفحة مقارنة اسعار سلة بالتكلفة", type="primary", width="stretch"):
                    st.session_state["salla_prices_df"] = salla_result_df.copy()
                    st.cache_data.clear()
                    st.session_state.page = "salla_review"
                    st.rerun()
            with c2:
                st.download_button(
                    "تنزيل الملف المعالج",
                    data=ExportManager.export_to_excel(
                        salla_result_df,
                        SALLA_OUTPUT_FILE_NAME,
                        sheet_name="salla_prices",
                    ),
                    file_name=SALLA_OUTPUT_FILE_NAME,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                )
        except Exception as e:
            st.error(f"خطأ في قراءة ملف أسعار سلة: {e}")
    elif st.session_state.get("salla_prices_df") is not None:
        st.success("ملف أسعار سلة محمل في هذه الجلسة وسيتم استخدامه في المقارنة.")
        if st.button("فتح صفحة مقارنة اسعار سلة بالتكلفة", type="primary", width="stretch"):
            st.session_state.page = "salla_review"
            st.rerun()
    else:
        st.warning("ارفع ملف أسعار سلة لاستخدامه في هذه الجلسة. لا يتم استخدام أي ملف محفوظ.")

# Page: COGS (Cost of Goods Sold)
elif st.session_state.page == "cogs":
    st.header("تكلفة البضاعة (COGS)")
    st.markdown("---")

    st.subheader("جاهزية البيانات للتشغيل التجاري")
    render_commercial_readiness(quality_report, key_prefix="cogs_readiness")
    st.markdown("---")

    # Validation checks
    st.subheader("التحقق من صحة البيانات")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("إجمالي المواد الخام", len(materials))

    with col2:
        st.metric("إجمالي المنتجات", len(product_recipes))

    with col3:
        st.metric("إجمالي البكجات", len(package_compositions))

    st.markdown("---")

    # Validation: Check Products have Materials
    st.subheader("التحقق من المنتجات")

    products_warnings = []
    for product_sku, materials_dict in product_recipes.items():
        if not materials_dict:
            products_warnings.append(f"المنتج {product_sku} بدون مواد خام")
        else:
            missing_materials = []
            for material_code in materials_dict.keys():
                if material_code not in materials:
                    missing_materials.append(material_code)

            if missing_materials:
                products_warnings.append(f"المنتج {product_sku} يحتاج مواد غير موجودة: {', '.join(missing_materials)}")

    if products_warnings:
        st.warning(f"وجدنا {len(products_warnings)} تحذيرات في المنتجات:")
        for warning in products_warnings:
            st.write(warning)
    else:
        st.success("جميع المنتجات لديها مواد خام موجودة")

    st.markdown("---")

    # Validation: Check Packages have Products
    st.subheader("التحقق من البكجات")

    packages_warnings = []
    product_skus = list(product_recipes.keys())
    package_skus = list(package_compositions.keys())
    material_skus = list(materials.keys())

    for package_sku, components_dict in package_compositions.items():
        if not components_dict:
            packages_warnings.append(f"الباقة {package_sku} بدون مكونات")
        else:
            missing_components = []
            for component_sku in components_dict.keys():
                # Check if component exists as product, package, or material
                if (
                    component_sku not in product_skus
                    and component_sku not in package_skus
                    and component_sku not in material_skus
                ):
                    missing_components.append(component_sku)

            if missing_components:
                packages_warnings.append(
                    f"الباقة {package_sku} تحتوي على مكونات غير موجودة: {', '.join(missing_components)}"
                )

    if packages_warnings:
        st.warning(f"وجدنا {len(packages_warnings)} تحذيرات في البكجات:")
        for warning in packages_warnings:
            st.write(warning)
    else:
        st.success("جميع البكجات لديها مكونات موجودة")

    st.markdown("---")

    # COGS Calculation Table
    st.subheader("جدول حساب تكلفة البضاعة")

    cogs_data = []

    # Helper function to calculate cost of any component (material, product, or package)
    def calculate_component_cost(sku, component_type="product"):
        return resolve_component_cost(sku, materials, product_recipes, package_compositions)

    # Product COGS
    st.write("**تكلفة المنتجات:**")
    for product_sku, materials_dict in product_recipes.items():
        product_name = products_summary[products_summary["Product_SKU"] == product_sku]["Product_Name"].values
        product_name = product_name[0] if len(product_name) > 0 else product_sku

        total_cost = calculate_component_cost(product_sku, "product")
        details = []

        for material_code, quantity in materials_dict.items():
            component_cost = calculate_component_cost(material_code, "material")
            if component_cost > 0:
                cost = component_cost * quantity
                details.append(f"{material_code}: {quantity} x {component_cost:.2f} = {cost:.2f}")

        cogs_data.append(
            {
                "النوع": "منتج",
                "SKU": product_sku,
                "الاسم": product_name,
                "التكلفة": total_cost,
                "التفاصيل": " | ".join(details) if details else "بدون مواد",
            }
        )

    # Package COGS
    st.write("**تكلفة البكجات:**")
    for package_sku, components_dict in package_compositions.items():
        package_name = packages_summary[packages_summary["Package_SKU"] == package_sku]["Package_Name"].values
        package_name = package_name[0] if len(package_name) > 0 else package_sku

        total_cost = 0
        details = []

        for component_sku, quantity in components_dict.items():
            # Determine component type and calculate its cost
            if component_sku in product_recipes:
                # It's a product
                comp_cost = calculate_component_cost(component_sku, "product")
                comp_type = "منتج"
            elif component_sku in package_compositions:
                # It's a package
                comp_cost = calculate_component_cost(component_sku, "package")
                comp_type = "بكج"
            elif component_sku in materials:
                # It's a material
                comp_cost = calculate_component_cost(component_sku, "material")
                comp_type = "مادة"
            else:
                comp_cost = 0
                comp_type = "غير معروف"

            cost = comp_cost * quantity
            total_cost += cost
            details.append(f"{component_sku} ({comp_type}): {quantity} x {comp_cost:.2f} = {cost:.2f}")

        cogs_data.append(
            {
                "النوع": "بكج",
                "SKU": package_sku,
                "الاسم": package_name,
                "التكلفة": total_cost,
                "التفاصيل": " | ".join(details) if details else "بدون مكونات",
            }
        )

    cogs_df = pd.DataFrame(cogs_data)
    if cogs_df.empty:
        # Ensure expected columns exist to avoid KeyError when data is missing
        cogs_df = pd.DataFrame(columns=["النوع", "SKU", "الاسم", "التكلفة", "التفاصيل"])

    # Separate dataframes for products and packages
    products_cogs_df = cogs_df[cogs_df["النوع"] == "منتج"].copy()
    packages_cogs_df = cogs_df[cogs_df["النوع"] == "بكج"].copy()

    # Products Table
    st.write("**جدول تكلفة المنتجات:**")
    if len(products_cogs_df) > 0:
        # Filter and Export for Products
        col_filter, col_export = st.columns([3, 1])
        with col_filter:
            products_search = st.text_input(
                "🔍 بحث في المنتجات (SKU أو الاسم)", key="products_search", placeholder="ابحث..."
            )
        with col_export:
            st.download_button(
                "📥 تصدير المنتجات",
                data=products_cogs_df[["SKU", "الاسم", "التكلفة", "التفاصيل"]].to_csv(
                    index=False, encoding="utf-8-sig"
                ),
                file_name="products_cogs.csv",
                mime="text/csv",
                width="stretch",
            )

        # Apply filter
        filtered_products = products_cogs_df
        if products_search:
            filtered_products = products_cogs_df[
                products_cogs_df["SKU"].str.contains(products_search, case=False, na=False)
                | products_cogs_df["الاسم"].str.contains(products_search, case=False, na=False)
            ]

        st.dataframe(
            filtered_products[["SKU", "الاسم", "التكلفة", "التفاصيل"]].style.format({"التكلفة": "{:.2f} SAR"}),
            width="stretch",
        )
        st.caption(f"عرض {len(filtered_products)} من {len(products_cogs_df)} منتج")
    else:
        st.info("لا توجد منتجات")

    st.markdown("---")

    # Packages Table
    st.write("**جدول تكلفة البكجات:**")
    if len(packages_cogs_df) > 0:
        # Filter and Export for Packages
        col_filter_pkg, col_export_pkg = st.columns([3, 1])
        with col_filter_pkg:
            packages_search = st.text_input(
                "🔍 بحث في البكجات (SKU أو الاسم)", key="packages_search", placeholder="ابحث..."
            )
        with col_export_pkg:
            st.download_button(
                "📥 تصدير البكجات",
                data=packages_cogs_df[["SKU", "الاسم", "التكلفة", "التفاصيل"]].to_csv(
                    index=False, encoding="utf-8-sig"
                ),
                file_name="packages_cogs.csv",
                mime="text/csv",
                width="stretch",
            )

        # Apply filter
        filtered_packages = packages_cogs_df
        if packages_search:
            filtered_packages = packages_cogs_df[
                packages_cogs_df["SKU"].str.contains(packages_search, case=False, na=False)
                | packages_cogs_df["الاسم"].str.contains(packages_search, case=False, na=False)
            ]

        st.dataframe(
            filtered_packages[["SKU", "الاسم", "التكلفة", "التفاصيل"]].style.format({"التكلفة": "{:.2f} SAR"}),
            width="stretch",
        )
        st.caption(f"عرض {len(filtered_packages)} من {len(packages_cogs_df)} بكج")
    else:
        st.info("لا توجد بكجات")

    # Summary Statistics
    st.subheader("إحصائيات التكاليف")

    col1, col2, col3, col4 = st.columns(4)

    products_cogs = products_cogs_df["التكلفة"]
    packages_cogs = packages_cogs_df["التكلفة"]

    with col1:
        st.metric("متوسط تكلفة المنتج", f"{products_cogs.mean():.2f} SAR")

    with col2:
        st.metric("أعلى تكلفة منتج", f"{products_cogs.max():.2f} SAR" if len(products_cogs) > 0 else "لا يوجد")

    with col3:
        st.metric("متوسط تكلفة الباقة", f"{packages_cogs.mean():.2f} SAR")

    with col4:
        st.metric("أعلى تكلفة باقة", f"{packages_cogs.max():.2f} SAR" if len(packages_cogs) > 0 else "لا يوجد")

    # Visualization - Separate charts for products and packages
    st.markdown("---")
    st.subheader("رسم بياني - تكاليف المنتجات")

    if len(products_cogs_df) > 0:
        fig_products = px.bar(
            products_cogs_df,
            x="SKU",
            y="التكلفة",
            title="تكلفة المنتجات (COGS)",
            labels={"التكلفة": "التكلفة (SAR)", "SKU": "رمز المنتج"},
            color="التكلفة",
            color_continuous_scale="Blues",
            text="التكلفة",
        )
        fig_products.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_products.update_layout(xaxis_tickangle=-45, height=500, hovermode="x unified", showlegend=False)
        st.plotly_chart(fig_products, width="stretch")
    else:
        st.info("لا توجد منتجات")

    st.markdown("---")
    st.subheader("رسم بياني - تكاليف البكجات")

    if len(packages_cogs_df) > 0:
        fig_packages = px.bar(
            packages_cogs_df,
            x="SKU",
            y="التكلفة",
            title="تكلفة البكجات (COGS)",
            labels={"التكلفة": "التكلفة (SAR)", "SKU": "رمز الباقة"},
            color="التكلفة",
            color_continuous_scale="Greens",
            text="التكلفة",
        )
        fig_packages.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_packages.update_layout(xaxis_tickangle=-45, height=500, hovermode="x unified", showlegend=False)
        st.plotly_chart(fig_packages, width="stretch")
    else:
        st.info("لا توجد بكجات")

    st.markdown("---")

    # Summary charts - Distribution
    st.subheader("الرسوم البيانية الملخصة")

    col_summary1, col_summary2, col_summary3 = st.columns(3)

    # Chart 1: Distribution by Type
    with col_summary1:
        st.write("**توزيع التكاليف حسب النوع**")
        type_summary = cogs_df.groupby("النوع")["التكلفة"].sum().reset_index()
        fig_pie = px.pie(
            type_summary,
            values="التكلفة",
            names="النوع",
            title="نسبة التكاليف",
            color_discrete_map={"منتج": "#0f766e", "بكج": "#b45309"},
            labels={"التكلفة": "التكلفة (SAR)"},
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, width="stretch")

    # Chart 2: Top 10 Items
    with col_summary2:
        st.write("**أعلى 10 عناصر تكلفة**")
        # Ensure numeric dtype for cost to avoid errors when data is empty or mixed
        cogs_df["التكلفة"] = pd.to_numeric(cogs_df["التكلفة"], errors="coerce").fillna(0)
        top_items = cogs_df.nlargest(10, "التكلفة")[["SKU", "النوع", "التكلفة"]].copy()
        fig_top = px.bar(
            top_items,
            y="SKU",
            x="التكلفة",
            orientation="h",
            color="النوع",
            title="أعلى العناصر تكلفة",
            labels={"التكلفة": "التكلفة (SAR)", "SKU": "رمز العنصر"},
            color_discrete_map={"منتج": "#0f766e", "بكج": "#b45309"},
            text="التكلفة",
        )
        fig_top.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_top.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_top, width="stretch")

    # Chart 3: Statistics Summary
    with col_summary3:
        st.write("**إحصائيات ملخصة**")

        # Create summary statistics dataframe
        stats_data = {
            "البيان": [
                "إجمالي المنتجات",
                "إجمالي البكجات",
                "إجمالي التكاليف",
                "متوسط تكلفة المنتج",
                "متوسط تكلفة الباقة",
                "أعلى منتج تكلفة",
                "أعلى بكجة تكلفة",
            ],
            "القيمة": [
                f"{len(products_cogs_df)}",
                f"{len(packages_cogs_df)}",
                f"{cogs_df['التكلفة'].sum():.2f} SAR",
                f"{products_cogs.mean():.2f} SAR" if len(products_cogs) > 0 else "0",
                f"{packages_cogs.mean():.2f} SAR" if len(packages_cogs) > 0 else "0",
                f"{products_cogs.max():.2f} SAR" if len(products_cogs) > 0 else "0",
                f"{packages_cogs.max():.2f} SAR" if len(packages_cogs) > 0 else "0",
            ],
        }
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, width="stretch", hide_index=True)

# Page: Settings
elif st.session_state.page == "settings":
    st.header("إعدادات القنوات والتسعير")
    st.markdown("---")

    # Load existing channels
    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    # Tab 1: Manage Channels
    # Tab 2: Channel Pricing
    tab_manage = st.tabs(["إدارة القنوات"])[0]

    # ===== Tab 1: Manage Channels =====
    with tab_manage:
        st.subheader("إدارة قنوات البيع")

        # Display existing channels
        if channels:
            st.write(f"**القنوات المحفوظة ({len(channels)}):**")
            col1, col2 = st.columns(2)

            with col1:
                existing_channels = list(channels.keys())
                selected_channel = st.selectbox("اختر قناة للتعديل", ["إضافة جديدة"] + existing_channels)

            with col2:
                if selected_channel != "إضافة جديدة":
                    if st.button("حذف القناة"):
                        del channels[selected_channel]
                        save_channels(channels, channels_file)
                        st.success(f"تم حذف القناة: {selected_channel}")
                        st.rerun()
        else:
            selected_channel = "إضافة جديدة"
            st.info("لا توجد قنوات محفوظة حالياً")

        st.markdown("---")

        # Add/Edit Channel Form
        if selected_channel == "إضافة جديدة":
            st.write("**إضافة قناة جديدة:**")
            channel_name = st.text_input("اسم القناة", placeholder="مثال: متجر إلكتروني، جملة، أمازون السعودية")
        else:
            st.write(f"**تعديل القناة: {selected_channel}**")
            channel_name = selected_channel

        st.markdown("**رسوم القناة:**")
        col1, col2 = st.columns(2)

        with col1:
            # Get current values if editing
            if selected_channel != "إضافة جديدة" and selected_channel in channels:
                current = channels[selected_channel]
                default_platform = current.platform_pct * 100
                default_payment = current.payment_pct * 100
                default_marketing = current.marketing_pct * 100
                default_opex = current.opex_pct * 100
            else:
                default_platform = 3.0
                default_payment = 2.5
                default_marketing = 28.0
                default_opex = 4.0

            platform_pct = (
                st.number_input("رسوم المنصات %", min_value=0.0, max_value=20.0, value=default_platform, step=0.1) / 100
            )
            payment_pct = (
                st.number_input("رسوم الدفع %", min_value=0.0, max_value=20.0, value=default_payment, step=0.1) / 100
            )
            marketing_pct = (
                st.number_input("نسبة التسويق %", min_value=0.0, max_value=50.0, value=default_marketing, step=0.1)
                / 100
            )
            opex_pct = (
                st.number_input("نسبة التشغيل %", min_value=0.0, max_value=20.0, value=default_opex, step=0.1) / 100
            )

        with col2:
            if selected_channel != "إضافة جديدة" and selected_channel in channels:
                current = channels[selected_channel]
                default_shipping = current.shipping_fixed
                default_prep = current.preparation_fee
                default_threshold = current.free_shipping_threshold
            else:
                default_shipping = 20.0
                default_prep = 5.0
                default_threshold = 0.0

            shipping_fixed = st.number_input(
                "رسوم الشحن الثابتة (SAR)", min_value=0.0, value=default_shipping, step=0.01
            )
            preparation_fee = st.number_input("رسوم التحضير (SAR)", min_value=0.0, value=default_prep, step=0.01)
            free_threshold = st.number_input(
                "الحد الأدنى للشحن والتجهيز مجاني (SAR)",
                min_value=0.0,
                value=default_threshold,
                step=0.01,
                help="إذا كان السعر قبل الخصم ≥ هذا الحد، يكون الشحن والتجهيز مجاني",
            )

        st.markdown("---")

        # ===== Custom Fees Management =====
        st.subheader("إدارة الرسوم الإضافية المخصصة")

        custom_fees = {}
        if selected_channel != "إضافة جديدة" and selected_channel in channels:
            current = channels[selected_channel]
            custom_fees = current.custom_fees if hasattr(current, "custom_fees") else {}

        col1, col2, col3 = st.columns(3)
        with col1:
            fee_name = st.text_input("اسم الرسم الجديد", placeholder="مثال: رسم معالجة", key="fee_name_input")
        with col2:
            fee_amount = st.number_input("المبلغ أو النسبة", min_value=0.0, step=0.01, key="fee_amount_input")
        with col3:
            fee_type = st.selectbox("نوع الرسم", ["نسبة %", "مبلغ ثابت SAR"], key="fee_type_select")

        if st.button("➕ إضافة رسم جديد", type="secondary", width="stretch", key="add_fee_btn"):
            if fee_name.strip():
                fee_type_key = "percentage" if fee_type == "نسبة %" else "fixed"
                if fee_type_key == "percentage":
                    custom_fees[fee_name] = {"name": fee_name, "amount": fee_amount / 100, "fee_type": fee_type_key}
                else:
                    custom_fees[fee_name] = {"name": fee_name, "amount": fee_amount, "fee_type": fee_type_key}
                
                # حفظ الرسوم مباشرة في القناة المحفوظة
                if selected_channel != "إضافة جديدة" and selected_channel in channels:
                    channels[selected_channel].custom_fees = custom_fees
                    save_channels(channels, channels_file)
                    st.success(f"✅ تم إضافة وحفظ الرسم: {fee_name}")
                    st.rerun()
                else:
                    st.success(f"تم إضافة الرسم: {fee_name}")

        # Display existing custom fees
        if custom_fees:
            st.write("**الرسوم المضافة:**")
            for fee_key, fee_data in list(custom_fees.items()):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{fee_data['name']}**")
                with col2:
                    if fee_data["fee_type"] == "percentage":
                        st.write(f"{fee_data['amount']*100:.1f}%")
                    else:
                        st.write(f"{fee_data['amount']:.2f} SAR")
                with col3:
                    st.write("نسبة" if fee_data["fee_type"] == "percentage" else "مبلغ ثابت")
                with col4:
                    if st.button("حذف", key=f"delete_fee_{fee_key}"):
                        del custom_fees[fee_key]
                        # حفظ التعديل مباشرة
                        if selected_channel != "إضافة جديدة" and selected_channel in channels:
                            channels[selected_channel].custom_fees = custom_fees
                            save_channels(channels, channels_file)
                        st.rerun()

        st.markdown("---")

        if st.button("💾 حفظ القناة", type="primary", width="stretch"):
            if channel_name.strip():
                new_channel = ChannelFeesData(
                    platform_pct=platform_pct,
                    payment_pct=payment_pct,
                    marketing_pct=marketing_pct,
                    opex_pct=opex_pct,
                    vat_rate=0.15,  # Default VAT 15%
                    discount_rate=0.10,  # Default discount 10%
                    shipping_fixed=shipping_fixed,
                    preparation_fee=preparation_fee,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                )
                channels[channel_name] = new_channel
                save_channels(channels, channels_file)
                st.success(f"تم حفظ القناة: {channel_name}")
                st.rerun()
            else:
                st.error("يجب إدخال اسم القناة")

        # Display all channels
        st.markdown("---")
        st.subheader("جميع القنوات المحفوظة")
        if channels:
            for ch_name, ch_fees in channels.items():
                with st.expander(f"📱 {ch_name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("رسوم المنصات", f"{ch_fees.platform_pct*100:.1f}%")
                        st.metric("رسوم الدفع", f"{ch_fees.payment_pct*100:.1f}%")
                        st.metric("نسبة التسويق", f"{ch_fees.marketing_pct*100:.1f}%")
                        st.metric("نسبة التشغيل", f"{ch_fees.opex_pct*100:.1f}%")
                    with col2:
                        st.metric("رسوم الشحن", f"{ch_fees.shipping_fixed:.2f} SAR")
                        st.metric("رسوم التحضير", f"{ch_fees.preparation_fee:.2f} SAR")
                        st.metric(
                            "الحد الأدنى للشحن مجاني",
                            (
                                f"{ch_fees.free_shipping_threshold:.2f} SAR"
                                if ch_fees.free_shipping_threshold > 0
                                else "معطل"
                            ),
                        )

                    # Display custom fees if any
                    if hasattr(ch_fees, "custom_fees") and ch_fees.custom_fees:
                        st.write("**الرسوم الإضافية:**")
                        for fee_key, fee_data in ch_fees.custom_fees.items():
                            if fee_data["fee_type"] == "percentage":
                                st.write(f"• {fee_data['name']}: {fee_data['amount']*100:.1f}%")
                            else:
                                st.write(f"• {fee_data['name']}: {fee_data['amount']:.2f} SAR")

# Main Page
elif st.session_state.page == "main":
    # Professional Dashboard Header
    st.markdown(
        """
    <div style="text-align: right; margin-bottom: 24px;">
        <h2 style="color: #111827; margin: 0; font-size: 1.45rem;">لوحة التحكم الرئيسية</h2>
        <p style="color: #667085; margin: 8px 0 0 0;">نظرة تشغيلية على بيانات التكلفة والتسعير</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.subheader("جاهزية التشغيل")
    render_commercial_readiness(quality_report, key_prefix="main_readiness", compact=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Key Metrics Row with Beautiful Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            """
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-top: 3px solid #0f766e;
                    border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <p style="color: #667085; font-size: 0.85em; margin: 0;">إجمالي المواد الخام</p>
            <p style="color: #0f766e; font-size: 2.1em; margin: 8px 0; font-weight: 700;">{}</p>
            <p style="color: #98a2b3; font-size: 0.8em; margin: 0;">مادة خام متوفرة</p>
        </div>
        """.format(
                len(materials)
            ),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-top: 3px solid #15803d;
                    border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <p style="color: #667085; font-size: 0.85em; margin: 0;">إجمالي المنتجات</p>
            <p style="color: #15803d; font-size: 2.1em; margin: 8px 0; font-weight: 700;">{}</p>
            <p style="color: #98a2b3; font-size: 0.8em; margin: 0;">منتج جاهز</p>
        </div>
        """.format(
                len(product_recipes)
            ),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-top: 3px solid #b45309;
                    border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <p style="color: #667085; font-size: 0.85em; margin: 0;">إجمالي البكجات</p>
            <p style="color: #b45309; font-size: 2.1em; margin: 8px 0; font-weight: 700;">{}</p>
            <p style="color: #98a2b3; font-size: 0.8em; margin: 0;">باقة متكاملة</p>
        </div>
        """.format(
                len(package_compositions)
            ),
            unsafe_allow_html=True,
        )

    with col4:
        # Count pricing history
        history_file = "data/pricing_history.csv"
        if os.path.exists(history_file):
            try:
                history_df = pd.read_csv(history_file, encoding="utf-8-sig")
                pricing_count = len(history_df)
            except:
                pricing_count = 0
        else:
            pricing_count = 0

        st.markdown(
            """
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-top: 3px solid #475467;
                    border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <p style="color: #667085; font-size: 0.85em; margin: 0;">سجلات التسعير</p>
            <p style="color: #475467; font-size: 2.1em; margin: 8px 0; font-weight: 700;">{}</p>
            <p style="color: #98a2b3; font-size: 0.8em; margin: 0;">سجل محفوظ</p>
        </div>
        """.format(
                pricing_count
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick Actions
    st.markdown(
        """
    <div style="background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; margin: 20px 0;
                box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
        <h3 style="color: #111827; margin: 0 0 14px 0;">الإجراءات السريعة</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("تسعير سريع", width="stretch", type="primary"):
            st.session_state.page = "pricing"
            st.rerun()

    with col2:
        if st.button("تكلفة البضاعة", width="stretch"):
            st.session_state.page = "cogs"
            st.rerun()

    with col3:
        if st.button("إعدادات المنصات", width="stretch"):
            st.session_state.page = "settings"
            st.rerun()

    with col4:
        if st.button("تسعير شامل", width="stretch"):
            st.session_state.page = "profit_margins"
            st.rerun()

    # Recent Activity & Charts
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            """
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px;
                    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <h3 style="color: #111827; margin: 0 0 14px 0;">النشاط الأخير</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if os.path.exists(history_file) and pricing_count > 0:
            try:
                recent_df = history_df.tail(5)[["التاريخ", "اسم المنتج/البكج", "سعر البيع", "الربح"]].copy()
                recent_df["سعر البيع"] = recent_df["سعر البيع"].apply(lambda x: f"{x:.2f} SAR")
                recent_df["الربح"] = recent_df["الربح"].apply(lambda x: f"{x:.2f} SAR")
                st.dataframe(recent_df, width="stretch", hide_index=True)
            except:
                st.info("لا توجد سجلات تسعير حالياً")
        else:
            st.info("لا توجد سجلات تسعير حالياً. ابدأ بتسعير منتج!")

    with col2:
        st.markdown(
            """
        <div style="background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px;
                    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
            <h3 style="color: #111827; margin: 0 0 14px 0;">توزيع البيانات</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if len(product_recipes) > 0 or len(package_compositions) > 0:
            data = pd.DataFrame(
                {"النوع": ["منتجات", "بكجات"], "العدد": [len(product_recipes), len(package_compositions)]}
            )
            fig = px.pie(data, values="العدد", names="النوع", color_discrete_sequence=["#0f766e", "#b45309"], hole=0.4)
            fig.update_layout(height=300, showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("لا توجد بيانات لعرضها. ابدأ برفع ملفات Zoho الثلاثة.")

    # Getting Started Guide
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
    <div style="background: #ffffff; border: 1px solid #d9dee7; border-right: 4px solid #0f766e;
                border-radius: 8px; padding: 22px; margin: 20px 0;
                box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06);">
        <h3 style="color: #111827; margin: 0 0 14px 0;">دليل البدء السريع</h3>
        <ol style="color: #475467; line-height: 1.8; margin: 0;">
            <li><strong>رفع الملفات</strong> - قم برفع ملفات Zoho الثلاثة: البنود، البكجات، وتقييم المخزون</li>
            <li><strong>إعداد المنصات</strong> - أضف قنوات البيع وحدد الرسوم والنسب</li>
            <li><strong>حساب التكاليف</strong> - تحقق من تكلفة البضاعة (COGS)</li>
            <li><strong>التسعير</strong> - احسب الأسعار المثلى لمنتجاتك</li>
            <li><strong>مراجعة النتائج</strong> - راجع السعر النهائي ومكونات التكلفة</li>
        </ol>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Page: Advanced Pricing
elif st.session_state.page == "pricing":
    st.header("💵 تسعير منتج/بكج فردي")
    st.markdown("حساب التكلفة الكاملة وتحليل هوامش الربح لمنتج أو بكج واحد")
    st.markdown("---")

    if quality_report is None or not quality_report.is_ready:
        st.error("لا يمكن اعتماد تسعير تجاري قبل معالجة مشاكل البيانات الحرجة.")
        render_commercial_readiness(quality_report, key_prefix="pricing_blocker")
        st.stop()

    # Load channels
    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    if not channels:
        st.error("⚠️ لا توجد قنوات محفوظة! يجب إضافة قناة أولاً من صفحة الإعدادات")
    else:
        # Use already loaded data (from load_all_data at the top)
        products_df = products_summary
        packages_df = packages_summary

        UIComponents.render_section_header(
            "تسعير احترافي لمنتج/بكج واحد",
            "اختر الاستراتيجية، أعد ضبط الرسوم التسويقية، واحصل على توصية سعرية مدعومة بحساسيات",
            "💡",
        )

        # Helper function to calculate cost of any component
        def calculate_component_cost(sku, component_type="product"):
            return resolve_component_cost(sku, materials, product_recipes, package_compositions)

        # Build selector options (unique)
        sku_options = []
        sku_to_name = {}
        sku_to_type = {}
        sku_to_cogs = {}

        def add_item(option, sku, name, item_type, cogs_val):
            sku_options.append(option)
            sku_to_name[option] = name
            sku_to_type[option] = item_type
            sku_to_cogs[option] = cogs_val

        if not products_df.empty:
            for _, row in products_df.iterrows():
                sku = row["Product_SKU"]
                name = row["Product_Name"]
                option = f"{name} - {sku}"
                add_item(option, sku, name, "منتج", calculate_component_cost(sku, "product"))

        if not packages_df.empty:
            for _, row in packages_df.iterrows():
                sku = row["Package_SKU"]
                name = row["Package_Name"]
                option = f"{name} - {sku}"
                add_item(option, sku, name, "باقة", calculate_component_cost(sku, "package"))

        # === Inputs ===
        col_left, col_mid, col_right = st.columns([1.2, 1, 1.1])

        with col_left:
            selected_channel = st.selectbox(
                "📍 قناة البيع", list(channels.keys()), help="اختر القناة لتطبيق رسومها وعتباتها"
            )


            search_term = st.text_input("🔎 بحث بالاسم أو SKU", placeholder="اكتب للبحث السريع")
            filtered_sku_options = (
                [opt for opt in sku_options if search_term.lower() in opt.lower()] if search_term else sku_options
            )
            if filtered_sku_options:
                selected_sku_option = st.selectbox("📦 المنتج/البكج", filtered_sku_options)
                sku_input = selected_sku_option.split(" - ")[-1]
                item_type = sku_to_type.get(selected_sku_option, "منتج")
                default_cogs = sku_to_cogs.get(selected_sku_option, 0.0)
                item_name = sku_to_name.get(selected_sku_option, sku_input)
            else:
                st.warning("لا توجد نتائج مطابقة للبحث")
                selected_sku_option = ""
                sku_input = ""
                item_type = "منتج"
                default_cogs = 0.0
                item_name = ""

            cogs = st.number_input("💰 تكلفة البضاعة (COGS)", min_value=0.0, step=0.01, value=default_cogs)

            # اختيارات استبعاد رسوم معينة لهذا السيناريو
            skip_shipping = st.checkbox("🚚 بدون رسوم شحن", value=False, help="استبعد الشحن لهذا السيناريو فقط")
            skip_preparation = st.checkbox("🧰 بدون رسوم تجهيز", value=False, help="استبعد رسوم التجهيز/التعبئة")
            skip_marketing = st.checkbox("📢 بدون رسوم تسويق", value=False, help="استبعد نسبة التسويق من الحساب")

        with col_mid:
            strategy_presets = {
                "اختراق السوق": {"margin": 10.0, "discount": 5.0},
                "توازن ربحي": {"margin": 18.0, "discount": 3.0},
                "تميز/بريميم": {"margin": 25.0, "discount": 0.0},
                "تصفية": {"margin": 8.0, "discount": 10.0},
            }
            strategy_descriptions = {
                "اختراق السوق": "تسعير هجومي لزيادة الحصة بسرعة بهامش أقل وخصم لجذب العملاء.",
                "توازن ربحي": "مزيج متوازن بين هامش جيد ونمو مستدام مع خصم محدود.",
                "تميز/بريميم": "تركيز على القيمة والعلامة؛ هامش أعلى وخصم شبه معدوم.",
                "تصفية": "تصريف المخزون بسرعة مع خصم أكبر مع الحفاظ على هامش أمان.",
            }

            strategy = st.selectbox(
                "🎯 الإستراتيجية السعرية",
                list(strategy_presets.keys()),
                index=list(strategy_presets.keys()).index("توازن ربحي"),
                format_func=lambda k: f"{k} — {strategy_descriptions.get(k, '')}",
            )
            preset_margin = strategy_presets[strategy]["margin"]
            preset_discount = strategy_presets[strategy]["discount"]

            target_margin_pct = st.number_input(
                "هامش الربح المستهدف (%)", min_value=0.0, max_value=40.0, value=preset_margin, step=0.5
            )
            discount_pct = st.number_input(
                "الخصم الممنوح (%)", min_value=0.0, max_value=50.0, value=preset_discount, step=0.5
            )


        with col_right:
            marketing_boost = st.number_input(
                "رفع ميزانية التسويق % إضافية",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.25,
                help="يضاف إلى نسبة التسويق للقناة لهذا السيناريو",
            )
            ops_buffer = st.number_input(
                "احتياط تشغيلي (SAR)", min_value=0.0, value=0.0, step=0.5, help="هوامش أمان لعمليات التعبئة والتغليف"
            )
            competitor_price = st.number_input(
                "سعر منافس (اختياري)",
                min_value=0.0,
                value=0.0,
                step=0.5,
                help="أدخل سعر المنافس شامل الضريبة قبل الخصم",
            )

        target_margin = target_margin_pct / 100
        discount_rate = discount_pct / 100

        st.markdown("---")

        # Auto-recalculate when channel changes if already calculated
        if "last_calculated_channel" not in st.session_state:
            st.session_state["last_calculated_channel"] = None

        channel_changed = (
            st.session_state["last_calculated_channel"] is not None
            and st.session_state["last_calculated_channel"] != selected_channel
        )

        col_btn = st.columns([1, 2, 1])[1]
        with col_btn:
            run_pricing = st.button("🚀 احسب التسعير الاحترافي", type="primary", width="stretch")

        if run_pricing or channel_changed:
            if not sku_input:
                st.error("اختر منتجاً أو بكجاً أولاً")
                st.stop()
            if cogs <= 0:
                st.error("أدخل تكلفة صالحة")
                st.stop()

            ch = channels[selected_channel]
            shipping = 0.0 if skip_shipping else ch.shipping_fixed
            preparation = 0.0 if skip_preparation else ch.preparation_fee
            vat_rate = ch.vat_rate
            free_threshold = getattr(ch, "free_shipping_threshold", 0)
            custom_fees = getattr(ch, "custom_fees", {}) or {}

            marketing_effective = 0.0 if skip_marketing else (ch.marketing_pct + (marketing_boost / 100))

            channel_dict = {
                "opex_pct": ch.opex_pct,
                "marketing_pct": marketing_effective,
                "platform_pct": ch.platform_pct,
                "payment_pct": ch.payment_pct,
                "vat_rate": vat_rate,
                "discount_rate": discount_rate,
            }

            total_pct = (
                channel_dict["opex_pct"]
                + channel_dict["marketing_pct"]
                + channel_dict["platform_pct"]
                + channel_dict["payment_pct"]
            )
            
            # حساب السعر المباشر من المعادلة لتحقيق الهامش المستهدف
            def solve_price_for_margin(target_margin_val: float):
                """حساب السعر المباشر الذي يحقق الهامش المستهدف مع مراعاة الشحن المجاني
                
                المنطق الذكي:
                1. نجرب أولاً السعر بدون شحن/تحضير
                2. إذا كان السعر < حد 98 ويحقق الهامش → نستخدمه (الأفضل للعميل!)
                3. وإلا نضيف الشحن والتحضير ونحسب السعر
                """
                
                # أولاً: نجرب بدون شحن/تحضير
                fixed_costs_free = cogs + ops_buffer
                denominator = 1 - total_pct - target_margin_val
                
                if denominator > 0:
                    net_price_free = fixed_costs_free / denominator
                    price_with_vat_after_discount_free = net_price_free * (1 + vat_rate)
                    price_before_discount_free = price_with_vat_after_discount_free / (1 - discount_rate)
                    
                    # إذا السعر بدون شحن < الحد (98) → نستخدمه!
                    if free_threshold > 0 and price_before_discount_free < free_threshold:
                        price_before_discount = price_before_discount_free
                    else:
                        # ثانياً: السعر >= الحد، نحسب مع الشحن/التحضير
                        fixed_costs_with_ship = cogs + shipping + preparation + ops_buffer
                        if denominator > 0:
                            net_price_with_ship = fixed_costs_with_ship / denominator
                            price_with_vat_after_discount_with_ship = net_price_with_ship * (1 + vat_rate)
                            price_before_discount = price_with_vat_after_discount_with_ship / (1 - discount_rate)
                        else:
                            price_before_discount = price_before_discount_free
                else:
                    # الحساب غير ممكن (denominator <= 0)
                    price_before_discount = 0
                
                # احسب التفصيل الكامل
                bd = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=price_before_discount
                )
                
                return price_before_discount, bd

            price_list_before_discount, breakdown = solve_price_for_margin(target_margin)

            # استخدام النتيجة المحسوبة مباشرة بدون تعديل الهامش
            display_price_with_vat = price_list_before_discount
            display_breakdown = breakdown

            UIComponents.render_section_header("نتيجة الإستراتيجية", "سعر موصى به مع تفكيك مالي", "📊")
            colm1, colm2, colm3, colm4 = st.columns(4)
            with colm1:
                st.metric("سعر البيع شامل الضريبة قبل الخصم", f"{display_price_with_vat:.2f} SAR")
            with colm2:
                st.metric(
                    "سعر بعد الخصم",
                    f"{display_breakdown['price_after_discount']:.2f} SAR",
                    help="السعر النهائي المتوقع بعد الخصم",
                )
            with colm3:
                st.metric(
                    "صافي الربح",
                    f"{display_breakdown['profit']:.2f} SAR",
                    delta=f"{display_breakdown['margin_pct']*100:.1f}%",
                )
            with colm4:
                st.metric("هامش صافي الربح", f"{display_breakdown['margin_pct']*100:.1f}%")

            st.markdown("### 💡 توصية الاستراتيجية")
            rec_notes = {
                "اختراق السوق": "تسعير هجومي لزيادة الحصة مع خصم محسوب.",
                "توازن ربحي": "مزيج متوازن بين الهامش والنمو.",
                "تميز/بريميم": "تركيز على القيمة المضافة مع خصم محدود.",
                "تصفية": "تسريع التصريف مع بقاء هامش آمن.",
            }
            UIComponents.render_info_box(f"النهج: {rec_notes.get(strategy, '')}", "info")

            st.markdown("---")

            # Sensitivity analysis using advanced engine (جداول مبسطة)
            sens = pricing_engine.perform_sensitivity_analysis(
                base_cogs=cogs,
                base_price=breakdown["price_after_discount"],
                channel_fees=channel_dict,
                shipping=shipping,
                preparation=preparation,
            )

            st.markdown("---")
            st.subheader("حساسية بسيطة يمكن التصرف عليها")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown("##### تغير التكلفة ±20%")
                df_cogs_sens = pd.DataFrame(sens["cogs_sensitivity"])
                df_cogs_sens.rename(
                    columns={"change_pct": "التغير %", "cogs": "تكلفة البضاعة", "profit": "الربح", "margin": "هامش %"},
                    inplace=True,
                )
                df_cogs_sens["هامش %"] = df_cogs_sens["هامش %"].round(2)
                df_cogs_sens["الربح"] = df_cogs_sens["الربح"].round(2)

                # تطبيق تنسيق محسّن
                def format_sensitivity_row(row):
                    if row["التغير %"] == "0%":
                        return ["background-color: #fff3cd; font-weight: bold"] * len(row)
                    elif row["التغير %"] in ["-20%", "-10%"]:
                        return ["background-color: #f8d7da"] * len(row)
                    elif row["التغير %"] in ["+10%", "+20%"]:
                        return ["background-color: #d1ecf1"] * len(row)
                    return [""] * len(row)

                styled_cogs = (
                    df_cogs_sens[["التغير %", "تكلفة البضاعة", "الربح", "هامش %"]]
                    .style.apply(format_sensitivity_row, axis=1)
                    .format({"تكلفة البضاعة": "{:.2f}", "الربح": "{:.2f}", "هامش %": "{:.2f}"})
                    .set_table_styles(
                        [
                            {
                                "selector": "th",
                                "props": [
                                    ("background-color", "#1e88e5"),
                                    ("color", "white"),
                                    ("font-weight", "bold"),
                                    ("text-align", "center"),
                                    ("padding", "10px"),
                                ],
                            },
                            {
                                "selector": "td",
                                "props": [("text-align", "right"), ("padding", "8px"), ("border", "1px solid #ddd")],
                            },
                            {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                        ]
                    )
                )
                st.dataframe(styled_cogs, width="stretch", hide_index=True, height=280)

            with col_s2:
                st.markdown("##### تغير السعر ±20%")
                df_price_sens = pd.DataFrame(sens["price_sensitivity"])
                df_price_sens.rename(
                    columns={"change_pct": "التغير %", "price": "السعر", "profit": "الربح", "margin": "هامش %"},
                    inplace=True,
                )
                df_price_sens["هامش %"] = df_price_sens["هامش %"].round(2)
                df_price_sens["الربح"] = df_price_sens["الربح"].round(2)

                # تطبيق تنسيق محسّن
                def format_sensitivity_row(row):
                    if row["التغير %"] == "0%":
                        return ["background-color: #fff3cd; font-weight: bold"] * len(row)
                    elif row["التغير %"] in ["-20%", "-10%"]:
                        return ["background-color: #f8d7da"] * len(row)
                    elif row["التغير %"] in ["+10%", "+20%"]:
                        return ["background-color: #d1ecf1"] * len(row)
                    return [""] * len(row)

                styled_price = (
                    df_price_sens[["التغير %", "السعر", "الربح", "هامش %"]]
                    .style.apply(format_sensitivity_row, axis=1)
                    .format({"السعر": "{:.2f}", "الربح": "{:.2f}", "هامش %": "{:.2f}"})
                    .set_table_styles(
                        [
                            {
                                "selector": "th",
                                "props": [
                                    ("background-color", "#1e88e5"),
                                    ("color", "white"),
                                    ("font-weight", "bold"),
                                    ("text-align", "center"),
                                    ("padding", "10px"),
                                ],
                            },
                            {
                                "selector": "td",
                                "props": [("text-align", "right"), ("padding", "8px"), ("border", "1px solid #ddd")],
                            },
                            {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                        ]
                    )
                )
                st.dataframe(styled_price, width="stretch", hide_index=True, height=280)

            # Positioning vs competitor with side-by-side detailed tables
            if competitor_price > 0:
                our_price_after_discount = breakdown["price_after_discount"]
                competitor_list_price = competitor_price  # إدخال المستخدم هو السعر شامل الضريبة قبل الخصم
                competitor_breakdown = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=competitor_list_price,
                )

                comp_price_after_discount = competitor_breakdown["price_after_discount"]
                positioning = (
                    "أعلى من السوق"
                    if our_price_after_discount > comp_price_after_discount * 1.05
                    else "ضمن السوق" if our_price_after_discount >= comp_price_after_discount * 0.95 else "أقل من السوق"
                )
                UIComponents.render_info_box(
                    f"مقارنة السعر بعد الخصم بالمنافس: {positioning} (بعد خصم منافس {comp_price_after_discount:.2f} SAR)",
                    "warning",
                )

                # عرض شروط المنصة المختارة
                st.info(f"📋 **شروط المنصة المختارة ({selected_channel}):**\n"
                      f"- حد الشحن المجاني: {free_threshold} ريال\n"
                      f"- رسوم الشحن: {shipping} ريال\n"
                      f"- رسوم التحضير: {preparation} ريال\n"
                      f"- القاعدة: إذا السعر < {free_threshold} → شحن مجاني | إذا ≥ {free_threshold} → شحن مدفوع")
                
                # عرض قرار الشحن لسعرنا
                our_list_price = price_list_before_discount
                if free_threshold > 0 and our_list_price < free_threshold:
                    st.success(f"✅ السعر قبل الخصم ({our_list_price:.2f}) < الحد ({free_threshold}) → شحن مجاني (0), تحضير مجاني (0)")
                elif free_threshold > 0:
                    st.success(f"✅ السعر قبل الخصم ({our_list_price:.2f}) ≥ الحد ({free_threshold}) → شحن مدفوع ({shipping}), تحضير مدفوع ({preparation})")
                else:
                    st.success(f"✅ لا يوجد حد للشحن المجاني → شحن مدفوع ({shipping}), تحضير مدفوع ({preparation})")

                st.markdown("### مقارنة سعرنا مع المنافس (تفصيل كامل مثل ورقة الحساب)")

                def build_detail_rows(bd: dict, rate_map: dict, list_price: float) -> pd.DataFrame:
                    custom_total = bd.get("custom_fees_total", 0)
                    rows = [
                        ("الجزء الأول: التسعير", None, None),
                        ("سعر البيع شامل الضريبة قبل الخصم", list_price, ""),
                        ("نسبة الخصم", bd["discount_rate"] * 100, "%"),
                        ("مبلغ الخصم", bd["discount_amount"], ""),
                        ("سعر البيع شامل الضريبة بعد الخصم", bd["price_after_discount"], ""),
                        ("سعر البيع غير الضريبة بعد الخصم", bd["net_price"], ""),
                        ("الجزء الثاني: تكلفة البضاعة المباعة", None, None),
                        ("تكلفة البضاعة للوحدة", bd["cogs"], ""),
                        ("الجزء الثالث: رسوم المنصة", None, None),
                        ("التحضير", bd["preparation_fee"], ""),
                        ("الشحن", bd["shipping_fee"], ""),
                    ]

                    # إضافة الرسوم فقط إذا كانت أكبر من صفر
                    if bd["admin_fee"] > 0:
                        rows.append(("المصاريف الإدارية", bd["admin_fee"], f"{rate_map['admin']*100:.1f}%"))
                    if bd["marketing_fee"] > 0:
                        rows.append(("مصاريف التسويق", bd["marketing_fee"], f"{rate_map['marketing']*100:.1f}%"))
                    if bd.get("payment_fee", 0) > 0:
                        rows.append(("رسوم الدفع", bd.get("payment_fee", 0), f"{rate_map['payment']*100:.1f}%"))
                    if bd["platform_fee"] > 0:
                        rows.append(("رسوم المنصات", bd["platform_fee"], f"{rate_map['platform']*100:.1f}%"))
                    if custom_total > 0:
                        rows.append(("رسوم مخصصة", custom_total, ""))

                    rows.extend(
                        [
                            ("إجمالي التكلفة والرسوم", bd["total_costs_fees"], ""),
                            ("الجزء الرابع: صافي الربح", None, None),
                            ("الربح", bd["profit"], ""),
                            ("هامش الربح %", bd["margin_pct"] * 100, "%"),
                        ]
                    )

                    df = pd.DataFrame(rows, columns=["البند", "القيمة", "ملاحظة"])

                    # تطبيق تنسيق محسّن
                    def format_comparison_row(row):
                        label = row["البند"]
                        if label and label.startswith("الجزء"):
                            return [
                                "background-color: #1e88e5; color: white; font-weight: bold; font-size: 16px"
                            ] * len(row)
                        elif label == "إجمالي التكلفة والرسوم":
                            return [
                                "background-color: #fff3cd; border-top: 2px solid #856404; font-weight: bold"
                            ] * len(row)
                        elif label in ["الربح", "هامش الربح %"]:
                            return ["background-color: #d4edda; color: #155724; font-weight: bold"] * len(row)
                        return [""] * len(row)

                    styled = (
                        df.style.apply(format_comparison_row, axis=1)
                        .format(
                            {
                                "القيمة": lambda x: (
                                    f"{x:.2f}" if isinstance(x, (int, float)) else ("—" if x is None else str(x))
                                ),
                                "ملاحظة": lambda x: "" if x is None else str(x),
                            }
                        )
                        .set_table_styles(
                            [
                                {
                                    "selector": "th",
                                    "props": [
                                        ("background-color", "#1e88e5"),
                                        ("color", "white"),
                                        ("font-weight", "bold"),
                                        ("text-align", "center"),
                                        ("padding", "10px"),
                                    ],
                                },
                                {
                                    "selector": "td",
                                    "props": [
                                        ("text-align", "right"),
                                        ("padding", "8px"),
                                        ("border", "1px solid #ddd"),
                                    ],
                                },
                                {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                            ]
                        )
                    )

                    return styled

                rate_map = {
                    "admin": channel_dict.get("opex_pct", 0),
                    "marketing": channel_dict.get("marketing_pct", 0),
                    "payment": channel_dict.get("payment_pct", 0),
                    "platform": channel_dict.get("platform_pct", 0),
                }

                # حساب سعر التعادل (هامش ربح 0%)
                breakeven_breakdown = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=breakdown["breakeven_price"],
                )

                col_cmp1, col_cmp2, col_cmp3 = st.columns(3)
                table_height = 820
                with col_cmp1:
                    st.markdown("**سعرنا**")
                    styled_ours = build_detail_rows(breakdown, rate_map, price_list_before_discount)
                    st.dataframe(styled_ours, width="stretch", hide_index=True, height=table_height)
                with col_cmp2:
                    st.markdown("**سعر المنافس**")
                    styled_comp = build_detail_rows(competitor_breakdown, rate_map, competitor_list_price)
                    st.dataframe(styled_comp, width="stretch", hide_index=True, height=table_height)
                with col_cmp3:
                    st.markdown("**سعر التعادل (0% ربح)**")
                    styled_breakeven = build_detail_rows(breakeven_breakdown, rate_map, breakdown["breakeven_price"])
                    st.dataframe(styled_breakeven, width="stretch", hide_index=True, height=table_height)

            st.markdown("---")
            st.subheader("حفظ التسعير")
            
            # حفظ النتائج في session_state للاحتفاظ بها
            if "current_pricing_result" not in st.session_state:
                st.session_state["current_pricing_result"] = None
            
            # تخزين النتيجة الحالية
            st.session_state["current_pricing_result"] = {
                "التاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "اسم المنتج/البكج": item_name,
                "SKU": sku_input.strip(),
                "النوع": item_type,
                "المنصة": selected_channel,
                "التكلفة": cogs,
                "سعر القائمة": price_list_before_discount,
                "سعر بعد الخصم": breakdown["price_after_discount"],
                "الربح": breakdown["profit"],
                "هامش الربح %": breakdown["margin_pct"] * 100,
                "رسوم الشحن": breakdown["shipping_fee"],
                "رسوم التحضير": breakdown["preparation_fee"],
                "رسوم إدارية": breakdown["admin_fee"],
                "رسوم تسويق": breakdown["marketing_fee"],
                "رسوم الدفع": breakdown.get("payment_fee", 0),
                "رسوم المنصة": breakdown["platform_fee"],
                "نسبة الخصم": discount_pct,
                "صافي السعر": breakdown["net_price"],
                "إجمالي التكاليف": breakdown["total_costs_fees"],
                "نقطة التعادل": breakdown["breakeven_price"],
                "استراتيجية": strategy,
            }
            
            if st.button("💾 حفظ النتيجة", type="primary", width="stretch", key="save_pricing_btn_pro"):
                pass  # سيتم معالجة الحفظ خارج هذا الشرط

        # معالجة الحفظ خارج شرط run_pricing لتجنب إعادة التحميل
        if "current_pricing_result" in st.session_state and st.session_state.get("current_pricing_result"):
            # فحص إذا تم الضغط على زر الحفظ
            if st.session_state.get("save_pricing_btn_pro"):
                try:
                    import os

                    data_dir = os.path.join(os.path.dirname(__file__), "data")
                    os.makedirs(data_dir, exist_ok=True)

                    pricing_record = st.session_state["current_pricing_result"]

                    history_file = os.path.join(data_dir, "pricing_history.csv")

                    if os.path.exists(history_file):
                        history_df = pd.read_csv(history_file, encoding="utf-8-sig")
                        history_df = pd.concat([history_df, pd.DataFrame([pricing_record])], ignore_index=True)
                    else:
                        history_df = pd.DataFrame([pricing_record])

                    history_df.to_csv(history_file, index=False, encoding="utf-8-sig")
                    append_audit_event(
                        data_dir,
                        {
                            **pricing_record,
                            "event_type": "pricing_saved",
                            "scope": "single_item",
                            "sku": pricing_record.get("SKU", ""),
                            "item_name": pricing_record.get("اسم المنتج/البكج", ""),
                            "item_type": pricing_record.get("النوع", ""),
                            "channel": pricing_record.get("المنصة", ""),
                            "cogs": pricing_record.get("التكلفة", 0),
                            "list_price": pricing_record.get("سعر القائمة", 0),
                            "net_price": pricing_record.get("صافي السعر", 0),
                            "discount_rate": pricing_record.get("نسبة الخصم", 0),
                            "margin_pct": pricing_record.get("هامش الربح %", 0),
                            "profit": pricing_record.get("الربح", 0),
                            "breakeven_price": pricing_record.get("نقطة التعادل", 0),
                            "details": {
                                "strategy": pricing_record.get("استراتيجية", ""),
                                "saved_from": "individual_pricing",
                            },
                        },
                    )

                    # Verify file was written
                    if os.path.exists(history_file):
                        st.success(f"✅ تم الحفظ بنجاح في: {history_file}")
                        st.info(f"📊 إجمالي السجلات: {len(history_df)}")
                    else:
                        st.error("❌ فشل في الحفظ - الملف غير موجود!")

                    st.session_state["saved_history_preview"] = history_df.copy()

                except Exception as e:
                    import traceback

                    st.error(f"❌ خطأ في الحفظ: {e}")
                    st.code(traceback.format_exc())
        
        # حفظ البيانات الوصفية للحساب الأخير
        if run_pricing or channel_changed:
            st.session_state["last_pricing_breakdown"] = breakdown
            st.session_state["last_pricing_meta"] = {
                "sku": sku_input.strip(),
                "sku_type": item_type,
                "platform": selected_channel,
                "base_price": price_list_before_discount,
                "discount_pct": discount_pct,
                "cogs": cogs,
            }
            st.session_state["last_calculated_channel"] = selected_channel

# Page: Custom Package Builder
elif st.session_state.page == "custom_package":
    st.header("🎁 إنشاء بكج مخصص جديد")
    st.markdown("قم بتجميع منتجات وبكجات مع بعضها لإنشاء بكج جديد واحسب تكلفته وهامش ربحه")
    st.markdown("---")

    if quality_report is None or not quality_report.is_ready:
        st.error("لا يمكن إنشاء تسعير بكج تجاري قبل معالجة مشاكل البيانات الحرجة.")
        render_commercial_readiness(quality_report, key_prefix="custom_package_blocker")
        st.stop()

    # Load channels
    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    if not channels:
        st.error("⚠️ لا توجد قنوات محفوظة! يجب إضافة قناة أولاً من صفحة الإعدادات")
    else:
        products_df = products_summary
        packages_df = packages_summary

        UIComponents.render_section_header(
            "بناء بكج مخصص",
            "اختر عدة منتجات أو بكجات وحدد كمياتها لإنشاء بكج جديد",
            "🎁",
        )

        # Helper function to calculate cost
        def calculate_component_cost(sku, component_type="product"):
            return resolve_component_cost(sku, materials, product_recipes, package_compositions)

        # Build selector options
        all_items = {}
        item_types = {}
        
        # Add products from product_recipes
        for sku in product_recipes.keys():
            # Try to get name from products_df
            name = None
            if not products_df.empty and "Product_SKU" in products_df.columns:
                product_row = products_df[products_df["Product_SKU"] == sku]
                if not product_row.empty and "Product_Name" in product_row.columns:
                    name_value = product_row.iloc[0]["Product_Name"]
                    if pd.notna(name_value) and str(name_value).strip():
                        name = str(name_value).strip()
            
            # Use SKU as fallback if no name found
            if not name:
                name = f"منتج {sku}"
            
            all_items[f"{sku} - {name}"] = sku
            item_types[sku] = "منتج"
        
        # Add packages from package_compositions
        for sku in package_compositions.keys():
            # Try to get name from packages_df
            name = None
            if not packages_df.empty and "Package_SKU" in packages_df.columns:
                package_row = packages_df[packages_df["Package_SKU"] == sku]
                if not package_row.empty and "Package_Name" in package_row.columns:
                    name_value = package_row.iloc[0]["Package_Name"]
                    if pd.notna(name_value) and str(name_value).strip():
                        name = str(name_value).strip()
            
            # Use SKU as fallback if no name found
            if not name:
                name = f"بكج {sku}"
            
            all_items[f"{sku} - {name}"] = sku
            item_types[sku] = "بكج"

        if not all_items:
            st.warning("⚠️ لا توجد منتجات أو بكجات متاحة. قم برفع الملفات من صفحة 'رفع الملفات' أولاً.")
            st.info("تأكد من رفع ملفات Zoho الثلاثة من صفحة رفع الملفات.")
            st.stop()

        # Initialize package components and rows in session state
        if "package_rows" not in st.session_state:
            st.session_state.package_rows = [{"id": 0}]  # Start with one empty row
        if "package_components" not in st.session_state:
            st.session_state.package_components = []
        if "show_pricing" not in st.session_state:
            st.session_state.show_pricing = False

        st.markdown("### 📦 بناء البكج المخصص")
        
        # Search box
        search_term = st.text_input(
            "🔍 بحث عن منتج أو بكج",
            placeholder="ابحث بالاسم أو SKU...",
            key="component_search"
        )
        
        # Filter items based on search
        filtered_items = {}
        if search_term:
            search_lower = search_term.lower()
            for display_name, sku in all_items.items():
                if search_lower in display_name.lower():
                    filtered_items[display_name] = sku
        else:
            filtered_items = all_items
        
        if not filtered_items and search_term:
            st.warning(f"⚠️ لم يتم العثور على نتائج للبحث: {search_term}")
        
        st.markdown("#### اختر المكونات")
        st.markdown("أضف عدة منتجات/بكجات بكميات مختلفة، ثم اضغط **تجميع** للانتقال للتسعير")
        
        # Display rows dynamically
        for idx, row in enumerate(st.session_state.package_rows):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 0.5])
            
            with col1:
                selected_item = st.selectbox(
                    "اختر منتج أو بكج",
                    options=[""] + list(filtered_items.keys()) if filtered_items else [""],
                    key=f"item_selector_{row['id']}",
                    label_visibility="collapsed"
                )
            
            with col2:
                quantity = st.number_input(
                    "الكمية",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"item_quantity_{row['id']}",
                    label_visibility="collapsed"
                )
            
            with col3:
                if idx == len(st.session_state.package_rows) - 1:
                    # Last row: show "Add another" button
                    if st.button("➕ إضافة عنصر آخر", type="primary", key=f"add_row_{row['id']}", use_container_width=True):
                        # Add new empty row
                        new_id = max([r['id'] for r in st.session_state.package_rows]) + 1
                        st.session_state.package_rows.append({"id": new_id})
                        st.rerun()
                else:
                    st.markdown("<div style='height: 38px'></div>", unsafe_allow_html=True)
            
            with col4:
                if len(st.session_state.package_rows) > 1:
                    # Show delete button for all rows except if only one row exists
                    if st.button("🗑️", key=f"delete_row_{row['id']}", help="حذف هذا السطر", use_container_width=True):
                        st.session_state.package_rows = [r for r in st.session_state.package_rows if r['id'] != row['id']]
                        st.rerun()
        
        st.markdown("---")
        
        # Aggregate button
        col_center = st.columns([1, 2, 1])[1]
        with col_center:
            if st.button("📦 تجميع البكج وحساب التسعير", type="primary", use_container_width=True):
                # Collect all selected items
                st.session_state.package_components = []
                
                for row in st.session_state.package_rows:
                    row_id = row['id']
                    # Get values from session state (streamlit stores widget values there)
                    item_key = f"item_selector_{row_id}"
                    qty_key = f"item_quantity_{row_id}"
                    
                    # Access widget values
                    if item_key in st.session_state and st.session_state[item_key]:
                        selected_item = st.session_state[item_key]
                        quantity = st.session_state[qty_key]
                        
                        if selected_item and selected_item in filtered_items:
                            sku = filtered_items[selected_item]
                            component_type = item_types[sku]
                            cost = calculate_component_cost(
                                sku, 
                                "product" if component_type == "منتج" else "package"
                            )
                            
                            st.session_state.package_components.append({
                                "sku": sku,
                                "name": selected_item,
                                "type": component_type,
                                "quantity": quantity,
                                "unit_cost": cost,
                                "total_cost": cost * quantity
                            })
                
                if st.session_state.package_components:
                    st.session_state.show_pricing = True
                    st.rerun()
                else:
                    st.error("⚠️ يجب اختيار منتج واحد على الأقل!")
        
        # Show assembled package if exists
        if st.session_state.show_pricing and st.session_state.package_components:
            st.markdown("---")
            st.markdown("#### 🧾 البكج المُجمّع")
            
            # Show SKU and Name separately
            display_data = []
            for idx, comp in enumerate(st.session_state.package_components):
                display_data.append({
                    "#": idx + 1,
                    "SKU": comp["sku"],
                    "الاسم": comp["name"].split(" - ", 1)[1] if " - " in comp["name"] else comp["name"],
                    "النوع": comp["type"],
                    "الكمية": comp["quantity"],
                    "تكلفة الوحدة": f"{comp['unit_cost']:.2f}",
                    "التكلفة الإجمالية": f"{comp['total_cost']:.2f}"
                })
            
            display_df = pd.DataFrame(display_data)
            
            # Show table
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                height=min(400, (len(display_data) + 1) * 35 + 38)
            )
            
            # Recalculate total
            components_df = pd.DataFrame(st.session_state.package_components)
            total_package_cost = components_df["total_cost"].sum()
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col2:
                st.metric("💰 إجمالي تكلفة البكج", f"{total_package_cost:.2f} SAR", 
                         help=f"مجموع {len(st.session_state.package_components)} مكونات")
            with col3:
                if st.button("🔄 إعادة التصميم", type="secondary", use_container_width=True):
                    st.session_state.show_pricing = False
                    st.session_state.package_components = []
                    st.session_state.package_rows = [{"id": 0}]
                    st.rerun()
            
            st.markdown("---")
            
            # Pricing section
            st.markdown("### 💵 حساب التسعير")
            
            col1, col2 = st.columns(2)
            with col1:
                package_name = st.text_input(
                    "اسم البكج الجديد",
                    value="بكج مخصص",
                    key="custom_package_name"
                )
            
            with col2:
                selected_channel = st.selectbox(
                    "🏪 اختر المنصة/القناة",
                    options=list(channels.keys()),
                    key="custom_pkg_channel"
                )

            # اختيارات استبعاد رسوم معينة لهذا البكج
            skip_shipping = st.checkbox(
                "🚚 بدون رسوم شحن",
                value=False,
                help="استبعد رسوم الشحن لهذا البكج فقط",
                key="custom_pkg_skip_shipping",
            )
            skip_preparation = st.checkbox(
                "🧰 بدون رسوم تجهيز",
                value=False,
                help="استبعد رسوم التجهيز/التعبئة لهذا البكج فقط",
                key="custom_pkg_skip_preparation",
            )
            skip_marketing = st.checkbox(
                "📢 بدون رسوم تسويق",
                value=False,
                help="استبعد نسبة التسويق من حساب هذا البكج",
                key="custom_pkg_skip_marketing",
            )

            # Strategy and pricing parameters
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                strategy = st.selectbox(
                    "الاستراتيجية",
                    ["اختراق السوق", "توازن ربحي", "تميز/بريميم", "تصفية"],
                    key="custom_pkg_strategy"
                )
            
            with col2:
                target_margin_input = st.number_input(
                    "هامش الربح المستهدف %",
                    min_value=0,
                    max_value=50,
                    value=9,
                    step=1,
                    key="custom_pkg_margin"
                )
                target_margin = target_margin_input / 100
            
            with col3:
                marketing_boost = st.number_input(
                    "زيادة تسويق إضافية %",
                    min_value=0,
                    max_value=20,
                    value=0,
                    step=1,
                    key="custom_pkg_marketing",
                    disabled=skip_marketing,
                    help="يتم تجاهلها عند اختيار بدون رسوم تسويق",
                )
            
            with col4:
                discount_pct_input = st.number_input(
                    "نسبة الخصم %",
                    min_value=0,
                    max_value=50,
                    value=10,
                    step=1,
                    key="custom_pkg_discount"
                )
                discount_pct = discount_pct_input / 100

            # Competitor price
            competitor_price = st.number_input(
                "سعر المنافس (اختياري)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key="custom_pkg_competitor"
            )

            # Calculate button
            col_btn = st.columns([1, 2, 1])[1]
            with col_btn:
                run_pricing = st.button(
                    "🚀 احسب تسعير البكج المخصص",
                    type="primary",
                    width="stretch",
                    key="custom_pkg_calc"
                )

            if run_pricing:
                ch = channels[selected_channel]
                shipping = 0.0 if skip_shipping else ch.shipping_fixed
                preparation = 0.0 if skip_preparation else ch.preparation_fee
                vat_rate = ch.vat_rate
                free_threshold = getattr(ch, "free_shipping_threshold", 0)
                custom_fees = getattr(ch, "custom_fees", {}) or {}
                marketing_effective = 0.0 if skip_marketing else ch.marketing_pct + (marketing_boost / 100)

                # عرض شروط المنصة المختارة
                st.info(f"📋 **شروط المنصة المختارة ({selected_channel}):**\n"
                       f"- حد الشحن المجاني: {free_threshold} ريال\n"
                       f"- رسوم الشحن: {shipping} ريال\n"
                       f"- رسوم التحضير: {preparation} ريال\n"
                      f"- القاعدة: إذا السعر < {free_threshold} → شحن مجاني | إذا ≥ {free_threshold} → شحن مدفوع")

                channel_dict = {
                    "opex_pct": ch.opex_pct,
                    "marketing_pct": marketing_effective,
                    "platform_pct": ch.platform_pct,
                    "payment_pct": ch.payment_pct,
                    "vat_rate": vat_rate,
                    "discount_rate": discount_pct,
                }

                # حساب نسبة ورسوم مخصصة إن وجدت
                custom_pct = 0.0
                custom_fixed = 0.0
                custom_fees_dict = {}
                if custom_fees:
                    for fee_name, fee_data in custom_fees.items():
                        if fee_data.get("fee_type") == "percentage":
                            custom_pct += fee_data.get("amount", 0)
                        else:
                            custom_fixed += fee_data.get("amount", 0)

                admin_pct = channel_dict["opex_pct"]
                marketing_pct = channel_dict["marketing_pct"]
                platform_pct = channel_dict["platform_pct"]
                payment_pct = channel_dict["payment_pct"]
                
                total_pct = admin_pct + marketing_pct + platform_pct + payment_pct + custom_pct
                denom = 1 - total_pct - target_margin

                if denom <= 0 or (1 - discount_pct) <= 0:
                    st.error("الهامش المطلوب غير ممكن مع نسب الرسوم الحالية. خفّض الهامش أو الرسوم أو الخصم.")
                    st.stop()

                # السيناريو 1: حساب السعر بدون رسوم شحن/تحضير (لو كان الشحن مجاني)
                fixed_costs_without_fees = total_package_cost + custom_fixed
                net_without_fees = fixed_costs_without_fees / denom
                price_after_vat_without_fees = net_without_fees * (1 + vat_rate)
                list_price_without_fees = price_after_vat_without_fees / (1 - discount_pct)
                
                # السيناريو 2: حساب السعر مع رسوم شحن/تحضير (لو كان الشحن مدفوع)
                fixed_costs_with_fees = total_package_cost + shipping + preparation + custom_fixed
                net_with_fees = fixed_costs_with_fees / denom
                price_after_vat_with_fees = net_with_fees * (1 + vat_rate)
                list_price_with_fees = price_after_vat_with_fees / (1 - discount_pct)
                
                # قرار: هل الشحن مجاني أم مدفوع؟
                # إذا السعر بدون رسوم < الحد → استخدم السعر بدون رسوم (شحن مجاني)
                # إذا السعر بدون رسوم ≥ الحد → استخدم السعر مع رسوم (شحن مدفوع)
                if free_threshold > 0 and list_price_without_fees < free_threshold:
                    # الشحن مجاني لأن السعر أقل من الحد
                    actual_shipping = 0
                    actual_preparation = 0
                    fixed_costs = fixed_costs_without_fees
                    net_price = net_without_fees
                    price_after_discount = price_after_vat_without_fees
                    list_price = list_price_without_fees
                    st.success(f"✅ السعر بدون رسوم ({list_price_without_fees:.2f}) ≤ الحد ({free_threshold}) → شحن مجاني (0), تحضير مجاني (0)")
                else:
                    # الشحن مدفوع لأن السعر > الحد (أو لا يوجد حد)
                    actual_shipping = shipping
                    actual_preparation = preparation
                    fixed_costs = fixed_costs_with_fees
                    net_price = net_with_fees
                    price_after_discount = price_after_vat_with_fees
                    list_price = list_price_with_fees
                    if free_threshold > 0:
                        st.success(f"✅ السعر بدون رسوم ({list_price_without_fees:.2f}) > الحد ({free_threshold}) → شحن مدفوع ({actual_shipping}), تحضير مدفوع ({actual_preparation})")
                    else:
                        st.success(f"✅ لا يوجد حد للشحن المجاني → شحن مدفوع ({actual_shipping}), تحضير مدفوع ({actual_preparation})")
                
                # استخدام القيم المحسوبة
                # B (discount amount) = A * discount_rate
                discount_amount = list_price * discount_pct
                
                # الرسوم المحسوبة من السعر الصافي
                admin_fee = net_price * admin_pct
                marketing_fee = net_price * marketing_pct
                platform_fee = net_price * platform_pct
                payment_fee = net_price * payment_pct
                
                # حساب الرسوم المخصصة
                custom_fees_total = custom_fixed
                if custom_fees:
                    for fee_name, fee_data in custom_fees.items():
                        if fee_data.get("fee_type") == "percentage":
                            fee_amount = net_price * fee_data.get("amount", 0)
                        else:
                            fee_amount = fee_data.get("amount", 0)
                        custom_fees_dict[fee_name] = fee_amount
                        if fee_data.get("fee_type") == "percentage":
                            custom_fees_total += fee_amount
                
                total_costs_fees = total_package_cost + actual_shipping + actual_preparation + admin_fee + marketing_fee + platform_fee + payment_fee + custom_fees_total
                profit = net_price - total_costs_fees
                margin_pct = target_margin  # الهامش المستهدف بالضبط
                
                # بناء breakdown يدوياً
                breakdown = {
                    "sale_price": list_price,
                    "discount_amount": discount_amount,
                    "discount_rate": discount_pct,
                    "price_after_discount": price_after_discount,
                    "vat_rate": vat_rate,
                    "net_price": net_price,
                    "custom_fees": custom_fees_dict,
                    "custom_fees_total": custom_fees_total,
                    "cogs": total_package_cost,
                    "preparation_fee": actual_preparation,
                    "shipping_fee": actual_shipping,
                    "admin_fee": admin_fee,
                    "marketing_fee": marketing_fee,
                    "payment_fee": payment_fee,
                    "platform_fee": platform_fee,
                    "total_costs_fees": total_costs_fees,
                    "profit": profit,
                    "margin_pct": margin_pct,
                    "breakeven_price": (fixed_costs / (1 - total_pct)) * (1 + vat_rate) / (1 - discount_pct) if (1 - total_pct) > 0 else 0,
                }

                # Display results
                UIComponents.render_section_header("نتيجة التسعير", "سعر موصى به للبكج المخصص", "📊")
                
                colm1, colm2, colm3, colm4 = st.columns(4)
                with colm1:
                    st.metric("سعر البيع شامل الضريبة قبل الخصم", f"{list_price:.2f} SAR")
                with colm2:
                    st.metric("سعر بعد الخصم", f"{breakdown['price_after_discount']:.2f} SAR")
                with colm3:
                    st.metric("صافي الربح", f"{breakdown['profit']:.2f} SAR")
                with colm4:
                    st.metric("هامش الربح", f"{breakdown['margin_pct']*100:.1f}%")

                # Detailed comparison tables (سعرنا / المنافس / التعادل)
                def build_detail_rows(bd: dict, rate_map: dict, list_price: float) -> pd.DataFrame:
                    custom_total = bd.get("custom_fees_total", 0)
                    rows = [
                        ("الجزء الأول: التسعير", None, None),
                        ("سعر البيع شامل الضريبة قبل الخصم", list_price, None),
                        ("نسبة الخصم", bd.get("discount_rate", 0) * 100, "%"),
                        ("مبلغ الخصم", bd.get("discount_amount", 0), None),
                        ("سعر البيع شامل الضريبة بعد الخصم", bd.get("price_after_discount", 0), None),
                        ("سعر البيع غير الضريبة بعد الخصم", bd.get("net_price", 0), None),
                        ("الجزء الثاني: تكلفة البضاعة المباعة", None, None),
                        ("تكلفة البضاعة للوحدة", bd.get("cogs", 0), None),
                        ("الجزء الثالث: رسوم المنصة", None, None),
                        ("التحضير", bd.get("preparation_fee", 0), None),
                        ("الشحن", bd.get("shipping_fee", 0), None),
                    ]

                    if bd.get("admin_fee", 0) > 0:
                        rows.append(("المصاريف الإدارية", bd.get("admin_fee", 0), f"{rate_map['admin']*100:.1f}%"))
                    if bd.get("marketing_fee", 0) > 0:
                        rows.append(("مصاريف التسويق", bd.get("marketing_fee", 0), f"{rate_map['marketing']*100:.1f}%"))
                    if bd.get("payment_fee", 0) > 0:
                        rows.append(("رسوم الدفع", bd.get("payment_fee", 0), f"{rate_map['payment']*100:.1f}%"))
                    if bd.get("platform_fee", 0) > 0:
                        rows.append(("رسوم المنصات", bd.get("platform_fee", 0), f"{rate_map['platform']*100:.1f}%"))
                    if custom_total > 0:
                        rows.append(("رسوم مخصصة", custom_total, None))

                    rows.extend(
                        [
                            ("إجمالي التكلفة والرسوم", bd.get("total_costs_fees", 0), None),
                            ("الجزء الرابع: صافي الربح", None, None),
                            ("الربح", bd.get("profit", 0), None),
                            ("هامش الربح %", bd.get("margin_pct", 0) * 100, "%"),
                        ]
                    )

                    df = pd.DataFrame(rows, columns=["البند", "القيمة", "ملاحظة"])

                    def format_comparison_row(row):
                        label = row["البند"]
                        if label and label.startswith("الجزء"):
                            return ["background-color: #1e88e5; color: white; font-weight: bold"] * len(row)
                        if label == "إجمالي التكلفة والرسوم":
                            return ["background-color: #fff3cd; font-weight: bold"] * len(row)
                        if label in ["الربح", "هامش الربح %"]:
                            return ["background-color: #d4edda; font-weight: bold"] * len(row)
                        return [""] * len(row)

                    styled = (
                        df.style.apply(format_comparison_row, axis=1)
                        .format(
                            {
                                "القيمة": lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else ("" if x is None else x),
                                "ملاحظة": lambda x: "" if x is None else x,
                            }
                        )
                        .set_table_styles(
                            [
                                {
                                    "selector": "th",
                                    "props": [
                                        ("background-color", "#1e88e5"),
                                        ("color", "white"),
                                        ("font-weight", "bold"),
                                        ("text-align", "center"),
                                        ("padding", "8px"),
                                    ],
                                },
                                {
                                    "selector": "td",
                                    "props": [("text-align", "right"), ("padding", "6px"), ("border", "1px solid #ddd")],
                                },
                                {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                            ]
                        )
                    )

                    return styled

                # Build rate map once
                rate_map = {
                    "admin": channel_dict.get("opex_pct", 0),
                    "marketing": channel_dict.get("marketing_pct", 0),
                    "payment": channel_dict.get("payment_pct", 0),
                    "platform": channel_dict.get("platform_pct", 0),
                }

                # Breakeven breakdown (Goal Seek: margin = 0%) باستخدام نفس منطق العتبة
                be_calc = calculate_price_breakdown(
                    cogs=total_package_cost,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_pct,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=None,
                )
                breakeven_list_price = be_calc["margin_prices"][0.00]
                breakeven_breakdown = calculate_price_breakdown(
                    cogs=total_package_cost,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_pct,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=breakeven_list_price,
                )

                # Competitor breakdown (if provided)
                competitor_breakdown = None
                if competitor_price and competitor_price > 0:
                    competitor_breakdown = calculate_price_breakdown(
                        cogs=total_package_cost,
                        channel_fees=channel_dict,
                        shipping=shipping,
                        preparation=preparation,
                        discount_rate=discount_pct,
                        vat_rate=vat_rate,
                        free_shipping_threshold=free_threshold,
                        custom_fees=custom_fees,
                        price_with_vat=competitor_price,
                    )

                st.markdown("### مقارنة سعرنا مع المنافس (تفصيل كامل مثل ورقة الحساب)")
                col_cmp1, col_cmp2, col_cmp3 = st.columns(3)
                table_height = 820
                with col_cmp1:
                    st.markdown("**سعرنا**")
                    styled_ours = build_detail_rows(breakdown, rate_map, list_price)
                    st.dataframe(styled_ours, width="stretch", hide_index=True, height=table_height)
                with col_cmp2:
                    st.markdown("**سعر المنافس**")
                    if competitor_breakdown:
                        styled_comp = build_detail_rows(competitor_breakdown, rate_map, competitor_price)
                        st.dataframe(styled_comp, width="stretch", hide_index=True, height=table_height)
                    else:
                        st.info("أدخل سعر المنافس لعرض الجدول")
                with col_cmp3:
                    st.markdown("**سعر التعادل (0% ربح)**")
                    styled_breakeven = build_detail_rows(breakeven_breakdown, rate_map, breakeven_list_price)
                    st.dataframe(styled_breakeven, width="stretch", hide_index=True, height=table_height)

                # Components breakdown
                st.markdown("---")
                st.markdown("### 📋 مكونات البكج")
                st.dataframe(display_df, width="stretch", hide_index=True, height=300)
                
                # Save option
                st.markdown("---")
                if st.button("💾 حفظ البكج المخصص", type="primary", width="stretch"):
                    try:
                        import os
                        
                        data_dir = os.path.join(os.path.dirname(__file__), "data")
                        os.makedirs(data_dir, exist_ok=True)

                        pricing_record = {
                            "التاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "اسم المنتج/البكج": package_name,
                            "SKU": "CUSTOM_PKG",
                            "النوع": "بكج مخصص",
                            "المنصة": selected_channel,
                            "التكلفة": total_package_cost,
                            "سعر القائمة": list_price,
                            "سعر بعد الخصم": breakdown["price_after_discount"],
                            "الربح": breakdown["profit"],
                            "هامش الربح %": breakdown["margin_pct"] * 100,
                            "بدون رسوم شحن": "نعم" if skip_shipping else "لا",
                            "بدون رسوم تجهيز": "نعم" if skip_preparation else "لا",
                            "بدون رسوم تسويق": "نعم" if skip_marketing else "لا",
                            "المكونات": " + ".join([f"{c['name']} (x{c['quantity']})" for c in st.session_state.package_components]),
                        }

                        history_file = os.path.join(data_dir, "pricing_history.csv")

                        if os.path.exists(history_file):
                            history_df = pd.read_csv(history_file, encoding="utf-8-sig")
                            history_df = pd.concat([history_df, pd.DataFrame([pricing_record])], ignore_index=True)
                        else:
                            history_df = pd.DataFrame([pricing_record])

                        history_df.to_csv(history_file, index=False, encoding="utf-8-sig")
                        append_audit_event(
                            data_dir,
                            {
                                **pricing_record,
                                "event_type": "pricing_saved",
                                "scope": "custom_package",
                                "sku": pricing_record.get("SKU", ""),
                                "item_name": pricing_record.get("اسم المنتج/البكج", ""),
                                "item_type": pricing_record.get("النوع", ""),
                                "channel": pricing_record.get("المنصة", ""),
                                "cogs": pricing_record.get("التكلفة", 0),
                                "list_price": pricing_record.get("سعر القائمة", 0),
                                "margin_pct": pricing_record.get("هامش الربح %", 0),
                                "profit": pricing_record.get("الربح", 0),
                                "details": {
                                    "components": pricing_record.get("المكونات", ""),
                                    "skip_shipping": skip_shipping,
                                    "skip_preparation": skip_preparation,
                                    "skip_marketing": skip_marketing,
                                    "saved_from": "custom_package_builder",
                                },
                            },
                        )
                        st.success("✅ تم حفظ البكج المخصص بنجاح!")
                        
                    except Exception as e:
                        st.error(f"❌ خطأ في الحفظ: {e}")
        
        else:
            st.info("💡 ابدأ بإضافة المنتجات/البكجات أعلاه، ثم اضغط **تجميع** لحساب التسعير")

elif st.session_state.page == "salla_review":
    UIComponents.render_section_header(
        "مقارنة اسعار سلة بالتكلفة",
        "الربح = صافي سعر البيع بعد الضريبة - تكلفة البضاعة - رسوم المنصة والقناة",
        "سلة",
    )
    st.info(
        "يتم أخذ سعر العميل النهائي من ملف سلة. ولأن السعر شامل ضريبة القيمة المضافة، يتم أولاً حساب صافي البيع بدون الضريبة، "
        "ثم: الربح = صافي البيع بدون الضريبة - تكلفة البضاعة من Zoho - رسوم المنصة/القناة."
    )
    st.caption("المطابقة مع بيانات Zoho تتم باستخدام SKU فقط. اسم المنتج للعرض والبحث فقط ولا يدخل في الربط.")

    if not st.session_state.get("zoho_upload_frames"):
        st.warning("ارفع ملفات Zoho الثلاثة أولاً في صفحة رفع الملفات حتى يتم حساب تكلفة المنتجات والبكجات.")
        if st.button("فتح صفحة رفع ملفات Zoho", type="primary", width="stretch", key="salla_review_open_upload_for_zoho"):
            st.session_state.page = "upload"
            st.rerun()
        st.stop()

    if materials is None or product_recipes is None or package_compositions is None:
        try:
            materials, product_recipes, products_summary, package_compositions, packages_summary = load_all_data()
        except Exception as e:
            st.error(f"تعذر تحميل تكلفة Zoho من الملفات المرفوعة: {e}")
            if st.button("إعادة رفع ملفات Zoho", type="primary", width="stretch", key="salla_review_reload_zoho"):
                st.session_state.page = "upload"
                st.rerun()
            st.stop()

    channels_file = "data/channels.json"
    channels_data = load_channels(channels_file)
    if not channels_data:
        st.warning("لا توجد منصات محفوظة. أضف منصة من صفحة المنصات أولاً.")
        st.stop()

    channel_names = list(channels_data.keys())
    default_channel_index = 0
    for idx, channel_name in enumerate(channel_names):
        if "سلة" in channel_name or "الرئيسية" in channel_name:
            default_channel_index = idx
            break

    col_config1, col_config2, col_config3 = st.columns([1, 1, 1])
    with col_config1:
        selected_channel = st.selectbox(
            "المنصة المستخدمة في الحساب",
            options=channel_names,
            index=default_channel_index,
            key="salla_review_channel",
        )
    with col_config2:
        min_margin_pct = st.number_input(
            "أقل هامش مقبول %",
            min_value=0.0,
            max_value=60.0,
            value=15.0,
            step=0.5,
            key="salla_review_min_margin",
        )
    with col_config3:
        st.metric("ملف أسعار سلة", "مرفوع في الجلسة" if st.session_state.get("salla_prices_df") is not None else "غير مرفوع")

    try:
        if st.session_state.get("salla_prices_df") is not None:
            salla_source_df = st.session_state["salla_prices_df"].copy()
        else:
            st.warning("لم يتم رفع ملف أسعار سلة في هذه الجلسة. ارفعه من صفحة رفع الملفات ثم ارجع للمقارنة.")
            if st.button("فتح صفحة رفع الملفات", type="primary", width="stretch"):
                st.session_state.page = "upload"
                st.rerun()
            st.stop()

        sku_options = list(salla_source_df.columns)
        detected_sku_col = detect_salla_sku_column(salla_source_df)
        default_sku_index = sku_options.index(detected_sku_col) if detected_sku_col in sku_options else 0
        selected_salla_sku_col = st.selectbox(
            "عمود SKU المستخدم للمطابقة",
            options=sku_options,
            index=default_sku_index,
            key="salla_review_sku_column",
            format_func=lambda col: "SKU محفوظ للمطابقة" if col == SALLA_MATCH_SKU_COL else str(col),
            help="اختر العمود الذي يحتوي SKU الحقيقي في ملف سلة. اسم المنتج لا يستخدم في المطابقة.",
        )
        salla_source_df = set_salla_match_sku_column(salla_source_df, selected_salla_sku_col)
        valid_sku_count = count_valid_sku_values(salla_source_df, SALLA_MATCH_SKU_COL)
        if valid_sku_count == 0:
            st.warning("عمود SKU المختار لا يحتوي قيماً صالحة. اختر عمود SKU الصحيح أو ارفع ملف سلة يحتوي SKU.")
        else:
            st.caption(f"سيتم الربط باستخدام {valid_sku_count} قيمة SKU صالحة من عمود: {selected_salla_sku_col}")
            st.session_state["salla_prices_df"] = salla_source_df.copy()

        cost_catalog_df = build_cost_catalog(
            materials,
            product_recipes,
            products_summary,
            package_compositions,
            packages_summary,
        )
        review_df, review_summary = calculate_salla_price_review(
            salla_source_df,
            cost_catalog_df,
            channels_data[selected_channel],
            min_margin_pct=min_margin_pct,
        )
    except Exception as e:
        st.error(f"تعذر إنشاء مقارنة اسعار سلة بالتكلفة: {e}")
        st.stop()

    st.markdown("---")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("إجمالي صفوف سلة", review_summary["total_rows"])
    m2.metric("بسعر بيع فعلي", review_summary.get("active_rows", 0))
    m3.metric("تمت مطابقتها", review_summary["matched_rows"])
    m4.metric("غير مطابقة", review_summary["unmatched_rows"])
    m5.metric("أسعار مناسبة", review_summary["profitable_rows"])
    m6.metric("تحتاج مراجعة", review_summary["low_margin_rows"] + review_summary["loss_rows"] + review_summary["needs_review_rows"])

    if review_summary["matched_rows"] == 0:
        st.warning("لم تتم مطابقة أي صف. تأكد أن عمود SKU في ملف سلة يحتوي نفس أكواد SKU الموجودة في ملفات Zoho.")

    priced_rows = review_df[pd.to_numeric(review_df["Margin_%"], errors="coerce").notna()].copy()
    if not priced_rows.empty:
        priced_rows["Margin_%"] = pd.to_numeric(priced_rows["Margin_%"], errors="coerce")
        priced_rows["Profit"] = pd.to_numeric(priced_rows["Profit"], errors="coerce")
        avg_margin = pd.to_numeric(priced_rows["Margin_%"], errors="coerce").mean()
        total_profit = pd.to_numeric(priced_rows["Profit"], errors="coerce").sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("متوسط الهامش", f"{avg_margin:.2f}%")
        c2.metric("إجمالي الربح المتوقع", f"{total_profit:,.2f} SAR")
        c3.metric("عدد الخسارة", review_summary["loss_rows"])

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            status_counts = review_df["Review_Status"].value_counts().reset_index()
            status_counts.columns = ["الحالة", "العدد"]
            fig_status = px.pie(
                status_counts,
                values="العدد",
                names="الحالة",
                title="توزيع حالات الأسعار",
                color="الحالة",
                color_discrete_map={
                    "مناسب": "#15803D",
                    "هامش منخفض": "#B45309",
                    "خسارة": "#B91C1C",
                    "تحتاج مراجعة": "#475467",
                },
            )
            fig_status.update_layout(height=360)
            st.plotly_chart(fig_status, width="stretch")

        with chart_col2:
            worst_rows = priced_rows.sort_values("Margin_%", ascending=True).head(15)
            fig_worst = px.bar(
                worst_rows,
                x="Salla_Name",
                y="Margin_%",
                color="Review_Status",
                title="أقل المنتجات من حيث الهامش",
                color_discrete_map={
                    "مناسب": "#15803D",
                    "هامش منخفض": "#B45309",
                    "خسارة": "#B91C1C",
                },
            )
            fig_worst.update_layout(height=360, xaxis_title="المنتج", yaxis_title="هامش الربح %")
            st.plotly_chart(fig_worst, width="stretch")

    st.markdown("---")
    st.subheader("جدول مقارنة اسعار سلة بالتكلفة")

    active_only = st.checkbox(
        "عرض المنتجات النشطة فقط",
        value=True,
        key="salla_review_active_only",
        help="يقصد بها الصفوف التي لها سعر بيع نهائي للعميل أكبر من صفر في ملف سلة.",
    )

    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    with filter_col1:
        search_term = st.text_input("بحث باسم المنتج أو SKU", key="salla_review_search")
    with filter_col2:
        status_filter = st.multiselect(
            "حالة السعر",
            options=["مناسب", "هامش منخفض", "خسارة", "تحتاج مراجعة"],
            default=["مناسب", "هامش منخفض", "خسارة", "تحتاج مراجعة"],
            key="salla_review_status_filter",
        )
    with filter_col3:
        match_filter = st.multiselect(
            "حالة المطابقة",
            options=["Matched", "Not Matched"],
            default=["Matched", "Not Matched"],
            key="salla_review_match_filter",
        )

    filtered_review_df = review_df.copy()
    if active_only and "Active_On_Store" in filtered_review_df.columns:
        filtered_review_df = filtered_review_df[filtered_review_df["Active_On_Store"]]
    if search_term:
        search_mask = (
            filtered_review_df["Salla_Name"].astype(str).str.contains(search_term, case=False, na=False)
            | filtered_review_df["Salla_SKU"].astype(str).str.contains(search_term, case=False, na=False)
            | filtered_review_df["System_SKU"].astype(str).str.contains(search_term, case=False, na=False)
            | filtered_review_df["System_Name"].astype(str).str.contains(search_term, case=False, na=False)
        )
        filtered_review_df = filtered_review_df[search_mask]
    if status_filter:
        filtered_review_df = filtered_review_df[filtered_review_df["Review_Status"].isin(status_filter)]
    if match_filter:
        filtered_review_df = filtered_review_df[filtered_review_df["Match_Status"].isin(match_filter)]

    st.info(f"عرض {len(filtered_review_df)} من أصل {len(review_df)} صف")

    display_cols = [
        "Salla_SKU",
        "Salla_Name",
        "System_SKU",
        "Item_Type",
        FINAL_INCL_VAT_COL,
        "Sales_VAT",
        "Net_Price_Excl_VAT",
        "COGS",
        "COGS_Details",
        "Shipping_Fee",
        "Preparation_Fee",
        "Platform_Fee",
        "Payment_Fee",
        "Marketing_Fee",
        "Opex_Fee",
        "Custom_Fees",
        "Channel_Fees_Total",
        "Fees_Formula",
        "Total_Costs_And_Fees",
        "Profit",
        "Margin_%",
        "Profit_Formula",
        "Price_Gap_To_Breakeven",
        "Review_Status",
        "Match_Method",
        "Match_Note",
        "Review_Note",
    ]
    available_display_cols = [col for col in display_cols if col in filtered_review_df.columns]
    display_df = filtered_review_df[available_display_cols].rename(
        columns={
            "Salla_Product_ID": "رقم المنتج في سلة",
            "Salla_SKU": "SKU سلة",
            "Salla_Name": "اسم المنتج في سلة",
            "System_SKU": "SKU النظام",
            "System_Name": "اسم المنتج في Zoho",
            "Item_Type": "النوع",
            FINAL_INCL_VAT_COL: "سعر البيع للعميل النهائي",
            "Sales_VAT": "ضريبة البيع",
            "Net_Price_Excl_VAT": "صافي البيع بدون الضريبة",
            "COGS": "تكلفة البضاعة",
            "COGS_Details": "تفاصيل تكلفة البضاعة",
            "Shipping_Fee": "رسوم الشحن",
            "Preparation_Fee": "رسوم التحضير",
            "Platform_Fee": "رسوم المنصة",
            "Payment_Fee": "رسوم الدفع",
            "Marketing_Fee": "رسوم التسويق",
            "Opex_Fee": "رسوم التشغيل",
            "Custom_Fees": "رسوم إضافية",
            "Channel_Fees_Total": "إجمالي الرسوم",
            "Fees_Formula": "تفصيل إجمالي الرسوم",
            "Total_Costs_And_Fees": "تكلفة البضاعة + إجمالي الرسوم",
            "Profit": "الربح",
            "Margin_%": "نسبة الربح %",
            "Profit_Formula": "معادلة الربح: سعر العميل - الضريبة - التكلفة - الرسوم",
            "Breakeven_Price_Incl_VAT": "نقطة التعادل شامل الضريبة",
            "Price_Gap_To_Breakeven": "فرق السعر عن التعادل",
            "Review_Status": "حالة السعر",
            "Match_Method": "طريقة المطابقة",
            "Match_Note": "ملاحظة المطابقة",
            "Review_Note": "ملاحظة المراجعة",
        }
    )
    hidden_salla_price_cols = [
        "سعر المنتج",
        "سعر التكلفة",
        "السعر المخفض",
        "تاريخ بداية التخفيض",
        "تاريخ نهاية التخفيض",
        FINAL_EXCL_VAT_COL,
    ]
    display_df = display_df.drop(columns=hidden_salla_price_cols, errors="ignore")

    st.dataframe(display_df, width="stretch", hide_index=True, height=620)

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "تنزيل مقارنة اسعار سلة CSV",
            data=ExportManager.export_to_csv(display_df, "salla_price_review.csv"),
            file_name=f"salla_cost_comparison_{selected_channel}.csv",
            mime="text/csv",
            width="stretch",
        )
    with d2:
        st.download_button(
            "تنزيل مقارنة اسعار سلة Excel",
            data=ExportManager.export_to_excel(display_df, "salla_price_review.xlsx", sheet_name="comparison"),
            file_name=f"salla_cost_comparison_{selected_channel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

elif st.session_state.page == "profit_margins":
    UIComponents.render_section_header("📊 تسعير منصة كاملة", "نسخة احترافية شاملة مع مؤشرات ورؤى فورية", "🚀")
    UIComponents.render_info_box(
        "احسب أسعار جميع المنتجات والبكجات دفعة واحدة مع لوحات بصرية، تنبيهات ذكية، وتصدير فوري.", "info"
    )

    if quality_report is None or not quality_report.is_ready:
        st.error("لا يمكن تشغيل التسعير الجماعي قبل معالجة مشاكل البيانات الحرجة.")
        render_commercial_readiness(quality_report, key_prefix="bulk_pricing_blocker")
        st.stop()

    # Load channels
    channels_file = "data/channels.json"
    channels_data = load_channels(channels_file)
    if not channels_data:
        st.warning("لا توجد قنوات محفوظة. يرجى إضافة قناة من صفحة الإعدادات أولاً.")
        st.stop()

    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        UIComponents.render_metric_card(
            "عدد المنتجات", str(len(product_recipes)), "جاهزة للتسعير", "📦", ColorScheme.PRIMARY
        )
    with col2:
        UIComponents.render_metric_card(
            "عدد البكجات", str(len(package_compositions)), "محتوى مركب", "🎁", ColorScheme.SUCCESS
        )
    with col3:
        total_items = len(product_recipes) + len(package_compositions)
        UIComponents.render_metric_card("إجمالي العناصر", str(total_items), "منتج + بكج", "🧮", ColorScheme.WARNING)
    with col4:
        UIComponents.render_metric_card(
            "آخر تحديث للبيانات", DateTimeHelper.get_date_string(), "من ملفات البيانات", "⏱️", ColorScheme.INFO
        )

    st.markdown("---")

    # Configuration
    st.subheader("⚙️ إعدادات التسعير الجماعي")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        selected_channel = st.selectbox(
            "القناة / المنصة",
            options=list(channels_data.keys()),
            key="pm_channel",
            help="حدد القناة لتطبيق رسومها الافتراضية",
        )

    with col2:
        target_margin_pct = st.number_input(
            "هامش الربح المستهدف (%)", min_value=0.0, max_value=50.0, value=18.0, step=0.5, key="pm_margin"
        )

    with col3:
        discount_pct = st.number_input(
            "نسبة الخصم للعميل (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5, key="pm_discount"
        )

    target_margin = target_margin_pct / 100
    discount_rate = discount_pct / 100
    channel = channels_data[selected_channel]

    # Set default values (no filtering)
    item_filter = ["منتج", "بكج"]
    min_cogs = 0.0
    max_cogs = 0.0

    st.caption("يتم تطبيق الخصم على السعر النهائي للعميل، بينما يبقى الهامش المستهدف بعد الخصم.")

    # Auto-recalculate when channel changes
    if "last_pm_channel" not in st.session_state:
        st.session_state["last_pm_channel"] = None
    
    channel_changed = (
        st.session_state["last_pm_channel"] is not None 
        and st.session_state["last_pm_channel"] != selected_channel
    )

    col_btn_left, col_btn_center, col_btn_right = st.columns([1, 2, 1])
    with col_btn_center:
        run_pricing = st.button("🚀 تشغيل المحرك الاحترافي", type="primary", width="stretch")

    if run_pricing or channel_changed:
        st.markdown("---")
        UIComponents.render_section_header("نتائج التسعير الجماعي", "حساب شامل لكل منتج وبكج", "📑")

        # Helper: calculate component cost
        def calculate_component_cost(sku, component_type):
            return resolve_component_cost(sku, materials, product_recipes, package_compositions)

        # Build items list
        all_items = []
        for _, row in products_summary.iterrows():
            all_items.append(
                {
                    "sku": row["Product_SKU"],
                    "name": row.get("Product_Name", row["Product_SKU"]),
                    "type": "منتج",
                    "cogs": calculate_component_cost(row["Product_SKU"], "product"),
                }
            )

        for _, row in packages_summary.iterrows():
            all_items.append(
                {
                    "sku": row["Package_SKU"],
                    "name": row.get("Package_Name", row["Package_SKU"]),
                    "type": "بكج",
                    "cogs": calculate_component_cost(row["Package_SKU"], "package"),
                }
            )

        # Apply filters
        filtered_items = [item for item in all_items if item["type"] in item_filter]
        if min_cogs > 0:
            filtered_items = [item for item in filtered_items if item["cogs"] >= min_cogs]
        if max_cogs > 0:
            filtered_items = [item for item in filtered_items if item["cogs"] <= max_cogs]

        if not filtered_items:
            st.warning("لا توجد عناصر مطابقة للمعايير المحددة")
            st.stop()

        # Pricing calculations
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        results = []

        shipping = channel.shipping_fixed
        preparation = channel.preparation_fee
        vat_rate = channel.vat_rate
        custom_fees = channel.custom_fees if hasattr(channel, "custom_fees") else {}
        free_shipping_threshold = channel.free_shipping_threshold if hasattr(channel, "free_shipping_threshold") else 0

        # إعداد قاموس الرسوم
        channel_dict = {
            "platform_pct": channel.platform_pct,
            "payment_pct": channel.payment_pct,
            "marketing_pct": channel.marketing_pct,
            "opex_pct": channel.opex_pct,
            "vat_rate": vat_rate,
        }

        # Binary Search Function (نفس الطريقة من صفحة التسعير الفردي)
        def solve_price_for_margin(cogs_val, target_margin_val):
            """استخدام Binary Search للوصول للسعر الذي يحقق الهامش المستهدف بدقة"""
            low = cogs_val * 1.1
            high = cogs_val * 10
            best_price = high
            best_bd = None

            tolerance = 0.0001
            for iteration in range(100):
                mid = (low + high) / 2
                bd = calculate_price_breakdown(
                    cogs=cogs_val,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_shipping_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=mid,
                )

                margin_diff = bd["margin_pct"] - target_margin_val

                if abs(margin_diff) < tolerance:
                    return mid, bd

                if margin_diff < 0:
                    low = mid
                else:
                    high = mid

                best_price = mid
                best_bd = bd

            return best_price, best_bd

        for idx, item in enumerate(filtered_items):
            status_placeholder.text(f"جاري تسعير {item['sku']} ({idx + 1}/{len(filtered_items)})")

            cogs_val = item["cogs"]

            # استخدام Binary Search للحصول على السعر الدقيق
            try:
                price_with_vat, breakdown = solve_price_for_margin(cogs_val, target_margin)

                # حساب السعر قبل الخصم
                price_before_discount = (
                    price_with_vat / (1 - discount_rate) if discount_rate > 0 else price_with_vat
                )

                # توليد تنبيهات
                alerts = []
                if breakdown["margin_pct"] < 0:
                    alerts.append("⛔ تحذير: السعر الحالي يحقق خسارة!")
                elif breakdown["margin_pct"] < 0.05:
                    alerts.append("⚠️ تحذير: هامش الربح أقل من الحد الأدنى المقبول (5.0%)")
                elif breakdown["margin_pct"] < 0.15:
                    alerts.append("💡 ملاحظة: هامش الربح أقل من الموصى به (15.0%)")
                elif breakdown["margin_pct"] >= 0.25:
                    alerts.append(f"✅ ممتاز: هامش ربح ممتاز ({breakdown['margin_pct']*100:.1f}%)")

                alerts_text = " | ".join(alerts) if alerts else "جيد"

                # حساب ROI
                roi = (breakdown["profit"] / breakdown["total_costs_fees"]) * 100 if breakdown["total_costs_fees"] > 0 else 0

                results.append(
                    {
                        "SKU": item["sku"],
                        "الاسم": item["name"],
                        "النوع": item["type"],
                        "الحالة": "تم التسعير",
                        "التكلفة": breakdown["cogs"],
                        "رسوم الشحن": breakdown["shipping_fee"],
                        "رسوم التحضير": breakdown["preparation_fee"],
                        "رسوم إدارية": breakdown["admin_fee"],
                        "رسوم تسويق": breakdown["marketing_fee"],
                        "رسوم الدفع": breakdown.get("payment_fee", 0),
                        "رسوم المنصة": breakdown["platform_fee"],
                        "رسوم إضافية مخصصة": breakdown.get("custom_fees_total", 0),
                        "إجمالي الرسوم": breakdown["total_costs_fees"] - breakdown["cogs"],
                        "سعر قبل الخصم": price_before_discount,
                        "السعر النهائي بعد الخصم": breakdown["price_after_discount"],
                        "الربح": breakdown["profit"],
                        "هامش الربح %": breakdown["margin_pct"] * 100,
                        "ROI %": roi,
                        "نقطة التعادل": breakdown["breakeven_price"],
                        "الهامش الآمن %": ((breakdown["price_after_discount"] - breakdown["breakeven_price"]) / breakdown["breakeven_price"] * 100) if breakdown["breakeven_price"] > 0 else 0,
                        "توصية السعر": price_with_vat,
                        "تنبيهات": alerts_text,
                    }
                )
            except Exception as e:
                # في حالة فشل الحساب
                results.append(
                    {
                        "SKU": item["sku"],
                        "الاسم": item["name"],
                        "النوع": item["type"],
                        "الحالة": "غير قابل للتحقيق",
                        "التكلفة": cogs_val,
                        "رسوم الشحن": 0.0,
                        "رسوم التحضير": 0.0,
                        "رسوم إدارية": 0.0,
                        "رسوم تسويق": 0.0,
                        "رسوم المنصة": 0.0,
                        "إجمالي الرسوم": 0.0,
                        "سعر قبل الخصم": 0.0,
                        "السعر النهائي بعد الخصم": 0.0,
                        "الربح": 0.0,
                        "هامش الربح %": 0.0,
                        "ROI %": 0.0,
                        "نقطة التعادل": 0.0,
                        "الهامش الآمن %": 0.0,
                        "توصية السعر": 0.0,
                        "تنبيهات": f"خطأ في الحساب: {str(e)}",
                    }
                )


            progress_bar.progress((idx + 1) / len(filtered_items))

        status_placeholder.empty()
        progress_bar.empty()

        if not results:
            st.warning("لا توجد نتائج للعرض")
            st.stop()

        df_results = pd.DataFrame(results)
        priced_df = df_results[df_results["الحالة"] == "تم التسعير"]

        if priced_df.empty:
            st.warning("لم يتم تسعير أي عنصر بسبب حدود الهامش أو الفلاتر")
            st.stop()

        # Save results to session state
        st.session_state["priced_results"] = priced_df
        st.session_state["last_pm_channel"] = selected_channel
        st.session_state["last_pm_target_margin"] = target_margin_pct
        
        st.success("✅ تم التسعير بنجاح! استخدم الفلاتر أدناه للبحث والتصفية.")

    # Display results if available (outside the if block to allow filtering)
    if "priced_results" in st.session_state and st.session_state["priced_results"] is not None:
        priced_df = st.session_state["priced_results"]
        # Retrieve saved target margin for display
        saved_target_margin = st.session_state.get("last_pm_target_margin", target_margin_pct)
        
        st.markdown("---")
        
        # Summary metrics
        st.markdown("### 💡 لقطات سريعة")
        col1, col2, col3, col4 = st.columns(4)

        avg_margin = priced_df["هامش الربح %"].mean()
        total_revenue = priced_df["السعر النهائي بعد الخصم"].sum()
        profitable = len(priced_df[priced_df["الربح"] > 0])
        loss_items = len(priced_df[priced_df["الربح"] <= 0])

        with col1:
            UIComponents.render_metric_card(
                "متوسط الهامش",
                FormatHelper.format_percentage(avg_margin, 1),
                f"هدفك {saved_target_margin:.0f}%",
                "📈",
                ColorScheme.SUCCESS,
            )
        with col2:
            UIComponents.render_metric_card(
                "إجمالي الإيراد المتوقع",
                FormatHelper.format_currency(total_revenue),
                "بعد الخصم",
                "💰",
                ColorScheme.PRIMARY,
            )
        with col3:
            UIComponents.render_metric_card("منتجات رابحة", str(profitable), "عناصر تحقق ربح", "✅", ColorScheme.INFO)
        with col4:
            UIComponents.render_metric_card(
                "منتجات بحاجة مراجعة", str(loss_items), "هامش منخفض أو خسارة", "⚠️", ColorScheme.WARNING
            )

        st.markdown("---")

        # رسوم بيانية تفاعلية للنتائج
        st.markdown("### 📊 تحليل بصري للنتائج")
        
        tab1, tab2, tab3, tab4 = st.tabs(["💰 توزيع الأرباح", "📈 هوامش الربح", "💵 التسعير", "📉 التكاليف"])
        
        with tab1:
            st.markdown("#### توزيع الأرباح حسب المنتجات")
            # رسم بياني شريطي للأرباح
            top_n = min(15, len(priced_df))
            top_profit_df = priced_df.nlargest(top_n, "الربح")[["الاسم", "الربح", "هامش الربح %"]].copy()
            
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Bar(
                x=top_profit_df["الاسم"],
                y=top_profit_df["الربح"],
                marker_color=top_profit_df["الربح"].apply(
                    lambda x: '#2ecc71' if x > 0 else '#e74c3c'
                ),
                text=top_profit_df["الربح"].round(2),
                textposition='outside',
                name='الربح',
                hovertemplate='<b>%{x}</b><br>الربح: %{y:.2f} SAR<br>الهامش: %{customdata:.1f}%<extra></extra>',
                customdata=top_profit_df["هامش الربح %"]
            ))
            
            fig_profit.update_layout(
                title=f"أعلى {top_n} منتجات من حيث الربح",
                xaxis_title="المنتج",
                yaxis_title="الربح (SAR)",
                height=500,
                showlegend=False,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_profit, width="stretch")
            
        with tab2:
            st.markdown("#### هوامش الربح % لجميع المنتجات")
            # رسم بياني دائري لتوزيع الهوامش
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # توزيع فئات الهامش
                margin_categories = pd.cut(
                    priced_df["هامش الربح %"],
                    bins=[-float('inf'), 0, 10, 20, float('inf')],
                    labels=['خسارة (<0%)', 'منخفض (0-10%)', 'جيد (10-20%)', 'ممتاز (≥20%)']
                )
                margin_dist = margin_categories.value_counts()
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=margin_dist.index,
                    values=margin_dist.values,
                    hole=0.4,
                    marker=dict(colors=['#e74c3c', '#f39c12', '#3498db', '#2ecc71']),
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>العدد: %{value}<br>النسبة: %{percent}<extra></extra>'
                )])
                
                fig_pie.update_layout(
                    title="توزيع فئات الهامش",
                    height=400,
                    showlegend=True,
                )
                st.plotly_chart(fig_pie, width="stretch")
            
            with col_chart2:
                # رسم بياني شريطي لهوامش الربح
                sorted_df = priced_df.sort_values("هامش الربح %", ascending=False).head(15)
                
                fig_margin = go.Figure()
                fig_margin.add_trace(go.Bar(
                    x=sorted_df["الاسم"],
                    y=sorted_df["هامش الربح %"],
                    marker_color=sorted_df["هامش الربح %"].apply(
                        lambda x: '#2ecc71' if x >= 20 else '#3498db' if x >= 10 else '#f39c12' if x >= 0 else '#e74c3c'
                    ),
                    text=sorted_df["هامش الربح %"].round(1).astype(str) + '%',
                    textposition='outside',
                    name='هامش الربح %',
                    hovertemplate='<b>%{x}</b><br>الهامش: %{y:.1f}%<extra></extra>'
                ))
                
                fig_margin.update_layout(
                    title="أعلى هوامش ربح",
                    xaxis_title="المنتج",
                    yaxis_title="هامش الربح %",
                    height=400,
                    showlegend=False,
                )
                st.plotly_chart(fig_margin, width="stretch")
        
        with tab3:
            st.markdown("#### مقارنة الأسعار")
            # مقارنة السعر قبل وبعد الخصم
            comparison_df = priced_df.head(15)[["الاسم", "سعر قبل الخصم", "السعر النهائي بعد الخصم"]].copy()
            
            fig_price = go.Figure()
            fig_price.add_trace(go.Bar(
                name='سعر قبل الخصم',
                x=comparison_df["الاسم"],
                y=comparison_df["سعر قبل الخصم"],
                marker_color='#3498db',
                text=comparison_df["سعر قبل الخصم"].round(2),
                textposition='outside',
            ))
            fig_price.add_trace(go.Bar(
                name='السعر النهائي',
                x=comparison_df["الاسم"],
                y=comparison_df["السعر النهائي بعد الخصم"],
                marker_color='#2ecc71',
                text=comparison_df["السعر النهائي بعد الخصم"].round(2),
                textposition='outside',
            ))
            
            fig_price.update_layout(
                title="مقارنة الأسعار (قبل وبعد الخصم)",
                xaxis_title="المنتج",
                yaxis_title="السعر (SAR)",
                barmode='group',
                height=500,
                hovermode='x unified',
            )
            st.plotly_chart(fig_price, width="stretch")
        
        with tab4:
            st.markdown("#### تحليل التكاليف")
            # رسم بياني مكدس للتكاليف
            cost_analysis_df = priced_df.head(10)[
                ["الاسم", "التكلفة", "رسوم الشحن", "رسوم التحضير", "رسوم إدارية", "رسوم تسويق", "رسوم المنصة"]
            ].copy()
            
            fig_cost = go.Figure()
            
            fig_cost.add_trace(go.Bar(
                name='التكلفة الأساسية',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["التكلفة"],
                marker_color='#34495e'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم الشحن',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم الشحن"],
                marker_color='#9b59b6'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم التحضير',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم التحضير"],
                marker_color='#e67e22'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم إدارية',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم إدارية"],
                marker_color='#e74c3c'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم تسويق',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم تسويق"],
                marker_color='#f39c12'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم المنصة',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم المنصة"],
                marker_color='#16a085'
            ))
            
            fig_cost.update_layout(
                title="تفصيل التكاليف والرسوم (أول 10 منتجات)",
                xaxis_title="المنتج",
                yaxis_title="المبلغ (SAR)",
                barmode='stack',
                height=500,
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig_cost, width="stretch")

        st.markdown("---")

        # Data table with all columns in one table (like individual pricing page but as columns)
        st.markdown("### 📋 جدول التسعير التفصيلي")
        
        # Search and filter section
        col_search, col_filter1, col_filter2 = st.columns([2, 1, 1])
        
        with col_search:
            search_term = st.text_input("🔍 بحث بالاسم أو SKU", placeholder="ابحث...", key="search_pricing_table")
        
        with col_filter1:
            filter_type = st.multiselect(
                "فلتر حسب النوع",
                options=["منتج", "بكج"],
                default=["منتج", "بكج"],
                key="filter_type_pricing"
            )
        
        with col_filter2:
            filter_margin = st.selectbox(
                "فلتر حسب الهامش",
                options=["الكل", "ممتاز (≥20%)", "جيد (10-20%)", "منخفض (<10%)", "خسارة (<0%)"],
                key="filter_margin_pricing"
            )
        
        # Apply filters
        filtered_df = priced_df.copy()
        
        # Search filter
        if search_term:
            filtered_df = filtered_df[
                filtered_df["SKU"].str.contains(search_term, case=False, na=False) |
                filtered_df["الاسم"].str.contains(search_term, case=False, na=False)
            ]
        
        # Type filter
        if filter_type:
            filtered_df = filtered_df[filtered_df["النوع"].isin(filter_type)]
        
        # Margin filter
        if filter_margin == "ممتاز (≥20%)":
            filtered_df = filtered_df[filtered_df["هامش الربح %"] >= 20]
        elif filter_margin == "جيد (10-20%)":
            filtered_df = filtered_df[(filtered_df["هامش الربح %"] >= 10) & (filtered_df["هامش الربح %"] < 20)]
        elif filter_margin == "منخفض (<10%)":
            filtered_df = filtered_df[(filtered_df["هامش الربح %"] >= 0) & (filtered_df["هامش الربح %"] < 10)]
        elif filter_margin == "خسارة (<0%)":
            filtered_df = filtered_df[filtered_df["هامش الربح %"] < 0]
        
        st.info(f"📊 عرض {len(filtered_df)} من أصل {len(priced_df)} منتج/بكج")
        
        display_cols = [
            "SKU",
            "الاسم",
            "النوع",
            # الجزء الأول: التسعير
            "سعر قبل الخصم",
            "السعر النهائي بعد الخصم",
            # الجزء الثاني: تكلفة البضاعة المباعة
            "التكلفة",
            # الجزء الثالث: رسوم المنصة
            "رسوم الشحن",
            "رسوم التحضير",
            "رسوم إدارية",
            "رسوم تسويق",
            "رسوم المنصة",
            "رسوم إضافية مخصصة",
            "إجمالي الرسوم",
            # الجزء الرابع: صافي الربح
            "الربح",
            "هامش الربح %",
            "ROI %",
            "نقطة التعادل",
            "الهامش الآمن %",
            "تنبيهات",
        ]
        
        # تصفية الأعمدة الموجودة فقط
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        styled_table = TableFormatter.style_dataframe(
            filtered_df[available_cols], highlight_cols=["الربح", "هامش الربح %"], precision=2
        )
        st.dataframe(styled_table, width="stretch", hide_index=True, height=600)

        st.markdown("#### 📥 تنزيل النتائج")
        export_col1, export_col2 = st.columns(2)
        
        # Use saved values for filename
        saved_channel = st.session_state.get("last_pm_channel", selected_channel)
        
        with export_col1:
            csv_bytes = ExportManager.export_to_csv(priced_df, "pricing_results.csv")
            st.download_button(
                "تنزيل CSV",
                data=csv_bytes,
                file_name=f"pricing_results_{saved_channel}_{saved_target_margin}pct.csv",
                mime="text/csv",
                width="stretch",
            )
        with export_col2:
            excel_bytes = ExportManager.export_to_excel(priced_df, "pricing_results.xlsx", sheet_name="results")
            st.download_button(
                "تنزيل Excel",
                data=excel_bytes,
                file_name=f"pricing_results_{saved_channel}_{saved_target_margin}pct.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )

        if st.button("اعتماد النتائج في سجل المراجعة", type="primary", width="stretch", key="approve_bulk_pricing"):
            data_dir = os.path.join(os.path.dirname(__file__), "data")
            audit_records = []
            for _, row in priced_df.iterrows():
                audit_records.append(
                    {
                        "event_type": "bulk_pricing_approved",
                        "scope": "bulk_channel",
                        "sku": row.get("SKU", ""),
                        "item_name": row.get("الاسم", ""),
                        "item_type": row.get("النوع", ""),
                        "channel": saved_channel,
                        "cogs": row.get("التكلفة", 0),
                        "list_price": row.get("سعر قبل الخصم", 0),
                        "discount_rate": discount_rate,
                        "margin_pct": row.get("هامش الربح %", 0),
                        "profit": row.get("الربح", 0),
                        "breakeven_price": row.get("نقطة التعادل", 0),
                        "status": "approved",
                        "details": {
                            "target_margin_pct": saved_target_margin,
                            "final_price_after_discount": row.get("السعر النهائي بعد الخصم", 0),
                            "alerts": row.get("تنبيهات", ""),
                        },
                    }
                )
            audit_path = append_audit_events(data_dir, audit_records)
            st.success(f"تم اعتماد {len(audit_records)} نتيجة في سجل المراجعة: {audit_path}")

# Page: Saved History
elif st.session_state.page == "history":
    st.header("🗂️ السجلات المحفوظة")
    st.markdown("عرض وتحميل كل نتائج التسعير المحفوظة")

    import os

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    history_file = os.path.join(data_dir, "pricing_history.csv")
    audit_file = os.path.join(data_dir, "pricing_audit_log.csv")

    hist_df = None

    # Try to load from file first
    if os.path.exists(history_file):
        try:
            hist_df = pd.read_csv(history_file, encoding="utf-8-sig")
            st.success(f"✅ تم تحميل {len(hist_df)} سجلات من الملف")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

    # Fallback to session state
    if hist_df is None or hist_df.empty:
        if "saved_history_preview" in st.session_state:
            hist_df = st.session_state["saved_history_preview"]
            st.info(f"📋 عرض {len(hist_df)} سجلات من الذاكرة المؤقتة")

    if hist_df is not None and not hist_df.empty:
        st.download_button(
            "⬇️ تحميل السجلات CSV",
            data=hist_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="pricing_history.csv",
            mime="text/csv",
            width="stretch",
        )
        st.dataframe(hist_df, width="stretch", hide_index=True)
    else:
        st.info("لا توجد سجلات محفوظة بعد. احفظ نتيجة تسعير أولاً من صفحة التسعير.")
        st.caption(f"📁 مسار الملف المتوقع: {history_file}")

    st.markdown("---")
    st.subheader("سجل المراجعة التجاري")
    if os.path.exists(audit_file):
        try:
            audit_df = pd.read_csv(audit_file, encoding="utf-8-sig")
            st.download_button(
                "تحميل سجل المراجعة CSV",
                data=audit_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name="pricing_audit_log.csv",
                mime="text/csv",
                width="stretch",
            )
            st.dataframe(audit_df, width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"خطأ في قراءة سجل المراجعة: {e}")
    else:
        st.info("لا يوجد سجل مراجعة بعد. اعتمد أو احفظ نتيجة تسعير أولاً.")

# Footer
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #667085; font-size: 0.9rem;">
    <p style="margin: 0;">محرك تسعير صفوة - Safwa Pricing Engine</p>
    <p style="margin: 4px 0 0 0;">نظام تجاري لحساب COGS والتسعير الأمثل</p>
</div>
""",
    unsafe_allow_html=True,
)
