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

// Principal ID for role assignments.
// The scripts\deploy-infra.ps1 script auto-fills this from `az ad signed-in-user show`,
// overriding the value below. If you deploy `az deployment group create` by hand,
// pass --parameters principalId=<your object id>. Get your object ID with:
//   az ad signed-in-user show --query id -o tsv
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
