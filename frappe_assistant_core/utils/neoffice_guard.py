# //// Neoffice — added file (no upstream equivalent).
# //// Upstream's FAC endpoints (chat/, plugins/faco/, the admin and utility helpers) answer ANY signed-in account:
# //// a Website User (a portal customer, no desk role) with a session or an API key could open chat sessions and
# //// create projects on a site where chat is switched off, read the day's tool usage, the health check (which
# //// names the database) and the prompt library. Neoffice keeps all of it for desk users: this auth hook refuses a
# //// Website User on every whitelisted method of the app except the MCP endpoint (api/fac_endpoint.handle_mcp,
# //// which authenticates and checks `assistant_enabled` itself) and the methods upstream declares guest-callable
# //// (discovery, OAuth, can_use_faco). Remove it when upstream gates those endpoints on the user type.
"""auth hook: FAC endpoints other than the MCP endpoint are for desk users only."""

import re

import frappe
from frappe import _

_FAC_METHOD = re.compile(r"^/api/(?:v\d+/)?method/(frappe_assistant_core\.[\w.]+)$")

# The one endpoint a non-desk account may use: it does its own authentication and checks.
_OPEN_METHODS = {"frappe_assistant_core.api.fac_endpoint.handle_mcp"}


def refuse_website_users_on_fac_endpoints():
    """Raise PermissionError when a non-desk account calls a FAC method that is not guest-callable."""
    request = getattr(frappe.local, "request", None)
    if not request:
        return

    match = _FAC_METHOD.match(request.path or "")
    if not match or match.group(1) in _OPEN_METHODS:
        return

    user = frappe.session.user
    if user == "Guest":
        # Guests are handled by Frappe's own allow_guest check on each method.
        return

    if frappe.get_cached_value("User", user, "user_type") == "System User":
        return

    try:
        method = frappe.get_attr(match.group(1))
    except Exception:
        # Not a method: Frappe answers 404 / 417 by itself.
        return
    if method in frappe.guest_methods:
        # Upstream declared it callable by anyone (discovery, OAuth callback, can_use_faco).
        return

    frappe.throw(_("This function is only available to desk users."), frappe.PermissionError)
