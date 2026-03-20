import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';
import {SlideBackground} from './SlideBackground';

/**
 * ContentCard - 内容要点卡组件
 *
 * 标题 + 分条要点逐条出现动画。
 * 支持图片背景（background / side_by_side 模式）。
 */
interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface ContentCardProps {
  heading?: string;
  bullets?: string[];
  hookText?: string;
  captionStyle?: 'spring' | 'fade' | 'typewriter';
  colors?: string[];
  textColor?: string;
  accentColor?: string;
  imagePath?: string;
  sentences?: Sentence[];
}

export const ContentCard: React.FC<ContentCardProps> = ({
  heading = '',
  bullets = [],
  hookText = '',
  captionStyle = 'spring',
  colors = ['#0f0c29', '#302b63'],
  textColor = '#ffffff',
  accentColor = '#00d2ff',
  imagePath,
  sentences = [],
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const currentTime = frame / fps;

  // 标题入场
  const headingSpring = spring({
    frame,
    fps,
    config: {damping: 14, stiffness: 130, mass: 0.7},
  });
  const headingOpacity = interpolate(headingSpring, [0, 0.4], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const headingX = interpolate(headingSpring, [0, 1], [-60, 0]);

  // 当前字幕
  let captionText = '';
  if (sentences.length > 0) {
    for (const s of sentences) {
      if (currentTime >= s.start && currentTime < s.end) {
        captionText = s.text;
        break;
      }
    }
  }

  return (
    <div style={{position: 'absolute', top: 0, left: 0, width, height}}>
      <SlideBackground colors={colors} imagePath={imagePath} />

      {/* 内容区域 */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '0 80px',
      }}>
        {/* 标题 */}
        <div style={{
          transform: `translateX(${headingX}px)`,
          opacity: headingOpacity,
          fontSize: 56,
          fontWeight: 800,
          color: accentColor,
          marginBottom: 50,
          fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
          textShadow: '0 2px 10px rgba(0,0,0,0.5)',
          borderLeft: `6px solid ${accentColor}`,
          paddingLeft: 24,
        }}>
          {heading}
        </div>

        {/* 要点列表 */}
        {bullets.map((bullet, i) => {
          const delay = 12 + i * 8;
          const bulletSpring = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {damping: 16, stiffness: 120, mass: 0.5},
          });
          const bulletOpacity = interpolate(bulletSpring, [0, 0.4], [0, 1], {
            extrapolateRight: 'clamp',
          });
          const bulletY = interpolate(bulletSpring, [0, 1], [40, 0]);

          return (
            <div
              key={i}
              style={{
                transform: `translateY(${bulletY}px)`,
                opacity: bulletOpacity,
                fontSize: 42,
                fontWeight: 500,
                color: textColor,
                marginBottom: 28,
                fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
                textShadow: '0 2px 8px rgba(0,0,0,0.4)',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 16,
              }}
            >
              <span style={{color: accentColor, fontSize: 36, marginTop: 4}}>●</span>
              <span>{bullet}</span>
            </div>
          );
        })}
      </div>

      {/* 底部字幕 */}
      {captionText && (
        <div style={{
          position: 'absolute',
          bottom: 60,
          left: 0, right: 0,
          textAlign: 'center',
          padding: '0 60px',
        }}>
          <div style={{
            fontSize: 44,
            fontWeight: 700,
            color: textColor,
            textShadow: '0 2px 10px rgba(0,0,0,0.8)',
            fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
          }}>
            {captionText}
          </div>
        </div>
      )}
    </div>
  );
};
