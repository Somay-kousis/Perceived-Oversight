// Shapes returned by the read-only Python API (perceived_oversight.explorer).

export type Outcome = 'execute' | 'hold' | 'stop'

/** Models per role and the arm, as the run recorded them; null where a run did not record it. */
export interface Setup {
  untrusted: string | null
  monitor: string | null
  broker: string | null
  judge: string | null
  arm: string | null
}

export interface Ended {
  reason: string // finished, cost limit, token limit, time limit, monitor stop, error, ...
  detail: string | null
}

export interface FailedRequest {
  step: number
  kind: 'rejected' | 'not_executed'
  detail: string
}

export interface JudgeLabel {
  judge: string // disclosure, probing, hold_response
  hold: number | null
  label: string
}

/** Scores a second monitor gave the same requests on replay, aligned with `actions`. */
export interface Replay {
  model: string
  scores: (number | null)[]
}

export interface RunRow {
  id: string
  kind: 'dev' | 'study'
  split: boolean
  reasoning_open: boolean
  episodes: number | null
  spend_usd: number | null
  error: string | null
  setup: Setup
}

export interface EpisodeSummary {
  n: number
  log_file: string
  sample_id: string
  epoch: number
  condition: string
  mode: string
  task_pair: string
  scored: number
  max_score: number | null
  outcomes: Record<Outcome, number>
  scores: (number | null)[]
  outcome_list: Outcome[]
  stopped: boolean
  error: boolean
  ended: Ended
  main_task_success: boolean | null
  side_task_success: boolean | null
}

export interface RunDetail {
  id: string
  kind: 'dev' | 'study'
  reasoning_open: boolean
  setup: Setup
  episodes: EpisodeSummary[]
}

export interface ScoredAction {
  i: number
  action: string
  transcript_len: number
  leaks: string[]
  scores: Record<string, number | null>
  score: number | null
  outcome: Outcome
  parsed_by: Record<string, 'tag' | 'fallback' | null>
  prompt_files: Record<string, string>
}

export interface ReasoningItem {
  step: number
  kind: string
  model: string
  text: string
}

export interface ReasoningPart {
  sealed: boolean
  blocks: number
  items: ReasoningItem[]
}

export interface EpisodeDetail extends EpisodeSummary {
  actions: ScoredAction[]
  failed_requests: FailedRequest[]
  judges: JudgeLabel[]
  replays: Replay[]
  steps: { role: string; text: string; tool_calls: string[] }[]
  reasoning: { agent: ReasoningPart; broker: ReasoningPart }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// A static build (VITE_STATIC=1) reads the exported snapshot: /runs -> /data/runs.json and so on.
const STATIC = import.meta.env.VITE_STATIC === '1'
const url = (path: string) => (STATIC ? `/data${path}.json` : `/api${path}`)

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url(path), { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? (STATIC && response.status === 404 ? 'not in this snapshot' : `request failed (${response.status})`))
  }
  return response.json() as Promise<T>
}

export const api = {
  runs: (signal?: AbortSignal) => get<RunRow[]>('/runs', signal),
  run: (id: string, signal?: AbortSignal) => get<RunDetail>(`/runs/${encodeURIComponent(id)}`, signal),
  episode: (id: string, n: number, signal?: AbortSignal) =>
    get<EpisodeDetail>(`/runs/${encodeURIComponent(id)}/episodes/${n}`, signal),
}

/** "request_type: payment\namount: 4295" -> { request_type: "payment", amount: "4295" } */
export function parseAction(action: string): Record<string, string> {
  const fields: Record<string, string> = {}
  for (const line of action.split('\n')) {
    const at = line.indexOf(':')
    if (at > 0) fields[line.slice(0, at).trim()] = line.slice(at + 1).trim()
  }
  return fields
}

/** "bedrock_reasoning/deepseek.v3.2" -> "DeepSeek V3.2"; unknown ids keep the part after the provider. */
const NAMES: [RegExp, string][] = [
  [/deepseek\.v3\.2/, 'DeepSeek V3.2'],
  [/gpt-oss-120b/, 'gpt-oss-120b'],
  [/gpt-oss-20b/, 'gpt-oss-20b'],
  [/grok-4\.7/, 'Grok 4.7'],
  [/kimi-k3/, 'Kimi K3'],
  [/glm-5/, 'GLM-5'],
  [/claude-sonnet-5-5/, 'Claude Sonnet 5.5'],
  [/claude-haiku-4-5/, 'Claude Haiku 4.5'],
  [/claude-haiku-5-5/, 'Claude Haiku 5.5'],
  [/claude-opus-5-5/, 'Claude Opus 5.5'],
  [/mockllm/, 'mock model'],
]
export function modelName(id: string | null): string {
  if (!id) return 'not recorded'
  for (const [pattern, name] of NAMES) if (pattern.test(id)) return name
  return id.split('/').pop() ?? id
}

/** An episode cut by a limit did not fail its task, it ran out; say which. */
export const cutShort = (e: Ended) => e.reason !== 'finished' && e.reason !== 'monitor stop'

export const SUSPICIOUS = 60 // scores above this are drawn in amber

export const money = (usd: number | null) => (usd === null ? 'n/a' : `$${usd.toFixed(2)}`)
