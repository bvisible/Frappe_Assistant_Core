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
Prompts handlers for MCP protocol
Handles prompts/list and prompts/get requests
"""

from typing import Any, Dict, List, Optional

from frappe_assistant_core.constants.definitions import (
    ErrorCodes,
    ErrorMessages,
    LogMessages,
    PromptTemplates,
)
from frappe_assistant_core.utils.logger import api_logger


def handle_prompts_list(request_id: Optional[Any]) -> Dict[str, Any]:
    """Handle prompts/list request - return available prompts for artifact streaming"""
    try:
        api_logger.debug(LogMessages.PROMPTS_LIST_REQUEST)

        prompts = _get_prompt_definitions()

        response = {"jsonrpc": "2.0", "result": {"prompts": prompts}}

        # Only include id if it's not None
        if request_id is not None:
            response["id"] = request_id

        api_logger.info(f"Prompts list request completed, returned {len(prompts)} prompts")
        return response

    except Exception as e:
        api_logger.error(f"Error in handle_prompts_list: {e}")

        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": ErrorCodes.INTERNAL_ERROR,
                "message": ErrorMessages.INTERNAL_ERROR,
                "data": str(e),
            },
        }

        # Only include id if it's not None
        if request_id is not None:
            response["id"] = request_id

        return response


def handle_prompts_get(params: Dict[str, Any], request_id: Optional[Any]) -> Dict[str, Any]:
    """Handle prompts/get request - return specific prompt content"""
    try:
        api_logger.debug(LogMessages.PROMPTS_GET_REQUEST.format(params))

        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if not prompt_name:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": ErrorCodes.INVALID_PARAMS, "message": ErrorMessages.MISSING_PROMPT_NAME},
            }
            if request_id is not None:
                response["id"] = request_id
            return response

        # Generate prompt content based on name
        prompt_result = _generate_prompt_content(prompt_name, arguments)

        if prompt_result is None:
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": ErrorCodes.INVALID_PARAMS,
                    "message": ErrorMessages.UNKNOWN_PROMPT.format(prompt_name),
                },
            }
            if request_id is not None:
                response["id"] = request_id
            return response

        response = {"jsonrpc": "2.0", "result": prompt_result}

        # Only include id if it's not None
        if request_id is not None:
            response["id"] = request_id

        api_logger.info(f"Prompts get request completed for: {prompt_name}")
        return response

    except Exception as e:
        api_logger.error(f"Error in handle_prompts_get: {e}")

        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": ErrorCodes.INTERNAL_ERROR,
                "message": ErrorMessages.INTERNAL_ERROR,
                "data": str(e),
            },
        }

        # Only include id if it's not None
        if request_id is not None:
            response["id"] = request_id

        return response


def _get_prompt_definitions() -> List[Dict[str, Any]]:
    """Get the list of available prompt definitions"""
    return [
        {
            "name": "enforce_artifact_streaming_analysis",
            "description": "Enforce artifact streaming for comprehensive analysis to prevent response limits",
            "arguments": [
                {
                    "name": "analysis_type",
                    "description": "Type of analysis to perform (sales, financial, operational, data_exploration)",
                    "required": True,
                },
                {
                    "name": "data_source",
                    "description": "Frappe data source or DocType to analyze",
                    "required": True,
                },
            ],
        },
        {
            "name": "create_business_intelligence_report",
            "description": "Create comprehensive business intelligence report in artifacts with unlimited depth",
            "arguments": [
                {
                    "name": "report_focus",
                    "description": "Primary focus area (sales, financial, operational, customer_analysis, inventory)",
                    "required": True,
                },
                {
                    "name": "time_period",
                    "description": "Analysis time period (last_month, last_quarter, last_year, custom)",
                    "required": False,
                },
            ],
        },
        {
            "name": "stream_python_analysis_to_artifact",
            "description": "Stream Python analysis results to dedicated artifact workspace for unlimited analysis depth",
            "arguments": [
                {
                    "name": "analysis_goal",
                    "description": "What insights are you trying to achieve with this analysis",
                    "required": True,
                },
                {
                    "name": "complexity_level",
                    "description": "Expected complexity (simple, medium, complex, comprehensive)",
                    "required": False,
                },
            ],
        },
    ]


def _generate_prompt_content(prompt_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate prompt content based on name and arguments"""

    if prompt_name == "enforce_artifact_streaming_analysis":
        analysis_type = arguments.get("analysis_type", "comprehensive")
        data_source = arguments.get("data_source", "Frappe data")

        return {
            "description": f"Artifact streaming workflow for {prompt_name}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": PromptTemplates.ENFORCE_STREAMING.format(
                            analysis_type=analysis_type, data_source=data_source
                        ),
                    },
                }
            ],
        }

    elif prompt_name == "create_business_intelligence_report":
        report_focus = arguments.get("report_focus", "business performance")
        time_period = arguments.get("time_period", "recent")

        return {
            "description": f"Artifact streaming workflow for {prompt_name}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": PromptTemplates.BI_REPORT.format(
                            report_focus=report_focus, time_period=time_period
                        ),
                    },
                }
            ],
        }

    elif prompt_name == "stream_python_analysis_to_artifact":
        analysis_goal = arguments.get("analysis_goal", "data analysis")
        complexity_level = arguments.get("complexity_level", "comprehensive")

        return {
            "description": f"Artifact streaming workflow for {prompt_name}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": PromptTemplates.PYTHON_ANALYSIS.format(
                            complexity_level=complexity_level, analysis_goal=analysis_goal
                        ),
                    },
                }
            ],
        }

    return None
