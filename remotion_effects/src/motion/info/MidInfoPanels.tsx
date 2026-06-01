import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {BODY_FONT, DISPLAY_FONT} from '../fonts';

interface Props {
  layout?: string;
  summaryLines?: string[];
  kineticPhrases?: string[];
  accentColor?: string;
  accentColor2?: string;
  /** 面板整体延迟入场（帧） */
  panelRevealFrame?: number;
  /** steps 每行入场帧 */
  stepRevealFrames?: number[];
}

export const MidInfoPanels: React.FC<Props> = ({
  layout = 'keywords',
  summaryLines = [],
  kineticPhrases = [],
  accentColor = '#3b82f6',
  accentColor2 = '#22d3ee',
  panelRevealFrame = 0,
  stepRevealFrames = [],
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const localFrame = Math.max(0, frame - panelRevealFrame);
  const enter = spring({
    frame: localFrame,
    fps,
    config: {damping: 14, stiffness: 160},
  });

  const lines = summaryLines.filter(Boolean).slice(0, 3);
  const chips = kineticPhrases.filter(Boolean).slice(0, 5);
  const mode = (layout || 'keywords').toLowerCase();

  if (mode === 'steps') {
    const steps = lines.length ? lines : ['第一步', '第二步', '第三步'];
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          width: width * 0.82,
          opacity: enter,
          transform: `translateY(${(1 - enter) * 16}px)`,
        }}
      >
        {steps.map((step, i) => {
          const delay = stepRevealFrames[i] ?? panelRevealFrame + i * 12;
          const s = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {damping: 12, stiffness: 180},
          });
          return (
            <div
              key={step}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                opacity: s,
                transform: `translateX(${(1 - s) * 24}px)`,
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: `${accentColor}33`,
                  border: `2px solid ${accentColor}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: DISPLAY_FONT,
                  fontWeight: 900,
                  color: accentColor2,
                  fontSize: 18,
                }}
              >
                {i + 1}
              </div>
              <span
                style={{
                  fontFamily: BODY_FONT,
                  fontSize: 26,
                  fontWeight: 700,
                  color: '#f8fafc',
                }}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>
    );
  }

  if (mode === 'compare') {
    const left = lines[0] || '之前';
    const right = lines[1] || lines[0] || '现在';
    const split = spring({frame: Math.max(0, frame - 6), fps, config: {damping: 16}});
    return (
      <div
        style={{
          display: 'flex',
          gap: 12,
          width: width * 0.88,
          opacity: enter,
        }}
      >
        {[left, right].map((label, i) => (
          <div
            key={label}
            style={{
              flex: 1,
              padding: '18px 16px',
              borderRadius: 12,
              border: `2px solid ${i === 0 ? '#64748b' : accentColor}`,
              background: i === 0 ? 'rgba(15,23,42,0.55)' : `${accentColor}22`,
              transform: `scale(${0.92 + split * 0.08})`,
              opacity: interpolate(split, [0, 1], [0.5, 1]),
            }}
          >
            <div style={{fontSize: 14, color: '#94a3b8', marginBottom: 8}}>
              {i === 0 ? 'BEFORE' : 'AFTER'}
            </div>
            <div
              style={{
                fontFamily: DISPLAY_FONT,
                fontSize: 28,
                fontWeight: 800,
                color: i === 0 ? '#cbd5e1' : accentColor2,
              }}
            >
              {label}
            </div>
          </div>
        ))}
      </div>
    );
  }

  const tags = chips.length ? chips : lines.length ? lines : ['开源', '好用'];
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 10,
        justifyContent: 'center',
        maxWidth: width * 0.9,
        opacity: enter,
      }}
    >
      {tags.map((tag, i) => {
        const delay =
          stepRevealFrames[i] ?? panelRevealFrame + 8 + i * 8;
        const s = spring({
          frame: Math.max(0, frame - delay),
          fps,
          config: {damping: 14, stiffness: 200},
        });
        return (
          <span
            key={`${tag}-${i}`}
            style={{
              padding: '10px 18px',
              borderRadius: 999,
              border: `1px solid ${accentColor}88`,
              background: `${accentColor}18`,
              fontFamily: BODY_FONT,
              fontSize: 22,
              fontWeight: 700,
              color: '#f1f5f9',
              transform: `scale(${0.85 + s * 0.15})`,
              opacity: s,
            }}
          >
            {tag}
          </span>
        );
      })}
    </div>
  );
};
