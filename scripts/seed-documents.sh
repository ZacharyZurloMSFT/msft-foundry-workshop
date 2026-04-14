#!/bin/bash
# Seed sample documents into the RAG application
# Usage: ./scripts/seed-documents.sh [BACKEND_URL]

BACKEND_URL="${1:-http://localhost:8000}"

echo "🌱 Seeding sample documents to $BACKEND_URL"
echo ""

for doc in docs/samples/*.txt; do
  filename=$(basename "$doc")
  echo -n "📄 Uploading $filename... "
  response=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND_URL/api/documents/upload" \
    -F "file=@$doc" 2>&1)
  code=$(echo "$response" | tail -1)
  body=$(echo "$response" | head -1)
  
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    echo "✅ ($code)"
  else
    echo "❌ ($code) $body"
  fi
done

echo ""
echo "🌱 Seeding complete! Check /api/documents for indexed files."
