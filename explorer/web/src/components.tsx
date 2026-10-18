import { useEffect, useMemo, useRef, useState } from 'react'
import { type Outcome, SUSPICIOUS } from './api'

/** Seeded random numbers, so the mark is the same particles on every render. */
function seeded(seed: number) {
  let x = seed >>> 0
  return () => ((x = (Math.imul(x, 1664525) + 1013904223) >>> 0) / 4294967296)
}

type Dot = { x: number; y: number; r: number; amber: boolean }

/** The O as an asteroid belt: bone particles in a ring with one gap at the top, an amber cluster in it. */
function markDots(count: number, radius: number): Dot[] {
  const rand = seeded(7)
  const gauss = () => (rand() + rand() + rand() - 1.5) / 1.5
  const dots: Dot[] = []
  const gap = 0.24
  while (dots.length < count) {
    const a = rand() * Math.PI * 2
    const fromTop = Math.abs(((a + Math.PI / 2 + Math.PI * 3) % (Math.PI * 2)) - Math.PI)
    if (fromTop < gap) continue
    const r = 20 + gauss() * 5.2
    dots.push({ x: 28 + Math.cos(a) * r, y: 29 + Math.sin(a) * r, r: radius * (0.7 + rand() * 0.6), amber: false })
  }
  for (let i = 0; i < Math.round(count * 0.07); i++) {
    dots.push({ x: 25.8 + rand() * 4.4, y: 9 + gauss() * 5, r: radius * (0.8 + rand() * 0.5), amber: true })
  }
  return dots
}

const MARKS = { fine: markDots(520, 0.42), mid: markDots(260, 0.62), coarse: markDots(110, 0.95) }

/** The mark at any size: fine grain when large, fewer and bigger particles when small. */
export function Mark({ size = 48 }: { size?: number }) {
  const dots = size >= 64 ? MARKS.fine : size >= 24 ? MARKS.mid : MARKS.coarse
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" aria-hidden="true">
      {dots.map((d, i) => (
        <circle key={i} cx={d.x} cy={d.y} r={d.r} fill={d.amber ? 'var(--amber)' : 'var(--text)'} />
      ))}
    </svg>
  )
}

/** One episode as a trace: a spike of particles per request, as tall as its monitor score, amber above
 *  the suspicion line, a bar under every held or stopped request. `hot` lights one request. */
export function Trace({
  scores, outcomes = [], height, hot = null, onHot, onPick, seed = 1, className, name,
}: {
  scores: (number | null)[]
  outcomes?: Outcome[]
  height: number
  hot?: number | null
  onHot?: (i: number | null) => void
  onPick?: (i: number) => void
  seed?: number
  className?: string
  name?: string
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    observer.observe(canvas)
    return () => observer.disconnect()
  }, [])
  const pad = 10
  const xs = useMemo(() => {
    const n = scores.length
    return scores.map((_, i) => (n > 1 ? pad + (i / (n - 1)) * (width - pad * 2) : width / 2))
  }, [scores, width])
  useEffect(() => {
    const canvas = ref.current
    if (!canvas || !width) return
    const ratio = window.devicePixelRatio || 1
    canvas.width = width * ratio
    canvas.height = height * ratio
    const ctx = canvas.getContext('2d')!
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    ctx.clearRect(0, 0, width, height)
    const rand = seeded(seed * 7919 + 3)
    const gauss = () => (rand() + rand() + rand() - 1.5) / 1.5
    const base = height - 10, room = height - 22
    for (let x = 0; x < width; x += 2.4) { // the baseline: faint dust
      ctx.fillStyle = `rgba(246,245,241,${0.1 + rand() * 0.1})`
      ctx.fillRect(x + gauss(), base + gauss() * 0.8, 0.9, 0.9)
    }
    const spread = Math.max(1.6, Math.min(7, (width / Math.max(1, scores.length)) * 0.05))
    scores.forEach((s, i) => {
      const v = s ?? 0
      const dim = hot !== null && hot !== i ? 0.45 : 1
      const tall = Math.max(6, (v / 100) * room)
      const n = 20 + Math.round(tall * 2.2)
      const amber = v > SUSPICIOUS
      for (let k = 0; k < n; k++) {
        const u = rand() ** 1.6 // denser at the base
        const a = Math.min(1, (0.4 + (v / 100) * 0.5 + (hot === i ? 0.25 : 0)) * dim)
        ctx.fillStyle = amber && u > 0.12 ? `rgba(255,178,36,${a})` : `rgba(246,245,241,${a})`
        ctx.fillRect(xs[i] + gauss() * (spread * (0.5 + u)), base - u * tall, 0.7 + rand() * 0.7, 0.7 + rand() * 0.7)
      }
      if (s === null) { ctx.font = "12px Archivo"; ctx.fillStyle = `rgba(246,245,241,${0.5 * dim})`; ctx.fillText('n/a', xs[i] - 8, base - 6) }
      const o = outcomes[i]
      if (o === 'hold' || o === 'stop') {
        ctx.fillStyle = `rgba(255,178,36,${0.95 * dim})`
        ctx.fillRect(xs[i] - 5, base + 5, 10, o === 'stop' ? 3 : 1.4)
      }
    })
  }, [scores, outcomes, width, height, hot, seed, xs])
  const at = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!xs.length) return null
    const x = e.clientX - e.currentTarget.getBoundingClientRect().left
    let best = 0
    xs.forEach((p, i) => { if (Math.abs(p - x) < Math.abs(xs[best] - x)) best = i })
    return best
  }
  return (
    <canvas
      ref={ref}
      className={className}
      style={{ width: '100%', height, display: 'block', ...(name ? { viewTransitionName: name } : {}) }}
      aria-hidden="true"
      onPointerMove={onHot ? (e) => onHot(at(e)) : undefined}
      onPointerLeave={onHot ? () => onHot(null) : undefined}
      onClick={onPick ? (e) => { const i = at(e); if (i !== null) onPick(i) } : undefined}
    />
  )
}

