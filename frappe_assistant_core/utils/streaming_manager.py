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
Centralized streaming configuration manager that reads from Assistant Core Settings.
Provides settings-driven streaming behavior instead of hardcoded values.
"""

import json
from typing import Any, Dict, Optional

import frappe
from frappe import _


class StreamingManager:
    """
    Centralized streaming configuration manager that reads from settings.

    This class provides a single source of truth for all streaming-related
    configuration, replacing hardcoded values throughout the codebase.
    """

    def __init__(self):
        self._settings = None
        self._streaming_config = None
        self.logger = frappe.logger("frappe_assistant_core.streaming_manager")

    @property
    def settings(self):
        """Get cached Assistant Core Settings"""
        if self._settings is None:
            try:
                self._settings = frappe.get_single("Assistant Core Settings")
            except Exception as e:
                self.logger.warning(f"Failed to load settings: {str(e)}")
                # Return a mock settings object with defaults
                self._settings = type(
                    "MockSettings",
                    (),
                    {
                        "enforce_artifact_streaming": True,
                        "response_limit_prevention": True,
                        "streaming_behavior_instructions": self._get_default_instructions(),
                        "streaming_line_threshold": 5,
                        "streaming_char_threshold": 1000,
                    },
                )()
        return self._settings

    @property
    def streaming_config(self):
        """Get cached streaming configuration"""
        if self._streaming_config is None:
            try:
                self._streaming_config = self.settings.get_streaming_protocol()
            except Exception as e:
                self.logger.warning(f"Failed to load streaming config: {str(e)}")
                # Fallback to defaults
                self._streaming_config = {
                    "artifact_streaming_enforced": True,
                    "limit_prevention_active": True,
                    "custom_instructions": self._get_default_instructions(),
                }
        return self._streaming_config

    def _get_default_instructions(self) -> str:
        """Get default streaming instructions"""
        return """Always create analysis workspace artifacts before performing data analysis.
