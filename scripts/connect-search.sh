#!/bin/bash
# Connect AI Search to the Foundry resource via Azure REST API
# Usage: ./scripts/connect-search.sh <resource-group> <env-name>

set -e

RG="${1:-rg-workshop-dev-v7}"
ENV_NAME="${2:-workshop-dev-v7}"

FOUNDRY_NAME="foundry-${ENV_NAME}"
SEARCH_NAME="search-${ENV_NAME}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

echo "🔗 Connecting AI Search to Foundry project..."
echo "  Foundry: $FOUNDRY_NAME"
echo "  Search:  $SEARCH_NAME"

# Get Search resource ID
SEARCH_ID=$(az search service show --name "$SEARCH_NAME" --resource-group "$RG" --query id -o tsv)
echo "  Search ID: $SEARCH_ID"

# Create connection on the Foundry resource
az rest --method PUT \
  --uri "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_NAME}/connections/ai-search-connection?api-version=2025-04-01-preview" \
  --body "{
    \"properties\": {
      \"category\": \"CognitiveSearch\",
      \"target\": \"https://${SEARCH_NAME}.search.windows.net\",
      \"authType\": \"AAD\",
      \"metadata\": {
        \"ResourceId\": \"${SEARCH_ID}\",
        \"ApiType\": \"Azure\"
      }
    }
  }"

echo "✅ AI Search connected to Foundry"

# Also connect OpenAI
OAI_NAME="oai-${ENV_NAME}"
OAI_ID=$(az cognitiveservices account show --name "$OAI_NAME" --resource-group "$RG" --query id -o tsv)
OAI_ENDPOINT=$(az cognitiveservices account show --name "$OAI_NAME" --resource-group "$RG" --query "properties.endpoint" -o tsv)

echo ""
echo "🔗 Connecting OpenAI to Foundry..."
echo "  OpenAI: $OAI_NAME"

az rest --method PUT \
  --uri "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_NAME}/connections/openai-connection?api-version=2025-04-01-preview" \
  --body "{
    \"properties\": {
      \"category\": \"AzureOpenAI\",
      \"target\": \"${OAI_ENDPOINT}\",
      \"authType\": \"AAD\",
      \"metadata\": {
        \"ResourceId\": \"${OAI_ID}\",
        \"ApiType\": \"Azure\"
      }
    }
  }"

echo "✅ OpenAI connected to Foundry"
echo ""
echo "🎉 All connections created!"
