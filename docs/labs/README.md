# Workshop Lab Guide

Welcome to the Azure AI Foundry Workshop labs! These hands-on exercises walk you through deploying, using, customizing, and securing an enterprise RAG (Retrieval-Augmented Generation) application.

## Labs Overview

| # | Lab | Description | Time |
|---|-----|-------------|------|
| 1 | [Deploy Infrastructure](lab-01-deploy-infrastructure.md) | Provision all Azure resources using `azd` | 15–20 min |
| 2 | [Upload and Index Documents](lab-02-upload-documents.md) | Upload documents and verify AI Search indexing | 10 min |
| 3 | [Chat with Your Data](lab-03-chat-with-data.md) | Ask questions grounded in your documents | 15 min |
| 4 | [Customize the RAG Pipeline](lab-04-customize-agent.md) | Modify agent behavior, model, and chunking | 20 min |
| 5 | [Security & Networking](lab-05-security-deep-dive.md) | Explore private endpoints, RBAC, and zero-trust | 15 min |

**Total estimated time: ~75 minutes**

## Recommended Order

Complete the labs in sequence — each builds on the previous:

1. **Lab 1** is required before all other labs (it deploys the infrastructure).
2. **Lab 2** must be completed before Lab 3 (you need documents to chat with).
3. **Labs 4 and 5** can be done in either order after Lab 3.

## Prerequisites

- An Azure subscription with **Owner** or **Contributor + User Access Administrator** role
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az`) installed
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) (`azd`) installed
- [Git](https://git-scm.com/) installed
- A modern web browser (Edge, Chrome, Firefox)
- A terminal (bash, PowerShell, or zsh)

## Getting Help

If you run into issues during any lab, check the **Troubleshooting** section at the bottom of each lab page. For issues not covered there, ask your workshop facilitator.
