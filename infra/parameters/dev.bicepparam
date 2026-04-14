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

// Principal ID for role assignments — replace with your user/SP object ID at deploy time
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
