// Main orchestrator for Azure AI Foundry Workshop infrastructure
targetScope = 'resourceGroup'

@description('Environment name (e.g., dev, staging, prod).')
param environmentName string

@description('Primary Azure region for all resources.')
param location string = resourceGroup().location

@description('Tags applied to every resource.')
param tags object = {
  environment: environmentName
  project: 'msft-foundry-workshop'
}

@description('Principal ID for role assignments (e.g., the deploying user or service principal). Required because several modules (storage, keyvault, openai, aiSearch) need it before the security module is created.')
param principalId string

@description('Azure region for Foundry account and project. May differ from primary location for agent service availability.')
param foundryLocation string = 'eastus2'

// ---------- Modules ----------

module networking 'modules/networking.bicep' = {
  name: 'networking'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry-${environmentName}'
  params: {
    environmentName: environmentName
    location: location
    foundryLocation: foundryLocation
    tags: tags
    subnetId: networking.outputs.subnetPrivateEndpointsId
    privateDnsZoneId: networking.outputs.dnsZoneCognitiveServicesId
    // managedIdentityId intentionally omitted (uses default '') to avoid circular dependency:
    // security depends on aiFoundry.outputs.foundryResourceId, so aiFoundry cannot depend on security.
    // The managed identity is assigned RBAC on the Foundry Hub via the security module instead.

    // Connections: AI Search + Application Insights
    searchServiceId: aiSearch.outputs.searchServiceId
    searchServiceName: aiSearch.outputs.searchServiceName
    appInsightsId: monitoring.outputs.appInsightsId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// ──────────────────────────────────────
// Monitoring (Log Analytics)
// ──────────────────────────────────────
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
  }
}

// ──────────────────────────────────────
// Container Apps
// ──────────────────────────────────────
module containerApps 'modules/container-apps.bicep' = {
  name: 'containerApps'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    acaSubnetId: networking.outputs.subnetAcaId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsId
    managedIdentityId: security.outputs.managedIdentityId
    chatDeploymentName: aiFoundry.outputs.chatDeploymentName
    embeddingDeploymentName: aiFoundry.outputs.embeddingDeploymentName
    foundryEndpoint: aiFoundry.outputs.foundryEndpoint
    projectEndpoint: aiFoundry.outputs.projectEndpoint
    searchEndpoint: aiSearch.outputs.searchEndpointUrl
  }
}

// ---------- Outputs ----------

// ──────────────────────────────────────
// Security (Managed Identity + RBAC)
// ──────────────────────────────────────
module security 'modules/security.bicep' = {
  name: 'security'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    storageAccountId: storage.outputs.storageAccountId
    aiFoundryId: aiFoundry.outputs.foundryResourceId
    keyVaultId: keyvault.outputs.keyVaultId
    deployingPrincipalId: principalId
  }
}

// ──────────────────────────────────────
// Storage Account
// ──────────────────────────────────────
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    subnetId: networking.outputs.subnetPrivateEndpointsId
    privateDnsZoneId: networking.outputs.dnsZoneBlobId
    principalId: principalId
  }
}

// ──────────────────────────────────────
// Key Vault
// ──────────────────────────────────────
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    subnetId: networking.outputs.subnetPrivateEndpointsId
    privateDnsZoneId: networking.outputs.dnsZoneKeyVaultId
    principalId: principalId
  }
}

// ──────────────────────────────────────
// Azure AI Search
// ──────────────────────────────────────
module aiSearch 'modules/ai-search.bicep' = {
  name: 'aiSearch'
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    skuName: 'basic'
    subnetId: networking.outputs.subnetPrivateEndpointsId
    privateDnsZoneId: networking.outputs.dnsZoneSearchId
    principalId: principalId
  }
}


@description('Resource ID of the AI Foundry account.')
output aiFoundryResourceId string = aiFoundry.outputs.foundryResourceId

@description('Resource ID of the AI Foundry Project.')
output aiFoundryProjectId string = aiFoundry.outputs.projectId

@description('Name of the AI Foundry Project.')
output aiFoundryProjectName string = aiFoundry.outputs.projectName

@description('Endpoint URL of the AI Foundry account (also serves as OpenAI endpoint).')
output aiFoundryEndpointUrl string = aiFoundry.outputs.foundryEndpoint

@description('Name of the chat model deployment.')
output chatDeploymentName string = aiFoundry.outputs.chatDeploymentName

@description('Name of the embedding model deployment.')
output embeddingDeploymentName string = aiFoundry.outputs.embeddingDeploymentName

@description('Resource ID of the Azure AI Search service.')
output searchId string = aiSearch.outputs.searchServiceId

@description('Name of the Azure AI Search service.')
output searchName string = aiSearch.outputs.searchServiceName

@description('Endpoint URL of the Azure AI Search service.')
output searchEndpoint string = aiSearch.outputs.searchEndpointUrl

@description('Resource ID of the Container Apps Environment.')
output acaEnvironmentId string = containerApps.outputs.acaEnvironmentId

@description('Name of the Azure Container Registry.')
output acrName string = containerApps.outputs.acrName

@description('Login server of the Azure Container Registry.')
output acrLoginServer string = containerApps.outputs.acrLoginServer

@description('FQDN of the backend container app.')
output backendFqdn string = containerApps.outputs.backendFqdn

@description('FQDN of the frontend container app.')
output frontendFqdn string = containerApps.outputs.frontendFqdn

@description('Storage Account name.')
output storageName string = storage.outputs.storageAccountName

@description('Key Vault name.')
output keyVaultName string = keyvault.outputs.keyVaultName

@description('Managed Identity resource ID.')
output managedIdentityId string = security.outputs.managedIdentityId

@description('Managed Identity principal ID.')
output managedIdentityPrincipalId string = security.outputs.managedIdentityPrincipalId

@description('Managed Identity client ID.')
output managedIdentityClientId string = security.outputs.managedIdentityClientId

@description('ACR login server endpoint for azd deploy.')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.acrLoginServer

@description('Azure AI Foundry endpoint (serves as both Foundry and OpenAI endpoint).')
output AZURE_OPENAI_ENDPOINT string = aiFoundry.outputs.foundryEndpoint

@description('Azure AI Search endpoint for azd.')
output AZURE_SEARCH_ENDPOINT string = aiSearch.outputs.searchEndpointUrl

@description('Search index name used by the application.')
output AZURE_SEARCH_INDEX_NAME string = 'documents'

@description('AI Foundry endpoint for azd.')
output AZURE_AI_PROJECT_ENDPOINT string = aiFoundry.outputs.projectEndpoint

@description('Backend container app FQDN for azd.')
output BACKEND_FQDN string = containerApps.outputs.backendFqdn

@description('Frontend container app FQDN for azd.')
output FRONTEND_FQDN string = containerApps.outputs.frontendFqdn
