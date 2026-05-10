"""Visualization suggestion engine for SQL query results."""

import re
from typing import Any, Optional


# Patterns that suggest time/date columns
DATE_PATTERNS = re.compile(
    r"(date|time|year|month|week|day|quarter|period|created|updated|timestamp)",
    re.IGNORECASE,
)

# Patterns that suggest categorical columns
CATEGORY_PATTERNS = re.compile(
    r"(name|type|category|status|region|country|city|state|group|segment|label|brand|department|channel)",
    re.IGNORECASE,
)


def _is_numeric(value: Any) -> bool:
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.replace(",", ""))
            return True
        except (ValueError, AttributeError):
            return False
    return False


def _is_date_column(col_name: str) -> bool:
    return bool(DATE_PATTERNS.search(col_name))


def _is_category_column(col_name: str) -> bool:
    return bool(CATEGORY_PATTERNS.search(col_name))


def _classify_columns(
    columns: list[str], rows: list[dict],
) -> dict[str, list[str]]:
    """Classify columns into numeric, date, and categorical."""
    numeric_cols = []
    date_cols = []
    category_cols = []

    for col in columns:
        # Sample up to 10 non-null values
        sample_values = [r[col] for r in rows[:10] if r.get(col) is not None]
        if not sample_values:
            continue

        numeric_count = sum(1 for v in sample_values if _is_numeric(v))
        is_mostly_numeric = numeric_count > len(sample_values) * 0.7

        if is_mostly_numeric and not _is_date_column(col):
            numeric_cols.append(col)
        elif _is_date_column(col):
            date_cols.append(col)
        else:
            category_cols.append(col)

    return {"numeric": numeric_cols, "date": date_cols, "category": category_cols}


def _generate_title(chart_type: str, x_col: str, y_col: str) -> str:
    """Generate a human-readable chart title."""
    x_label = x_col.replace("_", " ").title()
    y_label = y_col.replace("_", " ").title()

    if chart_type == "bar":
        return f"{y_label} by {x_label}"
    elif chart_type == "line":
        return f"{y_label} over {x_label}"
    elif chart_type == "area":
        return f"{y_label} over {x_label}"
    elif chart_type == "pie":
        return f"{y_label} Distribution by {x_label}"
    elif chart_type == "scatter":
        return f"{x_label} vs {y_label}"
    return f"{y_label} by {x_label}"


def suggest_visualization(
    columns: list[str], rows: list[dict],
) -> Optional[dict]:
    """Analyze query result columns and rows, return a viz config or None.

    Returns:
        dict with: chart_type, title, x_column, y_column, reasoning
        or None if no suitable visualization.
    """
    if not columns or not rows:
        return None

    # Skip single-row results (summary stats shown as text)
    if len(rows) == 1:
        return None

    # Skip if too many columns with no clear pattern
    if len(columns) > 10:
        return None

    classified = _classify_columns(columns, rows)
    numeric_cols = classified["numeric"]
    date_cols = classified["date"]
    category_cols = classified["category"]

    # Not enough structure for a chart
    if not numeric_cols:
        return None

    num_rows = len(rows)

    # --- Line chart: date x + numeric y ---
    if date_cols and numeric_cols:
        x_col = date_cols[0]
        y_col = numeric_cols[0]

        # Check if data looks cumulative (monotonically increasing)
        values = []
        for r in rows:
            v = r.get(y_col)
            if v is not None and _is_numeric(v):
                values.append(float(str(v).replace(",", "")))

        is_cumulative = len(values) > 2 and all(
            values[i] <= values[i + 1] for i in range(len(values) - 1)
        )

        chart_type = "area" if is_cumulative else "line"
        return {
            "chart_type": chart_type,
            "title": _generate_title(chart_type, x_col, y_col),
            "x_column": x_col,
            "y_column": y_col,
            "reasoning": f"Time-series data with {x_col} as temporal axis",
        }

    # --- Bar chart: categorical x + numeric y, < 20 categories ---
    if category_cols and numeric_cols and num_rows <= 20:
        x_col = category_cols[0]
        y_col = numeric_cols[0]

        # Check uniqueness of categories
        unique_cats = len(set(str(r.get(x_col, "")) for r in rows))

        if unique_cats <= 20:
            # Pie chart: < 8 categories with single numeric value
            if unique_cats <= 8 and len(numeric_cols) == 1:
                return {
                    "chart_type": "pie",
                    "title": _generate_title("pie", x_col, y_col),
                    "x_column": x_col,
                    "y_column": y_col,
                    "reasoning": f"Small number of categories ({unique_cats}) with single metric",
                }

            return {
                "chart_type": "bar",
                "title": _generate_title("bar", x_col, y_col),
                "x_column": x_col,
                "y_column": y_col,
                "reasoning": f"Categorical data with {unique_cats} distinct values",
            }

    # --- Scatter plot: two numeric columns ---
    if len(numeric_cols) >= 2 and not category_cols and not date_cols:
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]
        return {
            "chart_type": "scatter",
            "title": _generate_title("scatter", x_col, y_col),
            "x_column": x_col,
            "y_column": y_col,
            "reasoning": "Two numeric columns suggest correlation analysis",
        }

    # --- Fallback bar chart for category + numeric with more rows ---
    if category_cols and numeric_cols:
        x_col = category_cols[0]
        y_col = numeric_cols[0]
        unique_cats = len(set(str(r.get(x_col, "")) for r in rows))
        if unique_cats <= 20:
            return {
                "chart_type": "bar",
                "title": _generate_title("bar", x_col, y_col),
                "x_column": x_col,
                "y_column": y_col,
                "reasoning": f"Categorical breakdown with {unique_cats} groups",
            }

    # --- Fallback: first non-numeric + first numeric ---
    non_numeric = [c for c in columns if c not in numeric_cols]
    if non_numeric and numeric_cols and num_rows <= 20:
        x_col = non_numeric[0]
        y_col = numeric_cols[0]
        return {
            "chart_type": "bar",
            "title": _generate_title("bar", x_col, y_col),
            "x_column": x_col,
            "y_column": y_col,
            "reasoning": "Default bar chart for mixed column types",
        }

    return None
