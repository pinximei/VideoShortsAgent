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
}

/** 抖音：TikTok 逐词高亮；小红书：单行 spring 字幕 */
export const SlideCaptionLayer: React.FC<Props> = ({
  sentences,
  captionMode = '',
  motionProfile = '',
  motionParams = {},
  captionStyle = 'spring',
  accentColor = '#00d2ff',
}) => {
  if (!sentences.length) {
    return null;
  }
  const tikTok =
    captionMode === 'tiktok' || String(motionProfile).includes('tiktok');
  if (tikTok) {
    return (
      <TikTokActiveCaption
        words={sentences.map((s) => ({text: s.text + ' ', start: s.start, end: s.end}))}
        profile={motionProfile}
        wordsPerPageMs={motionParams.wordsPerPageMs ?? 800}
      />
    );
  }
  return (
    <div style={{position: 'absolute', inset: 0, zIndex: 100, pointerEvents: 'none'}}>
      <CaptionOverlay
        sentences={sentences}
        style={captionStyle}
        accentColor={accentColor}
      />
    </div>
  );
};
