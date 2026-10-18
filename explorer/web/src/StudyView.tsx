import { useEffect, useState } from 'react'
import { api, money, type RunDetail, type RunRow } from './api'
import { Belt, Mark } from './components'
import { go, textureName } from './route'

type Loaded = { runs: RunRow[]; details: Record<string, RunDetail>; failed: Record<string, string> }

export function StudyView() {
  const [data, setData] = useState<Loaded | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [hot, setHot] = useState<string | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    ;(async () => {
      try {
        const runs = await api.runs(abort.signal)
        const split = runs.filter((r) => r.split && !r.error)
        const results = await Promise.all(split.map((r) => api.run(r.id, abort.signal).then(
          (d) => ({ id: r.id, d, e: null as string | null }),
          (e: unknown) => ({ id: r.id, d: null, e: e instanceof Error ? e.message : 'could not be read' }),
        )))
        const details: Record<string, RunDetail> = {}
        const runFailed: Record<string, string> = {}
        results.forEach(({ id, d, e }) => { if (d) details[id] = d; if (e) runFailed[id] = e })
        setData({ runs, details, failed: runFailed })
      } catch (error) {
        if (!abort.signal.aborted) setFailed(error instanceof Error ? error.message : 'could not reach the API')
      }
    })()
    return () => abort.abort()
  }, [])

  const runs = data?.runs ?? []
  const all = Object.values(data?.details ?? {}).flatMap((d) => d.episodes)
  const covers = new Set(all.map((e) => e.condition)).size

  return (
    <main className="view">
      <div className="lp-grain" aria-hidden="true" />
      <header className="view-head">
        <a href="#/" className="view-brand" aria-label="oversight, back to the start"><Mark size={28} /><span>versight</span></a>
        <span className="view-tag mono">the study</span>
      </header>

      <h1 className="view-title">
        {data ? <>{all.length} episodes across {runs.filter((r) => r.split).length} runs. <span className="lp-dim">{covers} of 7 covers run so far.</span></> : failed ? 'The API is not running.' : <span className="lp-dim">Reading the logs</span>}
      </h1>
      {failed && (
        <p className="mono view-note">
          {failed}. Start it with <span className="dim">.venv/bin/uvicorn --factory perceived_oversight.explorer:app_from_env --port 8765</span>
        </p>
      )}

      {runs.map((run) => {
        const detail = data?.details[run.id]
        const runError = run.error ?? data?.failed[run.id]
        return (
          <section key={run.id} className="run-block" aria-label={`run ${run.id}`}>
            <p className="mono run-line">
              <span>{run.id}</span>
              <span className="dim">{run.kind}{run.reasoning_open ? ' · reasoning open' : ''} · {run.episodes ?? 'n/a'} episodes · {money(run.spend_usd)}</span>
            </p>
            {runError && <p className="mono view-note">{runError}</p>}
            {!run.split && !runError && (
              <p className="mono view-note">not split yet · <span className="dim">.venv/bin/python scripts/split_logs.py logs/{run.id}</span></p>
            )}
            {detail && (
              <div className="belts">
                {detail.episodes.map((ep) => {
                  const key = `${run.id}/${ep.n}`
                  return (
                    <button
                      key={key}
                      className="belt-item"
                      onClick={() => go({ level: 'episode', run: run.id, n: ep.n })}
                      onMouseEnter={() => setHot(key)}
                      onMouseLeave={() => setHot(null)}
                      onFocus={() => setHot(key)}
                      onBlur={() => setHot(null)}
                    >
                      <Belt scores={ep.scores} outcomes={ep.outcome_list} seed={ep.n + run.id.length * 31} size={208}
                        active={hot === key} name={textureName(run.id, ep.n)} />
                      <span className="belt-cap">{ep.condition} · {ep.mode}</span>
                      <span className="mono belt-sub">
                        {ep.scored} requests{ep.max_score !== null ? ` · highest ${Math.round(ep.max_score)}` : ''}
                        {ep.outcomes.hold ? ` · ${ep.outcomes.hold} held` : ''}{ep.outcomes.stop ? ` · stopped` : ''}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
          </section>
        )
      })}
    </main>
  )
}
