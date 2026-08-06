# Azure AI Foundry Workshop — Build a RAG Chat Application

Build and deploy an enterprise-grade **Retrieval-Augmented Generation (RAG)** application using **Azure AI Foundry**, **Azure AI Search**, and **Azure Container Apps**.

**What you'll build:** A chat application that answers questions from your uploaded documents — powered by GPT-4o-mini with grounded, cited responses from Azure AI Search.

---

## Architecture

```
                         ┌──────────────────────────────────────────────────────┐
                         │              Azure Resource Group (VNet)             │
                         │                                                      │
  ┌──────┐   HTTPS       │  ┌────────────┐        ┌─────────────────────────┐  │
  │ User │──────────────►│  │  Frontend   │  HTTP  │       Backend           │  │
  │      │◄──────────────│  │  (React on  │───────►│   (FastAPI on ACA)      │  │
  └──────┘               │  │   ACA)      │        │                         │  │
                         │  └────────────┘        │  ┌───────────────────┐  │  │
                         │                         │  │ AI Foundry Agent  │  │  │
                         │                         │  └────────┬──────────┘  │  │
                         │                         └───────────┼─────────────┘  │
                         │                                     │                │
                         │                    ┌────────────────┼────────────┐   │
                         │                    ▼                ▼            │   │
                         │  ┌──────────────────┐  ┌──────────────────────┐ │   │
                         │  │  Azure OpenAI     │  │  Azure AI Search    │ │   │
                         │  │  (GPT-4o-mini)    │  │  (vector + semantic)│ │   │
                         │  └──────────────────┘  └──────────┬───────────┘ │   │
                         │                                    ▲            │   │
                         │                         ┌──────────┴──────────┐ │   │
                         │  ┌─────────────┐        │ Ingestion Pipeline  │ │   │
                         │  │  Documents  │───────►│  (PDF/DOCX → Index) │ │   │
                         │  └─────────────┘        └─────────────────────┘ │   │
                         │                                                  │   │
                         │  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │   │
                         │  │ Key Vault │ │  Storage  │ │  Monitoring   │  │   │
                         │  └───────────┘ └───────────┘ └───────────────┘  │   │
                         │         (All behind private endpoints)           │   │
                         └──────────────────────────────────────────────────────┘
```

