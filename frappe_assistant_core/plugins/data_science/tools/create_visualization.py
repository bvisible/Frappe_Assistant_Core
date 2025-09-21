# Frappe Assistant Core - AI Assistant integration for Frappe Framework
# Copyright (C) 2025 Paul Clinton
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Create Visualization Tool for Data Science Plugin.
Generates charts and visualizations using matplotlib, plotly, and other libraries.
"""

import base64
import io
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import pandas as pd

import frappe
from frappe import _

from frappe_assistant_core.core.base_tool import BaseTool


class CreateVisualization(BaseTool):
    """
    Tool for creating data visualizations with scientific charting libraries.

    Provides capabilities for:
    - Multiple chart types (bar, line, pie, scatter, histogram, etc.)
    - Data processing and aggregation
    - Export to various formats (PNG, SVG, HTML, JSON)
    - Professional styling and theming
    """

    def __init__(self):
        super().__init__()
        self.name = "create_visualization"
        self.description = "Create data visualizations using matplotlib, plotly, and seaborn"
        self.requires_permission = None

        self.inputSchema = {
            "type": "object",
            "properties": {
                "data_source": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["data", "query", "doctype"]},
                        "data": {"type": "array", "description": "Raw data array"},
                        "query": {"type": "string", "description": "SQL query"},
                        "doctype": {"type": "string", "description": "DocType name"},
                        "fields": {"type": "array", "description": "Fields to fetch"},
                        "filters": {"type": "object", "description": "Filters to apply"},
                    },
                    "required": ["type"],
                    "description": "Data source configuration",
                },
                "chart_config": {
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "enum": ["bar", "line", "pie", "scatter", "histogram", "box", "heatmap", "area"],
                            "description": "Type of chart to create",
                        },
                        "title": {"type": "string", "description": "Chart title"},
                        "x_column": {"type": "string", "description": "X-axis column"},
                        "y_column": {"type": "string", "description": "Y-axis column"},
                        "color_column": {"type": "string", "description": "Column for color grouping"},
                        "size_column": {"type": "string", "description": "Column for size (scatter plots)"},
                        "aggregation": {
                            "type": "string",
                            "enum": ["sum", "count", "mean", "median", "min", "max"],
                            "default": "sum",
                            "description": "Aggregation method",
                        },
                    },
                    "required": ["chart_type", "title"],
                    "description": "Chart configuration",
                },
                "styling": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string", "enum": ["default", "dark", "whitegrid", "darkgrid"]},
                        "color_palette": {
                            "type": "string",
                            "enum": ["default", "viridis", "plasma", "cool", "warm"],
                        },
                        "figure_size": {"type": "array", "items": {"type": "number"}},
                        "dpi": {"type": "integer", "default": 150},
                    },
                    "description": "Visual styling options",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["base64", "svg", "html", "json"],
                    "default": "base64",
                    "description": "Output format",
                },
            },
            "required": ["data_source", "chart_config"],
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create visualization"""
        try:
            data_source = arguments.get("data_source", {})
            chart_config = arguments.get("chart_config", {})
            styling = arguments.get("styling", {})
            output_format = arguments.get("output_format", "base64")

            # Get data
            data = self._get_data(data_source)
            if not data:
                return {"success": False, "error": "No data available for visualization"}

            # Create visualization
            chart_result = self._create_chart(data, chart_config, styling, output_format)

            return {
                "success": True,
                "visualization": chart_result["data"],
                "format": output_format,
                "chart_type": chart_config.get("chart_type"),
                "title": chart_config.get("title"),
                "data_points": len(data),
                "display_hint": chart_result.get("display_hint"),
            }

        except Exception as e:
            frappe.log_error(
                title=_("Visualization Creation Error"), message=f"Error creating visualization: {str(e)}"
            )

            return {"success": False, "error": str(e)}

    def _get_data(self, data_source: Dict[str, Any]) -> List[Dict]:
        """Get data from various sources"""
        try:
            source_type = data_source.get("type")

            if source_type == "data":
                return data_source.get("data", [])

            elif source_type == "query":
                query = data_source.get("query")
                if not query:
                    return []

                result = frappe.db.sql(query, as_dict=True)
                return result

            elif source_type == "doctype":
                doctype = data_source.get("doctype")
                fields = data_source.get("fields", ["name"])
                filters = data_source.get("filters", {})
                limit = data_source.get("limit", 100)

                if not doctype:
                    return []

                # Check permissions
                if not frappe.has_permission(doctype, "read"):
                    return []

                result = frappe.get_all(doctype, fields=fields, filters=filters, limit=limit)
                return result

            else:
                return []

        except Exception as e:
            frappe.logger("create_visualization").error(f"Failed to get data: {str(e)}")
            return []

    def _create_chart(
        self, data: List[Dict], chart_config: Dict, styling: Dict, output_format: str
    ) -> Dict[str, Any]:
        """Create chart using matplotlib/plotly"""
        try:
            import json

            import matplotlib.pyplot as plt
            import pandas as pd
            import seaborn as sns

            # Clean data before creating DataFrame
            cleaned_data = []
            for row in data:
                clean_row = {}
                for key, value in row.items():
                    # Convert complex objects to strings
                    if hasattr(value, "__dict__") or hasattr(value, "__array_struct__"):
                        clean_row[key] = str(value)
                    elif isinstance(value, (list, dict)):
                        clean_row[key] = json.dumps(value) if value else ""
                    elif value is None:
                        clean_row[key] = ""
                    else:
                        clean_row[key] = value
                cleaned_data.append(clean_row)

            # Convert to DataFrame
            df = pd.DataFrame(cleaned_data)

            if df.empty:
                return {"data": "", "display_hint": "No data to visualize"}

            # Apply styling
            self._apply_styling(styling)

            # Create chart based on type
            chart_type = chart_config.get("chart_type", "bar")
            title = chart_config.get("title", "Chart")

            # Set up figure
            figure_size = styling.get("figure_size", [10, 6])
            dpi = styling.get("dpi", 150)

            plt.figure(figsize=figure_size, dpi=dpi)

            if chart_type == "bar":
                result = self._create_bar_chart(df, chart_config)
            elif chart_type == "line":
                result = self._create_line_chart(df, chart_config)
            elif chart_type == "pie":
                result = self._create_pie_chart(df, chart_config)
            elif chart_type == "scatter":
                result = self._create_scatter_chart(df, chart_config)
            elif chart_type == "histogram":
                result = self._create_histogram(df, chart_config)
            elif chart_type == "box":
                result = self._create_box_plot(df, chart_config)
            elif chart_type == "heatmap":
                result = self._create_heatmap(df, chart_config)
            elif chart_type == "area":
                result = self._create_area_chart(df, chart_config)
            else:
                # Default to bar chart
                result = self._create_bar_chart(df, chart_config)

            plt.title(title, fontsize=14, fontweight="bold")
            plt.tight_layout()

            # Export based on format
            if output_format == "base64":
                # Save to base64
                buffer = io.BytesIO()
                plt.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
                buffer.seek(0)

                chart_data = base64.b64encode(buffer.getvalue()).decode()
                plt.close()

                return {
                    "data": chart_data,
                    "display_hint": "Base64 encoded PNG image. Use in <img> tag or save as PNG file.",
                }

            elif output_format == "svg":
                buffer = io.StringIO()
                plt.savefig(buffer, format="svg", bbox_inches="tight")
                buffer.seek(0)

                chart_data = buffer.getvalue()
                plt.close()

                return {"data": chart_data, "display_hint": "SVG vector image data"}

            else:
                # Default to base64
                buffer = io.BytesIO()
                plt.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
                buffer.seek(0)

                chart_data = base64.b64encode(buffer.getvalue()).decode()
                plt.close()

                return {"data": chart_data, "display_hint": "Base64 encoded PNG image"}

        except Exception as e:
            plt.close()  # Make sure to close any open figures
            raise e

    def _apply_styling(self, styling: Dict):
        """Apply styling configuration"""
        theme = styling.get("theme", "default")
        color_palette = styling.get("color_palette", "default")

        # Apply seaborn style
        if theme == "dark":
            import matplotlib.pyplot as plt

            plt.style.use("dark_background")
        elif theme in ["whitegrid", "darkgrid"]:
            import seaborn as sns

            sns.set_style(theme)

        # Apply color palette
        if color_palette != "default":
            import seaborn as sns

            sns.set_palette(color_palette)

    def _create_bar_chart(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create bar chart"""
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd

        x_col = config.get("x_column") or df.columns[0]
        y_col = config.get("y_column") or df.columns[1] if len(df.columns) > 1 else df.columns[0]

        # Handle aggregation if needed
        if config.get("aggregation") and config["aggregation"] != "count":
            df_grouped = df.groupby(x_col)[y_col].agg(config["aggregation"]).reset_index()
        elif config.get("aggregation") == "count":
            df_grouped = df.groupby(x_col).size().reset_index(name="count")
            y_col = "count"
        else:
            df_grouped = df

        # Convert data to safe types for plotting
        try:
            x_data = (
                df_grouped[x_col].astype(str) if df_grouped[x_col].dtype == "object" else df_grouped[x_col]
            )
            y_data = pd.to_numeric(df_grouped[y_col], errors="coerce").fillna(0)

            # Handle any remaining NaN or inf values
            y_data = np.where(np.isfinite(y_data), y_data, 0)

            plt.bar(x_data, y_data)
            plt.xlabel(x_col)
            plt.ylabel(y_col)
            plt.xticks(rotation=45)

        except Exception as e:
            # Fallback: simple value counts if data conversion fails
            value_counts = df_grouped[x_col].value_counts()
            plt.bar(range(len(value_counts)), value_counts.values)
            plt.xticks(range(len(value_counts)), value_counts.index, rotation=45)
            plt.xlabel(x_col)
            plt.ylabel("Count")

        return {"success": True}

    def _create_line_chart(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create line chart"""
        import matplotlib.pyplot as plt

        x_col = config.get("x_column") or df.columns[0]
        y_col = config.get("y_column") or df.columns[1] if len(df.columns) > 1 else df.columns[0]

        plt.plot(df[x_col], df[y_col], marker="o")
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.xticks(rotation=45)

        return {"success": True}

    def _create_pie_chart(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create pie chart"""
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd

        x_col = config.get("x_column") or df.columns[0]

        # Count occurrences
        value_counts = df[x_col].value_counts()

        # Convert to safe types
        labels = [str(label) for label in value_counts.index]
        values = np.array(value_counts.values, dtype=float)

        # Filter out any zero or negative values
        mask = values > 0
        labels = [labels[i] for i in range(len(labels)) if mask[i]]
        values = values[mask]

        if len(values) > 0:
            plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        else:
            # Empty pie chart fallback
            plt.text(0.5, 0.5, "No data to display", ha="center", va="center")

        return {"success": True}

    def _create_scatter_chart(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create scatter plot"""
        import matplotlib.pyplot as plt

        x_col = config.get("x_column") or df.columns[0]
        y_col = config.get("y_column") or df.columns[1] if len(df.columns) > 1 else df.columns[0]

        plt.scatter(df[x_col], df[y_col])
        plt.xlabel(x_col)
        plt.ylabel(y_col)

        return {"success": True}

    def _create_histogram(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create histogram"""
        import matplotlib.pyplot as plt

        y_col = config.get("y_column") or df.columns[0]

        plt.hist(df[y_col], bins=20, alpha=0.7)
        plt.xlabel(y_col)
        plt.ylabel("Frequency")

        return {"success": True}

    def _create_box_plot(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create box plot"""
        import matplotlib.pyplot as plt

        y_col = config.get("y_column") or df.columns[0]

        plt.boxplot(df[y_col])
        plt.ylabel(y_col)

        return {"success": True}

    def _create_heatmap(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create heatmap"""
        import seaborn as sns

        # Use only numeric columns
        numeric_df = df.select_dtypes(include=["number"])

        if numeric_df.empty:
            raise ValueError("No numeric data available for heatmap")

        correlation_matrix = numeric_df.corr()
        sns.heatmap(correlation_matrix, annot=True, cmap="coolwarm", center=0)

        return {"success": True}

    def _create_area_chart(self, df: "pd.DataFrame", config: Dict) -> Dict:
        """Create area chart"""
        import matplotlib.pyplot as plt

        x_col = config.get("x_column") or df.columns[0]
        y_col = config.get("y_column") or df.columns[1] if len(df.columns) > 1 else df.columns[0]

        plt.fill_between(df[x_col], df[y_col], alpha=0.7)
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.xticks(rotation=45)

        return {"success": True}


# Export for plugin discovery
__all__ = ["CreateVisualization"]
