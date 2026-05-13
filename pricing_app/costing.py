from __future__ import annotations

from typing import Dict, Mapping, Optional, Set

import pandas as pd


def _direct_cost(sku: str, materials: Mapping) -> Optional[float]:
    material = materials.get(sku)
    if material is None:
        return None

    cost = getattr(material, "cost_per_unit", None)
    if cost is None:
        return None

    try:
        cost = float(cost)
    except (TypeError, ValueError):
        return None

    return cost if cost > 0 else None


def _has_real_components(sku: str, components: Mapping[str, float]) -> bool:
    for component_sku, quantity in (components or {}).items():
        component_sku = str(component_sku).strip()
        if not component_sku or component_sku == sku:
            continue
        try:
            quantity = float(quantity or 0)
        except (TypeError, ValueError):
            quantity = 0.0
        if quantity > 0:
            return True
    return False


def _format_quantity(quantity: float) -> str:
    try:
        quantity = float(quantity or 0)
    except (TypeError, ValueError):
        quantity = 0.0
    if quantity.is_integer():
        return str(int(quantity))
    return f"{quantity:.4f}".rstrip("0").rstrip(".")


def _format_component_label(sku: str, names_by_sku: Optional[Mapping[str, str]] = None) -> str:
    name = str((names_by_sku or {}).get(sku, "") or "").strip()
    if name and name != sku:
        return f"{sku} - {name}"
    return sku


def resolve_component_cost(
    sku: str,
    materials: Mapping,
    product_recipes: Mapping[str, Mapping[str, float]],
    package_compositions: Mapping[str, Mapping[str, float]],
    *,
    prefer_direct_cost: bool = True,
    _visiting: Optional[Set[str]] = None,
) -> float:
    """Resolve SKU cost using Zoho/accounting priority.

    Priority:
    1. Product/composite BOM recursively when the SKU has real components.
    2. Package BOM recursively, including packages that contain other packages.
    3. Direct cost from materials as a fallback for raw/standalone SKUs.
    """

    sku = str(sku).strip()
    if not sku:
        return 0.0

    product_components = product_recipes.get(sku, {}) if product_recipes else {}
    package_components = package_compositions.get(sku, {}) if package_compositions else {}
    has_product_bom = _has_real_components(sku, product_components)
    has_package_bom = _has_real_components(sku, package_components)

    direct = _direct_cost(sku, materials)
    if prefer_direct_cost and direct is not None and not has_product_bom and not has_package_bom:
        return direct

    if _visiting is None:
        _visiting = set()
    if sku in _visiting:
        return direct or 0.0

    _visiting.add(sku)
    try:
        if product_components:
            total = 0.0
            for component_sku, quantity in product_components.items():
                component_sku = str(component_sku).strip()
                if component_sku == sku:
                    component_cost = _direct_cost(sku, materials) or 0.0
                else:
                    component_cost = resolve_component_cost(
                        component_sku,
                        materials,
                        product_recipes,
                        package_compositions,
                        prefer_direct_cost=True,
                        _visiting=_visiting,
                    )
                total += component_cost * float(quantity or 0)
            if total > 0:
                return total

        if package_components:
            total = 0.0
            for component_sku, quantity in package_components.items():
                component_sku = str(component_sku).strip()
                if component_sku == sku:
                    component_cost = _direct_cost(sku, materials) or 0.0
                else:
                    component_cost = resolve_component_cost(
                        component_sku,
                        materials,
                        product_recipes,
                        package_compositions,
                        prefer_direct_cost=True,
                        _visiting=_visiting,
                    )
                total += component_cost * float(quantity or 0)
            if total > 0:
                return total

        return direct or 0.0
    finally:
        _visiting.remove(sku)


def build_cost_details(
    sku: str,
    materials: Mapping,
    product_recipes: Mapping[str, Mapping[str, float]],
    package_compositions: Mapping[str, Mapping[str, float]],
    *,
    names_by_sku: Optional[Mapping[str, str]] = None,
    _visiting: Optional[Set[str]] = None,
) -> str:
    sku = str(sku).strip()
    if not sku:
        return ""

    product_components = product_recipes.get(sku, {}) if product_recipes else {}
    package_components = package_compositions.get(sku, {}) if package_compositions else {}
    has_product_bom = _has_real_components(sku, product_components)
    has_package_bom = _has_real_components(sku, package_components)
    components = product_components if has_product_bom else package_components if has_package_bom else {}

    direct = _direct_cost(sku, materials)
    if not components:
        if direct is None:
            return ""
        return f"{_format_component_label(sku, names_by_sku)}: direct cost = {direct:.2f}"

    if _visiting is None:
        _visiting = set()
    if sku in _visiting:
        return f"{_format_component_label(sku, names_by_sku)}: circular reference"

    _visiting.add(sku)
    try:
        parts = []
        total = 0.0
        for component_sku, quantity in components.items():
            component_sku = str(component_sku).strip()
            try:
                quantity_value = float(quantity or 0)
            except (TypeError, ValueError):
                quantity_value = 0.0
            if not component_sku or quantity_value <= 0:
                continue

            if component_sku == sku:
                component_cost = _direct_cost(sku, materials) or 0.0
            else:
                component_cost = resolve_component_cost(
                    component_sku,
                    materials,
                    product_recipes,
                    package_compositions,
                    prefer_direct_cost=True,
                    _visiting=_visiting,
                )

            line_total = component_cost * quantity_value
            total += line_total
            parts.append(
                f"{_format_component_label(component_sku, names_by_sku)}: "
                f"{_format_quantity(quantity_value)} x {component_cost:.2f} = {line_total:.2f}"
            )

        if not parts:
            return ""
        parts.append(f"Total = {total:.2f}")
        return " | ".join(parts)
    finally:
        _visiting.remove(sku)


