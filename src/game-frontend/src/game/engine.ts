// Canvas isometric renderer + input for the Frontier. It owns movement,
// animation and interaction targeting only. It never decides game outcomes:
// the Vue layer forwards interactions to the trusted backend and calls
// `feedback()` with whatever the backend answered.

import {
  MAP_H,
  MAP_W,
  PLAYER_START,
  findPath,
  isWalkable,
  objects,
  tileAt,
  tiles,
  type WorldObject,
} from './world'

const TW = 64
const TH = 32
const ZH = 16
const BASE = 10
const STEP_MS = 170

type Vec = { x: number; y: number }

interface Particle {
  x: number
  y: number
  z: number
  vx: number
  vy: number
  vz: number
  life: number
  max: number
  color: string
  size: number
}

interface Floater {
  x: number
  y: number
  z: number
  text: string
  color: string
  life: number
}

export interface EngineCallbacks {
  onInteract?(obj: WorldObject): void
  onTargetChange?(obj: WorldObject | null): void
}

export interface EngineOptions {
  interactive: boolean
}

export interface ViewState {
  nodes: Record<string, { remaining: number }>
  hasPickaxe: boolean
}

// ---------- colour helpers ----------

function shade(hex: string, amt: number) {
  const n = parseInt(hex.slice(1), 16)
  const f = (c: number) => Math.max(0, Math.min(255, Math.round(c + (amt < 0 ? c * amt : (255 - c) * amt))))
  const r = f((n >> 16) & 255)
  const g = f((n >> 8) & 255)
  const b = f(n & 255)
  return `rgb(${r},${g},${b})`
}

function hash(x: number, y: number) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453
  return s - Math.floor(s)
}

const TERRAIN_COLORS = {
  g: ['#7cb342', '#86bd4a', '#74ab3d'],
  d: ['#c79a5b', '#cfa365', '#bf9152'],
  s: ['#9e9a92', '#a8a49b', '#96928a'],
  w: ['#3f8fc4', '#4799cf', '#3887bb'],
}
const SIDE = { g: '#8a6a43', d: '#9a7444', s: '#7d7a73', w: '#2f6e99' }

export class FrontierEngine {
  private ctx: CanvasRenderingContext2D
  private dpr = 1
  private w = 0
  private h = 0
  private raf = 0
  private last = 0
  private t = 0
  private ro: ResizeObserver
  private reduced: boolean

  private player = { x: PLAYER_START.x, y: PLAYER_START.y, fromX: PLAYER_START.x, fromY: PLAYER_START.y, p: 1, dir: { x: 0, y: 1 } }
  private path: Vec[] = []
  private pendingInteract: WorldObject | null = null
  private keys = new Set<string>()
  private cam = { x: 0, y: 0 }
  private hover: Vec | null = null
  private hoverObj: WorldObject | null = null
  private target: WorldObject | null = null
  private particles: Particle[] = []
  private floaters: Floater[] = []
  private shake: { id: string; t: number } | null = null
  private flash: { id: string; t: number; color: string } | null = null
  private swing = 0
  private view: ViewState = { nodes: {}, hasPickaxe: false }

  constructor(
    private canvas: HTMLCanvasElement,
    private cb: EngineCallbacks = {},
    private opts: EngineOptions = { interactive: true },
  ) {
    this.ctx = canvas.getContext('2d')!
    this.reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    this.ro = new ResizeObserver(() => this.resize())
    this.ro.observe(canvas)
    this.resize()
    const p = this.project(this.player.x + 0.5, this.player.y + 0.5, 0)
    this.cam = { x: p.x, y: p.y }
    if (opts.interactive) {
      window.addEventListener('keydown', this.onKeyDown)
      window.addEventListener('keyup', this.onKeyUp)
      canvas.addEventListener('pointermove', this.onPointerMove)
      canvas.addEventListener('pointerleave', this.onPointerLeave)
      canvas.addEventListener('click', this.onClick)
    }
    this.raf = requestAnimationFrame(this.frame)
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    this.ro.disconnect()
    window.removeEventListener('keydown', this.onKeyDown)
    window.removeEventListener('keyup', this.onKeyUp)
    this.canvas.removeEventListener('pointermove', this.onPointerMove)
    this.canvas.removeEventListener('pointerleave', this.onPointerLeave)
    this.canvas.removeEventListener('click', this.onClick)
  }

