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
Email Message Improvement Tool for Core Plugin.
Uses LLM to transform casual messages into professional business emails.
"""

from typing import Any, Dict
import re  # For regex placeholder removal

import frappe
from frappe import _

from frappe_assistant_core.core.base_tool import BaseTool


class ImproveEmail(BaseTool):
	"""
	Tool for improving email messages using LLM.

	Transforms casual/short messages into professional business emails with:
	- Proper greeting (Bonjour [Name],)
	- Well-structured body (2-5 sentences)
	- Professional but friendly tone
	- No emojis
	- No signature (added separately by send_email)
	"""

	def __init__(self):
		super().__init__()
		self.name = "improve_email_message"
		self.description = "Improve and format email message into professional business email with greeting and well-structured body. Use this before sending emails to ensure professional communication. Transforms casual messages like 'lui demander status projet' into 'Bonjour, J'espère que tout se passe bien. Pourrais-tu me faire un point sur l'avancement du projet ? Merci d'avance.'"
		self.requires_permission = None  # No specific permission needed

		self.inputSchema = {
			"type": "object",
			"properties": {
				"message": {
					"type": "string",
					"description": "Raw message to improve (can be casual, short, or incomplete)",
				},
				"recipient_name": {
					"type": "string",
					"description": "Recipient first name for personalization (optional, e.g., 'Jérémy')",
				},
				"context": {
					"type": "string",
					"description": "Additional context about the email purpose (optional)",
				},
			},
			"required": ["message"],
		}

	def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
		"""Improve email message using LLM"""
		message = arguments.get("message", "").strip()
		recipient_name = arguments.get("recipient_name", "").strip()
		context = arguments.get("context", "").strip()

		if not message:
			return {"success": False, "error": "Message is required"}

		try:
			from openai import AsyncOpenAI
			import asyncio

			# Get LLM config from Nora
			try:
				# Import from nora module (cross-app import)
				from nora.api.agents_config import get_llm_config

				config = get_llm_config()
			except ImportError:
				frappe.log_error(
					"Email Improvement Import Error",
					"Could not import nora.api.agents_config. Nora app may not be installed.",
				)
				return self._fallback_improvement(message, recipient_name)

			# Create AsyncOpenAI client
			client = AsyncOpenAI(
				base_url=config["base_url"],
				api_key="dummy",  # Dummy key for Ollama
				default_headers={"X-API-Key": config.get("api_key", "")},
				timeout=30.0,
			)

			# Construct personalized greeting
			if recipient_name:
				greeting = f"Bonjour {recipient_name},"
			else:
				greeting = "Bonjour,"

			# Build improvement prompt
			prompt = f"""Transforme ce message en email professionnel français.

MESSAGE ORIGINAL: "{message}"
{f'CONTEXTE: {context}' if context else ''}

RÈGLES STRICTES:
- Commence TOUJOURS par "{greeting}"
- Longueur: 2-5 phrases selon la complexité (sois CONCIS mais complet)
- Ton: Professionnel mais pas trop formel, courtois et sympathique
- Structure: Greeting → Corps du message → Remerciement/Clôture
- PAS d'émojis (aucun !)
- PAS de signature finale type "Cordialement, [Nom]" (sera ajoutée automatiquement)
- CRITIQUE: NE JAMAIS utiliser de placeholders comme [Votre nom], [Nom], [Prénom], [Signature]
- CRITIQUE: Le message doit être 100% PRÊT à l'envoi, AUCUNE donnée à remplacer
- Termine UNIQUEMENT par "Merci." ou "Merci d'avance." ou "Merci beaucoup."
- PAS de formule de politesse finale type "Cordialement," (sera ajoutée automatiquement)
- Garde le contexte et les détails importants
- Si la demande est urgente, le mentionner poliment

EXEMPLES:

Input: "lui demander status projet"
Output: "{greeting}

J'espère que tout se passe bien. Pourrais-tu me faire un point sur l'avancement du projet ?

