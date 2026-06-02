import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {DISPLAY_FONT, BODY_FONT} from '../fonts';

interface Props {
  text: string;
  fontSize?: number;
  fontWeight?: number;
  color?: string;
  accentColor?: string;
  startFrame?: number;
  /** 抖动收敛帧数（约 0.8s） */
  settleFrames?: number;
  fontFamily?: string;
  textAlign?: 'left' | 'center';
  lineHeight?: number;
}

/**
 * 逐字水波抖动，振幅逐渐衰减至静止（适合主标题/单条强调文案）。
 */
export const LiquidShakeText: React.FC<Props> = ({
  text,
  fontSize = 72,
  fontWeight = 900,
  color = '#f8fafc',
  accentColor = '#FFD93D',
  startFrame = 0,
  settleFrames = 24,
  fontFamily = DISPLAY_FONT,
  textAlign = 'center',
  lineHeight = 1.12,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = Math.max(0, frame - startFrame);
  const enter = spring({
    frame: local,
    fps,
    config: {damping: 14, stiffness: 160, mass: 0.6},
  });
  const damp = interpolate(local, [0, settleFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const chars = Array.from(text);

  return (
    <div
      style={{
        fontFamily,
        fontSize,
        fontWeight,
        color,
        textAlign,
        lineHeight,
        wordBreak: 'keep-all',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: textAlign === 'center' ? 'center' : 'flex-start',
        maxWidth: '92%',
        opacity: enter,
      }}
    >
      {chars.map((ch, i) => {
        if (ch === ' ') {
          return (
            <span key={`sp-${i}`} style={{display: 'inline-block', width: '0.35em'}} />
          );
        }
        const phase = i * 0.62;
        const wobble =
          damp > 0.02
            ? Math.sin(local * 0.42 + phase) * 7 * damp +
              Math.cos(local * 0.31 + phase * 1.2) * 4 * damp
            : 0;
        const rot = damp > 0.02 ? Math.sin(local * 0.38 + phase) * 2.5 * damp : 0;
        return (
          <span
            key={`${i}-${ch}`}
            style={{
              display: 'inline-block',
              transform: `translate(${wobble}px, ${wobble * 0.35}px) rotate(${rot}deg)`,
              textShadow:
                damp > 0.15
                  ? `0 0 12px ${accentColor}55, 0 2px 8px rgba(0,0,0,0.5)`
                  : '0 2px 8px rgba(0,0,0,0.45)',
            }}
          >
            {ch}
          </span>
        );
      })}
    </div>
  );
};

export const liquidShakeSubtitleStyle = {
  fontFamily: BODY_FONT,
} as const;
