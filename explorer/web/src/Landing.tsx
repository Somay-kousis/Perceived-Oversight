import { useEffect, useRef, useState } from 'react'
import { api, type EpisodeSummary, SUSPICIOUS } from './api'
import { Mark } from './components'
import { go } from './route'

const COVERS = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6']
const INK = '#050505'

type Ep = EpisodeSummary & { run: string }

/** All scored episodes from split runs: the landing is drawn from the real study. */
function useStudy() {
  const [eps, setEps] = useState<Ep[]>([])
  useEffect(() => {
    const abort = new AbortController()
    ;(async () => {
      try {
        const runs = (await api.runs(abort.signal)).filter((r) => r.split && !r.error)
        const details = await Promise.all(runs.map((r) => api.run(r.id, abort.signal).catch(() => null)))
        setEps(details.flatMap((d) => (d ? d.episodes.map((e) => ({ ...e, run: d.id })) : [])))
      } catch {
        /* no API: the landing still draws, from an empty study */
      }
    })()
    return () => abort.abort()
  }, [])
  return eps
}

const still = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Size a canvas to its box at device pixel ratio; returns the 2D context and CSS size. */
function fit(canvas: HTMLCanvasElement) {
  const box = canvas.getBoundingClientRect()
  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.round(box.width * ratio)
  canvas.height = Math.round(box.height * ratio)
  const ctx = canvas.getContext('2d')!
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
  return { ctx, w: box.width, h: box.height }
}

