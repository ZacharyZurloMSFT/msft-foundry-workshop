// Module: security
// User-assigned managed identity and RBAC role assignments not covered by individual modules.
//
// Roles already assigned elsewhere:
//   - Cognitive Services OpenAI User → openai.bicep
//   - Search Index Data Reader → ai-search.bicep
//   - Search Index Data Contributor → ai-search.bicep
//   - Search Service Contributor → ai-search.bicep

@description('Environment name (e.g., dev, staging, prod).')
param environmentName string

@description('Primary Azure region.')
param location string

@description('Tags applied to every resource.')
param tags object

// ---------- Resource IDs for scoped role assignments ----------

@description('Resource ID of the Storage Account.')
param storageAccountId string

@description('Resource ID of the Key Vault.')
param keyVaultId string

@description('Resource ID of the AI Foundry Hub.')
param aiFoundryId string

@description('Resource ID of the Container Registry. Leave empty to skip AcrPull assignment.')
param containerRegistryId string = ''

@description('Object ID of the deploying principal (e.g. GitHub Actions service principal). Leave empty to skip.')
param deployingPrincipalId string = ''

// ---------- Managed Identity ----------

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${environmentName}'
  location: location
  tags: tags
}

// ---------- Role Definitions ----------
// Built-in role GUIDs:
//   Storage Blob Data Contributor  : ba92f5b4-2d11-453d-a403-e96b0029c9fe
//   Key Vault Secrets User         : 4633458b-17de-408a-b874-0445c86b69e6
//   Azure AI User                  : 53ca6127-db72-4b80-b1b0-d745d6d5456d
//   AcrPull                        : 7f951dda-4ed3-4680-a7ca-43fe172d538d

// ---------- Storage Blob Data Contributor ----------

resource storageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountId, managedIdentity.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
      principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: last(split(storageAccountId, '/'))
}

// ---------- Key Vault Secrets User ----------

resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultId, managedIdentity.id, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: keyVaultResource
  properties: {
    principalId: managedIdentity.properties.principalId
      principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
  }
}

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: last(split(keyVaultId, '/'))
}

// ---------- Azure AI User on AI Foundry ----------

resource aiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundryId, managedIdentity.id, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: aiFoundryResource
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

resource aiFoundryResource 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: last(split(aiFoundryId, '/'))
}

// ---------- Azure AI User for deploying principal (CI/CD) ----------

resource aiUserDeployer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployingPrincipalId)) {
  name: guid(aiFoundryId, deployingPrincipalId, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: aiFoundryResource
  properties: {
    principalId: deployingPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

// ---------- AcrPull on Container Registry (conditional) ----------

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(containerRegistryId)) {
  name: guid(containerRegistryId, managedIdentity.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  scope: containerRegistry
  properties: {
    principalId: managedIdentity.properties.principalId
      principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = if (!empty(containerRegistryId)) {
  name: last(split(containerRegistryId, '/'))
}

// ---------- Outputs ----------

@description('Resource ID of the user-assigned managed identity.')
output managedIdentityId string = managedIdentity.id

@description('Principal ID of the user-assigned managed identity.')
output managedIdentityPrincipalId string = managedIdentity.properties.principalId

@description('Client ID of the user-assigned managed identity.')
output managedIdentityClientId string = managedIdentity.properties.clientId
