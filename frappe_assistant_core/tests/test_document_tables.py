# //// Neoffice — added file (no upstream equivalent). Tests for the table handling of
# //// update_document and for the required-field check of create_document (maintenance#1366).
# Same licence as the rest of the project (GNU AGPL v3).

"""
Tests for the tables of update_document and the required fields of create_document.

update_document used to put the rows it was given into the document as plain dicts, and the save
failed with "'dict' object has no attribute 'is_new'": no table could be updated through the tool.
create_document used to compare the DocType's required fields with what the caller sent before the
document had a chance to fill the ones it computes itself.
"""

import frappe

from frappe_assistant_core.core.tool_registry import get_tool_registry
from frappe_assistant_core.plugins.core.tools.create_document import (
    complete_document,
    missing_required_fields,
)
from frappe_assistant_core.tests.base_test import BaseAssistantTest

TEST_PREFIX = "Zz Assistant Tables"


class TestUpdateDocumentTables(BaseAssistantTest):
    """A table is updated through update_document the way a form saves it."""

    def setUp(self):
        super().setUp()
        self.registry = get_tool_registry()
        if not self.registry.has_tool("update_document"):
            self.skipTest("update_document tool not available")
        self.contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": f"{TEST_PREFIX} {frappe.generate_hash(length=6)}",
                "email_ids": [
                    {"email_id": "first@example.com", "is_primary": 1},
                    {"email_id": "second@example.com", "is_primary": 0},
                ],
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        frappe.delete_doc("Contact", self.contact.name, force=1, ignore_permissions=True)
        frappe.db.commit()
        super().tearDown()

    def _update(self, data):
        return self.registry.execute_tool(
            "update_document", {"doctype": "Contact", "name": self.contact.name, "data": data}
        )

    def _rows(self):
        contact = frappe.get_doc("Contact", self.contact.name)
        return [(row.idx, row.email_id, row.is_primary) for row in contact.email_ids]

    def test_a_list_of_rows_without_names_replaces_the_table(self):
        result = self._update(
            {"email_ids": [{"email_id": "new-a@example.com"}, {"email_id": "new-b@example.com"}]}
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual(
            [(idx, email) for idx, email, _ in self._rows()],
            [(1, "new-a@example.com"), (2, "new-b@example.com")],
        )

    def test_a_row_that_names_an_existing_row_keeps_the_fields_it_does_not_cite(self):
        first = self.contact.email_ids[0].name

        result = self._update({"email_ids": [{"name": first, "email_id": "changed@example.com"}]})

        self.assertTrue(result.get("success"), result)
        self.assertEqual(self._rows(), [(1, "changed@example.com", 1)])

    def test_rows_that_are_not_listed_are_removed(self):
        second = self.contact.email_ids[1].name

        result = self._update({"email_ids": [{"name": second}]})

        self.assertTrue(result.get("success"), result)
        # Contact makes the first address primary when none is: only the address and its number are ours
        self.assertEqual([(idx, email) for idx, email, _ in self._rows()], [(1, "second@example.com")])

    def test_the_order_of_the_list_is_the_order_of_the_rows(self):
        first, second = (row.name for row in self.contact.email_ids)

        result = self._update({"email_ids": [{"name": second}, {"name": first}]})

        self.assertTrue(result.get("success"), result)
        self.assertEqual(
            self._rows(),
            [(1, "second@example.com", 0), (2, "first@example.com", 1)],
        )

    def test_a_new_row_can_be_added_between_existing_ones(self):
        first, second = (row.name for row in self.contact.email_ids)

        result = self._update(
            {"email_ids": [{"name": first}, {"email_id": "between@example.com"}, {"name": second}]}
        )

        self.assertTrue(result.get("success"), result)
        self.assertEqual(
            [(idx, email) for idx, email, _ in self._rows()],
            [(1, "first@example.com"), (2, "between@example.com"), (3, "second@example.com")],
        )

    def test_a_name_that_matches_no_row_is_refused_and_nothing_changes(self):
        before = self._rows()

        result = self._update({"email_ids": [{"name": "no-such-row", "email_id": "x@example.com"}]})

        self.assertFalse(result.get("success"))
        self.assertIn("no-such-row", result.get("error", ""))
        self.assertEqual(self._rows(), before)

    def test_a_table_that_is_not_a_list_of_objects_is_refused(self):
        before = self._rows()

        result = self._update({"email_ids": "first@example.com"})

        self.assertFalse(result.get("success"))
        self.assertEqual(self._rows(), before)

    def test_a_plain_field_still_updates_and_leaves_the_tables_alone(self):
        before = self._rows()

        result = self._update({"last_name": "Updated"})

        self.assertTrue(result.get("success"), result)
        self.assertEqual(frappe.db.get_value("Contact", self.contact.name, "last_name"), "Updated")
        self.assertEqual(self._rows(), before)


class _FakeDocument:
    """Just enough of a Frappe document for the required-field helpers."""

    def __init__(self, missing, filled_by_completion=(), completion_error=None, children=()):
        self.missing = list(missing)
        self.filled_by_completion = set(filled_by_completion)
        self.completion_error = completion_error
        self.children = list(children)
        self.methods_run = []

    def run_method(self, method):
        self.methods_run.append(method)
        if self.completion_error:
            raise self.completion_error
        self.missing = [name for name in self.missing if name not in self.filled_by_completion]

    def _get_missing_mandatory_fields(self):
        return [(name, f"Value missing for {name}") for name in self.missing]

    def get_all_children(self):
        return self.children


class TestRequiredFieldsOfCreateDocument(BaseAssistantTest):
    """Frappe is asked to fill what it computes before a field is called missing."""

    def test_the_document_is_asked_to_complete_itself(self):
        document = _FakeDocument(["conversion_rate"], filled_by_completion=["conversion_rate"])

        self.assertTrue(complete_document(document))
        self.assertEqual(document.methods_run, ["set_missing_values"])
        self.assertEqual(missing_required_fields(document), [])

    def test_a_field_the_document_cannot_fill_is_still_reported(self):
        document = _FakeDocument(["customer", "conversion_rate"], filled_by_completion=["conversion_rate"])

        complete_document(document)

        self.assertEqual(missing_required_fields(document), ["customer"])

    def test_a_document_that_cannot_complete_itself_does_not_stop_the_tool(self):
        document = _FakeDocument(["conversion_rate"], completion_error=frappe.DoesNotExistError("Item X"))

        self.assertFalse(complete_document(document))

    def test_the_fields_missing_in_the_rows_are_reported_too(self):
        row = _FakeDocument(["qty"])
        document = _FakeDocument(["customer"], children=[row])

        self.assertEqual(missing_required_fields(document), ["customer", "qty"])

    def test_a_field_reported_by_the_document_and_by_a_row_is_listed_once(self):
        row = _FakeDocument(["qty"])
        other_row = _FakeDocument(["qty"])
        document = _FakeDocument([], children=[row, other_row])

        self.assertEqual(missing_required_fields(document), ["qty"])


class TestCreateDocumentReportsWhatIsReallyMissing(BaseAssistantTest):
    """The answer keeps its shape when a required field is truly absent."""

    def test_a_price_list_without_its_name_is_refused_with_the_list_of_required_fields(self):
        registry = get_tool_registry()
        if not registry.has_tool("create_document"):
            self.skipTest("create_document tool not available")

        result = registry.execute_tool("create_document", {"doctype": "Price List", "data": {"selling": 1}})

        self.assertFalse(result.get("success"))
        self.assertIn("price_list_name", result.get("error", ""))
        self.assertIn("price_list_name", result.get("required_fields", []))
        self.assertEqual(result.get("provided_fields"), ["selling"])
        self.assertEqual(result.get("doctype"), "Price List")
