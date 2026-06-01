import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';

interface Props {
  effect?: string;
  accentColor?: string;
  accentColor2?: string;
  width: number;
  height: number;
}

/** 中部装饰动效（非纯文字）：光晕 / 粒子 / 角标框 */
export const MidStageEffects: React.FC<Props> = ({
  effect = 'glow_ring',
  accentColor = '#FF9F43',
  accentColor2 = '#FFD93D',
  width,
  height,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const eff = (effect || 'glow_ring').toLowerCase();

  const pulse = 0.85 + Math.sin(frame / 18) * 0.15;
  const rot = interpolate(frame % 180, [0, 180], [0, 360]);

  if (eff === 'none') return null;

  const cx = width / 2;
  const cy = height * 0.46;

  return (
  <>
    {(eff === 'glow_ring' || eff === 'particle_dust' || eff === 'glow_scan') && (
      <div
        style={{
          position: 'absolute',
          left: cx - 220,
          top: cy - 220,
          width: 440,
          height: 440,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accentColor}22 0%, transparent 70%)`,
          transform: `scale(${pulse})`,
          pointerEvents: 'none',
          zIndex: 5,
        }}
      />
    )}

    {eff === 'bracket_slam' && (
      <>
        {[
          {l: 48, t: cy - 100, w: 48, h: 120},
          {l: width - 96, t: cy - 100, w: 48, h: 120},
        ].map((b, i) => {
          const s = spring({
            frame: Math.max(0, frame - i * 3),
            fps,
            config: {damping: 12, stiffness: 200},
          });
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: b.l,
                top: b.t,
                width: b.w,
                height: b.h,
                border: `3px solid ${accentColor}`,
                borderRight: i === 0 ? 'none' : undefined,
                borderLeft: i === 1 ? 'none' : undefined,
                opacity: s,
                transform: `scaleY(${interpolate(s, [0, 1], [0.3, 1])})`,
                zIndex: 6,
              }}
            />
          );
        })}
      </>
    )}

    {(eff === 'particle_dust' || eff === 'glow_scan') &&
      Array.from({length: 12}).map((_, i) => {
        const angle = (i / 12) * Math.PI * 2 + frame * 0.02;
        const r = 140 + (i % 3) * 40;
        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r * 0.6;
        const o = 0.2 + Math.sin(frame / 10 + i) * 0.15;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: accentColor2,
              opacity: o,
              boxShadow: `0 0 12px ${accentColor2}`,
              zIndex: 4,
            }}
          />
        );
      })}

    {eff === 'glow_scan' && (
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: cy - 80 + (frame % 90) * 1.8,
          height: 4,
          background: `linear-gradient(90deg, transparent, ${accentColor2}, transparent)`,
          opacity: 0.5,
          zIndex: 7,
        }}
      />
    )}

    {eff === 'glow_ring' && (
      <div
        style={{
          position: 'absolute',
          left: cx - 160,
          top: cy - 160,
          width: 320,
          height: 320,
          borderRadius: '50%',
          border: `2px solid ${accentColor}44`,
          transform: `rotate(${rot}deg) scale(${pulse})`,
          pointerEvents: 'none',
          zIndex: 6,
        }}
      />
    )}
  </>
  );
};
