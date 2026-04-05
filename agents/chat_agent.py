import os
import json
import re
import copy
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class ChatAgent:
    """
    Agent conversationnel pour modifier le plan de voyage en temps réel.
    Prend le résultat courant + message utilisateur → retourne une réponse
    textuelle + un dict de mises à jour à appliquer au résultat.
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY manquant dans le fichier .env")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    # ── CONTEXT BUILDER ────────────────────────────────────────────────────────

    def _build_context(self, result: dict) -> str:
        """Résumé compact du plan courant à injecter dans le prompt."""
        lines = []

        lines.append(
            f"Destination : {result.get('destination', '?')}  |  "
            f"Origine : {result.get('origin', '?')}"
        )
        lines.append(
            f"Dates : {result.get('depart_date', '?')} → {result.get('return_date', '?')} "
            f"({result.get('days', '?')} jours)"
        )
        lines.append(
            f"Budget : {result.get('budget_total', '?')}€  |  "
            f"Type : {result.get('travel_type', '?')}  |  "
            f"Voyageurs : {result.get('travelers', '?')}"
        )

        # Recommandation courante
        rec   = result.get("recommendation", {})
        rec_f = rec.get("recommended_flight", {})
        rec_h = rec.get("recommended_hotel",  {})
        if rec_f:
            obj = rec_f.get("object", {})
            lines.append(
                f"Vol recommandé : {rec_f.get('name', obj.get('airline', '?'))} — "
                f"{rec_f.get('price', obj.get('total_price', '?'))}€"
            )
        if rec_h:
            obj = rec_h.get("object", {})
            lines.append(
                f"Hôtel recommandé : {rec_h.get('name', obj.get('name', '?'))} — "
                f"{rec_h.get('price_per_night', obj.get('price_per_night', '?'))}€/nuit"
            )

        # Hôtels disponibles
        hotels = result.get("hotels", [])
        if hotels:
            lines.append("\nHôtels disponibles :")
            for i, h in enumerate(hotels[:6]):
                stars = "★" * int(h.get("stars", 0)) if h.get("stars") else ""
                lines.append(
                    f"  [{i}] {h['name']} {stars} — "
                    f"{h['price_per_night']:.0f}€/nuit — "
                    f"Total : {h['total_price']:.0f}€ — "
                    f"Note : {h['rating']}/10 — "
                    f"Équipements : {', '.join(h.get('amenities', [])[:3])}"
                )

        # Vols disponibles
        flights = result.get("flights", [])
        if flights:
            lines.append("\nVols disponibles :")
            for i, f in enumerate(flights[:5]):
                stops = "direct" if f["stops"] == 0 else f"{f['stops']} escale(s)"
                lines.append(
                    f"  [{i}] {f['airline']} {f['flight_number']} — "
                    f"{f['total_price']:.0f}€ total — {stops} — "
                    f"départ {f['departure'][:16]}"
                )

        # Itinéraire (résumé)
        itinerary = result.get("itinerary", [])
        if itinerary:
            lines.append("\nItinéraire actuel :")
            for day in itinerary:
                acts = day.get("activities", [])
                lines.append(
                    f"  Jour {day.get('day','?')} ({day.get('date','?')}) — "
                    f"{day.get('title','?')}"
                )
                for act in acts[:3]:
                    lines.append(f"    • {act}")

        # Conseils
        tips = result.get("tips", [])
        if tips:
            lines.append("\nConseils actuels :")
            for tip in tips:
                lines.append(f"  • {tip}")

        return "\n".join(lines)

    # ── MAIN METHOD ────────────────────────────────────────────────────────────

    def process(self, user_message: str, current_result: dict, chat_history: list) -> dict:
        """
        Traite un message utilisateur et retourne :
        {
          "message": str,       # réponse conversationnelle
          "updates": dict       # champs à mettre à jour dans result
        }
        """
        from prompts.system_prompt import CHAT_AGENT_SYSTEM_PROMPT

        context = self._build_context(current_result)

        messages = [
            {
                "role": "system",
                "content": CHAT_AGENT_SYSTEM_PROMPT.format(context=context)
            }
        ]

        # Historique (les 10 derniers échanges pour ne pas dépasser le contexte)
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.4,
            max_tokens=2500
        )
        raw = response.choices[0].message.content

        parsed = self._parse_json(raw)
        if not parsed.get("message"):
            parsed["message"] = raw
        if "updates" not in parsed:
            parsed["updates"] = {}

        return parsed

    # ── APPLY UPDATES ──────────────────────────────────────────────────────────

    def apply_updates(self, current_result: dict, updates: dict) -> dict:
        """
        Applique les mises à jour retournées par le LLM au résultat courant.
        Seuls les champs présents dans `updates` sont modifiés.
        """
        updated = copy.deepcopy(current_result)

        for key, value in updates.items():

            if key == "recommendation" and isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    updated.setdefault("recommendation", {})[sub_key] = sub_val

                    if sub_key == "recommended_hotel" and isinstance(sub_val, dict):
                        idx = sub_val.get("index")
                        hotels = updated.get("hotels", [])
                        if idx is not None and 0 <= idx < len(hotels):
                            updated["recommendation"]["recommended_hotel"]["object"] = hotels[idx]

                    if sub_key == "recommended_flight" and isinstance(sub_val, dict):
                        idx = sub_val.get("index")
                        flights = updated.get("flights", [])
                        if idx is not None and 0 <= idx < len(flights):
                            updated["recommendation"]["recommended_flight"]["object"] = flights[idx]

            elif key == "itinerary" and isinstance(value, list):
                # Si le LLM retourne seulement certains jours → merge par numéro de jour
                # Si tous les jours sont fournis (changement de dates) → remplacement complet
                existing_days = {d["day"] for d in updated.get("itinerary", [])}
                new_days      = {d["day"] for d in value if isinstance(d, dict) and "day" in d}
                if new_days and new_days.issubset(existing_days) and len(new_days) < len(existing_days):
                    # Mise à jour partielle
                    day_map = {d["day"]: d for d in updated.get("itinerary", [])}
                    for new_day in value:
                        day_map[new_day["day"]] = new_day
                    updated["itinerary"] = sorted(day_map.values(), key=lambda d: d["day"])
                else:
                    # Remplacement complet (nouveau nombre de jours ou itinéraire entier)
                    updated["itinerary"] = sorted(value, key=lambda d: d.get("day", 0))

            elif key == "tips" and isinstance(value, list):
                updated["tips"] = value

            elif key == "budget" and isinstance(value, dict):
                updated["budget"].update(value)

            elif key in ("depart_date", "return_date", "days", "dates"):
                # Changement de dates
                updated[key] = value
                # Synchroniser aussi dans selected_dates si présent
                if "selected_dates" in updated:
                    if key in ("depart_date", "return_date", "days"):
                        updated["selected_dates"][key] = value

            elif key in updated:
                updated[key] = value

        return updated

    # ── HELPERS ────────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> dict:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return {"message": text, "updates": {}}
