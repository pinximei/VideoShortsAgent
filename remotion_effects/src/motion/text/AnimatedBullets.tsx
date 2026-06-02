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
  /** 抖音：大标题 + 下方竖排副标题卡片（居中、逐条入场） */
  layoutMode?: 'default' | 'title_cards_vertical';
}

export const AnimatedBullets: React.FC<Props> = ({
  heading = '',
  bullets,
  profile,
  params = {},
  bulletStartFrames = [],
  colorMood = '',
  layoutMode = 'default',
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const p = String(profile);
  const theme = resolveMotionTheme(p, colorMood);
  const isWarm =
    colorMood === 'warm' ||
    theme.accent.toLowerCase() === '#ff9f43' ||
    theme.accent.toLowerCase() === '#ffd93d';
  const verticalProfiles = new Set([
    'glass_card_stack',
    'bullet_stagger_up',
    'shake_emphasis',
    'kinetic_slam_tight',
  ]);
  const verticalCards =
    layoutMode === 'title_cards_vertical' || verticalProfiles.has(p);
  const railRight = !verticalCards && p === 'bullet_rail_right';
  const fromRight = railRight || p.includes('github_daily');
  const staggerUp = p === 'bullet_stagger_up';
  const glassStack = verticalCards;
  /** 仅 glass_card_stack 逐条叠卡；其它竖排动效同时展示全部子标题 */
  const stackCards = p === 'glass_card_stack';
  const shakeCard = p === 'shake_emphasis';
  const slamCard = p === 'kinetic_slam_tight';

  const staggerGap = Math.max(20, params.staggerFrames ?? 22);
  const headSpring = spring({
    frame,
    fps,
    config: {damping: 16, stiffness: 120},
  });

  const bulletTriggers = bullets.map(
    (_, i) =>
      bulletStartFrames[i] ??
      (verticalCards ? 18 + i * staggerGap : 12 + i * (params.staggerFrames ?? 10)),
  );

  let latestStarted = -1;
  for (let i = 0; i < bullets.length; i += 1) {
    if (frame >= bulletTriggers[i]) latestStarted = i;
  }

  const renderBullet = (b: string, i: number, trigger: number) => {
    const s = spring({
      frame: Math.max(0, frame - trigger),
      fps,
      config: {damping: params.springDamping ?? 14, stiffness: params.springStiffness ?? 140},
    });
    let x = fromRight ? interpolate(s, [0, 1], [120, 0]) : interpolate(s, [0, 1], [-60, 0]);
    let y = 0;
    if (staggerUp || glassStack) {
      y = interpolate(s, [0, 1], [stackCards ? 28 : 48, 0]);
      x = 0;
    }
    const isLight = colorMood === 'xhs-soft' || colorMood === 'xhs';

    if (glassStack) {
      if (stackCards && frame < trigger) {
        return null;
      }
      const isCurrent = stackCards && i === latestStarted;
      const isPast = stackCards && i < latestStarted;
      const stackOpacity = stackCards
        ? isCurrent
          ? s
          : isPast
            ? 0.72
            : 0.12
        : s;
      const stackScale = stackCards
        ? isCurrent
          ? interpolate(s, [0, 1], [0.97, 1])
          : 0.94 - (latestStarted - i) * 0.02
        : interpolate(s, [0, 1], [0.96, 1]);
      const stackY = stackCards && isPast ? (latestStarted - i) * -10 : y;

      const cardSurface = shakeCard
        ? {
            background:
              'linear-gradient(145deg, rgba(255,80,120,0.28) 0%, rgba(40,20,30,0.5) 100%)',
            border: 'none',
            boxShadow:
              '0 10px 28px rgba(255, 60, 100, 0.22), inset 0 1px 0 rgba(255,255,255,0.2)',
          }
        : slamCard
          ? {
              background:
                'linear-gradient(145deg, rgba(120,180,255,0.25) 0%, rgba(20,30,50,0.55) 100%)',
              border: 'none',
              boxShadow:
                '0 12px 32px rgba(60, 120, 255, 0.2), inset 0 1px 0 rgba(255,255,255,0.18)',
            }
          : isWarm
            ? {
                background:
                  'linear-gradient(145deg, rgba(255,200,130,0.32) 0%, rgba(255,248,240,0.16) 48%, rgba(255,159,67,0.12) 100%)',
                border: 'none',
                boxShadow:
                  '0 12px 32px rgba(255, 120, 40, 0.2), inset 0 1px 0 rgba(255,255,255,0.32)',
              }
        : isLight
          ? {
              background: 'rgba(255,255,255,0.92)',
              border: 'none',
              boxShadow: '0 10px 28px rgba(0,0,0,0.1)',
            }
          : {
              background: 'rgba(255,248,240,0.14)',
              border: 'none',
              boxShadow: '0 12px 32px rgba(0,0,0,0.35)',
            };

      return (
        <div
          key={i}
          style={{
            alignSelf: 'center',
            marginBottom: stackCards ? (isCurrent ? 28 : 20) : 24,
            opacity: stackOpacity,
            transform: `translateY(${stackY}px) scale(${stackScale})`,
            zIndex: isCurrent ? 12 : 8 - i,
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              display: 'inline-block',
              maxWidth: 'min(92vw, 720px)',
              padding: '18px 32px',
              borderRadius: 14,
              backdropFilter: 'blur(10px)',
              boxSizing: 'border-box',
              textAlign: 'left',
              ...cardSurface,
            }}
          >
            <div
              style={{
                fontSize: verticalCards ? 40 : 38,
                fontWeight: 800,
                color: theme.fg,
                lineHeight: 1.32,
                wordBreak: 'keep-all',
                textAlign: 'left',
                whiteSpace: b.replace(/\s/g, '').length > 14 ? 'normal' : 'nowrap',
              }}
            >
              {b}
            </div>
          </div>
        </div>
      );
    }

    if (railRight) {
      return (
        <div
          key={i}
          style={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'stretch',
            gap: 14,
            marginBottom: 18,
            opacity: s,
            transform: `translateX(${interpolate(s, [0, 1], [100, 0])}px)`,
            maxWidth: 520,
          }}
        >
          <div
            style={{
              width: 5,
              minHeight: 52,
              background: theme.accent,
              borderRadius: 3,
              transformOrigin: 'top',
            }}
          />
          <div
            style={{
              padding: '16px 22px',
              borderRadius: 12,
              border: `1px solid ${theme.accent}55`,
              background: isLight ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.1)',
              flex: 1,
            }}
          >
            <div style={{fontSize: 32, fontWeight: 700, color: theme.fg, lineHeight: 1.35}}>
              {b}
            </div>
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
          }}
        />
        <div style={{fontSize: 36, fontWeight: 600, color: theme.fg, lineHeight: 1.35}}>{b}</div>
      </div>
    );
  };

  const containerStyle: React.CSSProperties = railRight
    ? {
        position: 'absolute',
        top: '16%',
        right: 48,
        bottom: '30%',
        left: 56,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        justifyContent: 'center',
        zIndex: 10,
        fontFamily: BODY_FONT,
      }
    : {
        position: 'absolute',
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: verticalCards ? '120px 44px 280px' : '180px 56px 280px',
        zIndex: 10,
        boxSizing: 'border-box',
        fontFamily: BODY_FONT,
      };

  return (
    <div style={containerStyle}>
      {heading ? (
        <div
          style={{
            fontFamily: DISPLAY_FONT,
            fontSize: verticalCards ? 80 : 48,
            fontWeight: 900,
            color: theme.fg,
            marginBottom: verticalCards ? 32 : 48,
            opacity: headSpring,
            transform: `translateY(${(1 - headSpring) * 32}px)`,
            maxWidth: verticalCards ? 820 : '92%',
            lineHeight: 1.2,
            wordBreak: 'keep-all',
            textAlign: 'center',
            alignSelf: 'center',
            width: verticalCards ? 'auto' : undefined,
            maxWidth: verticalCards ? '92%' : undefined,
          }}
        >
          {heading}
        </div>
      ) : null}
      <div
        style={
          verticalCards
            ? {
                display: 'inline-flex',
                flexDirection: 'column',
                alignItems: 'center',
                alignSelf: 'center',
                width: 'fit-content',
                maxWidth: '92%',
                gap: 4,
              }
            : undefined
        }
      >
        {bullets.map((b, i) => renderBullet(b, i, bulletTriggers[i]))}
      </div>
    </div>
  );
};
