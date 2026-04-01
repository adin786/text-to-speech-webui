import { useEffect, useMemo, useRef, useState } from "react";
import { createJob, fetchConfig, fetchJob, fetchJobs, fetchModels } from "./api";

const defaultForm = {
  text: "",
  model: "kokoro",
  voice: "",
  language: "en",
  speed: 1,
  output_format: "mp3",
};

function usePollingJob(jobId, onUpdate, onError) {
  useEffect(() => {
    if (!jobId) {
      return undefined;
    }

    let active = true;
    const timer = setInterval(async () => {
      try {
        const next = await fetchJob(jobId);
        if (!active) {
          return;
        }
        onUpdate(next);
        if (next.status === "completed" || next.status === "failed") {
          clearInterval(timer);
        }
      } catch (nextError) {
        clearInterval(timer);
        if (!active) {
          return;
        }
        onError(nextError);
      }
    }, 1000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [jobId, onError, onUpdate]);
}

function AppShell({ children, badge }) {
  return (
    <div className="page">
      <div className="page__glow page__glow--one" />
      <div className="page__glow page__glow--two" />
      <header className="hero">
        <div>
          <p className="eyebrow">Local-First Speech Studio</p>
          <h1>Generate speech offline-ready, preview instantly, export MP3.</h1>
        </div>
        <div className="hero__badge">{badge}</div>
      </header>
      {children}
    </div>
  );
}

function ModelSelector({ models, selectedModel, onChange }) {
  return (
    <div className="field">
      <label htmlFor="model">Model</label>
      <select id="model" value={selectedModel} onChange={(event) => onChange(event.target.value)}>
        {models.map((model) => (
          <option key={model.id} value={model.id} disabled={!model.available}>
            {model.display_name}
            {!model.available ? " (Unavailable)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

function VoiceSelector({ voices, value, onChange }) {
  return (
    <div className="field">
      <label htmlFor="voice">Voice</label>
      <select id="voice" value={value} onChange={(event) => onChange(event.target.value)}>
        {voices.map((voice) => (
          <option key={voice.id} value={voice.id}>
            {voice.display_name}
          </option>
        ))}
      </select>
    </div>
  );
}

function JobStatusPanel({ job }) {
  if (!job) {
    return (
      <section className="card card--status">
        <h2>Current Job</h2>
        <p>Submit text to start a synthesis job.</p>
      </section>
    );
  }

  return (
    <section className="card card--status">
      <div className="status__header">
        <h2>Current Job</h2>
        <span className={`status-pill status-pill--${job.status}`}>{job.status}</span>
      </div>
      <p>{job.progress_message}</p>
      {job.error_message ? <p className="error">{job.error_message}</p> : null}
      {job.output_available ? (
        <>
          <audio controls src={job.preview_url} className="audio-player">
            Your browser does not support audio playback.
          </audio>
          <a className="download-link" href={job.download_url}>
            Download MP3
          </a>
        </>
      ) : null}
    </section>
  );
}

function HistoryPanel({ jobs, onSelect }) {
  return (
    <section className="card">
      <div className="status__header">
        <h2>Recent Jobs</h2>
        <span className="muted">{jobs.length}</span>
      </div>
      <div className="history-list">
        {jobs.length === 0 ? <p>No history yet.</p> : null}
        {jobs.map((job) => (
          <button key={job.job_id} className="history-item" onClick={() => onSelect(job.job_id)}>
            <span>{job.model}</span>
            <strong>{job.status}</strong>
          </button>
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [models, setModels] = useState([]);
  const [history, setHistory] = useState([]);
  const [job, setJob] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) {
      return;
    }
    initialized.current = true;

    async function bootstrap() {
      try {
        const [configResponse, modelsResponse, jobsResponse] = await Promise.all([
          fetchConfig(),
          fetchModels(),
          fetchJobs(),
        ]);
        setConfig(configResponse);
        setModels(modelsResponse.models);
        setHistory(jobsResponse);
        const defaultModel = modelsResponse.models.find((model) => model.available)?.id ?? "kokoro";
        const defaultVoice = modelsResponse.models.find((model) => model.id === defaultModel)?.voices?.[0]?.id ?? "";
        setForm((current) => ({ ...current, model: defaultModel, voice: defaultVoice }));
      } catch (nextError) {
        setError(nextError.message);
      }
    }

    bootstrap();
  }, []);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === form.model) ?? null,
    [form.model, models],
  );

  useEffect(() => {
    if (!selectedModel) {
      return;
    }
    const nextVoice = selectedModel.voices[0]?.id ?? "";
    setForm((current) => ({ ...current, voice: nextVoice, language: selectedModel.languages[0] ?? "en" }));
  }, [selectedModel?.id]);

  usePollingJob(
    job?.job_id,
    async (nextJob) => {
      setJob(nextJob);
      if (nextJob.status === "completed" || nextJob.status === "failed") {
        const jobs = await fetchJobs();
        setHistory(jobs);
      }
    },
    (nextError) => {
      setError(nextError.message);
    },
  );

  const isInvalid = !form.text.trim() || !selectedModel?.available;

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const created = await createJob(form);
      const nextJob = await fetchJob(created.job_id);
      setJob(nextJob);
      const jobs = await fetchJobs();
      setHistory(jobs);
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSelectJob(jobId) {
    try {
      const nextJob = await fetchJob(jobId);
      setJob(nextJob);
      setError("");
    } catch (nextError) {
      setError(nextError.message);
    }
  }

  return (
    <AppShell badge={config?.offline_mode ? "Offline mode ready" : "Online mode"}>
      <main className="layout">
        <section className="card card--form">
          <div className="status__header">
            <h2>Create Speech</h2>
            <span className="muted">{form.text.length}/{config?.max_input_length ?? 1000}</span>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="text">Text</label>
              <textarea
                id="text"
                rows="9"
                value={form.text}
                onChange={(event) => setForm((current) => ({ ...current, text: event.target.value }))}
                placeholder="Type the words you want to hear."
              />
            </div>
            <div className="grid">
              <ModelSelector
                models={models}
                selectedModel={form.model}
                onChange={(value) => setForm((current) => ({ ...current, model: value }))}
              />
              <VoiceSelector
                voices={selectedModel?.voices ?? []}
                value={form.voice}
                onChange={(value) => setForm((current) => ({ ...current, voice: value }))}
              />
              <div className="field">
                <label htmlFor="language">Language</label>
                <select
                  id="language"
                  value={form.language}
                  onChange={(event) => setForm((current) => ({ ...current, language: event.target.value }))}
                >
                  {(selectedModel?.languages ?? ["en"]).map((language) => (
                    <option key={language} value={language}>
                      {language.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="speed">Speed</label>
                <input
                  id="speed"
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={form.speed}
                  onChange={(event) => setForm((current) => ({ ...current, speed: Number(event.target.value) }))}
                />
                <span className="muted">{form.speed.toFixed(1)}x</span>
              </div>
            </div>
            {selectedModel?.notes ? <p className="note">{selectedModel.notes}</p> : null}
            {error ? <p className="error">{error}</p> : null}
            <button className="primary-button" type="submit" disabled={isInvalid || submitting}>
              {submitting ? "Submitting..." : "Generate MP3"}
            </button>
          </form>
        </section>
        <JobStatusPanel job={job} />
        <HistoryPanel jobs={history} onSelect={handleSelectJob} />
      </main>
    </AppShell>
  );
}
