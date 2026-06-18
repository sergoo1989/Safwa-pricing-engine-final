from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd

from .models import Material


ZOHO_ITEMS_FILE = "zoho_items.csv"
ZOHO_COMPOSITES_FILE = "zoho_composite_items.csv"
ZOHO_VALUATION_FILE = "zoho_inventory_valuation.csv"
VALUATION_REQUIRED_COLUMNS = ("Item ID", "Item Name", "Stock On Hand", "Inventory Asset Value")


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=object)

    for encoding in ("utf-8-sig", "utf-8", "cp1256"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def parse_number(value, default: float = 0.0) -> float:
    if value is None or pd.isna(value):
        return default

    text = str(value).strip()
    if not text:
        return default

    text = (
        text.replace("SAR", "")
        .replace("ر.س", "")
        .replace(",", "")
        .replace("\u00a0", "")
        .strip()
    )

    try:
        return float(text)
    except ValueError:
        return default


def _clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _unique_column_names(values: Iterable) -> list[str]:
    names: list[str] = []
    seen: Dict[str, int] = {}

    for index, value in enumerate(values):
        base_name = _clean_text(value) or f"Unnamed: {index}"
        if base_name in seen:
            seen[base_name] += 1
            names.append(f"{base_name}.{seen[base_name]}")
        else:
            seen[base_name] = 0
            names.append(base_name)

    return names


def _ensure_valuation_sku_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "sku" not in df.columns:
        for column in df.columns:
            if str(column).strip().lower() == "sku":
                df["sku"] = df[column]
                break
    return df


def _normalise_valuation_frame(valuation_df: pd.DataFrame) -> pd.DataFrame:
    """Support both edited valuation sheets and raw Zoho xlsx exports.

    Raw Zoho Inventory Valuation Summary files include a report title above the
    actual table. When pandas reads that file normally, the title becomes the
    dataframe header and the real column names appear in the first data row.
    """

    valuation_df = _ensure_valuation_sku_column(_normalise_columns(valuation_df))
    required_set = set(VALUATION_REQUIRED_COLUMNS)
    if required_set.issubset(valuation_df.columns) and "sku" in valuation_df.columns:
        return valuation_df

    for row_position, (_, row) in enumerate(valuation_df.iterrows()):
        values = [_clean_text(value) for value in row.tolist()]
        value_set = set(values)
        has_required_columns = required_set.issubset(value_set)
        has_sku_column = any(value.lower() == "sku" for value in values)
        if not (has_required_columns and has_sku_column):
            continue

        promoted_df = valuation_df.iloc[row_position + 1 :].copy()
        promoted_df.columns = _unique_column_names(values)
        promoted_df = _ensure_valuation_sku_column(_normalise_columns(promoted_df))
        promoted_df = promoted_df.dropna(how="all").reset_index(drop=True)
        return promoted_df

    return valuation_df


def _first_existing_path(data_dir: Path, candidates: Iterable[str]) -> Optional[Path]:
    for candidate in candidates:
        path = data_dir / candidate
        if path.exists():
            return path
    return None


def find_zoho_files(data_dir: str | Path) -> Optional[Tuple[Path, Path, Path]]:
    data_path = Path(data_dir)
    items_path = _first_existing_path(
        data_path,
        (
            ZOHO_ITEMS_FILE,
            "Item.csv",
            "Items.csv",
            "Item (5).csv",
        ),
    )
    composites_path = _first_existing_path(
        data_path,
        (
            ZOHO_COMPOSITES_FILE,
            "Composite_Item.csv",
            "Composite Items.csv",
            "Composite_Item (1).csv",
        ),
    )
    valuation_path = _first_existing_path(
        data_path,
        (
            ZOHO_VALUATION_FILE,
            "Inventory Valuation Summary.csv",
            "Inventory Valuation Summary.xlsx",
            "Inventory Valuation Summary (1).csv",
            "Inventory Valuation Summary (1).xlsx",
        ),
    )

    if items_path and composites_path and valuation_path:
        return items_path, composites_path, valuation_path
    return None


def has_zoho_files(data_dir: str | Path) -> bool:
    return find_zoho_files(data_dir) is not None


def _require_columns(df: pd.DataFrame, required: Iterable[str], source_name: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{source_name} is missing required columns: {', '.join(missing)}")


def validate_zoho_export_frames(
    items_df: pd.DataFrame,
    composites_df: pd.DataFrame,
    valuation_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return a validation table for uploaded Zoho exports."""

    valuation_df = _normalise_valuation_frame(valuation_df)
    checks = [
        ("Item", _normalise_columns(items_df), ("Item ID", "Item Name", "SKU", "Purchase Rate", "Category Name", "Status")),
        (
            "Composite Item",
            _normalise_columns(composites_df),
            ("Composite Item ID", "Composite Item Name", "SKU", "Mapped Item SKU", "Mapped Quantity", "Combo Type"),
        ),
        (
            "Inventory Valuation Summary",
            _normalise_columns(valuation_df),
            VALUATION_REQUIRED_COLUMNS,
        ),
    ]

    rows = []
    for source_name, df, required in checks:
        missing = [col for col in required if col not in df.columns]
        if source_name == "Inventory Valuation Summary" and not ({"sku", "SKU"} & set(df.columns)):
            missing.append("sku")

        rows.append(
            {
                "source": source_name,
                "status": "valid" if not missing else "invalid",
                "rows": len(df),
                "missing_columns": ", ".join(missing),
            }
        )

    return pd.DataFrame(rows)


def _build_valuation_costs(valuation_df: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, Dict]]:
    costs: Dict[str, float] = {}
    meta: Dict[str, Dict] = {}

    for _, row in valuation_df.iterrows():
        sku = _clean_text(row.get("sku") or row.get("SKU"))
        if not sku:
            continue

        stock_on_hand = parse_number(row.get("Stock On Hand"))
        asset_value = parse_number(row.get("Inventory Asset Value"))
        if stock_on_hand > 0 and asset_value > 0:
            costs[sku] = asset_value / stock_on_hand
            meta[sku] = {
                "cost_source": "valuation_average",
                "stock_on_hand": stock_on_hand,
                "inventory_asset_value": asset_value,
            }

    return costs, meta


def _is_active(row) -> bool:
    return _clean_text(row.get("Status")).lower() in {"", "active"}


def _is_true(value) -> bool:
    return _clean_text(value).lower() == "true"


def _is_raw_material(row) -> bool:
    parent_category = _clean_text(row.get("Parent Category"))
    category = _clean_text(row.get("Category Name"))
    return "مواد خام" in parent_category or "مواد خام" in category


def _classify_composite(row) -> str:
    combo_type = _clean_text(row.get("Combo Type")).lower()
    category = _clean_text(row.get("Category Name"))
    if combo_type == "kit" or category == "العروض":
        return "package"
    return "product"


def load_zoho_cost_data(
    data_dir: str | Path,
    items_path: str | Path | None = None,
    composites_path: str | Path | None = None,
    valuation_path: str | Path | None = None,
):
    """Load Zoho exports and return the same structures used by the app.

    Cost priority:
    1. Inventory valuation weighted average: Inventory Asset Value / Stock On Hand.
    2. Item Purchase Rate from Zoho Items.
    3. Recursive BOM composition for composite items with no direct cost.
    """

    data_path = Path(data_dir)
    if items_path and composites_path and valuation_path:
        paths = (Path(items_path), Path(composites_path), Path(valuation_path))
    else:
        found = find_zoho_files(data_path)
        if found is None:
            raise FileNotFoundError("Zoho Item, Composite Item, and Inventory Valuation files were not found.")
        paths = found

    items_df = _read_table(paths[0])
    composites_df = _read_table(paths[1])
    valuation_df = _read_table(paths[2])

    return load_zoho_cost_data_from_frames(items_df, composites_df, valuation_df)


def load_zoho_cost_data_from_frames(
    items_df: pd.DataFrame,
    composites_df: pd.DataFrame,
    valuation_df: pd.DataFrame,
):
    """Load Zoho cost structures from uploaded DataFrames without saving files."""

    items_df = _normalise_columns(items_df)
    composites_df = _normalise_columns(composites_df)
    valuation_df = _normalise_valuation_frame(valuation_df)

    _require_columns(
        items_df,
        ("Item ID", "Item Name", "SKU", "Purchase Rate", "Category Name", "Status"),
        "Zoho Items",
    )
    _require_columns(
        composites_df,
        ("Composite Item ID", "Composite Item Name", "SKU", "Mapped Item SKU", "Mapped Quantity", "Combo Type"),
        "Zoho Composite Items",
    )
    _require_columns(
        valuation_df,
        (*VALUATION_REQUIRED_COLUMNS, "sku"),
        "Zoho Inventory Valuation",
    )

    item_rows = {
        _clean_text(row.get("SKU")): row
        for _, row in items_df.iterrows()
        if _clean_text(row.get("SKU")) and _is_active(row)
    }

    valuation_costs, cost_meta = _build_valuation_costs(valuation_df)

    direct_costs: Dict[str, float] = {}
    direct_sources: Dict[str, str] = {}
    for sku, row in item_rows.items():
        if sku in valuation_costs:
            direct_costs[sku] = valuation_costs[sku]
            direct_sources[sku] = "valuation_average"
            continue

        purchase_rate = parse_number(row.get("Purchase Rate"))
        if purchase_rate > 0:
            direct_costs[sku] = purchase_rate
            direct_sources[sku] = "purchase_rate"
            cost_meta.setdefault(sku, {})["cost_source"] = "purchase_rate"

    materials: Dict[str, Material] = {}
    for sku, cost in direct_costs.items():
        row = item_rows.get(sku, {})
        materials[sku] = Material(
            material_sku=sku,
            material_name=_clean_text(row.get("Item Name") or row.get("Product Name")) or sku,
            category=_clean_text(row.get("Category Name")) or "Zoho",
            unit=_clean_text(row.get("Usage unit") or row.get("Unit Name")) or "pcs",
            cost_per_unit=cost,
        )

    product_recipes: Dict[str, Dict[str, float]] = {}
    package_compositions: Dict[str, Dict[str, float]] = {}
    product_summary_rows = []
    package_summary_rows = []
    seen_product_skus = set()
    seen_package_skus = set()

    for _, row in composites_df.iterrows():
        if not _is_active(row):
            continue

        parent_sku = _clean_text(row.get("SKU"))
        child_sku = _clean_text(row.get("Mapped Item SKU"))
        quantity = parse_number(row.get("Mapped Quantity"))
        if not parent_sku or not child_sku or quantity <= 0:
            continue

        item_type = _classify_composite(row)
        target = product_recipes if item_type == "product" else package_compositions
        target.setdefault(parent_sku, {})
        target[parent_sku][child_sku] = target[parent_sku].get(child_sku, 0.0) + quantity

        summary_row = {
            "Product_SKU" if item_type == "product" else "Package_SKU": parent_sku,
            "Product_Name" if item_type == "product" else "Package_Name": _clean_text(row.get("Composite Item Name")) or parent_sku,
            "Category": _clean_text(row.get("Category Name")),
            "Combo_Type": _clean_text(row.get("Combo Type")),
        }

        if item_type == "product" and parent_sku not in seen_product_skus:
            product_summary_rows.append(summary_row)
            seen_product_skus.add(parent_sku)
        elif item_type == "package" and parent_sku not in seen_package_skus:
            package_summary_rows.append(summary_row)
            seen_package_skus.add(parent_sku)

    # Standalone sellable stock items are priced from their direct Zoho cost.
    composite_skus = set(product_recipes) | set(package_compositions)
    for sku, row in item_rows.items():
        if sku in composite_skus:
            continue
        if not _is_true(row.get("Sellable")):
            continue
        if _is_raw_material(row):
            continue
        if sku not in direct_costs:
            continue

        product_recipes[sku] = {sku: 1.0}
        product_summary_rows.append(
            {
                "Product_SKU": sku,
                "Product_Name": _clean_text(row.get("Item Name") or row.get("Product Name")) or sku,
                "Category": _clean_text(row.get("Category Name")),
                "Combo_Type": "Standalone",
            }
        )

    products_summary = pd.DataFrame(product_summary_rows)
    if products_summary.empty:
        products_summary = pd.DataFrame(columns=["Product_SKU", "Product_Name", "Category", "Combo_Type"])

    packages_summary = pd.DataFrame(package_summary_rows)
    if packages_summary.empty:
        packages_summary = pd.DataFrame(columns=["Package_SKU", "Package_Name", "Category", "Combo_Type"])

    return materials, product_recipes, products_summary, package_compositions, packages_summary


def save_zoho_exports(
    data_dir: str | Path,
    items_df: pd.DataFrame,
    composites_df: pd.DataFrame,
    valuation_df: pd.DataFrame,
) -> Tuple[Path, Path, Path]:
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    items_path = data_path / ZOHO_ITEMS_FILE
    composites_path = data_path / ZOHO_COMPOSITES_FILE
    valuation_path = data_path / ZOHO_VALUATION_FILE

    items_df.to_csv(items_path, index=False, encoding="utf-8-sig")
    composites_df.to_csv(composites_path, index=False, encoding="utf-8-sig")
    valuation_df.to_csv(valuation_path, index=False, encoding="utf-8-sig")

    return items_path, composites_path, valuation_path
