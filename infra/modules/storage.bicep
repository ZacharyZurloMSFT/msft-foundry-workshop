// ──────────────────────────────────────────────────────────────────────────────
// Module: storage.bicep
// Azure Storage Account with private endpoint and RBAC for managed identity.
// ──────────────────────────────────────────────────────────────────────────────

@description('Name of the environment (used for resource naming).')
param environmentName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Tags to apply to all resources.')
param tags object = {}

@description('Resource ID of the subnet for private endpoints.')
param subnetId string

@description('Resource ID of the private DNS zone for blob storage.')
param privateDnsZoneId string

@description('Principal ID for RBAC role assignment (e.g., managed identity).')
param principalId string

// ──────────────────────────────────────────────────────────────────────────────
// Variables
// ──────────────────────────────────────────────────────────────────────────────

// Storage account names must be 3-24 chars, lowercase alphanumeric only
var storageAccountName = 'st${take(replace(environmentName, '-', ''), 6)}${take(uniqueString(resourceGroup().id), 8)}'
var privateEndpointName = 'pep-st-${environmentName}'

// Built-in role: Storage Blob Data Contributor
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// ──────────────────────────────────────────────────────────────────────────────
// Storage Account
// ──────────────────────────────────────────────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Blob service + documents container
// ──────────────────────────────────────────────────────────────────────────────

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'documents'
  properties: {
    publicAccess: 'None'
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Private Endpoint + DNS Zone Group
// ──────────────────────────────────────────────────────────────────────────────

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
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
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

resource dnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-blob'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// RBAC: Storage Blob Data Contributor for managed identity
// ──────────────────────────────────────────────────────────────────────────────

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, principalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────────────────────────────────────

@description('Resource ID of the Storage Account.')
output storageAccountId string = storageAccount.id

@description('Name of the Storage Account.')
output storageAccountName string = storageAccount.name

@description('Primary blob endpoint.')
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
