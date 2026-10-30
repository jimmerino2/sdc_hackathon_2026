import { afterEach, describe, expect, it, vi } from 'vitest';
import { ensureRoadmap, type RoadmapEvent } from './roadmap';

const sse = (...events: object[]) => new Response(events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''), { headers: { 'Content-Type': 'text/event-stream' } });
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const built = { title: 'Software Developers', sections: [] };

/** fetch answers in order: a GET that finds nothing, then whatever the build does. */
function serve(...after: Response[]) {
  const calls: string[] = [];
  const queue = [new Response(null, { status: 404 }), ...after];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => (calls.push(url.replace(/^.*\/roadmap/, '')), queue.shift()!)));
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('ensureRoadmap', () => {
  it('reports the build as it goes, then returns the result', async () => {
    const calls = serve(
      sse({ type: 'role', title: 'Software Developers', onet_code: 'x' }, { type: 'plan', reused: false }, { type: 'roadmap', roadmap: built }, { type: 'result', ...built, challenges: [] }),
    );
    const seen: string[] = [];
    const roadmap = await ensureRoadmap('p', 'x', (e: RoadmapEvent) => seen.push(e.type));
    expect(seen).toEqual(['building', 'role', 'plan', 'roadmap']);
    expect(roadmap.title).toBe('Software Developers');
    expect(calls[1]).toBe('/stream');
  });

  it('says nothing when the roadmap already exists', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json(built)));
    const seen: string[] = [];
    await ensureRoadmap('p', 'x', (e) => seen.push(e.type));
    expect(seen).toEqual([]);
  });

  it('falls back to the plain request on a server that cannot stream', async () => {
    const calls = serve(new Response(null, { status: 404 }), json(built, 201));
    expect((await ensureRoadmap('p', 'x')).title).toBe('Software Developers');
    expect(calls[2]).toMatch(/^\??$/);
  });

  it('takes the roadmap another tab built when the stream says 409', async () => {
    serve(sse({ type: 'failed', status: 409, message: 'already built' }), json(built));
    expect((await ensureRoadmap('p', 'x')).title).toBe('Software Developers');
  });

  it('fails with a message the page can show', async () => {
    serve(sse({ type: 'failed', status: 502, message: 'boom' }));
    await expect(ensureRoadmap('p', 'x')).rejects.toThrow('Jobee couldn’t build your roadmap');
  });
});
