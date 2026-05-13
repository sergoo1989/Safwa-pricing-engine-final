from __future__ import annotations

import argparse
from pathlib import Path

from pricing_app.salla_prices import (
    SALLA_OUTPUT_FILE_NAME,
    add_customer_final_price_columns,
    load_salla_export,
)


def build_output_path(input_path: Path, output_arg: str | None) -> Path:
    output_path = Path(output_arg) if output_arg else input_path.with_name(SALLA_OUTPUT_FILE_NAME)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    return output_path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add customer-visible VAT-inclusive final price columns to a Salla prices export."
    )
    parser.add_argument("input_file", help="Path to the Salla Excel or CSV export file.")
    parser.add_argument(
        "--output",
        help=f"Optional output Excel path. Defaults to {SALLA_OUTPUT_FILE_NAME} next to the input file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_file).expanduser().resolve()

    if not input_path.exists():
        print(f"ERROR: Input file does not exist: {input_path}")
        return 1
    if not input_path.is_file():
        print(f"ERROR: Input path is not a file: {input_path}")
        return 1

    output_path = build_output_path(input_path, args.output)
    if output_path == input_path:
        print("ERROR: Output path cannot be the same as the input file.")
        return 1

    try:
        df = load_salla_export(input_path)
        result, summary = add_customer_final_price_columns(df)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_excel(output_path, index=False)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Saved file: {output_path}")
    print("Summary:")
    print(f"  total rows: {summary['total_rows']}")
    print(f"  rows using discount price: {summary['discount_rows']}")
    print(f"  rows using regular price: {summary['regular_rows']}")
    print(f"  rows with missing final price: {summary['missing_final_price_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
