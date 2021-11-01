const host = window.location.hostname.split('.')
export const SUPPORT_API_BASE_URL = `https://support.${host[host.length - 2]}.${host[host.length - 1]}`;
export const SUPPORT_API_SHINY_BASE_URL = `https://dashboards.${host[host.length - 2]}.${host[host.length - 1]}`;