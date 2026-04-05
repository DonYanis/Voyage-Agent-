import streamlit as st
import plotly.graph_objects as go
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

# CONFIG PAGE
st.set_page_config(
    page_title="Agent Planificateur de Voyage",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS
with open("css/styles.css", "r") as f:
    css = f.read()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Hide sidebar entirely
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "form"
if "result" not in st.session_state:
    st.session_state["result"] = None
if "trip_params" not in st.session_state:
    st.session_state["trip_params"] = {}

# ── HELPERS ────────────────────────────────────────────────────────────────────
MONTHS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
             "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTHS_FR)}


def go_home():
    st.session_state["page"] = "form"
    st.session_state["result"] = None
    st.session_state["trip_params"] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE FORMULAIRE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["page"] == "form":

    # Header
    st.markdown('<div class="main-title">✈️ Agent Planificateur de Voyage</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#888;font-size:1rem;'>"
        "Décris ton voyage, l'IA s'occupe du reste — dates, vols, hôtels, budget et itinéraire."
        "<br><small>Powered by LLaMA 3 · ReAct · Chain of Thought · Self-Correction</small>"
        "</p>",
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── FORM ──
    with st.form("voyage_form"):

        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("Ville de départ", value="Paris", placeholder="Ex: Paris")
        with col2:
            destination = st.text_input("Destination", value="Tokyo", placeholder="Ex: Tokyo, Bali...")

        st.markdown("**Période souhaitée**")
        col1, col2 = st.columns(2)
        with col1:
            period_start = st.selectbox("Mois de début", MONTHS_FR, index=5)
        with col2:
            period_end = st.selectbox("Mois de fin", MONTHS_FR, index=7)

        # Compute years and show them
        today = date.today()
        start_month_num = MONTH_NUM[period_start]
        end_month_num = MONTH_NUM[period_end]
        start_year = today.year if start_month_num >= today.month else today.year + 1
        end_year = start_year if end_month_num >= start_month_num else start_year + 1

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"📅 {period_start} **{start_year}**")
        with col2:
            st.caption(f"📅 {period_end} **{end_year}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            trip_days = st.number_input("Durée (jours)", min_value=1, max_value=90, value=7, step=1)
        with col2:
            travelers = st.slider("Voyageurs", 1, 8, 2)
        with col3:
            budget = st.number_input(
                "Budget total (€)",
                min_value=200, max_value=50000, value=3000, step=100,
                help="Budget total pour tous les voyageurs, vols inclus"
            )

        travel_type = st.selectbox(
            "Type de voyage",
            ["équilibré", "économique", "luxe", "aventure"],
            index=0
        )

        with st.expander("🔑 Clés API"):
            groq_key    = st.text_input("Groq API Key (obligatoire)", type="password",
                                         value=os.getenv("GROQ_API_KEY", ""),
                                         help="Gratuit sur console.groq.com")
            weather_key = st.text_input("OpenWeather Key (optionnel)", type="password",
                                         value=os.getenv("OPENWEATHER_API_KEY", ""),
                                         help="Gratuit sur openweathermap.org")
            serpapi_key = st.text_input("SerpApi Key (optionnel)", type="password",
                                         value=os.getenv("SERPAPI_API_KEY", ""),
                                         help="Gratuit sur serpapi.com")

        submitted = st.form_submit_button("🚀 Planifier mon voyage !", use_container_width=True)

    # ── ON SUBMIT ──
    if submitted:
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key
        if weather_key:
            os.environ["OPENWEATHER_API_KEY"] = weather_key
        if serpapi_key:
            os.environ["SERPAPI_API_KEY"] = serpapi_key

        if not os.getenv("GROQ_API_KEY"):
            st.error("❌ Clé Groq manquante. Renseigne-la dans la section Clés API.")
            st.stop()

        # Progress UI (shown while form is still visible, then we rerun to results)
        progress_bar = st.progress(0)
        status_text  = st.empty()

        def update_progress(msg):
            steps_map = {
                "Sélection des meilleures dates...": 10,
                "Recherche des données météo...": 25,
                "Recherche des vols disponibles...": 42,
                "Recherche des hôtels disponibles...": 52,
                "Le LLM analyse et recommande le meilleur vol et hôtel...": 57,
                "Calcul de la répartition du budget...": 65,
                "Génération de l'itinéraire personnalisé...": 82,
                "Vérification et correction du plan...": 95,
            }
            progress_bar.progress(steps_map.get(msg, 50))
            status_text.markdown(f"**{msg}**")

        try:
            from agents.planner_agent import VoyageAgent
            agent = VoyageAgent()

            update_progress("Sélection des meilleures dates...")
            origin_iata = agent.get_iata_from_llm(origin)
            dest_iata   = agent.get_iata_from_llm(destination)

            params = {
                "origin":       origin,
                "destination":  destination,
                "period_start": f"{period_start} {start_year}",
                "period_end":   f"{period_end} {end_year}",
                "year":         start_year,
                "trip_days":    int(trip_days),
                "budget":       budget,
                "travelers":    travelers,
                "travel_type":  travel_type,
                "origin_iata":  origin_iata,
                "dest_iata":    dest_iata,
            }

            with st.spinner("L'agent planifie ton voyage..."):
                result = agent.plan(params, progress_callback=update_progress)

            progress_bar.progress(100)
            status_text.markdown("**Plan généré !**")

            st.session_state["result"]      = result
            st.session_state["trip_params"] = params
            st.session_state["page"]        = "results"
            st.rerun()

        except ValueError as e:
            st.error(f"❌ {e}")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")
            st.exception(e)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE RÉSULTATS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "results":

    result      = st.session_state["result"]
    params      = st.session_state["trip_params"]
    origin      = params.get("origin", "")
    destination = params.get("destination", "")
    travelers   = params.get("travelers", 1)
    budget      = params.get("budget", 0)
    travel_type = params.get("travel_type", "")

    depart_date = result["depart_date"]
    return_date = result["return_date"]
    days        = result["days"]

    # ── HOME BUTTON ──
    if st.button("⬅️ Nouveau voyage", type="secondary"):
        go_home()
        st.rerun()

    st.markdown("---")

    # ── TRIP HEADER ──
    st.markdown(
        f'<div class="main-title" style="font-size:1.6rem;">'
        f'✈️ {origin} → {destination}</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='text-align:center;color:#666;'>"
        f"{days} jours · {depart_date} → {return_date} · "
        f"{travelers} voyageur(s) · {budget}€ · {travel_type}"
        f"</p>",
        unsafe_allow_html=True
    )

    date_info = result.get("selected_dates", {})
    if date_info.get("explanation"):
        st.info(f"📅 **Pourquoi ces dates ?** {date_info['explanation']}")

    # ── TABS ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧠 Raisonnement", "💰 Budget", "📅 Itinéraire", "📄 Export PDF"
    ])

    # TAB 1 : RAISONNEMENT
    with tab1:
        st.markdown("### 🧠 Raisonnement de l'agent (ReAct)")
        st.markdown("*Voici comment l'agent a raisonné pour construire ton voyage :*")
        st.markdown("---")

        for step in result.get("reasoning_steps", []):
            stype   = step["type"]
            content = step["content"]
            if stype == "thought":
                st.markdown(f'<div class="thought-box"><b>Thought</b> — {content}</div>',
                            unsafe_allow_html=True)
            elif stype == "action":
                st.markdown(f'<div class="action-box"><b>Action</b> — {content}</div>',
                            unsafe_allow_html=True)
            elif stype == "observation":
                st.markdown(f'<div class="obs-box"><b>Observation</b> — {content}</div>',
                            unsafe_allow_html=True)
            elif stype == "final":
                st.markdown(f'<div class="final-box">{content}</div>',
                            unsafe_allow_html=True)

        if date_info.get("reasoning"):
            st.markdown("---")
            st.markdown("### Sélection des dates (ReAct — Étape 0)")
            st.markdown("*Voici comment l'agent a choisi les dates optimales :*")
            st.markdown(f'<div class="thought-box">{date_info["reasoning"]}</div>',
                        unsafe_allow_html=True)

        if result.get("cot_budget"):
            st.markdown("---")
            st.markdown("### Raisonnement budget (Chain of Thought)")
            st.markdown("*Voici comment l'agent a raisonné pour répartir le budget :*")
            st.markdown(f'<div class="thought-box">{result["cot_budget"]}</div>',
                        unsafe_allow_html=True)

        if result.get("correction"):
            st.markdown("---")
            st.markdown("### Auto-correction (Self-Correction)")
            st.info(result["correction"])

    # TAB 2 : BUDGET
    with tab2:
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

            dest_note = budget_data.get("destination_note", "")
            if dest_note:
                st.info(f"💡 {dest_note}")
            st.markdown("---")

            breakdown = budget_data.get("breakdown", {})
            if breakdown:
                labels     = ["Vols"] + [k.replace("_", " ").capitalize() for k in breakdown]
                values     = [budget_data["flight_cost"]] + [v["total"] for v in breakdown.values()]
                colors_pie = ["#2E86AB", "#F18F01", "#28B463", "#E74C3C", "#8E44AD", "#F39C12"]

                fig_pie = go.Figure(data=[go.Pie(
                    labels=labels, values=values, hole=0.4,
                    marker=dict(colors=colors_pie)
                )])
                fig_pie.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Détail par catégorie :**")
                    for cat, vals in breakdown.items():
                        st.markdown(
                            f"- **{cat.replace('_', ' ').capitalize()}** : "
                            f"{vals['total']:.0f}€ total / {vals['per_person_per_day']:.0f}€ pers/jour"
                        )
                with col_b:
                    st.metric("💸 Budget journalier / personne",
                              f"{budget_data.get('daily_per_person', 0):.0f}€")

        st.markdown("---")

        # Recommandation LLM
        recommendation = result.get("recommendation", {})
        if recommendation:
            rec_f   = recommendation.get("recommended_flight", {})
            rec_h   = recommendation.get("recommended_hotel", {})
            summary = recommendation.get("global_summary", "")

            st.markdown("### Recommandation de l'agent")
            if summary:
                st.info(summary)

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

        # Vols disponibles
        st.markdown("### Vols disponibles")
        flights = result.get("flights", [])
        if flights:
            for f in flights[:3]:
                stops = "Direct" if f["stops"] == 0 else f"{f['stops']} escale(s)"
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
        else:
            st.caption("Aucun vol trouvé (clé SerpApi non configurée).")

        st.markdown("---")

        # Hôtels disponibles
        st.markdown("### Hôtels disponibles")
        hotels = result.get("hotels", [])
        if hotels:
            for h in hotels[:4]:
                stars_str = "★" * int(h.get("stars", 0)) if h.get("stars") else ""
                rating    = h.get("rating", 0)
                with st.expander(
                    f"**{h['name']}** {stars_str} — {h['price_per_night']:.0f}€/nuit — Note : {rating}/10"
                ):
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
        else:
            st.caption("Aucun hôtel trouvé (clé SerpApi non configurée).")

    # TAB 3 : ITINÉRAIRE
    with tab3:
        st.markdown(f"### 📅 Itinéraire {origin} → {destination}")

        score_data = result.get("travel_score", {})
        if score_data:
            score   = score_data.get("score", 7)
            reasons = score_data.get("reasons", [])
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f'<div class="score-badge">⭐ {score}/10</div>',
                            unsafe_allow_html=True)
                st.caption("Score de voyage")
            with col2:
                st.markdown("**Pourquoi ce score :**")
                for r in reasons:
                    st.markdown(f"• {r}")

        st.markdown("---")

        itinerary = result.get("itinerary", [])
        if itinerary:
            for day_plan in itinerary:
                weather_note = day_plan.get("weather_note", "")
                st.markdown(
                    f'<div class="day-card">'
                    f'<h4>Jour {day_plan.get("day", "?")} — {day_plan.get("date", "")} : '
                    f'{day_plan.get("title", "")}</h4>'
                    + (f'<p style="color:#666;font-size:0.85rem;">🌤 {weather_note}</p>'
                       if weather_note else "")
                    + "</div>",
                    unsafe_allow_html=True
                )
                for activity in day_plan.get("activities", []):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {activity}")
                st.markdown("")

        tips = result.get("tips", [])
        if tips:
            st.markdown("### 💡 Conseils pratiques")
            for tip in tips:
                st.info(f"💡 {tip}")

    # TAB 4 : EXPORT PDF
    with tab4:
        st.markdown("### 📄 Télécharger l'itinéraire")
        st.markdown("Télécharge ton itinéraire complet en PDF pour l'avoir hors-ligne.")

        try:
            from tools.pdf_tool import generate_pdf

            plan_for_pdf = {
                "destination":      destination,
                "origin":           origin,
                "dates":            f"{depart_date} au {return_date}",
                "travelers":        travelers,
                "budget":           budget,
                "flight_cost":      result.get("flight_cost", 0),
                "budget_breakdown": result.get("budget_breakdown", {}),
                "weather":          result.get("weather", []),
                "itinerary":        result.get("itinerary", []),
                "recommendation":   result.get("recommendation", {}),
                "tips":             result.get("tips", []),
                "travel_type":      travel_type,
            }

            pdf_bytes = generate_pdf(plan_for_pdf)
            st.download_button(
                label="📥 Télécharger le PDF",
                data=pdf_bytes,
                file_name=f"itineraire_{destination.lower().replace(' ', '_')}_{depart_date[:7]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.success("PDF prêt au téléchargement !")

        except Exception as e:
            st.error(f"Erreur PDF : {e}")
