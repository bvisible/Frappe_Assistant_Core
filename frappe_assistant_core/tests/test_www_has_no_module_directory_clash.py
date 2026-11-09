# //// Neoffice — added file (no upstream equivalent)
"""A www controller and a directory of the same name must not sit side by side (neoffice-maintenance#1853).

`www/copilot.py` and a directory `www/copilot/` with no `__init__.py` made `frappe_assistant_core.www.copilot`
resolve to the module, which is not a package: Frappe's website router imports every www controller to list the
pages of the site, so `/sitemap.xml` answered 500 on every site that runs this app.
"""

import os

import frappe
from frappe.website.router import get_pages_from_path

from frappe_assistant_core.tests.base_test import BaseAssistantTest

APP = "frappe_assistant_core"


class TestWwwHasNoModuleDirectoryClash(BaseAssistantTest):
    def test_no_www_module_has_a_directory_of_the_same_name(self):
        www = frappe.get_app_path(APP, "www")
        clashes = sorted(
            name
            for name in os.listdir(www)
            if name.endswith(".py") and os.path.isdir(os.path.join(www, name[: -len(".py")]))
        )
        self.assertEqual(clashes, [], "a module and a directory of the same name in www/: " + ", ".join(clashes))

    def test_the_website_router_lists_the_pages_of_the_app(self):
        # What /sitemap.xml does for this app: import the controller of every page of www/. It raised
        # ModuleNotFoundError ('frappe_assistant_core.www.copilot' is not a package) on the clash above.
        get_pages_from_path("www", APP, frappe.get_app_path(APP))
