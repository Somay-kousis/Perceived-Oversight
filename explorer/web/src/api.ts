// Shapes returned by the read-only Python API (perceived_oversight.explorer).

export type Outcome = 'execute' | 'hold' | 'stop'

export interface RunRow {
  id: string
  kind: 'dev' | 'study'
  split: boolean
  reasoning_open: boolean
  episodes: number | null
  spend_usd: number | null
  error: string | null
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
  main_task_success: boolean | null
  side_task_success: boolean | null
}

export interface RunDetail {
  id: string
  kind: 'dev' | 'study'
  reasoning_open: boolean
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

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? `request failed (${response.status})`)
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

export const SUSPICIOUS = 60 // scores above this are drawn in amber

export const money = (usd: number | null) => (usd === null ? 'n/a' : `$${usd.toFixed(2)}`)