def _recipes_from_products_df(products_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    recipes: Dict[str, Dict[str, float]] = {}
    if products_df is None or products_df.empty:
        return recipes

    if {"Product_SKU", "Material_Code", "Quantity"}.issubset(products_df.columns):
        for _, row in products_df.iterrows():
            product_sku = str(row.get("Product_SKU", "")).strip()
            material_sku = str(row.get("Material_Code", "")).strip()
            if not product_sku or not material_sku:
                continue
            recipes.setdefault(product_sku, {})
            recipes[product_sku][material_sku] = recipes[product_sku].get(material_sku, 0.0) + float(row.get("Quantity", 0) or 0)
        return recipes

    if {"Product_SKU", "BOM"}.issubset(products_df.columns):
        for _, row in products_df.iterrows():
            product_sku = str(row.get("Product_SKU", "")).strip()
            bom = str(row.get("BOM", "")).strip()
            if not product_sku or not bom:
                continue
            recipes.setdefault(product_sku, {})
            for component in bom.split(";"):
                if ":" not in component:
                    continue
                material_sku, quantity = component.split(":", 1)
                material_sku = material_sku.strip()
                recipes[product_sku][material_sku] = recipes[product_sku].get(material_sku, 0.0) + float(quantity or 0)

    return recipes


def _compositions_from_packages_df(packages_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    compositions: Dict[str, Dict[str, float]] = {}
    if packages_df is None or packages_df.empty:
        return compositions

    if {"Package_SKU", "Product_SKU", "Quantity"}.issubset(packages_df.columns):
        for _, row in packages_df.iterrows():
            package_sku = str(row.get("Package_SKU", "")).strip()
            component_sku = str(row.get("Product_SKU", "")).strip()
            if not package_sku or not component_sku:
                continue
            compositions.setdefault(package_sku, {})
            compositions[package_sku][component_sku] = compositions[package_sku].get(component_sku, 0.0) + float(row.get("Quantity", 0) or 0)
        return compositions

    if {"Package_SKU", "Components"}.issubset(packages_df.columns):
        for _, row in packages_df.iterrows():
            package_sku = str(row.get("Package_SKU", "")).strip()
            components = str(row.get("Components", "")).strip()
            if not package_sku or not components:
                continue
            compositions.setdefault(package_sku, {})
            for component in components.split(";"):
                parts = component.split(":")
                if len(parts) < 2:
                    continue
                component_sku = parts[0].strip()
                compositions[package_sku][component_sku] = compositions[package_sku].get(component_sku, 0.0) + float(parts[1] or 0)

    return compositions


def compute_product_costs(products_df, materials: Dict, package_compositions: Optional[Dict] = None) -> Dict[str, float]:
    if isinstance(products_df, dict):
        product_recipes = products_df
    else:
        product_recipes = _recipes_from_products_df(products_df)

    package_compositions = package_compositions or {}
    return {
        sku: resolve_component_cost(sku, materials, product_recipes, package_compositions)
        for sku in product_recipes
    }


def compute_package_costs(
    packages_df,
    product_costs_or_recipes: Dict[str, float] | Dict[str, Dict[str, float]],
    materials: Dict,
    max_depth: int = 10,
) -> Dict[str, float]:
    del max_depth

    if isinstance(packages_df, dict):
        package_compositions = packages_df
    else:
        package_compositions = _compositions_from_packages_df(packages_df)

    if product_costs_or_recipes and all(isinstance(value, dict) for value in product_costs_or_recipes.values()):
        product_recipes = product_costs_or_recipes
        return {
            sku: resolve_component_cost(sku, materials, product_recipes, package_compositions)
            for sku in package_compositions
        }
    else:
        product_recipes = {}
        product_costs = {
            str(sku).strip(): float(cost or 0)
            for sku, cost in (product_costs_or_recipes or {}).items()
        }

    def resolve_package_cost(sku: str, visiting: Optional[Set[str]] = None) -> float:
        components = package_compositions.get(sku, {})
        has_package_bom = _has_real_components(sku, components)

        if sku in product_costs and not has_package_bom:
            return product_costs[sku]

        direct = _direct_cost(sku, materials)
        if direct is not None and not has_package_bom:
            return direct

        if visiting is None:
            visiting = set()
        if sku in visiting:
            return 0.0

        visiting.add(sku)
        try:
            total = 0.0
            for component_sku, quantity in components.items():
                component_sku = str(component_sku).strip()
                if component_sku == sku:
                    component_cost = product_costs.get(sku, direct or 0.0)
                elif component_sku in product_costs:
                    component_cost = product_costs[component_sku]
                elif component_sku in package_compositions:
                    component_cost = resolve_package_cost(component_sku, visiting)
                else:
                    component_cost = _direct_cost(component_sku, materials) or 0.0
                total += component_cost * float(quantity or 0)
            return total
        finally:
            visiting.remove(sku)

    return {sku: resolve_package_cost(sku) for sku in package_compositions}
