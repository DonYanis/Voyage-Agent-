import os

def search_hotels(city: str, check_in: str, check_out: str, adults: int = 2, budget_per_night: float = None) -> dict:
    api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key:
        None
    try:
        from serpapi import GoogleSearch
        params = {
            "engine": "google_hotels",
            "q": f"hotels {city}",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": adults,
            "currency": "EUR",
            "hl": "fr",
            "api_key": api_key,
            "sort_by": 3,
            "num": 5
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        hotels = []
        for prop in results.get("properties", [])[:6]:
            price = prop.get("rate_per_night", {}).get("lowest", 0)
            if isinstance(price, str):
                price = float(''.join(filter(str.isdigit, price)) or 0)
            days = _count_days(check_in, check_out)
            hotels.append({
                "name":             prop.get("name", "Hôtel inconnu"),
                "stars":             _parse_stars(prop.get("hotel_class", 0)),
                "rating":           prop.get("overall_rating", 0),
                "reviews":          prop.get("reviews", 0),
                "price_per_night":  float(price),
                "total_price":      round(float(price) * days, 2),
                "days":             days,
                "currency":         "EUR",
                "description":      prop.get("description", "")[:150],
                "amenities":        prop.get("amenities", [])[:5],
                "link":             prop.get("link", ""),
            })
        if not hotels:
            None
        hotels.sort(key=lambda x: x["price_per_night"])
        return {"hotels": hotels, "city": city, "check_in": check_in,
                "check_out": check_out, "days": _count_days(check_in, check_out),
                "success": True, "source": "Google Hotels (SerpApi)"}
    except Exception as e:
        print(f"SerpApi Hotels error: {e}")
        return None

def _count_days(check_in: str, check_out: str) -> int:
    from datetime import datetime
    d1 = datetime.strptime(check_in,  "%Y-%m-%d")
    d2 = datetime.strptime(check_out, "%Y-%m-%d")
    return max((d2 - d1).days, 1)


def hotels_summary(hotels_data: dict) -> str:
    if not hotels_data.get("success") or not hotels_data.get("hotels"):
        return "Aucun hôtel trouvé."
    lines = [f"Hôtels à {hotels_data['city']} ({hotels_data.get('days',1)} nuits) :"]
    for i, h in enumerate(hotels_data["hotels"][:4], 1):
        stars = "★" * int(h["stars"]) if h["stars"] else ""
        lines.append(
            f"{i}. {h['name']} {stars} — {h['price_per_night']:.0f}€/nuit — "
            f"Total : {h['total_price']:.0f}€ — Note : {h['rating']}/10"
        )
    return "\n".join(lines)

def _parse_stars(value) -> int:
    """Extrait le nombre d'étoiles depuis un int ou une chaîne comme 'Hôtel 2 étoiles'."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        import re
        match = re.search(r'\d+', value)
        return int(match.group()) if match else 0
    return 0