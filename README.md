# MediGuide AI

A **responsible, multilingual medical assistant** built entirely on **Azure** for the **Microsoft AI Dev Days Hackathon 2026**. MediGuide helps patients understand their health — symptoms, lab reports, medications, and medical images — in clear, simple language across **English, Urdu, Arabic, and Hindi**.

Live App: https://mediguide-ai-evgudghhfrf8hfgy.canadaeast-01.azurewebsites.net
---

## The Problem

Millions of patients receive lab reports they cannot interpret, wait weeks for appointments to ask simple questions, or turn to search engines and find alarming, unreliable information. For **250 million+ Urdu speakers** and large Arabic and Hindi communities, the gap is even wider: healthcare AI in their language is scarce.

---

## Features

| Feature | Description |
|---------|-------------|
| **Symptom Checker** | AI triage agent that always asks follow-up questions before giving any assessment, urgency level (🟢 🟡 🔴), and specialist recommendation |
| **Medical Report Explainer** | Upload a blood test or lab PDF; AI explains every value in plain language and flags abnormal results |
| **Medical Image Analysis** | Upload X-rays or scans; GPT-4o vision describes findings, possible conditions, and urgency |
| **Medication Safety Checker** | Enter multiple medications; AI checks for drug–drug interactions and explains risks |
| **Multilingual** | Full support for English, Urdu, Arabic, and Hindi |
| **Health Literacy Modes** | Simple (easy language, emoji), Standard (balanced), Medical (clinical terminology, ICD codes) |
| **ER Prep Sheet** | Auto-generated downloadable PDF when triage urgency is HIGH — includes latest summary, urgency, and questions for the doctor |
| **Find Doctors Near Me** | Searches the US NPPES registry by specialty (US users only) |
| **Health Timeline** | Visual history of all past health interactions stored in Cosmos DB |
| **Voice Input** | Speak your symptoms using browser speech recognition |

---

## Responsible AI & Scope Restrictions

- **Medical-only scope** — Refuses off-topic queries (programming, jokes, essays, politics, healthcare system explainers, clinical prescribing advice).
- **Mandatory triage flow** — Always asks follow-up questions before providing diagnoses or urgency levels.
- **Crisis support** — Self-harm or suicidal ideation triggers immediate crisis hotline resources.
- **Location consent** — Doctor recommendations only after user confirms their location.
- **Content safety** — Azure Content Safety filters all outputs; jailbreak attempts get a friendly refusal, not raw errors.
- **Disclaimer on every response** — "AI guidance only — not a substitute for professional medical advice."

---

## Authentication

MediGuide supports **Azure App Service Authentication (Easy Auth)** with:

- **Microsoft** — Work or personal Microsoft accounts
- **Google** — Google accounts
- **Guest mode** — Continue without signing in (session stored by browser-generated UUID)

---

## Azure Services Used

| Service | Purpose |
|---------|---------|
| **Azure OpenAI (GPT-4o)** | Chat, triage, report explanation, image analysis, medication safety |
| **Azure AI Translator** | Multilingual responses (English, Urdu, Arabic, Hindi) |
| **Azure AI Content Safety** | Output filtering for harmful content |
| **Azure Cosmos DB** | Session history, health timeline, user preferences |
| **Azure App Service** | Web app hosting + Authentication (Microsoft & Google via Easy Auth) |
| **GitHub Actions** | CI/CD pipeline |

---

## Tech Stack

- **Backend:** Python 3.11+ / Flask / Gunicorn
- **AI:** Azure OpenAI (GPT-4o) with vision support
- **Frontend:** HTML + Tailwind CSS + Vanilla JavaScript
- **Database:** Azure Cosmos DB (NoSQL)
- **PDF Generation:** ReportLab (ER Prep Sheets, Health Timeline reports)
- **Deployment:** Azure App Service (Linux, Canada East)

---

## Project Structure

