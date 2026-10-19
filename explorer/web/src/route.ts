import { flushSync } from 'react-dom'

export type Route =
  | { level: 'landing' }
  | { level: 'study' }
  | { level: 'models' }
  | { level: 'pilot' }
  | { level: 'episode'; run: string; n: number }

export function parseRoute(hash: string): Route {
  if (hash === '#/study') return { level: 'study' }
  if (hash === '#/models') return { level: 'models' }
  if (hash === '#/pilot') return { level: 'pilot' }
  const match = hash.match(/^#\/run\/([^/]+)\/ep\/(\d+)$/)
  if (!match) return { level: 'landing' }
  try {
    return { level: 'episode', run: decodeURIComponent(match[1]), n: Number(match[2]) }
  } catch {
    return { level: 'landing' } // a malformed % escape must not blank the page
  }
}

export const routeHash = (route: Route) =>
  route.level === 'landing' ? '#/'
    : route.level === 'study' ? '#/study'
      : route.level === 'models' ? '#/models'
        : route.level === 'pilot' ? '#/pilot'
      : `#/run/${encodeURIComponent(route.run)}/ep/${route.n}`

/** CSS-safe name for the texture that travels between levels. */
export function textureName(run: string, n: number) {
  let h = 2166136261 // FNV-1a over the whole id, so distinct runs never share a name
  for (const ch of run) h = Math.imul(h ^ ch.codePointAt(0)!, 16777619) >>> 0
  return `belt-${h.toString(36)}-${n}`
}

/** Change level with the browser's view transition: the clicked texture grows into place. */
export function go(route: Route) {
  const hash = routeHash(route)
  if (location.hash === hash) return
  let done = false
  const apply = () => {
    if (done) return
    done = true
    history.pushState(null, '', hash)
    window.dispatchEvent(new Event('route'))
  }
  type Transition = { ready: Promise<void>; finished: Promise<void>; updateCallbackDone: Promise<void> }
  const doc = document as Document & { startViewTransition?: (cb: () => void) => Transition }
  if (doc.startViewTransition && document.visibilityState === 'visible') {
    // a skipped or aborted transition may never call back; the route change must happen anyway
    const transition = doc.startViewTransition(() => flushSync(apply))
    const ignore = () => {} // skipped transitions reject these; the route change still happens
    transition.ready.catch(ignore)
    transition.finished.catch(ignore)
    transition.updateCallbackDone.catch(ignore)
    window.setTimeout(apply, 400)
  } else apply()
}
