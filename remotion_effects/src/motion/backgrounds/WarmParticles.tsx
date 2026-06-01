import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

function seeded(i: number): number {
  return Math.sin(i * 127.1) * 43758.5453 - Math.floor(Math.sin(i * 127.1) * 43758.5453);
}

/** 暖色漂浮粒子（抖音科技播报氛围） */
export const WarmParticles: React.FC<{accent?: string}> = ({accent = '#FF9F43'}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  const dots = useMemo(() => {
    return Array.from({length: 48}, (_, i) => ({
      x: seeded(i * 3) * width,
      y: seeded(i * 7 + 1) * height,
      r: 2 + seeded(i * 11) * 5,
      speed: 0.3 + seeded(i * 13) * 0.9,
      phase: seeded(i * 17) * Math.PI * 2,
    }));
  }, [width, height]);

  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden'}}>
      {dots.map((d, i) => {
        const driftY = ((frame * d.speed + d.phase * 40) % (height + 80)) - 40;
        const driftX = Math.sin(frame / 30 + d.phase) * 18;
        const pulse = 0.35 + Math.sin(frame / 18 + d.phase) * 0.25;
        const warm = i % 3 === 0 ? accent : i % 3 === 1 ? '#FFD93D' : '#FF6B6B';
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: d.x + driftX,
              top: (d.y + driftY) % (height + 1),
              width: d.r,
              height: d.r,
              borderRadius: '50%',
              background: warm,
              opacity: pulse,
              boxShadow: `0 0 ${d.r * 3}px ${warm}88`,
            }}
          />
        );
      })}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(ellipse 80% 55% at 50% 35%, ${accent}22, transparent 70%)`,
          opacity: interpolate(frame, [0, 90], [0.5, 0.85], {extrapolateRight: 'clamp'}),
        }}
      />
    </div>
  );
};
