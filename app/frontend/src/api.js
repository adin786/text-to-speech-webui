const API_PREFIX = "/api";

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: isFormData
      ? { ...(options.headers ?? {}) }
      : {
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

export function fetchVoiceSamples() {
  return request("/voices");
}

export function createVoiceSample({ name, transcript, audioFile }) {
  const body = new FormData();
  body.append("name", name);
  body.append("transcript", transcript);
  body.append("audio", audioFile);
  return request("/voices", {
    method: "POST",
    body,
  });
}

export function updateVoiceSample(sampleId, payload) {
  return request(`/voices/${sampleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteVoiceSample(sampleId) {
  return request(`/voices/${sampleId}`, {
    method: "DELETE",
  });
}
