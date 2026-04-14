using '../main.bicep'

// ──────────────────────────────────────
// Production Environment Parameters
// ──────────────────────────────────────

param environmentName = 'prod'
param location = 'centralus'

param tags = {
  environment: 'prod'
  project: 'ai-foundry-workshop'
}

// Principal ID for role assignments — replace with your user/SP object ID at deploy time
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
