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
Send Email Tool for Core Plugin.
Creates email drafts with recipient search, message improvement, and preview.
"""

from typing import Any, Dict
import frappe
from frappe import _

from frappe_assistant_core.core.base_tool import BaseTool


class SendEmail(BaseTool):
	"""
	Tool for sending emails with smart recipient search and message improvement.

	Workflow:
	1. Search for recipient (User or Contact)
	2. Optionally improve message via LLM
	3. Create Communication draft
	4. Return preview for user confirmation
	5. Use confirm_send_email tool to actually send
	"""

	def __init__(self):
		super().__init__()
		self.name = "send_email"
		self.description = "Prepare and send emails to users or contacts. Automatically searches for recipients by name or email, improves message formatting, creates draft in Communication DocType, and returns preview for confirmation. Use send_now=false to get preview first (recommended), then use confirm_send_email to actually send. Supports auto-generating subjects and adding professional signatures."
		self.requires_permission = "Email"

		self.inputSchema = {
			"type": "object",
			"properties": {
				"recipient": {
					"type": "string",
					"description": "Recipient name (e.g., 'Jeremy', 'John Doe') or email address. Tool will search Users and Contacts to find the email."
				},
				"subject": {
					"type": "string",
					"description": "Email subject line. If not provided, will be auto-generated from message content."
				},
				"message": {
					"type": "string",
					"description": "Email message body. Can be informal - tool will improve formatting and add greetings/signature if improve_message=true."
				},
				"send_now": {
					"type": "boolean",
					"default": False,
					"description": "If true, sends email immediately. If false (recommended), creates draft and returns preview for user confirmation. Use confirm_send_email tool to send after user approves."
				},
				"improve_message": {
					"type": "boolean",
					"default": True,
					"description": "If true, improves message with proper greetings, formatting, and professional signature. If false, uses message as-is."
				},
				"cc": {
					"type": "string",
					"description": "Optional CC recipients (comma-separated emails or names)."
				},
				"bcc": {
					"type": "string",
					"description": "Optional BCC recipients (comma-separated emails or names)."
				}
			},
			"required": ["recipient", "message"]
		}

	def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
		"""Prepare and optionally send an email"""
		recipient = arguments.get("recipient")
		subject = arguments.get("subject")
		message = arguments.get("message")
		send_now = arguments.get("send_now", False)
		improve_message = arguments.get("improve_message", True)
		cc = arguments.get("cc")
		bcc = arguments.get("bcc")

		try:
			# Step 1: Find recipient email
			recipient_email = self._find_recipient(recipient)
			if not recipient_email:
				return {
					"success": False,
					"error": f"Could not find recipient '{recipient}' in Users or Contacts",
					"suggestion": "Try using full name or email address directly, or use search_link tool to find the contact first"
				}

			# Step 2: Find CC/BCC emails if provided
			cc_emails = self._parse_recipients(cc) if cc else []
			bcc_emails = self._parse_recipients(bcc) if bcc else []

			# Step 3: Improve message if requested
			if improve_message:
				improved_message = self._improve_message(message, recipient)
				improved_subject = subject or self._generate_subject(message)
			else:
				improved_message = message
				improved_subject = subject or "Message from NORA Assistant"

			# Step 4: Get sender info
			sender_email = frappe.session.user
			sender_name = frappe.db.get_value("User", sender_email, "full_name") or sender_email

			# Step 5: Create Communication draft
			comm = frappe.new_doc("Communication")
			comm.communication_type = "Communication"
			comm.communication_medium = "Email"
			comm.sent_or_received = "Sent"
			comm.subject = improved_subject
			comm.content = improved_message
			comm.sender = sender_email
			comm.sender_full_name = sender_name
			comm.recipients = recipient_email

			if cc_emails:
				comm.cc = ", ".join(cc_emails)
			if bcc_emails:
				comm.bcc = ", ".join(bcc_emails)

			# Don't set email_status yet - it will be set when actually sent
			comm.status = "Open"

			comm.insert()

			# Step 6: Generate preview with communication_id
			preview_markdown = self._generate_preview(
				recipient_email,
				improved_subject,
				improved_message,
				cc_emails,
				bcc_emails,
				sender_name,
				comm.name  # Pass communication_id to preview
			)

			# Step 7: Send now if requested
			if send_now:
				send_result = self._send_communication(comm.name)
				if send_result["success"]:
					return {
						"success": True,
						"communication_id": comm.name,
						"recipient": recipient_email,
						"subject": improved_subject,
						"sent": True,
						"message": f"Email sent to {recipient_email}",
						"preview": preview_markdown
					}
				else:
					return {
						"success": False,
						"communication_id": comm.name,
						"error": f"Draft created but send failed: {send_result.get('error')}",
						"preview": preview_markdown,
						"next_step": "Use confirm_send_email tool to retry sending"
					}

			# Return draft for confirmation
			return {
				"success": True,
				"communication_id": comm.name,
				"recipient": recipient_email,
				"subject": improved_subject,
				"sent": False,
				"preview": preview_markdown,
				"message": "Email draft created. Show preview to user and ask for confirmation.",
				"next_step": f"Use confirm_send_email tool with communication_id='{comm.name}' to send after user approves"
			}

		except Exception as e:
			frappe.log_error(
				title=_("Send Email Error"),
				message=f"Error preparing email: {str(e)}"
			)
			return {
				"success": False,
				"error": str(e),
				"error_type": "email_preparation_error"
			}

	def _find_recipient(self, recipient: str) -> str:
		"""
		Find recipient email from name or email string.
		Searches Users first, then Contacts.
		"""
		# If it looks like an email, validate and return
		if "@" in recipient:
			# Basic email validation
			if "." in recipient.split("@")[1]:
				return recipient.strip()

		# Search in Users
		users = frappe.get_all(
			"User",
			filters={"enabled": 1},
			fields=["name", "email", "full_name"],
			or_filters=[
				{"full_name": ["like", f"%{recipient}%"]},
				{"email": ["like", f"%{recipient}%"]},
				{"name": ["like", f"%{recipient}%"]}
			],
			limit=1
		)

		if users:
			return users[0].email or users[0].name

		# Search in Contacts
		contacts = frappe.get_all(
			"Contact",
			fields=["name", "email_id", "first_name", "last_name"],
			or_filters=[
				{"first_name": ["like", f"%{recipient}%"]},
				{"last_name": ["like", f"%{recipient}%"]},
				{"email_id": ["like", f"%{recipient}%"]},
				{"name": ["like", f"%{recipient}%"]}
			],
			limit=1
		)

		if contacts:
			return contacts[0].email_id

		return None

	def _parse_recipients(self, recipients_string: str) -> list:
		"""Parse comma-separated recipients and find their emails"""
		if not recipients_string:
			return []

		recipients = [r.strip() for r in recipients_string.split(",")]
		emails = []

		for recipient in recipients:
			email = self._find_recipient(recipient)
			if email:
				emails.append(email)

		return emails

	def _improve_message(self, message: str, recipient: str) -> str:
		"""
		Improve message formatting to be professional but natural in French.
		Reformulates informal messages into proper sentences while keeping them concise.
		"""
		# Get recipient first name
		recipient_name = recipient.split()[0] if " " in recipient else recipient.split("@")[0]

		# Reformulate common informal patterns into professional French
		improved = message.strip()

		# Pattern: "venir demain à 18h" → "Je souhaiterais te voir demain à 18h."
		if improved.startswith(("venir", "viens")):
			improved = improved.replace("venir ", "")
			improved = improved.replace("viens ", "")
			improved = f"Je souhaiterais te voir {improved}."

		# Pattern: "appeler moi" → "Pourrais-tu m'appeler ?"
		elif "appel" in improved.lower() and "moi" in improved.lower():
			improved = "Pourrais-tu m'appeler ?"

		# Pattern: "envoyer document X" → "Peux-tu m'envoyer le document X ?"
		elif improved.startswith(("envoyer", "envoie")):
			improved = improved.replace("envoyer ", "")
			improved = improved.replace("envoie ", "")
			improved = f"Peux-tu m'envoyer {improved} ?"

		# Pattern: "réunion demain" → "Je te propose une réunion demain."
		elif "réunion" in improved.lower() and not improved.endswith(("?", ".", "!")):
			improved = f"Je te propose une {improved}."

		# Add proper punctuation if missing
		if not improved.endswith((".", "?", "!")):
			# If it's a question-like message
			if any(word in improved.lower() for word in ["peux", "pourrai", "veux", "souhaite", "possible"]):
				improved += " ?"
			else:
				improved += "."

		# Capitalize first letter
		if improved and improved[0].islower():
			improved = improved[0].upper() + improved[1:]

		# Add greeting if not present
		if not improved.lower().startswith(("bonjour", "hello", "hi", "salut", "coucou")):
			improved = f"Bonjour {recipient_name},\n\n{improved}"

		# Add closing if not present
		if not any(closing in improved.lower() for closing in ["cordialement", "bien à vous", "merci d'avance", "à bientôt", "regards"]):
			# Choose closing based on message tone
			if any(word in improved.lower() for word in ["urgent", "important", "rapidement"]):
				improved = f"{improved}\n\nMerci d'avance,"
			else:
				improved = f"{improved}\n\nCordialement,"

		# Add sender signature
		sender_name = frappe.db.get_value("User", frappe.session.user, "full_name") or "NORA Assistant"
		if sender_name not in improved:
			improved = f"{improved}\n{sender_name}"

		return improved

	def _generate_subject(self, message: str) -> str:
		"""Generate professional subject from message content"""
		# Clean message for subject extraction
		msg_lower = message.lower().strip()

		# Pattern-based subject generation for common cases
		if msg_lower.startswith(("venir", "viens")):
			return "Invitation pour demain"
		elif "réunion" in msg_lower:
			return "Proposition de réunion"
		elif "appel" in msg_lower:
			return "Demande d'appel"
		elif "envoyer" in msg_lower or "envoie" in msg_lower:
			return "Demande de document"
		elif "question" in msg_lower:
			return "Question"
		elif "urgent" in msg_lower:
			return "Message urgent"
		elif "rendez-vous" in msg_lower or "rdv" in msg_lower:
			return "Demande de rendez-vous"

		# Default: take first sentence or first 50 chars
		first_line = message.split("\n")[0].strip()

		# Remove common prefixes that don't work well in subjects
		for prefix in ["je ", "tu ", "il ", "elle ", "nous ", "vous ", "ils ", "elles "]:
			if first_line.lower().startswith(prefix):
				first_line = first_line[len(prefix):]
				break

		# Capitalize and limit length
		if first_line:
			first_line = first_line[0].upper() + first_line[1:] if len(first_line) > 1 else first_line.upper()
			if len(first_line) > 50:
				return first_line[:47] + "..."
			return first_line

		return "Message de NORA"

	def _generate_preview(self, recipient: str, subject: str, content: str, cc: list, bcc: list, sender: str, communication_id: str = None) -> str:
		"""Generate markdown preview of email"""
		preview = f"📧 **Aperçu de l'email**\n\n"
		preview += f"**De:** {sender}\n"
		preview += f"**À:** {recipient}\n"

		if cc:
			preview += f"**CC:** {', '.join(cc)}\n"
		if bcc:
			preview += f"**BCC:** {', '.join(bcc)}\n"

		preview += f"**Objet:** {subject}\n\n"
		preview += f"**Message:**\n\n"

		# Quote the message content
		for line in content.split("\n"):
			preview += f"> {line}\n"

		# CRITICAL: Include communication_id in preview for LLM to see
		if communication_id:
			preview += f"\n\n🆔 **ID:** `{communication_id}`\n"

		return preview

	def _send_communication(self, communication_id: str) -> Dict[str, Any]:
		"""Actually send the communication via frappe.sendmail"""
		try:
			comm = frappe.get_doc("Communication", communication_id)

			# Send via frappe.sendmail
			frappe.sendmail(
				recipients=comm.recipients,
				cc=comm.cc,
				bcc=comm.bcc,
				subject=comm.subject,
				message=comm.content,
				reference_doctype="Communication",
				reference_name=comm.name,
				send_email=True
			)

			# Update communication status
			comm.email_status = "Open"
			comm.db_update()
			frappe.db.commit()

			return {"success": True}

		except Exception as e:
			return {
				"success": False,
				"error": str(e)
			}


# Make sure class name matches file name for discovery
send_email = SendEmail
