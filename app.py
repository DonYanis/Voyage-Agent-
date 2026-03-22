import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import json
import os
from dotenv import load_dotenv

load_dotenv()

# CONFIG PAGE
st.set_page_config(
    page_title="Agent Planificateur de Voyage",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS :
with open("css/styles.css", "r") as f:
    css = f.read()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# FORMULAIRE
with st.sidebar:
    st.markdown("## Planifier mon voyage")
    st.markdown("---")

    origin = st.text_input("Ville de départ", value="Paris", placeholder="Ex: Paris")
    destination = st.text_input("Destination", value="Tokyo", placeholder="Ex: Tokyo, Bali...")

    col1, col2 = st.columns(2)
    with col1:
        depart_date = st.date_input(
            "Départ",
            value=date.today() + timedelta(days=30),
            min_value=date.today()
        )
    with col2:
        return_date = st.date_input(
            "Retour",
            value=date.today() + timedelta(days=37),
            min_value=date.today() + timedelta(days=1)
        )

    travelers = st.slider("Voyageurs", 1, 8, 2)

    budget = st.number_input(
        "Budget total (€)",
        min_value=200,
        max_value=50000,
        value=3000,
        step=100,
        help="Budget total pour tous les voyageurs incluant les vols"
    )

    travel_type = st.selectbox(
        "Type de voyage",
        ["équilibré", "économique", "luxe", "aventure"],
        index=0
    )

    st.markdown("---")
    st.markdown("**Clés API**")
    groq_key = st.text_input("Groq API Key obligatoire", type="password",
                              value=os.getenv("GROQ_API_KEY", ""),
                              help="Gratuit sur console.groq.com")
    weather_key = st.text_input("OpenWeather Key (optionnel)", type="password",
                                 value=os.getenv("OPENWEATHER_API_KEY", ""),
                                 help="Gratuit sur openweathermap.org")
    serpapi_key = st.text_input("SerpApi Key (optionnel)", type="password",
                                 value=os.getenv("SERPAPI_API_KEY", ""),
                                 help="Gratuit sur serpapi.com — vols Google Flights reels")

    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
    if weather_key:
        os.environ["OPENWEATHER_API_KEY"] = weather_key
    if serpapi_key:
        os.environ["SERPAPI_API_KEY"] = serpapi_key

    st.markdown("---")
    plan_btn = st.button("Planifier mon voyage !", use_container_width=True)


# PAGE PRINCIPALE
st.markdown('<div class="main-title">Agent Planificateur de Voyage</div>', unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#666;'>Powered by LLaMA 3 (Groq) · ReAct + Chain of Thought + Self-Correction</p>",
    unsafe_allow_html=True
)

if not plan_btn:
    # Page d'accueil
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("### ReAct\nL'agent raisonne étape par étape avant chaque action")
    with col2:
        st.info("### Chain of Thought\nDécomposition intelligente du budget en étapes")
    with col3:
        st.info("### Self-Correction\nL'agent vérifie et corrige son propre plan")

    st.markdown("---")
    st.markdown("""
    ### Comment ça marche ?
    1. **Remplis le formulaire** à gauche avec ta destination et ton budget
    2. **L'agent collecte** la météo et les vols en temps réel
    3. **Il raisonne** (ReAct) pour adapter le programme à la météo
    4. **Il répartit** ton budget intelligemment (Chain of Thought)
    5. **Il vérifie** la cohérence du plan (Self-Correction)
    6. **Tu télécharges** l'itinéraire complet en PDF !
    """)

else:
    # Validation dates
    if return_date <= depart_date:
        st.error("❌ La date de retour doit être après la date de départ.")
        st.stop()

    days = (return_date - depart_date).days

    if days < 1:
        st.error("❌ Le voyage doit durer au moins 1 jour.")
        st.stop()

    if not os.getenv("GROQ_API_KEY"):
        st.error("❌ Clé Groq manquante. Entre ta clé API dans la sidebar.")
        st.stop()

    # get iata des villes avec llm expl : charles de gaule : CDG
    from agents.planner_agent import VoyageAgent
    agent = VoyageAgent()
    origin_iata = agent.get_iata_from_llm(origin)
    dest_iata = agent.get_iata_from_llm(destination)

    # LANCEMENT DE L'AGENT
    params = {
        "origin": origin,
        "destination": destination,
        "depart_date": depart_date.strftime("%Y-%m-%d"),
        "return_date": return_date.strftime("%Y-%m-%d"),
        "budget": budget,
        "travelers": travelers,
        "travel_type": travel_type,
        "origin_iata": origin_iata,
        "dest_iata": dest_iata
    }

    progress_bar = st.progress(0)
    status_text = st.empty()
    steps_container = st.empty()

    reasoning_display = []

    def update_progress(msg):
        steps_map = {
            "Recherche des données météo...": 20,
            "Recherche des vols disponibles...": 40,
            "Recherche des hôtels disponibles...": 50,
            "Le LLM analyse et recommande le meilleur vol et hôtel...": 55,
            "Calcul de la répartition du budget...": 60,
            "Génération de l'itinéraire personnalisé...": 80,
            "Vérification et correction du plan...": 95,
        }
        pct = steps_map.get(msg, 50)
        progress_bar.progress(pct)
        status_text.markdown(f"**{msg}**")

    try:
        from agents.planner_agent import VoyageAgent
        agent = VoyageAgent()

        with st.spinner("L'agent planifie ton voyage..."):
            result = agent.plan(params, progress_callback=update_progress)

        progress_bar.progress(100)
        status_text.markdown("**Plan généré avec succès !**")

        st.success(f"Ton voyage à **{destination}** est planifié ! ({days} jours)")

        # ONGLETS DE RÉSULTATS
        #tab1,  tab3, tab4, tab2, tab5 = st.tabs(["🧠 Raisonnement",  "💰 Budget", "📅 Itinéraire","🌤 Météo", "📄 Export PDF"])
        tab1,  tab3, tab4,  tab5 = st.tabs([
            "🧠 Raisonnement",  "💰 Budget", "📅 Itinéraire", "📄 Export PDF"
        ])


        # TAB 1 : RAISONNEMENT 
        with tab1:
            st.markdown("### 🧠 Raisonnement de l'agent (ReAct)")
            st.markdown("*Voici comment l'agent a raisonné pour construire ton voyage :*")
            st.markdown("---")

            for step in result.get("reasoning_steps", []):
                stype = step["type"]
                content = step["content"]
                icon = step["icon"]

                if stype == "thought":
                    st.markdown(f'<div class="thought-box"> <b>Thought</b> — {content}</div>',
                               unsafe_allow_html=True)
                elif stype == "action":
                    st.markdown(f'<div class="action-box"> <b>Action</b> — {content}</div>',
                               unsafe_allow_html=True)
                elif stype == "observation":
                    st.markdown(f'<div class="obs-box"> <b>Observation</b> — {content}</div>',
                               unsafe_allow_html=True)
                elif stype == "final":
                    st.markdown(f'<div class="final-box"> {content}</div>',
                               unsafe_allow_html=True)

            
            if result.get("cot_budget"):
                st.markdown("---")
                st.markdown("### Raisonnement budget (Chain of Thought)")
                st.markdown("*Voici comment l'agent a raisonné pour répartir le budget :*")
                st.markdown(
                    f'<div class="thought-box">{result["cot_budget"]}</div>',
                    unsafe_allow_html=True
                )

            if result.get("correction"):
                st.markdown("---")
                st.markdown("###  Auto-correction (Self-Correction)")
                st.markdown(f"*L'agent a vérifié son plan :*")
                st.info(result["correction"])
      
#        # TAB 2 : MÉTÉO
#        with tab2:
#            st.markdown(f"### 🌤 Météo à {destination}")
#
#            weather_days = result.get("weather", [])
#            if weather_days:
#                # Graphique températures
#                dates_w = [d["date"] for d in weather_days]
#                temps_min = [d["temp_min"] for d in weather_days]
#                temps_max = [d["temp_max"] for d in weather_days]
#
#                fig = go.Figure()
#                fig.add_trace(go.Scatter(
#                    x=dates_w, y=temps_max, name="Temp. max",
#                    line=dict(color="#F18F01", width=2),
#                    fill=None
#                ))
#                fig.add_trace(go.Scatter(
#                    x=dates_w, y=temps_min, name="Temp. min",
#                    line=dict(color="#2E86AB", width=2),
#                    fill="tonexty", fillcolor="rgba(46,134,171,0.1)"
#                ))
#                fig.update_layout(
#                    title="Températures prévues",
#                    xaxis_title="Date",
#                    yaxis_title="Température (°C)",
#                    height=300,
#                    margin=dict(l=0, r=0, t=40, b=0)
#                )
#                st.plotly_chart(fig, use_container_width=True)
#
#                # Cartes météo par jour
#                cols = st.columns(min(len(weather_days), 4))
#                for i, day in enumerate(weather_days[:8]):
#                    with cols[i % 4]:
#                        rain_emoji = "🌧️" if day.get("rain", 0) > 0 else ""
#                        desc = day["description"].capitalize()
#                        if "soleil" in desc.lower() or "dégagé" in desc.lower() or "clair" in desc.lower():
#                            emoji = "☀️"
#                        elif "pluie" in desc.lower() or "rain" in desc.lower():
#                            emoji = "🌧️"
#                        elif "nuage" in desc.lower() or "cloud" in desc.lower():
#                            emoji = "⛅"
#                        elif "orage" in desc.lower():
#                            emoji = "⛈️"
#                        else:
#                            emoji = "🌤️"
#
#                        st.metric(
#                            label=f"{emoji} {day['date']}",
#                            value=f"{day['temp_max']}°C",
#                            delta=f"min {day['temp_min']}°C"
#                        )
#                        st.caption(f"{desc} | 💧{day['humidity']}%")
#        
#        # TAB 3 : BUDGET
        with tab3:
            st.markdown("### 💰 Répartition du budget")

            budget_data = result.get("budget", {})
            if budget_data.get("success"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Budget total", f"{budget_data['total_budget']}€")
                with col2:
                    st.metric("Coût des vols", f"{budget_data['flight_cost']:.0f}€")
                with col3:
                    st.metric("Restant", f"{budget_data['remaining_after_flights']:.0f}€")

                st.markdown("---")

                breakdown = budget_data.get("breakdown", {})
                if breakdown:
                    # Graphique camembert
                    labels = [k.replace("_", " ").capitalize() for k in breakdown.keys()]
                    labels = ["Vols"] + labels
                    values = [budget_data["flight_cost"]] + [v["total"] for v in breakdown.values()]
                    colors_pie = ["#2E86AB", "#F18F01", "#28B463", "#E74C3C", "#8E44AD", "#F39C12"]

                    fig_pie = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.4,
                        marker=dict(colors=colors_pie)
                    )])
                    fig_pie.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig_pie, use_container_width=True)

                    # Tableau
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Détail par catégorie :**")
                        for cat, vals in breakdown.items():
                            st.markdown(
                                f"- **{cat.replace('_', ' ').capitalize()}** : "
                                f"{vals['total']:.0f}€ total / "
                                f"{vals['per_person_per_day']:.0f}€ pers/jour"
                            )
                    with col_b:
                        daily = budget_data.get("daily_per_person", 0)
                        st.metric("💸 Budget journalier / personne", f"{daily:.0f}€")

            # Vols disponibles
            st.markdown("---")
            # ── RECOMMANDATION LLM ──
            recommendation = result.get("recommendation", {})
            if recommendation:
                rec_f = recommendation.get("recommended_flight", {})
                rec_h = recommendation.get("recommended_hotel", {})
                summary = recommendation.get("global_summary", "")

                st.markdown("### Recommandation de l'agent")

                if summary:
                    st.info(f" {summary}")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### Vol recommandé")
                    if rec_f:
                        obj = rec_f.get("object", {})
                        st.success(
                            f"**{rec_f.get('name', obj.get('airline', '?'))}**\n\n"
                            f"Prix total : **{rec_f.get('price', obj.get('total_price', '?'))}€**"
                        )
                        st.markdown(f"**Pourquoi ?** {rec_f.get('reason', '')}")

                with col2:
                    st.markdown("#### Hôtel recommandé")
                    if rec_h:
                        obj = rec_h.get("object", {})
                        st.success(
                            f"**{rec_h.get('name', obj.get('name', '?'))}**\n\n"
                            f"{rec_h.get('price_per_night', obj.get('price_per_night', '?'))}€/nuit — "
                            f"Total : **{rec_h.get('total_price', obj.get('total_price', '?'))}€**"
                        )
                        st.markdown(f"**Pourquoi ?** {rec_h.get('reason', '')}")

                st.markdown("---")
            st.markdown("###  Vols disponibles")
            flights = result.get("flights", [])
            if flights:
                for i, f in enumerate(flights[:3]):
                    stops = " Direct" if f["stops"] == 0 else f" {f['stops']} escale(s)"
                    with st.expander(f"**{f['airline']}** — {f['total_price']:.0f}€ total — {stops}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Vol** : {f['flight_number']}")
                            st.write(f"**Départ** : {f['departure'][:16]}")
                        with col2:
                            st.write(f"**Arrivée** : {f['arrival'][:16]}")
                            st.write(f"**Durée** : {f['duration']}")
                        with col3:
                            st.write(f"**Prix/pers.** : {f['price_per_person']:.0f}€")
                            st.write(f"**Total** : {f['total_price']:.0f}€")
            # Hôtels disponibles
            st.markdown("---")
            st.markdown("### Hôtels disponibles")
            hotels = result.get("hotels", [])
            if hotels:
                for i, h in enumerate(hotels[:4]):
                    stars_str = "★" * int(h.get("stars", 0)) if h.get("stars") else ""
                    rating = h.get("rating", 0)
                    with st.expander(f"**{h['name']}** {stars_str} — {h['price_per_night']:.0f}€/nuit — Note : {rating}/10"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Prix/nuit** : {h['price_per_night']:.0f}€")
                            st.write(f"**Total {h['days']} nuits** : {h['total_price']:.0f}€")
                        with col2:
                            st.write(f"**Note** : {rating}/10")
                            st.write(f"**Avis** : {h.get('reviews', 0)} avis")
                        with col3:
                            amenities = h.get("amenities", [])
                            if amenities:
                                st.write("**Équipements** : " + ", ".join(amenities[:3]))
                        if h.get("description"):
                            st.caption(h["description"])
                        if h.get("link"):
                            st.markdown(f"[Voir sur Google Hotels]({h['link']})")
        # TAB 4 : ITINÉRAIRE
        with tab4:
            st.markdown(f"### 📅 Itinéraire {origin} → {destination}")

            # Score de voyage
            score_data = result.get("travel_score", {})
            if score_data:
                score = score_data.get("score", 7)
                reasons = score_data.get("reasons", [])
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f'<div class="score-badge">⭐ {score}/10</div>', unsafe_allow_html=True)
                    st.caption("Score de voyage")
                with col2:
                    st.markdown("**Pourquoi ce score :**")
                    for r in reasons:
                        st.markdown(f"• {r}")

            st.markdown("---")

            # Jours
            itinerary = result.get("itinerary", [])
            if itinerary:
                for day_plan in itinerary:
                    weather_note = day_plan.get("weather_note", "")
                    st.markdown(
                        f'<div class="day-card">'
                        f'<h4> Jour {day_plan.get("day", "?")} — {day_plan.get("date", "")} : '
                        f'{day_plan.get("title", "")}</h4>'
                        + (f'<p style="color:#666;font-size:0.85rem;">🌤 {weather_note}</p>' if weather_note else "")
                        + "</div>",
                        unsafe_allow_html=True
                    )
                    activities = day_plan.get("activities", [])
                    for activity in activities:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {activity}")
                    st.markdown("")

            # Conseils
            tips = result.get("tips", [])
            if tips:
                st.markdown("### 💡 Conseils pratiques")
                for tip in tips:
                    st.info(f"💡 {tip}")

        # TAB 5 : EXPORT PDF
        with tab5:
            st.markdown("### 📄 Télécharger l'itinéraire")
            st.markdown("Télécharge ton itinéraire complet en PDF pour l'avoir hors-ligne.")

            try:
                from tools.pdf_tool import generate_pdf

                plan_for_pdf = {
                    "destination": destination,
                    "origin": origin,
                    "dates": f"{depart_date} au {return_date}",
                    "travelers": travelers,
                    "budget": budget,
                    "flight_cost": result.get("flight_cost", 0),
                    "budget_breakdown": result.get("budget_breakdown", {}),
                    "weather": result.get("weather", []),
                    "itinerary": result.get("itinerary", []),
                    "recommendation": result.get("recommendation", {}),
                    "tips": result.get("tips", []),
                    "travel_type": travel_type
                }

                pdf_bytes = generate_pdf(plan_for_pdf)

                st.download_button(
                    label="📥 Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"itineraire_{destination.lower().replace(' ', '_')}_{depart_date}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF prêt au téléchargement !")

            except Exception as e:
                st.error(f"Erreur PDF : {e}")

    except ValueError as e:
        st.error(f"❌ {e}")
        st.info("💡 Entre ta clé API Groq dans la sidebar (console.groq.com)")
    except Exception as e:
        st.error(f"❌ Erreur : {e}")
        st.exception(e)