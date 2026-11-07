// Half-circle trust gauge. 0 on the left (red) .. 100 on the right (green),
// needle color follows the score band. `score` is the contract trust score
// (higher = safer).
import { clampScore, gaugeAngle, scoreBand, verdictClasses } from "../lib/score.js";

const NEEDLE_COLOR = {
  green: "#34d399", // emerald-400
  amber: "#fbbf24", // amber-400
  red: "#f87171", // red-400
};

export default function ScoreGauge({ score, verdict }) {
  const s = clampScore(score);
  const angle = gaugeAngle(s);
  const band = scoreBand(s);
  const needleX = 100 + 66 * Math.cos(((angle + 90) * Math.PI) / 180);
  const needleY = 100 - 66 * Math.sin(((angle + 90) * Math.PI) / 180);
  // angle+90: gaugeAngle() is 0=up based; here we draw with math angles where
  // up = 90deg, left = 180deg, right = 0deg.

  return (
    <div className="flex flex-col items-center gap-2">
      <svg viewBox="0 0 200 118" className="w-56 max-w-full" role="img" aria-label={`Trust score ${s} of 100`}>
        {/* three arc segments: red (0-33), amber (33-66), green (66-100) */}
        <path d="M 20 100 A 80 80 0 0 1 60 30.72" fill="none" stroke="#7f1d1d" strokeWidth="14" strokeLinecap="round" opacity="0.55" />
        <path d="M 60 30.72 A 80 80 0 0 1 140 30.72" fill="none" stroke="#78350f" strokeWidth="14" opacity="0.55" />
        <path d="M 140 30.72 A 80 80 0 0 1 180 100" fill="none" stroke="#064e3b" strokeWidth="14" strokeLinecap="round" opacity="0.55" />

        {/* needle */}
        <line x1="100" y1="100" x2={needleX.toFixed(2)} y2={needleY.toFixed(2)} stroke={NEEDLE_COLOR[band]} strokeWidth="5" strokeLinecap="round" />
        <circle cx="100" cy="100" r="7" fill={NEEDLE_COLOR[band]} />

        <text x="20" y="114" className="fill-slate-500" fontSize="11">0</text>
        <text x="173" y="114" className="fill-slate-500" fontSize="11">100</text>
      </svg>

      <div className="text-5xl font-bold tabular-nums" style={{ color: NEEDLE_COLOR[band] }}>
        {s}
      </div>
      {verdict && (
        <span className={`rounded-full px-3 py-1 text-sm font-semibold uppercase tracking-wide ring-1 ${verdictClasses(verdict, s)}`}>
          {verdict}
        </span>
      )}
    </div>
  );
}
