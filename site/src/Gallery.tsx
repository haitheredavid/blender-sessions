import { asset, type ModelEntry } from "./types";

export default function Gallery({ models }: { models: ModelEntry[] }) {
  if (!models.length) {
    return <p className="notice">nothing published yet.</p>;
  }
  return (
    <main className="gallery">
      {models.map((m) => (
        <a key={m.name} className="tile" href={`#/m/${encodeURIComponent(m.name)}`}>
          <div className="thumb">
            {m.render ? <img src={asset(m.render)} alt={m.title} loading="lazy" /> : <span>3D</span>}
          </div>
          <div className="caption">
            <strong>{m.title}</strong>
            <span>{m.created}</span>
          </div>
        </a>
      ))}
    </main>
  );
}