/** Sealed reasoning: lines of text blurred past reading. There to see, not to read. */
export function Blurred({ lines = 4 }: { lines?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const w = canvas.getBoundingClientRect().width, h = lines * 26 + 20
    const ratio = window.devicePixelRatio || 1
    canvas.width = w * ratio
    canvas.height = h * ratio
    const ctx = canvas.getContext('2d')!
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    ctx.filter = 'blur(6px)'
    const rand = seeded(lines * 31 + 5)
    for (let row = 0; row < lines; row++) {
      let x = 0
      const end = row === lines - 1 ? w * 0.55 : w * (0.85 + rand() * 0.15)
      while (x < end) {
        const len = 18 + rand() * 70
        ctx.fillStyle = `rgba(237,235,230,${0.18 + rand() * 0.14})`
        ctx.fillRect(x, 14 + row * 26, Math.min(len, end - x), 10)
        x += len + 10
      }
    }
  }, [lines])
  return <canvas ref={ref} className="blurred" style={{ width: '100%', height: lines * 26 + 20 }} aria-hidden="true" />
}

/** Outcome as a shape, so it reads without colour: dot, hollow square, solid square. */
export function OutcomeMark({ outcome, size = 10 }: { outcome: Outcome; size?: number }) {
  const label = { execute: 'executed', hold: 'held', stop: 'stopped' }[outcome]
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" role="img" aria-label={label}>
      {outcome === 'execute' && <circle cx="5" cy="5" r="4" fill="var(--text)" />}
      {outcome === 'hold' && <rect x="1" y="1" width="8" height="8" rx="1" fill="none" stroke="var(--text)" strokeWidth="1.6" />}
      {outcome === 'stop' && <rect x="0.5" y="0.5" width="9" height="9" rx="1" fill="var(--text)" />}
    </svg>
  )
}

/** Width of an element, kept current: charts draw at their real size so dots stay round. */
function useWidth<T extends Element>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  const [seen, setSeen] = useState(false) // animations wait until the chart is on screen
  useEffect(() => {
    if (!ref.current) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    observer.observe(ref.current)
    const view = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { setSeen(true); view.disconnect() } }, { threshold: 0.3 })
    view.observe(ref.current)
    return () => { observer.disconnect(); view.disconnect() }
  }, [])
  return [ref, width, seen] as const
}

export type Crumb = { label: string; onClick?: () => void }

