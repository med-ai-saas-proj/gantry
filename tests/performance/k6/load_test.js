import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
const userToken = __ENV.USER_TOKEN || '';
const adminToken = __ENV.ADMIN_TOKEN || '';
const apiKey = __ENV.API_KEY || '';
const projectUuid = __ENV.PROJECT_UUID || '';
const apiKeyUuid = __ENV.API_KEY_UUID || '';
const conversationUid = __ENV.CONVERSATION_UID || '';

export const options = {
  scenarios: {
    public_catalogs: {
      executor: 'constant-vus',
      vus: Number(__ENV.K6_PUBLIC_VUS || 2),
      duration: __ENV.K6_PUBLIC_DURATION || '30s',
      exec: 'publicCatalogs',
    },
    management_user: {
      executor: 'constant-vus',
      vus: Number(__ENV.K6_USER_VUS || 1),
      duration: __ENV.K6_USER_DURATION || '30s',
      exec: 'managementUser',
    },
    admin_dashboard: {
      executor: 'constant-vus',
      vus: Number(__ENV.K6_ADMIN_VUS || 1),
      duration: __ENV.K6_ADMIN_DURATION || '30s',
      exec: 'adminDashboard',
    },
    api_key_service: {
      executor: 'constant-vus',
      vus: Number(__ENV.K6_API_KEY_VUS || 1),
      duration: __ENV.K6_API_KEY_DURATION || '30s',
      exec: 'apiKeyService',
    },
  },
  thresholds: {
    http_req_failed: [__ENV.K6_FAILED_THRESHOLD || 'rate<0.01'],
    http_req_duration: [__ENV.K6_P95_THRESHOLD || 'p(95)<500'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
};

function authHeaders(token) {
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
}

function apiKeyHeaders(key) {
  return key ? { headers: { 'X-Api-Key': key } } : {};
}

function checkNo5xx(response, label) {
  check(response, { [`${label} is not 5xx`]: (res) => res.status < 500 });
}

export function publicCatalogs() {
  for (const path of [
    '/management/v1/organizations/permissions',
    '/management/v1/projects/permissions',
    '/management/v1/api-keys/permissions',
  ]) {
    const response = http.get(`${baseUrl}${path}`);
    check(response, { [`${path} status is 200`]: (res) => res.status === 200 });
  }
  sleep(1);
}

export function managementUser() {
  const headers = authHeaders(userToken);
  checkNo5xx(http.get(`${baseUrl}/management/v1/projects`, headers), 'project list');
  const query = projectUuid ? `?project_id=${projectUuid}` : '';
  checkNo5xx(http.get(`${baseUrl}/management/v1/api-keys${query}`, headers), 'api key list');
  if (apiKeyUuid) {
    checkNo5xx(http.get(`${baseUrl}/management/v1/api-keys/${apiKeyUuid}`, headers), 'api key detail');
  }
  sleep(1);
}

export function adminDashboard() {
  const headers = authHeaders(adminToken);
  checkNo5xx(http.get(`${baseUrl}/management/v1/admin/dashboard/summary`, headers), 'admin summary');
  checkNo5xx(http.get(`${baseUrl}/management/v1/admin/users`, headers), 'admin users');
  sleep(1);
}

export function apiKeyService() {
  const headers = apiKeyHeaders(apiKey);
  checkNo5xx(http.get(`${baseUrl}/service/v1/file-storage/service/`, headers), 'service files');
  checkNo5xx(http.get(`${baseUrl}/service/v1/rag/service/files`, headers), 'service rag files');
  if (conversationUid) {
    checkNo5xx(
      http.get(`${baseUrl}/service/v1/conversations/${conversationUid}`, headers),
      'conversation detail',
    );
  }
  sleep(1);
}

export default function () {
  publicCatalogs();
}
