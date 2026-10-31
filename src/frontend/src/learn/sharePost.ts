import { formatMinutes } from './time';

export interface ShareFacts {
  role: string;
  skills: number;
  sections: number;
  /** Estimated learning time, when the roadmap has one. */
  minutes?: number | null;
  /** The learner's name, only when they chose to put it on the image. */
  name?: string | null;
  date?: Date;
  /** Set for a finished challenge: the card and post are about it, not a roadmap. */
  challenge?: { title: string; sdg: number; sdgName: string; score?: number | null; stack?: { area: string; skills: string[] }[]; repoUrl?: string | null };
}

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** "Software Developers" -> "SoftwareDevelopers": a hashtag has no spaces or punctuation. */
export function hashtagFor(title: string): string {
  return title.split(/[^A-Za-z0-9]+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join('');
}

/** The post to start from. It says what the learner did, nothing more: no "certified" and no claim of a qualification. */
export function draftText({ role, skills, sections, challenge }: ShareFacts): string {
  const tag = hashtagFor(role);
  if (challenge) {
    const stack = (challenge.stack ?? []).filter((a) => a.skills.length).map((a) => `${a.area}: ${a.skills.join(', ')}`);
    return [
      `I just completed a Jobee challenge, "${challenge.title}", a real-world project for ${role} tied to SDG ${challenge.sdg}: ${challenge.sdgName}. I held off Robbee, the Corrupt CEO, through a rewritten brief too.`,
      '',
      ...(stack.length ? ['Here is the tech stack:', ...stack, ''] : []),
      ...(challenge.repoUrl ? ['View the full repo over here:', challenge.repoUrl, ''] : []),
      ['#Jobee', tag ? `#${tag}` : '', `#SDG${challenge.sdg}`].filter(Boolean).join(' '),
    ].join('\n');
  }
  return [
    `I just completed a Jobee learning roadmap for ${role}: ${plural(skills, 'skill')} across ${plural(sections, 'section')}, built around what the role actually asks for.`,
    '',
    ['#Jobee', tag ? `#${tag}` : '', '#Upskilling'].filter(Boolean).join(' '),
  ].join('\n');
}

/** Breaks text into at most `maxLines` lines that each fit `maxWidth`, ending the last with an ellipsis if words are left over. */
export function wrapLines(text: string, measure: (s: string) => number, maxWidth: number, maxLines: number): string[] {
  const lines: string[] = [];
  let line = '';
  const words = text.split(/\s+/).filter(Boolean);
  for (let i = 0; i < words.length; i++) {
    const next = line ? `${line} ${words[i]}` : words[i];
    if (measure(next) <= maxWidth || !line) {
      line = next;
      continue;
    }
    lines.push(line);
    line = words[i];
    if (lines.length === maxLines - 1) {
      const rest = words.slice(i).join(' ');
      let last = rest;
      while (last.length > 1 && measure(`${last}…`) > maxWidth) last = last.slice(0, -1);
      lines.push(last === rest ? rest : `${last.trimEnd()}…`);
      return lines;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export const IMAGE_W = 1200;
export const IMAGE_H = 627; // LinkedIn's recommended size for a shared image

/** Draws the "Jobee roadmap completed" card. It is Jobee's own card: it never says "certified" and says so at the bottom. */
export function drawCertificate(ctx: CanvasRenderingContext2D, f: ShareFacts): void {
  const ink = '#1e1e1e', muted = '#6b665e', amber = '#9a5200', honey = '#ffc107', cream = '#fff8e1';
  const font = (weight: number, px: number) => `${weight} ${px}px Nunito, system-ui, -apple-system, 'Segoe UI', sans-serif`;
  const W = IMAGE_W, H = IMAGE_H;

  ctx.fillStyle = cream;
  ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = honey;
  ctx.lineWidth = 14;
  ctx.strokeRect(20, 20, W - 40, H - 40);
  ctx.textBaseline = 'alphabetic';

  // wordmark and date
  ctx.fillStyle = honey;
  ctx.beginPath();
  ctx.roundRect(72, 70, 150, 52, 26);
  ctx.fill();
  ctx.fillStyle = ink;
  ctx.font = font(900, 30);
  ctx.textAlign = 'center';
  ctx.fillText('Jobee', 147, 107);
  ctx.textAlign = 'right';
  ctx.fillStyle = muted;
  ctx.font = font(700, 26);
  ctx.fillText((f.date ?? new Date()).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }), W - 72, 107);

  // heading and role
  ctx.textAlign = 'left';
  ctx.fillStyle = amber;
  ctx.font = font(900, 28);
  ctx.fillText(f.challenge ? 'JOBEE CHALLENGE COMPLETED' : 'JOBEE ROADMAP COMPLETED', 72, 210);
  ctx.fillStyle = ink;
  ctx.font = font(900, 70);
  const lines = wrapLines(f.challenge?.title ?? f.role, (s) => ctx.measureText(s).width, W - 144, 2);
  lines.forEach((l, i) => ctx.fillText(l, 72, 292 + i * 78));

  // what they did
  const y = 292 + (lines.length - 1) * 78 + 70;
  const chips = f.challenge
    ? [f.role, `SDG ${f.challenge.sdg}`, f.challenge.score != null ? `Score ${Math.round(f.challenge.score)}` : ''].filter(Boolean)
    : [plural(f.skills, 'skill'), plural(f.sections, 'section'), f.minutes ? `about ${formatMinutes(f.minutes)}` : ''].filter(Boolean);
  ctx.font = font(800, 28);
  let x = 72;
  for (const chip of chips) {
    const w = ctx.measureText(chip).width + 44;
    ctx.fillStyle = '#fff';
    ctx.strokeStyle = honey;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(x, y, w, 52, 26);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = ink;
    ctx.fillText(chip, x + 22, y + 36);
    x += w + 14;
  }

  if (f.name) {
    ctx.fillStyle = ink;
    ctx.font = font(700, 30);
    ctx.fillText(`Completed by ${f.name}`, 72, y + 112);
  }

  ctx.fillStyle = muted;
  ctx.font = font(600, 20);
  ctx.fillText('Self-reported learning on Jobee. Not an accredited qualification.', 72, H - 50);
}
