import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import type {MotionParams, MotionProfileId} from '../types';
import {THEMES} from '../types';

interface Props {
  heading?: string;
  bullets: string[];
  profile: MotionProfileId | string;
  params?: MotionParams;
  bulletStartFrames?: number[];
}

export const AnimatedBullets: React.FC<Props> = ({
  heading = '',
  bullets,
  profile,
  params = {},
  bulletStartFrames = [],
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = String(profile);
  const theme = p.includes('github') ? THEMES.github : p.includes('tiktok') ? THEMES.tiktok : THEMES.kinetic;
  const fromRight = p === 'bullet_rail_right' || p.includes('github_daily');
  const staggerUp = p === 'bullet_stagger_up';
  const glassStack = p === 'glass_card_stack';

  const headSpring = spring({frame, fps, config: {damping: 16, stiffness: 100}});

  const renderBullet = (b: string, i: number, trigger: number) => {
    const s = spring({
      frame: Math.max(0, frame - trigger),
      fps,
      config: {damping: params.springDamping ?? 16, stiffness: params.springStiffness ?? 110},
    });
    let x = fromRight ? interpolate(s, [0, 1], [120, 0]) : interpolate(s, [0, 1], [-80, 0]);
    let y = 0;
    if (staggerUp) {
      y = interpolate(s, [0, 1], [80, 0]);
      x = 0;
    }
    const lineW = interpolate(s, [0, 1], [0, 100]);

    if (glassStack) {
      return (
        <div
          key={i}
          style={{
            marginBottom: 20,
            opacity: s,
            transform: `translateY(${y || interpolate(s, [0, 1], [40, 0])}px)`,
          }}
        >
          <div
            style={{
              padding: '20px 28px',
              borderRadius: 14,
              border: `1px solid ${theme.accent}44`,
              background: 'rgba(255,255,255,0.06)',
              backdropFilter: 'blur(8px)',
              maxWidth: 880,
            }}
          >
            <div style={{
              fontSize: 34,
              fontWeight: 600,
              color: theme.fg,
              lineHeight: 1.35,
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
            }}>{b}</div>
          </div>
        </div>
      );
    }

    return (
      <div
        key={i}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          marginBottom: 28,
          opacity: s,
          transform: `translate(${x}px, ${y}px)`,
        }}
      >
        <div
          style={{
            width: 6,
            height: 40,
            background: theme.accent,
            borderRadius: 3,
            transform: `scaleY(${lineW / 100})`,
            transformOrigin: 'top',
          }}
        />
        <div style={{
          fontSize: 36,
          fontWeight: 600,
          color: theme.fg,
          lineHeight: 1.35,
          maxWidth: 820,
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
        }}>{b}</div>
      </div>
    );
  };

  return (
    <div style={{padding: '200px 72px 120px', zIndex: 10}}>
      {heading && (
        <div
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: theme.fg,
            marginBottom: 48,
            opacity: headSpring,
            transform: `translateX(${(1 - headSpring) * (fromRight ? 80 : -40)}px)`,
            maxWidth: '92%',
            lineHeight: 1.25,
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
          }}
        >
          {heading}
        </div>
      )}
      {bullets.map((b, i) => {
        const trigger = bulletStartFrames[i] ?? 12 + i * (params.staggerFrames ?? 10);
        return renderBullet(b, i, trigger);
      })}
    </div>
  );
};
