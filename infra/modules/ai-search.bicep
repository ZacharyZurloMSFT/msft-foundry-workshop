// Module: ai-search
// Azure AI Search service for RAG and vector search scenarios.

@description('Name of the environment (e.g., dev, staging, prod)')
param environmentName string

@description('Azure region for the AI Search resource')
param location string

@description('Tags to apply to all resources')
param tags object = {}

@description('SKU name for the search service (free for dev, basic for workshop)')
@allowed([
  'free'
  'basic'
  'standard'
  'standard2'
  'standard3'
])
param skuName string = 'basic'

// subnetId and privateDnsZoneId are no longer used (private endpoint removed
// so Foundry IQ can reach Search). Kept as optional params to avoid breaking
// callers that still pass them.
@description('(Unused) Legacy: subnet for a private endpoint. Ignored.')
param subnetId string = ''

@description('(Unused) Legacy: private DNS zone for privatelink.search.windows.net. Ignored.')
param privateDnsZoneId string = ''

@description('Principal ID of the managed identity to grant RBAC roles')
param principalId string

var searchServiceName = 'search-${environmentName}'

// Azure AI Search resource
// Foundry IQ (Knowledge Sources) reaches this service from the Microsoft-managed
// Foundry runtime, which cannot cross into our VNet. So publicNetworkAccess must
// be Enabled; AAD-only auth (disableLocalAuth) keeps it locked to identity-based
// access. If you need true private-only search, remove the AzureAISearchTool
// from agent.py and switch to a backend-mediated search flow.
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: true
    partitionCount: 1
    replicaCount: 1
  }
}

// Private endpoint intentionally removed — Foundry IQ requires public
// network access on the AI Search service. AAD-only auth still protects it.

// RBAC Role Assignments

// Search Index Data Reader — for querying indexes
resource searchIndexDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, principalId, '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  scope: searchService
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f')
  }
}

// Search Index Data Contributor — for indexing data
resource searchIndexDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, principalId, '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
  scope: searchService
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
  }
}

// Search Service Contributor — for managing indexes and service configuration
resource searchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, principalId, '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  scope: searchService
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
  }
}

// Outputs

@description('Resource ID of the search service')
output searchServiceId string = searchService.id

@description('Name of the search service')
output searchServiceName string = searchService.name

@description('Endpoint URL of the search service')
output searchEndpointUrl string = 'https://${searchService.name}.search.windows.net'

@description('Principal ID of the Search service system-assigned identity — needs Cognitive Services OpenAI User on the Foundry account so the integrated vectorizer can call the embedding deployment.')
output searchIdentityPrincipalId string = searchService.identity.principalId
