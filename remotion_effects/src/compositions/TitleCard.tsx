import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';
import {SlideBackground} from './SlideBackground';

/**
 * TitleCard - 标题卡组件
 *
 * 大字标题居中 + 副标题 + 渐变/图片背景 + 弹性入场动画。
 * 用于视频开场。
 */
interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface TitleCardProps {
  heading?: string;
  subheading?: string;
  hookText?: string;
  captionStyle?: 'spring' | 'fade' | 'typewriter';
  colors?: string[];
  textColor?: string;
  accentColor?: string;
  imagePath?: string;
  sentences?: Sentence[];
}

export const TitleCard: React.FC<TitleCardProps> = ({
  heading = '',
  subheading = '',
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

  // 标题入场动画
  const titleSpring = spring({
    frame,
    fps,
    config: {damping: 12, stiffness: 120, mass: 0.8},
  });

  const titleY = interpolate(titleSpring, [0, 1], [100, 0]);
  const titleOpacity = interpolate(titleSpring, [0, 0.5], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 副标题延迟入场
  const subSpring = spring({
    frame: Math.max(0, frame - 10),
    fps,
    config: {damping: 14, stiffness: 100, mass: 0.6},
  });
  const subOpacity = interpolate(subSpring, [0, 0.5], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const subY = interpolate(subSpring, [0, 1], [50, 0]);

  // 装饰线动画
  const lineWidth = interpolate(titleSpring, [0, 1], [0, 200]);

  // 当前显示的字幕（从 sentences）
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

      {/* 主内容区域 - 居中 */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 80px',
      }}>
        {/* 装饰线 */}
        <div style={{
          width: lineWidth,
          height: 4,
          background: accentColor,
          marginBottom: 40,
          borderRadius: 2,
        }} />

        {/* 主标题 */}
        <div style={{
          transform: `translateY(${titleY}px)`,
          opacity: titleOpacity,
          fontSize: 80,
          fontWeight: 900,
          color: textColor,
          textAlign: 'center',
          lineHeight: 1.3,
          fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
          textShadow: '0 4px 20px rgba(0,0,0,0.5)',
          letterSpacing: 3,
        }}>
          {heading}
        </div>

        {/* 副标题 */}
        {subheading && (
          <div style={{
            transform: `translateY(${subY}px)`,
            opacity: subOpacity,
            fontSize: 36,
            fontWeight: 400,
            color: accentColor,
            textAlign: 'center',
            marginTop: 24,
            fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
            letterSpacing: 2,
          }}>
            {subheading}
          </div>
        )}

        {/* 装饰线 */}
        <div style={{
          width: lineWidth,
          height: 4,
          background: accentColor,
          marginTop: 40,
          borderRadius: 2,
        }} />
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
