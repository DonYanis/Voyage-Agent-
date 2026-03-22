import os

def search_flights(origin: str, destination: str, date: str, adults: int = 1, budget: float = None) -> dict:

    api_key = os.getenv("SERPAPI_API_KEY", "")

    try:
        from serpapi import GoogleSearch

        params = {
            "engine": "google_flights",
            "departure_id": origin.upper(),
            "arrival_id": destination.upper(),
            "outbound_date": date,
            "currency": "EUR",
            "hl": "fr",
            "adults": adults,
            "api_key": api_key,
            "type": "2",
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        flights = []
        best = results.get("best_flights", []) + results.get("other_flights", [])

        for offer in best[:5]:
            legs = offer.get("flights", [])
            if not legs:
                continue

            first_leg = legs[0]
            last_leg = legs[-1]
            airline = first_leg.get("airline", "Inconnu")
            flight_number = first_leg.get("flight_number", "??")
            departure_time = first_leg.get("departure_airport", {}).get("time", date + " 00:00")
            arrival_time = last_leg.get("arrival_airport", {}).get("time", date + " 00:00")
            duration = offer.get("total_duration", 0)
            stops = len(legs) - 1
            price = offer.get("price", 0)

            flights.append({
                "airline": airline,
                "flight_number": flight_number,
                "departure": departure_time,
                "arrival": arrival_time,
                "duration": f"{duration // 60}h{duration % 60:02d}m",
                "stops": stops,
                "price_per_person": round(price / adults, 2),
                "total_price": float(price),
                "currency": "EUR"
            })

        flights.sort(key=lambda x: x["total_price"])
        return {
            "flights": flights,
            "success": True,
            "origin": origin,
            "destination": destination,
            "source": "Google Flights (SerpApi)"
        }

    except Exception as e:
        print(f"SerpApi error: {e}")
        return None

def flights_summary(flights_data: dict) -> str:
    """Convertit les données vols en texte pour le LLM."""
    if not flights_data.get("success") or not flights_data.get("flights"):
        return "Aucun vol trouvé."

    source = flights_data.get("source", "")
    lines = [f"Vols de {flights_data['origin']} vers {flights_data['destination']} ({source}) :"]
    for i, f in enumerate(flights_data["flights"][:4], 1):
        stops = "direct" if f["stops"] == 0 else f"{f['stops']} escale(s)"
        lines.append(
            f"{i}. {f['airline']} ({f['flight_number']}) — "
            f"{f['total_price']:.0f}EUR total — "
            f"{stops} — depart {f['departure']} — duree {f['duration']}"
        )
    return "\n".join(lines)
