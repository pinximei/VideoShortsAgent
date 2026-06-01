import React from 'react';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {TitleCard} from './TitleCard';
import {ContentCard} from './ContentCard';
import {CTACard} from './CTACard';

export type MontageSegment = {
  composition: 'TitleCard' | 'ContentCard' | 'CTACard';
  durationInFrames: number;
  transition?: 'fade' | 'slide';
  props: Record<string, unknown>;
};

const TRANSITION_FRAMES = 14;

function pickTransition(name?: string) {
  if (name === 'slide') {
    return slide({direction: 'from-right'});
  }
  return fade();
}

function SegmentBody({segment}: {segment: MontageSegment}) {
  const p = segment.props;
  if (segment.composition === 'TitleCard') {
    return <TitleCard {...(p as React.ComponentProps<typeof TitleCard>)} />;
  }
  if (segment.composition === 'CTACard') {
    return <CTACard {...(p as React.ComponentProps<typeof CTACard>)} />;
  }
  return <ContentCard {...(p as React.ComponentProps<typeof ContentCard>)} />;
}

export const SlidesMontage: React.FC<{segments: MontageSegment[]}> = ({segments}) => {
  if (!segments.length) {
    return null;
  }

  return (
    <TransitionSeries>
      {segments.map((seg, i) => (
        <React.Fragment key={`seg-${i}-${seg.composition}`}>
          <TransitionSeries.Sequence durationInFrames={Math.max(1, seg.durationInFrames)}>
            <SegmentBody segment={seg} />
          </TransitionSeries.Sequence>
          {i < segments.length - 1 ? (
            <TransitionSeries.Transition
              presentation={pickTransition(seg.transition)}
              timing={linearTiming({durationInFrames: TRANSITION_FRAMES})}
            />
          ) : null}
        </React.Fragment>
      ))}
    </TransitionSeries>
  );
};

export function montageTotalFrames(segments: MontageSegment[]): number {
  const sum = segments.reduce((a, s) => a + Math.max(1, s.durationInFrames), 0);
  const trans = Math.max(0, segments.length - 1) * TRANSITION_FRAMES;
  return Math.max(1, sum - trans);
}
