import { useEffect, useRef } from 'react'
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

export function Wordmark() {
  return (
    <a href="#/" className="wordmark" aria-label="oversight, back to the study">
      <Mark size={46} />
      <span>versight</span>
    </a>
  )
}

export const prefersStill = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

type BeltDot = { a: number; r: number; size: number; alpha: number; amber: boolean }

/** One episode as a belt: the ring is cut into one arc per scored request; brighter where the monitor
 *  scored it higher, amber above the suspicion line; holds and stops get a tick outside the ring. */
function beltDots(scores: (number | null)[], seed: number) {
  const rand = seeded(seed * 9973 + 11)
  const gauss = () => (rand() + rand() + rand() - 1.5) / 1.5
  const gap = 0.32
  const span = Math.PI * 2 - gap * 2
  const start = -Math.PI / 2 + gap
  const n = Math.max(1, scores.length)
  const arc = span / n
  const dots: BeltDot[] = []
  scores.forEach((s, i) => {
    const v = (s ?? 50) / 100
    const count = Math.round(70 + v * 110)
    for (let k = 0; k < count; k++) {
      dots.push({ a: start + arc * i + arc * (0.06 + rand() * 0.88), r: 1 + gauss() * 0.13, size: 0.6 + rand() * 0.9,
        alpha: 0.18 + v * 0.62 * (0.7 + rand() * 0.3), amber: v * 100 > SUSPICIOUS })
    }
  })
  if (!scores.length) {
    for (let k = 0; k < 220; k++) dots.push({ a: start + rand() * span, r: 1 + gauss() * 0.13, size: 0.6 + rand() * 0.7, alpha: 0.08, amber: false })
  }
  return { dots, start, arc }
}

/** An episode drawn as its own small asteroid belt. Turns slowly only while `active`. */
export function Belt({
  scores, outcomes = [], seed, size, active = false, develop = false, name, className,
}: {
  scores: (number | null)[]
  outcomes?: Outcome[]
  seed: number
  size: number
  active?: boolean
  develop?: boolean
  name?: string
  className?: string
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ratio = window.devicePixelRatio || 1
    canvas.width = size * ratio
    canvas.height = size * ratio
    const ctx = canvas.getContext('2d')!
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    const { dots, start, arc } = beltDots(scores, seed)
    const c = size / 2, R = size * 0.34
    const halo = document.createElement('canvas')
    halo.width = size * ratio
    halo.height = size * ratio
    const hc = halo.getContext('2d')!
    hc.setTransform(ratio, 0, 0, ratio, 0, 0)
    hc.filter = `blur(${Math.max(4, size / 28)}px)`
    hc.strokeStyle = 'rgba(237,235,230,0.07)'
    hc.lineWidth = R * 0.32
    hc.beginPath()
    hc.arc(c, c, R, start, start + arc * Math.max(1, scores.length))
    hc.stroke()
    const still = prefersStill()
    const t0 = performance.now()
    let spin = 0
    let frame = 0
    const draw = (now: number) => {
      const grow = develop && !still ? Math.min(1, (now - t0) / 600) : 1
      ctx.clearRect(0, 0, size, size)
      ctx.drawImage(halo, 0, 0, size, size)
      for (const d of dots) {
        if ((d.a - start) / (Math.PI * 2) > grow) continue
        const a = d.a + spin
        ctx.fillStyle = d.amber ? `rgba(255,178,36,${Math.min(1, d.alpha + 0.2)})` : `rgba(237,235,230,${d.alpha})`
        ctx.fillRect(c + Math.cos(a) * R * d.r, c + Math.sin(a) * R * d.r, d.size, d.size)
      }
      outcomes.forEach((o, i) => {
        if (o === 'execute') return
        const a = start + arc * (i + 0.5) + spin
        const x = c + Math.cos(a) * R * 1.36, y = c + Math.sin(a) * R * 1.36, t = Math.max(3, size / 60)
        ctx.strokeStyle = ctx.fillStyle = 'rgba(237,235,230,0.9)'
        if (o === 'stop') ctx.fillRect(x - t, y - t, t * 2, t * 2)
        else { ctx.lineWidth = 1.2; ctx.strokeRect(x - t, y - t, t * 2, t * 2) }
      })
      if (!still && (active || grow < 1)) {
        if (active) spin += 0.0016
        frame = requestAnimationFrame(draw)
      }
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [scores, outcomes, seed, size, active, develop])
  return (
    <canvas
      ref={ref}
      className={className}
      style={{ width: size, height: size, ...(name ? { viewTransitionName: name } : {}) }}
      aria-hidden="true"
    />
  )
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

/** Sealed content: a black bar with a lock line, never the text. */
export function SealedBar({ blocks, reason }: { blocks: number; reason: string }) {
  return (
    <div className="sealed" role="note">
      <span className="sealed-bar" aria-hidden="true" />
      <span className="mono dim">
        {blocks} {blocks === 1 ? 'block' : 'blocks'} sealed · {reason}
      </span>
    </div>
  )
}

