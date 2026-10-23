/** How a skill group (onet_role_skills.skill_group) looks on the roadmap: an icon from Icon.vue and a shade of the brand yellow. */
export interface GroupStyle {
  icon: string;
  /** 0 (lightest) to SHADES - 1 (deepest). */
  shade: number;
}

export const SHADES = 5;

// Shades step round the list, so neighbouring groups (the programming ones, the data ones) differ.
const icons: Record<string, string> = {
  'Programming Languages': 'code',
  'Web Development': 'monitor',
  'Backend Development': 'layers',
  'Mobile Development': 'plug',
  'Databases & SQL': 'database',
  'Data Engineering': 'boxes',
  'Data Science & ML': 'brain',
  'Data Analytics & BI': 'chart-bar',
  'Cloud & DevOps': 'cloud',
  'Developer Tools & Testing': 'wrench',
  'Systems & Networking': 'cpu',
  Cybersecurity: 'shield',
  'Business Systems': 'briefcase',
  'Management & Business': 'target',
  'Project & Team Tools': 'clipboard-list',
  'Office & Productivity': 'file',
  'Communication & People': 'users',
  'Thinking & Problem Solving': 'search',
  'Hands-on & Operations': 'truck',
  'Design & Creative': 'palette',
  'Engineering & CAD': 'pen-tool',
  'Engineering & Technology': 'factory',
  'Math & Science': 'sigma',
  'Humanities & Social Sciences': 'book',
  'Marketing & Social Media': 'megaphone',
  'Healthcare Systems': 'stethoscope',
  'Health & Life Sciences': 'microscope',
};
const order = Object.keys(icons);

/** A group with no entry above (a new one, or a skill with no group) gets a sparkle and a shade made from its name. */
export function groupStyle(group: string | null | undefined): GroupStyle {
  const name = group ?? '';
  const i = order.indexOf(name);
  if (i >= 0) return { icon: icons[name]!, shade: i % SHADES };
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return { icon: 'sparkles', shade: h % SHADES };
}
