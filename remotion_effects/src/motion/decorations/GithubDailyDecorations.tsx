import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';
import {LaserCornerFrame} from './LaserCornerFrame';

export type CssDecorationId =
  | 'grid-tunnel-bg'
  | 'text-stroke-yellow'
  | 'float-icon'
  | 'chart-line-rise'
  | 'stat-pill-row'
  | 'plain-white-bg'
  | 'repo-header'
  | 'pill-badge'
  | 'accent-orange-word'
  | 'daily-video-tag'
  | 'rank-number'
  | 'caption-bottom-safe'
  | 'github-badge'
  | 'cursor-blink'
  | 'image-right-panel'
  | 'glass-card'
  | 'marquee-top'
  | 'odometer-stars'
  | 'soft-purple-gradient'
  | 'pulse-button'
  | 'corner-brackets'
  | 'scan-lines'
  | 'sparkle-dots';

interface Props {
  decorations?: string[];
  /** title | content | cta */
  slideRole?: 'title' | 'content' | 'cta';
  starCount?: number;
  repoUrl?: string;
}

const TOPICS = ['OpenSource', 'AI Tools', 'DevOps', 'CLI', 'Rust', 'Python', 'Star↑'];

export const GithubDailyDecorations: React.FC<Props> = ({
  decorations = [],
  slideRole = 'title',
  starCount = 12800,
  repoUrl = '',
}) => {
  const showRepo = Boolean(repoUrl && !repoUrl.includes('owner/repo'));
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const has = (id: CssDecorationId) => decorations.includes(id);
  const layers: React.ReactNode[] = [];

  if (has('grid-tunnel-bg') && !has('corner-brackets')) {
    const shift = interpolate(frame, [0, 120], [0, 64]);
    layers.push(
      <div
        key="grid-tunnel"
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(147,112,219,0.22) 1px, transparent 1px),
            linear-gradient(90deg, rgba(88,166,255,0.16) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          backgroundPosition: `${shift}px ${shift * 0.6}px`,
          opacity: 0.42,
          transform: 'perspective(800px) rotateX(12deg) scale(1.2)',
          transformOrigin: '50% 30%',
        }}
      />,
    );
  }

  if (has('soft-purple-gradient')) {
    layers.push(
      <div
        key="soft-purple"
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse 90% 60% at 50% 20%, #6b21a866, transparent 70%)',
        }}
      />,
    );
  }

  if (has('caption-bottom-safe')) {
    layers.push(
      <div
        key="caption-safe"
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: '32%',
          background: 'linear-gradient(to top, #000000f0, transparent)',
          pointerEvents: 'none',
        }}
      />,
    );
  }

  if (has('daily-video-tag')) {
    layers.push(
      <div
        key="daily-tag"
        style={{
          position: 'absolute',
          top: 48,
          right: 48,
          padding: '8px 16px',
          border: '1px solid rgba(255,255,255,0.35)',
          borderRadius: 4,
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: 3,
          color: '#fff',
          fontFamily: 'Consolas, monospace',
        }}
      >
        DAILY VIDEO
      </div>,
    );
  }

  if (has('rank-number') && slideRole === 'title') {
    const s = spring({frame, fps, config: {damping: 14, stiffness: 180}});
    layers.push(
      <div
        key="rank"
        style={{
          position: 'absolute',
          top: 120,
          left: 48,
          fontSize: 120,
          fontWeight: 900,
          color: '#39E508',
          opacity: s,
          transform: `scale(${interpolate(s, [0, 1], [1.3, 1])})`,
        }}
      >
        TOP10
      </div>,
    );
  }

  if (has('repo-header') && showRepo) {
    layers.push(
      <div
        key="repo-header"
        style={{
          position: 'absolute',
          top: 56,
          left: 48,
          right: 48,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          fontSize: 22,
          color: '#333',
          fontWeight: 600,
        }}
      >
        <span style={{fontSize: 28}}>🐙</span>
        <span style={{fontFamily: 'Consolas, monospace'}}>{repoUrl}</span>
      </div>,
    );
  }

  if (has('marquee-top')) {
    const offset = interpolate(frame, [0, 300], [0, -width]);
    const text = TOPICS.join('  ·  ') + '  ·  ';
    layers.push(
      <div
        key="marquee"
        style={{
          position: 'absolute',
          top: 40,
          left: 0,
          width: '200%',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          fontSize: 24,
          fontWeight: 700,
          color: '#58a6ff',
          transform: `translateX(${offset}px)`,
        }}
      >
        {text.repeat(4)}
      </div>,
    );
  }

  if (has('float-icon')) {
    const y = Math.sin(frame / 15) * 12;
    layers.push(
      <div
        key="float"
        style={{
          position: 'absolute',
          right: 80,
          top: 280,
          fontSize: 72,
          transform: `translateY(${y}px)`,
          opacity: 0.9,
        }}
      >
        🚀
      </div>,
    );
  }

  if (has('glass-card') && !has('corner-brackets')) {
    const barW = Math.min(820, width * 0.86);
    const barLeft = (width - barW) / 2;
    const bars = [
      {top: '14%', h: 6},
      {top: '86%', h: 6},
    ];
    for (const b of bars) {
      const s = spring({frame, fps, config: {damping: 16, stiffness: 120}});
      layers.push(
        <div
          key={`glass-bar-${b.top}`}
          style={{
            position: 'absolute',
            left: barLeft,
            top: b.top,
            width: barW * s,
            height: b.h,
            marginLeft: (barW * (1 - s)) / 2,
            borderRadius: 4,
            background:
              'linear-gradient(90deg, transparent, rgba(255,180,90,0.85), rgba(255,217,61,0.9), rgba(255,180,90,0.85), transparent)',
            boxShadow: '0 0 18px rgba(255,159,67,0.45)',
            zIndex: 4,
            pointerEvents: 'none',
          }}
        />,
      );
    }
    const sideH = height * 0.42;
    const sideTop = height * 0.22;
    for (const side of ['left', 'right'] as const) {
      const s = spring({frame: frame - 6, fps, config: {damping: 14, stiffness: 140}});
      layers.push(
        <div
          key={`glass-side-${side}`}
          style={{
            position: 'absolute',
            top: sideTop,
            [side]: 40,
            width: 4,
            height: sideH * Math.max(0, s),
            borderRadius: 3,
            background: 'linear-gradient(180deg, rgba(255,217,61,0.1), rgba(255,159,67,0.9), rgba(255,217,61,0.1))',
            opacity: 0.85,
            zIndex: 4,
          }}
        />,
      );
    }
  }

  if (has('stat-pill-row') && slideRole !== 'title') {
    const pills = ['⭐ Star', 'MIT', 'TypeScript'];
    layers.push(
      <div
        key="pills-stat"
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 240,
          display: 'flex',
          flexDirection: 'row',
          justifyContent: 'center',
          gap: 12,
          flexWrap: 'wrap',
          pointerEvents: 'none',
          zIndex: 5,
        }}
      >
        {pills.map((label, i) => {
          const s = spring({frame: Math.max(0, frame - i * 6), fps, config: {damping: 16, stiffness: 120}});
          return (
            <div
              key={label}
              style={{
                padding: '10px 18px',
                borderRadius: 999,
                background: 'rgba(255,255,255,0.12)',
                border: '1px solid rgba(255,255,255,0.25)',
                color: '#fff',
                fontSize: 22,
                fontWeight: 700,
                opacity: s,
                transform: `translateY(${(1 - s) * 20}px)`,
              }}
            >
              {label}
            </div>
          );
        })}
      </div>,
    );
  }

  if (has('pill-badge')) {
    const badges = ['⭐ Star', '🔥 Hot', 'MIT License'];
    layers.push(
      <div
        key="pill-badge"
        style={{
          position: 'absolute',
          bottom: slideRole === 'title' ? 280 : 160,
          left: 48,
          right: 48,
          display: 'flex',
          justifyContent: 'center',
          gap: 10,
          flexWrap: 'wrap',
        }}
      >
        {badges.map((b) => (
          <span
            key={b}
            style={{
              padding: '8px 16px',
              borderRadius: 999,
              background: '#e8e8e8',
              color: '#222',
              fontSize: 20,
              fontWeight: 700,
            }}
          >
            {b}
          </span>
        ))}
      </div>,
    );
  }

  if (has('chart-line-rise') && slideRole === 'content' && !has('mid-viz-active')) {
    const h = [40, 55, 48, 70, 85, 95];
    layers.push(
      <div
        key="chart"
        style={{
          position: 'absolute',
          left: 48,
          right: 48,
          bottom: 320,
          height: 200,
          background: 'rgba(255,255,255,0.08)',
          borderRadius: 16,
          padding: 24,
          display: 'flex',
          alignItems: 'flex-end',
          gap: 12,
        }}
      >
        {h.map((target, i) => {
          const barH = interpolate(
            frame,
            [i * 4, i * 4 + 20],
            [0, target],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: `${barH}%`,
                background: 'linear-gradient(to top, #58a6ff, #3fb950)',
                borderRadius: 6,
                minHeight: 8,
              }}
            />
          );
        })}
      </div>,
    );
  }

  if (has('odometer-stars') && starCount > 0) {
    const display = Math.floor(
      interpolate(frame, [0, 50], [starCount * 0.65, starCount], {extrapolateRight: 'clamp'}),
    );
    const wan = display / 10000;
    const label =
      display >= 10000
        ? `${wan.toFixed(1).replace(/\.0$/, '')}万`
        : display >= 1000
          ? `${(display / 1000).toFixed(1).replace(/\.0$/, '')}k`
          : String(display);
    layers.push(
      <div
        key="odometer"
        style={{
          position: 'absolute',
          top: slideRole === 'content' ? 168 : 200,
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '10px 22px',
          borderRadius: 10,
          border: '1.5px solid #ffd70088',
          background: 'rgba(0,0,0,0.55)',
          fontSize: 46,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          lineHeight: 1.1,
          fontWeight: 900,
          color: '#ffd700',
          fontFamily: 'Consolas, monospace',
          textShadow: '0 0 18px rgba(255,215,0,0.65)',
          zIndex: 12,
        }}
      >
        ⭐ {label} Star
      </div>,
    );
  }

  if (has('image-right-panel')) {
    layers.push(
      <div
        key="img-panel"
        style={{
          position: 'absolute',
          right: 48,
          top: 220,
          width: width * 0.38,
          height: height * 0.45,
          borderRadius: 12,
          border: '2px solid rgba(88,166,255,0.5)',
          background: 'rgba(13,17,23,0.9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#58a6ff',
          fontSize: 20,
          fontFamily: 'monospace',
        }}
      >
        README.md
      </div>,
    );
  }

  if (has('corner-brackets')) {
    layers.push(<LaserCornerFrame key="laser-corner-frame" />);
  }

  if (has('scan-lines')) {
    const y1 = interpolate(frame % 120, [0, 120], [height * 0.15, height * 0.75]);
    const y2 = interpolate((frame + 60) % 120, [0, 120], [height * 0.2, height * 0.8]);
    for (const [key, y] of [
      ['scan-a', y1],
      ['scan-b', y2],
    ] as const) {
      layers.push(
        <div
          key={key}
          style={{
            position: 'absolute',
            left: 32,
            right: 32,
            top: y,
            height: 2,
            background:
              'linear-gradient(90deg, transparent, rgba(88,166,255,0.55), rgba(255,159,67,0.7), transparent)',
            opacity: 0.55,
            pointerEvents: 'none',
          }}
        />,
      );
    }
  }

  if (has('sparkle-dots')) {
    const dots = [
      {x: 0.12, y: 0.22, s: 8},
      {x: 0.88, y: 0.28, s: 6},
      {x: 0.18, y: 0.62, s: 5},
      {x: 0.82, y: 0.58, s: 7},
      {x: 0.5, y: 0.18, s: 4},
      {x: 0.72, y: 0.78, s: 5},
    ];
    dots.forEach((d, i) => {
      const pulse = 0.4 + 0.6 * Math.sin(frame / 12 + i);
      layers.push(
        <div
          key={`spark-${i}`}
          style={{
            position: 'absolute',
            left: width * d.x,
            top: height * d.y,
            width: d.s,
            height: d.s,
            borderRadius: '50%',
            background: `rgba(255,217,61,${0.35 + pulse * 0.45})`,
            boxShadow: `0 0 ${12 + pulse * 8}px rgba(255,159,67,0.6)`,
          }}
        />,
      );
    });
  }

  if (has('github-badge')) {
    const repoLabel = showRepo
      ? repoUrl.replace('https://', '').replace('http://', '').slice(0, 36)
      : 'GITHUB · 每日一项目';
    layers.push(
      <div
        key="gh-badge"
        style={{
          position: 'absolute',
          top: slideRole === 'content' ? 88 : 100,
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '10px 18px',
          borderRadius: 8,
          border: '1px solid #58a6ff88',
          color: '#58a6ff',
          fontSize: slideRole === 'content' ? 20 : 24,
          fontWeight: 700,
          letterSpacing: 0.5,
          lineHeight: 1.2,
          fontFamily: 'Consolas, monospace',
          maxWidth: width * 0.82,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          boxSizing: 'border-box',
        }}
      >
        {repoLabel}
      </div>,
    );
  }

  if (layers.length === 0) return null;

  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5}}>
      {layers}
    </div>
  );
};

/** 标题用：黄字黑描边 */
export function headingStyleForDecorations(
  decorations: string[] | undefined,
  base: React.CSSProperties,
): React.CSSProperties {
  if (!decorations?.includes('text-stroke-yellow')) return base;
  return {
    ...base,
    color: '#FFE135',
    WebkitTextStroke: '3px #000',
    paintOrder: 'stroke fill',
    textShadow: '4px 4px 0 #000',
  };
}

/** 橙词强调：最后一个词橙色 */
export function accentOrangeLastWord(text: string, decorations: string[] | undefined): React.ReactNode {
  if (!decorations?.includes('accent-orange-word')) return text;
  const parts = text.split(/(\s+)/);
  const words = parts.filter((p) => p.trim());
  if (words.length === 0) return text;
  const last = words[words.length - 1];
  const idx = text.lastIndexOf(last);
  return (
    <>
      {text.slice(0, idx)}
      <span style={{color: '#ff6b35', fontWeight: 900}}>{last}</span>
    </>
  );
}