```
MediGuide/
├── app.py                    # Flask routes and main application
├── config.py                 # Environment variable configuration
├── prompts.py                # All system prompts, scope restrictions, classifiers
├── requirements.txt          # Python dependencies
├── .env.example              # Template for environment variables
├── templates/
│   ├── landing.html          # Sign-in / guest landing page
│   └── index.html            # Main chat interface
├── static/
│   ├── css/styles.css        # Custom styles
│   ├── images/               # Robot mascot, favicon
│   └── js/
│       ├── config.js         # Client-side constants
│       ├── state.js          # Application state
│       ├── api.js            # Fetch wrappers for all API endpoints
│       ├── handlers.js       # Feature switching, forms, file upload
│       ├── render.js         # Message rendering, ER Prep Sheet cards
│       ├── main.js           # Bootstrap, sidebar, literacy mode
│       ├── location.js       # IP-based location detection
│       ├── voice.js          # Voice input (Web Speech API)
│       └── persistence.js    # LocalStorage session persistence
├── services/
│   ├── cosmos_store.py       # Cosmos DB read/write operations
│   ├── translator.py         # Azure AI Translator wrapper
│   └── content_safety.py     # Azure AI Content Safety wrapper
├── utils/
│   ├── files.py              # PDF text extraction, file utilities
│   └── pdf_generator.py      # ER Prep Sheet and Health Timeline PDF generation
└── generate_architecture.py  # Architecture diagram PDF generator
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11 or newer
- An Azure account with access to Azure OpenAI

### 1. Clone and install

```bash
git clone https://github.com/ibrahimzahid777/MediGuide.git
cd MediGuide
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your Azure credentials:

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | Your Azure OpenAI resource URL |
| `AZURE_OPENAI_KEY` | Yes | Your API key |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Deployed model name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | Yes | API version (default: `2024-02-01`) |
| `AZURE_TRANSLATOR_ENDPOINT` | Optional | Azure AI Translator endpoint |
| `AZURE_TRANSLATOR_KEY` | Optional | Translator API key |
| `AZURE_TRANSLATOR_REGION` | Optional | Translator region |
| `AZURE_CONTENT_SAFETY_ENDPOINT` | Optional | Content Safety endpoint |
| `AZURE_CONTENT_SAFETY_KEY` | Optional | Content Safety API key |
| `COSMOSDB_ACCOUNT_URI` | Optional | Cosmos DB account URI |
| `COSMOSDB_ACCOUNT_KEY` | Optional | Cosmos DB account key |
| `COSMOSDB_DATABASE_NAME` | Optional | Cosmos DB database name |
| `COSMOSDB_CONTAINER_NAME` | Optional | Cosmos DB container name |
| `FLASK_SECRET_KEY` | Optional | Flask session secret (set a strong value in production) |

> **Minimum to run:** Only the 4 `AZURE_OPENAI_*` variables are required. Translation, content safety, and Cosmos DB features will gracefully degrade if their credentials are not set.

### 3. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Azure Setup Guide

### Step 1: Create a Free Azure Account

1. Go to [azure.microsoft.com/free](https://azure.microsoft.com/free)
2. Sign up — you get **$200 in free credits** for 30 days

### Step 2: Create an Azure OpenAI Resource

1. Go to [portal.azure.com](https://portal.azure.com) → **+ Create a resource** → search **"Azure OpenAI"**
2. Create with: Resource group `mediguide-rg`, region of your choice, pricing tier `Standard S0`
3. Go to **Keys and Endpoint** → copy **Endpoint** and **KEY 1** into your `.env`

### Step 3: Deploy a Model

1. Go to [ai.azure.com](https://ai.azure.com) (Azure AI Foundry)
2. Create a deployment: choose **gpt-4o** (supports image analysis) or **gpt-4o-mini** (cheaper)
3. Set `AZURE_OPENAI_DEPLOYMENT` in `.env` to match the deployment name

### Step 4: (Optional) Set Up Additional Services

- **Azure AI Translator** — Create a Translator resource; copy endpoint, key, and region
- **Azure AI Content Safety** — Create a Content Safety resource; copy endpoint and key
- **Azure Cosmos DB** — Create a Cosmos DB for NoSQL account; copy URI, key, database name, and container name

### Step 5: Test It

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) and type "I have a headache and fever". If you get follow-up questions from the AI, everything is working.

---

## Deploy to Azure App Service

```bash
az login

az webapp up --name mediguide-ai --runtime PYTHON:3.11

az webapp config appsettings set --name mediguide-ai --resource-group mediguide-rg --settings \
    AZURE_OPENAI_ENDPOINT="your-endpoint" \
    AZURE_OPENAI_KEY="your-key" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    FLASK_SECRET_KEY="your-strong-secret"
```

Your app will be live at `https://mediguide-ai.azurewebsites.net`

To enable Microsoft/Google sign-in, configure **Authentication** in Azure App Service → **Settings → Authentication**.

---

## Architecture

See `MediGuide_Architecture.pdf` for the full system architecture diagram, or run:

```bash
python generate_architecture.py
```

```
User / Browser
      ↕ HTTPS
Azure App Service (Flask + Gunicorn)
      ↓
  ┌───────────┬──────────────┬──────────────┬──────────────┐
  │ Azure     │ Azure        │ Azure AI     │ Azure AI     │
  │ OpenAI    │ Cosmos DB    │ Translator   │ Content      │
  │ (GPT-4o)  │ (NoSQL)      │ (4 langs)    │ Safety       │
  └───────────┴──────────────┴──────────────┴──────────────┘
```

---

## Impact

MediGuide narrows the gap between patients and healthcare: **24/7**, in the user's **own language**, on **any device**. It focuses on underserved populations in South Asia and the Middle East, where healthcare AI in Urdu, Arabic, and Hindi is still rare. By explaining labs, triaging symptoms safely, and checking medications in plain language, it helps people prepare for the doctor, avoid misinformation, and get clearer guidance — without replacing the clinician in the room.

---

## Disclaimer

MediGuide AI provides general health information only and is **not** a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider about your own health.

---

## License

MIT
