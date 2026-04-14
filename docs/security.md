# Security Posture — Azure AI Foundry Workshop

This document describes the security controls applied to the workshop deployment.

## Overview

The architecture follows Azure security best practices: network isolation via VNet + private endpoints, passwordless authentication via managed identity, and least-privilege RBAC. No secrets are stored in application code or environment variables at runtime.

## Network Security

### Virtual Network Isolation

All Azure PaaS services are connected through **private endpoints** within a Virtual Network. Public network access is disabled for:

- Azure OpenAI
- Azure AI Search
- Azure Storage
- Azure Key Vault
- Azure AI Foundry Hub
- Azure Container Registry

### Private DNS Zones

Private DNS zones are linked to the VNet to ensure name resolution for private endpoints:

- `privatelink.openai.azure.com`
- `privatelink.search.windows.net`
- `privatelink.blob.core.windows.net`
- `privatelink.vaultcore.azure.net`
- `privatelink.cognitiveservices.azure.com`
- `privatelink.azurecr.io`

### Network Security Groups (NSGs)

Subnets are protected by NSGs that restrict inbound and outbound traffic:

- **Container Apps subnet** — Allows only necessary egress to private endpoints
- **Private endpoints subnet** — Restricts traffic to VNet-internal sources

### Container Apps

- The Container Apps Environment is **VNet-injected** into a dedicated subnet
- The frontend is the only service with an external ingress (HTTPS)
- Backend-to-backend communication stays within the VNet

## Identity & Access Management

### Managed Identity

A **user-assigned managed identity** is used by the Container Apps to authenticate to Azure services. No connection strings, API keys, or passwords are stored in the application.

The backend uses `DefaultAzureCredential`, which automatically picks up:
- The managed identity in Azure (production)
- Your Azure CLI credentials locally (development)

### RBAC Role Assignments

The `security.bicep` module assigns least-privilege roles to the managed identity:

| Role | Scope | Purpose |
|---|---|---|
| **Cognitive Services OpenAI User** | Azure OpenAI | Invoke chat and embedding models |
| **Search Index Data Contributor** | Azure AI Search | Read/write search index data |
| **Storage Blob Data Contributor** | Storage Account | Upload and read documents |
| **Key Vault Secrets User** | Key Vault | Read secrets (if needed) |
| **Azure AI Developer** | AI Foundry Hub | Create and manage agents |

The deploying user's principal ID also receives these roles for local development and `azd` operations.

## Secrets Management

### Azure Key Vault

- Used for storing any secrets that services may need
- Access is controlled via RBAC (no access policies)
- Private endpoint ensures Key Vault is not exposed to the internet
- Soft-delete and purge protection are enabled

### No Hardcoded Secrets

- The backend connects to Azure services using managed identity — no API keys
- The AI Foundry project connection string is injected as an environment variable by the Container Apps module (sourced from Bicep outputs, not stored in code)

## Data Protection

### Data at Rest

- Azure Storage uses Microsoft-managed encryption keys (SSE) by default
- Azure AI Search encrypts index data at rest
- Key Vault uses HSM-backed encryption for secrets

### Data in Transit

- All communication between services uses TLS 1.2+
- Private endpoints ensure traffic stays on the Microsoft backbone network
- The frontend is served over HTTPS via Container Apps' built-in TLS termination

## Compliance Considerations

- All resources are deployed within a single Azure region (configurable)
- No data leaves the VNet except through the frontend's public HTTPS endpoint
- Logging and monitoring via Log Analytics provides an audit trail
- The architecture supports Azure Policy and Microsoft Defender for Cloud integration

## Recommendations for Production

The workshop deployment provides a strong security baseline. For production, consider:

1. **Enable Microsoft Defender for Cloud** on the subscription
2. **Add WAF** (Web Application Firewall) via Azure Front Door or Application Gateway in front of the Container Apps
3. **Enable diagnostic settings** on all resources to stream logs to Log Analytics
4. **Implement network policies** for Container Apps for micro-segmentation
5. **Use customer-managed keys (CMK)** for encryption at rest if required by compliance
6. **Enable Azure Private Link** for the Container Apps ingress (remove public endpoint)
7. **Add IP restrictions** or Azure AD authentication to the frontend
