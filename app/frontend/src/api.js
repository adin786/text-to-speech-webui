const API_PREFIX = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = payload?.detail?.message ?? "Request failed.";
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function fetchConfig() {
  return request("/config");
}

export function fetchModels() {
  return request("/models");
}

export function fetchJobs() {
  return request("/jobs");
}

export function createJob(payload) {
  return request("/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchJob(jobId) {
  return request(`/jobs/${jobId}`);
}
