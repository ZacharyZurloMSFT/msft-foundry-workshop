# Architecture — Azure AI Foundry Workshop

This document provides a detailed explanation of the workshop's architecture.

## Overview

The application follows a three-tier architecture deployed entirely on Azure, with all services connected through a Virtual Network using private endpoints for security.

```
┌─────────┐       ┌──────────────────────────────────────────────────────────────┐
│  User    │ HTTPS │                    Azure Resource Group                      │
│ (Browser)│──────►│                                                              │
└─────────┘       │   ┌─────────────────────────────────────────────────────┐    │
                  │   │        Container Apps Environment (VNet-injected)   │    │
                  │   │                                                     │    │
                  │   │   ┌──────────────┐       ┌───────────────────┐     │    │
                  │   │   │   Frontend    │ HTTP  │     Backend       │     │    │
                  │   │   │  (React +    │──────►│  (FastAPI +       │     │    │
                  │   │   │   Nginx)     │       │   Uvicorn)        │     │    │
                  │   │   └──────────────┘       └────────┬──────────┘     │    │
                  │   └───────────────────────────────────┼────────────────┘    │
                  │                                        │                     │
                  │              ┌──────────────────────────┘                     │
                  │              ▼                                                │
                  │   ┌──────────────────┐                                       │
                  │   │  AI Foundry Hub  │                                       │
                  │   │   + Project      │                                       │
                  │   └────────┬─────────┘                                       │
                  │            │ (manages connections)                            │
                  │     ┌──────┴──────┐                                          │
                  │     ▼             ▼                                           │
                  │  ┌────────────┐ ┌─────────────────┐                          │
                  │  │Azure OpenAI│ │Azure AI Search   │                          │
                  │  │GPT-4o-mini │ │(vector+semantic) │◄─── Ingestion Pipeline   │
                  │  │+ embeddings│ └─────────────────┘     (PDF/DOCX parsing)   │
                  │  └────────────┘                                              │
                  │                                                              │
                  │  ┌───────────┐ ┌───────────┐ ┌─────────────┐ ┌────────────┐ │
                  │  │ Key Vault │ │  Storage  │ │  Monitoring │ │ Managed ID │ │
                  │  └───────────┘ └───────────┘ └─────────────┘ └────────────┘ │
                  └──────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (React + Vite + Tailwind CSS)

- Single-page application served by Nginx on Azure Container Apps
- Provides chat interface with streaming message display
- Document upload with drag-and-drop support
- Conversation history sidebar
- Communicates with the backend via REST API

### Backend (FastAPI + Uvicorn)

- Python REST API handling chat, document, and conversation endpoints
- Manages the AI Foundry Agent lifecycle (creation, thread management)
- Runs the document ingestion pipeline: parses PDFs and DOCX files, chunks text, generates embeddings, and indexes into Azure AI Search
- Uses `DefaultAzureCredential` for passwordless authentication to all Azure services

### Azure AI Foundry (Hub + Project)

- Central orchestration layer for AI services
- The **Hub** provides shared infrastructure (connections, compute, storage)
- The **Project** scopes the agent, model deployments, and search connections
- The backend creates an AI Foundry Agent with Azure AI Search as a grounding tool

### Azure OpenAI

- **GPT-4o-mini** — Primary chat model used by the agent for generating responses
- **text-embedding-ada-002** — Embedding model used during document ingestion to vectorize chunks

### Azure AI Search

- Stores document chunks with vector embeddings
- Supports hybrid retrieval: vector similarity search + BM25 keyword search + semantic reranking
- The AI Foundry Agent uses it as a grounding tool to retrieve relevant document passages

### Networking

- All services are deployed inside a **Virtual Network**
- **Private endpoints** ensure traffic between services never traverses the public internet
- **Private DNS zones** provide name resolution for private endpoints
- **NSGs** restrict traffic between subnets
- Subnets:
  - `snet-aca` — Container Apps Environment
  - `snet-private-endpoints` — Private endpoints for PaaS services

### Monitoring

- **Log Analytics Workspace** — Centralized log collection
- **Application Insights** — Distributed tracing, request metrics, and performance monitoring

## Data Flow

### Chat Flow

1. User types a message in the React frontend
2. Frontend sends POST to `/chat` endpoint on the backend
3. Backend creates (or reuses) an AI Foundry Agent with Azure AI Search configured as a tool
4. Backend creates a thread and sends the user's message
5. The Agent:
   - Queries Azure AI Search to find relevant document chunks
   - Sends the retrieved context + user question to GPT-4o-mini
   - Returns a grounded response with citations
6. Backend streams the response back to the frontend

### Document Ingestion Flow

1. User uploads a PDF or DOCX file via the frontend
2. Backend receives the file at `/documents` endpoint
3. Ingestion pipeline:
   - Parses the document (PyPDF / python-docx)
   - Splits text into overlapping chunks
   - Generates vector embeddings via Azure OpenAI
   - Uploads chunks + vectors to Azure AI Search index
4. Documents are now searchable by the AI agent
