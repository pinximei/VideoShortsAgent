import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import type {MotionParams, MotionProfileId} from '../types';
import {resolveMotionTheme} from '../types';
import {DISPLAY_FONT, BODY_FONT} from '../fonts';

interface Props {
  heading?: string;
  bullets: string[];
  profile: MotionProfileId | string;
  params?: MotionParams;
  bulletStartFrames?: number[];
  colorMood?: string;
}

export const AnimatedBullets: React.FC<Props> = ({
  heading = '',
  bullets,
  profile,
  params = {},
  bulletStartFrames = [],
  colorMood = '',
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const p = String(profile);
  const theme = resolveMotionTheme(p, colorMood);
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

    const isLight = colorMood === 'xhs-soft' || colorMood === 'xhs';
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
              border: `1px solid ${theme.accent}${isLight ? '55' : '44'}`,
              background: isLight ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.08)',
              backdropFilter: 'blur(8px)',
              maxWidth: 880,
              boxShadow: isLight ? '0 8px 24px rgba(0,0,0,0.08)' : 'none',
            }}
          >
            <div style={{
              fontSize: 34,
              fontWeight: 600,
              color: theme.fg,
              lineHeight: 1.35,
              maxWidth: 820,
              wordBreak: 'keep-all',
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
          wordBreak: 'keep-all',
        }}>{b}</div>
      </div>
    );
  };

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '180px 56px 280px',
        zIndex: 10,
        boxSizing: 'border-box',
        fontFamily: BODY_FONT,
      }}
    >
      {heading && (
        <div
          style={{
            fontFamily: DISPLAY_FONT,
            fontSize: 48,
            fontWeight: 800,
            color: theme.fg,
            marginBottom: 48,
            opacity: headSpring,
            transform: `translateX(${(1 - headSpring) * (fromRight ? 80 : -40)}px)`,
            maxWidth: '92%',
            lineHeight: 1.25,
            wordBreak: 'keep-all',
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
