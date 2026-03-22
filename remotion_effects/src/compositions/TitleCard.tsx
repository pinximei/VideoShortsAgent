import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
} from 'remotion';
import {SlideBackground} from './SlideBackground';
import {CaptionOverlay} from './CaptionOverlay';

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
  cameraPan?: string;
  particleType?: string;
  decorationStyle?: string;
  textEffect?: 'glitch' | 'neon' | 'cinematic' | 'classic';
  layoutStyle?: 'center' | 'split-left' | 'split-right' | 'top-heavy';
  colorMood?: string;
  headingStartFrame?: number;
}

export const TitleCard: React.FC<TitleCardProps> = ({
  heading = '',
  subheading = '',
  hookText = '',
  captionStyle = 'spring',
  colors = ['#0a0a0f', '#1a1a2e'],
  textColor = '#ffffff',
  accentColor = '#00e5c8',
  imagePath,
  sentences = [],
  cameraPan = 'zoom-in',
  particleType = 'glow',
  decorationStyle = 'none',
  textEffect = 'classic',
  layoutStyle = 'center',
  colorMood = '',
  headingStartFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const currentTime = frame / fps;

  // ==== Shared Springs ====
  const entryFrame = Math.max(0, frame - headingStartFrame);
  const mainSpring = spring({
    frame: entryFrame,
    fps,
    config: {damping: 15, stiffness: 100, mass: 1},
  });

  const headingChars = heading.split('');

  // ==== Effect Implementations ====
  const renderClassic = () => {
    // Original style
    const titleY = interpolate(mainSpring, [0, 1], [80, 0]);
    const titleOpacity = interpolate(mainSpring, [0, 0.5], [0, 1], { extrapolateRight: 'clamp' });
    const subSpring = spring({ frame: Math.max(0, entryFrame - 12), fps, config: {damping: 14, stiffness: 100, mass: 0.6} });
    const lineProgress = interpolate(mainSpring, [0, 1], [0, 1]);
    const lineWidth = lineProgress * 80;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 48, opacity: lineProgress }}>
          <div style={{ width: lineWidth, height: 2, background: `linear-gradient(90deg, transparent, ${accentColor})` }} />
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: accentColor, transform: `scale(${lineProgress})` }} />
          <div style={{ width: lineWidth, height: 2, background: `linear-gradient(90deg, ${accentColor}, transparent)` }} />
        </div>
        <div style={{
          transform: `translateY(${titleY}px)`, opacity: titleOpacity,
          fontSize: 80, fontWeight: 900, textAlign: 'center',
          color: textColor, textShadow: `0 4px 20px rgba(0,0,0,0.6)`
        }}>
          {heading}
        </div>
        {subheading && (
          <div style={{
            transform: `translateY(${interpolate(subSpring, [0, 1], [40, 0])}px)`,
            opacity: interpolate(subSpring, [0, 0.5], [0, 1], { extrapolateRight: 'clamp' }),
            marginTop: 32, fontSize: 34, color: accentColor,
            padding: '12px 36px', border: `1px solid ${accentColor}35`, borderRadius: 50,
          }}>
            {subheading}
          </div>
        )}
      </div>
    );
  };

  const renderGlitch = () => {
    // Cyberpunk glitch
    const progress = interpolate(mainSpring, [0, 1], [0, 1]);
    const scale = interpolate(progress, [0, 1], [1.3, 1]);
    const opacity = interpolate(progress, [0, 0.6], [0, 1]);
    const isGlitching = entryFrame > 10 && entryFrame < 25 && entryFrame % 3 === 0;

    const redShadow = isGlitching ? '4px 0px 0px rgba(255,0,0,0.8)' : '1px 0px 0px rgba(255,0,0,0.8)';
    const cyanShadow = isGlitching ? '-4px 0px 0px rgba(0,255,255,0.8)' : '-1px 0px 0px rgba(0,255,255,0.8)';

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${scale})`, opacity }}>
        <div style={{
          fontSize: 90, fontWeight: 900, textAlign: 'center',
          color: '#ffffff',
          textShadow: `${redShadow}, ${cyanShadow}, 0px 0px 15px rgba(255,255,255,0.5)`,
          transform: isGlitching ? `translateX(${Math.random() * 10 - 5}px)` : 'none',
          fontFamily: '"Impact", "Microsoft YaHei", sans-serif',
          textTransform: 'uppercase', letterSpacing: 8,
        }}>
          {heading}
        </div>
        {subheading && (
          <div style={{
            background: `${accentColor}cc`, color: '#000', padding: '5px 20px', marginTop: 20,
            fontSize: 30, fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 4,
            transform: `skewX(-15deg)`
          }}>
            <div style={{ transform: 'skewX(15deg)' }}>{subheading}</div>
          </div>
        )}
      </div>
    );
  };

  const renderNeon = () => {
    const isFlickering = (entryFrame > 5 && entryFrame < 15) ? (entryFrame % 2 === 0) : true;
    const flickerOpacity = isFlickering ? 1 : 0.3;
    const baseOpacity = interpolate(entryFrame, [0, 5], [0, 1], { extrapolateRight: 'clamp' });
    
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: baseOpacity }}>
        <div style={{
          fontSize: 100, fontWeight: 900, textAlign: 'center',
          color: '#ffffff', fontFamily: '"Arial Rounded MT Bold", "Microsoft YaHei", sans-serif',
          textShadow: `0 0 10px #fff, 0 0 20px #fff, 0 0 40px ${accentColor}, 0 0 80px ${accentColor}, 0 0 120px ${accentColor}`,
          opacity: flickerOpacity,
        }}>
          {headingChars.map((char, i) => {
            const flickerChar = Math.random() > 0.9 && entryFrame > 20;
            return <span key={i} style={{ opacity: flickerChar ? 0.5 : 1 }}>{char}</span>;
          })}
        </div>
        {subheading && (
          <div style={{
            marginTop: 40, fontSize: 36, color: accentColor, fontWeight: 'normal',
            textShadow: `0 0 10px ${accentColor}, 0 0 20px ${accentColor}`,
            opacity: flickerOpacity, letterSpacing: 10,
          }}>
            {subheading}
          </div>
        )}
      </div>
    );
  };

  const renderCinematic = () => {
    const opacity = interpolate(entryFrame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
    const tracking = interpolate(entryFrame, [0, 150], [5, 25]);
    const yShift = interpolate(entryFrame, [0, 150], [20, -10]);

    // High contrast light sweep
    const sweep = interpolate((entryFrame * 2) % 200, [0, 200], [-100, 300]);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', opacity, transform: `translateY(${yShift}px)` }}>
        <div style={{
          position: 'relative',
          fontSize: 85, fontWeight: 300, textAlign: 'center',
          color: textColor, letterSpacing: tracking,
          fontFamily: '"Times New Roman", "Songti SC", serif',
          textShadow: '0 10px 30px rgba(0,0,0,0.8)',
        }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            background: `linear-gradient(45deg, transparent ${sweep - 10}%, rgba(255,255,255,0.8) ${sweep}%, transparent ${sweep + 10}%)`,
            WebkitBackgroundClip: 'text', backgroundClip: 'text',
            WebkitTextFillColor: 'transparent', pointerEvents: 'none'
          }}>
            {heading}
          </div>
          {heading}
        </div>
        {subheading && (
          <div style={{
            marginTop: 50, fontSize: 24, color: '#aaa', letterSpacing: tracking * 1.5,
            textTransform: 'uppercase', borderTop: '1px solid rgba(255,255,255,0.2)',
            paddingTop: 20, width: '80%', textAlign: 'center'
          }}>
            {subheading}
          </div>
        )}
      </div>
    );
  };

  let wrapperStyle: React.CSSProperties = {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    display: 'flex', flexDirection: 'column', padding: '0 80px',
  };
  let captionStyleObj: React.CSSProperties = {
    position: 'absolute', left: 0, right: 0, textAlign: 'center', padding: '0 60px', zIndex: 100
  };

  switch(layoutStyle) {
    case 'split-left':
      wrapperStyle.justifyContent = 'center';
      wrapperStyle.alignItems = 'flex-start';
      break;
    case 'split-right':
      wrapperStyle.justifyContent = 'center';
      wrapperStyle.alignItems = 'flex-end';
      break;
    case 'top-heavy':
      wrapperStyle.justifyContent = 'flex-start';
      wrapperStyle.alignItems = 'center';
      wrapperStyle.paddingTop = '200px';
      break;
    case 'center':
    default:
      wrapperStyle.justifyContent = 'center';
      wrapperStyle.alignItems = 'center';
      break;
  }

  return (
    <div style={{position: 'absolute', top: 0, left: 0, width, height, fontFamily: '"Microsoft YaHei", sans-serif'}}>
      <SlideBackground 
        colors={colors} 
        imagePath={imagePath} 
        accentColor={accentColor}
        cameraPan={cameraPan}
        particleType={particleType}
        decorationStyle={decorationStyle}
        colorMood={colorMood}
      />

      {/* Vignette */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        background: 'radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.7) 100%)',
        pointerEvents: 'none',
      }} />

      {/* Main Container */}
      <div style={wrapperStyle}>
        {textEffect === 'glitch' && renderGlitch()}
        {textEffect === 'neon' && renderNeon()}
        {textEffect === 'cinematic' && renderCinematic()}
        {textEffect === 'classic' && renderClassic()}
      </div>

      {/* Subtitles (Universal Overlay) */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 100, pointerEvents: 'none' }}>
        <CaptionOverlay sentences={sentences} style={captionStyle} accentColor={accentColor} />
      </div>
    </div>
  );
};
