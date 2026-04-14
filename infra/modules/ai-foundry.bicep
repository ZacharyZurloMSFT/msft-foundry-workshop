// Microsoft Foundry resource + Project (NOT legacy AI Hub/Project)
// Uses Microsoft.CognitiveServices/accounts with kind: 'AIServices'

@description('Environment name used for resource naming.')
param environmentName string

@description('Azure region for all resources.')
param location string

@description('Tags to apply to all resources.')
param tags object = {}

@description('Resource ID of the subnet for private endpoints.')
param subnetId string

@description('Resource ID of the private DNS zone for the Foundry private endpoint.')
param privateDnsZoneId string








@description('Resource ID of a user-assigned managed identity.')
param managedIdentityId string = ''

// ---------- Naming ----------
var foundryName = 'foundry-${environmentName}'
var projectName = 'project-${environmentName}'
var privateEndpointName = 'pep-foundry-${environmentName}'

// ---------- Microsoft Foundry Resource ----------
resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: foundryName
  location: location
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
    customSubDomainName: foundryName
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}

// ---------- Foundry Project ----------
resource project 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  dependsOn: [foundry]
  name: projectName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: projectName
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}

// ---------- Private Endpoint ----------
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  dependsOn: [foundry, project]
  name: privateEndpointName
  location: location
  tags: tags
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
@description('Resource ID of the Foundry resource.')
output foundryResourceId string = foundry.id

@description('Foundry resource name.')
output foundryName string = foundry.name

@description('Endpoint URL of the Foundry resource.')
output foundryEndpoint string = foundry.properties.endpoint

@description('Resource ID of the Foundry Project.')
output projectId string = project.id

@description('Name of the Foundry Project.')
output projectName string = project.name

@description('Endpoint URL of the Foundry Project.')
output projectEndpoint string = project.properties.endpoint
