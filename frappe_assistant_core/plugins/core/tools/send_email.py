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
		self.description = """Prépare et envoie des emails avec résolution intelligente du destinataire.

📧 PARAMÈTRE RECIPIENT (destinataire):
  • Email complet: "jeremy@example.com" → utilisé directement
  • Nom uniquement: "Jeremy" ou "John Doe" → recherche automatique dans Users et Contacts
  • Recherche dans les champs: full_name, first_name, last_name, email

🎯 GESTION AUTOMATIQUE DES CAS SPÉCIAUX:
  • 1 seul match trouvé → email créé automatiquement avec l'adresse trouvée
  • Plusieurs matches → retourne liste des correspondances, demande clarification
  • Aucun match exact → suggestions avec recherche floue (tolérance typos)
  • Exemple: "Jeremmy" (typo) → suggère "Jeremy (85% match)"

🔄 WORKFLOW COMPLET EN 5 ÉTAPES:
  1. Résout automatiquement le destinataire (nom → email via recherche)
  2. Améliore le message si improve_message=true (greeting, formatting, signature)
  3. Auto-génère le sujet si non fourni (analyse du contenu du message)
  4. Crée un brouillon Communication dans Frappe
  5. Retourne aperçu formaté pour confirmation utilisateur

⚠️ IMPORTANT - WORKFLOW DE CONFIRMATION:
  • send_email avec send_now=false → Crée brouillon et retourne communication_id
  • ❌ NE JAMAIS rappeler send_email pour confirmer!
  • ✅ TOUJOURS utiliser confirm_send_email(communication_id) pour envoyer le brouillon
  • Exemple: send_email(..., send_now=false) retourne {communication_id: "abc123"}
            → Ensuite: confirm_send_email(communication_id="abc123") pour envoyer

💡 EXEMPLES D'UTILISATION:

Exemple 1 - Nom simple (résolution automatique):
  send_email(
    recipient="Jeremy",  # Sera résolu automatiquement en jeremy@bvisible.ch
    subject="Réunion achats",
    message="Es-tu dispo demain pour discuter des achats?",
    send_now=false  # RECOMMANDÉ: crée brouillon, demande confirmation
  )

Exemple 2 - Email direct (pas de recherche):
  send_email(
    recipient="jeremy@example.com",  # Utilisé directement
    message="Urgent: projet en retard!",
    send_now=true,  # Envoie immédiatement SANS confirmation (à éviter)
    improve_message=false  # Garde le message tel quel, sans amélioration
  )

Exemple 3 - WORKFLOW CORRECT avec confirmation (TOUJOURS faire comme ça!):
  # Étape 1: Créer le brouillon
  result = send_email(
    recipient="Jeremy",
    subject="Réunion achats",
    message="Es-tu dispo demain?",
    send_now=false  # ← IMPORTANT: false pour créer brouillon
  )
  # result = {
  #   "success": true,
  #   "communication_id": "abc123xyz",
  #   "preview": "📧 Aperçu...",
  #   "next_step": "Use confirm_send_email tool..."
  # }

  # Étape 2: Montrer l'aperçu à l'utilisateur et demander confirmation
  # (l'agent affiche le preview et demande "Voulez-vous envoyer?")

  # Étape 3: ✅ UTILISER confirm_send_email (PAS send_email à nouveau!)
  confirm_send_email(communication_id="abc123xyz")  # ← BON
  # ❌ NE PAS FAIRE: send_email(..., send_now=true)  # ← MAUVAIS!

Exemple 4 - Avec CC/BCC:
  send_email(
    recipient="Jeremy",
    cc="Paul, Marie",  # Supporte noms OU emails séparés par virgule
    bcc="admin@company.com",
    message="Compte-rendu réunion...",
    send_now=false
  )

⚠️ GESTION DES AMBIGUÏTÉS:
  • Si 3 personnes nommées "Jeremy" trouvées:
    → Tool retourne: {"success": false, "matches": [...liste...]}
    → LLM demande: "J'ai trouvé 3 Jeremy: ..., lequel voulez-vous?"
  • L'utilisateur précise alors l'email exact ou le nom complet

⚠️ BONNES PRATIQUES:
  1. TOUJOURS utiliser send_now=false pour demander confirmation avant envoi
  2. Le système gère automatiquement les ambiguïtés et les typos
  3. Si incertain sur le destinataire, le tool demandera clarification
  4. Pour lister les utilisateurs disponibles: get_list('User', filters={'enabled': 1})
  5. Pour chercher une personne spécifique d'abord: search_link('User', 'jeremy')"""
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
			# Step 1: Enhanced recipient resolution
			recipient_result = self._find_recipient(recipient)

			# Case 1: Ambiguous - multiple people match
			if isinstance(recipient_result, dict) and recipient_result.get("ambiguous"):
				matches_list = "\n".join([
					f"  • {m['name']} ({m['email']})"
					for m in recipient_result["matches"]
				])

				return {
					"success": False,
					"error": f"Multiple people found matching '{recipient}'",
					"matches": recipient_result["matches"],
					"message": f"🤔 J'ai trouvé {len(recipient_result['matches'])} personnes nommées '{recipient}':\n\n{matches_list}\n\n💡 Veuillez préciser laquelle vous voulez contacter en utilisant:\n  • Le nom complet exact\n  • Ou l'adresse email directement",
					"next_step": "Specify exact email or full name to disambiguate"
				}

			# Case 2: Not found but fuzzy suggestions available
			if isinstance(recipient_result, dict) and recipient_result.get("not_found"):
				suggestions_list = "\n".join([
					f"  • {s['name']} ({s['email']}) - {s['similarity']}% match"
					for s in recipient_result["suggestions"]
				])

				return {
					"success": False,
					"error": f"No exact match for '{recipient}'",
					"suggestions": recipient_result["suggestions"],
					"message": f"❓ Aucune personne trouvée nommée exactement '{recipient}'.\n\n💡 Vouliez-vous dire:\n{suggestions_list}\n\nVous pouvez utiliser un des emails ci-dessus ou chercher la personne avec search_link('User', '{recipient}').",
					"next_step": "Use suggested email or search_link tool to find correct person"
				}

			# Case 3: Not found and no suggestions
			if not recipient_result:
				return {
					"success": False,
					"error": f"Could not find '{recipient}' in Users or Contacts",
					"message": f"❌ Aucun utilisateur ou contact trouvé pour '{recipient}'.\n\n💡 Suggestions:\n  1. Vérifiez l'orthographe du nom\n  2. Utilisez l'adresse email complète: jeremy@example.com\n  3. Ou cherchez d'abord la personne: search_link('User', '{recipient}')\n  4. Ou listez les utilisateurs: get_list('User', filters={{'enabled': 1}})",
					"next_step": "Provide email address or use search_link tool first"
				}

			# Case 4: Success - recipient_result is an email string
			recipient_email = recipient_result

			# Step 2: Find CC/BCC emails if provided
			cc_emails = self._parse_recipients(cc) if cc else []
			bcc_emails = self._parse_recipients(bcc) if bcc else []

			# Step 3: Improve message if requested
			if improve_message:
				# Use MCP improve_email tool for LLM-based improvement
				try:
					from frappe_assistant_core.core.tool_registry import get_tool_registry

					registry = get_tool_registry()

					# Extract recipient first name if available
					recipient_name = ""
					if recipient:
						try:
							recipient_name = (
								frappe.db.get_value("User", recipient, "first_name") or ""
							)
						except Exception:
							pass

					# Call improve_email_message tool via MCP
					result = registry.execute_tool(
						tool_name="improve_email_message",
						arguments={"message": message, "recipient_name": recipient_name},
					)

					if result.get("success"):
						improved_message = result["improved_message"]
						frappe.logger().info(
							f"[SEND_EMAIL] Message improved via MCP ({result.get('method', 'unknown')})"
						)
					else:
						# Fallback to old pattern-based method
						frappe.logger().warning(
							"[SEND_EMAIL] MCP improvement failed, using fallback"
						)
						improved_message = self._improve_message(message, recipient)

				except Exception as e:
					frappe.logger().error(
						f"[SEND_EMAIL] MCP improvement error: {str(e)}"
					)
					# Fallback to old pattern-based method
					improved_message = self._improve_message(message, recipient)

				improved_subject = subject or self._generate_subject(message)
			else:
				improved_message = message
				improved_subject = subject or "Message from NORA Assistant"

			# Step 4: Get sender info
			sender_email = frappe.session.user
			sender_name = self._get_sender_name(sender_email)

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

			# Step 6: Generate preview
			preview_markdown = self._generate_preview(
				recipient_email,
				improved_subject,
				improved_message,
				cc_emails,
				bcc_emails,
				sender_name
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
				"awaiting_confirmation": True,  # NEW: Indicates waiting for user confirmation
				"confirmation_prompt": "Voulez-vous envoyer cet email? (Répondez 'oui' pour confirmer)",  # NEW: Suggested prompt
				"next_action": {  # NEW: Structured next action for LLM
					"tool": "confirm_send_email",
					"parameters": {"communication_id": comm.name},
					"user_trigger_words": ["oui", "yes", "ok", "envoie", "send", "confirme", "d'accord", "ouais", "yeah", "okay", "go", "vas-y", "sure", "go ahead"]
				},
				"preview": preview_markdown,
				"message": f"📧 Email draft created (ID: {comm.name}). Awaiting user confirmation to send.",
				"next_step": f"When user confirms, call: confirm_send_email(communication_id='{comm.name}')",
				# CRITICAL: pending_email dict for deep_chat.py to save as System message
				"pending_email": {
					"communication_id": comm.name,
					"recipient": recipient_email,
					"subject": improved_subject
				}
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

	def _find_recipient(self, recipient: str):
		"""
		Enhanced recipient resolution with ambiguity detection and fuzzy search.

		Returns:
			str: Email address if single match found
			dict: Error/ambiguity info if multiple/no matches
			None: No match and no suggestions
		"""
		frappe.logger("send_email").info(f"🔍 Searching for recipient: '{recipient}'")

		# If it looks like an email, validate and return
		if "@" in recipient:
			# Basic email validation
			if "." in recipient.split("@")[1]:
				frappe.logger("send_email").info(f"✉️ Using email directly: {recipient}")
				return recipient.strip()

		# Search in Users (increased limit to detect ambiguity)
		users = frappe.get_all(
			"User",
			filters={"enabled": 1},
			fields=["name", "email", "full_name"],
			or_filters=[
				{"full_name": ["like", f"%{recipient}%"]},
				{"email": ["like", f"%{recipient}%"]},
				{"name": ["like", f"%{recipient}%"]}
			],
			limit=5  # Increased from 1 to detect multiple matches
		)

		frappe.logger("send_email").info(f"👤 User search: found {len(users)} match(es)")

		# Handle multiple matches - ask user to clarify
		if len(users) > 1:
			frappe.logger("send_email").warning(f"⚠️ Ambiguous: {len(users)} users match '{recipient}'")
			return {
				"ambiguous": True,
				"type": "User",
				"matches": [
					{"name": u.full_name, "email": u.email or u.name}
					for u in users
				]
			}

		# Single user match found
		if len(users) == 1:
			resolved_email = users[0].email or users[0].name
			frappe.logger("send_email").info(
				f"✅ Resolved '{recipient}' → '{resolved_email}' ({users[0].full_name})"
			)
			return resolved_email

		# Search in Contacts (same pattern)
		contacts = frappe.get_all(
			"Contact",
			fields=["name", "email_id", "first_name", "last_name"],
			or_filters=[
				{"first_name": ["like", f"%{recipient}%"]},
				{"last_name": ["like", f"%{recipient}%"]},
				{"email_id": ["like", f"%{recipient}%"]},
				{"name": ["like", f"%{recipient}%"]}
			],
			limit=5
		)

		frappe.logger("send_email").info(f"📇 Contact search: found {len(contacts)} match(es)")

		# Handle multiple contact matches
		if len(contacts) > 1:
			frappe.logger("send_email").warning(f"⚠️ Ambiguous: {len(contacts)} contacts match '{recipient}'")
			return {
				"ambiguous": True,
				"type": "Contact",
				"matches": [
					{
						"name": f"{c.first_name or ''} {c.last_name or ''}".strip() or c.name,
						"email": c.email_id
					}
					for c in contacts
				]
			}

		# Single contact match found
		if len(contacts) == 1:
			resolved_email = contacts[0].email_id
			contact_name = f"{contacts[0].first_name or ''} {contacts[0].last_name or ''}".strip() or contacts[0].name
			frappe.logger("send_email").info(
				f"✅ Resolved '{recipient}' → '{resolved_email}' ({contact_name})"
			)
			return resolved_email

		# No exact matches - try fuzzy search
		frappe.logger("send_email").info(f"🔎 No exact match, trying fuzzy search...")
		fuzzy_matches = self._fuzzy_search_recipients(recipient)

		if fuzzy_matches:
			frappe.logger("send_email").info(f"💡 Fuzzy search found {len(fuzzy_matches)} suggestions")
			return {
				"not_found": True,
				"suggestions": fuzzy_matches
			}

		# Absolutely no matches found
		frappe.logger("send_email").warning(f"❌ No recipient found for '{recipient}'")
		return None

	def _fuzzy_search_recipients(self, query: str) -> list:
		"""
		Fuzzy search for recipients using difflib for typo tolerance.

		Args:
			query: Name to search for (e.g., "Jeremmy" with typo)

		Returns:
			list: Top 3 suggestions with similarity scores
				[{"name": "Jeremy", "email": "jeremy@...", "similarity": 85}, ...]
		"""
		import difflib

		frappe.logger("send_email").info(f"🔎 Fuzzy search starting for: '{query}'")

		# Get all enabled users
		all_users = frappe.get_all(
			"User",
			filters={"enabled": 1},
			fields=["email", "full_name", "name"]
		)

		# Calculate similarity scores
		matches = []
		query_lower = query.lower()

		for user in all_users:
			name = user.full_name or user.name or ""
			if not name:
				continue

			# Calculate similarity ratio (0.0 to 1.0)
			similarity = difflib.SequenceMatcher(
				None,
				query_lower,
				name.lower()
			).ratio()

			# Keep matches above 60% similarity threshold
			if similarity > 0.6:
				matches.append({
					"name": user.full_name or user.name,
					"email": user.email or user.name,
					"similarity": round(similarity * 100)  # Convert to percentage
				})

		# Also search contacts
		all_contacts = frappe.get_all(
			"Contact",
			fields=["email_id", "first_name", "last_name", "name"]
		)

		for contact in all_contacts:
			name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() or contact.name
			if not name:
				continue

			similarity = difflib.SequenceMatcher(
				None,
				query_lower,
				name.lower()
			).ratio()

			if similarity > 0.6:
				matches.append({
					"name": name,
					"email": contact.email_id,
					"similarity": round(similarity * 100)
				})

		# Sort by similarity (best matches first)
		matches.sort(key=lambda x: x["similarity"], reverse=True)

		# Return top 3 suggestions
		top_matches = matches[:3]

		frappe.logger("send_email").info(
			f"💡 Fuzzy search for '{query}': {len(top_matches)} suggestions (from {len(matches)} total)"
		)

		return top_matches

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
		sender_name = self._get_sender_name(frappe.session.user)
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

	def _generate_preview(self, recipient: str, subject: str, content: str, cc: list, bcc: list, sender: str) -> str:
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
				now=True
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

	def _get_sender_name(self, user_email: str) -> str:
		"""
		Get sender name with smart fallback logic.

		Priority:
		1. full_name (if not empty)
		2. first_name + last_name (if both exist)
		3. first_name only (if exists)
		4. last_name only (if exists)
		5. email address (last resort)

		Args:
			user_email: User email address

		Returns:
			str: Best available name for signature
		"""
		user = frappe.get_doc("User", user_email)

		# Priority 1: full_name
		if user.full_name and user.full_name.strip():
			return user.full_name.strip()

		# Priority 2: first_name + last_name
		first = (user.first_name or "").strip()
		last = (user.last_name or "").strip()

		if first and last:
			return f"{first} {last}"

		# Priority 3: first_name only
		if first:
			return first

		# Priority 4: last_name only
		if last:
			return last

		# Priority 5: email (last resort)
		return user_email


# Make sure class name matches file name for discovery
send_email = SendEmail
