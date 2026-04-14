// ──────────────────────────────────────────────────────────────────────────────
// Module: monitoring.bicep
// Log Analytics workspace and Application Insights for observability.
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

var logAnalyticsName = 'log-${environmentName}'
var appInsightsName = 'appi-${environmentName}'

// ──────────────────────────────────────────────────────────────────────────────
// Log Analytics Workspace
// ──────────────────────────────────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Application Insights (workspace-based)
// ──────────────────────────────────────────────────────────────────────────────

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    Flow_Type: 'Bluefield'
    Request_Source: 'rest'
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Outputs
// ──────────────────────────────────────────────────────────────────────────────

@description('Resource ID of the Log Analytics workspace.')
output logAnalyticsId string = logAnalytics.id

@description('Name of the Log Analytics workspace.')
output logAnalyticsName string = logAnalytics.name

@description('Resource ID of the Application Insights instance.')
output appInsightsId string = appInsights.id

@description('Application Insights connection string.')
output appInsightsConnectionString string = appInsights.properties.ConnectionString

@description('Application Insights instrumentation key.')
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
