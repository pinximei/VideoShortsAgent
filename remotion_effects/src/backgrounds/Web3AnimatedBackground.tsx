import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

/** 确定性随机 */
function seeded(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

export type BackgroundVariant =
  | 'mesh-aurora'
  | 'liquid-orbs'
  | 'neon-grid'
  | 'plasma-wave'
  | 'starfield-warp'
  | 'duotone-flow'
  | 'hex-tunnel'
  | 'gradient-mesh';

export interface Web3BackgroundProps {
  variant?: BackgroundVariant;
  colors?: string[];
  accentColor?: string;
  accentColor2?: string;
  imagePath?: string;
  /** 有配图时叠加强度，建议 0.08~0.2 */
  overlayOpacity?: number;
}

interface Orb {
  x: number;
  y: number;
  r: number;
  hue: number;
  phase: number;
  speed: number;
}

function buildOrbs(count: number, accent: string, accent2: string): Orb[] {
  return Array.from({length: count}, (_, i) => ({
    x: 10 + seeded(i * 3) * 80,
    y: 10 + seeded(i * 3 + 1) * 80,
    r: 120 + seeded(i * 3 + 2) * 220,
    hue: seeded(i * 5) > 0.5 ? 0 : 1,
    phase: seeded(i * 7) * Math.PI * 2,
    speed: 0.4 + seeded(i * 11) * 0.8,
  }));
}

const MeshAurora: React.FC<{
  colors: string[];
  accent: string;
  accent2: string;
  frame: number;
  width: number;
  height: number;
}> = ({colors, accent, accent2, frame, width, height}) => {
  const breathe = interpolate(frame % 120, [0, 60, 120], [0.92, 1.08, 0.92]);
  const angle = interpolate(frame, [0, 900], [200, 560]);

  const blobs = [
    {x: 20, y: 25, c: accent, s: breathe},
    {x: 75, y: 60, c: accent2, s: 1.1 / breathe},
    {x: 50, y: 85, c: colors[1] || accent, s: breathe * 0.95},
  ];

  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(${angle}deg, ${colors.join(', ')})`,
        }}
      />
      {blobs.map((b, i) => {
        const driftX = Math.sin(frame * 0.012 + i) * 8;
        const driftY = Math.cos(frame * 0.01 + i * 1.3) * 6;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${b.x + driftX}%`,
              top: `${b.y + driftY}%`,
              width: 520 * b.s,
              height: 520 * b.s,
              transform: 'translate(-50%, -50%)',
              borderRadius: '50%',
              background: `radial-gradient(circle at 30% 30%, ${b.c}55 0%, ${b.c}18 45%, transparent 72%)`,
              filter: 'none',
              mixBlendMode: 'screen',
            }}
          />
        );
      })}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `conic-gradient(from ${frame * 0.4}deg at 50% 40%, transparent, ${accent}12, transparent, ${accent2}15, transparent)`,
          mixBlendMode: 'soft-light',
        }}
      />
    </>
  );
};

const LiquidOrbs: React.FC<{
  orbs: Orb[];
  accent: string;
  accent2: string;
  frame: number;
}> = ({orbs, accent, accent2, frame}) => (
  <>
    {orbs.map((o, i) => {
      const x = o.x + Math.sin(frame * 0.008 * o.speed + o.phase) * 12;
      const y = o.y + Math.cos(frame * 0.007 * o.speed + o.phase) * 10;
      const col = o.hue ? accent : accent2;
      const pulse = 1 + Math.sin(frame * 0.04 + o.phase) * 0.12;
      return (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${x}%`,
            top: `${y}%`,
            width: o.r * pulse,
            height: o.r * pulse,
            transform: 'translate(-50%, -50%)',
            borderRadius: '50%',
            background: `radial-gradient(circle, ${col}40 0%, ${col}12 50%, transparent 70%)`,
            boxShadow: `0 0 60px ${col}25`,
            filter: 'none',
          }}
        />
      );
    })}
  </>
);

const NeonGrid: React.FC<{accent: string; frame: number; height: number}> = ({
  accent,
  frame,
  height,
}) => (
  <div
    style={{
      position: 'absolute',
      left: '-20%',
      right: '-20%',
      bottom: '-30%',
      height: height * 0.7,
      backgroundImage: `
        linear-gradient(${accent}22 1px, transparent 1px),
        linear-gradient(90deg, ${accent}22 1px, transparent 1px)
      `,
      backgroundSize: '48px 48px',
      transform: `perspective(600px) rotateX(68deg) translateY(${frame % 48}px)`,
      transformOrigin: 'center top',
      opacity: 0.85,
    }}
  />
);

const HexTunnel: React.FC<{accent: string; accent2: string; frame: number}> = ({
  accent,
  accent2,
  frame,
}) => {
  const rings = 6;
  return (
    <>
      {Array.from({length: rings}).map((_, i) => {
        const scale = 0.5 + ((frame * 0.015 + i * 0.18) % 1.2);
        const op = interpolate(scale, [0.5, 1.7], [0.35, 0], {extrapolateRight: 'clamp'});
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: '50%',
              top: '48%',
              width: 340 + i * 90,
              height: 340 + i * 90,
              transform: `translate(-50%, -50%) scale(${scale})`,
              borderRadius: '50%',
              border: `1px solid ${i % 2 ? accent : accent2}55`,
              opacity: op,
              boxShadow: `0 0 24px ${accent}20`,
            }}
          />
        );
      })}
    </>
  );
};

const StarfieldWarp: React.FC<{accent: string; frame: number; count: number}> = ({
  accent,
  frame,
  count,
}) => (
  <>
    {Array.from({length: count}).map((_, i) => {
      const bx = seeded(i) * 100;
      const by = seeded(i + 50) * 100;
      const z = ((frame * (0.3 + seeded(i * 2) * 0.5) + seeded(i * 3) * 200) % 120) / 120;
      const size = 2 + seeded(i * 4) * 3;
      const alpha = 0.3 + z * 0.7;
      const cx = 50 + (bx - 50) * (1 + z * 1.5);
      const cy = 50 + (by - 50) * (1 + z * 1.5);
      return (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${cx}%`,
            top: `${cy}%`,
            width: size,
            height: size,
            borderRadius: '50%',
            background: i % 5 === 0 ? accent : '#fff',
            opacity: alpha,
            boxShadow: `0 0 ${size * 2}px ${accent}`,
            filter: 'none',
          }}
        />
      );
    })}
  </>
);

