import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import type {MotionProfileId} from '../types';
import {THEMES} from '../types';

function seeded(n: number): number {
  return Math.sin(n * 12.9898) * 43758.5453 - Math.floor(Math.sin(n * 12.9898) * 43758.5453);
}

interface Props {
  profile: MotionProfileId | string;
  imagePath?: string;
  backgroundColor?: string;
  cssDecorations?: string[];
}

/** 锐背景：无全屏 blur，按动效档案 + 日更装饰选背景 */
export const ProfileBackground: React.FC<Props> = ({
  profile,
  imagePath,
  backgroundColor,
  cssDecorations = [],
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const p = String(profile);
  const dec = cssDecorations;

  const theme =
    p.includes('github') ? THEMES.github
    : p.includes('tiktok') ? THEMES.tiktok
    : p.includes('terminal') || p.includes('mono') ? THEMES.terminal
    : p.includes('minimal') ? THEMES.minimal
    : THEMES.kinetic;

  const bg =
    backgroundColor ||
    (dec.includes('plain-white-bg') ? '#f5f5f0' : null) ||
    theme.bg;

  const isTiktok = p.includes('tiktok') || bg === '#000000';
  const isLight = bg === '#f5f5f0' || bg === '#ececec' || bg === '#f0f0f0';
  const skipGradient = isTiktok || isLight || dec.includes('plain-white-bg');
  const angle = interpolate(frame, [0, 300], [160, 220]);

  return (
    <div style={{position: 'absolute', inset: 0, background: bg, overflow: 'hidden'}}>
      {!skipGradient && !dec.includes('soft-purple-gradient') && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(${angle}deg, ${bg} 0%, ${theme.accent}18 50%, ${bg} 100%)`,
          }}
        />
      )}

      {(p.includes('github') || p === 'mono_code_rain') && !dec.includes('grid-tunnel-bg') && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `linear-gradient(${theme.accent}0d 1px, transparent 1px), linear-gradient(90deg, ${theme.accent}0d 1px, transparent 1px)`,
            backgroundSize: '32px 32px',
            opacity: isLight ? 0.15 : 0.6,
          }}
        />
      )}

      {(p === 'mono_code_rain' || p.includes('terminal')) &&
        Array.from({length: 14}).map((_, col) => (
          <div
            key={col}
            style={{
              position: 'absolute',
              left: `${(col * 7 + 3) % 100}%`,
              top: `${((frame * 3 + col * 37) % 110) - 10}%`,
              fontFamily: 'Consolas, monospace',
              fontSize: 14,
              color: theme.accent,
              opacity: 0.25,
            }}
          >
            {seeded(col + frame) > 0.5 ? '1' : '0'}
          </div>
        ))}

      {dec.includes('caption-bottom-safe') && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 0,
            height: '28%',
            background: `linear-gradient(to top, ${bg}ee, transparent)`,
          }}
        />
      )}

      {(p.includes('kinetic') || p === 'flash_hook_smash') && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: interpolate(frame % 90, [0, 90], [-30, 130]) + '%',
            width: '25%',
            height: '100%',
            background: `linear-gradient(90deg, transparent, ${theme.accent}15, transparent)`,
            transform: 'skewX(-8deg)',
          }}
        />
      )}

      {imagePath && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `radial-gradient(ellipse 80% 70% at 50% 40%, transparent 50%, ${bg}dd 100%)`,
          }}
        />
      )}
    </div>
  );
};
