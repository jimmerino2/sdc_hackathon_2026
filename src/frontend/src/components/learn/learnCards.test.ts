// @vitest-environment node
import { createSSRApp, h } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { describe, expect, it } from 'vitest';
import type { Programme } from '../../api/hrd';
import HrdCard from './HrdCard.vue';
import NextUpCard, { type NextUpSkill } from './NextUpCard.vue';

const render = (component: object, props: Record<string, unknown>) => renderToString(createSSRApp({ render: () => h(component, props) }));

const programme = (over: Partial<Programme> = {}): Programme => ({
  course_id: 1, training_provider: 'JUNZO SDN. BHD.', course_name: 'Critical Thinking - Analytical Skills and Decision Making', scheme: 'HRD Corp Claimable Course',
  certification: 'Attendance/Completion', fee_rm: 8000, discount_pct: 20, fee_after_discount_rm: 6400, in_house: false, fetched: '2026-10-31',
  source_url: 'https://example.test', ...over,
});

const skill = (links: NextUpSkill['links']): NextUpSkill => ({
  id: 'n1', name: 'Critical Thinking', skillName: 'Critical Thinking', state: 'ready', kind: 'Ability', blurb: null, blockers: [], links,
});

describe('HRD Corp card', () => {
  it('shows the verified title, that it is paid, the fee after the discount and the original', async () => {
    const html = await render(HrdCard, { programmes: [programme()] });
    expect(html).toContain('HRD Corp Verified');
    expect(html).toContain('Paid');
    expect(html).toContain('RM 6,400');
    expect(html).toContain('RM 8,000');
    expect(html).toContain('-20%');
    expect(html).not.toContain('jb-hrd__tick');
    expect(html).not.toContain('employer');
  });

  it('has a government building in its seal, like the other bands', async () => {
    const html = await render(HrdCard, { programmes: [programme()] });
    expect(html).toContain('lucide-landmark');
    expect(html).not.toContain('jb-hrd__verified');
  });

  it('shows no in-house note, RM 0 for a free course, and no footnote about the list', async () => {
    const html = await render(HrdCard, { programmes: [programme({ in_house: true, fee_after_discount_rm: 0, discount_pct: 100, fee_rm: 1280 })] });
    expect(html).not.toContain('In-house');
    expect(html).not.toContain('company books');
    expect(html).toContain('RM 0');
    expect(html).not.toContain('Fees are from');
  });

  it('marks a professional certification with a short tag that keeps the full name as its title', async () => {
    const cert = await render(HrdCard, { programmes: [programme({ certification: 'Professional Certification' })] });
    expect(cert).toContain('jb-hrd__tag--cert');
    expect(cert).toContain('title="Professional certification"');
    expect(cert).not.toContain('>Professional certification<');
    const plain = await render(HrdCard, { programmes: [programme()] });
    expect(plain).not.toContain('jb-hrd__tag--cert');
  });

  it('opens each course on its source_url in a new tab', async () => {
    const url = 'https://bizmatch.test/courses?page=25&sortOrder=asc&sortCol=name';
    const html = await render(HrdCard, { programmes: [programme({ source_url: url })] });
    expect(html).toContain(`href="${url.replace(/&/g, '&amp;')}"`);
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it('starts open like the other bands, toggles from its header, and shows a plain count', async () => {
    const html = await render(HrdCard, { programmes: [programme(), programme({ course_id: 2 })] });
    expect(html).toContain('jb-res__count">2<');
    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain('aria-controls="hrd-body"');
    expect(html).toContain('id="hrd-body"');
  });

  it('renders nothing when there is no course or the list is still loading', async () => {
    expect(await render(HrdCard, { programmes: [] })).not.toContain('HRD Corp Verified');
    expect(await render(HrdCard, { programmes: null })).not.toContain('HRD Corp Verified');
  });
});

describe('Next up card: free and may-cost links', () => {
  const links = [
    { title: '6 Creative Ways To Sharpen Critical-Thinking Skills', url: 'https://elearningindustry.com/a', kind: 'Practice' },
    { title: 'Critical Thinking (Coursera)', url: 'https://www.coursera.org/learn/critical-thinking', kind: 'Get certified' },
  ];

  it('puts a free link under Free resources and a paid-platform link under May cost', async () => {
    const html = await render(NextUpCard, { skill: skill(links), selected: true });
    const free = html.indexOf('Free resources');
    const maybe = html.indexOf('Courses and credentials');
    expect(free).toBeGreaterThan(-1);
    expect(maybe).toBeGreaterThan(free);
    expect(html.indexOf('6 Creative Ways')).toBeGreaterThan(free);
    expect(html.indexOf('6 Creative Ways')).toBeLessThan(maybe);
    expect(html.indexOf('Critical Thinking (Coursera)')).toBeGreaterThan(maybe);
  });

  it('styles the groups as bands: green for free, amber for may-cost', async () => {
    const html = await render(NextUpCard, { skill: skill(links), selected: true });
    expect(html).toContain('jb-res jb-res--free');
    expect(html).toContain('jb-res jb-res--cost');
    expect(html).toContain('lucide-gift');
    expect(html).toContain('lucide-coins');
  });

  it('lets each group fold away from its header, and says how many links it holds', async () => {
    const html = await render(NextUpCard, { skill: skill(links), selected: true });
    expect(html).toContain('aria-controls="res-free"');
    expect(html).toContain('aria-controls="res-cost"');
    expect(html).toContain('id="res-free"');
    expect(html).toContain('id="res-cost"');
    expect((html.match(/aria-expanded="true"/g) ?? []).length).toBeGreaterThanOrEqual(3); // the card's own toggle and the two groups
  });

  it('shows no empty group', async () => {
    const onlyFree = await render(NextUpCard, { skill: skill([links[0]]), selected: true });
    expect(onlyFree).toContain('Free resources');
    expect(onlyFree).not.toContain('Courses and credentials');
    const onlyPaid = await render(NextUpCard, { skill: skill([links[1]]), selected: true });
    expect(onlyPaid).not.toContain('Free resources');
    expect(onlyPaid).toContain('May cost');
  });

  it('holds the HRD Corp courses as its last band, open like the other two', async () => {
    const html = await render(NextUpCard, { skill: skill(links), selected: true, programmes: [programme()] });
    expect(html.indexOf('HRD Corp Verified')).toBeGreaterThan(html.indexOf('Courses and credentials'));
    expect(html).toMatch(/aria-expanded="true" aria-controls="res-free"/);
    expect(html).toMatch(/aria-expanded="true" aria-controls="hrd-body"/);
  });

  it('hides the HRD Corp band when there are no courses, even when the skill has no links of its own', async () => {
    const html = await render(NextUpCard, { skill: skill([]), selected: true, programmes: [] });
    expect(html).toContain('We don’t have a recommended resource');
    expect(html).not.toContain('HRD Corp Verified');
  });
});
