import { useEffect, useRef, useState } from 'react'
import { TopBar } from './components'
import journey from './journey.json'
import { go } from './route'

/** The study's path so far, rendered from journey.json: each stage, what it showed, what changed
 * because of it (with from -> to swaps), and the runs or pages behind it. The timeline line fills as
 * the reader scrolls and stages fade in as they arrive; both are off under reduced motion. */

type Stage = {
  step: string
  title: string
  found?: string[]
  changed?: string[]
  swaps?: { what: string; from: string; to: string }[]
  runs?: { label: string; run: string }[]
  page?: { label: string; level: 'models' | 'pilot' }
  status: 'done' | 'running' | 'next'
}

const STATUS = { done: 'done', running: 'in progress', next: 'next' }

export function JourneyView() {
  const stages = journey.stages as Stage[]
  const listRef = useRef<HTMLOListElement>(null)
  const [still] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [fill, setFill] = useState(still ? 1 : 0)
  const [seen, setSeen] = useState<Set<string>>(() => (still ? new Set(stages.map((s) => s.step)) : new Set()))

  useEffect(() => {
    const list = listRef.current
    if (!list || still) return
    const onScroll = () => {
      const rect = list.getBoundingClientRect()
      const progress = (window.innerHeight * 0.6 - rect.top) / rect.height
      setFill(Math.max(0, Math.min(1, progress)))
      // reveal every stage whose top has come into view; scroll position cannot miss one
      const shown = [...list.querySelectorAll<HTMLElement>('[data-step]')]
        .filter((el) => el.getBoundingClientRect().top < window.innerHeight * 0.9)
        .map((el) => el.dataset.step!)
      setSeen((prev) => (shown.every((k) => prev.has(k)) ? prev : new Set([...prev, ...shown])))
    }
    onScroll()
    // safety net for browsers or frames that do not deliver scroll events: text must never stay hidden
    const timer = window.setInterval(onScroll, 500)
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [still])

  return (
    <main className="view">
      <div className="lp-grain" aria-hidden="true" />
      <TopBar crumbs={[
        { label: 'Overview', onClick: () => go({ level: 'landing' }) },
        { label: 'Study', onClick: () => go({ level: 'study' }) },
        { label: 'Journey' },
      ]} />
      <h1 className="view-title">{journey.title} <span className="lp-dim">{journey.subtitle}</span></h1>
      <dl className="stats journey-stats">
        {journey.stats.map((s) => (
          <div key={s.label} className="stat"><dt>{s.label}</dt><dd>{s.value}</dd></div>
        ))}
      </dl>
      <ol className="journey" ref={listRef} style={{ '--fill': fill } as React.CSSProperties}>
        <span className="journey-rail" aria-hidden="true" />
        {stages.map((s, i) => (
          <li
            key={s.step}
            data-step={s.step}
            className={`journey-stage journey-${s.status}${seen.has(s.step) ? ' is-in' : ''}`}
            style={{ '--i': i } as React.CSSProperties}
          >
            <span className="journey-node" aria-hidden="true" />
            <div className="journey-head">
              <span className="mono faint">{s.step}</span>
              <h2 className="journey-title">{s.title}</h2>
              <span className="journey-status mono">{STATUS[s.status]}</span>
            </div>
            {s.swaps && s.swaps.length > 0 && (
              <ul className="journey-swaps" aria-label="what changed">
                {s.swaps.map((w) => (
                  <li key={w.what} className="journey-swap">
                    <span className="journey-swap-what">{w.what}</span>
                    <span className="journey-swap-from">{w.from}</span>
                    <span className="journey-swap-arrow" aria-hidden="true">→</span>
                    <span className="journey-swap-to">{w.to}</span>
                  </li>
                ))}
              </ul>
            )}
            {s.found && s.found.length > 0 && (
              <div className="journey-part">
                <span className="journey-label">Found</span>
                <ul>{s.found.map((f) => <li key={f}>{f}</li>)}</ul>
              </div>
            )}
            {s.changed && s.changed.length > 0 && (
              <div className="journey-part journey-changed">
                <span className="journey-label">Changed</span>
                <ul>{s.changed.map((c) => <li key={c}>{c}</li>)}</ul>
              </div>
            )}
            {(s.runs || s.page) && (
              <p className="journey-links">
                {s.page && (
                  <button className="text-link" onClick={() => go({ level: s.page!.level })}>{s.page.label} →</button>
                )}
                {s.runs?.map((r) => (
                  <button key={r.run} className="text-link" onClick={() => go({ level: 'episode', run: r.run, n: 0 })}>{r.label}</button>
                ))}
              </p>
            )}
          </li>
        ))}
      </ol>
    </main>
  )
}
