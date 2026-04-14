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

@description('Resource ID of the subnet for the private endpoint')
param subnetId string

@description('Resource ID of the private DNS zone for privatelink.search.windows.net')
param privateDnsZoneId string

@description('Principal ID of the managed identity to grant RBAC roles')
param principalId string

var searchServiceName = 'search-${environmentName}'

// Azure AI Search resource
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
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
    publicNetworkAccess: 'disabled'
    disableLocalAuth: true
    semanticSearch: skuName == 'free' ? 'disabled' : 'free'
    partitionCount: 1
    replicaCount: 1
  }
}

// Private endpoint for the search service
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: 'pe-${searchServiceName}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pe-${searchServiceName}'
        properties: {
          privateLinkServiceId: searchService.id
          groupIds: [
            'searchService'
          ]
        }
      }
    ]
  }
}

// Private DNS zone group
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-search-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

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
