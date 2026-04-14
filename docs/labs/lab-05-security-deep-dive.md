# Lab 5: Security & Networking Deep Dive

⏱️ **Expected time: 15 minutes**

## Objective

Explore the security architecture of the deployed workshop environment. Examine private endpoints, RBAC role assignments, network isolation, and managed identity usage to understand how enterprise-grade security is implemented.

## Prerequisites

- Lab 1 completed — infrastructure is deployed.
- Access to the Azure Portal.

---

## Exercise 1: Examine Private Endpoints

### Steps

1. Go to [portal.azure.com](https://portal.azure.com)
2. Navigate to your **Resource group**
3. Filter by type: **Private endpoint**
4. Click on each private endpoint and examine:
   - **Target resource:** Which service does it connect to?
   - **Network interface:** What private IP was assigned?
   - **DNS configuration:** What FQDN resolves to the private IP?

### What to look for

The deployment creates private endpoints for:

| Service | Why |
|---------|-----|
| Azure AI Search | So the backend accesses search over the private network, not the internet |
| Azure OpenAI / AI Foundry | Model calls stay within the VNet |
| Storage Account | Document uploads and blob access are private |
| Key Vault | Secret retrieval happens over private networking |

### Verify

Click on the **Virtual Network** resource → **Subnets** to see how subnets are organized. Private endpoints sit in a dedicated subnet.

---

## Exercise 2: Review RBAC Role Assignments

### Steps

1. Navigate to your **Resource group**
2. Click **Access control (IAM)** in the left menu
3. Click **Role assignments** tab
4. Look for assignments with **Managed Identity** as the principal type

### What to look for

| Principal | Role | Resource | Purpose |
|-----------|------|----------|---------|
| Backend Container App identity | **Search Index Data Contributor** | AI Search | Read/write search index data |
| Backend Container App identity | **Cognitive Services OpenAI User** | AI Foundry | Call OpenAI models |
| Backend Container App identity | **Storage Blob Data Contributor** | Storage Account | Upload/read documents |
| Backend Container App identity | **Key Vault Secrets User** | Key Vault | Read configuration secrets |

> **Key insight:** No passwords or connection strings are stored anywhere. The managed identity authenticates automatically using Azure's identity platform.

---

## Exercise 3: Check Network Isolation

### Steps

1. Navigate to your **AI Search** resource
2. Click **Networking** in the left menu
3. Check the **Public network access** setting

Repeat for:
- **Storage Account** → **Networking**
- **Key Vault** → **Networking**

### What to look for

- Public network access should be **Disabled** or restricted to specific networks
- Only the VNet (via private endpoints) should have access
- The Container Apps access these services through the VNet integration

### Verify no public endpoints

Try accessing the AI Search URL directly in your browser:

```
https://<your-search-service>.search.windows.net
```

You should get a **403 Forbidden** or connection timeout — confirming public access is blocked.

---

## Exercise 4: Review Managed Identity Usage

### Steps

1. Navigate to the **Backend Container App**
2. Click **Identity** in the left menu
3. Check the **System assigned** tab — Status should be **On**
4. Click **Azure role assignments** to see what roles this identity has

### What to look for

- The Container App has a **system-assigned managed identity**
- This identity is automatically created and managed by Azure
- No credentials are stored in code, config files, or environment variables
- The identity is used with `DefaultAzureCredential` in the Python code (see `src/backend/app/agent.py`)

### How it works in code

```python
from azure.identity import DefaultAzureCredential

# No secrets needed — the managed identity authenticates automatically
credential = DefaultAzureCredential()
client = AIProjectClient.from_connection_string(
    credential=credential,
    conn_str=settings.azure_ai_project_connection_string,
)
```

---

## Discussion: Security Concepts

### Why private endpoints?

Private endpoints ensure that traffic between services **never traverses the public internet**. Instead:

- Services communicate over Azure's backbone network
- Each service gets a private IP within your VNet
- DNS is configured so service FQDNs resolve to private IPs
- Even if credentials leaked, the services are unreachable from outside the VNet

### What is zero-trust?

Zero-trust is a security model based on the principle: **"Never trust, always verify."**

In this workshop architecture, zero-trust is implemented through:

| Principle | Implementation |
|-----------|---------------|
| **Verify explicitly** | Every request authenticated via managed identity + RBAC |
| **Least-privilege access** | Each identity has only the roles it needs |
| **Assume breach** | Network segmentation via private endpoints; no shared secrets |

### Defense in depth

This architecture uses multiple layers of security:

```
┌─────────────────────────────────────────────┐
│  Layer 1: Network (VNet + Private Endpoints) │
│  ┌─────────────────────────────────────────┐ │
│  │  Layer 2: Identity (Managed Identity)    │ │
│  │  ┌─────────────────────────────────────┐ │ │
│  │  │  Layer 3: Access (RBAC Roles)       │ │ │
│  │  │  ┌─────────────────────────────────┐│ │ │
│  │  │  │  Layer 4: Data (Encryption)     ││ │ │
│  │  │  └─────────────────────────────────┘│ │ │
│  │  └─────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## ✅ Checkpoint

Confirm you understand:
- [ ] Why private endpoints are used for each service
- [ ] How RBAC role assignments follow least-privilege
- [ ] That no service has public network access
- [ ] How managed identities eliminate the need for stored credentials
- [ ] The zero-trust and defense-in-depth principles at work

---

**🎉 Congratulations!** You've completed all 5 labs. You now have hands-on experience deploying, using, customizing, and securing an enterprise RAG application on Azure AI Foundry.

[← Back to Lab Guide](README.md)
