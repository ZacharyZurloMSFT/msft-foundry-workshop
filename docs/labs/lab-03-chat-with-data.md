# Lab 3: Chat with Your Data

⏱️ **Expected time: 15 minutes**

## Objective

Ask questions and receive answers grounded in your uploaded documents. Observe how RAG (Retrieval-Augmented Generation) works in practice — including citations, streaming, and conversation memory.

## Prerequisites

- Lab 2 completed — at least one document is uploaded and indexed.

## Steps

### 1. Navigate to the Chat page

Open your application and click **Chat** in the navigation bar. You should see an empty conversation with a text input at the bottom.

### 2. Ask a factual question

If you uploaded the [sample document](../samples/sample-document.txt), try:

```
What year was Contoso Industries founded?
```

**Observe:**
- The response streams in token-by-token
- The answer cites the source document
- The answer should say **2018** (per the sample document)

### 3. Ask a follow-up question

Without starting a new conversation:

```
Who is the current CEO?
```

**Observe:**
- The agent uses conversation memory — it knows you're still asking about Contoso Industries
- The answer references **Maria Chen** and cites the document

### 4. Ask a question with multiple facts

```
What products does the company offer and what are their prices?
```

**Observe:**
- The agent retrieves multiple chunks to construct a comprehensive answer
- Multiple citations may appear
- Pricing details from the sample document should be included

### 5. Ask a question NOT in the documents

```
What is the current stock price of Contoso Industries?
```

**Observe:**
- The agent should acknowledge that this information is not in the available documents
- A well-configured RAG agent does **not** hallucinate an answer

### 6. Try an ambiguous question

```
Tell me about the company's plans
```

**Observe:**
- The agent searches for relevant chunks about future plans, roadmap, or strategy
- It synthesizes what's available and notes any gaps

## What to observe

| Feature | What to look for |
|---------|-----------------|
| **Streaming** | Responses appear word-by-word, not all at once |
| **Citations** | Source document names appear with the answer |
| **Conversation memory** | Follow-up questions work without repeating context |
| **Grounding** | Answers are based on document content, not general knowledge |
| **Honesty** | The agent admits when information isn't available |

## Discussion: How does RAG work?

```
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────┐
│  User     │───▶│  AI Search   │───▶│  LLM       │───▶│  Answer  │
│  Question │    │  (retrieve   │    │  (generate │    │  with    │
│           │    │   chunks)    │    │   answer)  │    │  sources │
└──────────┘    └──────────────┘    └────────────┘    └──────────┘
```

1. **Retrieve:** The user's question is used to search the AI Search index. The most relevant chunks are returned.
2. **Augment:** The retrieved chunks are added to the LLM prompt as context.
3. **Generate:** The LLM generates an answer grounded in the provided context.

### Why RAG instead of fine-tuning?

- **Fresh data:** Documents can be updated without retraining a model
- **Citations:** Answers can reference specific source documents
- **Cost:** No expensive fine-tuning compute required
- **Control:** You control exactly what data the model can access

### Limitations to be aware of

- **Chunk boundaries:** If an answer spans two chunks that aren't retrieved together, it may be incomplete
- **Retrieval quality:** If the search doesn't find the right chunks, the answer will be wrong or missing
- **Context window:** Very long documents produce many chunks; only the top-k are sent to the LLM
- **No reasoning across documents:** The model reasons over retrieved chunks, not the full corpus

## ✅ Checkpoint

Before moving to Lab 4, confirm:
- [ ] You received grounded answers with citations
- [ ] Follow-up questions worked (conversation memory)
- [ ] The agent admitted when information wasn't available
- [ ] You understand the Retrieve → Augment → Generate flow

---

**Next:** [Lab 4 — Customize the RAG Pipeline →](lab-04-customize-agent.md)