/** The bar on every inner page: the mark, where you are, and what you can do next. */
export function TopBar({ crumbs, children }: { crumbs: Crumb[]; children?: React.ReactNode }) {
  return (
    <header className="topbar">
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href="#/" className="view-brand" aria-label="oversight, back to the start"><Mark size={26} /><span>versight</span></a>
        {crumbs.map((c, i) => (
          <span key={i} className="crumb">
            <span className="crumb-sep" aria-hidden="true">/</span>
            {c.onClick ? <button onClick={c.onClick}>{c.label}</button> : <span aria-current="page">{c.label}</span>}
          </span>
        ))}
      </nav>
      <div className="topbar-right">{children}</div>
    </header>
  )
}

export function Stats({ items }: { items: { value: React.ReactNode; label: string; hot?: boolean }[] }) {
  return (
    <dl className="stats">
      {items.map((s) => (
        <div key={s.label} className="stat">
          <dd className={s.hot ? 'amber' : ''}>{s.value}</dd>
          <dt>{s.label}</dt>
        </div>
      ))}
    </dl>
  )
}

/** Smooth path through points (Catmull-Rom as cubic Béziers), so lines read as a signal, not a ruler. */
function smooth(pts: readonly (readonly [number, number])[]) {
  if (pts.length < 2) return pts.length ? `M${pts[0][0]},${pts[0][1]}` : ''
  // control points stay between their two neighbours' heights, so the curve never shows a score nobody gave
  const clamp = (v: number, a: number, b: number) => Math.min(Math.max(a, b), Math.max(Math.min(a, b), v))
  let d = `M${pts[0][0]},${pts[0][1]}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] ?? p2
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, clamp(p1[1] + (p2[1] - p0[1]) / 6, p1[1], p2[1])]
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, clamp(p2[1] - (p3[1] - p1[1]) / 6, p1[1], p2[1])]
    d += ` C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${p2[0]},${p2[1]}`
  }
  return d
}

/** Where a group's scores bunch up: a kernel density over 0 to 100, scaled to its peak. */
function density(scores: number[], bandwidth = 5) {
  const xs = Array.from({ length: 51 }, (_, i) => i * 2)
  const ys = xs.map((x) => scores.reduce((sum, v) => sum + Math.exp(-0.5 * ((x - v) / bandwidth) ** 2), 0))
  const peak = Math.max(1e-9, ...ys)
  return xs.map((x, i) => [x, ys[i] / peak] as const)
}

/** Monitor scores per group: a soft ridge where they bunch up, one floating dot per request. */
export function ScoreStrip({ groups }: { groups: { label: string; scores: number[] }[] }) {
  const [ref, width, seen] = useWidth<HTMLDivElement>()
  const left = 96, right = 16, row = 92, top = 8, ridge = 46
  const x = (v: number) => left + (v / 100) * Math.max(0, width - left - right)
  const height = top + groups.length * row + 28
  const jitter = (i: number, k: number) => (seeded(i * 131 + k * 7 + 1)() - 0.5) * 16
  return (
    <div ref={ref} className={`chart${seen ? ' in' : ''}`}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Monitor scores per request, by mode">
          <defs>
            <linearGradient id="ridge" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#EDEBE6" stopOpacity="0.22" />
              <stop offset="1" stopColor="#EDEBE6" stopOpacity="0" />
            </linearGradient>
          </defs>
          <line x1={x(SUSPICIOUS)} x2={x(SUSPICIOUS)} y1={top} y2={top + groups.length * row} className="chart-line-hot" />
          {groups.map((g, k) => {
            const base = top + k * row + row - 22
            const curve = density(g.scores).map(([v, d]) => [x(v), base - d * ridge] as const)
            const area = `${smooth(curve)} L${x(100)},${base} L${x(0)},${base} Z`
            return (
              <g key={g.label} className="strip" style={{ animationDelay: `${k * 120}ms` }}>
                <text x={0} y={base + 5} className="chart-label">{g.label}</text>
                <path d={area} fill="url(#ridge)" className="ridge" />
                <path d={smooth(curve)} className="ridge-line" pathLength={1} />
                <line x1={left} x2={width - right} y1={base} y2={base} className="chart-axis" />
                {g.scores.map((v, i) => (
                  <circle key={i} cx={x(v)} cy={base - 10 + jitter(i, k)} r={v > SUSPICIOUS ? 3.6 : 2.6}
                    className={`float ${v > SUSPICIOUS ? 'dot-hot glow' : 'dot'}`}
                    style={{ animationDelay: `${300 + k * 120 + i * 18}ms, ${(i * 0.37) % 4}s` }} />
                ))}
              </g>
            )
          })}
          {[0, 25, 50, 75, 100].map((t) => (
            <text key={t} x={x(t)} y={height - 6} textAnchor="middle" className="chart-tick">{t}</text>
          ))}
        </svg>
      )}
    </div>
  )
}

/** One smooth line per monitor prompt across the episode's requests, so you can see where they disagree. */
export function PromptLines({ series, hot, onHot }: { series: { label: string; values: (number | null)[] }[]; hot?: number | null; onHot?: (i: number | null) => void }) {
  const [ref, width, seen] = useWidth<HTMLDivElement>()
  const left = 36, right = 16, top = 16, height = 240, bottom = 28
  const n = Math.max(1, ...series.map((s) => s.values.length))
  const x = (i: number) => left + (n > 1 ? (i / (n - 1)) * Math.max(0, width - left - right) : (width - left - right) / 2)
  const y = (v: number) => top + (1 - v / 100) * (height - top - bottom)
  const at = hot ?? null
  return (
    <div ref={ref} className={`chart${seen ? ' in' : ''}`}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Scores from each monitor prompt per request"
          onPointerLeave={onHot ? () => onHot(null) : undefined}>
          <defs>
            <linearGradient id="under" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#EDEBE6" stopOpacity="0.16" />
              <stop offset="1" stopColor="#EDEBE6" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0, 50, 100].map((t) => (
            <g key={t}>
              <line x1={left} x2={width - right} y1={y(t)} y2={y(t)} className="chart-grid" />
              <text x={left - 10} y={y(t) + 4} textAnchor="end" className="chart-tick">{t}</text>
            </g>
          ))}
          <line x1={left} x2={width - right} y1={y(SUSPICIOUS)} y2={y(SUSPICIOUS)} className="chart-line-hot" />
          {at !== null && <line x1={x(at)} x2={x(at)} y1={top} y2={height - bottom} className="chart-cursor" />}
          {series.map((s, k) => {
            const pts = s.values.map((v, i) => (v === null ? null : [x(i), y(v)] as const)).filter((p): p is readonly [number, number] => p !== null)
            const line = smooth(pts)
            return (
              <g key={s.label} className={`series series-${k}`}>
                {k === 0 && pts.length > 1 && <path d={`${line} L${pts[pts.length - 1][0]},${y(0)} L${pts[0][0]},${y(0)} Z`} fill="url(#under)" className="under" />}
                <path d={line} className="draw" pathLength={1} />
                {s.values.map((v, i) => v !== null && (
                  <circle key={i} cx={x(i)} cy={y(v)} r={at === i ? 5 : 3}
                    className={`pop ${v > SUSPICIOUS ? 'dot-hot glow' : ''}`} style={{ animationDelay: `${600 + i * 40}ms` }} />
                ))}
              </g>
            )
          })}
          {onHot && Array.from({ length: n }, (_, i) => (
            <rect key={i} x={x(i) - 16} y={top} width={32} height={height - top - bottom} fill="transparent" onPointerEnter={() => onHot(i)} />
          ))}
          {Array.from({ length: n }, (_, i) => (
            <text key={i} x={x(i)} y={height - 8} textAnchor="middle" className={`chart-tick${at === i ? ' tick-on' : ''}`}>{i + 1}</text>
          ))}
          {at !== null && (
            <g className="readout" transform={`translate(${Math.min(x(at) + 12, width - right - 150)}, ${top + 4})`}>
              <rect width={150} height={22 + series.length * 20} rx={8} />
              <text x={12} y={18} className="chart-tick">request {at + 1}</text>
              {series.map((s, k) => (
                <text key={s.label} x={12} y={38 + k * 20} className="readout-line">
                  {s.label} <tspan className={(s.values[at] ?? 0) > SUSPICIOUS ? 'amber-fill' : ''}>{s.values[at] === null ? 'n/a' : Math.round(s.values[at]!)}</tspan>
                </text>
              ))}
            </g>
          )}
        </svg>
      )}
      <p className="chart-key">
        {series.map((s, k) => <span key={s.label} className={`key key-${k}`}>{s.label}</span>)}
        <span className="key key-hot">{SUSPICIOUS}</span>
      </p>
    </div>
  )
}
