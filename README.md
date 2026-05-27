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
| **Azure Developer CLI** (`azd`) | Latest | [Install](https://aka.ms/azd-install) |
| **Python** | 3.11+ | [Download](https://www.python.org/) |
| **Node.js** | 20+ | [Download](https://nodejs.org/) |
| **Docker** | Latest | For local testing and container builds |
| **Git** | Latest | |
| **VS Code** | Latest | Recommended — with Python and Azure extensions |

---

## Setup

### 1. Get Your User Principal ID

The `principalId` parameter is your Azure AD user Object ID — used to grant YOU access to the deployed resources.

```bash
az ad signed-in-user show --query id -o tsv
```

Save this value — you'll need it when running `azd up`.

### 2. Set Up GitHub Actions (Optional — for CI/CD)

If you want automated deployments via GitHub Actions, create an app registration:

```bash
# Create app registration
az ad app create --display-name "foundry-workshop-github"

# Note the appId from the output, then create a service principal
az ad sp create --id <APP_ID>

# Grant Contributor role
az role assignment create \
  --assignee <APP_ID> \
  --role "Contributor" \
  --scope "/subscriptions/<YOUR_SUBSCRIPTION_ID>"

# Grant User Access Administrator (needed for RBAC assignments)
az role assignment create \
  --assignee <APP_ID> \
  --role "User Access Administrator" \
  --scope "/subscriptions/<YOUR_SUBSCRIPTION_ID>"

# Create federated credential for GitHub OIDC
az ad app federated-credential create --id <APP_ID> --parameters '{
  "name": "foundry-workshop-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<YOUR_GITHUB_ORG>/msft-foundry-workshop:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

Then add these GitHub Secrets to your repo (Settings → Secrets → Actions):

| Secret | How to get |
|---|---|
| `AZURE_CLIENT_ID` | The `appId` from `az ad app create` output |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |

And these GitHub Variables (Settings → Variables → Actions):

| Variable | Description | Example |
|---|---|---|
| `AZURE_PRINCIPAL_ID` | **Object ID** of the service principal created above — grants it access to deployed resources. Get it with: `az ad sp show --id <APP_ID> --query id -o tsv` | `xxxxxxxx-...` |
| `AZURE_ENV_NAME` | Name for the azd environment — used as a suffix in all Azure resource names | `dev` |
| `AZURE_LOCATION` | Azure region to deploy to | `centralus` |

> **Important:** `AZURE_PRINCIPAL_ID` is the service principal's **Object ID** (from `az ad sp show`), not the `appId`. These are different values. The Object ID is used to assign RBAC roles so the GitHub Actions runner can create the Foundry agent and access deployed resources.

> **Note:** `AZURE_CLIENT_ID` (app registration for CI/CD) is different from `AZURE_PRINCIPAL_ID` (service principal Object ID for resource access). They serve different purposes.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/zzurlo/msft-foundry-workshop.git
cd msft-foundry-workshop

# Login to Azure
az login
azd auth login

# Deploy everything
azd up

# The command will prompt for:
# - Environment name (e.g., "dev")
# - Azure subscription
# - Azure region (e.g., "centralus")
# - Principal ID (your user object ID)
```

> **Tip:** Find your principal ID with `az ad signed-in-user show --query id -o tsv`

---

## Project Structure

```
msft-foundry-workshop/
├── azure.yaml                      # azd project definition (services, infra path)
├── README.md                       # This file
├── docs/
│   ├── architecture.md             # Detailed architecture explanation
│   └── security.md                 # Security posture documentation
├── infra/
│   ├── main.bicep                  # Bicep orchestrator — wires all modules together
│   ├── main.json                   # Compiled ARM template
│   ├── main.parameters.json        # Default parameter file
│   ├── abbreviations.json          # Resource naming abbreviation map
│   ├── parameters/
│   │   ├── dev.bicepparam          # Dev environment parameters (basic SKU, cost-optimized)
│   │   ├── dev.json                # Dev parameters (JSON format)
│   │   └── prod.bicepparam         # Prod environment parameters
│   └── modules/
│       ├── networking.bicep        # VNet, subnets, NSGs, private DNS zones
│       ├── storage.bicep           # Azure Storage account
│       ├── keyvault.bicep          # Azure Key Vault
│       ├── ai-foundry.bicep        # AI Foundry Hub + Project
│       ├── ai-search.bicep         # Azure AI Search service
│       ├── openai.bicep            # Azure OpenAI (GPT-4o-mini + embeddings)
│       ├── container-apps.bicep    # Container Apps Environment + backend/frontend apps
│       ├── monitoring.bicep        # Log Analytics + Application Insights
│       └── security.bicep          # Managed identity + RBAC role assignments
├── src/
│   ├── backend/
│   │   ├── Dockerfile              # Backend container image
│   │   ├── pyproject.toml          # Python project metadata
│   │   ├── requirements.txt        # Python dependencies
│   │   ├── .env.example            # Environment variable template
│   │   └── app/
│   │       ├── main.py             # FastAPI application entry point
│   │       ├── config.py           # Pydantic settings (env vars)
│   │       ├── agent.py            # AI Foundry Agent setup + lifecycle
│   │       ├── clients.py          # Azure SDK client initialization
│   │       ├── ingestion.py        # Document ingestion pipeline (PDF/DOCX → AI Search)
│   │       ├── search_index.py     # Search index schema definition
│   │       ├── conversation_store.py # Conversation history management
│   │       ├── models.py           # Pydantic request/response models
│   │       └── routers/
│   │           ├── chat.py         # /chat endpoints (streaming + sync)
│   │           ├── conversations.py # /conversations CRUD
│   │           └── documents.py    # /documents upload + management
│   └── frontend/
│       ├── Dockerfile              # Frontend container image
│       ├── nginx.conf              # Nginx config for serving SPA
│       ├── package-lock.json       # Locked dependencies
│       ├── index.html              # HTML entry point
│       ├── vite.config.ts          # Vite bundler config
│       ├── tailwind.config.ts      # Tailwind CSS config
│       ├── tsconfig.json           # TypeScript config
│       ├── .env.example            # Frontend env template
│       └── src/
│           ├── main.tsx            # React app entry
│           ├── App.tsx             # Root component + routing
│           ├── config.ts           # Runtime configuration
│           ├── index.css           # Global styles (Tailwind)
│           ├── api/
│           │   └── client.ts       # API client (fetch wrapper)
│           ├── components/
│           │   ├── Layout.tsx      # App shell / layout
│           │   ├── ChatInput.tsx   # Message input component
│           │   ├── ChatMessage.tsx # Message bubble with citations
│           │   ├── ConversationSidebar.tsx # Conversation list
│           │   ├── DocumentList.tsx # Uploaded documents list
│           │   └── FileUpload.tsx  # Drag-and-drop file upload
│           ├── hooks/
│           │   └── useChat.ts      # Chat hook (streaming support)
│           ├── pages/
│           │   ├── ChatPage.tsx    # Main chat interface
│           │   └── DocumentsPage.tsx # Document management page
│           └── types/
│               └── index.ts        # TypeScript type definitions
└── scripts/
    └── create-index.py             # Utility: manually create AI Search index
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
| `azd up` hangs on container build | Docker not running | Start Docker Desktop and retry |
| AI Search index empty after deploy | Documents not yet ingested | Upload documents via the `/documents` endpoint first |
| `azure.identity.CredentialUnavailableError` | Not logged in locally | Run `az login` and ensure DefaultAzureCredential can pick up creds |

---

## Clean Up

Remove all deployed Azure resources:

```bash
azd down
```

This deletes the resource group and all resources within it. You'll be prompted to confirm.

To also remove the local environment configuration:

```bash
azd down --purge
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Commit your changes (`git commit -m 'feat: add something'`)
4. Push to the branch (`git push origin feature/my-change`)
5. Open a Pull Request

## License

MIT
