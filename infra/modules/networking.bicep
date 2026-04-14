// ──────────────────────────────────────────────────────────────────────────────
// Module: networking.bicep
// Creates VNet, subnets with NSGs, and private DNS zones for Azure AI Foundry
// ──────────────────────────────────────────────────────────────────────────────

@description('Name of the environment (used for resource naming).')
param environmentName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Tags to apply to all resources.')
param tags object = {}

// ──────────────────────────────────────────────────────────────────────────────
// Variables
// ──────────────────────────────────────────────────────────────────────────────

var vnetName = 'vnet-${environmentName}'
var nsgAcaName = 'nsg-snet-aca-${environmentName}'
var nsgPeName = 'nsg-snet-pe-${environmentName}'
var nsgAiName = 'nsg-snet-ai-${environmentName}'

var vnetAddressPrefix = '10.0.0.0/16'

var subnets = {
  aca: {
    name: 'snet-aca'
    addressPrefix: '10.0.0.0/23'
  }
  privateEndpoints: {
    name: 'snet-private-endpoints'
    addressPrefix: '10.0.2.0/24'
  }
  ai: {
    name: 'snet-ai'
    addressPrefix: '10.0.3.0/24'
  }
}

var privateDnsZoneNames = [
  'privatelink.openai.azure.com'
  'privatelink.search.windows.net'
  'privatelink.vaultcore.azure.net'
  'privatelink.blob.core.windows.net'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.azurecr.io'
]

// ──────────────────────────────────────────────────────────────────────────────
// NSGs
// ──────────────────────────────────────────────────────────────────────────────

@description('NSG for the ACA subnet — allow outbound HTTPS, deny inbound except from VNet.')
resource nsgAca 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: nsgAcaName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowVNetInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
      {
        name: 'AllowHttpsOutbound'
        properties: {
          priority: 100
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
    ]
  }
}

@description('NSG for the private endpoints subnet — allow inbound from VNet only.')
resource nsgPe 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: nsgPeName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowVNetInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

@description('NSG for the AI subnet — allow inbound from VNet only.')
resource nsgAi 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: nsgAiName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowVNetInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Virtual Network
// ──────────────────────────────────────────────────────────────────────────────

@description('Virtual network for the AI Foundry workshop environment.')
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: subnets.aca.name
        properties: {
          addressPrefix: subnets.aca.addressPrefix
          networkSecurityGroup: {
            id: nsgAca.id
          }
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: subnets.privateEndpoints.name
        properties: {
          addressPrefix: subnets.privateEndpoints.addressPrefix
          networkSecurityGroup: {
            id: nsgPe.id
          }
        }
      }
      {
        name: subnets.ai.name
        properties: {
          addressPrefix: subnets.ai.addressPrefix
          networkSecurityGroup: {
            id: nsgAi.id
          }
        }
      }
    ]
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Private DNS Zones + VNet Links
// ──────────────────────────────────────────────────────────────────────────────

@description('Private DNS zones for Azure services accessed via private endpoints.')
resource privateDnsZones 'Microsoft.Network/privateDnsZones@2024-06-01' = [
  for zoneName in privateDnsZoneNames: {
    name: zoneName
    location: 'global'
    tags: tags
  }
]

@description('Link each private DNS zone to the VNet for automatic registration.')
resource privateDnsZoneLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [
  for (zoneName, i) in privateDnsZoneNames: {
    parent: privateDnsZones[i]
    name: '${vnetName}-link'
    location: 'global'
    tags: tags
    properties: {
      virtualNetwork: {
        id: vnet.id
      }
      registrationEnabled: false
    }
  }
]

// ──────────────────────────────────────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────────────────────────────────────

@description('Resource ID of the virtual network.')
output vnetId string = vnet.id

@description('Name of the virtual network.')
output vnetName string = vnet.name

@description('Resource ID of the ACA subnet.')
output subnetAcaId string = vnet.properties.subnets[0].id

@description('Resource ID of the private endpoints subnet.')
output subnetPrivateEndpointsId string = vnet.properties.subnets[1].id

@description('Resource ID of the AI subnet.')
output subnetAiId string = vnet.properties.subnets[2].id

@description('Resource ID of the Azure OpenAI private DNS zone.')
output dnsZoneOpenAiId string = privateDnsZones[0].id

@description('Resource ID of the AI Search private DNS zone.')
output dnsZoneSearchId string = privateDnsZones[1].id

@description('Resource ID of the Key Vault private DNS zone.')
output dnsZoneKeyVaultId string = privateDnsZones[2].id

@description('Resource ID of the Blob Storage private DNS zone.')
output dnsZoneBlobId string = privateDnsZones[3].id

@description('Resource ID of the Cognitive Services private DNS zone.')
output dnsZoneCognitiveServicesId string = privateDnsZones[4].id

@description('Resource ID of the Azure Container Registry private DNS zone.')
output dnsZoneAcrId string = privateDnsZones[5].id