  setView(view: ViewState) {
    this.view = view
  }

  /** Swing animation while waiting for the backend's verdict. */
  startSwing() {
    this.swing = 1
  }

  feedback(objId: string, kind: 'success' | 'fail' | 'info', text: string) {
    const o = objects.find((ob) => ob.id === objId)
    if (!o) return
    const z = tileAt(o.x, o.y)!.z
    this.floaters.push({
      x: o.x + 0.5,
      y: o.y + 0.5,
      z: z + 3,
      text,
      color: kind === 'success' ? '#ffc107' : kind === 'fail' ? '#ff6b61' : '#fffdf5',
      life: 1.6,
    })
    if (kind === 'success') {
      this.flash = { id: objId, t: 0.5, color: 'rgba(255,193,7,0.8)' }
      if (!this.reduced) {
        for (let i = 0; i < 14; i++) {
          this.particles.push({
            x: o.x + 0.5,
            y: o.y + 0.5,
            z: z + 1.2,
            vx: (Math.random() - 0.5) * 2.2,
            vy: (Math.random() - 0.5) * 2.2,
            vz: 2 + Math.random() * 3,
            life: 0.9,
            max: 0.9,
            color: i % 3 === 0 ? '#ffc107' : '#d9783b',
            size: 3 + Math.random() * 3,
          })
        }
      }
    } else if (kind === 'fail') {
      this.flash = { id: objId, t: 0.5, color: 'rgba(229,83,75,0.75)' }
      if (!this.reduced) this.shake = { id: objId, t: 0.4 }
    }
  }

  // ---------- projection ----------

  private project(x: number, y: number, z: number) {
    return { x: ((x - y) * TW) / 2, y: ((x + y) * TH) / 2 - z * ZH }
  }

  private toScreen(x: number, y: number, z: number) {
    const p = this.project(x, y, z)
    return { x: p.x - this.cam.x + this.w / 2, y: p.y - this.cam.y + this.h / 2 }
  }

  private resize() {
    const rect = this.canvas.getBoundingClientRect()
    this.dpr = Math.min(window.devicePixelRatio || 1, 2)
    this.w = rect.width
    this.h = rect.height
    this.canvas.width = Math.round(rect.width * this.dpr)
    this.canvas.height = Math.round(rect.height * this.dpr)
  }

  private playerPos() {
    const pl = this.player
    const e = pl.p
    const x = pl.fromX + (pl.x - pl.fromX) * e
    const y = pl.fromY + (pl.y - pl.fromY) * e
    const z = tileAt(pl.fromX, pl.fromY)!.z + (tileAt(pl.x, pl.y)!.z - tileAt(pl.fromX, pl.fromY)!.z) * e
    return { x, y, z }
  }

  // ---------- input ----------