> For a detailed architecture walkthrough, see [docs/architecture.md](docs/architecture.md).
> For security details, see [docs/security.md](docs/security.md).

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Azure subscription** | — | With ability to create AI services and Owner/Contributor access |
| **Azure CLI** (`az`) | Latest | [Install](https://docs.microsoft.com/cli/azure/install-azure-cli) |
| **PowerShell** | 7+ (or Windows PowerShell 5.1) | Used to drive the deploy scripts |
| **Python** | 3.11+ | For the post-deploy index + agent scripts |
| **Git** | Latest | |
| **VS Code** | Latest | Recommended — with Python and Azure extensions |

> Docker and Node.js are **not required** — container images are built server-side by `az acr build`.

---

## Quick Start

The whole stack deploys with one PowerShell command. It calls Bicep for infrastructure, then `az` CLI for everything else (image builds, container app updates, search index, Foundry agent, sample docs).

```powershell
# Clone the repo
git clone https://github.com/zzurlo/msft-foundry-workshop.git
cd msft-foundry-workshop

# Sign in
az login

# Deploy everything (infra → images → apps → index → agent → sample docs)
.\scripts\deploy-all.ps1 -EnvironmentName dev -Location centralus
```

The orchestrator runs each stage in order and prints the final frontend/backend URLs when done. Deployment outputs are cached to `.deploy-state/outputs.json` so you can re-run individual stages without redeploying infra.

### Running individual stages

If you'd rather run stages one at a time (useful for debugging or iterating on app code):

| Stage | Script | What it does |
|---|---|---|
| 1 | `scripts\deploy-infra.ps1`   | `az deployment group create` against `infra\main.bicep` |
| 2 | `scripts\build-and-push.ps1` | `az acr build` backend + frontend images into ACR |
| 3 | `scripts\update-apps.ps1`    | `az containerapp update` to swap placeholder images |
| 4 | `scripts\create-index.ps1`   | Creates/updates the Azure AI Search index |
| 5 | `scripts\setup-agent.ps1`    | Creates the Foundry agent, sets `AGENT_ID` on the backend |
| 6 | `scripts\seed-documents.ps1` | Uploads `docs\samples\*.txt` to the backend for indexing |

Re-run any stage on its own — for example, `scripts\build-and-push.ps1` followed by `scripts\update-apps.ps1` to ship a code change without touching infra.

### Common flags

```powershell
# Different environment / region
.\scripts\deploy-all.ps1 -EnvironmentName prod -Location eastus2

# Deploy without seeding sample data
.\scripts\deploy-all.ps1 -SkipSeed

# Pin to a specific subscription
.\scripts\deploy-all.ps1 -SubscriptionId <guid>
```

> **Tip:** The scripts auto-resolve your `principalId` from `az ad signed-in-user show`. Pass `-PrincipalId <guid>` to override.

---

## Project Structure

```
msft-foundry-workshop/
├── README.md                       # This file
├── docs/
│   ├── architecture.md             # Detailed architecture explanation
│   ├── security.md                 # Security posture documentation
│   ├── labs/                       # Workshop labs (5 modules)
│   └── samples/                    # Sample .txt files for seeding
├── infra/
│   ├── main.bicep                  # Bicep orchestrator — wires all modules together
│   ├── main.parameters.json        # Default parameter file
│   ├── abbreviations.json          # Resource naming abbreviation map
│   ├── parameters/
│   │   ├── dev.bicepparam          # Dev environment parameters (basic SKU)
│   │   └── prod.bicepparam         # Prod environment parameters
│   └── modules/
│       ├── networking.bicep        # VNet, subnets, NSGs, private DNS zones
│       ├── storage.bicep           # Azure Storage account
│       ├── keyvault.bicep          # Azure Key Vault
│       ├── ai-foundry.bicep        # AI Foundry Hub + Project
│       ├── ai-search.bicep         # Azure AI Search service
│       ├── container-apps.bicep    # Container Apps Environment + ACR + backend/frontend
│       ├── monitoring.bicep        # Log Analytics + Application Insights
│       └── security.bicep          # Managed identity + RBAC role assignments
├── scripts/
│   ├── _common.ps1                 # Shared helpers (state, logging)
│   ├── deploy-all.ps1              # One-shot orchestrator
│   ├── deploy-infra.ps1            # Stage 1: Bicep deployment
│   ├── build-and-push.ps1          # Stage 2: az acr build for images
│   ├── update-apps.ps1             # Stage 3: swap placeholder images
│   ├── create-index.ps1            # Stage 4: create/update Search index
│   ├── setup-agent.ps1             # Stage 5: create Foundry agent
│   ├── seed-documents.ps1          # Stage 6: upload docs/samples
│   ├── create-index.py             # Python helper (called by create-index.ps1)
│   └── setup-agent.py              # Python helper (called by setup-agent.ps1)
├── src/
│   ├── backend/                    # FastAPI + Python (see .env.example)
│   └── frontend/                   # React + Vite + Tailwind
└── .deploy-state/                  # (gitignored) Cached Bicep outputs
```

---

## What Gets Deployed

| Resource | Azure Service | Description | Approx. Monthly Cost |
|---|---|---|---|
| Virtual Network | VNet + Subnets + NSGs | Network isolation with private endpoints | Free |
| Private DNS Zones | Azure DNS | Name resolution for private endpoints | ~$0.50/zone |
| AI Foundry Hub + Project | Azure AI Foundry | Orchestration hub for AI services | Free (pay for compute) |
| OpenAI Service | Azure OpenAI | GPT-4o-mini (chat) + text-embedding-ada-002 | ~$1–10 (usage-based) |
| AI Search | Azure AI Search (Basic) | Vector + semantic search index | ~$75 (Basic SKU) |
| Storage Account | Azure Blob Storage | Document storage + AI Foundry data | ~$1–5 |
| Key Vault | Azure Key Vault | Secrets and certificate management | ~$0.03/operation |
| Container Apps | Azure Container Apps | Backend (FastAPI) + Frontend (React/Nginx) | ~$0–20 (consumption plan) |
| Log Analytics + App Insights | Azure Monitor | Logging, metrics, distributed tracing | ~$2–10 |
| Managed Identity | User-Assigned MI | Passwordless auth between services | Free |
| **Total estimate** | | | **~$80–120/month** |

> Costs vary by region and usage. The dev parameter file uses Basic SKUs to minimize workshop costs.

---

## Configuration

### Backend Environment Variables

| Variable | Description | Default |
|---|---|---|
| `AZURE_AI_PROJECT_CONNECTION_STRING` | AI Foundry project connection string | — (required) |
| `AZURE_AI_SEARCH_INDEX_NAME` | Name of the AI Search index | `default-index` |
| `AZURE_AI_SEARCH_CONNECTION_NAME` | AI Search connection name in AI Foundry | — (required) |
| `AGENT_MODEL` | OpenAI model for the agent | `gpt-4o-mini` |
| `AGENT_ID` | Reuse an existing agent (skip creation) | — (optional) |

### Frontend Environment Variables

| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000` |

### Customizing the AI Agent

The agent's system instructions are defined in `src/backend/app/agent.py` in the `AGENT_INSTRUCTIONS` constant:

```python
AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that answers questions based on the "
    "provided documents. Always cite your sources. If you don't know "
    "the answer, say so."
)
```

Edit this string to change the agent's behavior, tone, or domain focus.

### Changing the OpenAI Model

Update the `AGENT_MODEL` environment variable or edit `src/backend/app/config.py`:

```python
agent_model: str = "gpt-4o-mini"  # Change to "gpt-4o" for higher quality
```

---

## Local Development

### Backend

```bash
cd src/backend

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your Azure resource values

