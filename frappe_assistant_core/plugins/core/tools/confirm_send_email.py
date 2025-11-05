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
Confirm Send Email Tool for Core Plugin.
Sends a Communication draft that was created by send_email tool.
"""

from typing import Any, Dict
import frappe
from frappe import _

from frappe_assistant_core.core.base_tool import BaseTool


class ConfirmSendEmail(BaseTool):
	"""
	Tool for sending an email draft created by send_email tool.

	Use this tool after send_email returns a preview and user confirms they want to send.
	Can optionally modify the email before sending (subject, message, recipients).
	"""

	def __init__(self):
		super().__init__()
		self.name = "confirm_send_email"
		self.description = """Confirme et envoie un brouillon d'email créé par send_email.

⚠️ IMPORTANT - UTILISATION AUTOMATIQUE:
Ce tool DOIT être appelé AUTOMATIQUEMENT quand:
1. send_email a retourné un brouillon (sent=false, communication_id=xxx, awaiting_confirmation=true)
2. Vous avez montré l'aperçu à l'utilisateur
3. L'utilisateur CONFIRME avec: "oui", "yes", "ok", "envoie", "send", "confirme", "d'accord", etc.

🔄 WORKFLOW TYPIQUE:
1. send_email(..., send_now=false) → retourne {"communication_id": "COMM-001", "awaiting_confirmation": true}
2. Vous montrez le preview et demandez confirmation
3. User: "oui" (ou any confirmation word)
4. Vous: → IMMÉDIATEMENT appeler confirm_send_email(communication_id="COMM-001")
   ❌ NE PAS juste répondre "D'accord, je vais l'envoyer!" - APPELER LE TOOL!

📝 PARAMÈTRES:
- communication_id (REQUIS): L'ID retourné par send_email (ex: "COMM-2025-10-28-001")
  → Vous AVEZ DÉJÀ cet ID dans la réponse précédente de send_email!
  → Il est dans response["communication_id"]
  → NE PAS demander à l'utilisateur de le fournir!
- modifications (OPTIONNEL): Modifications avant envoi (subject, content, recipients, cc, bcc)

✅ EXEMPLE CORRECT:
```
User: "Envoie email à Paul pour la réunion"
Agent: send_email(recipient="Paul", message="...", send_now=false)
Tool: {"communication_id": "xyz123", "preview": "...", "awaiting_confirmation": true}
Agent: "Voici l'aperçu:\n[preview]\n\nVoulez-vous l'envoyer?"
User: "oui"
Agent: confirm_send_email(communication_id="xyz123")  ← AUTOMATIQUE! IMMÉDIAT!
Tool: {"success": true, "sent": true}
Agent: "✅ Email envoyé avec succès!"
```

❌ EXEMPLE INCORRECT:
```
User: "oui"
Agent: "D'accord, je vais envoyer l'email!"  ← MAUVAIS - pas de tool call!
```

