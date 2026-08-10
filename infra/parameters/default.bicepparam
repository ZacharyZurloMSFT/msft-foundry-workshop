using '../main.bicep'

// ──────────────────────────────────────
// Default parameter template
//
// This file is used automatically by scripts\deploy-infra.ps1 when no
// <EnvironmentName>.bicepparam file exists for the environment name you
// passed. The script overrides `environmentName`, `location`, and
// `principalId` on the command line, so you can deploy a fresh, uniquely
// named environment without editing or copying this file:
//
//   .\scripts\deploy-all.ps1 -EnvironmentName myrag -Location centralus
//
// If you want custom tags or non-default settings for a specific env,
// copy this file to `<EnvironmentName>.bicepparam` and edit it.
// ──────────────────────────────────────

param environmentName = 'default'
param location = 'centralus'

param tags = {
  project: 'ai-foundry-workshop'
}

// Auto-filled by scripts\deploy-infra.ps1 from `az ad signed-in-user show`.
param principalId = '<REPLACE_WITH_YOUR_PRINCIPAL_ID>'
