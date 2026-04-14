// ──────────────────────────────────────────────────────────────────────────────
// Module: keyvault.bicep
// Azure Key Vault with RBAC, private endpoint, soft-delete, and purge protection.
// ──────────────────────────────────────────────────────────────────────────────

@description('Name of the environment (used for resource naming).')
param environmentName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Tags to apply to all resources.')
param tags object = {}

@description('Resource ID of the subnet for private endpoints.')
param subnetId string

@description('Resource ID of the private DNS zone for Key Vault.')
param privateDnsZoneId string

@description('Principal ID for RBAC role assignment (e.g., managed identity).')
param principalId string

// ──────────────────────────────────────────────────────────────────────────────
// Variables
// ──────────────────────────────────────────────────────────────────────────────

var keyVaultName = 'kv-${take(environmentName, 6)}-${take(uniqueString(resourceGroup().id), 8)}'
var privateEndpointName = 'pep-kv-${environmentName}'

// Built-in role: Key Vault Secrets User
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

// ──────────────────────────────────────────────────────────────────────────────
// Key Vault
// ──────────────────────────────────────────────────────────────────────────────

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
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
          privateLinkServiceId: keyVault.id
          groupIds: [
            'vault'
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
        name: 'privatelink-vaultcore'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// RBAC: Key Vault Secrets User for managed identity
// ──────────────────────────────────────────────────────────────────────────────

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────────────────────────────────────

@description('Resource ID of the Key Vault.')
output keyVaultId string = keyVault.id

@description('Name of the Key Vault.')
output keyVaultName string = keyVault.name

@description('URI of the Key Vault.')
output keyVaultUri string = keyVault.properties.vaultUri