Stream all detailed work to artifacts to prevent response limits.
Keep responses minimal with artifact references.
Build unlimited analysis depth via progressive artifact updates."""

    def should_enforce_streaming(self) -> bool:
        """Check if streaming should be enforced globally"""
        try:
            return bool(getattr(self.settings, "enforce_artifact_streaming", True))
        except Exception:
            return True  # Default to enforced for safety

    def should_prevent_response_limits(self) -> bool:
        """Check if response limit prevention is enabled"""
        try:
            return bool(getattr(self.settings, "response_limit_prevention", True))
        except Exception:
            return True  # Default to enabled for safety

    def get_custom_instructions(self) -> str:
        """Get custom streaming instructions from settings"""
        try:
            instructions = getattr(self.settings, "streaming_behavior_instructions", "")
            return instructions or self._get_default_instructions()
        except Exception:
            return self._get_default_instructions()

    def get_line_threshold(self) -> int:
        """Get line threshold for streaming"""
        try:
            return int(getattr(self.settings, "streaming_line_threshold", 5))
        except Exception:
            return 5

    def get_char_threshold(self) -> int:
        """Get character threshold for streaming"""
        try:
            return int(getattr(self.settings, "streaming_char_threshold", 1000))
        except Exception:
            return 1000

    def should_stream_tool_result(self, result: str, tool_name: str) -> bool:
        """
        Determine if result should be streamed based on settings.

        Args:
            result: Tool execution result
            tool_name: Name of the tool that generated the result

        Returns:
            bool: True if result should be streamed to artifact
        """
        try:
            # Analysis tools that should always stream when enforcement is enabled
            analysis_tools = [
                "analyze_frappe_data",
                "execute_python_code",
                "query_and_analyze",
                "create_visualization",
            ]

            # If streaming is enforced, always stream analysis tools
            if self.should_enforce_streaming() and tool_name in analysis_tools:
                self.logger.debug(f"Streaming enforced for analysis tool: {tool_name}")
                return True

            # If response limit prevention is enabled, check thresholds
            if self.should_prevent_response_limits():
                line_count = len(result.split("\n"))
                char_count = len(result)

                line_threshold = self.get_line_threshold()
                char_threshold = self.get_char_threshold()

                if line_count > line_threshold:
                    self.logger.debug(f"Streaming triggered by line count: {line_count} > {line_threshold}")
                    return True

                if char_count > char_threshold:
                    self.logger.debug(f"Streaming triggered by char count: {char_count} > {char_threshold}")
                    return True

                # Additional heuristics for complex data
                if self._detect_complex_data(result):
                    self.logger.debug("Streaming triggered by complex data detection")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error determining streaming requirement: {str(e)}")
            # Default to streaming for safety
            return True

    def _detect_complex_data(self, result: str) -> bool:
        """Detect if result contains complex data structures"""
        try:
            # Check for JSON with many records
            if result.strip().startswith("{") and '"data"' in result:
                # Count occurrences of "name" field (indicates records)
                name_count = result.count('"name"')
                if name_count > 3:
                    return True

            # Check for extensive tabular data
            if result.count("|") > 20:
                return True

            # Check for many list items
            if result.count("\n- ") > 10 or result.count("\n• ") > 10:
                return True

            return False

        except Exception:
            return False

    def get_streaming_instructions(self, tool_name: str, result: str, arguments: Dict[str, Any]) -> str:
        """
        Generate streaming instructions based on current settings.

        Args:
            tool_name: Name of the tool
            result: Tool execution result
            arguments: Tool arguments

        Returns:
            str: Formatted streaming instructions
        """
        try:
            lines = len(result.split("\n"))
            chars = len(result)

            # Get custom instructions from settings
            custom_instructions = self.get_custom_instructions()

            # Determine artifact type and sections based on tool
            artifact_type, sections = self._get_artifact_suggestions(tool_name)

            # Format based on enforcement setting
            if self.should_enforce_streaming():
                return self._format_enforced_streaming(
                    tool_name, result, arguments, custom_instructions, artifact_type, sections, lines, chars
                )
            else:
                return self._format_optional_streaming(
                    tool_name, result, arguments, custom_instructions, artifact_type, sections, lines, chars
                )

        except Exception as e:
            self.logger.error(f"Error generating streaming instructions: {str(e)}")
            # Return basic instructions as fallback
            return self._get_basic_fallback_instructions(tool_name, result)

    def _get_artifact_suggestions(self, tool_name: str) -> tuple:
        """Get suggested artifact type and sections for a tool"""
        if tool_name in ["analyze_frappe_data", "execute_python_code", "query_and_analyze"]:
            return "Data Analysis Report", [
                "Executive Summary",
                "Key Findings",
                "Detailed Analysis",
                "Recommendations",
            ]
        elif tool_name.startswith("report_"):
            return "Business Report", ["Report Summary", "Key Metrics", "Detailed Data", "Action Items"]
        elif tool_name.startswith("search_") or tool_name.startswith("metadata_"):
            return "Technical Documentation", [
                "Overview",
                "Search Results",
                "Technical Details",
                "Usage Notes",
            ]
        elif tool_name == "create_visualization":
            return "Visualization Report", [
                "Chart Overview",
                "Data Insights",
                "Visual Analysis",
                "Recommendations",
            ]
        else:
            return "Comprehensive Results", ["Summary", "Main Results", "Detailed Output", "Next Steps"]

    def _format_enforced_streaming(
        self,
        tool_name: str,
        result: str,
        arguments: Dict[str, Any],
        custom_instructions: str,
        artifact_type: str,
        sections: list,
        lines: int,
        chars: int,
    ) -> str:
        """Format instructions for enforced streaming"""

        # For extremely large results, don't include full content
        include_full_result = chars <= 10000

        # Create preview
        result_lines = result.split("\n")
        preview_lines = result_lines[:3] if len(result_lines) > 3 else result_lines
        preview = "\n".join(preview_lines)
        if len(result_lines) > 3:
            preview += f"\n... ({lines - 3} more lines)"

        instructions = f"""
🚨 ARTIFACT STREAMING ENFORCED (Administrator Setting)

📊 **Result Statistics:**
• Lines: {lines} (threshold: {self.get_line_threshold()}+)
• Characters: {chars:,} (threshold: {self.get_char_threshold():,}+)
• Tool: {tool_name}
• Enforcement: Enabled by Administrator

📋 **MANDATORY WORKFLOW (Admin Configuration):**
1. **CREATE ARTIFACT** - Type: {artifact_type}
2. **ADD SECTIONS:** {", ".join(sections)}
3. **STREAM FULL RESULTS** to artifact sections
4. **KEEP RESPONSE MINIMAL** (only summary/confirmation)

⚙️ **Custom Instructions from Settings:**
{custom_instructions}

