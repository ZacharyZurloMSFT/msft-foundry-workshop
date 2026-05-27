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
// When deploying via GitHub Actions, this is overridden by the AZURE_PRINCIPAL_ID variable
// (see deploy.yml: azd env config set infra.parameters.principalId).
// For local deploys, get your object ID with:
//   az ad signed-in-user show --query id -o tsv
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
