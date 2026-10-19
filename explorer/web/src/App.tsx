import { useEffect, useState } from 'react'
import { EpisodeView } from './EpisodeView'
import { Landing } from './Landing'
import { ModelsView } from './ModelsView'
import { PilotView } from './PilotView'
import { parseRoute, type Route } from './route'
import { StudyView } from './StudyView'

export default function App() {
  const [route, setRoute] = useState<Route>(() => parseRoute(location.hash))
  useEffect(() => {
    const update = () => setRoute(parseRoute(location.hash))
    window.addEventListener('route', update)
    window.addEventListener('popstate', update)
    return () => {
      window.removeEventListener('route', update)
      window.removeEventListener('popstate', update)
    }
  }, [])
  useEffect(() => {
    window.scrollTo(0, 0) // returns a Promise in newer browsers; an effect must return nothing
  }, [route])
  if (route.level === 'episode') return <EpisodeView key={`${route.run}/${route.n}`} run={route.run} n={route.n} />
  if (route.level === 'models') return <ModelsView />
  if (route.level === 'pilot') return <PilotView />
  return route.level === 'study' ? <StudyView /> : <Landing />
}
