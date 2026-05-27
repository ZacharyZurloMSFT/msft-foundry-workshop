// Module: container-apps
// Azure Container Apps environment, ACR, backend and frontend container apps.

@description('Environment name (e.g., dev, staging, prod).')
param environmentName string

@description('Primary Azure region for all resources.')
param location string

@description('Tags applied to every resource.')
param tags object

@description('Resource ID of the ACA-delegated subnet.')
param acaSubnetId string

@description('Resource ID of the Log Analytics workspace.')
param logAnalyticsWorkspaceId string

@description('Resource ID of a user-assigned managed identity for ACR pull and Azure service auth.')
param managedIdentityId string

@description('Azure AI Foundry endpoint URL (also serves as OpenAI endpoint).')
param foundryEndpoint string

@description('Project-scoped endpoint for the AI Projects SDK.')
param projectEndpoint string

@description('Azure AI Search endpoint URL.')
param searchEndpoint string

@description('Name of the Azure AI Search index.')
param searchIndexName string = 'documents'

@description('Client ID of the user-assigned managed identity (for AZURE_MANAGED_IDENTITY_CLIENT_ID env var).')
param managedIdentityClientId string

@description('Name of the OpenAI chat model deployment.')
param chatDeploymentName string

@description('Name of the OpenAI embedding model deployment.')
param embeddingDeploymentName string

// ──────────────────────────────────────────────────────────────────────────────
// Container Apps Environment (Consumption, VNet-integrated)
// ──────────────────────────────────────────────────────────────────────────────

@description('Container Apps Environment with VNet integration and Log Analytics.')
resource acaEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${environmentName}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnetId
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// Reference the existing Log Analytics workspace to get customerId and key
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(logAnalyticsWorkspaceId, '/'))
}

var logAnalyticsCustomerId = logAnalytics.properties.customerId
var logAnalyticsSharedKey = logAnalytics.listKeys().primarySharedKey

// ──────────────────────────────────────────────────────────────────────────────
// Azure Container Registry (Basic tier)
// ──────────────────────────────────────────────────────────────────────────────

@description('Azure Container Registry for workshop container images.')
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('acr-${environmentName}', '-', '')
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// ACR private endpoint
// ACR pull role assignment for managed identity
@description('AcrPull role assignment for the managed identity.')
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, managedIdentityId, 'acrpull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: managedIdentityPrincipalId
  }
}

// Reference managed identity to get principalId
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: last(split(managedIdentityId, '/'))
}

var managedIdentityPrincipalId = managedIdentity.properties.principalId

// ──────────────────────────────────────────────────────────────────────────────
// Backend Container App
// ──────────────────────────────────────────────────────────────────────────────

@description('Backend container app for the AI Foundry workshop.')
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-backend-${environmentName}'
  location: location
  tags: union(tags, { 'azd-service-name': 'backend' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: foundryEndpoint
            }
            {
              name: 'AZURE_AI_PROJECT_ENDPOINT'
              value: projectEndpoint
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: searchEndpoint
            }
            {
              name: 'AZURE_SEARCH_INDEX_NAME'
              value: searchIndexName
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: chatDeploymentName
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: embeddingDeploymentName
            }
            {
              name: 'AZURE_MANAGED_IDENTITY_CLIENT_ID'
              value: managedIdentityClientId
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Frontend Container App
// ──────────────────────────────────────────────────────────────────────────────

@description('Frontend container app for the AI Foundry workshop.')
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-frontend-${environmentName}'
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────────────────────────────────────

@description('Resource ID of the Container Apps Environment.')
output acaEnvironmentId string = acaEnv.id

@description('Name of the Azure Container Registry.')
output acrName string = acr.name

@description('Login server URL of the Azure Container Registry.')
output acrLoginServer string = acr.properties.loginServer

@description('FQDN of the backend container app.')
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn

@description('FQDN of the frontend container app.')
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
