import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {DISPLAY_FONT} from '../fonts';

interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface Props {
  sentences: Sentence[];
  accentColor?: string;
}

/** 口播同步：画面中部大字动效（解决「有声音无动画字」） */
export const MidScreenKinetic: React.FC<Props> = ({
  sentences,
  accentColor = '#FF9F43',
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const t = frame / fps;

  let active = '';
  let localT = 0;
  for (const s of sentences) {
    if (t >= s.start && t < s.end) {
      active = s.text.trim();
      localT = t - s.start;
      break;
    }
  }
  if (!active) {
    return null;
  }

  const chars = Array.from(active);
  const fontSize = Math.min(72, Math.floor((width * 0.82) / Math.max(4, chars.length * 0.55)));

  return (
    <div
      style={{
        position: 'absolute',
        top: '38%',
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 56px',
        zIndex: 92,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 4,
          maxWidth: width * 0.88,
          textAlign: 'center',
        }}
      >
        {chars.map((ch, i) => {
          const delay = i * 2;
          const s = spring({
            frame: Math.max(0, frame - Math.round(localT * fps) - delay),
            fps,
            config: {damping: 11, stiffness: 200},
          });
          const scale = interpolate(s, [0, 1], [1.4, 1]);
          const isAccent = /[0-9]/.test(ch) || ch === '！' || ch === '？';
          return (
            <span
              key={`${i}-${ch}`}
              style={{
                display: 'inline-block',
                fontFamily: DISPLAY_FONT,
                fontSize,
                fontWeight: 900,
                color: isAccent ? '#FFD93D' : '#fff8f0',
                transform: `scale(${scale}) translateY(${(1 - s) * 24}px)`,
                opacity: s,
                textShadow: `0 4px 20px rgba(0,0,0,0.75), 0 0 16px ${accentColor}55`,
                lineHeight: 1.15,
              }}
            >
              {ch}
            </span>
          );
        })}
      </div>
    </div>
  );
};
