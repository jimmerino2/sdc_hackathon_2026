/**
 * Sites that sell courses or credentials. A link there is free to preview at best: the full course or the certificate
 * usually costs. Everything else we link (YouTube, docs, blogs, GitHub, free tutorials) is free to read or watch.
 */
const MAY_COST = [
  'coursera.org', 'udemy.com', 'edx.org', 'credly.com', 'oreilly.com', 'datacamp.com', 'educative.io', 'ed2go.com',
  'igmguru.com', 'careerkarma.com', 'plcacademy.com', 'pluralsight.com', 'linkedin.com', 'skillshare.com', 'simplilearn.com',
  'mylearn.oracle.com',
];

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '').toLowerCase();
  } catch {
    return '';
  }
}

/** True when the link is on a site that sells what it teaches. */
export const mayCost = (url: string): boolean => {
  const host = hostOf(url);
  return MAY_COST.some((d) => host === d || host.endsWith(`.${d}`));
};

/** The links split by whether we can call them free. */
export function splitByCost<T extends { url: string }>(links: T[]): { free: T[]; mayCost: T[] } {
  return { free: links.filter((l) => !mayCost(l.url)), mayCost: links.filter((l) => mayCost(l.url)) };
}