Merci d'avance."

Input: "besoin rapport Q4 urgent pour réunion lundi"
Output: "{greeting}

J'espère que tu vas bien. Nous aurions besoin du rapport Q4 de manière assez urgente pour la réunion de lundi prochain.

Pourrais-tu nous le transmettre dès que possible ?

Merci beaucoup."

IMPORTANT: Génère UNIQUEMENT le corps de l'email (greeting + message + merci).
NE METS PAS "Cordialement," ou toute autre formule de politesse finale.
NE METS PAS de nom/signature à la fin.
NE METS PAS de placeholders comme [Votre nom] ou [Nom].
Tout ce qui vient après "Merci." sera ajouté automatiquement par le système.

Génère maintenant l'email professionnel pour le message ci-dessus:"""

			# Call LLM asynchronously
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)

			async def get_completion():
				response = await client.chat.completions.create(
					model=config["model"],
					messages=[{"role": "user", "content": prompt}],
					temperature=0.7,
					max_tokens=400,  # Allow variable length based on complexity
				)
				return response.choices[0].message.content.strip()

			improved = loop.run_until_complete(get_completion())
			loop.close()

			# Cleanup: Remove any accidental signature/closing/placeholders that LLM might have added
			closing_phrases = [
				"cordialement",
				"bien à vous",
				"bien à toi",
				"sincèrement",
				"meilleures salutations",
				"à bientôt",
				"au plaisir",
			]

			# Regex patterns for placeholders (case-insensitive)
			placeholder_patterns = [
				r"\[votre\s+nom\]",
				r"\[nom\]",
				r"\[prénom\]",
				r"\[votre\s+prénom\]",
				r"\[signature\]",
				r"\[votre\s+signature\]",
			]

			# Split by double newlines to find paragraphs
			paragraphs = improved.split("\n\n")
			cleaned_paragraphs = []

			for para in paragraphs:
				para_lower = para.lower().strip()

				# Skip paragraph if it contains any closing phrase
				# (even if there's other text like "[Votre Nom]" after)
				if any(phrase in para_lower for phrase in closing_phrases):
					frappe.logger().info(f"[IMPROVE_EMAIL] Skipping closing paragraph: {para[:50]}...")
					continue

				# Remove placeholder patterns from paragraph
				for pattern in placeholder_patterns:
					para = re.sub(pattern, '', para, flags=re.IGNORECASE)

				# Skip paragraph if it's empty after cleanup
				para = para.strip()
				if para:
					cleaned_paragraphs.append(para)

			improved = "\n\n".join(cleaned_paragraphs).strip()

			frappe.logger().info("[IMPROVE_EMAIL] Cleanup: removed closings and placeholders")

			frappe.logger().info(f"[IMPROVE_EMAIL] Message improved successfully via LLM")

			return {
				"success": True,
				"improved_message": improved,
				"original_message": message,
				"method": "llm",
			}

		except Exception as e:
			frappe.log_error("Email Improvement Error", f"LLM improvement failed: {str(e)}\n\n{frappe.get_traceback()}")

			# Fallback to basic formatting
			return self._fallback_improvement(message, recipient_name)

	def _fallback_improvement(self, message: str, recipient_name: str = "") -> Dict[str, Any]:
		"""
		Fallback method when LLM is unavailable.
		Provides basic professional formatting.
		"""
		if recipient_name:
			greeting = f"Bonjour {recipient_name},"
		else:
			greeting = "Bonjour,"

		# Basic improvement: add greeting and closing
		improved = f"{greeting}\n\n{message}\n\nMerci d'avance."

		frappe.logger().warning("[IMPROVE_EMAIL] Using fallback improvement (LLM unavailable)")

		return {
			"success": True,
			"improved_message": improved,
			"original_message": message,
			"method": "fallback",
			"warning": "LLM unavailable, basic formatting applied",
		}


# Make sure class name matches file name for discovery
improve_email = ImproveEmail
