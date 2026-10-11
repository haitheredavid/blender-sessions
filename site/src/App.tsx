import { lazy, Suspense, useEffect, useState } from "react";
import Gallery from "./Gallery";
import { asset, type ModelEntry } from "./types";

// three.js is most of the bundle; the gallery shouldn't wait for it.
const Viewer = lazy(() => import("./Viewer"));

/** #/ is the gallery, #/m/<name> a model. Hash routes need no server rewrites. */
function useRoute() {
  const read = () => window.location.hash.replace(/^#\/?/, "");
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const on = () => setRoute(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export default function App() {
  const route = useRoute();
  const [models, setModels] = useState<ModelEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(asset("models.json"))
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
      .then(setModels)
      .catch((e) => setError(`couldn't load models.json (${e.message})`));
  }, []);

  const name = route.startsWith("m/") ? decodeURIComponent(route.slice(2)) : null;
  const current = name ? models?.find((m) => m.name === name) : undefined;

  return (
    <div className="app">
      <header className="bar">
        <a href="#/" className="brand">
          <span className="dot red" />
          <span className="dot yellow" />
          <span className="dot blue" />
          bless
        </a>
        <span className="tagline">blender + sessions</span>
        <a className="gh" href="https://github.com/haitheredavid/bless">github</a>
      </header>
      {error && <p className="notice">{error}</p>}
      {!error && !models && <p className="notice">loading…</p>}
      {models && !name && <Gallery models={models} />}
      {models && name && !current && (
        <p className="notice">
          no model called “{name}”. <a href="#/">back to the gallery</a>
        </p>
      )}
      {current && (
        <Suspense fallback={<p className="notice">loading viewer…</p>}>
          <Viewer key={current.name} model={current} />
        </Suspense>
      )}
    </div>
  );
}