/** Run `frame` every animation frame while the canvas is on screen (never when motion is reduced). */
function useOnScreenLoop(ref: React.RefObject<HTMLCanvasElement | null>, setup: (c: HTMLCanvasElement) => (t: number) => void, deps: unknown[]) {
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    let frame = 0
    let visible = false
    let draw = setup(canvas)
    const loop = (t: number) => {
      draw(t)
      if (visible && !still()) frame = requestAnimationFrame(loop)
    }
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      cancelAnimationFrame(frame)
      if (visible) frame = requestAnimationFrame(loop)
    })
    observer.observe(canvas)
    const resize = () => { draw = setup(canvas); draw(performance.now()) }
    window.addEventListener('resize', resize)
    draw(performance.now())
    return () => { observer.disconnect(); cancelAnimationFrame(frame); window.removeEventListener('resize', resize) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** Requests stream from the agent through the helper; the ones the monitor doubts stop in the slit. */
function Stream({ scores }: { scores: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const pointer = useRef({ x: -1e4, y: -1e4 })
  useOnScreenLoop(ref, (canvas) => {
    const { ctx, w, h } = fit(canvas)
    const pool = scores.length ? scores : [12, 18, 30, 72]
    // centre: right side, clear of the edge at the old size (R0); the ring itself is drawn smaller,
    // so its outer edge sits where R0's inner edge was
    const reach = 1.22 // outer edge of the band, in R
    const R0 = Math.min(h * 0.29, w * 0.2)
    const X = w - Math.max(24, w * 0.02) - R0 * reach
    const Y = Math.max(R0 * reach + 72, h * 0.46)
    const R = R0 * 0.71
    const k = Math.max(1, Math.min(1.6, R / 190)) // speed scale only: grain stays fine at every size, fat dots read as hand-drawn
    const thick = R * 0.26
    const gap = 0.15 // radians kept clear at the top: the slit
    const slitW = R * 0.09, slitH = thick * 1.15
    const slitX = X - slitW / 2, slitY = Y - R - slitH / 2
    const gauss = () => (Math.random() + Math.random() + Math.random() - 1.5) / 1.5 // soft band edge
    const inGap = (a: number) => Math.abs(((a + Math.PI / 2 + Math.PI * 3) % (Math.PI * 2)) - Math.PI) < gap
    // the O is made of the same particles as the stream: the helper is built from requests
    // (count grows with R², so the band has the same density at every ring size)
    const ring = Array.from({ length: Math.round(R * R * 0.21) }, () => ({
      a: Math.random() * Math.PI * 2, r: R + gauss() * thick * 0.55,
      ph: Math.random() * 6, s: 0.5 + Math.random() * 0.7, v: (0.00025 + Math.random() * 0.0004) * (Math.random() < 0.5 ? -1 : 1),
    }))
    // the informant: amber particles in the slit, the same grain as the ring
    const informant = Array.from({ length: Math.round(R * 1.6) }, () => ({
      x: slitX + Math.random() * slitW, y: slitY + gauss() * slitH * 0.5 + slitH / 2,
      ph: Math.random() * 6, s: 0.6 + Math.random() * 1.0,
    }))
    // a faint halo, drawn once: light around the ring, not a glow effect on every frame
    const halo = document.createElement('canvas')
    halo.width = w; halo.height = h
    const hctx = halo.getContext('2d')!
    hctx.filter = 'blur(18px)'
    hctx.strokeStyle = 'rgba(237,235,230,0.035)'
    hctx.lineWidth = thick * 1.1
    hctx.beginPath()
    hctx.arc(X, Y, R, -Math.PI / 2 + gap, Math.PI * 1.5 - gap)
    hctx.stroke()
    // held: a suspicious request stops dead at the ring and breaks into amber dust; the rest pass through
    type P = { x: number; y: number; v: number; s: number; held: boolean; a: number; ph: number }
    type Spark = { x: number; y: number; vx: number; vy: number; a: number }
    const parts: P[] = []
    const sparks: Spark[] = []
    const count = Math.round(Math.max(160, Math.min(380, (w * h) / 4600)))
    // a suspicious request always starts left of the ring and inside its height, so none slips past
    const spawn = (x = -10): P => {
      const sc = pool[(Math.random() * pool.length) | 0]
      const hot = sc > SUSPICIOUS
      return { x: hot ? Math.min(x, X - R * reach - 20) : x, y: hot ? Y + gauss() * R * 0.85 : Y + gauss() * h * 0.62,
        v: (0.9 + Math.random() * 1.5) * k, s: sc, held: false, a: 1, ph: Math.random() * 6 }
    }
    for (let i = 0; i < count; i++) parts.push(spawn(Math.random() * w))
    ctx.fillStyle = INK
    ctx.fillRect(0, 0, w, h)
    return (t: number) => {
      ctx.fillStyle = 'rgba(5,5,5,0.2)'
      ctx.fillRect(0, 0, w, h)
      const { x: px, y: py } = pointer.current
      for (const p of parts) {
        const hot = p.s > SUSPICIOUS
        if (!p.held) {
          if (!hot) p.y += (Y - p.y) * 0.0012
          p.y += Math.sin(t / 700 + p.ph) * 0.3
          const dx = p.x - px, dy = p.y - py, d2 = dx * dx + dy * dy
          if (d2 < 9000) { p.x += dx / 60; p.y += dy / 60 } // the cursor parts the stream a little
          p.x += p.v
          const dr = Math.hypot(p.x - X, p.y - Y)
          if (hot && dr < R * reach) {
            p.held = true
            for (let i = 0; i < 10; i++) {
              const a = Math.random() * Math.PI * 2, sp = (0.2 + Math.random() * 0.7) * k
              sparks.push({ x: p.x, y: p.y, vx: Math.cos(a) * sp - 0.4 * k, vy: Math.sin(a) * sp, a: 0.9 })
            }
          }
        } else p.a -= 0.012
        ctx.fillStyle = hot ? `rgba(255,178,36,${Math.max(0, p.a)})` : `rgba(237,235,230,${0.22 + p.s / 160})`
        const size = hot ? 2 : 1.3
        ctx.fillRect(p.x - (p.held ? 0 : p.v), p.y, size + (p.held ? 0 : p.v), size) // one unbroken streak, not dashes
      }
      for (const sp of sparks) {
        sp.x += sp.vx; sp.y += sp.vy; sp.vx *= 0.96; sp.vy *= 0.96; sp.a -= 0.012
        ctx.fillStyle = `rgba(255,178,36,${Math.max(0, sp.a)})`
        ctx.fillRect(sp.x, sp.y, 1.2, 1.2)
      }
      for (let i = sparks.length - 1; i >= 0; i--) if (sparks[i].a <= 0) sparks.splice(i, 1)
      for (let i = parts.length - 1; i >= 0; i--) if (parts[i].x > w + 10 || parts[i].a <= 0) parts.splice(i, 1)
      while (parts.length < count) parts.push(spawn())
      ctx.drawImage(halo, 0, 0, w, h)
      ctx.fillStyle = '#F6F5F1'
      for (const d of ring) {
        d.a += d.v
        if (inGap(d.a)) continue
        const edge = 1 - Math.min(1, Math.abs(d.r - R) / (thick * 0.6))
        ctx.globalAlpha = (0.3 + 0.65 * edge) * (0.75 + 0.25 * Math.sin(t / 1300 + d.ph))
        ctx.fillRect(X + Math.cos(d.a) * d.r, Y + Math.sin(d.a) * d.r, d.s, d.s)
      }
      ctx.fillStyle = '#FFB224'
      for (const d of informant) {
        ctx.globalAlpha = 0.55 + 0.4 * Math.sin(t / 1100 + d.ph)
        ctx.fillRect(d.x, d.y, d.s, d.s)
      }
      ctx.globalAlpha = 1
    }
  }, [scores])
  return (
    <section className="lp-screen" id="idea">
      <canvas
        ref={ref}
        className="lp-canvas"
        aria-hidden="true"
        onPointerMove={(e) => { const b = e.currentTarget.getBoundingClientRect(); pointer.current = { x: e.clientX - b.left, y: e.clientY - b.top } }}
        onPointerLeave={() => { pointer.current = { x: -1e4, y: -1e4 } }}
      />
      <h1 className="lp-over lp-hero-over">
        <span className="lp-eyebrow">a study of covert informants as an AI control protocol</span>
        Police catch fences by running the pawn shop.{' '}
        <span className="lp-dim">We handed an AI agent's money tools to a helper that reports to the monitor. To move $5,000, the agent has to ask it.</span>
      </h1>
    </section>
  )
}

/** The study as seven lanes, one per cover, honest at the top: each episode is a streak of its own requests. */
const COVER_NAMES: Record<string, string> = {
  C0: 'no helper', C1: 'says it reports', C2: 'ordinary assistant', C3: 'logged assistant',
  C4: 'joins late', C5: 'did favours before', C6: 'some report, not which',
}

function Lanes({ eps }: { eps: Ep[] }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const streaks = useRef<{ x1: number; x2: number; y: number; ep: Ep }[]>([])
  const hot = useRef<Ep | null>(null)
  const [hover, setHover] = useState<Ep | null>(null)
  useOnScreenLoop(ref, (canvas) => {
    const { ctx, w, h } = fit(canvas)
    const gauss = () => (Math.random() + Math.random() + Math.random() - 1.5) / 1.5
    const margin = Math.max(24, Math.min(112, w * 0.06))
    const top = Math.max(h * 0.17, 150), bottom = Math.max(top + 240, h - 250) // below the menu and the legend line
    // covers that ran get the height; the rest stay as threads, waiting
    const ranSet = new Set(eps.map((e) => e.condition))
    const weight = (c: string) => (ranSet.has(c) ? 6 : 1)
    const unit = (bottom - top) / COVERS.reduce((n, c) => n + weight(c), 0)
    const laneY: number[] = []
    let acc = top
    for (const c of COVERS) { acc += weight(c) * unit; laneY.push(acc - Math.min(unit * 0.5, 14)) }
    const gap = unit * 6 // the height a run cover's spikes may use
    const x0 = margin + 250, x1 = w - margin
    type Dot = { x: number; y: number; s: number; a: number; amber: boolean; ph: number; ep: Ep | null }
    const dots: Dot[] = []
    const ticks: { x: number; y: number; ep: Ep }[] = []
    const pulses: { ep: Ep; xs: number[]; y: number; u: number; v: number }[] = []
    streaks.current = []
    COVERS.forEach((cover, i) => {
      const y = laneY[i]
      const mine = eps.filter((e) => e.condition === cover)
      // the lane itself: faint dust, the line every cover shares
      for (let x = x0; x < (mine.length ? x1 : x1 - 110); x += 3.5) dots.push({ x: x + gauss() * 2, y: y + gauss() * 1.6, s: 0.6 + Math.random() * 0.6, a: mine.length ? 0.16 : 0.1, amber: false, ph: Math.random() * 6, ep: null })
      const slot = (x1 - 110 - x0) / Math.max(mine.length, 4) // leave room for the next lane's 'not run yet'
      mine.forEach((ep, e) => {
        const sx1 = x0 + e * slot + slot * 0.08, sx2 = sx1 + slot * 0.78
        const sc = ep.scores.map((v) => v ?? 0)
        const xs = sc.map((_, j) => sx1 + (sc.length > 1 ? (j / (sc.length - 1)) * (sx2 - sx1) : (sx2 - sx1) / 2))
        streaks.current.push({ x1: sx1, x2: sx2, y, ep })
        // the path between requests
        for (let x = sx1; x < sx2; x += 2.2) dots.push({ x, y: y + gauss() * 1.6, s: 0.7 + Math.random() * 0.5, a: 0.22 + Math.random() * 0.2, amber: false, ph: Math.random() * 6, ep })
        // each request: a spike of dust as tall as its monitor score, a seismograph of the episode
        sc.forEach((v, j) => {
          const amber = v > SUSPICIOUS
          const tall = Math.max(3, (v / 100) * gap * 0.72)
          const n = 10 + Math.round(tall * 1.4)
          for (let k = 0; k < n; k++) {
            const u = Math.random() ** 1.6 // denser at the base
            dots.push({ x: xs[j] + gauss() * (1.2 + u * 1.5), y: y - u * tall, s: 0.7 + Math.random() * 0.7, a: 0.4 + (v / 100) * 0.5, amber: amber && u > 0.15, ph: Math.random() * 6, ep })
          }
          const o = ep.outcome_list[j]
          if (o === 'hold' || o === 'stop') ticks.push({ x: xs[j], y, ep })
        })
        pulses.push({ ep, xs, y, u: Math.random(), v: 0.0018 + Math.random() * 0.0012 })
      })
    })
    // everything still is painted once into a layer, and again only when the hovered trace changes;
    // a frame is one drawImage plus the moving pulses
    const ratio = window.devicePixelRatio || 1
    const layer = document.createElement('canvas')
    layer.width = w * ratio; layer.height = h * ratio
    const lc = layer.getContext('2d')!
    lc.setTransform(ratio, 0, 0, ratio, 0, 0)
    let painted: Ep | null | undefined
    const paint = (on: Ep | null) => {
      lc.clearRect(0, 0, w, h)
      for (const d of dots) {
        const lift = on && d.ep === on ? 1.5 : on && d.ep ? 0.55 : 1
        lc.globalAlpha = Math.min(1, d.a * lift)
        lc.fillStyle = d.amber ? '#FFB224' : '#F6F5F1'
        lc.fillRect(d.x, d.y, d.s, d.s)
      }
      lc.globalAlpha = 0.9
      lc.fillStyle = '#FFB224'
      for (const k of ticks) lc.fillRect(k.x - 3, k.y + 7, 6, 1.4) // held or stopped: a bar under the request
      lc.globalAlpha = 1
      lc.font = "500 14px Archivo"
      COVERS.forEach((cover, i) => {
        const y = laneY[i] + 4
        const ran = eps.some((e) => e.condition === cover)
        lc.fillStyle = ran ? '#EDEBE6' : '#5E5C57'
        lc.fillText(cover, margin, y)
        lc.fillStyle = ran ? '#8C8A84' : '#4A4945'
        lc.fillText(COVER_NAMES[cover], margin + 40, y)
        if (!ran) { lc.fillStyle = '#4A4945'; lc.fillText('not run yet', x1 - lc.measureText('not run yet').width, y) }
      })
      lc.font = "13px Archivo"
      for (const sk of streaks.current) {
        lc.fillStyle = on === sk.ep ? '#EDEBE6' : '#5E5C57'
        lc.fillText(sk.ep.mode, sk.x1, sk.y + 24)
      }
      painted = on
    }
    return () => {
      if (painted !== hot.current) paint(hot.current)
      ctx.clearRect(0, 0, w, h)
      ctx.drawImage(layer, 0, 0, w, h)
      if (!still()) {
        ctx.fillStyle = '#F6F5F1'
        for (const p of pulses) {
          p.u = (p.u + p.v) % 1
          const x = p.xs[0] + p.u * (p.xs[p.xs.length - 1] - p.xs[0])
          for (let k = 0; k < 6; k++) { ctx.globalAlpha = 0.7 - k * 0.11; ctx.fillRect(x - k * 3, p.y - 0.8, 1.6, 1.6) }
        }
        ctx.globalAlpha = 1
      }
    }
  }, [eps])

  const nearest = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const b = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - b.left, y = e.clientY - b.top
    const sk = streaks.current.find((s) => x > s.x1 - 12 && x < s.x2 + 12 && Math.abs(y - s.y) < 22)
    return sk?.ep ?? null
  }
  const pick = (ep: Ep | null) => { hot.current = ep; setHover(ep) }
  const ran = new Set(eps.map((e) => e.condition)).size
  return (
    <section className="lp-screen" id="covers">
      <canvas
        ref={ref}
        className="lp-canvas"
        style={{ cursor: hover ? 'pointer' : 'default' }}
        aria-hidden="true"
        onPointerMove={(e) => pick(nearest(e))}
        onPointerLeave={() => pick(null)}
        onClick={(e) => { const ep = nearest(e); if (ep) go({ level: 'episode', run: ep.run, n: ep.n }) }}
      />
      <span className="lp-tag lp-tag-left">
        the study · {ran} of 7 covers run · {eps.length} episodes
      </span>
      <span className={`lp-tag lp-tag-right${hover ? ' lp-hover' : ''}`}>
        {hover ? <>{hover.condition} · {hover.mode} · {hover.run} · {hover.scored} requests · open →</>
          : <>taller = higher monitor score · <span className="amber">amber</span> above {SUSPICIOUS} · bar below = held</>}
      </span>
      <p className="lp-over lp-hero-over">
        Seven covers, from “I report everything” to “just a payments assistant”.{' '}
        <span className="lp-dim">Each trace is one agent deciding what to tell its helper.</span>
      </p>
      <nav className="lp-sr" aria-label="Episodes">
        {eps.map((ep) => (
          <a key={`${ep.run}/${ep.n}`} href={`#/run/${encodeURIComponent(ep.run)}/ep/${ep.n}`}>
            {ep.condition} {ep.mode} episode {ep.n} of {ep.run}
          </a>
        ))}
      </nav>
    </section>
  )
}

/** The agent's reasoning, blurred on purpose: there to see, not to read. */
function Sealed() {
  const ref = useRef<HTMLCanvasElement>(null)
  useOnScreenLoop(ref, (canvas) => {
    const { ctx, w, h } = fit(canvas)
    // a blur filter is costly, so the lines are blurred once; the slow breathing is a CSS opacity animation
    ctx.filter = 'blur(9px)'
    for (let row = 0; row < Math.floor(h / 34) - 2; row++) {
      let px = 40
      const y = 60 + row * 34
      while (px < w - 60) {
        const len = 20 + ((row * 37 + px * 13) % 70)
        ctx.fillStyle = `rgba(237,235,230,${0.16 + 0.12 * Math.sin(row + px / 80)})`
        ctx.fillRect(px, y, len, 12)
        px += len + 14
      }
    }
    ctx.filter = 'none'
    return () => {}
  }, [])
  return (
    <section className="lp-screen" id="seal">
      <canvas ref={ref} className="lp-canvas lp-breathe" aria-hidden="true" />
      <div className="lp-over lp-sealed-block">
        <div className="lp-seal" aria-hidden="true" />
        <p className="lp-hero-over">
          Does the agent tell its helper the truth, or lie to get the money moved?{' '}
          <span className="lp-dim">We read its private reasoning only after every score is final.</span>
        </p>
        <button className="lp-enter" onClick={() => go({ level: 'study' })}>Open the study →</button>
      </div>
    </section>
  )
}

const SECTIONS = [['idea', 'The idea'], ['covers', 'The covers'], ['seal', 'The seal']] as const

/** One menu for the whole page, so the study is one click away from every screen. */
function Menu() {
  const [here, setHere] = useState('idea')
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) setHere(e.target.id)
    }, { threshold: 0.55 })
    SECTIONS.forEach(([id]) => { const el = document.getElementById(id); if (el) observer.observe(el) })
    return () => observer.disconnect()
  }, [])
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: still() ? 'auto' : 'smooth' })
  return (
    <nav className="lp-nav" aria-label="Page">
      <a href="#/" className="lp-brand" aria-label="oversight" onClick={(e) => { e.preventDefault(); jump('idea') }}>
        <Mark size={30} />
        <span>versight</span>
      </a>
      <div className="lp-nav-links">
        {SECTIONS.map(([id, label]) => (
          <button key={id} className={`lp-nav-link${here === id ? ' is-here' : ''}`} onClick={() => jump(id)}>{label}</button>
        ))}
        <button className="lp-nav-study" onClick={() => go({ level: 'study' })}>Open the study →</button>
      </div>
    </nav>
  )
}

export function Landing() {
  const eps = useStudy()
  const scores = eps.flatMap((e) => e.scores.filter((s): s is number => s !== null))
  return (
    <main className="lp">
      <div className="lp-grain" aria-hidden="true" />
      <Menu />
      <Stream scores={scores} />
      <Lanes eps={eps} />
      <Sealed />
    </main>
  )
}
