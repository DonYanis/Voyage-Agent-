import requests
import os
from datetime import datetime

def get_weather(city: str, days: int = 7) -> dict:

    api_key = os.getenv("OPENWEATHER_API_KEY", "demo")

    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "fr",
            "cnt": min(days * 8, 40)
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        # Parser les données par jour
        daily = {}
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            if date not in daily:
                daily[date] = {
                    "date": date,
                    "temp_min": item["main"]["temp_min"],
                    "temp_max": item["main"]["temp_max"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"],
                    "humidity": item["main"]["humidity"],
                    "wind": item["wind"]["speed"],
                    "rain": item.get("rain", {}).get("3h", 0)
                }
            else:
                daily[date]["temp_min"] = min(daily[date]["temp_min"], item["main"]["temp_min"])
                daily[date]["temp_max"] = max(daily[date]["temp_max"], item["main"]["temp_max"])

        return {
            "city": city,
            "country": data["city"]["country"],
            "days": list(daily.values())[:days],
            "success": True
        }

    except Exception as e:
        return None


def weather_summary(weather_data: dict) -> str:
    """Convertit les données météo en texte pour le LLM."""
    if not weather_data.get("success"):
        return "Météo non disponible."

    lines = [f"Météo pour {weather_data['city']} ({weather_data.get('country', '')}) :"]
    for day in weather_data["days"]:
        lines.append(
            f"- {day['date']} : {day['description']}, "
            f"{day['temp_min']}°C à {day['temp_max']}°C, "
            f"humidité {day['humidity']}%, "
            f"vent {day['wind']} km/h"
            + (f", pluie {day['rain']}mm" if day['rain'] > 0 else "")
        )
    return "\n".join(lines)
