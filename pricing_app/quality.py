from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Mapping, Set

import pandas as pd

from .costing import resolve_component_cost


@dataclass
class DataQualityReport:
    status: str
    checked_at: str
    total_materials: int
    total_products: int
    total_packages: int
    issue_count: int
    critical_count: int
    warning_count: int
    issues: pd.DataFrame

    @property
    def is_ready(self) -> bool:
        return self.critical_count == 0


def _issue(severity: str, area: str, sku: str, message: str, action: str) -> Dict[str, str]:
    return {
        "severity": severity,
        "area": area,
        "sku": str(sku),
        "message": message,
        "recommended_action": action,
    }


def _component_exists(
    sku: str,
    materials: Mapping,
    product_recipes: Mapping[str, Mapping[str, float]],
    package_compositions: Mapping[str, Mapping[str, float]],
) -> bool:
    return sku in materials or sku in product_recipes or sku in package_compositions


def _detect_package_cycles(package_compositions: Mapping[str, Mapping[str, float]]) -> Set[str]:
    cyclic: Set[str] = set()
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(sku: str, path: Set[str]) -> None:
        if sku in visiting:
            cyclic.update(path | {sku})
            return
        if sku in visited:
            return

        visiting.add(sku)
        for child_sku in package_compositions.get(sku, {}):
            child_sku = str(child_sku).strip()
            if child_sku in package_compositions:
                visit(child_sku, path | {sku})
        visiting.remove(sku)
        visited.add(sku)

    for package_sku in package_compositions:
        visit(str(package_sku).strip(), set())

    return cyclic


def _missing_summary_rows(summary: pd.DataFrame, key_col: str, known_skus: Iterable[str]) -> Set[str]:
    if summary is None or summary.empty or key_col not in summary.columns:
        return set(known_skus)
    summary_skus = {str(value).strip() for value in summary[key_col].dropna()}
    return {str(sku).strip() for sku in known_skus if str(sku).strip() not in summary_skus}


