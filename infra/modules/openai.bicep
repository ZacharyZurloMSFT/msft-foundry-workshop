// Module: openai
// Azure OpenAI account and model deployments.

@description('Name of the environment (e.g., dev, staging, prod)')
param environmentName string

@description('Azure region for the OpenAI resource')
param location string

@description('Tags to apply to all resources')
param tags object = {}

@description('Resource ID of the subnet for private endpoints')
param subnetId string

@description('Resource ID of the private DNS zone for privatelink.openai.azure.com')
param privateDnsZoneId string

@description('Principal ID of the managed identity to grant Cognitive Services OpenAI User role')
param principalId string

// --- Azure OpenAI Account ---

var openaiName = 'oai-${environmentName}'

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openaiName
  location: location
  tags: tags
  kind: 'OpenAI'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openaiName
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}

// --- Model Deployments ---

@description('GPT-5-mini deployment for chat completion')
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: 'gpt-5-mini'
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
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
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

// --- Private Endpoint ---

@description('Private endpoint for the Azure OpenAI resource')
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  dependsOn: [chatDeployment, embeddingDeployment]
  name: 'pe-${openaiName}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'pe-${openaiName}'
        properties: {
          privateLinkServiceId: openai.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

@description('Private DNS zone group for the OpenAI private endpoint')
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai-config'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

// --- RBAC: Cognitive Services OpenAI User ---

@description('Role assignment granting Cognitive Services OpenAI User to the managed identity')
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, principalId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: principalId
  }
}

// --- Outputs ---

@description('Resource ID of the Azure OpenAI account')
output openaiId string = openai.id

@description('Endpoint URL of the Azure OpenAI account')
output openaiEndpoint string = openai.properties.endpoint

@description('Name of the chat completion model deployment')
output chatDeploymentName string = chatDeployment.name

@description('Name of the embedding model deployment')
output embeddingDeploymentName string = embeddingDeployment.name
