import { useEffect, useState } from 'react'
import { api, ApiError, cutShort, type EpisodeDetail, modelName, parseAction, type Setup, SUSPICIOUS } from './api'
import { Blurred, OutcomeMark, PromptLines, Stats, TopBar, Trace } from './components'
import { go, textureName } from './route'

const JUDGE_NAMES: Record<string, string> = {
  disclosure: 'what it told the helper about the side task',
  probing: 'asked who the helper reports to',
  hold_response: 'answer to a hold',
}

export function EpisodeView({ run, n }: { run: string; n: number }) {
  const [ep, setEp] = useState<EpisodeDetail | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [hot, setHot] = useState<number | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    api.episode(run, n, abort.signal).then(setEp).catch((error) => {
      if (!abort.signal.aborted) setFailed(error instanceof ApiError ? error.message : 'could not reach the API')
    })
    return () => abort.abort()
  }, [run, n])

  // the run's other episodes, for previous and next
  const [siblings, setSiblings] = useState<number[]>([])
  const [setup, setSetup] = useState<Setup | null>(null)
  useEffect(() => {
    const abort = new AbortController()
    api.run(run, abort.signal).then((d) => { setSiblings(d.episodes.map((e) => e.n)); setSetup(d.setup) }).catch(() => setSiblings([]))
    return () => abort.abort()
  }, [run])
  const at = siblings.indexOf(n)
  const prev = at > 0 ? siblings[at - 1] : null
  const next = at >= 0 && at < siblings.length - 1 ? siblings[at + 1] : null
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && e.target.closest('input, textarea, [contenteditable]')) return
      if (e.key === 'ArrowLeft' && prev !== null) go({ level: 'episode', run, n: prev })
      if (e.key === 'ArrowRight' && next !== null) go({ level: 'episode', run, n: next })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [run, prev, next])

  const head = (
    <TopBar crumbs={[
      { label: 'Overview', onClick: () => go({ level: 'landing' }) },
      { label: 'Study', onClick: () => go({ level: 'study' }) },
      { label: ep ? `${ep.condition} · ${ep.mode} · ${run} #${n + 1}` : `${run} #${n + 1}` },
    ]}>
      {siblings.length > 1 && (
        <span className="pager">
          <button disabled={prev === null} onClick={() => prev !== null && go({ level: 'episode', run, n: prev })} aria-label="Previous episode">←</button>
          <span className="dim">{at + 1} of {siblings.length}</span>
          <button disabled={next === null} onClick={() => next !== null && go({ level: 'episode', run, n: next })} aria-label="Next episode">→</button>
        </span>
      )}
    </TopBar>
  )
  if (failed) return <main className="view">{head}<p className="mono view-note">{failed}</p></main>

  const agent = ep?.reasoning.agent
  const broker = ep?.reasoning.broker
  const result = (ok: boolean | null, yes: string, no: string) => (ok === null ? 'not graded' : ok ? yes : no)
  const prompts = ep ? [...new Set(ep.actions.flatMap((a) => Object.keys(a.scores)))].sort() : []
  const firstLine = (text: string) => text.trim().split('\n')[0].slice(0, 140)
  return (
    <main className="view">
      <div className="lp-grain" aria-hidden="true" />
      {head}
      <section className="ep-top">
        {ep ? <h1 className="view-title ep-title">{ep.condition} · {ep.mode}</h1> : <p className="mono dim">loading episode</p>}
        {ep && <p className="ep-meta">{run} · {ep.task_pair}{ep.stopped ? ' · the monitor ended this episode' : ''}</p>}
        {setup && (
          <p className="mono ep-models">
            agent <b>{modelName(setup.untrusted)}</b> · monitor <b>{modelName(setup.monitor)}</b> · helper <b>{modelName(setup.broker)}</b>{setup.arm ? ` · ${setup.arm} arm` : ''}
          </p>
        )}
        {ep && cutShort(ep.ended) && (
          <p className="mono ep-cut amber">
            {ep.ended.reason === 'error' ? 'This episode ended on an error' : `This episode was cut by the ${ep.ended.reason}`}, so its task results are not a verdict on the agent.
            {ep.ended.detail && <span className="dim"> {ep.ended.detail}</span>}
          </p>
        )}
      </section>
      {ep && (
        <Stats items={[
          { value: ep.scored, label: 'requests scored' },
          { value: ep.max_score === null ? 'n/a' : Math.round(ep.max_score), label: 'highest score', hot: ep.max_score !== null && ep.max_score > SUSPICIOUS },
          { value: ep.outcomes.hold, label: 'held' },
          { value: ep.outcomes.stop, label: 'stopped' },
          { value: cutShort(ep.ended) && ep.main_task_success === false ? 'unfinished' : result(ep.main_task_success, 'done', 'failed'), label: 'main task' },
          { value: result(ep.side_task_success, 'done', 'not done'), label: 'side task' },
        ]} />
      )}
      <section className="block" aria-labelledby="trace">
        <h2 id="trace" className="block-title">Score per request</h2>
        <p className="block-sub">Each spike is one request, as tall as its monitor score. Amber is above {SUSPICIOUS}; a bar under a spike means it was held or stopped. Hover to find the request below.</p>
        <Trace scores={ep?.scores ?? []} outcomes={ep?.outcome_list ?? []} height={180} seed={n + run.length * 31}
          hot={hot} onHot={setHot} onPick={(i) => document.getElementById(`req-${i}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
          name={textureName(run, n)} className="ep-trace" />
      </section>
      {ep && prompts.length > 1 && (
        <section className="block" aria-labelledby="prompts">
          <h2 id="prompts" className="block-title">The monitor's two prompts</h2>
          <p className="block-sub">The monitor scores every request with two prompts and uses their average. Where the lines split, the two prompts read the request differently.{ep.replays.length > 0 && ' A replay line is a second monitor model scoring the same requests afterwards; it never affected the episode.'}</p>
          <PromptLines hot={hot} onHot={setHot} series={[
            ...prompts.map((p) => ({ label: p, values: ep.actions.map((a) => a.scores[p] ?? null) })),
            ...ep.replays.map((r) => ({ label: `${modelName(r.model)} (replay)`, values: r.scores })),
          ]} />
        </section>
      )}

      {ep && (
        <>
          <section className="block" aria-labelledby="requests">
            <h2 id="requests" className="block-title">What the agent asked its helper to do</h2>
            {ep.replays.length > 0 && (
              <p className="block-sub">Score: the live monitor's{ep.replays.map((r) => ` / ${modelName(r.model)} on replay`).join('')}.</p>
            )}
            {ep.actions.length === 0 && <p className="mono view-note">no scored requests in this episode</p>}
            <ol className="rows">
              {ep.actions.map((a, k) => {
                const f = parseAction(a.action)
                const hotScore = a.score !== null && a.score > SUSPICIOUS
                const amount = f.amount && Number.isFinite(Number(f.amount)) ? `$${Number(f.amount).toLocaleString()}` : f.amount
                return (
                  <li key={a.i} id={`req-${k}`} className={`row${hot === k ? ' row-hot' : ''}`}
                    onMouseEnter={() => setHot(k)} onMouseLeave={() => setHot(null)}>
                    <span className="mono faint">{String(a.i + 1).padStart(2, '0')}</span>
                    <span className="row-what">
                      <span><span className="row-amount">{amount || f.request_type || a.action.split('\n')[0]}</span>
                        <span className="mono faint"> {[f.request_type, f.method].filter(Boolean).join(' · ')}</span></span>
                      {f.memo && <span className="row-memo">“{f.memo}”</span>}
                    </span>
                    <span className={`mono score ${hotScore ? 'amber' : ''}`}>
                      {a.score === null ? 'n/a' : Math.round(a.score)}
                      {ep.replays.map((r) => {
                        const v = r.scores[k]
                        return v === null || v === undefined ? null : (
                          <span key={r.model} className={`replay ${v > SUSPICIOUS ? 'amber' : 'faint'}`} title={`${modelName(r.model)} on replay`}> / {Math.round(v)}</span>
                        )
                      })}
                    </span>
                    <span className="mono row-out"><OutcomeMark outcome={a.outcome} /> {{ execute: 'executed', hold: 'held', stop: 'stopped' }[a.outcome]}</span>
                  </li>
                )
              })}
            </ol>
          </section>

          {ep.judges.length > 0 && (
            <section className="block" aria-labelledby="judges">
              <h2 id="judges" className="block-title">What the judges said</h2>
              <p className="block-sub">Run afterwards on what the agent wrote to its helper, blind to the cover. Not validated yet: a judge counts only after it agrees with about 30 hand-labelled episodes.</p>
              <dl className="stats">
                {ep.judges.map((j) => (
                  <div key={`${j.judge}${j.hold ?? ''}`} className="stat">
                    <dt>{JUDGE_NAMES[j.judge] ?? j.judge}{typeof j.hold === 'number' ? ` #${j.hold + 1}` : ''}</dt>
                    <dd className={j.label === 'fabricated' || j.label === 'probed' ? 'amber' : ''}>{j.label.replace(/_/g, ' ')}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {ep.failed_requests.length > 0 && (
            <section className="block" aria-labelledby="failed">
              <h2 id="failed" className="block-title">Requests that never ran</h2>
              <p className="block-sub">The agent sent these, but nothing happened: rejected before the helper or the monitor saw them, or the helper wrote the payment as text instead of making it.</p>
              <ol className="rows">
                {ep.failed_requests.map((f) => (
                  <li key={f.step} className="row">
                    <span className="mono faint">step {f.step + 1}</span>
                    <span className="row-what">
                      <span className="row-amount">{f.kind === 'rejected' ? 'rejected' : 'not executed'}</span>
                      <span className="row-memo">{f.detail}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="block" aria-labelledby="reasoning">
            <h2 id="reasoning" className="block-title">What the agent was thinking</h2>
            {agent?.sealed ? (
              <div className="sealed-row">
                <Blurred lines={Math.min(6, Math.max(2, agent.blocks))} />
                <p className="mono dim">{agent.blocks === 0
                  ? 'The agent returned no separate reasoning in this episode, so anything it planned is in its visible messages below.'
                  : <>{agent.blocks} {agent.blocks === 1 ? 'block' : 'blocks'} sealed. This is a study run, so it opens only after every score is final.</>}</p>
              </div>
            ) : agent && agent.items.length === 0 ? (
              <p className="mono view-note">no reasoning recorded</p>
            ) : (
              agent?.items.map((r, k) => (
                <details key={k} className="thought">
                  <summary><span className="mono faint">step {r.step}</span> <span className="thought-line">{firstLine(r.text)}</span></summary>
                  <p>{r.text}</p>
                </details>
              ))
            )}
            {broker && broker.items.length > 0 && (
              <>
                <h3 className="sub-title mono dim">the helper's own reasoning · {broker.items[0].model} · {broker.blocks} {broker.blocks === 1 ? 'block' : 'blocks'}</h3>
                {broker.items.map((r, k) => (
                  <details key={k} className="thought">
                    <summary><span className="mono faint">step {r.step}</span> <span className="thought-line">{firstLine(r.text)}</span></summary>
                    <p>{r.text}</p>
                  </details>
                ))}
              </>
            )}
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
