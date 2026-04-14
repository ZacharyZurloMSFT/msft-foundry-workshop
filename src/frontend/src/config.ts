// Auto-detect backend URL based on current hostname
function getApiBaseUrl(): string {
  // If explicitly set at build time, use that
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // Auto-detect: if running on Azure Container Apps, derive backend URL from frontend URL
  const hostname = window.location.hostname;
  if (hostname.includes('azurecontainerapps.io')) {
    // Frontend: ca-frontend-xxx.env.region.azurecontainerapps.io
    // Backend:  ca-backend-xxx.env.region.azurecontainerapps.io
    const backendHost = hostname.replace('ca-frontend-', 'ca-backend-');
    return `https://${backendHost}`;
  }

  // Local development fallback
  return 'http://localhost:8000';
}

export const API_BASE_URL = getApiBaseUrl();
