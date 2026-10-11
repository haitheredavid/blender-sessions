import { Bounds, Center, ContactShadows, Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { Suspense, useMemo, useState } from "react";
import * as THREE from "three";
import { asset, type ModelEntry } from "./types";

type Mode = "model" | "parts";

/** A GLB scaled to ~1 unit (exports keep Blender's numbers, so mm models arrive huge),
 * centred and sitting on y=0. Upright models are stood up as hung: Blender's
 * +Z face (glTF +Y) turns toward the camera (+Z). In parts mode each mesh slides away
 * from the middle by `explode` (0..1) of the model's size. */
function Glb({ url, upright, explode }: { url: string; upright: boolean; explode: number }) {
  const { scene } = useGLTF(url);
  const root = useMemo(() => scene.clone(true), [scene]);
  const { offsets, fit } = useMemo(() => {
    const box = new THREE.Box3().setFromObject(root);
    const mid = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3()).length();
    const out: [THREE.Object3D, THREE.Vector3, THREE.Vector3][] = [];
    root.traverse((o) => {
      if (!(o as THREE.Mesh).isMesh) return;
      const c = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
      const dir = c.sub(mid);
      if (dir.lengthSq() < 1e-9) dir.set(0, 1, 0);
      out.push([o, o.position.clone(), dir.normalize().multiplyScalar(size * 0.35)]);
    });
    const dims = box.getSize(new THREE.Vector3());
    return { offsets: out, fit: 1 / Math.max(dims.x, dims.y, dims.z, 1e-6) };
  }, [root]);

  useFrame((_, dt) => {
    const k = 1 - Math.exp(-dt * 8);
    for (const [o, home, dir] of offsets) {
      o.position.lerp(home.clone().addScaledVector(dir, explode), k);
    }
  });

  return (
    <Center top>
      <group scale={fit} rotation={upright ? [Math.PI / 2, 0, 0] : [0, 0, 0]}>
        <primitive object={root} />
      </group>
    </Center>
  );
}

function Studio() {
  return (
    <>
      <hemisphereLight args={["#fff8ec", "#8a8172", 0.9]} />
      <directionalLight position={[2, 4, 3]} intensity={1.6} />
      <directionalLight position={[-3, 1.5, -2]} intensity={0.5} />
    <Environment resolution={256}>
      <Lightformer form="rect" intensity={3} position={[0, 5, 4]} scale={[10, 4, 1]} />
      <Lightformer form="rect" intensity={1.5} position={[-6, 2, -2]} rotation-y={Math.PI / 2} scale={[8, 3, 1]} />
      <Lightformer form="rect" intensity={1} position={[6, 1, 2]} rotation-y={-Math.PI / 2} scale={[8, 3, 1]} />
      <Lightformer form="ring" color="#f2b632" intensity={0.6} position={[2, 6, -6]} scale={3} />
    </Environment>
    </>
  );
}

export default function Viewer({ model }: { model: ModelEntry }) {
  const [mode, setMode] = useState<Mode>("model");
  const [explode, setExplode] = useState(0.4);
  const url = asset(mode === "parts" && model.parts ? model.parts : model.model);
  const parts = mode === "parts";

  return (
    <main className="viewer">
      <div className="stage">
        <Canvas shadows camera={{ position: [0.6, 0.5, 1.8], fov: 35 }} dpr={[1, 2]}>
          <color attach="background" args={["#efe6d2"]} />
          <Suspense fallback={null}>
            <Bounds key={mode} fit clip margin={parts ? 1.8 : 1.25}>
              <Glb url={url} upright={model.upright} explode={parts ? explode : 0} />
            </Bounds>
            <ContactShadows position={[0, 0, 0]} opacity={0.45} blur={2.4} far={1.5} scale={4} />
            <Studio />
          </Suspense>
          <OrbitControls makeDefault enableDamping />
        </Canvas>
        {model.parts && (
          <div className="controls">
            <div className="seg">
              <button className={!parts ? "on" : ""} onClick={() => setMode("model")}>assembled</button>
              <button className={parts ? "on" : ""} onClick={() => setMode("parts")}>print parts</button>
            </div>
            {parts && (
              <label className="slider">
                explode
                <input type="range" min={0} max={1} step={0.01} value={explode} onChange={(e) => setExplode(+e.target.value)} />
              </label>
            )}
          </div>
        )}
      </div>
      <aside className="info">
        <a href="#/" className="back">← all models</a>
        <h1>{model.title}</h1>
        <p className="meta">
          {model.created} · {model.status}
        </p>
        {model.intent && <p>{model.intent}</p>}
        {!!model.tags.length && (
          <ul className="tags">
            {model.tags.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        )}
        <p className="links">
          <a href={model.brief}>brief</a>
          {model.speckle && <a href={model.speckle}>speckle</a>}
          <a href={asset(model.model)} download>
            model.glb
          </a>
        </p>
        <p className="hint">drag to orbit · scroll to zoom · right-drag to pan</p>
      </aside>
    </main>
  );
}
