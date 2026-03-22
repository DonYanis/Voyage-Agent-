# Agent Planificateur de Voyage

Application Streamlit utilisant un agent LLM (LLaMA 3 via Groq) pour planifier des voyages personnalisés avec raisonnement avancé.

## Fonctionnalités

- **Météo en temps réel** via OpenWeatherMap API
- **Recherche de vols et Hotels** avec prix via Serp API
- **Répartition intelligente du budget** selon le profil de voyage
- **Itinéraire jour par jour** adapté à la météo
- **Export PDF** de l'itinéraire complet
- **Raisonnement visible** (Thought / Action / Observation)

## Techniques de Raisonnement

### 1. ReAct (Reason + Act) — Technique principale
La boucle ReAct est au cœur de l'agent. Pour chaque décision, l'agent :
- **Thought** : Réfléchit à ce qu'il doit faire
- **Action** : Appelle un outil (météo, vols,hotels, budget)
- **Observation** : Analyse le résultat
- Répète jusqu'à la réponse finale

Exemple concret : si la météo indique de la pluie le jour 2, l'agent détecte cela dans sa phase Thought et adapte les activités (musées, restaurants couverts) lors de l'Action suivante.

### 2. Chain of Thought (CoT) — Budget
Pour la répartition du budget, l'agent décompose explicitement le problème en étapes :
1. Calculer le budget restant après les vols
2. Appliquer les ratios selon le profil (économique/équilibré/luxe/aventure)
3. Calculer les montants par catégorie
4. Vérifier que la somme = budget restant
5. Calculer le budget journalier par personne

### 3. Self-Correction — Vérification du plan
Après avoir généré l'itinéraire, l'agent se critique lui-même :
- Les activités sont-elles adaptées à la météo ?
- Le budget est-il respecté ?
- Y a-t-il des incohérences horaires ?
- Y a-t-il des informations inventées (hallucinations) ?
Il génère ensuite une version corrigée si nécessaire.

## Installation
### Avec un env virtuel :
```bash
# 1. créer l'environnement virtuel
python -m venv .venv

# 2. activer l'env virtuel
.venv\Scripts\activate   # (Windows)
# ou
source .venv/bin/activate  # (Mac/Linux)

# 3. installer les dépendances
pip install streamlit groq requests python-dotenv reportlab plotly google-search-results
# ou avec  : 
pip install -r requirements.txt


# 4. créer le fichier .env à la racine du projet et ajouter :
GROQ_API_KEY=ta_cle_groq
OPENWEATHER_API_KEY=ta_cle_openweather
SERPAPI_API_KEY=ta_cle_serpapi

# 5. lancer l'app
streamlit run app.py

```

##  Clés API

| Service | Usage | Lien |
|---------|-------|------|
| **Groq** | LLM (LLaMA 3) | [console.groq.com](https://console.groq.com) |
| OpenWeatherMap | Météo réelle | [openweathermap.org](https://openweathermap.org/api) |
| Serpapi | Vols et Hotels réels | [serpapi.com](https://serpapi.com/users/welcome) |


## Structure du projet

```
voyage-agent/
├── app.py                    # Application Streamlit
├── requirements.txt          # Dépendances Python
├── .env                      # variables d'environnement
├── agents/
│   └── planner_agent.py     # Agent principal (ReAct + CoT + Self-Correction)
├── css/
│   └── styles.css           # code css
├── tools/
│   ├── weather_tool.py      # Outil météo (OpenWeatherMap)
│   ├── flights_tool.py      # Outil vols (Amadeus)
│   ├── budget_tool.py       # Outil budget (CoT)
│   └── pdf_tool.py          # Export PDF (ReportLab)
└── prompts/
    └── system_prompt.py     # Prompts système (ReAct, CoT, Self-Correction)
```

## Contexte académique

Projet réalisé dans le cadre du cours **IA Générative** — Agents Intelligents, Raisonnement Avancé & Streamlit.

- **Modèle** : LLaMA 3.3 70B (Groq, gratuit)
- **Techniques** : ReAct + Chain of Thought + Self-Correction
- **Interface** : Streamlit
- **APIs** : OpenWeatherMap, Serpapi, Groq
