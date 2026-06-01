import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {loadFont} from '@remotion/google-fonts/NotoSansSC';
import {BODY_FONT} from '../fonts';

const {fontFamily: chartFont} = loadFont();

interface Props {
  label?: string;
  unit?: string;
  series?: number[];
  accentColor?: string;
  accentColor2?: string;
  startFrame?: number;
}

/** 折线图：spring 描边 + 填充（官方 timing 模式） */
export const AnimatedLineChart: React.FC<Props> = ({
  label = '走势',
  unit = '',
  series = [30, 45, 40, 62, 78, 90],
  accentColor = '#3b82f6',
  accentColor2 = '#22d3ee',
  startFrame = 10,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const w = 820;
  const h = 120;
  const pad = 16;
  const pts = series.length >= 2 ? series : [30, 60, 90];
  const maxV = Math.max(...pts, 1);
  const coords = pts.map((v, i) => {
    const x = pad + (i / Math.max(1, pts.length - 1)) * (w - pad * 2);
    const y = pad + (1 - v / maxV) * (h - pad * 2);
    return {x, y};
  });

  const head = spring({
    frame: frame - startFrame,
    fps,
    config: {damping: 18, stiffness: 80},
  });
  const reveal = Math.max(1, Math.floor(coords.length * head));
  const pathD = coords
    .slice(0, reveal)
    .map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`)
    .join(' ');

  return (
    <div
      style={{
        width: '100%',
        maxWidth: 880,
        padding: '20px 24px',
        borderRadius: 18,
        background: 'rgba(15,23,42,0.55)',
        border: `1px solid ${accentColor}44`,
        fontFamily: chartFont,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 12,
          fontFamily: BODY_FONT,
          fontSize: 22,
          fontWeight: 700,
          color: '#e2e8f0',
        }}
      >
        <span>{label}</span>
        {unit ? <span style={{color: accentColor2, fontSize: 18}}>{unit}</span> : null}
      </div>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display: 'block'}}>
        <defs>
          <linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accentColor} stopOpacity="0.35" />
            <stop offset="100%" stopColor={accentColor2} stopOpacity="0" />
          </linearGradient>
        </defs>
        {reveal >= 2 ? (
          <path
            d={`${pathD} L ${coords[reveal - 1].x} ${h} L ${coords[0].x} ${h} Z`}
            fill="url(#lineFill)"
            opacity={interpolate(head, [0, 1], [0, 0.85])}
          />
        ) : null}
        <path
          d={pathD}
          fill="none"
          stroke={accentColor2}
          strokeWidth={4}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {coords.slice(0, reveal).map((c, i) => {
          const pop = spring({
            frame: frame - startFrame - i * 5,
            fps,
            config: {damping: 18, stiffness: 80},
          });
          return (
            <circle
              key={i}
              cx={c.x}
              cy={c.y}
              r={interpolate(pop, [0, 1], [0, 7])}
              fill={accentColor}
              stroke="#fff"
              strokeWidth={2}
            />
          );
        })}
      </svg>
    </div>
  );
};
