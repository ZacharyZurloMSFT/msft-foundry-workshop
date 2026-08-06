using '../main.bicep'

// ──────────────────────────────────────
// Workshop / expert-guide session environment
// Short unique name to avoid collisions with existing dev deploys
// ──────────────────────────────────────

param environmentName = 'zzrag01'
param location = 'centralus'

param tags = {
  environment: 'zzrag01'
  project: 'ai-foundry-workshop'
  owner: 'zacharyzurlo'
}

param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
