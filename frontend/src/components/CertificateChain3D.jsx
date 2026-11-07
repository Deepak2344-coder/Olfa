// 3D certificate chain: root -> intermediate -> leaf as glowing blocks
// connected by links. Lazy-loaded by CertificateChain.jsx so three.js only
// downloads when this view is opened.
//
// Low-spec care: no shadows / postprocessing / antialias, low dpr cap,
// "low-power" GPU hint, tiny label textures. prefers-reduced-motion: the
// scene is static (frameloop "demand") — no auto-rotate, no pulsing.
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { certStatusKind } from "../lib/score.js";

const BLOCK = [1.7, 1.15, 0.55];
const SPACING = 2.8;
const LINK_LENGTH = SPACING - BLOCK[0]; // bar between block edges
const KIND_COLORS = { ok: "#34d399", warn: "#fbbf24", bad: "#f87171" };
const KIND_LABEL = { ok: "trusted", warn: "unknown", bad: "weak / distrusted" };
const KIND_RANK = { ok: 0, warn: 1, bad: 2 };

// Shared immutable geometry: one crisp edge outline for every block.
const BLOCK_EDGES = new THREE.EdgesGeometry(new THREE.BoxGeometry(...BLOCK));

function useReducedMotion() {
  return useMemo(() => {
    try {
      return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    } catch {
      return false;
    }
  }, []);
}

/** Tiny canvas-texture label ("root", "intermediate", …) under each block. */
function makeLabelTexture(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.font = "600 30px system-ui, sans-serif";
  ctx.fillStyle = "rgba(226, 232, 240, 0.95)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 128, 32);
  return new THREE.CanvasTexture(canvas);
}

function NodeBlock({ index, count, node, hovered, reduced, onHover }) {
  const kind = certStatusKind(node.status);
  const color = KIND_COLORS[kind];
  const meshRef = useRef(null);
  const label = useMemo(() => makeLabelTexture(node.role || "cert"), [node.role]);
  useEffect(() => () => label.dispose(), [label]);

  const x = (index - (count - 1) / 2) * SPACING;

  // Skip all per-frame work when the user prefers reduced motion; the scene
  // uses frameloop="demand" then, so this only runs on pointer events.
  useFrame((state, delta) => {
    if (reduced || !meshRef.current) return;
    const target = hovered ? 1.12 : 1.0;
    const next = THREE.MathUtils.damp(meshRef.current.scale.x, target, 8, delta);
    meshRef.current.scale.setScalar(next);
    if (kind === "bad") {
      // weak / distrusted nodes glow red, gently pulsing
      meshRef.current.material.emissiveIntensity = 0.55 + 0.3 * Math.sin(state.clock.elapsedTime * 3.2);
    }
  });

  return (
    <group
      position={[x, 0, 0]}
      scale={reduced ? (hovered ? 1.1 : 1.0) : 1.0}
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(index, node, e.clientX, e.clientY);
      }}
      onPointerMove={(e) => onHover(index, node, e.clientX, e.clientY)}
      onPointerOut={() => onHover(null)}
    >
      <mesh ref={meshRef}>
        <boxGeometry args={BLOCK} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={kind === "bad" ? 0.7 : kind === "warn" ? 0.3 : 0.15}
          roughness={0.45}
          metalness={0.05}
        />
      </mesh>
      <lineSegments geometry={BLOCK_EDGES}>
        <lineBasicMaterial color={color} transparent opacity={0.65} />
      </lineSegments>
      <sprite position={[0, -1.1, 0]} scale={[2.0, 0.5, 1]}>
        <spriteMaterial map={label} transparent opacity={0.95} />
      </sprite>
    </group>
  );
}

/** Link bar between two nodes, colored by the weaker of the two endpoints. */
function LinkBar({ x, statusA, statusB }) {
  const kindA = certStatusKind(statusA);
  const kindB = certStatusKind(statusB);
  const color = KIND_COLORS[KIND_RANK[kindA] >= KIND_RANK[kindB] ? kindA : kindB];
  return (
    <mesh position={[x, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[0.12, 0.12, LINK_LENGTH, 10]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.25} roughness={0.5} />
    </mesh>
  );
}

function ChainScene({ chain, reduced, hoveredIdx, onHover }) {
  const groupRef = useRef(null);

  useFrame((_, delta) => {
    // slow auto-rotate, pauses while inspecting a node; never when reduced
    if (!reduced && hoveredIdx == null && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.25; // ~1 turn per 25s
    }
  });

  return (
    <group ref={groupRef} rotation={[0.08, reduced ? 0 : 0.4, 0]}>
      {chain.map((node, i) => (
        <NodeBlock
          key={i}
          index={i}
          count={chain.length}
          node={node}
          hovered={hoveredIdx === i}
          reduced={reduced}
          onHover={onHover}
        />
      ))}
      {chain.slice(0, -1).map((node, i) => (
        <LinkBar
          key={`link-${i}`}
          x={(i - (chain.length - 1) / 2) * SPACING + SPACING / 2}
          statusA={chain[i].status}
          statusB={chain[i + 1].status}
        />
      ))}
    </group>
  );
}

const LEGEND = [
  { key: "ok", label: "trusted" },
  { key: "warn", label: "unknown" },
  { key: "bad", label: "weak / distrusted" },
];

export default function CertificateChain3D({ chain }) {
  const reduced = useReducedMotion();
  const [hover, setHover] = useState(null); // {idx, node, x, y}

  const onHover = (idx, node, x, y) => {
    if (idx == null) setHover(null);
    else setHover({ idx, node, x, y });
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="relative h-64 w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950/80 md:h-72">
        <Canvas
          dpr={[1, 1.5]}
          frameloop={reduced ? "demand" : "always"}
          camera={{ position: [0, 1.6, 7.5], fov: 40 }}
          gl={{ antialias: false, powerPreference: "low-power" }}
        >
          <ambientLight intensity={0.9} />
          <directionalLight position={[4, 6, 6]} intensity={1.3} />
          <ChainScene
            chain={chain}
            reduced={reduced}
            hoveredIdx={hover?.idx ?? null}
            onHover={onHover}
          />
        </Canvas>

        {hover && (
          <div
            className="pointer-events-none fixed z-50 max-w-xs break-all rounded-lg border border-slate-700 bg-slate-950/95 p-3 text-xs shadow-xl"
            style={{ left: hover.x + 14, top: hover.y + 14 }}
          >
            <p className="font-mono text-[11px] leading-relaxed text-slate-200">{hover.node.subject}</p>
            {hover.node.issuer && hover.node.issuer !== hover.node.subject && (
              <p className="mt-1 font-mono text-[10px] text-slate-500">issued by {hover.node.issuer}</p>
            )}
            <p className="mt-1.5 flex items-center gap-1.5">
              <span className="capitalize text-slate-400">{hover.node.role || "cert"}</span>·
              <span style={{ color: KIND_COLORS[certStatusKind(hover.node.status)] }}>
                {KIND_LABEL[certStatusKind(hover.node.status)]}
              </span>
            </p>
          </div>
        )}

        {reduced && (
          <p className="pointer-events-none absolute bottom-1.5 left-1/2 -translate-x-1/2 rounded bg-slate-900/80 px-2 py-0.5 text-[10px] text-slate-500">
            auto-rotate off (prefers-reduced-motion)
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
        {LEGEND.map((item) => (
          <span key={item.key} className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: KIND_COLORS[item.key] }} />
            {item.label}
          </span>
        ))}
        <span className="ml-auto">hover a block for subject / issuer</span>
      </div>
    </div>
  );
}
