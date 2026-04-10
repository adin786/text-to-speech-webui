import { useEffect, useMemo, useRef, useState } from "react";
import {
  createJob,
  createVoiceSample,
  deleteVoiceSample,
  fetchConfig,
  fetchJob,
  fetchJobs,
  fetchModels,
  fetchVoiceSamples,
  updateVoiceSample,
} from "./api";

const defaultForm = {
  text: "",
  model: "kokoro",
  voice: "",
  saved_voice_id: "",
  language: "en",
  speed: 1,
  kokoro_speed: 1,
  kokoro_split_pattern: "\\n+",
  qwen_non_streaming_mode: true,
  qwen_do_sample: true,
  qwen_top_k: 50,
  qwen_top_p: 0.95,
  qwen_temperature: 0.8,
  qwen_repetition_penalty: 1.1,
  qwen_subtalker_do_sample: true,
  qwen_subtalker_top_k: 30,
  qwen_subtalker_top_p: 0.95,
  qwen_subtalker_temperature: 0.8,
  qwen_max_new_tokens: 2048,
  qwen_x_vector_only_mode: false,
  output_format: "mp3",
};

const defaultVoiceDraft = {
  name: "",
  transcript: "",
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
      <select
        id="model"
        value={selectedModel}
        onChange={(event) => onChange(event.target.value)}
      >
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
      <select
        id="voice"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {voices.map((voice) => (
          <option key={voice.id} value={voice.id}>
            {voice.display_name}
          </option>
        ))}
      </select>
    </div>
  );
}

function VoiceModeSelector({ mode, onChange }) {
  return (
    <div className="field">
      <label>Qwen Voice Mode</label>
      <div className="segmented-control">
        <button
          type="button"
          className={mode === "builtin" ? "segment is-active" : "segment"}
          onClick={() => onChange("builtin")}
        >
          Built-in voices
        </button>
        <button
          type="button"
          className={mode === "saved" ? "segment is-active" : "segment"}
          onClick={() => onChange("saved")}
        >
          Saved cloned voices
        </button>
      </div>
    </div>
  );
}

function SavedVoiceSelector({ voices, value, onChange }) {
  return (
    <div className="field">
      <label htmlFor="saved-voice">Saved Voice</label>
      <select
        id="saved-voice"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Select a saved voice</option>
        {voices.map((voice) => (
          <option key={voice.sample_id} value={voice.sample_id}>
            {voice.name}
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
        <span className={`status-pill status-pill--${job.status}`}>
          {job.status}
        </span>
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
          <button
            key={job.job_id}
            className="history-item"
            onClick={() => onSelect(job.job_id)}
          >
            <span>{job.model}</span>
            <strong>{job.status}</strong>
          </button>
        ))}
      </div>
    </section>
  );
}