# Run the dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd src/frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
# → http://localhost:5173
```

### Running Both Together

Open two terminal windows or use a process manager. The frontend proxies API calls to the backend at `http://localhost:8000` by default (configured via `VITE_API_BASE_URL`).

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `QuotaExceeded` on OpenAI deployment | Region doesn't have GPT-4o-mini quota | Try a different region (`eastus`, `centralus`, `swedencentral`) |
| `InvalidTemplateDeployment` | Missing required parameters | Ensure `principalId` is set — run `az ad signed-in-user show --query id -o tsv` |
| `AuthorizationFailed` | Insufficient subscription permissions | You need Owner or Contributor + User Access Administrator roles |
| Private endpoint DNS not resolving | VNet DNS not configured | Ensure private DNS zones are linked to the VNet (handled by Bicep) |
| Frontend shows "Network Error" | Backend not running or CORS issue | Check `VITE_API_BASE_URL` matches the backend URL |
| `azd up` hangs on container build | Docker not running | The new flow uses `az acr build` — no local Docker needed. If you see this, you're on an older README/script. |
| `az acr build` fails with "resource not found" | ACR not yet created | Run `scripts\deploy-infra.ps1` first — infra must exist before pushing images. |
| AI Search index empty after deploy | Documents not yet ingested | Upload documents via the `/documents` endpoint first |
| `azure.identity.CredentialUnavailableError` | Not logged in locally | Run `az login` and ensure DefaultAzureCredential can pick up creds |

---

## Clean Up

Remove all deployed Azure resources by deleting the resource group:

```powershell
az group delete --name rg-dev --yes --no-wait
Remove-Item .deploy-state -Recurse -Force
```

---

## License

MIT
