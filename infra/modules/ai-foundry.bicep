// Microsoft Foundry account + Project (child resource) + Connections
// Based on: https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Azure region for Foundry account and project (may differ from other resources for service availability).')
param foundryLocation string = location

@description('Tags to apply to all resources.')
param tags object = {}

@description('Resource ID of the subnet for private endpoints.')
param subnetId string

@description('Resource ID of the private DNS zone for the Foundry private endpoint.')
param privateDnsZoneId string

@description('Resource ID of a user-assigned managed identity.')
param managedIdentityId string = ''

// ---------- Connection parameters ----------

@description('Resource ID of the Azure AI Search service to connect.')
param searchServiceId string

@description('Name of the Azure AI Search service.')
param searchServiceName string

@description('Resource ID of the Application Insights instance to connect.')
param appInsightsId string

@description('Application Insights connection string.')
param appInsightsConnectionString string

// ---------- Naming ----------
var foundryName = 'foundry-${environmentName}'
var projectName = 'project-${environmentName}'
var privateEndpointName = 'pep-foundry-${environmentName}'

// ---------- Microsoft Foundry Account ----------
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: foundryName
  location: foundryLocation
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: empty(managedIdentityId) ? {
    type: 'SystemAssigned'
  } : {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// ---------- Foundry Project (child resource) ----------
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: projectName
  parent: foundry
  location: foundryLocation
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// ---------- Model Deployments (on Foundry account) ----------

@description('GPT-5-mini deployment for chat completion')
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: foundry
  name: 'gpt-5-mini'
  dependsOn: [project]
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5-mini'
      version: '2025-08-07'
    }
  }
}

@description('text-embedding-3-small deployment for embeddings')
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = {
  parent: foundry
  name: 'text-embedding-3-small'
  dependsOn: [chatDeployment]
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
}

// ---------- Connection: Azure AI Search ----------
resource searchConnection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: 'ai-search-connection'
  parent: foundry
  dependsOn: [embeddingDeployment]
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net'
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceId
    }
  }
}

// ---------- Connection: Application Insights ----------
resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: 'app-insights-connection'
  parent: foundry
  dependsOn: [searchConnection]
  properties: {
    category: 'AppInsights'
    target: appInsightsId
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: appInsightsConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsightsId
    }
  }
}

// ---------- Private Endpoint ----------
// Must wait for all child resources to complete so the account leaves 'Accepted' state
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  dependsOn: [appInsightsConnection]
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointName
        properties: {
          privateLinkServiceId: foundry.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'foundry-dns'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

// ---------- Outputs ----------
@description('Resource ID of the Foundry account.')
output foundryResourceId string = foundry.id

@description('Foundry account name.')
output foundryName string = foundry.name

@description('Endpoint URL of the Foundry account (CognitiveServices endpoint for OpenAI inference).')
output foundryEndpoint string = foundry.properties.endpoint

@description('Project-scoped endpoint for the AI Projects SDK (https://{name}.services.ai.azure.com/api/projects/{project}).')
output projectEndpoint string = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'

@description('Resource ID of the Foundry Project.')
output projectId string = project.id

@description('Name of the Foundry Project.')
output projectName string = project.name

@description('Name of the AI Search connection in Foundry.')
output searchConnectionName string = searchConnection.name

@description('Name of the chat completion model deployment.')
output chatDeploymentName string = chatDeployment.name

@description('Name of the embedding model deployment.')
output embeddingDeploymentName string = embeddingDeployment.name
