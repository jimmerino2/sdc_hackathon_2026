export interface Achievement {
  id: string
  title: string
  description: string
  icon: string
}

export const achievements: Achievement[] = [
  {
    id: 'first-steps',
    title: 'Ink on the Ledger',
    description: 'Complete your first mission.',
    icon: '🪶',
  },
  {
    id: 'debugger',
    title: 'Evidence-Based',
    description: 'Pass a mission after reading a failing test.',
    icon: '🔎',
  },
  {
    id: 'copper-rights',
    title: 'Copper Rights',
    description: 'Ship a mining route that validates its input.',
    icon: '⛏️',
  },
  {
    id: 'first-ore',
    title: 'Ore of Your Own Making',
    description: 'Mine copper in the Frontier through your own route.',
    icon: '🟧',
  },
]

export const achievementById = Object.fromEntries(achievements.map((a) => [a.id, a])) as Record<
  string,
  Achievement
>

/** Cumulative XP needed to reach each level (index 0 = level 1). */
export const LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400]

export const levelTitles = ['Greenhorn', 'Camp Hand', 'Prospector', 'Surveyor', 'Pathfinder', 'Engineer', 'Trailblazer']
