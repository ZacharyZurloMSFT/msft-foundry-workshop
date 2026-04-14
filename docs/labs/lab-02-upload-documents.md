# Lab 2: Upload and Index Documents

⏱️ **Expected time: 10 minutes**

## Objective

Upload documents into the application and verify they are chunked, embedded, and indexed in Azure AI Search.

## Prerequisites

- Lab 1 completed — infrastructure is deployed and the app is running.
- A sample document ready to upload. You can use the provided [sample-document.txt](../samples/sample-document.txt) or any PDF/TXT file of your choice.

## Steps

### 1. Open the application

Navigate to your frontend URL from Lab 1:

```
https://<your-app>.azurecontainerapps.io
```

### 2. Go to the Documents page

Click **Documents** in the navigation bar. You should see an empty document list and an upload area.

### 3. Upload a sample document

1. Click the **Upload** button or drag a file into the upload area.
2. Select the sample document: [`docs/samples/sample-document.txt`](../samples/sample-document.txt) from the cloned repo (or download it from GitHub).
3. Wait for the upload to complete. The UI will show a progress indicator.

> **What happens behind the scenes:**
> 1. The file is sent to the backend API (`POST /api/documents/upload`)
> 2. Text is extracted from the file
> 3. Text is split into chunks (default: 1,000 characters with 200-character overlap)
> 4. Each chunk is embedded using Azure OpenAI's embedding model
> 5. Chunks and embeddings are indexed in Azure AI Search

### 4. Verify the document appears in the list

After upload completes, the document should appear in the document list with:
- File name
- Upload timestamp
- Processing status (should show as completed)

### 5. Verify indexing in Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com)
2. Navigate to your **AI Search** resource
3. Click **Indexes** in the left menu
4. Click on the index (named `default-index`)
5. Check the **Document count** — it should be greater than 0
6. Click **Search explorer** and run an empty search (`*`) to see the indexed chunks

You should see multiple documents in the index — each representing one chunk of your uploaded file. Each chunk contains:
- The text content
- The source document name
- An embedding vector

## Try it yourself

- Upload a second document (any PDF or text file).
- Check the index again — the document count should increase.
- Try searching for a specific term from your document in the Search explorer.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Upload button is unresponsive | Frontend can't reach backend | Check that both Container Apps are running in the Portal |
| Document shows "Processing failed" | Embedding model quota or indexing error | Check backend Container App logs in the Portal |
| Index document count is 0 | Indexing hasn't completed yet | Wait 30 seconds and refresh; check backend logs |
| "413 Request Entity Too Large" | File too large | Try a smaller file (< 10 MB) |

## ✅ Checkpoint

Before moving to Lab 3, confirm:
- [ ] At least one document is uploaded and shows as completed
- [ ] Azure AI Search index shows chunks (document count > 0)
- [ ] You can see chunk content in the Search explorer

---

**Next:** [Lab 3 — Chat with Your Data →](lab-03-chat-with-data.md)
