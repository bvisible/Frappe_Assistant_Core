# //// Neoffice — added file (no upstream equivalent). Tests of utils/neoffice_guard.py (FAC endpoints other than the
# //// MCP one are for desk users only) and of the audit-statistics permission check.
"""A Website User reaches no FAC endpoint but the MCP one; a desk user and the guest-callable methods are untouched."""

from types import SimpleNamespace

import frappe

from frappe_assistant_core.tests.base_test import BaseAssistantTest
from frappe_assistant_core.utils.neoffice_guard import refuse_website_users_on_fac_endpoints

WEB_USER = "fac-guard-web@example.com"
STAFF_USER = "fac-guard-staff@example.com"
CHAT_PATH = "/api/method/frappe_assistant_core.chat.api.chat.sessions.create_session"
GUEST_CALLABLE_PATH = "/api/method/frappe_assistant_core.chat.api.settings.access.can_use_faco"
MCP_PATH = "/api/method/frappe_assistant_core.api.fac_endpoint.handle_mcp"
ADMIN_PATH = "/api/method/frappe_assistant_core.utils.dashboard.get_system_health_check"


def _make_user(email, user_type, roles):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    user = frappe.new_doc("User")
    user.email = email
    user.first_name = "FAC guard"
    user.user_type = user_type
    user.send_welcome_email = 0
    for role in roles:
        user.append("roles", {"role": role})
    user.insert(ignore_permissions=True)


class TestNeofficeGuard(BaseAssistantTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _make_user(WEB_USER, "Website User", [])
        _make_user(STAFF_USER, "System User", ["Assistant User"])

    def setUp(self):
        super().setUp()
        self._request = getattr(frappe.local, "request", None)
        self._user = frappe.session.user

    def tearDown(self):
        frappe.local.request = self._request
        frappe.set_user(self._user)
        super().tearDown()

    def _call(self, path, user):
        frappe.local.request = SimpleNamespace(path=path, method="POST")
        frappe.set_user(user)
        return refuse_website_users_on_fac_endpoints()

    def test_website_user_is_refused_on_a_chat_method(self):
        with self.assertRaises(frappe.PermissionError):
            self._call(CHAT_PATH, WEB_USER)

    def test_versioned_api_path_is_refused_too(self):
        with self.assertRaises(frappe.PermissionError):
            self._call(CHAT_PATH.replace("/api/method/", "/api/v2/method/"), WEB_USER)

    def test_website_user_is_refused_on_a_utility_method(self):
        with self.assertRaises(frappe.PermissionError):
            self._call(ADMIN_PATH, WEB_USER)

    def test_desk_user_passes(self):
        self.assertIsNone(self._call(CHAT_PATH, STAFF_USER))

    def test_guest_callable_method_passes_for_a_website_user(self):
        self.assertIsNone(self._call(GUEST_CALLABLE_PATH, WEB_USER))

    def test_mcp_endpoint_is_not_touched(self):
        self.assertIsNone(self._call(MCP_PATH, WEB_USER))

    def test_guest_is_left_to_frappe(self):
        self.assertIsNone(self._call(CHAT_PATH, "Guest"))

    def test_unrelated_path_passes(self):
        self.assertIsNone(self._call("/api/method/frappe.client.get_list", WEB_USER))

    def test_audit_statistics_refuses_a_website_user(self):
        from frappe_assistant_core.assistant_core.doctype.assistant_audit_log.assistant_audit_log import (
            get_audit_statistics,
        )

        frappe.set_user(WEB_USER)
        with self.assertRaises(frappe.PermissionError):
            get_audit_statistics()
