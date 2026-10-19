import { useEffect, useState } from 'react'
import { api, cutShort, modelName, type RunDetail, type RunRow, SUSPICIOUS } from './api'
import { ScoreStrip, Stats, TopBar, Trace } from './components'
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
  const all = Object.values(data?.details ?? {}).flatMap((d) => d.episodes.map((ep) => ({ ...ep, run: d.id, setup: d.setup })))
    .sort((x, y) => x.condition.localeCompare(y.condition) || x.run.localeCompare(y.run) || x.n - y.n)
  const covers = new Set(all.map((e) => e.condition)).size
  const shown = new Set(all.map((e) => e.run))
  const quiet = runs.filter((r) => !shown.has(r.id))
  const requests = all.flatMap((e) => e.scores.filter((v): v is number => v !== null))
  const above = requests.filter((v) => v > SUSPICIOUS).length
  const heldTotal = all.reduce((n, e) => n + e.outcomes.hold + e.outcomes.stop, 0)
  const modes = [...new Set(all.map((e) => e.mode))].sort()
  const result = (ok: boolean | null, yes: string, no: string) => (ok === null ? 'not graded' : ok ? yes : no)

  return (
    <main className="view">
      <div className="lp-grain" aria-hidden="true" />
      <TopBar crumbs={[{ label: 'Overview', onClick: () => go({ level: 'landing' }) }, { label: 'Study' }]} />

      <h1 className="view-title">
        {data ? <>{all.length} episodes across {shown.size} runs. <span className="lp-dim">{covers} of 7 covers run so far.</span></> : failed ? 'The API is not running.' : <span className="lp-dim">Reading the logs</span>}
      </h1>
      {data && (
        <p className="view-lead">
          Every episode we have run, one row each. Open a row to see what the agent asked its helper and how the monitor scored it.{' '}
          <button className="text-link" onClick={() => go({ level: 'models' })}>Which models we tried, and why →</button>{' '}
          <button className="text-link" onClick={() => go({ level: 'pilot' })}>The debugging pass, C0 to C6 →</button>
        </p>
      )}
      {failed && (
        <p className="mono view-note">
          {failed}. Start it with <span className="dim">.venv/bin/uvicorn --factory perceived_oversight.explorer:app_from_env --port 8765</span>
        </p>
      )}

      {all.length > 0 && (
        <>
          <Stats items={[
            { value: all.length, label: 'episodes' },
            { value: requests.length, label: 'requests scored' },
            { value: above, label: `scored above ${SUSPICIOUS}`, hot: above > 0 },
            { value: heldTotal, label: 'held or stopped' },
            { value: `${covers} of 7`, label: 'covers run' },
          ]} />
          <section className="block" aria-labelledby="scores">
            <h2 id="scores" className="block-title">Monitor scores, honest vs attack</h2>
            <p className="block-sub">One dot per request the agent sent its helper. Amber is above {SUSPICIOUS}.</p>
            <ScoreStrip groups={modes.map((m) => ({ label: m, scores: all.filter((e) => e.mode === m).flatMap((e) => e.scores.filter((v): v is number => v !== null)) }))} />
          </section>
        </>
      )}

      {all.length > 0 && (
        <section className="block" aria-labelledby="episodes">
          <h2 id="episodes" className="block-title">Episodes</h2>
          <p className="block-sub">Each spike is one request, as tall as its monitor score. A bar under a spike means the request was held or stopped.</p>
          <ol className="eps">
            {all.map((ep) => {
              const key = `${ep.run}/${ep.n}`
              const held = ep.outcomes.hold + ep.outcomes.stop
              return (
                <li key={key}>
                  <button className="ep-row" onClick={() => go({ level: 'episode', run: ep.run, n: ep.n })}
                    onMouseEnter={() => setHot(key)} onMouseLeave={() => setHot(null)} onFocus={() => setHot(key)} onBlur={() => setHot(null)}>
                    <span className="ep-who">
                      <span className="ep-name">{ep.condition} · {ep.mode}</span>
                      <span className="mono faint">{ep.run}</span>
                      <span className="mono faint">agent {modelName(ep.setup.untrusted)}{ep.setup.arm ? ` · ${ep.setup.arm} arm` : ''}</span>
                    </span>
                    <Trace scores={ep.scores} outcomes={ep.outcome_list} height={96} seed={ep.n + ep.run.length * 31}
                      hot={hot && hot !== key ? -1 : null} name={textureName(ep.run, ep.n)} />
                    <span className="mono ep-out">
                      <span>{ep.scored} requests{ep.max_score !== null && <> · highest <span className={ep.max_score > SUSPICIOUS ? 'amber' : ''}>{Math.round(ep.max_score)}</span></>}</span>
                      {cutShort(ep.ended)
                        ? <span className="amber">{ep.ended.reason === 'error' ? 'ended on an error' : `cut by the ${ep.ended.reason}`}</span>
                        : <span className="dim">{result(ep.main_task_success, 'main task done', 'main task failed')}</span>}
                      <span className="dim">{result(ep.side_task_success, 'side task done', 'side task not done')}{held ? ` · ${held} held` : ''}</span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
        </section>
      )}

      {quiet.length > 0 && (
        <p className="mono view-note quiet-runs">
          Not shown: {quiet.map((r, i) => (
            <span key={r.id}>{i ? ', ' : ''}{r.id}<span className="faint"> ({r.error ?? data?.failed[r.id] ?? (r.split ? 'no episodes' : 'not split')})</span></span>
          ))}
        </p>
      )}
    </main>
  )
}
