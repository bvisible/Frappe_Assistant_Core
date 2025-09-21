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

import json
from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.utils import now


def log_document_change(doc, method):
    """Log document changes for audit trail"""
    if should_log_document(doc.doctype):
        try:
            frappe.get_doc(
                {
                    "doctype": "Assistant Audit Log",
                    "action": "update_document",
                    "user": frappe.session.user,
                    "status": "Success",
                    "timestamp": now(),
                    "target_doctype": doc.doctype,
                    "target_name": doc.name,
                    "ip_address": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else None,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            pass  # Ignore audit logging errors


def log_document_submit(doc, method):
    """Log document submissions"""
    if should_log_document(doc.doctype):
        try:
            frappe.get_doc(
                {
                    "doctype": "Assistant Audit Log",
                    "action": "update_document",
                    "user": frappe.session.user,
                    "status": "Success",
                    "timestamp": now(),
                    "target_doctype": doc.doctype,
                    "target_name": doc.name,
                    "ip_address": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else None,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            pass


def log_document_cancel(doc, method):
    """Log document cancellations"""
    if should_log_document(doc.doctype):
        try:
            frappe.get_doc(
                {
                    "doctype": "Assistant Audit Log",
                    "action": "update_document",
                    "user": frappe.session.user,
                    "status": "Success",
                    "timestamp": now(),
                    "target_doctype": doc.doctype,
                    "target_name": doc.name,
                    "ip_address": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else None,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            pass


def should_log_document(doctype):
    """Check if document type should be logged"""
    # Don't log assistant internal documents to avoid recursion
    if doctype.startswith("assistant "):
        return False

    # try:
    #     # Get audit settings using the correct method
    #     audit_doctypes = frappe.db.get_single_value("assistant Server Settings", "audit_doctypes") or ""

    #     if audit_doctypes:
    #         return doctype in audit_doctypes.split(",")
    # except Exception:
    #     # If assistant Server Settings doesn't exist or has issues, don't log
    #     pass

    # By default, don't audit everything to avoid performance impact
    return False


def log_tool_execution(
    tool_name: str,
    user: str,
    arguments: Dict[str, Any],
    success: bool,
    execution_time: float,
    source_app: str,
    error_message: Optional[str] = None,
    output_data: Optional[Dict[str, Any]] = None,
):
    """
    Log tool execution for comprehensive audit trail.

    Args:
        tool_name: Name of the executed tool
        user: User who executed the tool
        arguments: Tool arguments (sensitive data should be pre-sanitized)
        success: Whether execution was successful
        execution_time: Time taken in seconds
        source_app: App that provides the tool
        error_message: Error message if execution failed
        output_data: Tool output data for audit trail
    """
    try:
        # Extract target information from arguments
        target_doctype = None
        target_name = None

        if arguments and isinstance(arguments, dict):
            # For tools that work with specific documents
            target_doctype = arguments.get("doctype")
            target_name = arguments.get("name")

        # Use tool name directly as action (since action field is now Data type)
        action = tool_name

        # Serialize output data for storage
        try:
            output_data_str = json.dumps(output_data, default=str) if output_data else None
        except (TypeError, ValueError):
            # Fallback: convert to string and truncate for large data
            output_data_str = str(output_data)[:2000]

        audit_doc = frappe.get_doc(
            {
                "doctype": "Assistant Audit Log",
                "action": action,  # Now uses tool name directly
                "tool_name": tool_name,
                "user": user,
                "status": "Success" if success else "Failed",
                "timestamp": now(),
                "execution_time": execution_time,
                "target_doctype": target_doctype,  # Populated from arguments
                "target_name": target_name,  # Populated from arguments
                "ip_address": getattr(frappe.local, "request_ip", None),
                "input_data": json.dumps(arguments) if arguments else None,
                "output_data": output_data_str,  # Now includes output
                "error_message": error_message,
            }
        )

        audit_doc.insert(ignore_permissions=True)

    except Exception as e:
        # Don't fail tool execution due to audit logging issues
        frappe.logger("audit_trail").warning(f"Failed to log tool execution: {str(e)}")


def log_tool_discovery(app_name: str, tools_found: int, errors: int, discovery_time: float):
    """
    Log tool discovery events.

    Args:
        app_name: Name of the app being scanned
        tools_found: Number of tools discovered
        errors: Number of discovery errors
        discovery_time: Time taken for discovery
    """
    try:
        audit_doc = frappe.get_doc(
            {
                "doctype": "Assistant Audit Log",
                "action": "discover_tools",
                "user": frappe.session.user or "System",
                "status": "Success" if errors == 0 else "Partial",
                "timestamp": now(),
                "target_doctype": "Tool Discovery",
                "target_name": app_name,
                "details": json.dumps(
                    {
                        "app_name": app_name,
                        "tools_found": tools_found,
                        "errors": errors,
                        "discovery_time": discovery_time,
                    },
                    default=str,
                ),
            }
        )

        audit_doc.insert(ignore_permissions=True)

    except Exception as e:
        frappe.logger("audit_trail").warning(f"Failed to log tool discovery: {str(e)}")


def log_security_event(event_type: str, user: str, details: Dict[str, Any], severity: str = "Medium"):
    """
    Log security-related events.

    Args:
        event_type: Type of security event (e.g., 'permission_denied', 'suspicious_activity')
        user: User associated with the event
        details: Event details dictionary
        severity: Event severity (Low, Medium, High, Critical)
    """
    try:
        audit_doc = frappe.get_doc(
            {
                "doctype": "Assistant Audit Log",
                "action": f"security_{event_type}",
                "user": user,
                "status": "Alert",
                "timestamp": now(),
                "target_doctype": "Security Event",
                "target_name": event_type,
                "ip_address": getattr(frappe.local, "request_ip", None),
                "details": json.dumps(
                    {"event_type": event_type, "severity": severity, **details}, default=str
                ),
            }
        )

        audit_doc.insert(ignore_permissions=True)

        # For critical events, also log to error log
        if severity == "Critical":
            frappe.log_error(
                title=f"Critical Security Event: {event_type}",
                message=f"User: {user}, Details: {json.dumps(details, default=str)}",
            )

    except Exception as e:
        frappe.logger("audit_trail").warning(f"Failed to log security event: {str(e)}")


def get_audit_summary(user: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
    """
    Get audit trail summary for monitoring.

    Args:
        user: Filter by specific user (None for all users)
        days: Number of days to include

    Returns:
        Audit summary statistics
    """
    try:
        from frappe.utils import add_days

        # Calculate date range
        from_date = add_days(now(), -days)

        # Build filters
        filters = {"timestamp": [">=", from_date]}
        if user:
            filters["user"] = user

        # Get audit logs
        logs = frappe.get_all(
            "Assistant Audit Log",
            filters=filters,
            fields=["action", "status", "user", "timestamp"],
            order_by="timestamp desc",
            limit=1000,
        )

        # Calculate statistics
        summary = {
            "total_events": len(logs),
            "date_range": {"from": from_date, "to": now()},
            "user_filter": user,
            "actions": {},
            "status_breakdown": {},
            "recent_events": logs[:10],  # Last 10 events
        }

        # Action breakdown
        for log in logs:
            action = log.get("action", "unknown")
            summary["actions"][action] = summary["actions"].get(action, 0) + 1

        # Status breakdown
        for log in logs:
            status = log.get("status", "unknown")
            summary["status_breakdown"][status] = summary["status_breakdown"].get(status, 0) + 1

        return summary

    except Exception as e:
        frappe.logger("audit_trail").error(f"Failed to get audit summary: {str(e)}")
        return {"total_events": 0, "error": str(e)}
