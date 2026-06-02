import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import type {MotionProfileId} from '../types';
import {resolveMotionTheme} from '../types';
import {WarmParticles} from './WarmParticles';

function seeded(n: number): number {
  return Math.sin(n * 12.9898) * 43758.5453 - Math.floor(Math.sin(n * 12.9898) * 43758.5453);
}

interface Props {
  profile: MotionProfileId | string;
  imagePath?: string;
  backgroundColor?: string;
  cssDecorations?: string[];
  colorMood?: string;
  particleType?: string;
}

/** 锐背景：暖色粒子 / 浅底深字，避免白字白底与杂乱网格叠层 */
export const ProfileBackground: React.FC<Props> = ({
  profile,
  imagePath,
  backgroundColor,
  cssDecorations = [],
  colorMood = '',
  particleType = '',
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const p = String(profile);
  const dec = cssDecorations;
  const theme = resolveMotionTheme(p, colorMood, backgroundColor);

  let bg =
    backgroundColor ||
    (dec.includes('plain-white-bg') ? theme.bg : null) ||
    theme.bg;

  const mood = (colorMood || '').trim().toLowerCase();
  let isLight =
    mood !== 'cool' &&
    mood !== 'warm' &&
    (mood === 'xhs-soft' ||
      ['#f5f5f0', '#ececec', '#f0f0f0', '#f3efe8'].includes(String(bg).toLowerCase()));
  const isXhsEditorial =
    colorMood === 'xhs-editorial' || colorMood === 'xhs';
  const isCool =
    colorMood === 'cool' || colorMood === 'xhs-soft';
  let isWarm =
    (colorMood === 'warm' || particleType === 'warm' || isXhsEditorial) && !isCool;
  let useWarmParticles = (isWarm || isCool || isXhsEditorial) && !isLight;
  const particleAccent = isXhsEditorial
    ? '#FF6B8A'
    : isCool
      ? '#3b82f6'
      : theme.accent;
  if (isWarm && isLight) {
    bg = '#120908';
    isLight = false;
    useWarmParticles = true;
  }
  if (isXhsEditorial) {
    bg = backgroundColor || '#1a1028';
    isLight = false;
    isWarm = true;
    useWarmParticles = true;
  } else if (isCool) {
    bg = backgroundColor || bg;
    isLight = false;
    useWarmParticles = true;
  }
  const angle = interpolate(frame, [0, 300], [165, 215]);
  const pulse = 0.1 + Math.sin(frame / 24) * 0.05;

  return (
    <div style={{position: 'absolute', inset: 0, background: bg, overflow: 'hidden'}}>
      {useWarmParticles && <WarmParticles accent={particleAccent} />}

      {!isLight && !useWarmParticles && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(${angle}deg, ${bg} 0%, ${theme.accent}14 45%, ${bg} 100%)`,
          }}
        />
      )}

      {isLight && (
        <>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: `linear-gradient(165deg, #fff9f2 0%, ${bg} 40%, #f5e6d8 100%)`,
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: '20%',
              left: '10%',
              width: '80%',
              height: '45%',
              background: `radial-gradient(ellipse, ${theme.accent}18, transparent 70%)`,
            }}
          />
        </>
      )}

      {isWarm && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `radial-gradient(ellipse 75% 50% at 50% 30%, ${theme.accent}${Math.round(pulse * 255).toString(16).padStart(2, '0')}, transparent 72%)`,
          }}
        />
      )}

      {(p.includes('github') || p === 'mono_code_rain') &&
        !useWarmParticles &&
        !isLight &&
        !dec.includes('grid-tunnel-bg') && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundImage: `linear-gradient(${theme.accent}08 1px, transparent 1px), linear-gradient(90deg, ${theme.accent}08 1px, transparent 1px)`,
              backgroundSize: '36px 36px',
              opacity: 0.35,
            }}
          />
        )}

      {(p === 'mono_code_rain' || p.includes('terminal')) &&
        Array.from({length: 10}).map((_, col) => (
          <div
            key={col}
            style={{
              position: 'absolute',
              left: `${(col * 9 + 4) % 100}%`,
              top: `${((frame * 2 + col * 41) % 110) - 10}%`,
              fontFamily: 'Consolas, monospace',
              fontSize: 13,
              color: theme.accent,
              opacity: 0.18,
            }}
          >
            {seeded(col + frame) > 0.5 ? '1' : '0'}
          </div>
        ))}

      {dec.includes('caption-bottom-safe') && !isLight && (
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

      {(p.includes('kinetic') || p === 'flash_hook_smash') && !isLight && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: interpolate(frame % 90, [0, 90], [-30, 130]) + '%',
            width: '22%',
            height: '100%',
            background: `linear-gradient(90deg, transparent, ${theme.accent}12, transparent)`,
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