function VoiceLabPanel({
  qwenEnabled,
  voices,
  activeVoiceId,
  onSelectVoice,
  editor,
  onEditorChange,
  onSaveEdits,
  onDelete,
  draft,
  onDraftChange,
  draftPreviewUrl,
  onDraftFileChange,
  onStartRecording,
  onStopRecording,
  recording,
  recordingAvailable,
  onSaveDraft,
  savingDraft,
}) {
  const selectedVoice =
    voices.find((voice) => voice.sample_id === activeVoiceId) ?? null;

  return (
    <section className="card">
      <div className="status__header">
        <h2>Voice Lab</h2>
        <span className="muted">{voices.length} saved</span>
      </div>
      {!qwenEnabled ? (
        <p className="note">Enable Qwen to create and reuse cloned voices.</p>
      ) : null}
      <div className="guide">
        <p className="note">How to get the best clone</p>
        <ul className="guide-list">
          <li>Record one speaker in a quiet room with no music underneath.</li>
          <li>
            Qwen documents cloning from a short reference clip. In practice, 5-15
            seconds of clean speech is a safer target than the bare minimum.
          </li>
          <li>
            The transcript must match the recording exactly. Read a short script
            instead of free-form improvising.
          </li>
          <li>
            Natural, continuous speech works better than long pauses, shouting,
            or heavily compressed audio.
          </li>
        </ul>
      </div>

      <div className="voice-lab__section">
        <div className="status__header">
          <h3>New Voice Sample</h3>
          {recording ? <span className="recording-pill">Recording</span> : null}
        </div>
        <div className="field">
          <label htmlFor="voice-sample-name">Name</label>
          <input
            id="voice-sample-name"
            value={draft.name}
            onChange={(event) => onDraftChange("name", event.target.value)}
            placeholder="Narrator A"
          />
        </div>
        <div className="field">
          <label htmlFor="voice-sample-transcript">Exact Transcript</label>
          <textarea
            id="voice-sample-transcript"
            rows="4"
            value={draft.transcript}
            onChange={(event) => onDraftChange("transcript", event.target.value)}
            placeholder="Type exactly what you say in the recording."
          />
        </div>
        <div className="voice-actions">
          {recordingAvailable ? (
            <>
              {!recording ? (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={onStartRecording}
                >
                  Start recording
                </button>
              ) : (
                <button
                  type="button"
                  className="secondary-button secondary-button--danger"
                  onClick={onStopRecording}
                >
                  Stop recording
                </button>
              )}
            </>
          ) : (
            <p className="muted">This browser does not support in-page recording.</p>
          )}
          <label className="upload-button">
            Import audio
            <input
              type="file"
              accept="audio/*"
              onChange={(event) => onDraftFileChange(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        {draftPreviewUrl ? (
          <audio controls className="audio-player" src={draftPreviewUrl}>
            Your browser does not support audio playback.
          </audio>
        ) : (
          <p className="muted">Record in-browser or import an audio file to save it.</p>
        )}
        <button
          type="button"
          className="primary-button"
          onClick={onSaveDraft}
          disabled={savingDraft || !draftPreviewUrl || !qwenEnabled}
        >
          {savingDraft ? "Saving..." : "Save cloned voice"}
        </button>
      </div>

      <div className="voice-lab__section">
        <div className="status__header">
          <h3>Saved Voices</h3>
          {selectedVoice ? (
            <button
              type="button"
              className="text-button"
              onClick={() => onSelectVoice("")}
            >
              Clear selection
            </button>
          ) : null}
        </div>
        <div className="voice-list">
          {voices.length === 0 ? <p>No saved voices yet.</p> : null}
          {voices.map((voice) => (
            <button
              key={voice.sample_id}
              type="button"
              className={
                voice.sample_id === activeVoiceId
                  ? "voice-list__item is-active"
                  : "voice-list__item"
              }
              onClick={() => onSelectVoice(voice.sample_id)}
            >
              <strong>{voice.name}</strong>
              <span>{voice.duration_seconds}s</span>
            </button>
          ))}
        </div>
        {selectedVoice ? (
          <div className="voice-editor">
            <audio controls className="audio-player" src={selectedVoice.audio_url}>
              Your browser does not support audio playback.
            </audio>
            <div className="field">
              <label htmlFor="edit-voice-name">Rename</label>
              <input
                id="edit-voice-name"
                value={editor.name}
                onChange={(event) => onEditorChange("name", event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="edit-voice-transcript">Transcript</label>
              <textarea
                id="edit-voice-transcript"
                rows="4"
                value={editor.transcript}
                onChange={(event) => onEditorChange("transcript", event.target.value)}
              />
            </div>
            <div className="voice-actions">
              <button type="button" className="secondary-button" onClick={onSaveEdits}>
                Save changes
              </button>
              <button
                type="button"
                className="secondary-button secondary-button--danger"
                onClick={() => onDelete(selectedVoice.sample_id)}
              >
                Delete voice
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("generation");
  const [config, setConfig] = useState(null);
  const [models, setModels] = useState([]);
  const [savedVoices, setSavedVoices] = useState([]);
  const [history, setHistory] = useState([]);
  const [job, setJob] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [voiceMode, setVoiceMode] = useState("builtin");
  const [voiceDraft, setVoiceDraft] = useState(defaultVoiceDraft);
  const [voiceEditor, setVoiceEditor] = useState(defaultVoiceDraft);
  const [draftAudioFile, setDraftAudioFile] = useState(null);
  const [draftPreviewUrl, setDraftPreviewUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [savingVoice, setSavingVoice] = useState(false);
  const [error, setError] = useState("");
  const initialized = useRef(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const recorderChunksRef = useRef([]);
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    if (initialized.current) {
      return;
    }
    initialized.current = true;

    async function bootstrap() {
      try {
        const [configResponse, modelsResponse, jobsResponse, voiceSamples] =
          await Promise.all([
            fetchConfig(),
            fetchModels(),
            fetchJobs(),
            fetchVoiceSamples(),
          ]);
        setConfig(configResponse);
        setModels(modelsResponse.models);
        setHistory(jobsResponse);
        setSavedVoices(voiceSamples);
        const defaultModel =
          modelsResponse.models.find((model) => model.available)?.id ?? "kokoro";
        const defaultVoice =
          modelsResponse.models.find((model) => model.id === defaultModel)?.voices?.[0]
            ?.id ?? "";
        setForm((current) => ({
          ...current,
          model: defaultModel,
          voice: defaultVoice,
          saved_voice_id: voiceSamples[0]?.sample_id ?? "",
        }));
      } catch (nextError) {
        setError(nextError.message);
      }
    }

    bootstrap();
  }, []);

  useEffect(() => {
    return () => {
      if (draftPreviewUrl) {
        URL.revokeObjectURL(draftPreviewUrl);
      }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [draftPreviewUrl]);

  const selectedModel = useMemo(
    () => models.find((model) => model.id === form.model) ?? null,
    [form.model, models],
  );
  const qwenEnabled = models.some((model) => model.id === "qwen3_0_6b" && model.enabled);
  const isQwenSelected = form.model === "qwen3_0_6b";

  useEffect(() => {
    if (!selectedModel) {
      return;
    }
    const nextVoice = selectedModel.voices[0]?.id ?? "";
    setForm((current) => ({
      ...current,
      voice: nextVoice,
      language: selectedModel.languages[0] ?? "en",
      saved_voice_id:
        current.saved_voice_id || savedVoices[0]?.sample_id || "",
    }));
  }, [selectedModel?.id, savedVoices]);

  useEffect(() => {
    const activeSavedVoice =
      savedVoices.find((voice) => voice.sample_id === form.saved_voice_id) ?? null;
    setVoiceEditor(
      activeSavedVoice
        ? {
            name: activeSavedVoice.name,
            transcript: activeSavedVoice.transcript,
          }
        : defaultVoiceDraft,
    );
  }, [form.saved_voice_id, savedVoices]);

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

  const isInvalid =
    !form.text.trim() ||
    !selectedModel?.available ||
    (isQwenSelected && voiceMode === "saved" && !form.saved_voice_id);

  async function refreshVoiceSamples(selectSampleId = null) {
    const nextSamples = await fetchVoiceSamples();
    setSavedVoices(nextSamples);
    const fallbackId = selectSampleId ?? nextSamples[0]?.sample_id ?? "";
    setForm((current) => ({
      ...current,
      saved_voice_id: nextSamples.some((sample) => sample.sample_id === current.saved_voice_id)
        ? current.saved_voice_id
        : fallbackId,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        ...form,
        voice: isQwenSelected && voiceMode === "saved" ? null : form.voice,
        saved_voice_id:
          isQwenSelected && voiceMode === "saved" ? form.saved_voice_id : null,
      };
      const created = await createJob(payload);
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

  function setDraftAudio(file) {
    if (draftPreviewUrl) {
      URL.revokeObjectURL(draftPreviewUrl);
    }
    setDraftAudioFile(file);
    setDraftPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  async function handleStartRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      recorderChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recorderChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        const blob = new Blob(recorderChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        const extension = blob.type.includes("ogg") ? "ogg" : "webm";
        const file = new File([blob], `voice-sample.${extension}`, {
          type: blob.type || "audio/webm",
        });
        setDraftAudio(file);
        mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        setIsRecording(false);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch (nextError) {
      setError(nextError.message || "Could not start recording.");
    }
  }

  function handleStopRecording() {
    mediaRecorderRef.current?.stop();
  }

  async function handleSaveVoiceSample() {
    setSavingVoice(true);
    setError("");
    try {
      const created = await createVoiceSample({
        name: voiceDraft.name,
        transcript: voiceDraft.transcript,
        audioFile: draftAudioFile,
      });
      await refreshVoiceSamples(created.sample_id);
      setForm((current) => ({ ...current, saved_voice_id: created.sample_id }));
      setVoiceMode("saved");
      setVoiceDraft(defaultVoiceDraft);
      setDraftAudio(null);
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setSavingVoice(false);
    }
  }

  async function handleSaveVoiceEdits() {
    if (!form.saved_voice_id) {
      return;
    }
    setError("");
    try {
      await updateVoiceSample(form.saved_voice_id, voiceEditor);
      await refreshVoiceSamples(form.saved_voice_id);
    } catch (nextError) {
      setError(nextError.message);
    }
  }

  async function handleDeleteVoice(sampleId) {
    setError("");
    try {
      await deleteVoiceSample(sampleId);
      await refreshVoiceSamples();
    } catch (nextError) {
      setError(nextError.message);
    }
  }

  return (
    <AppShell badge={config?.offline_mode ? "Offline mode ready" : "Online mode"}>
      <div className="tab-nav" role="tablist" aria-label="Voice workflow tabs">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "generation"}
          className={activeTab === "generation" ? "tab-button is-active" : "tab-button"}
          onClick={() => setActiveTab("generation")}
        >
          Voice Generation
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "cloning"}
          className={activeTab === "cloning" ? "tab-button is-active" : "tab-button"}
          onClick={() => setActiveTab("cloning")}
        >
          Voice Cloning
        </button>
      </div>

      {activeTab === "generation" ? (
        <main className="layout">
          <section className="card card--form">
            <div className="status__header">
              <h2>Create Speech</h2>
              <span className="muted">
                {form.text.length}/{config?.max_input_length ?? 1000}
              </span>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="text">Text</label>
                <textarea
                  id="text"
                  rows="9"
                  value={form.text}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, text: event.target.value }))
                  }
                  placeholder="Type the words you want to hear."
                />
              </div>
              <div className="grid">
                <ModelSelector
                  models={models}
                  selectedModel={form.model}
                  onChange={(value) =>
                    setForm((current) => ({ ...current, model: value }))
                  }
                />
                {isQwenSelected ? (
                  <VoiceModeSelector mode={voiceMode} onChange={setVoiceMode} />
                ) : (
                  <VoiceSelector
                    voices={selectedModel?.voices ?? []}
                    value={form.voice}
                    onChange={(value) =>
                      setForm((current) => ({ ...current, voice: value }))
                    }
                  />
                )}
                {isQwenSelected && voiceMode === "builtin" ? (
                  <VoiceSelector
                    voices={selectedModel?.voices ?? []}
                    value={form.voice}
                    onChange={(value) =>
                      setForm((current) => ({ ...current, voice: value }))
                    }
                  />
                ) : null}
                {isQwenSelected && voiceMode === "saved" ? (
                  <SavedVoiceSelector
                    voices={savedVoices}
                    value={form.saved_voice_id}
                    onChange={(value) =>
                      setForm((current) => ({ ...current, saved_voice_id: value }))
                    }
                  />
                ) : null}
                <div className="field">
                  <label htmlFor="language">Language</label>
                  <select
                    id="language"
                    value={form.language}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        language: event.target.value,
                      }))
                    }
                  >
                    {(selectedModel?.languages ?? []).map((language) => (
                      <option key={language} value={language}>
                        {language}
                      </option>
                    ))}
                  </select>
                </div>
                {selectedModel ? (
                  <div className="model-settings">
                    <div className="model-settings__header">
                      {selectedModel.display_name} inference settings
                    </div>
                    {isQwenSelected ? (
                      <>
                        <div className="field">
                          <label htmlFor="qwen-non-streaming-mode">
                            Qwen Non-streaming Mode
                          </label>
                          <select
                            id="qwen-non-streaming-mode"
                            value={String(form.qwen_non_streaming_mode)}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_non_streaming_mode:
                                  event.target.value === "true",
                              }))
                            }
                          >
                            <option value="true">Enabled</option>
                            <option value="false">Disabled</option>
                          </select>
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-do-sample">Qwen Do Sample</label>
                          <select
                            id="qwen-do-sample"
                            value={String(form.qwen_do_sample)}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_do_sample: event.target.value === "true",
                              }))
                            }
                          >
                            <option value="true">Enabled</option>
                            <option value="false">Disabled</option>
                          </select>
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-top-k">Qwen Top-k</label>
                          <input
                            id="qwen-top-k"
                            type="number"
                            min="1"
                            step="1"
                            value={form.qwen_top_k}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_top_k: Number(event.target.value),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-top-p">Qwen Top-p</label>
                          <input
                            id="qwen-top-p"
                            type="number"
                            min="0.01"
                            max="1"
                            step="0.01"
                            value={form.qwen_top_p}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_top_p: Number(event.target.value),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-temperature">
                            Qwen Temperature
                          </label>
                          <input
                            id="qwen-temperature"
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={form.qwen_temperature}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_temperature: Number(event.target.value),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-repetition-penalty">
                            Qwen Repetition Penalty
                          </label>
                          <input
                            id="qwen-repetition-penalty"
                            type="number"
                            min="1"
                            step="0.01"
                            value={form.qwen_repetition_penalty}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_repetition_penalty: Number(
                                  event.target.value,
                                ),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-subtalker-do-sample">
                            Qwen Subtalker Do Sample
                          </label>
                          <select
                            id="qwen-subtalker-do-sample"
                            value={String(form.qwen_subtalker_do_sample)}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_subtalker_do_sample:
                                  event.target.value === "true",
                              }))
                            }
                          >
                            <option value="true">Enabled</option>
                            <option value="false">Disabled</option>
                          </select>
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-subtalker-top-k">
                            Qwen Subtalker Top-k
                          </label>
                          <input
                            id="qwen-subtalker-top-k"
                            type="number"
                            min="1"
                            step="1"
                            value={form.qwen_subtalker_top_k}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_subtalker_top_k: Number(
                                  event.target.value,
                                ),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-subtalker-top-p">
                            Qwen Subtalker Top-p
                          </label>
                          <input
                            id="qwen-subtalker-top-p"
                            type="number"
                            min="0.01"
                            max="1"
                            step="0.01"
                            value={form.qwen_subtalker_top_p}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_subtalker_top_p: Number(
                                  event.target.value,
                                ),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-subtalker-temperature">
                            Qwen Subtalker Temperature
                          </label>
                          <input
                            id="qwen-subtalker-temperature"
                            type="number"
                            min="0.01"
                            step="0.01"
                            value={form.qwen_subtalker_temperature}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_subtalker_temperature: Number(
                                  event.target.value,
                                ),
                              }))
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor="qwen-max-new-tokens">
                            Qwen Max New Tokens
                          </label>
                          <input
                            id="qwen-max-new-tokens"
                            type="number"
                            min="1"
                            step="1"
                            value={form.qwen_max_new_tokens}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                qwen_max_new_tokens: Number(
                                  event.target.value,
                                ),
                              }))
                            }
                          />
                        </div>
                        {voiceMode === "saved" ? (
                          <div className="field">
                            <label htmlFor="qwen-x-vector-only-mode">
                              Qwen X-vector Only Mode
                            </label>
                            <select
                              id="qwen-x-vector-only-mode"
                              value={String(form.qwen_x_vector_only_mode)}
                              onChange={(event) =>
                                setForm((current) => ({
                                  ...current,
                                  qwen_x_vector_only_mode:
                                    event.target.value === "true",
                                }))
                              }
                            >
                              <option value="false">
                                Disabled (ICL mode)
                              </option>
                              <option value="true">
                                Enabled (embedding only)
                              </option>
                            </select>
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <>
                        <div className="field">
                          <label htmlFor="kokoro-speed">Kokoro Speed</label>
                          <input
                            id="kokoro-speed"
                            type="range"
                            min="0.5"
                            max="1.6"
                            step="0.05"
                            value={form.kokoro_speed}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                kokoro_speed: Number(event.target.value),
                                speed: Number(event.target.value),
                              }))
                            }
                          />
                          <span className="muted">
                            {form.kokoro_speed.toFixed(2)}x
                          </span>
                        </div>
                        <div className="field">
                          <label htmlFor="kokoro-split-pattern">
                            Kokoro Split Pattern (regex)
                          </label>
                          <input
                            id="kokoro-split-pattern"
                            type="text"
                            value={form.kokoro_split_pattern}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                kokoro_split_pattern: event.target.value,
                              }))
                            }
                          />
                        </div>
                      </>
                    )}
                  </div>
                ) : null}
              </div>
              {selectedModel?.notes ? <p className="note">{selectedModel.notes}</p> : null}
              {isQwenSelected && voiceMode === "saved" && savedVoices.length === 0 ? (
                <p className="note">
                  Save a voice sample in the Voice Cloning tab before submitting a Qwen
                  clone job.
                </p>
              ) : null}
              {error ? <p className="error">{error}</p> : null}
              <button className="primary-button" disabled={isInvalid || submitting}>
                {submitting ? "Submitting..." : "Generate Speech"}
              </button>
            </form>
          </section>

          <JobStatusPanel job={job} />
          <HistoryPanel jobs={history} onSelect={handleSelectJob} />
        </main>
      ) : (
        <main className="layout layout--single">
          <VoiceLabPanel
            qwenEnabled={qwenEnabled}
            voices={savedVoices}
            activeVoiceId={form.saved_voice_id}
            onSelectVoice={(sampleId) =>
              setForm((current) => ({ ...current, saved_voice_id: sampleId }))
            }
            editor={voiceEditor}
            onEditorChange={(field, value) =>
              setVoiceEditor((current) => ({ ...current, [field]: value }))
            }
            onSaveEdits={handleSaveVoiceEdits}
            onDelete={handleDeleteVoice}
            draft={voiceDraft}
            onDraftChange={(field, value) =>
              setVoiceDraft((current) => ({ ...current, [field]: value }))
            }
            draftPreviewUrl={draftPreviewUrl}
            onDraftFileChange={setDraftAudio}
            onStartRecording={handleStartRecording}
            onStopRecording={handleStopRecording}
            recording={isRecording}
            recordingAvailable={
              typeof window !== "undefined" &&
              Boolean(window.MediaRecorder) &&
              Boolean(navigator.mediaDevices?.getUserMedia)
            }
            onSaveDraft={handleSaveVoiceSample}
            savingDraft={savingVoice}
          />
        </main>
      )}
    </AppShell>
  );
}
