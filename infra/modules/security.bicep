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

@description('Resource ID of the AI Search service. Used to grant managed identity search RBAC roles.')
param aiSearchId string

@description('Principal ID of the AI Search system-assigned identity — needs Cognitive Services OpenAI User on the Foundry account so the integrated vectorizer can call the embedding deployment.')
param aiSearchPrincipalId string = ''

@description('Principal ID of the Foundry project system-assigned identity — needed to grant the Foundry Agents runtime access to AI Search when it uses a Knowledge Source.')
param foundryProjectPrincipalId string = ''

@description('Resource ID of the Container Registry. Leave empty to skip AcrPull assignment.')
param containerRegistryId string = ''

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
//   Azure AI Developer             : 64702f94-c441-49e6-a78b-ef80e0188fee  (create/manage agents + AI resources)
//   Foundry User                   : a97b65f3-24c7-4388-baec-2e87135dc908  (data-plane on Foundry projects; required for Agents runtime)
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

// ---------- Azure AI Developer + Foundry User on AI Foundry ----------
// Azure AI Developer (64702f94)     — create/manage agents + AI resources.
// Foundry User (a97b65f3)           — data-plane access to the agents runtime
//                                     (Microsoft.CognitiveServices/* dataActions,
//                                      covers AIServices/agents/* used by
//                                      POST /api/projects/{project}/threads).

resource aiDeveloper 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundryId, managedIdentity.id, '64702f94-c441-49e6-a78b-ef80e0188fee')
  scope: aiFoundryResource
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
  }
}

// Foundry User — grants `Microsoft.CognitiveServices/*` data actions on the Foundry
// account. Required for the Agents runtime (threads/create) which we hit via
// azure-ai-agents. Note: Foundry RBAC data-plane propagation can take 5+ minutes
// after the assignment is created.
resource foundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundryId, managedIdentity.id, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: aiFoundryResource
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}

resource aiFoundryResource 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: last(split(aiFoundryId, '/'))
}

// ---------- AI Search RBAC for Managed Identity ----------
// Moved here from ai-search.bicep to break the circular dependency:
// aiFoundry → aiSearch → security → aiFoundry.
// security already depends on aiFoundry and aiSearch, so adding search roles here is safe.

resource aiSearchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: last(split(aiSearchId, '/'))
}

// Search Index Data Reader
resource miSearchIndexDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearchId, managedIdentity.id, '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  scope: aiSearchService
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  }
}

// Search Index Data Contributor
resource miSearchIndexDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearchId, managedIdentity.id, '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
  scope: aiSearchService
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
  }
}

// Search Service Contributor
resource miSearchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearchId, managedIdentity.id, '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  scope: aiSearchService
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  }
}

// Cognitive Services OpenAI User for the AI Search system-assigned identity.
// Needed because the search index has an integrated Azure OpenAI vectorizer —
// AI Search calls the text-embedding-3-small deployment at query time on behalf
// of Foundry IQ.
resource searchToOpenAI 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(aiSearchPrincipalId)) {
  name: guid(aiFoundryId, aiSearchPrincipalId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  scope: aiFoundryResource
  properties: {
    principalId: aiSearchPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

// Foundry project MI → Search Index Data Reader (Foundry IQ runtime queries)
resource foundryToSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryProjectPrincipalId)) {
  name: guid(aiSearchId, foundryProjectPrincipalId, '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  scope: aiSearchService
  properties: {
    principalId: foundryProjectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  }
}

// Foundry project MI → Search Service Contributor
resource foundryToSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryProjectPrincipalId)) {
  name: guid(aiSearchId, foundryProjectPrincipalId, '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  scope: aiSearchService
  properties: {
    principalId: foundryProjectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
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