🔧 **Tool Execution Details:**
• Tool: {tool_name}
• Arguments: {json.dumps(arguments, indent=2, default=str)}
• Timestamp: {frappe.utils.now()}

═══════════════════════════════════════════════════════════

📄 **PREVIEW:**
```
{preview}
```
"""

        if include_full_result:
            instructions += f"""
════════════════════════════════════════════════════════════════

🔄 **FULL RESULT FOR ARTIFACT STREAMING:**

{result}

════════════════════════════════════════════════════════════════

⚠️ **NEXT STEPS:**
1. Create workspace artifact with suggested sections above
2. Stream the complete result to appropriate artifact sections
3. Provide executive summary in your response
4. Build unlimited depth analysis via artifact streaming
"""
        else:
            instructions += f"""
⚠️ **RESULT TOO LARGE FOR DISPLAY:**
Result is {chars:,} characters - too large for conversation display.

**REQUIRED ACTION:**
1. Create workspace artifact with the suggested sections
2. Re-run this exact tool with same arguments
3. Stream all results directly to artifact sections
4. Provide only executive summary in response
"""

        return instructions

    def _format_optional_streaming(
        self,
        tool_name: str,
        result: str,
        arguments: Dict[str, Any],
        custom_instructions: str,
        artifact_type: str,
        sections: list,
        lines: int,
        chars: int,
    ) -> str:
        """Format instructions for optional streaming"""

        return f"""
💡 ARTIFACT STREAMING RECOMMENDED

📊 **Result Statistics:**
• Lines: {lines}
• Characters: {chars:,}
• Tool: {tool_name}

📋 **OPTIONAL WORKFLOW:**
This result may benefit from artifact streaming for better organization.

**Suggested Artifact Type:** {artifact_type}
**Suggested Sections:** {", ".join(sections)}

⚙️ **Custom Guidelines:**
{custom_instructions}

🔧 **Tool Details:**
• Tool: {tool_name}
• Arguments: {json.dumps(arguments, indent=2, default=str)}
• Timestamp: {frappe.utils.now()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**RESULT:**

{result}
"""

    def _get_basic_fallback_instructions(self, tool_name: str, result: str) -> str:
        """Get basic fallback instructions if main formatting fails"""
        return f"""
⚠️ STREAMING CONFIGURATION ERROR

Tool: {tool_name}
Timestamp: {frappe.utils.now()}

Result:
{result}

Note: Streaming configuration could not be loaded. Please check Assistant Core Settings.
"""

    def get_tool_description_suffix(self, tool_name: str) -> str:
        """
        Get dynamic description suffix for tools based on current settings.

        Args:
            tool_name: Name of the tool

        Returns:
            str: Description suffix to append to tool descriptions
        """
        try:
            analysis_tools = [
                "analyze_frappe_data",
                "execute_python_code",
                "query_and_analyze",
                "create_visualization",
            ]

            if tool_name in analysis_tools and self.should_enforce_streaming():
                return f"""

🚨 **ARTIFACT STREAMING ENFORCED**: This tool requires workspace artifacts for analysis results.
Create artifacts before execution to prevent response limits.

⚙️ **Custom Instructions**: {self.get_custom_instructions()}
"""
            elif self.should_prevent_response_limits():
                return f"""

💡 **ARTIFACT STREAMING RECOMMENDED**: Large results (>{self.get_line_threshold()} lines or >{self.get_char_threshold():,} characters) will be automatically streamed to artifacts.

⚙️ **Guidelines**: {self.get_custom_instructions()}
"""
            else:
                return f"""

💡 **ARTIFACT STREAMING AVAILABLE**: Consider using artifacts for complex analysis results.

⚙️ **Guidelines**: {self.get_custom_instructions()}
"""

        except Exception as e:
            self.logger.error(f"Error generating tool description suffix: {str(e)}")
            return "\n\n💡 **ARTIFACT STREAMING**: Consider using artifacts for complex results."

    def refresh_cache(self):
        """Refresh cached settings and configuration"""
        self._settings = None
        self._streaming_config = None
        self.logger.info("Streaming manager cache refreshed")


# Global instance
_streaming_manager = None


def get_streaming_manager() -> StreamingManager:
    """Get global streaming manager instance"""
    global _streaming_manager
    if _streaming_manager is None:
        _streaming_manager = StreamingManager()
    return _streaming_manager


def refresh_streaming_manager():
    """Refresh the global streaming manager instance"""
    global _streaming_manager
    _streaming_manager = None
    return get_streaming_manager()
