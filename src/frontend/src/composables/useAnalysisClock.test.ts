import { describe, expect, it } from 'vitest';
import { formatElapsed, progressAt, stageAt } from './useAnalysisClock';

describe('progressAt', () => {
  it('starts at zero and never passes 94%', () => {
    expect(progressAt(0)).toBe(0);
    expect(progressAt(0.5)).toBeCloseTo(0.7769, 3);
    expect(progressAt(1)).toBe(0.94);
    expect(progressAt(50)).toBe(0.94);
  });

  it('only goes up', () => {
    expect(progressAt(0.5)).toBeGreaterThan(progressAt(0.2));
  });
});

describe('stageAt', () => {
  it.each([[0, 0], [0.11, 0], [0.12, 1], [0.41, 1], [0.42, 2], [0.78, 3], [3, 3]])('f=%s is stage %s', (f, stage) => {
    expect(stageAt(f)).toBe(stage);
  });
});

it('formats elapsed time as m:ss', () => {
  expect(formatElapsed(0)).toBe('0:00');
  expect(formatElapsed(65_900)).toBe('1:05');
});
