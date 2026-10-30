import { describe, expect, it } from 'vitest';
import { takeSseEvents } from './resume';

describe('takeSseEvents', () => {
  it('returns whole events and keeps a half-received one for later', () => {
    const first = takeSseEvents('data: {"type":"read"}\n\ndata: {"type":"cand');
    expect(first.events).toEqual([{ type: 'read' }]);
    const next = takeSseEvents(first.rest + 'idates","count":3}\n\n');
    expect(next.events).toEqual([{ type: 'candidates', count: 3 }]);
    expect(next.rest).toBe('');
  });

  it('ignores keep-alive comments and garbage', () => {
    expect(takeSseEvents(': keepalive\n\ndata: not json\n\ndata: {"type":"skill","name":"SQL","score":0.8}\n\n').events).toEqual([
      { type: 'skill', name: 'SQL', score: 0.8 },
    ]);
  });
});
