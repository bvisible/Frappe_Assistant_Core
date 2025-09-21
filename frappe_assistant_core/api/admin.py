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
Administrative API endpoints for Frappe Assistant Core.
Provides system administration and configuration endpoints.
"""

import json
from typing import Any, Dict, List

import frappe
from frappe import _

from frappe_assistant_core.core.tool_registry import get_tool_registry
from frappe_assistant_core.utils.plugin_manager import get_plugin_manager


@frappe.whitelist(allow_guest=False)
def get_system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status information.

    Returns:
        System status including tools, plugins, and health metrics
    """
    frappe.only_for("System Manager")

    try:
        # Get tool registry status
        registry = get_tool_registry()
        tools = registry.get_available_tools()

        # Get plugin manager status
        plugin_manager = get_plugin_manager()
        plugins = plugin_manager.get_discovered_plugins()
        enabled_plugins = plugin_manager.get_enabled_plugins()

        # Calculate statistics
        core_tools = [t for t in tools if not hasattr(t, "plugin_name")]
        plugin_tools = [t for t in tools if hasattr(t, "plugin_name")]

        # Get settings
        settings = frappe.get_single("Assistant Core Settings")

        status = {
            "success": True,
            "system_info": {
                "app_version": frappe.get_app_version("frappe_assistant_core") or "1.0.0",
                "frappe_version": frappe.__version__,
                "system_enabled": settings.enable_assistant if settings else False,
                "last_updated": frappe.utils.now(),
            },
            "tools": {
                "total": len(tools),
                "core_tools": len(core_tools),
                "plugin_tools": len(plugin_tools),
                "available_tools": [{"name": t.name, "description": t.description} for t in tools],
            },
            "plugins": {
                "total_discovered": len(plugins),
                "enabled": len(enabled_plugins),
                "available": len([p for p in plugins if p.get("can_enable", False)]),
                "plugin_list": plugins,
            },
            "performance": {
                "tool_registry_cache_hits": getattr(registry, "cache_hits", 0),
                "plugin_load_time": getattr(plugin_manager, "last_load_time", 0),
            },
        }

        return status

    except Exception as e:
        frappe.log_error(title=_("System Status Error"), message=f"Error getting system status: {str(e)}")

        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics for the assistant system.

    Returns:
        Performance metrics and statistics
    """
    frappe.only_for("System Manager")

    try:
        # Get tool execution statistics from cache
        metrics = frappe.cache().hget("assistant_metrics", "performance") or {}

        # Get recent error logs
        recent_errors = frappe.get_all(
            "Error Log",
            filters={
                "error": ["like", "%assistant%"],
                "creation": [">", frappe.utils.add_days(frappe.utils.now(), -7)],
            },
            fields=["name", "error", "creation"],
            limit=10,
            order_by="creation desc",
        )

        # Get database statistics
        db_stats = {
            "total_queries": frappe.db.sql(
                "SELECT COUNT(*) as count FROM `tabQuery Log` WHERE creation > %s",
                (frappe.utils.add_days(frappe.utils.now(), -1),),
            )[0][0]
            if frappe.db.table_exists("Query Log")
            else 0
        }

        return {
            "success": True,
            "metrics": {
                "tool_executions": metrics.get("tool_executions", {}),
                "average_response_time": metrics.get("avg_response_time", 0),
                "error_rate": metrics.get("error_rate", 0),
                "cache_hit_rate": metrics.get("cache_hit_rate", 0),
            },
            "recent_errors": recent_errors,
            "database_stats": db_stats,
            "memory_usage": {
                "tool_registry_size": len(get_tool_registry().get_available_tools()),
                "plugin_manager_cache": len(get_plugin_manager().get_discovered_plugins()),
            },
        }

    except Exception as e:
        frappe.log_error(
            title=_("Performance Metrics Error"), message=f"Error getting performance metrics: {str(e)}"
        )

        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def update_system_settings(settings_data: str) -> Dict[str, Any]:
    """
    Update system settings for Assistant Core.

    Args:
        settings_data: JSON string with settings to update

    Returns:
        Update operation result
    """
    frappe.only_for("System Manager")

    try:
        # Parse settings data
        settings = json.loads(settings_data)

        # Get current settings document
        doc = frappe.get_single("Assistant Core Settings")

        # Update allowed fields only
        allowed_fields = [
            "enable_assistant",
            "max_request_size",
            "request_timeout",
            "cache_enabled",
            "cache_ttl",
            "log_level",
            "enable_performance_monitoring",
        ]

        updated_fields = []
        for field in allowed_fields:
            if field in settings:
                old_value = getattr(doc, field, None)
                new_value = settings[field]

                if old_value != new_value:
                    setattr(doc, field, new_value)
                    updated_fields.append({"field": field, "old_value": old_value, "new_value": new_value})

        # Save settings
        doc.save()

        # Log the change
        frappe.logger("admin").info(f"System settings updated by {frappe.session.user}: {updated_fields}")

        return {"success": True, "message": "Settings updated successfully", "updated_fields": updated_fields}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        frappe.log_error(title=_("Settings Update Error"), message=f"Error updating settings: {str(e)}")

        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def clear_cache() -> Dict[str, Any]:
    """
    Clear assistant system caches.

    Returns:
        Cache clearing operation result
    """
    frappe.only_for("System Manager")

    try:
        # Clear tool registry cache
        registry = get_tool_registry()
        if hasattr(registry, "clear_cache"):
            registry.clear_cache()

        # Clear plugin manager cache
        plugin_manager = get_plugin_manager()
        if hasattr(plugin_manager, "clear_cache"):
            plugin_manager.clear_cache()

        # Clear Frappe cache for assistant-related keys
        cache_keys = ["assistant_tools", "assistant_plugins", "assistant_metrics", "plugin_config"]

        for key in cache_keys:
            frappe.cache().delete_key(key)

        # Log the action
        frappe.logger("admin").info(f"Assistant caches cleared by {frappe.session.user}")

        return {
            "success": True,
            "message": "Caches cleared successfully",
            "cleared_caches": ["tool_registry", "plugin_manager", "frappe_cache_keys"],
        }

    except Exception as e:
        frappe.log_error(title=_("Cache Clear Error"), message=f"Error clearing caches: {str(e)}")

        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def export_configuration() -> Dict[str, Any]:
    """
    Export system configuration for backup or migration.

    Returns:
        Exported configuration data
    """
    frappe.only_for("System Manager")

    try:
        # Get current settings
        settings = frappe.get_single("Assistant Core Settings")

        # Get plugin configurations
        plugin_configs = frappe.get_all(
            "Assistant Plugin Config",
            fields=["plugin_name", "enabled", "configuration"],
            filters={"parent": settings.name},
        )

        # Get tool registry state
        registry = get_tool_registry()
        tools = registry.get_available_tools()

        # Get plugin manager state
        plugin_manager = get_plugin_manager()
        plugins = plugin_manager.get_discovered_plugins()

        config_export = {
            "export_info": {
                "exported_at": frappe.utils.now(),
                "exported_by": frappe.session.user,
                "app_version": frappe.get_app_version("frappe_assistant_core") or "1.0.0",
            },
            "system_settings": {
                "enable_assistant": settings.enable_assistant,
                "max_request_size": settings.max_request_size,
                "request_timeout": settings.request_timeout,
                "cache_enabled": settings.cache_enabled,
                "cache_ttl": settings.cache_ttl,
                "log_level": settings.log_level,
            },
            "plugin_configurations": plugin_configs,
            "available_tools": [
                {"name": t.name, "type": "core" if not hasattr(t, "plugin_name") else "plugin"} for t in tools
            ],
            "discovered_plugins": [
                {"name": p.get("name"), "status": p.get("status", "unknown")} for p in plugins
            ],
        }

        return {"success": True, "configuration": config_export}

    except Exception as e:
        frappe.log_error(
            title=_("Configuration Export Error"), message=f"Error exporting configuration: {str(e)}"
        )

        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def import_configuration(config_data: str) -> Dict[str, Any]:
    """
    Import system configuration from backup.

    Args:
        config_data: JSON string with configuration to import

    Returns:
        Import operation result
    """
    frappe.only_for("System Manager")

    try:
        # Parse configuration data
        config = json.loads(config_data)

        # Validate configuration structure
        required_keys = ["export_info", "system_settings"]
        for key in required_keys:
            if key not in config:
                return {"success": False, "error": f"Missing required configuration key: {key}"}

        # Get current settings document
        settings = frappe.get_single("Assistant Core Settings")

        # Update system settings
        system_settings = config["system_settings"]
        for field, value in system_settings.items():
            if hasattr(settings, field):
                setattr(settings, field, value)

        settings.save()

        # Update plugin configurations if provided
        if "plugin_configurations" in config:
            # Clear existing plugin configs
            frappe.db.delete("Assistant Plugin Config", {"parent": settings.name})

            # Import new plugin configs
            for plugin_config in config["plugin_configurations"]:
                frappe.get_doc(
                    {
                        "doctype": "Assistant Plugin Config",
                        "parent": settings.name,
                        "parenttype": "Assistant Core Settings",
                        "parentfield": "plugin_configurations",
                        "plugin_name": plugin_config["plugin_name"],
                        "enabled": plugin_config["enabled"],
                        "configuration": plugin_config.get("configuration", "{}"),
                    }
                ).insert()

        # Log the import
        export_info = config["export_info"]
        frappe.logger("admin").info(
            f"Configuration imported by {frappe.session.user} from export created by {export_info.get('exported_by')} at {export_info.get('exported_at')}"
        )

        return {
            "success": True,
            "message": "Configuration imported successfully",
            "import_info": {
                "original_export": export_info,
                "imported_at": frappe.utils.now(),
                "imported_by": frappe.session.user,
            },
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        frappe.log_error(
            title=_("Configuration Import Error"), message=f"Error importing configuration: {str(e)}"
        )

        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def run_diagnostics() -> Dict[str, Any]:
    """
    Run comprehensive system diagnostics.

    Returns:
        Diagnostic results and recommendations
    """
    frappe.only_for("System Manager")

    try:
        diagnostics = {
            "success": True,
            "diagnostics": {
                "timestamp": frappe.utils.now(),
                "system_health": "healthy",
                "issues": [],
                "warnings": [],
                "recommendations": [],
            },
        }

        # Check tool registry health
        try:
            registry = get_tool_registry()
            tools = registry.get_available_tools()

            if len(tools) == 0:
                diagnostics["diagnostics"]["issues"].append("No tools available in registry")
                diagnostics["diagnostics"]["system_health"] = "degraded"
            elif len(tools) < 5:
                diagnostics["diagnostics"]["warnings"].append("Low number of available tools")

        except Exception as e:
            diagnostics["diagnostics"]["issues"].append(f"Tool registry error: {str(e)}")
            diagnostics["diagnostics"]["system_health"] = "unhealthy"

        # Check plugin system health
        try:
            plugin_manager = get_plugin_manager()
            plugins = plugin_manager.get_discovered_plugins()

            if len(plugins) == 0:
                diagnostics["diagnostics"]["warnings"].append("No plugins discovered")

            # Check for plugin validation failures
            for plugin in plugins:
                if not plugin.get("can_enable", False):
                    diagnostics["diagnostics"]["warnings"].append(
                        f"Plugin '{plugin.get('name')}' cannot be enabled"
                    )

        except Exception as e:
            diagnostics["diagnostics"]["issues"].append(f"Plugin system error: {str(e)}")
            diagnostics["diagnostics"]["system_health"] = "unhealthy"

        # Check settings
        try:
            settings = frappe.get_single("Assistant Core Settings")

            if not settings.enable_assistant:
                diagnostics["diagnostics"]["warnings"].append("Assistant system is disabled")

            if settings.request_timeout < 30:
                diagnostics["diagnostics"]["recommendations"].append(
                    "Consider increasing request timeout for complex operations"
                )

        except Exception as e:
            diagnostics["diagnostics"]["issues"].append(f"Settings error: {str(e)}")

        # Check recent errors
        try:
            recent_errors = frappe.get_all(
                "Error Log",
                filters={
                    "error": ["like", "%assistant%"],
                    "creation": [">", frappe.utils.add_days(frappe.utils.now(), -1)],
                },
                limit=5,
            )

            if len(recent_errors) > 10:
                diagnostics["diagnostics"]["warnings"].append("High error rate in last 24 hours")

        except Exception:
            pass  # Error log checking is not critical

        # Set overall health status
        if len(diagnostics["diagnostics"]["issues"]) > 0:
            diagnostics["diagnostics"]["system_health"] = "unhealthy"
        elif len(diagnostics["diagnostics"]["warnings"]) > 2:
            diagnostics["diagnostics"]["system_health"] = "degraded"

        return diagnostics

    except Exception as e:
        frappe.log_error(title=_("Diagnostics Error"), message=f"Error running diagnostics: {str(e)}")

        return {"success": False, "error": str(e)}
