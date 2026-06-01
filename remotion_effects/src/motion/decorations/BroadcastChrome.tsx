import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {BROADCAST_FONT} from '../fonts';

/** 新闻/科技播报外框：LIVE 角标 + 底栏 + 顶栏滚动 */
export const BroadcastChrome: React.FC<{accent?: string}> = ({accent = '#FF9F43'}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const tickerOffset = interpolate(frame, [0, 300], [0, -width * 0.6]);
  const liveBlink = frame % 40 < 20 ? 1 : 0.35;
  const topics = 'GitHub Trending · AI Tools · Open Source · Star↑ · 日更拆解 · ';

  return (
    <>
      <div
        style={{
          position: 'absolute',
          top: 52,
          left: 48,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          zIndex: 88,
          fontFamily: BROADCAST_FONT,
        }}
      >
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: '50%',
            background: '#ff3344',
            opacity: liveBlink,
            boxShadow: '0 0 12px #ff334488',
          }}
        />
        <span style={{fontSize: 22, fontWeight: 800, color: '#fff', letterSpacing: 3}}>LIVE</span>
        <span
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: accent,
            padding: '4px 12px',
            border: `1px solid ${accent}66`,
            borderRadius: 4,
          }}
        >
          科技播报
        </span>
      </div>

      <div
        style={{
          position: 'absolute',
          top: 108,
          left: 0,
          width: '200%',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          fontFamily: BROADCAST_FONT,
          fontSize: 20,
          fontWeight: 700,
          color: `${accent}dd`,
          transform: `translateX(${tickerOffset}px)`,
          zIndex: 86,
        }}
      >
        {(topics.repeat(6))}
      </div>

      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 8,
          background: `linear-gradient(90deg, ${accent}, #FFD93D, ${accent})`,
          zIndex: 130,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 48,
          right: 48,
          bottom: 280,
          height: 3,
          background: `linear-gradient(90deg, transparent, ${accent}88, transparent)`,
          opacity: 0.6,
          zIndex: 85,
        }}
      />
    </>
  );
};
