using '../main.bicep'

// ──────────────────────────────────────
// Dev / Workshop Environment Parameters
// Cost-optimized for development use
// ──────────────────────────────────────

param environmentName = 'dev'
param location = 'centralus'

param tags = {
  environment: 'dev'
  project: 'ai-foundry-workshop'
}

// AI Search: 'free' tier does not support vector search; use 'basic' for dev
// (The skuName param is set in the aiSearch module call inside main.bicep)

// Principal ID for role assignments.
// When deploying via GitHub Actions, this is overridden by the AZURE_PRINCIPAL_ID variable
// (see deploy.yml: azd env config set infra.parameters.principalId).
// For local deploys, get your object ID with:
//   az ad signed-in-user show --query id -o tsv
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
