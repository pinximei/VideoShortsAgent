import React from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {BODY_FONT, DISPLAY_FONT} from '../fonts';
import {LiquidShakeText} from '../text/LiquidShakeText';

interface Props {
  layout?: string;
  summaryLines?: string[];
  kineticPhrases?: string[];
  accentColor?: string;
  accentColor2?: string;
  panelRevealFrame?: number;
  stepRevealFrames?: number[];
}

/** 单条子标题：宽度随文案，组内居中 */
const SubtitleCard: React.FC<{
  accentColor: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({accentColor, style, children}) => (
  <div
    style={{
      display: 'inline-block',
      alignSelf: 'center',
      width: 'fit-content',
      maxWidth: 'min(92vw, 720px)',
      padding: '18px 32px',
      borderRadius: 14,
      border: `1.5px solid ${accentColor}bb`,
      background: `linear-gradient(135deg, ${accentColor}28, rgba(15,23,42,0.78))`,
      boxShadow: `0 8px 24px ${accentColor}30`,
      boxSizing: 'border-box',
      textAlign: 'left',
      opacity: style?.opacity,
      transform: style?.transform,
    }}
  >
    {children}
  </div>
);

function subtitleTextStyle(text: string): React.CSSProperties {
  const long = text.replace(/\s/g, '').length > 14;
  return {
    fontFamily: BODY_FONT,
    fontSize: 36,
    fontWeight: 800,
    color: '#f8fafc',
    lineHeight: 1.32,
    letterSpacing: 0,
    textAlign: 'left',
    wordBreak: 'keep-all',
    whiteSpace: long ? 'normal' : 'nowrap',
  };
}

/** 子标题列表：整组按内容宽度水平居中，卡片内文字左对齐 */
function subtitleListShell(enter: number, width: number): React.CSSProperties {
  return {
    display: 'inline-flex',
    flexDirection: 'column',
    alignItems: 'center',
    alignSelf: 'center',
    width: 'fit-content',
    maxWidth: Math.round(width * 0.9),
    marginLeft: 'auto',
    marginRight: 'auto',
    gap: 38,
    opacity: enter,
    transform: `translateY(${(1 - enter) * 16}px)`,
  };
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

  const mode = (layout || 'keywords').toLowerCase();
  const maxLines = mode === 'steps' || mode === 'framed' ? 4 : 3;
  const lines = summaryLines.filter(Boolean).slice(0, maxLines);
  const chips = kineticPhrases.filter(Boolean).slice(0, 5);

  if (mode === 'steps') {
    const pad = ['说清需求', '直接生成', '迭代版本', '马上能用'];
    const merged = lines.length ? [...lines] : [];
    for (p of pad) {
      if (merged.length >= 4) break;
      if (!merged.includes(p)) merged.push(p);
    }
    const steps = merged.slice(0, 4);
    return (
      <div style={subtitleListShell(enter, width)}>
        {steps.map((step, i) => {
          const delay = stepRevealFrames[i] ?? panelRevealFrame + i * 12;
          const s = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {damping: 12, stiffness: 180},
          });
          return (
            <SubtitleCard
              key={step}
              accentColor={accentColor}
              style={{
                opacity: s,
                transform: `translateY(${(1 - s) * 18}px) scale(${0.96 + s * 0.04})`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 14,
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    flexShrink: 0,
                    borderRadius: 8,
                    background: `${accentColor}44`,
                    border: `1.5px solid ${accentColor}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: DISPLAY_FONT,
                    fontWeight: 900,
                    color: accentColor2,
                    fontSize: 18,
                    lineHeight: 1,
                  }}
                >
                  {i + 1}
                </div>
                <span style={subtitleTextStyle(step)}>{step}</span>
              </div>
            </SubtitleCard>
          );
        })}
      </div>
    );
  }

  if (mode === 'framed') {
    const pad = ['核心亮点', '一步上手', '值得收藏', '马上能用'];
    const cards = (lines.length ? lines : pad).slice(0, 4);
    if (cards.length < 3) {
      cards.push(...pad.filter((x) => !cards.includes(x)).slice(0, 4 - cards.length));
    }
    return (
      <div style={subtitleListShell(enter, width)}>
        {cards.map((line, i) => {
          const delay = stepRevealFrames[i] ?? panelRevealFrame + 10 + i * 12;
          const s = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {damping: 14, stiffness: 170},
          });
          return (
            <SubtitleCard
              key={`${line}-${i}`}
              accentColor={accentColor}
              style={{
                opacity: s,
                transform: `translateY(${(1 - s) * 18}px) scale(${0.96 + s * 0.04})`,
              }}
            >
              <LiquidShakeText
                text={line}
                fontSize={36}
                fontWeight={800}
                color="#f8fafc"
                accentColor={accentColor2}
                startFrame={delay}
                settleFrames={18}
                fontFamily={BODY_FONT}
                textAlign="left"
                lineHeight={1.32}
              />
            </SubtitleCard>
          );
        })}
      </div>
    );
  }

  if (mode === 'compare') {
    const pairs = [
      {label: 'BEFORE', text: lines[0] || '之前'},
      {label: 'AFTER', text: lines[1] || lines[0] || '现在'},
    ];
    if (lines[2]) {
      pairs.push({label: 'PLUS', text: lines[2]});
    }
    return (
      <div style={subtitleListShell(enter, width)}>
        {pairs.map((item, i) => {
          const delay = stepRevealFrames[i] ?? panelRevealFrame + 10 + i * 12;
          const s = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {damping: 14, stiffness: 170},
          });
          return (
            <SubtitleCard
              key={`${item.label}-${item.text}`}
              accentColor={i === 0 ? '#64748b' : accentColor}
              style={{
                opacity: s,
                transform: `translateY(${(1 - s) * 18}px) scale(${0.96 + s * 0.04})`,
              }}
            >
              <div style={{fontSize: 16, color: '#94a3b8', marginBottom: 10, textAlign: 'left'}}>
                {item.label}
              </div>
              <span
                style={{
                  ...subtitleTextStyle(item.text),
                  color: i === 0 ? '#e2e8f0' : accentColor2,
                }}
              >
                {item.text}
              </span>
            </SubtitleCard>
          );
        })}
      </div>
    );
  }

  const tags = (lines.length ? lines : chips.length ? chips : ['开源', '好用']).slice(0, 3);
  return (
    <div style={subtitleListShell(enter, width)}>
      {tags.map((tag, i) => {
        const delay = stepRevealFrames[i] ?? panelRevealFrame + 8 + i * 10;
        const s = spring({
          frame: Math.max(0, frame - delay),
          fps,
          config: {damping: 14, stiffness: 200},
        });
        return (
          <SubtitleCard
            key={`${tag}-${i}`}
            accentColor={accentColor}
            style={{
              opacity: s,
              transform: `translateY(${(1 - s) * 16}px) scale(${0.88 + s * 0.12})`,
            }}
          >
            <span style={subtitleTextStyle(tag)}>{tag}</span>
          </SubtitleCard>
        );
      })}
    </div>
  );
};
