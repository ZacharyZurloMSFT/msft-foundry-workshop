# Lab 1: Deploy Infrastructure

⏱️ **Expected time: 15–20 minutes**

## Objective

Deploy all Azure resources for the RAG workshop using **Bicep** for infrastructure and **`az` CLI** PowerShell scripts for images, container updates, the Search index, and the Foundry agent. By the end of this lab you'll have a fully provisioned environment: Azure AI Foundry, AI Search, Container Apps, Key Vault, Storage, and networking — all deployed and ready.

## Prerequisites

- Azure subscription with sufficient permissions (Owner, or Contributor + User Access Administrator)
- Azure CLI (`az`) and PowerShell 7+ installed (see the main [README](../../README.md))

## Steps

### 1. Clone the repository

```powershell
git clone https://github.com/zzurlo/msft-foundry-workshop.git
cd msft-foundry-workshop
```

### 2. Log in to Azure

```powershell
az login
```

> **Tip:** If you have multiple subscriptions, set the one you want to use:
> ```powershell
> az account set --subscription "<subscription-name-or-id>"
> ```

### 3. Deploy everything

Run the one-shot orchestrator:

```powershell
.\scripts\deploy-all.ps1 -EnvironmentName dev -Location centralus
```

This runs:

| # | Stage | What happens |
|---|---|---|
| 1 | `.\scripts\deploy-infra.ps1`   | Bicep infrastructure (VNet + private endpoints, AI Foundry, AI Search, Container Apps env + ACR, Key Vault, Storage, Log Analytics, managed identity + RBAC) |
| 2 | `.\scripts\build-and-push.ps1` | `az acr build` backend + frontend images |
| 3 | `.\scripts\update-apps.ps1`    | Swap placeholder images for the real ones |
| 4 | *(automatic)*                  | Backend startup creates the Search index, creates the Foundry agent, and seeds the built-in sample documents |

The deployment takes approximately **10–15 minutes** end-to-end. Foundry data-plane RBAC propagation adds ~5–10 minutes before the first chat request works.

### 4. Note the outputs

When `deploy-all.ps1` finishes it prints the frontend and backend URLs. All Bicep outputs are also cached to `.deploy-state\outputs.json` — you can re-run any single stage script and it will pick them up automatically.

```
✔ Deploy complete
  Frontend: https://ca-frontend-dev.<region>.azurecontainerapps.io
  Backend:  https://ca-backend-dev.<region>.azurecontainerapps.io
```

## Verify

### From the CLI

```powershell
az resource list --resource-group rg-dev --output table
```

### In the Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com)
2. Open resource group **`rg-dev`**
3. Confirm these resources exist:

| Resource | Type | What to look for |
|----------|------|-------------------|
| AI Foundry account + project | `Microsoft.CognitiveServices/accounts` | Status: Succeeded |
| AI Search | `Microsoft.Search/searchServices` | Status: Running |
| Container Apps (frontend) | `Microsoft.App/containerApps` | Status: Running |
| Container Apps (backend) | `Microsoft.App/containerApps` | Status: Running |
| Key Vault | `Microsoft.KeyVault/vaults` | Status: Succeeded |
| Storage Account | `Microsoft.Storage/storageAccounts` | Status: Available |
| Container Apps Environment | `Microsoft.App/managedEnvironments` | Status: Succeeded |
| Virtual Network | `Microsoft.Network/virtualNetworks` | Subnets configured |
| Container Registry | `Microsoft.ContainerRegistry/registries` | Contains backend + frontend images |

### Open the app

Open the **frontend URL** from the deploy output in your browser. You should see the workshop application's landing page and be able to chat over the seeded sample docs.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Deployment fails with "quota exceeded" | Region doesn't have GPT-4o-mini capacity | Re-run: `.\scripts\deploy-all.ps1 -Location swedencentral` |
| `az login` hangs | Browser pop-up blocked | Use `az login --use-device-code` |
| "Subscription not found" | Wrong subscription selected | `az account set --subscription <id>` and re-run |
| Container app shows "Failed" after update | Image build failure | Re-run `.\scripts\build-and-push.ps1` then `.\scripts\update-apps.ps1` |
| "OpenAI resource not available in region" | Region doesn't support Azure OpenAI | Use `eastus2`, `swedencentral`, or `westus3` |
| Bicep deployment times out | Transient Azure-side issue | Re-run `.\scripts\deploy-infra.ps1` — it's idempotent |
| Search index empty | Backend startup hit AI Search before RBAC propagated | Restart the backend: `az containerapp revision restart --name ca-backend-<env> --resource-group rg-<env> --revision <rev>` |
| First chat returns "PermissionDenied" | Foundry data-plane RBAC (Foundry User) not yet propagated | Wait 5–10 minutes after `deploy-all.ps1` finishes and try again. |

## ✅ Checkpoint

Before moving to Lab 2, confirm:
- [ ] `.\scripts\deploy-all.ps1` completed successfully
- [ ] You can see all resources in the Azure Portal under `rg-dev`
- [ ] The frontend URL loads in your browser
- [ ] You can chat with the seeded sample documents

---

**Next:** [Lab 2 — Upload and Index Documents →](lab-02-upload-documents.md)
