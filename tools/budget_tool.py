def calculate_budget(
    total_budget: float,
    flight_cost: float,
    days: int,
    travelers: int,
    travel_type: str = "équilibré"
) -> dict:
    """
    Répartit intelligemment le budget selon le type de voyage.
    Technique CoT : décompose le calcul étape par étape.
    """

    # Étape 1 : Budget restant après vols
    remaining = total_budget - flight_cost
    if remaining <= 0:
        return {
            "error": "Budget insuffisant pour couvrir les vols.",
            "flight_cost": flight_cost,
            "total_budget": total_budget,
            "success": False
        }

    # Étape 2 : Répartition selon le type de voyage
    profiles = {
        "économique": {
            "hebergement": 0.35,
            "activites": 0.20,
            "nourriture": 0.30,
            "transport_local": 0.10,
            "imprevus": 0.05
        },
        "équilibré": {
            "hebergement": 0.40,
            "activites": 0.25,
            "nourriture": 0.20,
            "transport_local": 0.10,
            "imprevus": 0.05
        },
        "luxe": {
            "hebergement": 0.45,
            "activites": 0.25,
            "nourriture": 0.20,
            "transport_local": 0.05,
            "imprevus": 0.05
        },
        "aventure": {
            "hebergement": 0.25,
            "activites": 0.45,
            "nourriture": 0.20,
            "transport_local": 0.05,
            "imprevus": 0.05
        }
    }

    profile = profiles.get(travel_type.lower(), profiles["équilibré"])

    # Étape 3 : Calcul des montants
    breakdown = {}
    for category, ratio in profile.items():
        amount = remaining * ratio
        breakdown[category] = {
            "total": round(amount, 2),
            "per_day": round(amount / days, 2),
            "per_person_per_day": round(amount / days / travelers, 2)
        }

    # Étape 4 : Budget journalier total par personne
    daily_per_person = round(remaining / days / travelers, 2)

    return {
        "total_budget": total_budget,
        "flight_cost": flight_cost,
        "remaining_after_flights": round(remaining, 2),
        "days": days,
        "travelers": travelers,
        "travel_type": travel_type,
        "breakdown": breakdown,
        "daily_per_person": daily_per_person,
        "success": True
    }


def budget_summary(budget_data: dict) -> str:
    """Convertit le budget en texte pour le LLM."""
    if not budget_data.get("success"):
        return budget_data.get("error", "Erreur budget.")

    b = budget_data
    lines = [
        f"Répartition du budget ({b['travel_type']}) pour {b['travelers']} personne(s) sur {b['days']} jours :",
        f"- Budget total : {b['total_budget']}€",
        f"- Vols : {b['flight_cost']}€",
        f"- Restant : {b['remaining_after_flights']}€",
        ""
    ]
    for cat, vals in b["breakdown"].items():
        lines.append(
            f"- {cat.replace('_', ' ').capitalize()} : {vals['total']}€ total "
            f"({vals['per_person_per_day']}€/pers/jour)"
        )
    lines.append(f"\nBudget journalier par personne : {b['daily_per_person']}€")
    return "\n".join(lines)
