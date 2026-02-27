# MediGuide AI

An AI-powered medical Q&A assistant that helps patients understand their symptoms, medications, and medical reports in plain, simple language.

Built with **Azure OpenAI (GPT-4o)**, **Python/Flask**, and **Tailwind CSS** for the Microsoft AI Dev Days Hackathon.

## Features

| Feature | Description |
|---|---|
| **Symptom Checker** | Describe symptoms in everyday language, get possible conditions and urgency levels |
| **Report Explainer** | Upload a medical PDF — AI explains every value in simple language |
| **Medication Info** | Look up any medication for uses, side effects, and interactions |
| **Image Analysis** | Upload X-rays or scans — AI describes findings in plain language |

## Tech Stack

- **Backend:** Python 3.11+ / Flask
- **AI:** Azure OpenAI (GPT-4o / GPT-4o-mini)
- **Frontend:** HTML + Tailwind CSS + Vanilla JavaScript
- **Deployment:** Azure App Service

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11 or newer
- An Azure account with Azure OpenAI access

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/MediGuide-AI.git
cd MediGuide-AI
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your Azure credentials (see the Azure Setup Guide below).

### 3. Run the app

```bash
python app.py
```

Open http://localhost:5000 in your browser.

---

## Azure Setup Guide — What You Need and Where to Get It

You need **2 values** from Azure to make this app work:

| Value | What it is | Where it goes |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI resource URL | `.env` file |
| `AZURE_OPENAI_KEY` | Your API key for authentication | `.env` file |

### Step-by-Step Instructions

#### Step 1: Create a Free Azure Account

1. Go to [azure.microsoft.com/free](https://azure.microsoft.com/free)
2. Click **Start Free** and sign up (requires a credit card for verification — you will NOT be charged)
3. You get **$200 in free credits** for 30 days

#### Step 2: Create an Azure OpenAI Resource

1. Go to [portal.azure.com](https://portal.azure.com)
2. Click **+ Create a resource** (top left)
3. Search for **"Azure OpenAI"** and select it
4. Click **Create**
5. Fill in:
   - **Subscription:** your free subscription
   - **Resource group:** click "Create new" → name it `mediguide-rg`
   - **Region:** pick the closest one to you (e.g., `East US`, `Sweden Central`)
   - **Name:** `mediguide-openai` (or any unique name)
   - **Pricing tier:** `Standard S0`
6. Click **Review + create** → **Create**
7. Wait for deployment to complete, then click **Go to resource**

#### Step 3: Get Your Endpoint and Key

1. In your Azure OpenAI resource page, look at the left sidebar
2. Click **Keys and Endpoint**
3. Copy these two values:
   - **Endpoint** → looks like `https://mediguide-openai.openai.azure.com/`
   - **KEY 1** → a long string of letters and numbers
4. Paste them into your `.env` file:

```
AZURE_OPENAI_ENDPOINT=https://mediguide-openai.openai.azure.com/
AZURE_OPENAI_KEY=abc123your_key_here
```

#### Step 4: Deploy a Model in Azure AI Foundry

1. Go to [ai.azure.com](https://ai.azure.com) (Azure AI Foundry)
2. Select your resource/project
3. Go to **Deployments** in the left sidebar
4. Click **+ Create deployment**
5. Choose model: **gpt-4o-mini** (cheaper, great for hackathon) or **gpt-4o** (more powerful, supports image analysis)
6. Give the deployment a name: `gpt-4o-mini` (keep it the same as the model name for simplicity)
7. Click **Create**
8. Make sure your `.env` file has the matching deployment name:

```
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

#### Step 5: Test It

Run `python app.py`, open http://localhost:5000, and type a symptom like "I have a headache and fever". If you get an AI response, everything is working.

---

## Where Each Azure Value Goes in the Code

```
.env file (YOUR secrets — never commit this):
├── AZURE_OPENAI_ENDPOINT  → Used in config.py → passed to AzureOpenAI client in app.py
├── AZURE_OPENAI_KEY       → Used in config.py → passed to AzureOpenAI client in app.py
├── AZURE_OPENAI_DEPLOYMENT → Used in config.py → the model name in API calls
└── AZURE_OPENAI_API_VERSION → Used in config.py → API version (default works fine)
```

---

## Deploy to Azure App Service

```bash
# Install Azure CLI (if not already installed)
# macOS: brew install azure-cli
# Windows: winget install Microsoft.AzureCLI

# Login to Azure
az login

# Deploy (run from your project folder)
az webapp up --name mediguide-ai --runtime PYTHON:3.11

# Set your environment variables on Azure
az webapp config appsettings set --name mediguide-ai --resource-group <your-rg> --settings \
    AZURE_OPENAI_ENDPOINT="your-endpoint" \
    AZURE_OPENAI_KEY="your-key" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
```

Your app will be live at `https://mediguide-ai.azurewebsites.net`

---

## Disclaimer

MediGuide AI provides general health information only and is **not** a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.

---

## License

MIT
