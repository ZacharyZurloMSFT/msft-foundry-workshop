# Lab 1: Deploy Infrastructure

⏱️ **Expected time: 15–20 minutes**

## Objective

Deploy all Azure resources for the RAG workshop using the Azure Developer CLI (`azd`). By the end of this lab you will have a fully provisioned environment including Azure AI Foundry, AI Search, Container Apps, Key Vault, Storage, and networking.

## Prerequisites

- Azure subscription with sufficient permissions (Owner or Contributor + User Access Administrator)
- Azure CLI and Azure Developer CLI installed (see [Lab Guide README](README.md))

## Steps

### 1. Clone the repository

```bash
git clone https://github.com/zzurlo/msft-foundry-workshop.git
cd msft-foundry-workshop
```

### 2. Log in to Azure

```bash
# Log in to Azure CLI
az login

# Log in to Azure Developer CLI
azd auth login
```

> **Tip:** If you have multiple subscriptions, set the one you want to use:
> ```bash
> az account set --subscription "<subscription-name-or-id>"
> ```

### 3. Initialize the environment

```bash
azd init
```

When prompted:
- **Environment name:** Choose a short, unique name (e.g., `foundry-workshop-dev`). This becomes a prefix for all resources.
- Accept the defaults for other prompts.

### 4. Deploy everything

```bash
azd up
```

When prompted:
- **Azure subscription:** Select your subscription.
- **Azure location:** Choose a region that supports Azure OpenAI (e.g., `eastus2`, `swedencentral`).

This command will:
1. Provision all infrastructure via Bicep templates (`infra/`)
2. Build and deploy the frontend and backend container apps
3. Configure networking, Key Vault, and managed identities

The deployment takes approximately **10–15 minutes**.

### 5. Note the outputs

When `azd up` completes it prints output values including the **frontend URL**. Copy this — you'll use it in subsequent labs.

```
Outputs:
  frontendUrl: https://<your-app>.azurecontainerapps.io
```

## Verify

### In the terminal

```bash
azd show
```

This lists all deployed resources and their status.

### In the Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com)
2. Navigate to **Resource groups** and find the resource group matching your environment name
3. Confirm these resources exist:

| Resource | Type | What to look for |
|----------|------|-------------------|
| AI Foundry project | `Microsoft.MachineLearningServices/workspaces` | Status: Succeeded |
| AI Search | `Microsoft.Search/searchServices` | Status: Running |
| Container Apps (frontend) | `Microsoft.App/containerApps` | Status: Running |
| Container Apps (backend) | `Microsoft.App/containerApps` | Status: Running |
| Key Vault | `Microsoft.KeyVault/vaults` | Status: Succeeded |
| Storage Account | `Microsoft.Storage/storageAccounts` | Status: Available |
| Container Apps Environment | `Microsoft.App/managedEnvironments` | Status: Succeeded |
| Virtual Network | `Microsoft.Network/virtualNetworks` | Subnets configured |

### Open the app

Open the **frontend URL** from the deployment outputs in your browser. You should see the workshop application's landing page.

## Screenshots guidance

Here's where to look in the Azure Portal to verify each component:

- **Resource Group overview** → Shows all resources at a glance
- **AI Search → Overview** → Check the service is running; note the URL
- **Container Apps → Overview** → Check the provisioning state and URL
- **Key Vault → Secrets** → Verify secrets were created (you won't see values)
- **Virtual Network → Subnets** → Verify subnet configuration

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `azd up` fails with "quota exceeded" | Region doesn't have enough capacity | Try a different region: `azd up --location swedencentral` |
| `azd auth login` hangs | Browser pop-up blocked | Use `azd auth login --use-device-code` |
| "Subscription not found" | Wrong subscription selected | Run `az account set --subscription <id>` then retry |
| Container Apps show "Failed" | Docker build error or missing env vars | Run `azd deploy` to retry just the deployment step |
| "OpenAI resource not available in region" | Region doesn't support Azure OpenAI | Choose `eastus2`, `swedencentral`, or `westus3` |
| Timeout during provisioning | Large Bicep deployment | Wait and retry with `azd provision`; it's idempotent |

## ✅ Checkpoint

Before moving to Lab 2, confirm:
- [ ] `azd up` completed successfully
- [ ] You can see all resources in the Azure Portal
- [ ] The frontend URL loads in your browser

---

**Next:** [Lab 2 — Upload and Index Documents →](lab-02-upload-documents.md)