⚡ MOTS DE CONFIRMATION RECONNUS:
Français: oui, ouais, ok, d'accord, vas-y, envoie, confirme, go
Anglais: yes, yeah, okay, send, confirm, go ahead, sure"""
		self.requires_permission = "Email"

		self.inputSchema = {
			"type": "object",
			"properties": {
				"communication_id": {
					"type": "string",
					"description": "The Communication document ID returned by send_email tool (e.g., 'COMM-0001')"
				},
				"modifications": {
					"type": "object",
					"description": "Optional modifications to make before sending. Can include: subject, content, recipients, cc, bcc",
					"properties": {
						"subject": {
							"type": "string",
							"description": "New subject line"
						},
						"content": {
							"type": "string",
							"description": "New message content"
						},
						"recipients": {
							"type": "string",
							"description": "New recipients (email addresses)"
						},
						"cc": {
							"type": "string",
							"description": "New CC recipients"
						},
						"bcc": {
							"type": "string",
							"description": "New BCC recipients"
						}
					}
				}
			},
			"required": ["communication_id"]
		}

	def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
		"""Send the email draft"""
		communication_id = arguments.get("communication_id")
		modifications = arguments.get("modifications", {})

		try:
			# Get the Communication document
			if not frappe.db.exists("Communication", communication_id):
				return {
					"success": False,
					"error": f"Communication '{communication_id}' not found",
					"suggestion": "Use send_email tool to create a new email draft"
				}

			comm = frappe.get_doc("Communication", communication_id)

			# Check if already sent
			if comm.email_status in ["Sent", "Delivered"]:
				return {
					"success": False,
					"error": f"Email {communication_id} was already sent",
					"sent_at": str(comm.modified),
					"recipient": comm.recipients
				}

			# Apply modifications if provided
			if modifications:
				if "subject" in modifications:
					comm.subject = modifications["subject"]
				if "content" in modifications:
					comm.content = modifications["content"]
				if "recipients" in modifications:
					comm.recipients = modifications["recipients"]
				if "cc" in modifications:
					comm.cc = modifications["cc"]
				if "bcc" in modifications:
					comm.bcc = modifications["bcc"]

				comm.save()

			# Get attachments from Communication if any
			attachments_list = []
			if comm.has_attachment:
				frappe.logger("confirm_send_email").info(
					f"📎 Loading attachments for Communication {comm.name}"
				)
				attached_files = frappe.get_all(
					"File",
					filters={
						"attached_to_doctype": "Communication",
						"attached_to_name": comm.name
					},
					fields=["name", "file_name"]
				)
				# Format attachments as dicts with 'fid' key (required by frappe.sendmail)
				attachments_list = [{"fid": f.name} for f in attached_files]
				frappe.logger("confirm_send_email").info(
					f"📎 Found {len(attachments_list)} attachment(s): {[f['file_name'] for f in attached_files]}"
				)

			# Send the email
			frappe.sendmail(
				recipients=comm.recipients,
				cc=comm.cc if comm.cc else None,
				bcc=comm.bcc if comm.bcc else None,
				subject=comm.subject,
				message=comm.content,
				attachments=attachments_list if attachments_list else None,
				reference_doctype="Communication",
				reference_name=comm.name,
				now=True
			)

			# Update communication status
			comm.email_status = "Sent"
			comm.delivery_status = "Sent"
			comm.status = "Linked"
			comm.db_update()
			frappe.db.commit()

			return {
				"success": True,
				"communication_id": comm.name,
				"sent": True,
				"recipient": comm.recipients,
				"cc": comm.cc if comm.cc else None,
				"subject": comm.subject,
				"message": f"✅ Email sent successfully to {comm.recipients}",
				"sent_at": str(frappe.utils.now())
			}

		except Exception as e:
			frappe.log_error(
				title=_("Confirm Send Email Error"),
				message=f"Error sending email {communication_id}: {str(e)}"
			)

			error_msg = str(e)

			# Provide specific guidance based on error type
			result = {
				"success": False,
				"communication_id": communication_id,
				"error": error_msg
			}

			if "smtp" in error_msg.lower() or "mail" in error_msg.lower():
				result.update({
					"error_type": "smtp_configuration_error",
					"guidance": "Email server (SMTP) not configured properly.",
					"suggestion": "Contact system administrator to configure email settings in Frappe"
				})
			elif "permission" in error_msg.lower():
				result.update({
					"error_type": "permission_error",
					"guidance": "Insufficient permissions to send emails.",
					"suggestion": "Contact system administrator to grant email sending permissions"
				})
			elif "recipient" in error_msg.lower() or "email" in error_msg.lower():
				result.update({
					"error_type": "recipient_error",
					"guidance": "Invalid recipient email address.",
					"suggestion": "Verify the recipient email address is valid and try again"
				})
			else:
				result.update({
					"error_type": "general_error",
					"guidance": "Email sending failed due to system error.",
					"suggestion": "Check system logs or try again later"
				})

			return result


# Make sure class name matches file name for discovery
confirm_send_email = ConfirmSendEmail
