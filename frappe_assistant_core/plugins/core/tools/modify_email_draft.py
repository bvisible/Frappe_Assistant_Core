"""
Modify Email Draft Tool for Core Plugin.
Modifies an existing email draft (Communication) without sending it.
"""

from typing import Any, Dict
import frappe
from frappe import _

from frappe_assistant_core.core.base_tool import BaseTool


class ModifyEmailDraft(BaseTool):
	"""
	Tool to modify an existing email draft.

	This tool allows modifying the content and/or subject of an email draft
	that was previously created with send_email (send_now=false).

	The draft is NOT sent - only modified. Use confirm_send_email to send after.
	"""

	def __init__(self):
		super().__init__()
		self.name = "modify_email_draft"
		self.description = """Modifie un brouillon d'email existant SANS l'envoyer.

📝 UTILISATION:
  • Modifier le contenu d'un email draft créé avec send_email
  • Modifier le sujet d'un email draft
  • Afficher le nouvel aperçu après modification

⚠️ IMPORTANT - WORKFLOW:
  1. L'utilisateur a un draft créé (avec send_email, send_now=false)
  2. L'utilisateur demande "modifie le message pour dire X" ou "change l'objet"
  3. Tu DOIS utiliser modify_email_draft (PAS confirm_send_email avec modifications!)
  4. Après modification, afficher le nouvel aperçu
  5. Attendre confirmation de l'utilisateur pour envoyer avec confirm_send_email

❌ NE PAS FAIRE:
  • NE PAS utiliser confirm_send_email avec modifications pour modifier un email
  • NE PAS envoyer l'email après modification (attendre confirmation)

✅ FAIRE:
  • Utiliser modify_email_draft pour TOUTE modification de draft
  • Afficher le nouvel aperçu après modification
  • Demander "Voulez-vous envoyer cet email maintenant?"

💡 EXEMPLE WORKFLOW COMPLET:

User: "Envoie la facture 00004 au client"
You → call send_email(..., send_now=false)
Tool: {"communication_id": "abc123", "preview": "..."}
You: "📧 Email brouillon créé (ID: `abc123`).\n[preview]\nVoulez-vous l'envoyer?"

User: "modifie le message pour dire Bonjour Helie au lieu de Bonjour"
You → call modify_email_draft(
  communication_id="abc123",
  message="Bonjour Helie,\n\nVeuillez trouver ci-joint votre facture.\n\nCordialement,\nAdministrator"
)
Tool: {"success": true, "preview": "..."}
You: "✏️ Email modifié.\n[nouveau preview]\nVoulez-vous l'envoyer maintenant?"

User: "oui envoie"
You → call confirm_send_email(communication_id="abc123")
Tool: {"success": true, "sent": true}
You: "✅ Email envoyé avec succès!"

📋 PARAMÈTRES:
  • communication_id (required): L'ID du draft à modifier
  • message (optional): Le nouveau contenu de l'email
  • subject (optional): Le nouveau sujet de l'email
  • Au moins un des deux (message ou subject) doit être fourni
"""

		# Input schema
		self.inputSchema = {
			"type": "object",
			"properties": {
				"communication_id": {
					"type": "string",
					"description": "ID of the Communication draft to modify (returned by send_email)"
				},
				"message": {
					"type": "string",
					"description": "New email message content. Should include proper greeting (Bonjour) and closing (Cordialement)."
				},
				"subject": {
					"type": "string",
					"description": "New email subject (optional)"
				}
			},
			"required": ["communication_id"]
		}

	def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
		"""
		Modify an email draft.

		Args:
			arguments (dict): Tool arguments containing:
				communication_id (str): ID of the Communication to modify
				message (str, optional): New email content
				subject (str, optional): New email subject

		Returns:
			dict: Result with success status and new preview
		"""
		communication_id = arguments.get("communication_id")
		new_message = arguments.get("message")
		new_subject = arguments.get("subject")

		# Validate inputs
		if not communication_id:
			return {
				"success": False,
				"error": "communication_id is required"
			}

		if not new_message and not new_subject:
			return {
				"success": False,
				"error": "At least one of 'message' or 'subject' must be provided"
			}

		try:
			# Check if Communication exists
			if not frappe.db.exists("Communication", communication_id):
				return {
					"success": False,
					"error": f"Communication '{communication_id}' not found"
				}

			# Load Communication
			comm = frappe.get_doc("Communication", communication_id)

			# Check if it's a draft (not sent)
			if comm.sent_or_received == "Sent" and comm.get("email_status") == "Sent":
				return {
					"success": False,
					"error": "Cannot modify an already sent email. This Communication has already been sent."
				}

			# Apply modifications
			modified_fields = []

			if new_message:
				comm.content = new_message
				modified_fields.append("message")

			if new_subject:
				comm.subject = new_subject
				modified_fields.append("subject")

			# Save changes
			comm.save(ignore_permissions=True)
			frappe.db.commit()

			# Get sender name for preview
			sender_name = comm.sender_full_name or comm.sender or "Unknown"

			# Generate new preview
			preview = self._generate_preview(
				recipient=comm.recipients or "Unknown",
				subject=comm.subject,
				content=comm.content,
				cc=comm.cc.split(", ") if comm.cc else [],
				bcc=comm.bcc.split(", ") if comm.bcc else [],
				sender=sender_name
			)

			return {
				"success": True,
				"communication_id": communication_id,
				"modified_fields": modified_fields,
				"preview": preview,
				"message": f"✏️ Email draft modified successfully. The email has NOT been sent yet.",
				"next_step": f"Show the new preview to the user and ask for confirmation. When user confirms, call: confirm_send_email(communication_id='{communication_id}')"
			}

		except Exception as e:
			frappe.log_error(f"Error modifying email draft: {str(e)}", "Modify Email Draft")
			return {
				"success": False,
				"error": f"Failed to modify email draft: {str(e)}"
			}

	def _generate_preview(self, recipient: str, subject: str, content: str, cc: list, bcc: list, sender: str) -> str:
		"""Generate markdown preview of email"""
		preview = f"📧 **Aperçu de l'email (modifié)**\n\n"
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

		return preview
