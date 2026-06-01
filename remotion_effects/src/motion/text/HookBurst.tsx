import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {DISPLAY_FONT} from '../fonts';

interface Props {
  text: string;
  beats?: string[];
  accentColor?: string;
  /** 每条爆点展示帧数（未指定 openingDurationFrames 时） */
  beatFrames?: number;
  /** 开场 hook 总帧数上限（如 100≈3.3s） */
  openingDurationFrames?: number;
}

/** 前 3 秒多句爆点轮播：大字砸入，避免整镜一句不变 */
export const HookBurst: React.FC<Props> = ({
  text,
  beats = [],
  accentColor = '#FFE135',
  beatFrames = 28,
  openingDurationFrames = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const lines = (beats.length ? beats : [text]).map((x) => (x || '').trim()).filter(Boolean);
  if (!lines.length) {
    return null;
  }

  const totalFrames =
    openingDurationFrames > 0
      ? openingDurationFrames
      : beatFrames * lines.length + 12;
  const perBeat = Math.max(
    20,
    openingDurationFrames > 0
      ? Math.floor(openingDurationFrames / lines.length)
      : beatFrames,
  );

  const idx = Math.min(lines.length - 1, Math.floor(frame / perBeat));
  const local = frame - idx * perBeat;
  const t = lines[idx];
  if (frame > totalFrames) {
    return null;
  }

  const enter = spring({
    frame: local,
    fps,
    config: {damping: 8, stiffness: 280, mass: 0.5},
  });
  const scale = interpolate(enter, [0, 1], [1.55, 1]);
  const shake =
    local > 6 && local < 20 && local % 3 === 0 ? Math.sin(local * 4) * 5 : 0;
  const fadeOut = interpolate(
    local,
    [perBeat - 8, perBeat],
    [1, idx < lines.length - 1 ? 0.15 : 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const fontSize = Math.min(108, Math.floor((width * 0.88) / Math.max(4, t.length * 0.72)));

  return (
    <div
      style={{
        position: 'absolute',
        top: '22%',
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        padding: '0 40px',
        zIndex: 95,
        pointerEvents: 'none',
        transform: `translateX(${shake}px) scale(${scale})`,
        opacity: enter * fadeOut,
      }}
    >
      <div
        style={{
          fontSize,
          fontFamily: DISPLAY_FONT,
          fontWeight: 900,
          textAlign: 'center',
          lineHeight: 1.1,
          color: '#fff',
          WebkitTextStroke: `3px ${accentColor}`,
          textShadow: `0 0 24px ${accentColor}88, 0 8px 32px rgba(0,0,0,0.9)`,
          letterSpacing: 2,
          wordBreak: 'keep-all',
          maxWidth: width * 0.92,
        }}
      >
        {t}
      </div>
    </div>
  );
};
