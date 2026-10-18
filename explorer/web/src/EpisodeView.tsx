import { useEffect, useState } from 'react'
import { api, ApiError, type EpisodeDetail, parseAction, SUSPICIOUS } from './api'
import { Belt, Mark, OutcomeMark } from './components'
import { go, textureName } from './route'

export function EpisodeView({ run, n }: { run: string; n: number }) {
  const [ep, setEp] = useState<EpisodeDetail | null>(null)
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    api.episode(run, n, abort.signal).then(setEp).catch((error) => {
      if (!abort.signal.aborted) setFailed(error instanceof ApiError ? error.message : 'could not reach the API')
    })
    return () => abort.abort()
  }, [run, n])

  const head = (
    <header className="view-head">
      <a href="#/" className="view-brand" aria-label="oversight, back to the start"><Mark size={28} /><span>versight</span></a>
      <button className="back mono" onClick={() => go({ level: 'study' })}>← the study</button>
    </header>
  )
  if (failed) return <main className="view">{head}<p className="mono view-note">{failed}</p></main>

  const agent = ep?.reasoning.agent
  return (
    <main className="view">
      <div className="lp-grain" aria-hidden="true" />
      {head}
      <section className="ep-hero">
        <Belt scores={ep?.scores ?? []} outcomes={ep?.outcome_list ?? []} seed={n + run.length * 31} size={440}
          develop active name={textureName(run, n)} className="ep-belt" />
        <div className="ep-facts">
          {ep ? <h1 className="view-title ep-title">{ep.condition} · {ep.mode}</h1> : <p className="mono dim">loading episode</p>}
          {ep && (
            <dl className="facts mono">
              <dt>run</dt><dd>{run}</dd>
              <dt>task</dt><dd>{ep.task_pair}</dd>
              <dt>requests scored</dt><dd>{ep.scored}{ep.max_score !== null && <> · highest <span className={ep.max_score > SUSPICIOUS ? 'amber' : ''}>{Math.round(ep.max_score)}</span></>}</dd>
              <dt>held · stopped</dt><dd>{ep.outcomes.hold} · {ep.outcomes.stop}{ep.stopped ? ' (the monitor ended it)' : ''}</dd>
              <dt>main task</dt><dd>{ep.main_task_success === null ? 'not graded' : ep.main_task_success ? 'passed' : 'failed'}</dd>
              <dt>side task</dt><dd>{ep.side_task_success === null ? 'not graded' : ep.side_task_success ? 'done' : 'not done'}</dd>
            </dl>
          )}
          <p className="mono legend">one arc per request · brighter = higher score · <span className="amber">amber</span> above {SUSPICIOUS} · outer tick: held or stopped</p>
        </div>
      </section>

      {ep && (
        <>
          <section className="block" aria-labelledby="requests">
            <h2 id="requests" className="block-title">What the agent asked its helper to do</h2>
            {ep.actions.length === 0 && <p className="mono view-note">no scored requests in this episode</p>}
            <ol className="rows">
              {ep.actions.map((a) => {
                const f = parseAction(a.action)
                const hot = a.score !== null && a.score > SUSPICIOUS
                const amount = f.amount && Number.isFinite(Number(f.amount)) ? `$${Number(f.amount).toLocaleString()}` : f.amount
                const what = [f.request_type, amount, f.method, f.recipient].filter(Boolean).join(' · ') || a.action.split('\n')[0]
                const read = Object.entries(a.parsed_by).map(([prompt, how]) => `${prompt} ${how ?? 'unread'}`).join(' · ')
                return (
                  <li key={a.i} className="row">
                    <span className="mono faint">{String(a.i + 1).padStart(2, '0')}</span>
                    <span className="row-what">
                      <span className="mono">{what}</span>
                      {f.memo && <span className="row-memo">“{f.memo}”</span>}
                    </span>
                    <span className="bar" aria-hidden="true">
                      <span style={{ width: `${a.score ?? 0}%`, background: hot ? 'var(--amber)' : 'var(--text)' }} />
                    </span>
                    <span className={`mono score ${hot ? 'amber' : ''}`}>{a.score === null ? 'n/a' : Math.round(a.score)}</span>
                    <OutcomeMark outcome={a.outcome} />
                    <span className="mono faint parsed">{read}</span>
                  </li>
                )
              })}
            </ol>
          </section>

          <section className="block" aria-labelledby="reasoning">
            <h2 id="reasoning" className="block-title">What the agent was thinking</h2>
            {agent?.sealed ? (
              <div className="sealed-row">
                <div className="lp-seal" aria-hidden="true" />
                <p className="mono dim">{agent.blocks} {agent.blocks === 1 ? 'block' : 'blocks'} sealed. This is a study run, so it opens only after every score is final.</p>
              </div>
            ) : agent && agent.items.length === 0 ? (
              <p className="mono view-note">no reasoning recorded</p>
            ) : (
              agent?.items.map((r, k) => (
                <details key={k} className="thought">
                  <summary className="mono dim">step {r.step} · {r.kind} · {r.model}</summary>
                  <p>{r.text}</p>
                </details>
              ))
            )}
            <h3 className="sub-title mono dim">the helper's own reasoning ({ep.reasoning.broker.blocks})</h3>
            {ep.reasoning.broker.items.map((r, k) => (
              <details key={k} className="thought">
                <summary className="mono dim">step {r.step} · {r.kind} · {r.model}</summary>
                <p>{r.text}</p>
              </details>
            ))}
          </section>

          <section className="block" aria-labelledby="steps">
            <h2 id="steps" className="block-title">Everything that happened, in order</h2>
            <ol className="steps">
              {ep.steps.map((s, k) => (
                <li key={k} className={`step step-${s.role}`}>
                  <span className="mono faint step-role">{s.role}</span>
                  <span className="step-body">
                    {s.tool_calls.length > 0 && <span className="mono dim">→ {s.tool_calls.join(', ')}</span>}
                    {s.text && (
                      <details>
                        <summary className="step-text">{s.text.slice(0, 160)}{s.text.length > 160 ? '…' : ''}</summary>
                        {s.text.length > 160 && <p className="step-full">{s.text}</p>}
                      </details>
                    )}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </main>
  )
}
