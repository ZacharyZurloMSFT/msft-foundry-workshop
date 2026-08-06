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
// The scripts\deploy-infra.ps1 script auto-fills this from `az ad signed-in-user show`,
// overriding the value below. If you deploy `az deployment group create` by hand,
// pass --parameters principalId=<your object id>. Get your object ID with:
//   az ad signed-in-user show --query id -o tsv
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
