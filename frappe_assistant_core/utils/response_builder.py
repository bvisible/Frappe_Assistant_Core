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

from typing import Any, Dict


def build_response(success: bool, message: str = "", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build a standardized response format for assistant API."""
    response = {"success": success, "message": message, "data": data or {}}
    return response


def handle_error(error_message: str, error_code: int = 400) -> Dict[str, Any]:
    """Build an error response format for assistant API."""
    return {"success": False, "error": {"message": error_message, "code": error_code}}


class StreamingResponseBuilder:
    """Response templates that automatically promote artifact creation for analysis tools"""

    # Streaming response templates
    STREAMING_TEMPLATES = {
        "analysis_initialization": """
🔄 **STARTING STREAMING ANALYSIS**

Creating analysis workspace artifact to avoid response limits...

**Streaming Protocol Active:**
- All detailed analysis → Artifact workspace
- Real-time updates → Progressive artifact building
- Unlimited depth → No response constraints
- Professional output → Stakeholder-ready deliverables

**Analysis Progress:**
✅ Workspace created
🔄 Streaming {operation_type} analysis...
📊 Building insights in artifact...

*See artifact for complete analysis details and findings.*
        """,
        "tool_result_streaming": """
**Analysis update streamed to workspace artifact**

Tool: `{tool_name}`
Status: ✅ Results captured in artifact
Progress: Building comprehensive analysis...

*All detailed findings and calculations are in the workspace artifact for unlimited analysis depth.*
        """,
        "multi_step_continuation": """
**Continuing analysis in workspace artifact...**

Added: {operation_type} findings
Status: Analysis expanding in artifact
Depth: Unlimited via streaming approach

*Comprehensive analysis building in artifact - no response limits with this approach.*
        """,
    }

    @staticmethod
    def build_streaming_response(
        tool_name: str, operation_type: str, raw_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Hybrid approach: show small results directly, auto-stream large results to artifacts"""

        # For analysis tools, use hybrid streaming approach
        if tool_name in [
            "analyze_frappe_data",
            "execute_python_code",
            "query_and_analyze",
            "create_visualization",
        ]:
            # More reasonable thresholds for streaming
            output_lines = len(raw_result.get("output", "").split("\n")) if raw_result.get("output") else 0
            variable_count = len(raw_result.get("variables", {}))
            data_rows = len(raw_result.get("data", []))

            # Smart streaming logic
            needs_streaming = (
                output_lines > 20  # More than 20 lines of output
                or variable_count > 15  # More than 15 variables created
                or data_rows > 100  # More than 100 data rows
                or (output_lines > 10 and variable_count > 8)  # Medium complexity combination
            )

            if needs_streaming:
                # Format full content for artifact creation
                full_content = StreamingResponseBuilder._format_full_analysis_for_artifact(
                    tool_name, raw_result
                )
                summary = StreamingResponseBuilder._get_analysis_summary(tool_name, raw_result)

                # Response that triggers Claude to create an artifact
                artifact_trigger_response = f"""
I'll create a comprehensive analysis artifact to present these substantial results without response limits.

{summary}

The analysis contains extensive output that benefits from artifact presentation for professional formatting and unlimited depth. Let me create a dedicated workspace for these results:

{full_content}
"""

                return {"content": [{"type": "text", "text": artifact_trigger_response}]}
            else:
                # Show full results for small analyses
                actual_content = StreamingResponseBuilder._format_actual_results(tool_name, raw_result)

                streaming_tip = """

---

💡 **ARTIFACT TIP:** For larger analyses (>20 lines output), results will auto-stream to artifacts for unlimited depth.
"""

                return {"content": [{"type": "text", "text": actual_content + streaming_tip}]}

        # Return standard response for non-analysis tools
        return build_response(raw_result.get("success", True), raw_result.get("message", ""), raw_result)

    @staticmethod
    def _get_analysis_summary(tool_name: str, raw_result: Dict[str, Any]) -> str:
        """Generate a brief summary of analysis results for streaming enforcement"""

        if tool_name == "execute_python_code":
            output_lines = len(raw_result.get("output", "").split("\n")) if raw_result.get("output") else 0
            variable_count = len(raw_result.get("variables", {}))
            return f"📊 **Summary:** {output_lines} lines of output, {variable_count} variables created"

        elif tool_name == "analyze_frappe_data":
            record_count = len(raw_result.get("data", []))
            insight_count = len(raw_result.get("insights", []))
            return f"📈 **Summary:** Analyzed {record_count} records, generated {insight_count} insights"

        elif tool_name == "query_and_analyze":
            row_count = raw_result.get("row_count", 0)
            column_count = len(raw_result.get("columns", []))
            return f"🔍 **Summary:** Query returned {row_count} rows, {column_count} columns"

        elif tool_name == "create_visualization":
            chart_type = raw_result.get("chart_type", "unknown")
            data_points = raw_result.get("data_points", 0)
            return f"📊 **Summary:** Created {chart_type} chart with {data_points} data points"

        else:
            return "📋 **Summary:** Complex analysis completed with substantial results"

    @staticmethod
    def _get_results_preview(tool_name: str, raw_result: Dict[str, Any]) -> str:
        """Generate a preview of results for auto-streaming responses"""

        if tool_name == "execute_python_code":
            preview = ""

            # Show first few lines of output
            if raw_result.get("output"):
                output_lines = raw_result["output"].split("\n")
                preview_lines = output_lines[:8]  # First 8 lines
                preview += "```\n" + "\n".join(preview_lines)
                if len(output_lines) > 8:
                    preview += f"\n... ({len(output_lines) - 8} more lines in artifact)"
                preview += "\n```\n\n"

            # Show key variables
            if raw_result.get("variables"):
                variables = raw_result["variables"]
                key_vars = list(variables.items())[:5]  # First 5 variables
                preview += "**Key Variables:**\n"
                for var_name, var_value in key_vars:
                    if isinstance(var_value, dict) and var_value.get("type") == "dataframe":
                        shape = var_value.get("shape", "unknown shape")
                        preview += f"• `{var_name}`: DataFrame {shape}\n"
                    else:
                        value_str = (
                            str(var_value)[:50] + "..." if len(str(var_value)) > 50 else str(var_value)
                        )
                        preview += f"• `{var_name}`: {value_str}\n"

                if len(variables) > 5:
                    preview += f"• ... and {len(variables) - 5} more variables in artifact\n"

            return preview

        elif tool_name in ["analyze_frappe_data", "query_and_analyze"]:
            preview = ""
            if raw_result.get("data"):
                data = raw_result["data"]
                preview += f"**Data Preview:** {len(data)} total records\n"
                # Show first few records
                preview_records = data[:3] if len(data) > 3 else data
                for i, record in enumerate(preview_records, 1):
                    preview += f"{i}. {str(record)[:100]}...\n"
                if len(data) > 3:
                    preview += f"... and {len(data) - 3} more records in artifact\n"
            return preview

        else:
            return "Full results available in artifact workspace."

    @staticmethod
    def _format_full_analysis_for_artifact(tool_name: str, raw_result: Dict[str, Any]) -> str:
        """Format complete analysis results for artifact creation"""

        if tool_name == "execute_python_code":
            # Build content safely without complex f-strings
            variables_count = len(raw_result.get("variables", {}))
            output_lines = len(raw_result.get("output", "").split("\n")) if raw_result.get("output") else 0
            output_text = raw_result.get("output", "No output generated")

            content = "# Python Analysis Results\n\n"
            content += "## Execution Summary\n"
            content += f"- **Tool:** `{tool_name}`\n"
            content += "- **Status:** ✅ Completed Successfully\n"
            content += f"- **Variables Created:** {variables_count}\n"
            content += f"- **Output Lines:** {output_lines}\n\n"
            content += "## Analysis Output\n\n"
            content += "```\n"
            content += output_text + "\n"
            content += "```\n\n"
            content += "## Variables & Data Created\n\n"

            # Add detailed variable information
            if raw_result.get("variables"):
                variables = raw_result["variables"]
                for var_name, var_value in variables.items():
                    if isinstance(var_value, dict) and var_value.get("type") == "dataframe":
                        shape = var_value.get("shape", "unknown shape")
                        content += f"### `{var_name}` - DataFrame {shape}\n"
                        if var_value.get("columns"):
                            content += f"**Columns:** {', '.join(var_value['columns'][:10])}{'...' if len(var_value['columns']) > 10 else ''}\n\n"
                        if var_value.get("preview"):
                            content += f"**Preview:**\n```\n{var_value['preview']}\n```\n\n"
                    elif isinstance(var_value, dict) and var_value.get("type") == "numpy_array":
                        content += f"### `{var_name}` - NumPy Array {var_value.get('shape', '')}\n"
                        content += f"**Data Type:** {var_value.get('dtype', 'unknown')}\n\n"
                    else:
                        content += f"### `{var_name}`\n"
                        content += f"**Value:** `{str(var_value)[:200]}{'...' if len(str(var_value)) > 200 else ''}`\n\n"

            # Add library information
            if raw_result.get("libraries_info"):
                lib_info = raw_result["libraries_info"]
                content += "## Available Libraries\n\n"
                core_libs = lib_info.get("core_data_science", {})
                available_core = [name for name, available in core_libs.items() if available]
                if available_core:
                    content += f"**Data Science Libraries:** {', '.join(available_core)}\n\n"

                if lib_info.get("import_results"):
                    content += "**Import Results:**\n"
                    for result in lib_info["import_results"]:
                        content += f"- {result}\n"
                    content += "\n"

            # Add error information if any
            if raw_result.get("errors"):
                content += "## Warnings/Errors\n\n```\n"
                content += raw_result["errors"] + "\n"
                content += "```\n\n"

            content += "\n## Analysis Complete\n\n"
            content += "This comprehensive analysis has been preserved in this artifact workspace with:\n"
            content += "- ✅ Complete execution output and results\n"
            content += "- ✅ All variables and data structures\n"
            content += "- ✅ Library availability and import status\n"
            content += "- ✅ Professional formatting for stakeholder presentation\n"
            content += "- ✅ Unlimited depth without response truncation\n\n"
            content += (
                "*Use this artifact to continue analysis, share insights, or build upon these results.*\n"
            )

            return content

        elif tool_name in ["analyze_frappe_data", "query_and_analyze"]:
            records_count = len(raw_result.get("data", []))

            content = "# Frappe Data Analysis Results\n\n"
            content += "## Analysis Summary\n"
            content += f"- **Tool:** `{tool_name}`\n"
            content += "- **Status:** ✅ Completed Successfully\n"
            content += f"- **Records Processed:** {records_count}\n\n"

            if raw_result.get("data"):
                content += "## Data Results\n\n"
                data = raw_result["data"]
                for i, record in enumerate(data, 1):
                    content += f"### Record {i}\n```json\n{str(record)}\n```\n\n"

            if raw_result.get("insights"):
                content += "## Business Insights\n\n"
                for insight in raw_result["insights"]:
                    content += f"- {insight}\n"
                content += "\n"

            content += "\n## Analysis Complete\n\n"
            content += "This Frappe data analysis provides comprehensive insights with unlimited depth in this artifact workspace.\n"

            return content

        else:
            content = f"# Analysis Results - {tool_name}\n\n"
            content += "## Complete Results\n\n"
            content += str(raw_result) + "\n\n"
            content += "## Analysis Complete\n\n"
            content += "Full results preserved in artifact workspace for unlimited depth and professional presentation.\n"
            return content

    @staticmethod
    def _format_actual_results(tool_name: str, raw_result: Dict[str, Any]) -> str:
        """Format the actual tool execution results"""

        if tool_name == "execute_python_code":
            text = "**Python Code Execution Results:**\n\n"

            if raw_result.get("output"):
                text += f"**Output:**\n```\n{raw_result['output']}\n```\n\n"

            if raw_result.get("variables"):
                text += f"**Variables Created ({len(raw_result['variables'])}):**\n"
                for var_name, var_value in raw_result["variables"].items():
                    if isinstance(var_value, dict) and var_value.get("type") == "dataframe":
                        shape = var_value.get("shape", "unknown shape")
                        text += f"• `{var_name}`: DataFrame {shape}\n"
                        # Show column info if available
                        if var_value.get("columns"):
                            cols = var_value["columns"][:5]  # First 5 columns
                            text += f"  Columns: {', '.join(cols)}{'...' if len(var_value['columns']) > 5 else ''}\n"
                    elif isinstance(var_value, dict) and var_value.get("type") == "numpy_array":
                        text += f"• `{var_name}`: NumPy Array {var_value.get('shape', '')}\n"
                    else:
                        value_str = (
                            str(var_value)[:100] + "..." if len(str(var_value)) > 100 else str(var_value)
                        )
                        text += f"• `{var_name}`: {value_str}\n"
                text += "\n"

            if raw_result.get("errors"):
                text += f"**Warnings/Errors:**\n```\n{raw_result['errors']}\n```\n\n"

            # Show library information if available
            if raw_result.get("libraries_info"):
                lib_info = raw_result["libraries_info"]
                core_libs = lib_info.get("core_data_science", {})
                available_core = [name for name, available in core_libs.items() if available]

                if available_core:
                    text += f"**Available Libraries:** {', '.join(available_core)}\n"

                if lib_info.get("import_results"):
                    text += "**Import Results:**\n"
                    for result in lib_info["import_results"]:
                        text += f"  {result}\n"
                    text += "\n"

            if not raw_result.get("success"):
                text += f"**Error:** {raw_result.get('error', 'Unknown error')}\n\n"
                # Show allowed modules on error
                if raw_result.get("allowed_modules"):
                    text += f"**Allowed modules:** {', '.join(raw_result['allowed_modules'][:10])}...\n\n"

        elif tool_name == "analyze_frappe_data":
            analysis = raw_result.get("analysis", {})
            text = "**Data Analysis Results:**\n\n"
            text += f"• Analysis Type: {analysis.get('type', 'Unknown')}\n"
            text += f"• DocType: {analysis.get('doctype', 'Unknown')}\n\n"

            if analysis.get("numerical_summary"):
                text += "**Numerical Summary:**\n"
                for field, stats in analysis["numerical_summary"].items():
                    text += f"• **{field}:**\n"
                    for stat, value in stats.items():
                        if isinstance(value, (int, float)):
                            text += f"  - {stat}: {value:.2f}\n"
                        else:
                            text += f"  - {stat}: {value}\n"
                text += "\n"

            if analysis.get("categorical_summary"):
                text += "**Categorical Summary:**\n"
                for field, counts in analysis["categorical_summary"].items():
                    text += f"• **{field}:** {len(counts)} unique values\n"
                    # Show top values
                    if isinstance(counts, dict):
                        for value, count in list(counts.items())[:5]:
                            text += f"  - {value}: {count}\n"
                text += "\n"

        elif tool_name == "query_and_analyze":
            text = "**SQL Query Results:**\n\n"
            text += f"• Rows Returned: {raw_result.get('row_count', 0)}\n"
            if raw_result.get("columns"):
                text += f"• Columns: {', '.join(raw_result['columns'])}\n\n"

            # Show sample data if available
            if raw_result.get("data") and len(raw_result["data"]) > 0:
                text += "**Sample Results (first 3 rows):**\n"
                for i, row in enumerate(raw_result["data"][:3]):
                    text += f"Row {i + 1}: {str(row)[:200]}{'...' if len(str(row)) > 200 else ''}\n"
                text += "\n"

        else:
            # Generic formatting for other tools
            text = f"**Tool Results ({tool_name}):**\n\n"
            if not raw_result.get("success"):
                text += f"**Error:** {raw_result.get('error', 'Unknown error')}\n\n"
            else:
                text += f"**Success:** {raw_result.get('message', 'Operation completed')}\n\n"
                if raw_result.get("data"):
                    text += f"**Data:** {str(raw_result['data'])[:500]}{'...' if len(str(raw_result['data'])) > 500 else ''}\n\n"

        return text

    @staticmethod
    def format_minimal_summary(raw_result: Dict[str, Any]) -> str:
        """Create minimal summaries that encourage artifact exploration"""
        # Extract key metrics from result
        record_count = 0
        if "data" in raw_result:
            record_count = len(raw_result["data"]) if isinstance(raw_result["data"], list) else 1
        elif "row_count" in raw_result:
            record_count = raw_result["row_count"]
        elif "total_records" in raw_result:
            record_count = raw_result["total_records"]

        summary = f"Key findings captured in artifact. Records processed: {record_count}."

        # Add specific summaries based on tool type
        if "analysis" in raw_result:
            analysis = raw_result["analysis"]
            if "numerical_summary" in analysis:
                summary += f" Analyzed {len(analysis['numerical_summary'])} numerical fields."
            if "categorical_summary" in analysis:
                summary += f" Analyzed {len(analysis['categorical_summary'])} categorical fields."

        summary += " See workspace for comprehensive analysis."
        return summary


def format_tool_response(tool_name: str, raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced response formatting with mandatory artifact promotion for analysis tools"""

    # Check if this is an analysis tool that requires streaming
    analysis_tools = [
        "analyze_frappe_data",
        "execute_python_code",
        "query_and_analyze",
        "create_visualization",
        "report_execute",
    ]

    if tool_name in analysis_tools:
        return StreamingResponseBuilder.build_streaming_response(tool_name, "data_analysis", raw_result)

    # For non-analysis tools, use standard response format
    return build_response(raw_result.get("success", True), raw_result.get("message", ""), raw_result)
