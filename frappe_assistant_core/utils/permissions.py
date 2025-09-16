# -*- coding: utf-8 -*-
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

from frappe import get_doc, has_permission
import json
import frappe
from frappe import _

def check_tool_permissions(tool_name: str, user: str) -> bool:
    """Check if the user has permissions to access the specified tool."""
    tool = get_doc("assistant Tool Registry", tool_name)
    
    if not tool.enabled:
        return False
    
    required_permissions = json.loads(tool.required_permissions or "[]")
    
    for perm in required_permissions:
        if isinstance(perm, dict):
            doctype = perm.get("doctype")
            permission_type = perm.get("permission", "read")
            if not has_permission(doctype, permission_type, user=user):
                return False
        elif isinstance(perm, str):
            if perm not in get_roles(user):
                return False
    
    return True

def get_roles(user: str) -> list:
    """Retrieve roles for the specified user."""
    return [role.role for role in get_doc("User", user).roles] if user else []

# NOTE: get_permission_query_conditions function removed as Assistant Connection Log no longer exists

def get_audit_permission_query_conditions(user=None):
    """Permission query conditions for assistant Audit Log"""
    if not user:
        user = frappe.session.user
    
    # System Manager and assistant Admin can see all audit logs
    if "System Manager" in frappe.get_roles(user) or "assistant Admin" in frappe.get_roles(user):
        return ""
    
    # assistant Users can only see their own audit logs
    if "assistant User" in frappe.get_roles(user):
        return f"`tabassistant Audit Log`.user = '{user}'"
    
    # No access for others
    return "1=0"

def check_assistant_permission(user=None):
    """Check if user has assistant access permission"""
    if not user:
        user = frappe.session.user
    
    user_roles = frappe.get_roles(user)
    assistant_roles = ["System Manager", "Assistant Admin", "Assistant User"]
    
    return any(role in user_roles for role in assistant_roles)