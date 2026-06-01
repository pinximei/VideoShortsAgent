import React from 'react';
import {CaptionOverlay} from '../../compositions/CaptionOverlay';
import {TikTokActiveCaption} from './TikTokActiveCaption';
import type {MotionParams} from '../types';

interface Sentence {
  text: string;
  start: number;
  end: number;
}

interface Props {
  sentences: Sentence[];
  captionMode?: string;
  motionProfile?: string;
  motionParams?: MotionParams;
  captionStyle?: 'spring' | 'fade' | 'typewriter';
  accentColor?: string;
  colorMood?: string;
  midScreenKinetic?: boolean;
  textColor?: string;
}

/** 抖音：中屏动效字 + 底栏 TikTok；小红书：居中 fade 字幕 */
export const SlideCaptionLayer: React.FC<Props> = ({
  sentences,
  captionMode = '',
  motionProfile = '',
  motionParams = {},
  captionStyle = 'spring',
  accentColor = '#FF9F43',
  colorMood = '',
  midScreenKinetic = false,
  textColor = '#FFFFFF',
}) => {
  if (!sentences.length) {
    return null;
  }
  const tikTok =
    captionMode === 'tiktok' || String(motionProfile).includes('tiktok');

  return (
    <>
      {tikTok ? (
        <TikTokActiveCaption
          words={sentences.map((s) => ({text: s.text + ' ', start: s.start, end: s.end}))}
          profile={motionProfile}
          wordsPerPageMs={motionParams.wordsPerPageMs ?? 800}
          accentColor={accentColor}
        />
      ) : (
        <div style={{position: 'absolute', inset: 0, zIndex: 100, pointerEvents: 'none'}}>
          <CaptionOverlay
            sentences={sentences}
            style={captionStyle}
            accentColor={accentColor}
            textColor={textColor}
          />
        </div>
      )}
    </>
  );
};
