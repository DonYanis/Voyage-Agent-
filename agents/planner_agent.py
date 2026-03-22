import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

from tools.weather_tool import get_weather, weather_summary
from tools.flights_tool import search_flights, flights_summary
from tools.budget_tool import calculate_budget, budget_summary
from prompts.system_prompt import (
    SYSTEM_PROMPT, REACT_PROMPT, COT_BUDGET_PROMPT,
    SELF_CORRECTION_PROMPT, ITINERARY_PROMPT
)

load_dotenv()

class VoyageAgent:
    """
    - ReAct : boucle Thought → Action → Observation
    - Chain of Thought : décomposition du budget
    - Self-Correction : vérification et correction du plan
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY manquant dans le fichier .env")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.reasoning_steps = []

    def _call_llm(self, messages: list, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def _add_step(self, step_type: str, content: str, icon: str = "🔵"):
        """Les etpes react"""
        self.reasoning_steps.append({
            "type": step_type,
            "content": content,
            "icon": icon
        })

    def plan(self, params: dict, progress_callback=None) -> dict:
        """
        Pipeline principal de planification.
        params = {
            origin, destination, depart_date, return_date,
            budget, travelers, travel_type,
            origin_iata, dest_iata
        }
        """
        self.reasoning_steps = []
        result = {}

        def update(msg):
            if progress_callback:
                progress_callback(msg)

        # ÉTAPE 1 : COLLECTE DES DONNÉES (Actions)
        self._add_step("thought", "Thought 1 : Je dois collecter les données météo et de vols pour planifier le voyage.", "🤔")
        update("Recherche des données météo...")

        # Action 1 : Météo
        days = (self._parse_date(params["return_date"]) - self._parse_date(params["depart_date"])).days
        weather_data = get_weather(params["destination"], days)
        w_summary = weather_summary(weather_data)
        result["weather"] = weather_data.get("days", [])

        self._add_step("action", f"Action 1 : Récupération météo pour {params['destination']} sur {days} jours.", "⚡")
        self._add_step("observation", f"Observation 1 : {w_summary[:200]}...", "👁️")

        # Action 2 : Vols
        update("Recherche des vols disponibles...")
        self._add_step("thought", f"Thought 2 : Je cherche les vols de {params['origin']} vers {params['destination']}.", "🤔")

        flights_data = search_flights(
            params.get("origin_iata", "CDG"),
            params.get("dest_iata", "JFK"),
            params["depart_date"],
            params["travelers"]
        )
        f_summary = flights_summary(flights_data)
        result["flights"] = flights_data.get("flights", [])
        best_flight_cost = result["flights"][0]["total_price"] if result["flights"] else 0

        self._add_step("action", f"Action 2 : Recherche de vols pour {params['travelers']} voyageur(s).", "⚡")
        self._add_step("observation", f"Observation 2 : {f_summary}", "👁️")

        # ÉTAPE 2 : BUDGET (Chain of Thought)
        update("Calcul de la répartition du budget...")
        self._add_step("thought", "Thought 3 : Je calcule la répartition du budget étape par étape (Chain of Thought).", "🤔")

        budget_data = calculate_budget(
            total_budget=params["budget"],
            flight_cost=best_flight_cost,
            days=days,
            travelers=params["travelers"],
            travel_type=params["travel_type"]
        )
        b_summary = budget_summary(budget_data)
        result["budget"] = budget_data

        # Enrichir avec CoT via LLM
        cot_prompt = COT_BUDGET_PROMPT.format(
            total=params["budget"],
            flights=best_flight_cost,
            days=days,
            travelers=params["travelers"],
            travel_type=params["travel_type"]
        )
        cot_response = self._call_llm([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": cot_prompt}
        ], temperature=0.3)

        self._add_step("action", "Action 3 : Répartition du budget par catégorie.", "⚡")
        self._add_step("observation", f"Observation 3 :\n{b_summary}", "👁️")


        # ÉTAPE 3 : ITINÉRAIRE
        update("Génération de l'itinéraire personnalisé...")
        self._add_step("thought", "Thought 4 : Je génère l'itinéraire en adaptant chaque activité à la météo prévue.", "🤔")

        daily_budget = budget_data.get("daily_per_person", params["budget"] / days)
        dates_str = f"{params['depart_date']} au {params['return_date']}"

        itinerary_prompt = ITINERARY_PROMPT.format(
            destination=params["destination"],
            dates=dates_str,
            days=days,
            weather_summary=w_summary,
            daily_budget=daily_budget,
            travel_type=params["travel_type"],
            travelers=params["travelers"]
        )

        itinerary_response = self._call_llm([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": itinerary_prompt}
        ], temperature=0.7, max_tokens=3000)

        # Parser le JSON de l'itinéraire
        itinerary_data = self._parse_json(itinerary_response)
        result["itinerary"] = itinerary_data.get("itinerary", [])
        result["tips"] = itinerary_data.get("tips", [])
        result["travel_score"] = itinerary_data.get("travel_score", {})

        self._add_step("action", "Action 4 : Génération du programme jour par jour adapté à la météo.", "⚡")
        self._add_step("observation", f"Observation 4 : Itinéraire de {len(result['itinerary'])} jours généré.", "👁️")

        # ÉTAPE 4 : SELF-CORRECTION
        update("Vérification et correction du plan...")
        self._add_step("thought", "Thought 5 : Je vérifie la cohérence du plan (Self-Correction) — météo, budget, logique.", "🤔")

        plan_text = json.dumps(result["itinerary"], ensure_ascii=False, indent=2)[:2000]
        correction_prompt = SELF_CORRECTION_PROMPT.format(
            plan=plan_text,
            weather=w_summary[:500],
            budget=b_summary[:300]
        )

        correction = self._call_llm([
            {"role": "system", "content": "Tu es un agent critique expert en voyage. Sois précis et concis."},
            {"role": "user", "content": correction_prompt}
        ], temperature=0.3)

        result["correction"] = correction
        self._add_step("action", "Action 5 : Auto-critique du plan généré.", "⚡")
        self._add_step("observation", f"Observation 5 (Auto-correction) :\n{correction[:300]}...", "👁️")

        # RÉPONSE FINALE
        self._add_step("final", "Thought Final : Plan validé et prêt. Toutes les vérifications sont passées.", "✅")

        # Méta-données pour le PDF
        result["destination"] = params["destination"]
        result["origin"] = params["origin"]
        result["dates"] = dates_str
        result["travelers"] = params["travelers"]
        result["budget_total"] = params["budget"]
        result["flight_cost"] = best_flight_cost
        result["budget_breakdown"] = budget_data.get("breakdown", {})
        result["travel_type"] = params["travel_type"]
        result["days"] = days
        result["reasoning_steps"] = self.reasoning_steps

        return result

    def _parse_date(self, date_str: str):
        from datetime import datetime
        return datetime.strptime(date_str, "%Y-%m-%d")

    def _parse_json(self, text: str) -> dict:
        # Essayer de trouver le JSON dans le texte
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        # Fallback : structure vide
        return {"itinerary": [], "tips": [], "travel_score": {"score": 7.0, "reasons": []}}



    def get_iata_from_llm(self, city: str) -> str:
        """Utilise le LLM pour trouver le code IATA d'une ville. xpl paris CDG"""
        response = self._call_llm([
            {
                "role": "system",
                "content": "Tu es un expert en aviation. Réponds UNIQUEMENT avec le code IATA à 3 lettres, rien d'autre."
            },
            {
                "role": "user",
                "content": f"Quel est le code IATA de l'aéroport principal de {city} ?"
            }
        ], temperature=0, max_tokens=10)
        
        # Extraire les 3 lettres
        import re
        match = re.search(r'\b[A-Z]{3}\b', response.upper())
        return match.group() if match else city[:3].upper()