  private onKeyDown = (e: KeyboardEvent) => {
    const el = e.target as HTMLElement | null
    if (el && (el.isContentEditable || /INPUT|TEXTAREA|SELECT/.test(el.tagName))) return
    const k = e.key.toLowerCase()
    if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) {
      e.preventDefault()
      this.keys.add(k)
      this.path = []
      this.pendingInteract = null
      // Step on the press itself so quick taps register; holding keeps walking via update().
      if (!e.repeat && this.player.p >= 1) {
        const [dx, dy] = ({ w: [0, -1], arrowup: [0, -1], s: [0, 1], arrowdown: [0, 1], a: [-1, 0], arrowleft: [-1, 0], d: [1, 0], arrowright: [1, 0] } as Record<string, [number, number]>)[k]
        this.tryStep(dx, dy)
      }
    } else if (k === 'e' || k === ' ') {
      e.preventDefault()
      if (this.target) this.cb.onInteract?.(this.target)
    }
  }

  private onKeyUp = (e: KeyboardEvent) => {
    this.keys.delete(e.key.toLowerCase())
  }

  private pick(clientX: number, clientY: number): { tile: Vec | null; obj: WorldObject | null } {
    const rect = this.canvas.getBoundingClientRect()
    const mx = clientX - rect.left
    const my = clientY - rect.top
    // Objects first, front-most wins.
    const sorted = [...objects].sort((a, b) => b.x + b.y - (a.x + a.y))
    for (const o of sorted) {
      const z = tileAt(o.x, o.y)!.z
      const c = this.toScreen(o.x + 0.5, o.y + 0.5, z)
      const tall = o.kind === 'tree' ? 70 : o.kind === 'npc' ? 46 : 36
      if (mx > c.x - 22 && mx < c.x + 22 && my > c.y - tall && my < c.y + 8) return { tile: null, obj: o }
    }
    for (let s = MAP_W + MAP_H - 2; s >= 0; s--) {
      for (let x = Math.min(s, MAP_W - 1); x >= 0 && s - x < MAP_H; x--) {
        const y = s - x
        const t = tiles[y][x]
        const c = this.toScreen(x + 0.5, y + 0.5, t.terrain === 'w' ? -0.3 : t.z)
        if (Math.abs(mx - c.x) / (TW / 2) + Math.abs(my - c.y) / (TH / 2) <= 1) return { tile: { x, y }, obj: null }
      }
    }
    return { tile: null, obj: null }
  }

  private onPointerMove = (e: PointerEvent) => {
    const hit = this.pick(e.clientX, e.clientY)
    this.hover = hit.tile
    this.hoverObj = hit.obj
    this.canvas.style.cursor = hit.obj?.action ? 'pointer' : 'default'
  }

  private onPointerLeave = () => {
    this.hover = null
    this.hoverObj = null
  }

  private onClick = (e: MouseEvent) => {
    const hit = this.pick(e.clientX, e.clientY)
    if (hit.obj) {
      const o = hit.obj
      if (this.isAdjacent(o) && this.player.p >= 1) {
        this.faceTowards(o)
        if (o.action) this.cb.onInteract?.(o)
        return
      }
      // Walk to the nearest reachable neighbour, then interact.
      let best: Vec[] | null = null
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]]) {
        const p = findPath(this.player, { x: o.x + dx, y: o.y + dy })
        if (p && (!best || p.length < best.length)) best = p
      }
      if (best) {
        this.path = best
        this.pendingInteract = o.action ? o : null
      }
    } else if (hit.tile && isWalkable(hit.tile.x, hit.tile.y)) {
      this.path = findPath(this.player, hit.tile) ?? []
      this.pendingInteract = null
    }
  }

  private isAdjacent(o: WorldObject) {
    return Math.max(Math.abs(o.x - this.player.x), Math.abs(o.y - this.player.y)) === 1
  }

  private faceTowards(o: WorldObject) {
    this.player.dir = { x: Math.sign(o.x - this.player.x), y: Math.sign(o.y - this.player.y) }
  }

  // ---------- update ----------

  private tryStep(dx: number, dy: number) {
    const pl = this.player
    pl.dir = { x: dx, y: dy }
    const nx = pl.x + dx
    const ny = pl.y + dy
    if (!isWalkable(nx, ny)) return false
    if (Math.abs(tileAt(nx, ny)!.z - tileAt(pl.x, pl.y)!.z) > 1) return false
    pl.fromX = pl.x
    pl.fromY = pl.y
    pl.x = nx
    pl.y = ny
    pl.p = 0
    return true
  }

  private update(dt: number) {
    this.t += dt
    const pl = this.player

    if (pl.p < 1) {
      pl.p = Math.min(1, pl.p + (dt * 1000) / STEP_MS)
    }
    if (pl.p >= 1) {
      if (this.path.length) {
        const n = this.path.shift()!
        this.tryStep(n.x - pl.x, n.y - pl.y)
      } else if (this.pendingInteract) {
        const o = this.pendingInteract
        this.pendingInteract = null
        if (this.isAdjacent(o)) {
          this.faceTowards(o)
          this.cb.onInteract?.(o)
        }
      } else {
        const k = this.keys
        if (k.has('w') || k.has('arrowup')) this.tryStep(0, -1)
        else if (k.has('s') || k.has('arrowdown')) this.tryStep(0, 1)
        else if (k.has('a') || k.has('arrowleft')) this.tryStep(-1, 0)
        else if (k.has('d') || k.has('arrowright')) this.tryStep(1, 0)
      }
    }

    // Interaction target: prefer the object we're facing, else any adjacent.
    if (this.opts.interactive) {
      const adj = objects.filter((o) => o.action && this.isAdjacent(o) && pl.p >= 1)
      const facing = adj.find((o) => o.x === pl.x + pl.dir.x && o.y === pl.y + pl.dir.y)
      const next = facing ?? adj.find((o) => o.action !== 'inspect') ?? adj[0] ?? null
      if (next !== this.target) {
        this.target = next
        this.cb.onTargetChange?.(next)
      }
    }

    // Camera follows the player (or drifts gently on the title screen).
    const pp = this.playerPos()
    let goal = this.project(pp.x + 0.5, pp.y + 0.5, pp.z)
    if (!this.opts.interactive) {
      const c = this.project(MAP_W / 2, MAP_H / 2 - 1, 0)
      const drift = this.reduced ? 0 : Math.sin(this.t * 0.15) * 40
      goal = { x: c.x + drift, y: c.y }
    }
    const k = 1 - Math.pow(0.001, dt)
    this.cam.x += (goal.x - this.cam.x) * k
    this.cam.y += (goal.y - this.cam.y) * k

    if (this.swing > 0) this.swing = Math.max(0, this.swing - dt * 2.2)
    if (this.shake) this.shake.t -= dt
    if (this.shake && this.shake.t <= 0) this.shake = null
    if (this.flash) this.flash.t -= dt
    if (this.flash && this.flash.t <= 0) this.flash = null

    for (const p of this.particles) {
      p.x += p.vx * dt
      p.y += p.vy * dt
      p.z += p.vz * dt
      p.vz -= 9 * dt
      p.life -= dt
    }
    this.particles = this.particles.filter((p) => p.life > 0)
    for (const f of this.floaters) {
      f.z += dt * 1.6
      f.life -= dt
    }
    this.floaters = this.floaters.filter((f) => f.life > 0)
  }

  // ---------- drawing ----------

  private frame = (now: number) => {
    const dt = this.last ? Math.min(0.05, (now - this.last) / 1000) : 0.016
    this.last = now
    this.update(dt)
    this.draw()
    this.raf = requestAnimationFrame(this.frame)
  }

  private poly(pts: Vec[], fill: string, stroke?: string) {
    const c = this.ctx
    c.beginPath()
    c.moveTo(pts[0].x, pts[0].y)
    for (let i = 1; i < pts.length; i++) c.lineTo(pts[i].x, pts[i].y)
    c.closePath()
    c.fillStyle = fill
    c.fill()
    if (stroke) {
      c.strokeStyle = stroke
      c.lineWidth = 1
      c.stroke()
    }
  }

  /** An axis-aligned voxel box standing on world point (x, y, z). Footprint in tiles, height in px. */
  private box(x: number, y: number, z: number, w: number, d: number, hPx: number, color: string, lift = 0) {
    const hz = hPx / ZH
    const lz = lift / ZH
    const x0 = x - w / 2
    const x1 = x + w / 2
    const y0 = y - d / 2
    const y1 = y + d / 2
    const top = z + lz + hz
    const bot = z + lz
    const S = (a: number, b: number, c: number) => this.toScreen(a, b, c)
    this.poly([S(x0, y1, top), S(x1, y1, top), S(x1, y1, bot), S(x0, y1, bot)], shade(color, -0.18))
    this.poly([S(x1, y0, top), S(x1, y1, top), S(x1, y1, bot), S(x1, y0, bot)], shade(color, -0.34))
    this.poly([S(x0, y0, top), S(x1, y0, top), S(x1, y1, top), S(x0, y1, top)], color)
  }

  private draw() {
    const c = this.ctx
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)

    // Sky / void
    const g = c.createLinearGradient(0, 0, 0, this.h)
    g.addColorStop(0, '#2a2620')
    g.addColorStop(1, '#1e1e1e')
    c.fillStyle = g
    c.fillRect(0, 0, this.w, this.h)

    const pp = this.playerPos()
    const playerCell = { x: Math.round(Math.max(pp.x, this.player.x)), y: Math.round(Math.max(pp.y, this.player.y)) }
    const objAt = new Map(objects.map((o) => [`${o.x},${o.y}`, o]))

    // Back-to-front by diagonal so tall terrain correctly hides what's behind it.
    for (let s = 0; s <= MAP_W + MAP_H - 2; s++) {
      for (let x = 0; x <= s; x++) {
        const y = s - x
        if (x >= MAP_W || y >= MAP_H) continue
        this.drawTile(x, y)
        const o = objAt.get(`${x},${y}`)
        if (o) this.drawObject(o)
        if (playerCell.x === x && playerCell.y === y) this.drawPlayer(pp)
      }
    }

    this.drawCampfireGlow()

    for (const p of this.particles) {
      const s = this.toScreen(p.x, p.y, p.z)
      c.globalAlpha = Math.max(0, p.life / p.max)
      c.fillStyle = p.color
      c.fillRect(s.x - p.size / 2, s.y - p.size / 2, p.size, p.size)
    }
    c.globalAlpha = 1

    c.textAlign = 'center'
    c.font = '700 16px "Pixelify Sans", sans-serif'
    for (const f of this.floaters) {
      const s = this.toScreen(f.x, f.y, f.z)
      c.globalAlpha = Math.min(1, f.life)
      c.lineWidth = 4
      c.strokeStyle = '#1e1e1e'
      c.strokeText(f.text, s.x, s.y)
      c.fillStyle = f.color
      c.fillText(f.text, s.x, s.y)
    }
    c.globalAlpha = 1

    // Warm vignette
    const v = c.createRadialGradient(this.w / 2, this.h / 2, Math.min(this.w, this.h) * 0.35, this.w / 2, this.h / 2, Math.max(this.w, this.h) * 0.75)
    v.addColorStop(0, 'rgba(30,20,10,0)')
    v.addColorStop(1, 'rgba(20,12,4,0.45)')
    c.fillStyle = v
    c.fillRect(0, 0, this.w, this.h)
  }

  private drawTile(x: number, y: number) {
    const t = tiles[y][x]
    const water = t.terrain === 'w'
    const zTop = water ? -0.3 + Math.sin(this.t * 1.5 + x + y) * (this.reduced ? 0 : 0.04) : t.z
    const palette = TERRAIN_COLORS[t.terrain]
    const top = palette[Math.floor(hash(x, y) * palette.length)]
    const S = (a: number, b: number, z: number) => this.toScreen(a, b, z)
    const bottom = -BASE / ZH - 0.4

    // Only draw sides that face the camera and aren't covered by a neighbour.
    const front = tileAt(x, y + 1)
    const right = tileAt(x + 1, y)
    const frontZ = front ? (front.terrain === 'w' ? -0.3 : front.z) : bottom
    const rightZ = right ? (right.terrain === 'w' ? -0.3 : right.z) : bottom
    if (frontZ < zTop) {
      this.poly([S(x, y + 1, zTop), S(x + 1, y + 1, zTop), S(x + 1, y + 1, frontZ), S(x, y + 1, frontZ)], shade(SIDE[t.terrain], -0.05))
    }
    if (rightZ < zTop) {
      this.poly([S(x + 1, y, zTop), S(x + 1, y + 1, zTop), S(x + 1, y + 1, rightZ), S(x + 1, y, rightZ)], shade(SIDE[t.terrain], -0.25))
    }
    // Grass gets a thin green lip over the dirt side.
    if (t.terrain === 'g' && frontZ < zTop) {
      this.poly([S(x, y + 1, zTop), S(x + 1, y + 1, zTop), S(x + 1, y + 1, zTop - 0.25), S(x, y + 1, zTop - 0.25)], '#5f9a33')
    }

    this.poly([S(x, y, zTop), S(x + 1, y, zTop), S(x + 1, y + 1, zTop), S(x, y + 1, zTop)], top)

    // Pixel details
    const c = this.ctx
    const h = hash(x * 3.1, y * 7.7)
    if (t.terrain === 'g' && h > 0.55) {
      const p = S(x + 0.3 + h * 0.4, y + 0.3 + (1 - h) * 0.4, zTop)
      c.fillStyle = '#5e9530'
      c.fillRect(p.x - 3, p.y - 3, 2, 3)
      c.fillRect(p.x + 1, p.y - 4, 2, 4)
      if (h > 0.85) {
        c.fillStyle = h > 0.92 ? '#ffc107' : '#fffdf5'
        c.fillRect(p.x + 6, p.y - 2, 3, 3)
      }
    } else if (t.terrain === 's' && h > 0.4) {
      const p = S(x + 0.25 + h * 0.5, y + 0.5, zTop)
      c.fillStyle = '#87837b'
      c.fillRect(p.x - 4, p.y - 1, 6, 2)
    } else if (t.terrain === 'w' && h > 0.6 && !this.reduced) {
      const p = S(x + 0.5, y + 0.5, zTop)
      c.globalAlpha = 0.5 + Math.sin(this.t * 2 + h * 10) * 0.3
      c.fillStyle = '#a9d8f5'
      c.fillRect(p.x - 6, p.y, 8, 2)
      c.globalAlpha = 1
    } else if (t.terrain === 'd' && h > 0.5) {
      const p = S(x + 0.4, y + 0.6, zTop)
      c.fillStyle = '#a97f47'
      c.fillRect(p.x, p.y, 3, 2)
    }

    if (this.hover && this.hover.x === x && this.hover.y === y && !water) {
      this.poly([S(x, y, zTop), S(x + 1, y, zTop), S(x + 1, y + 1, zTop), S(x, y + 1, zTop)], 'rgba(255,253,245,0.18)', 'rgba(255,253,245,0.7)')
    }
  }

  private highlight(o: WorldObject) {
    if (o !== this.target && o !== this.hoverObj) return
    const z = tileAt(o.x, o.y)!.z
    const S = (a: number, b: number) => this.toScreen(a, b, z)
    const pulse = this.reduced ? 0.6 : 0.45 + Math.sin(this.t * 5) * 0.25
    this.ctx.lineWidth = 2
    this.poly(
      [S(o.x + 0.05, o.y + 0.05), S(o.x + 0.95, o.y + 0.05), S(o.x + 0.95, o.y + 0.95), S(o.x + 0.05, o.y + 0.95)],
      `rgba(255,193,7,${pulse * 0.35})`,
      `rgba(255,193,7,${pulse + 0.3})`,
    )
  }

  private drawObject(o: WorldObject) {
    this.highlight(o)
    const z = tileAt(o.x, o.y)!.z
    let cx = o.x + 0.5
    const cy = o.y + 0.5
    if (this.shake?.id === o.id) cx += Math.sin(this.shake.t * 60) * 0.04

    switch (o.kind) {
      case 'tree': {
        const sway = this.reduced ? 0 : Math.sin(this.t * 1.2 + o.x) * 0.015
        this.box(cx, cy, z, 0.18, 0.18, 18, '#7a5230')
        this.box(cx + sway, cy, z, 0.72, 0.72, 20, '#3f7d2c', 14)
        this.box(cx + sway * 1.5, cy, z, 0.52, 0.52, 16, '#4c9135', 34)
        this.box(cx + sway * 2, cy, z, 0.28, 0.28, 12, '#5aa23e', 50)
        break
      }
      case 'rock':
        this.box(cx, cy, z, 0.55, 0.5, 13, '#8f8b84')
        this.box(cx + 0.1, cy - 0.05, z, 0.3, 0.3, 8, '#a19d95', 13)
        break
      case 'ore': {
        const remaining = this.view.nodes[o.id]?.remaining ?? 1
        if (remaining <= 0) {
          this.box(cx, cy, z, 0.6, 0.55, 6, '#7f7b74')
          this.box(cx - 0.15, cy + 0.1, z, 0.2, 0.2, 5, '#8c6a55', 6)
          break
        }
        this.box(cx, cy, z, 0.7, 0.66, 22, '#7d7973')
        this.box(cx - 0.05, cy, z, 0.42, 0.42, 10, '#8a8680', 22)
        // Copper veins on the visible faces
        const c = this.ctx
        const sparkle = this.reduced ? 1 : 0.75 + Math.sin(this.t * 3 + o.x) * 0.25
        for (const [fx, fy, fz] of [[0.2, 0.33, 0.55], [0.45, 0.33, 1.0], [0.35, 0.33, 0.25], [0.35, 0.05, 0.8], [0.35, -0.2, 0.4]]) {
          const p = this.toScreen(cx - 0.35 + fx, cy + fy, z + fz)
          c.fillStyle = shade('#d9783b', (sparkle - 1) * 0.6)
          c.fillRect(p.x - 3, p.y - 2, 5, 4)
          c.fillStyle = '#ffc107'
          c.fillRect(p.x - 1, p.y - 2, 2, 2)
        }
        break
      }
      case 'crate': {
        this.box(cx, cy, z, 0.5, 0.5, 16, this.view.hasPickaxe ? '#8a6238' : '#a8743f')
        const c = this.ctx
        const a = this.toScreen(cx - 0.25, cy + 0.25, z + 0.5)
        const b = this.toScreen(cx + 0.25, cy + 0.25, z + 0.5)
        c.strokeStyle = '#6d4a26'
        c.lineWidth = 2
        c.beginPath()
        c.moveTo(a.x, a.y)
        c.lineTo(b.x, b.y)
        c.stroke()
        if (!this.view.hasPickaxe) {
          const bob = this.reduced ? 0 : Math.sin(this.t * 3) * 3
          const p = this.toScreen(cx, cy, z + 2.2)
          this.drawPickaxeIcon(p.x, p.y + bob)
        }
        break
      }
      case 'campfire': {
        for (const [dx, dy] of [[-0.15, 0], [0.15, 0], [0, -0.15], [0, 0.15]]) this.box(cx + dx, cy + dy, z, 0.14, 0.14, 5, '#6b4a2b')
        const f = this.reduced ? 1 : 0.8 + Math.sin(this.t * 13) * 0.12 + Math.sin(this.t * 7.3) * 0.08
        this.box(cx, cy, z, 0.24 * f, 0.24 * f, 12 * f, '#ff9800', 4)
        this.box(cx, cy, z, 0.13 * f, 0.13 * f, 9 * f, '#ffc107', 10)
        break
      }
      case 'tent': {
        const c = this.ctx
        const S = (a: number, b: number, h: number) => this.toScreen(a, b, z + h)
        const x0 = o.x + 0.1
        const x1 = o.x + 0.9
        const y0 = o.y + 0.15
        const y1 = o.y + 0.85
        const ym = (y0 + y1) / 2
        this.poly([S(x0, y1, 0), S(x1, y1, 0), S(x1, ym, 2.4), S(x0, ym, 2.4)], '#e88a1a')
        this.poly([S(x1, y0, 0), S(x1, y1, 0), S(x1, ym, 2.4)], '#b8650c')
        const door = S(x1, ym, 0)
        c.fillStyle = '#5a3208'
        c.beginPath()
        c.moveTo(door.x - 6, door.y + 2)
        c.lineTo(door.x, door.y - 16)
        c.lineTo(door.x + 6, door.y - 1)
        c.fill()
        break
      }
      case 'npc':
        this.drawCharacter(cx, cy, z, { shirt: '#4b7bb5', hat: '#5b4636', bob: Math.sin(this.t * 2) * 1 })
        {
          const p = this.toScreen(cx, cy, z + 4.2)
          this.ctx.font = '700 15px "Pixelify Sans", sans-serif'
          this.ctx.textAlign = 'center'
          this.ctx.fillStyle = '#ffc107'
          this.ctx.fillText('!', p.x, p.y + (this.reduced ? 0 : Math.sin(this.t * 4) * 2))
        }
        break
      case 'gate':
        this.box(cx, cy - 0.35, z, 0.16, 0.16, 34, '#5b4636')
        this.box(cx, cy + 0.35, z, 0.16, 0.16, 34, '#5b4636')
        for (const h of [8, 18, 28]) this.box(cx, cy, z, 0.08, 0.6, 4, '#7a5d44', h)
        this.box(cx - 0.02, cy, z, 0.1, 0.14, 8, '#ffc107', 14)
        break
      case 'smelter': {
        this.box(cx, cy, z, 0.8, 0.75, 24, '#8c7b6b')
        this.box(cx, cy, z, 0.5, 0.5, 14, '#7a6a5b', 24)
        this.box(cx, cy, z, 0.18, 0.18, 12, '#5a4c40', 38)
        const p = this.toScreen(cx, cy + 0.38, z + 0.6)
        this.ctx.fillStyle = '#2a201a'
        this.ctx.fillRect(p.x - 8, p.y - 6, 12, 9)
        break
      }
    }

    if (this.flash?.id === o.id) {
      const p = this.toScreen(cx, cy, z + 1)
      this.ctx.globalAlpha = Math.max(0, this.flash.t * 2)
      const rg = this.ctx.createRadialGradient(p.x, p.y, 2, p.x, p.y, 40)
      rg.addColorStop(0, this.flash.color)
      rg.addColorStop(1, 'rgba(0,0,0,0)')
      this.ctx.fillStyle = rg
      this.ctx.fillRect(p.x - 40, p.y - 40, 80, 80)
      this.ctx.globalAlpha = 1
    }
  }

  private drawPickaxeIcon(x: number, y: number) {
    const c = this.ctx
    c.save()
    c.translate(x, y)
    c.rotate(-0.6)
    c.fillStyle = '#7a5230'
    c.fillRect(-2, -10, 4, 20)
    c.fillStyle = '#b0aca4'
    c.fillRect(-10, -12, 20, 5)
    c.fillStyle = '#d6d2ca'
    c.fillRect(-10, -12, 20, 2)
    c.restore()
  }

  private drawCharacter(x: number, y: number, z: number, look: { shirt: string; hat: string; bob: number; tool?: boolean; swing?: number }) {
    const b = this.reduced ? 0 : look.bob
    this.box(x - 0.08, y, z, 0.12, 0.14, 10, '#3b2f28')
    this.box(x + 0.08, y, z, 0.12, 0.14, 10, '#3b2f28')
    this.box(x, y, z, 0.34, 0.24, 15, look.shirt, 10 + b)
    this.box(x, y, z, 0.28, 0.28, 13, '#f1c27d', 25 + b)
    this.box(x, y, z, 0.34, 0.34, 5, look.hat, 37 + b)
    if (look.tool) {
      const c = this.ctx
      const p = this.toScreen(x + 0.15, y + 0.2, z + 1.4 + b / ZH)
      c.save()
      c.translate(p.x, p.y)
      c.rotate(-0.4 + (look.swing ?? 0) * 1.9 * Math.sin((look.swing ?? 0) * Math.PI))
      c.fillStyle = '#7a5230'
      c.fillRect(-1.5, -16, 3, 16)
      c.fillStyle = '#b0aca4'
      c.fillRect(-8, -19, 16, 4)
      c.restore()
    }
  }

  private drawPlayer(pp: { x: number; y: number; z: number }) {
    const moving = this.player.p < 1
    const S = this.toScreen(pp.x + 0.5, pp.y + 0.5, pp.z)
    // shadow
    this.ctx.fillStyle = 'rgba(0,0,0,0.25)'
    this.ctx.beginPath()
    this.ctx.ellipse(S.x, S.y, 12, 6, 0, 0, Math.PI * 2)
    this.ctx.fill()
    this.drawCharacter(pp.x + 0.5, pp.y + 0.5, pp.z, {
      shirt: '#2f8f83',
      hat: '#ff9800',
      bob: moving ? Math.abs(Math.sin(this.player.p * Math.PI)) * 3 : Math.sin(this.t * 2) * 0.8,
      tool: this.view.hasPickaxe,
      swing: this.swing,
    })
  }

  private drawCampfireGlow() {
    const fire = objects.find((o) => o.kind === 'campfire')!
    const p = this.toScreen(fire.x + 0.5, fire.y + 0.5, 0.5)
    const f = this.reduced ? 1 : 0.92 + Math.sin(this.t * 9) * 0.05
    const c = this.ctx
    c.globalCompositeOperation = 'lighter'
    const rg = c.createRadialGradient(p.x, p.y, 4, p.x, p.y, 150 * f)
    rg.addColorStop(0, 'rgba(255,152,0,0.30)')
    rg.addColorStop(0.5, 'rgba(255,120,0,0.08)')
    rg.addColorStop(1, 'rgba(0,0,0,0)')
    c.fillStyle = rg
    c.fillRect(p.x - 160, p.y - 160, 320, 320)
    c.globalCompositeOperation = 'source-over'
  }
}