export const Web3AnimatedBackground: React.FC<Web3BackgroundProps> = ({
  variant = 'mesh-aurora',
  colors = ['#030712', '#0f172a', '#1e1b4b'],
  accentColor = '#22d3ee',
  accentColor2 = '#a855f7',
  imagePath,
  overlayOpacity = 0.14,
}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const orbs = useMemo(() => buildOrbs(5, accentColor, accentColor2), [accentColor, accentColor2]);

  const base = colors[0] || '#030712';

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        backgroundColor: base,
      }}
    >
      {/* 基底 */}
      <div style={{position: 'absolute', inset: 0, background: `linear-gradient(165deg, ${colors.join(', ')})`}} />

      {variant === 'mesh-aurora' && (
        <MeshAurora colors={colors} accent={accentColor} accent2={accentColor2} frame={frame} width={width} height={height} />
      )}
      {variant === 'liquid-orbs' && (
        <LiquidOrbs orbs={orbs} accent={accentColor} accent2={accentColor2} frame={frame} />
      )}
      {(variant === 'neon-grid' || variant === 'hex-tunnel') && (
        <NeonGrid accent={accentColor} frame={frame} height={height} />
      )}
      {variant === 'hex-tunnel' && (
        <HexTunnel accent={accentColor} accent2={accentColor2} frame={frame} />
      )}
      {variant === 'starfield-warp' && (
        <StarfieldWarp accent={accentColor} frame={frame} count={70} />
      )}
      {variant === 'plasma-wave' && (
        <div
          style={{
            position: 'absolute',
            inset: -40,
            background: `conic-gradient(from ${frame * 1.2}deg at 50% 50%, ${accentColor}30, transparent, ${accentColor2}35, transparent, ${accentColor}25)`,
            mixBlendMode: 'screen',
            opacity: 0.9,
          }}
        />
      )}
      {variant === 'duotone-flow' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(${90 + Math.sin(frame * 0.02) * 30}deg, ${accentColor}22, transparent 40%, ${accentColor2}28)`,
          }}
        />
      )}
      {variant === 'gradient-mesh' && (
        <MeshAurora colors={[colors[0], accentColor2, colors[colors.length - 1] || colors[0]]} accent={accentColor} accent2={accentColor2} frame={frame + 30} width={width} height={height} />
      )}

      {/* 配图：低叠加强度 + 锐化遮罩，避免糊成一团 */}
      {imagePath && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(180deg, ${base}cc 0%, transparent 35%, transparent 65%, ${base}dd 100%)`,
            pointerEvents: 'none',
            zIndex: 2,
          }}
        />
      )}

      {/* 扫光 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: interpolate(frame % (fps * 4), [0, fps * 4], [-40, 140]) + '%',
          width: '35%',
          height: '100%',
          background: `linear-gradient(105deg, transparent, ${accentColor}12, transparent)`,
          transform: 'skewX(-12deg)',
          mixBlendMode: 'screen',
          zIndex: 3,
        }}
      />

      {/* 暗角（轻） */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse 85% 75% at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)',
          zIndex: 4,
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};
