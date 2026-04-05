# Agent Planificateur de Voyage

Application web intelligente qui génère automatiquement des itinéraires de voyage personnalisés. L'utilisateur indique une destination, une période, un budget et un style de voyage — deux agents IA s'occupent du reste.

**Modèle** : LLaMA 3.3 70B via Groq · **Interface** : Streamlit · **Techniques** : ReAct + Chain of Thought + Self-Correction

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
|  **Sélection intelligente des dates** | L'IA choisit les dates optimales dans une période donnée (météo saisonnière, prix, événements) |
|  **Météo en temps réel** | Prévisions OpenWeatherMap — activités adaptées chaque jour |
|  **Vols réels** | Google Flights via SerpApi — recommandation personnalisée selon profil |
|  **Hôtels réels** | Google Hotels via SerpApi — recommandation selon budget et profil |
|  **Budget intelligent** | Répartition Chain of Thought ajustée au coût de vie de la destination |
|  **Itinéraire jour par jour** | Programme quotidien avec horaires, activités et notes météo |
|  **Chatbot de modification** | Modifications en temps réel sans relancer le pipeline (hôtel, vol, dates, budget, activités) |
|  **Export PDF** | Itinéraire complet téléchargeable |

---

## Techniques de Raisonnement IA

### 1. ReAct (Reasoning + Acting)

La boucle ReAct est au cœur du `VoyageAgent`. Chaque décision suit le cycle **Thought → Action → Observation**, rendu visible dans l'onglet Raisonnement de l'interface.

| Étape | Type | Action |
|---|---|---|
| 0 | Thought / Action / Obs | Analyse la fenêtre temporelle → sélection des dates optimales |
| 1 | Thought / Action / Obs | Collecte météo — OpenWeatherMap |
| 2 | Thought / Action / Obs | Recherche vols — Google Flights |
| 2b | Thought / Action / Obs | Recherche hôtels — Google Hotels |
| 2c | Thought / Action / Obs | Recommandation personnalisée vol + hôtel |
| 3 | Thought / Action / Obs | Répartition du budget (Chain of Thought) |
| 4 | Thought / Action / Obs | Génération de l'itinéraire adapté à la météo |
| 5 | Thought / Action / Obs | Auto-critique du plan (Self-Correction) |
| Final | Thought Final | Validation globale |

### 2. Chain of Thought — Budget

Le LLM décompose le calcul du budget en 6 étapes explicites :

1. Calcul du budget restant après déduction des vols
2. Évaluation du coût de vie de la destination (Tokyo = cher, Bangkok = abordable...)
3. Application des ratios du profil (économique / équilibré / luxe / aventure) ajustés à la destination
4. Calcul des montants exacts par catégorie (hébergement, activités, nourriture, transport, imprévus)
5. Vérification que la somme des catégories égale le budget restant
6. Calcul du budget journalier par personne

> Si le LLM retourne un JSON invalide, un calculateur Python de secours (`budget_tool.py`) prend le relais.

### 3. Self-Correction

Après la génération de l'itinéraire, un second appel LLM joue le rôle d'agent critique et vérifie :
- Les activités sont-elles cohérentes avec la météo prévue ?
- Le budget journalier est-il respecté ?
- Y a-t-il des incohérences dans les horaires ?
- Y a-t-il des hallucinations (lieux ou prix inventés) ?

---

## Les deux agents

### VoyageAgent — Planificateur (`agents/planner_agent.py`)
- Génère le plan complet en une seule exécution
- 5+ appels LLM séquentiels + 3 appels APIs externes
- Implémente les 3 techniques : ReAct, Chain of Thought, Self-Correction
- Résultat : dict JSON complet stocké dans `st.session_state`

### ChatAgent — Modificateur (`agents/chat_agent.py`)
- Modifie le plan existant à la demande, via chat en langage naturel
- 1 seul appel LLM par message, sans appel API externe
- Lit le plan courant comme contexte, retourne uniquement un **patch** (champs modifiés)
- Appliqué chirurgicalement via `apply_updates()` sans régénérer tout le plan

**Ce que le chatbot peut faire :**
- Changer l'hôtel ou le vol (parmi les options déjà récupérées)
- Modifier, ajouter ou supprimer des activités dans l'itinéraire
- Changer les dates → régénère l'itinéraire complet pour les nouvelles dates
- Changer le budget → recalcule toute la répartition
- Répondre à des questions sur la destination

---

## Interface

L'application est organisée en **deux pages** gérées par `st.session_state` :

**Page Formulaire** — interface centrée, sans sidebar
- Période souhaitée (mois de début → mois de fin avec année calculée automatiquement)
- Durée en jours, nombre de voyageurs, budget total
- Profil de voyage : équilibré / économique / luxe / aventure
- Clés API dans un expander rétractable
- Barre de progression pendant le traitement

**Page Résultats** — formulaire masqué, bouton "Nouveau voyage" en haut
- Onglet **Budget** : camembert, métriques, recommandations vol + hôtel, listes disponibles
- Onglet **Itinéraire** : programme jour par jour avec score de voyage et conseils
- Onglet **Export PDF** : téléchargement direct
- Onglet **Raisonnement** : trace complète ReAct + CoT + Self-Correction
- **Chatbot** en bas de page pour modifications en temps réel

---

## Installation

```bash
# 1. Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Créer le fichier .env
GROQ_API_KEY=ta_cle_groq
OPENWEATHER_API_KEY=ta_cle_openweather  # optionnel
SERPAPI_API_KEY=ta_cle_serpapi          # optionnel

# 4. Lancer l'application
streamlit run app.py
```

## Clés API

| Service | Usage |  Lien |
|---|---|---|
| **Groq** | LLM LLaMA 3.3 70B |  [console.groq.com](https://console.groq.com) |
| OpenWeatherMap | Météo réelle | [openweathermap.org](https://openweathermap.org/api) |
| SerpApi | Vols et hôtels réels |  [serpapi.com](https://serpapi.com) |

---

## Structure du projet

```
voyage-agent/
├── app.py                        # Application Streamlit (2 pages : formulaire / résultats)
├── requirements.txt
├── .env
├── agents/
│   ├── planner_agent.py          # VoyageAgent — pipeline complet (ReAct + CoT + Self-Correction)
│   └── chat_agent.py             # ChatAgent — modifications conversationnelles en temps réel
├── tools/
│   ├── weather_tool.py           # Météo — OpenWeatherMap
│   ├── flights_tool.py           # Vols — Google Flights (SerpApi)
│   ├── hotels_tool.py            # Hôtels — Google Hotels (SerpApi)
│   ├── budget_tool.py            # Calculateur budget Python (fallback CoT)
│   └── pdf_tool.py               # Export PDF — ReportLab
├── prompts/
│   └── system_prompt.py          # Tous les prompts LLM (ReAct, CoT, Self-Correction, Chat, Dates)
└── css/
    └── styles.css
```

---

## Contexte académique

Projet réalisé dans le cadre du cours **IA Générative** — Agents Intelligents, Raisonnement Avancé & Streamlit.