def validate_commercial_readiness(
    materials: Mapping,
    product_recipes: Mapping[str, Mapping[str, float]],
    products_summary: pd.DataFrame,
    package_compositions: Mapping[str, Mapping[str, float]],
    packages_summary: pd.DataFrame,
) -> DataQualityReport:
    issues = []

    if not materials:
        issues.append(
            _issue(
                "critical",
                "Zoho Items",
                "",
                "لا توجد بنود بتكلفة صالحة.",
                "ارفع ملف Item و Inventory Valuation من Zoho وتأكد من وجود Purchase Rate أو متوسط مخزون.",
            )
        )

    if not product_recipes:
        issues.append(
            _issue(
                "critical",
                "Zoho Composite Items",
                "",
                "لا توجد منتجات قابلة للتسعير.",
                "ارفع ملف Composite Item وتأكد من وجود Mapped Item SKU و Mapped Quantity.",
            )
        )

    for sku, material in materials.items():
        cost = getattr(material, "cost_per_unit", 0) or 0
        try:
            cost = float(cost)
        except (TypeError, ValueError):
            cost = 0
        if cost <= 0:
            issues.append(
                _issue(
                    "critical",
                    "Cost",
                    sku,
                    "البند لديه تكلفة صفرية أو غير صالحة.",
                    "راجع متوسط تقييم المخزون أو Purchase Rate في Zoho.",
                )
            )

    for product_sku, components in product_recipes.items():
        if not components:
            issues.append(
                _issue(
                    "critical",
                    "Product BOM",
                    product_sku,
                    "المنتج بدون مكونات.",
                    "راجع مكونات المنتج في Composite Item.",
                )
            )
            continue

        for component_sku, quantity in components.items():
            component_sku = str(component_sku).strip()
            quantity = float(quantity or 0)
            if quantity <= 0:
                issues.append(
                    _issue(
                        "critical",
                        "Product BOM",
                        product_sku,
                        f"كمية غير صالحة للمكون {component_sku}.",
                        "راجع Mapped Quantity في ملف Composite Item.",
                    )
                )
            if not _component_exists(component_sku, materials, product_recipes, package_compositions):
                issues.append(
                    _issue(
                        "critical",
                        "Product BOM",
                        product_sku,
                        f"المكون {component_sku} غير موجود في بيانات Zoho المحملة.",
                        "راجع SKU المكون أو أعد تصدير ملفات Zoho.",
                    )
                )

        total_cost = resolve_component_cost(product_sku, materials, product_recipes, package_compositions)
        if total_cost <= 0:
            issues.append(
                _issue(
                    "critical",
                    "Cost",
                    product_sku,
                    "تكلفة المنتج النهائية صفرية.",
                    "راجع تكاليف المكونات ومتوسط تقييم المخزون.",
                )
            )

    for package_sku, components in package_compositions.items():
        if not components:
            issues.append(
                _issue(
                    "critical",
                    "Package BOM",
                    package_sku,
                    "البكج بدون مكونات.",
                    "راجع مكونات البكج في Composite Item.",
                )
            )
            continue

        for component_sku, quantity in components.items():
            component_sku = str(component_sku).strip()
            quantity = float(quantity or 0)
            if quantity <= 0:
                issues.append(
                    _issue(
                        "critical",
                        "Package BOM",
                        package_sku,
                        f"كمية غير صالحة للمكون {component_sku}.",
                        "راجع Mapped Quantity في ملف Composite Item.",
                    )
                )
            if not _component_exists(component_sku, materials, product_recipes, package_compositions):
                issues.append(
                    _issue(
                        "critical",
                        "Package BOM",
                        package_sku,
                        f"المكون {component_sku} غير موجود في بيانات Zoho المحملة.",
                        "راجع SKU المكون أو أعد تصدير ملفات Zoho.",
                    )
                )

        total_cost = resolve_component_cost(package_sku, materials, product_recipes, package_compositions)
        if total_cost <= 0:
            issues.append(
                _issue(
                    "critical",
                    "Cost",
                    package_sku,
                    "تكلفة البكج النهائية صفرية.",
                    "راجع تكاليف المكونات ومتوسط تقييم المخزون.",
                )
            )

    for package_sku in _detect_package_cycles(package_compositions):
        issues.append(
            _issue(
                "critical",
                "Package BOM",
                package_sku,
                "يوجد اعتماد دائري بين البكجات.",
                "راجع مكونات البكجات واحذف الحلقة قبل التسعير.",
            )
        )

    for sku in _missing_summary_rows(products_summary, "Product_SKU", product_recipes):
        issues.append(
            _issue(
                "warning",
                "Product Summary",
                sku,
                "المنتج موجود في الوصفة لكن غير موجود في ملخص المنتجات.",
                "راجع اسم المنتج في Composite Item.",
            )
        )

    for sku in _missing_summary_rows(packages_summary, "Package_SKU", package_compositions):
        issues.append(
            _issue(
                "warning",
                "Package Summary",
                sku,
                "البكج موجود في المكونات لكن غير موجود في ملخص البكجات.",
                "راجع اسم البكج في Composite Item.",
            )
        )

    issues_df = pd.DataFrame(
        issues,
        columns=["severity", "area", "sku", "message", "recommended_action"],
    )
    critical_count = int((issues_df["severity"] == "critical").sum()) if not issues_df.empty else 0
    warning_count = int((issues_df["severity"] == "warning").sum()) if not issues_df.empty else 0
    status = "جاهز للتشغيل التجاري" if critical_count == 0 else "يحتاج مراجعة قبل التشغيل"

    return DataQualityReport(
        status=status,
        checked_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_materials=len(materials),
        total_products=len(product_recipes),
        total_packages=len(package_compositions),
        issue_count=len(issues_df),
        critical_count=critical_count,
        warning_count=warning_count,
        issues=issues_df,
    )
