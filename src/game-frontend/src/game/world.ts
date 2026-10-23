// Hand-authored map for World 1. Terrain: w water, g grass, d dirt path, s stone.

export type Terrain = 'w' | 'g' | 'd' | 's'

const TERRAIN = [
  'wwwwwggggggggggg',
  'wwwwggggggggsssg',
  'wwwgggggggggssss',
  'wwggggdddddsssss',
  'wggggddgggdsssss',
  'wgggddggggdddddd',
  'wgggdgggggggsssg',
  'wwggdggggggggggg',
  'wwggddddgggggggg',
  'wwwggggdgggggggg',
  'wwwggggddggggggg',
  'wwwwggggdggggggg',
  'wwwwwggggggggggg',
  'wwwwwwgggggggggg',
]

// Height in blocks (0-2). Water is drawn slightly below 0.
const HEIGHT = [
  '0000000000000000',
  '0000000000001222',
  '0000000000001122',
  '0000000000011111',
  '0000000000011111',
  '0000000000000000',
  '0000000000001110',
  '0000000000000000',
  '0000000000000000',
  '0000000000000000',
  '0000000000000000',
  '0000000000000111',
  '0000000000000111',
  '0000000000000111',
]

export const MAP_W = TERRAIN[0].length
export const MAP_H = TERRAIN.length

export interface Tile {
  x: number
  y: number
  terrain: Terrain
  z: number
}

export const tiles: Tile[][] = TERRAIN.map((row, y) =>
  [...row].map((t, x) => ({ x, y, terrain: t as Terrain, z: Number(HEIGHT[y][x]) })),
)

export function tileAt(x: number, y: number): Tile | null {
  return tiles[y]?.[x] ?? null
}

export type ObjectKind =
  | 'tree'
  | 'rock'
  | 'ore'
  | 'crate'
  | 'campfire'
  | 'tent'
  | 'npc'
  | 'gate'
  | 'smelter'

export interface WorldObject {
  id: string
  kind: ObjectKind
  x: number
  y: number
  label: string
  /** What pressing E does. Absent means the object is just scenery. */
  action?: 'mine' | 'pickup' | 'talk' | 'inspect'
  resource?: string
}

export const objects: WorldObject[] = [
  { id: 'tent', kind: 'tent', x: 6, y: 5, label: 'Tent', action: 'inspect' },
  { id: 'campfire', kind: 'campfire', x: 7, y: 6, label: 'Campfire', action: 'inspect' },
  { id: 'crate-1', kind: 'crate', x: 8, y: 7, label: 'Supply crate', action: 'pickup' },
  { id: 'marlo', kind: 'npc', x: 9, y: 4, label: 'Surveyor Marlo', action: 'talk' },
  { id: 'copper-1', kind: 'ore', x: 12, y: 3, label: 'Copper deposit', action: 'mine', resource: 'copper' },
  { id: 'copper-2', kind: 'ore', x: 14, y: 2, label: 'Copper deposit', action: 'mine', resource: 'copper' },
  { id: 'smelter', kind: 'smelter', x: 13, y: 6, label: 'Cold smelter', action: 'inspect' },
  { id: 'gate', kind: 'gate', x: 15, y: 5, label: 'Locked gate', action: 'inspect' },
  { id: 'rock-1', kind: 'rock', x: 11, y: 1, label: 'Stone', action: 'inspect' },
  { id: 'rock-2', kind: 'rock', x: 10, y: 2, label: 'Stone', action: 'inspect' },
  { id: 'rock-3', kind: 'rock', x: 3, y: 10, label: 'Stone' },
  ...(
    [
      [2, 4], [6, 2], [8, 1], [3, 7], [3, 9], [5, 11], [10, 10], [12, 8],
      [14, 9], [9, 12], [13, 12], [15, 10], [11, 13], [7, 13], [1, 6], [4, 1],
    ] as const
  ).map(([x, y], i) => ({ id: `tree-${i}`, kind: 'tree' as const, x, y, label: 'Pine tree', action: 'inspect' as const })),
]

export const PLAYER_START = { x: 6, y: 8 }

const blocking = new Set(objects.map((o) => `${o.x},${o.y}`))

export function isWalkable(x: number, y: number) {
  const t = tileAt(x, y)
  return !!t && t.terrain !== 'w' && !blocking.has(`${x},${y}`)
}

/** BFS over the grid. Steps may climb or drop at most one block. */
export function findPath(from: { x: number; y: number }, to: { x: number; y: number }) {
  const key = (x: number, y: number) => y * MAP_W + x
  const prev = new Map<number, number>()
  const start = key(from.x, from.y)
  const goal = key(to.x, to.y)
  const queue = [start]
  prev.set(start, -1)
  while (queue.length) {
    const cur = queue.shift()!
    if (cur === goal) break
    const cx = cur % MAP_W
    const cy = Math.floor(cur / MAP_W)
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = cx + dx
      const ny = cy + dy
      const k = key(nx, ny)
      if (prev.has(k) || !isWalkable(nx, ny)) continue
      if (Math.abs(tileAt(nx, ny)!.z - tileAt(cx, cy)!.z) > 1) continue
      prev.set(k, cur)
      queue.push(k)
    }
  }
  if (!prev.has(goal)) return null
  const path: { x: number; y: number }[] = []
  for (let k = goal; k !== start; k = prev.get(k)!) path.unshift({ x: k % MAP_W, y: Math.floor(k / MAP_W) })
  return path
}
