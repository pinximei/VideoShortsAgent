import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {DISPLAY_FONT, BODY_FONT} from '../fonts';
import {resolveMotionTheme} from '../types';

const ICONS = ['📈', '⚡', '🎬', '🔥', '⭐', '🛠️'];

interface Props {
  heading?: string;
  featureLabel: string;
  sceneIndex?: number;
  sceneTotal?: number;
  accentColor?: string;
  colorMood?: string;
}

/** 单要点聚焦镜：一次只亮一个卖点，配场景编号（非口播字幕重复） */
export const ContentFocusStage: React.FC<Props> = ({
  heading = '',
  featureLabel,
  sceneIndex = 0,
  sceneTotal = 3,
  accentColor = '#FF9F43',
  colorMood = 'warm',
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const theme = resolveMotionTheme('tiktok', colorMood);
  const label = (featureLabel || '').trim();
  const icon = ICONS[sceneIndex % ICONS.length];

  const badgeIn = spring({frame, fps, config: {damping: 14, stiffness: 160}});
  const headIn = spring({frame: Math.max(0, frame - 8), fps, config: {damping: 16, stiffness: 120}});
  const cardIn = spring({frame: Math.max(0, frame - 18), fps, config: {damping: 12, stiffness: 180}});
  const pulse = 1 + Math.sin(frame / 20) * 0.03;
  const fontSize = Math.min(56, Math.floor((width * 0.78) / Math.max(4, label.length * 0.52)));

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '200px 48px 360px',
        boxSizing: 'border-box',
        zIndex: 20,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 148,
          left: 48,
          padding: '10px 20px',
          borderRadius: 8,
          border: `2px solid ${accentColor}88`,
          fontFamily: BODY_FONT,
          fontSize: 22,
          fontWeight: 800,
          color: accentColor,
          opacity: badgeIn,
          transform: `translateY(${(1 - badgeIn) * 16}px)`,
        }}
      >
        场景 {sceneIndex + 1}/{sceneTotal}
      </div>

      {heading ? (
        <div
          style={{
            fontFamily: DISPLAY_FONT,
            fontSize: 44,
            fontWeight: 800,
            color: theme.fg,
            marginBottom: 48,
            opacity: headIn,
            transform: `translateY(${(1 - headIn) * 24}px)`,
            textAlign: 'center',
            maxWidth: width * 0.88,
          }}
        >
          {heading}
        </div>
      ) : null}

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 28,
          padding: '36px 40px',
          borderRadius: 24,
          background: 'rgba(0,0,0,0.45)',
          border: `2px solid ${accentColor}55`,
          boxShadow: `0 16px 48px rgba(0,0,0,0.5), 0 0 40px ${accentColor}22`,
          maxWidth: width * 0.9,
          opacity: cardIn,
          transform: `scale(${interpolate(cardIn, [0, 1], [0.88, 1]) * pulse})`,
        }}
      >
        <div style={{fontSize: 72, lineHeight: 1}}>{icon}</div>
        <div
          style={{
            fontFamily: DISPLAY_FONT,
            fontSize,
            fontWeight: 900,
            color: theme.fg,
            textAlign: 'center',
            lineHeight: 1.2,
            wordBreak: 'keep-all',
            textShadow: `0 4px 24px rgba(0,0,0,0.6), 0 0 20px ${accentColor}44`,
          }}
        >
          {label}
        </div>
      </div>
    </div>
  );
};
