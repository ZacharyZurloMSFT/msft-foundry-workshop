# Lab 4: Customize the RAG Pipeline

⏱️ **Expected time: 20 minutes**

## Objective

Modify the RAG agent's behavior by changing system instructions, the model, chunking parameters, and adding a custom greeting. Each exercise shows you **what to change**, **where in the code**, and the **expected result**.

## Prerequisites

- Labs 1–3 completed.
- A code editor (VS Code recommended).
- The repository cloned locally.

---

## Exercise 1: Change the System Instructions

**Goal:** Make the agent respond in a specific tone — for example, like a friendly pirate. 🏴‍☠️

### What to change

Open `src/backend/app/agent.py` and find the `AGENT_INSTRUCTIONS` constant (around line 24):

```python
AGENT_INSTRUCTIONS = (
    "You are a helpful assistant that answers questions based on the "
    "provided documents. Always cite your sources. If you don't know "
    "the answer, say so."
)
```

### Change it to

```python
AGENT_INSTRUCTIONS = (
    "You are a friendly pirate assistant that answers questions based on the "
    "provided documents. Speak like a pirate — use 'Ahoy', 'matey', 'Arrr' "
    "and nautical language. Always cite your sources. If you don't know "
    "the answer, say 'Shiver me timbers, I can't find that in me scrolls!'"
)
```

### Deploy the change

```powershell
.\scripts\build-and-push.ps1
.\scripts\update-apps.ps1
```

### Expected result

Ask a question in the chat. The agent should now respond in pirate-speak while still citing documents accurately.

### Reset

Change the instructions back to the original when done, or customize them to a tone that fits your use case (formal, concise, multilingual, etc.).

---

## Exercise 2: Change the Model

**Goal:** Upgrade from `gpt-4o-mini` to `gpt-4o` for higher-quality responses.

### What to change

Open `src/backend/app/config.py` and find the `agent_model` setting (around line 13):

```python
agent_model: str = "gpt-4o-mini"
```

### Change it to

```python
agent_model: str = "gpt-4o"
```

### Deploy the change

```powershell
.\scripts\build-and-push.ps1
.\scripts\update-apps.ps1
```

### Expected result

- Responses may be more detailed and nuanced
- Response latency may increase slightly (larger model)
- Token costs will be higher

> **Note:** Make sure your Azure OpenAI resource has a `gpt-4o` deployment. If not, create one in the Azure AI Foundry portal before changing this setting.

### When to use which model

| Model | Best for | Trade-off |
|-------|----------|-----------|
| `gpt-4o-mini` | Fast responses, lower cost, simple Q&A | Less nuanced reasoning |
| `gpt-4o` | Complex reasoning, detailed answers | Slower, more expensive |

---

## Exercise 3: Adjust Chunking Parameters

**Goal:** Change how documents are split into chunks to affect retrieval quality.

### What to change

Open `src/backend/app/ingestion.py` and find the defaults (around lines 17–18):

```python
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
```

### Try these variations

#### Smaller chunks (more precise retrieval)

```python
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100
```

#### Larger chunks (more context per chunk)

```python
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 400
```

### Re-index after changing

After changing chunk parameters, you need to re-upload your documents for the new settings to take effect. The existing chunks in the index were created with the old parameters.

1. Deploy: `.\scripts\build-and-push.ps1; .\scripts\update-apps.ps1`
2. Re-upload your sample document through the app

### Expected result

| Setting | Effect |
|---------|--------|
| Smaller chunks | More precise retrieval but may miss broader context |
| Larger chunks | More context per result but may include irrelevant text |
| More overlap | Better continuity across chunk boundaries |
| Less overlap | Fewer duplicate chunks, smaller index |

### Reset

Set values back to the defaults (1000 / 200) when done experimenting.

---

## Exercise 4: Add a Custom Greeting Message

**Goal:** Show a welcome message when users start a new conversation.

### What to change

Open `src/frontend/src/pages/ChatPage.tsx` and find the chat area. Add a greeting that displays when there are no messages yet.

Look for the messages rendering section and add a conditional:

```tsx
{messages.length === 0 && (
  <div className="text-center text-gray-500 mt-10">
    <h2 className="text-2xl font-semibold mb-2">👋 Welcome to the RAG Workshop!</h2>
    <p>Upload documents in the Documents tab, then ask me anything about them.</p>
    <p className="mt-2 text-sm">Try: "What products does the company offer?"</p>
  </div>
)}
```

### Deploy the change

```powershell
.\scripts\build-and-push.ps1
.\scripts\update-apps.ps1
```

### Expected result

When starting a new conversation, users see a friendly greeting with suggested questions instead of an empty chat window.

---

## ✅ Checkpoint

Before moving to Lab 5, confirm:
- [ ] You successfully changed agent instructions and saw different tone in responses
- [ ] You understand the trade-offs between gpt-4o-mini and gpt-4o
- [ ] You understand how chunk size and overlap affect retrieval
- [ ] You added (or know how to add) a custom greeting

---

**Next:** [Lab 5 — Security & Networking →](lab-05-security-deep-dive.md)
