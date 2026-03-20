import {registerRoot, Composition} from 'remotion';
import {CaptionOverlay} from './compositions/CaptionOverlay';
import {GradientBackground} from './compositions/GradientBackground';
import {TitleCard} from './compositions/TitleCard';
import {ContentCard} from './compositions/ContentCard';
import {CTACard} from './compositions/CTACard';

/**
 * Remotion Root - 注册所有特效组件
 *
 * 每个 Composition 是一个独立的特效模板，可通过 CLI 渲染：
 *   npx remotion render src/index.tsx CaptionOverlay --props='...'
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* 字幕弹出特效 - 大字居中 + 弹性动画 */}
      <Composition
        id="CaptionOverlay"
        component={CaptionOverlay}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          text: '示例金句文案',
          sentences: [],
          style: 'spring' as const,
        }}
      />

      {/* 渐变背景特效 - 作为透明覆盖层 */}
      <Composition
        id="GradientBackground"
        component={GradientBackground}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          colorFrom: '#FF6B6B',
          colorTo: '#4ECDC4',
          opacity: 0.3,
        }}
      />

      {/* 标题卡 - 大字居中 + 弹性入场 */}
      <Composition
        id="TitleCard"
        component={TitleCard}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          heading: '示例标题',
          subheading: '副标题',
          colors: ['#0f0c29', '#302b63'],
          textColor: '#ffffff',
          accentColor: '#00d2ff',
        }}
      />

      {/* 内容要点卡 - 标题 + 分条逐现 */}
      <Composition
        id="ContentCard"
        component={ContentCard}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          heading: '核心要点',
          bullets: ['要点一', '要点二', '要点三'],
          colors: ['#0f0c29', '#302b63'],
          textColor: '#ffffff',
          accentColor: '#00d2ff',
        }}
      />

      {/* CTA 行动号召卡 */}
      <Composition
        id="CTACard"
        component={CTACard}
        durationInFrames={9000}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          heading: '立即行动',
          ctaText: '点击了解 →',
          colors: ['#e94560', '#533483'],
          textColor: '#ffffff',
          accentColor: '#ffdd57',
        }}
      />
    </>
  );
};

registerRoot(RemotionRoot);

