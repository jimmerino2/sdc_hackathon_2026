// Data-driven mission definitions for World 1. The evaluation tests themselves
// live with the trusted backend; `tests` here is the learner-facing description
// of each one, keyed by the same id the runner reports.

import type { ErrorCategory, GameCommand, HttpMethod } from '@/api/types'

export type Block =
  | { kind: 'p'; text: string }
  | { kind: 'code'; text: string; caption?: string }
  | { kind: 'output'; text: string; caption?: string }
  | { kind: 'term'; term: string; text: string }

export interface MissionTest {
  id: string
  name: string
  /** Shown before the test is run so the learner knows what is checked. */
  expects: string
}

export interface RequestExample {
  label: string
  method: HttpMethod
  path: string
  body?: unknown
  query?: Record<string, string>
}

export interface Mission {
  id: string
  world: number
  chapter: string
  order: number
  title: string
  concept: string
  icon: string
  narrative: string
  objective: string
  prerequisites: string[]
  lesson: Block[]
  task: string[]
  starterCode: string
  tests: MissionTest[]
  hints: string[]
  /** Companion feedback for a specific failing test or error category. */
  feedback: Partial<Record<string, string>> & Partial<Record<ErrorCategory, string>>
  xp: number
  achievementOnComplete?: string
  /** Missions this one unlocks once completed. */
  unlocks: string[]
  /** Teaser of how this connects to the world. */
  frontierLink: string
  /** Present when this mission's code powers a Frontier action. */
  game?: { command: GameCommand; label: string }
  /** Present when the mission's code is a web app the Workshop can call. */
  workshop?: { examples: RequestExample[] }
  /** Placeholder node for content that is not built yet. */
  comingSoon?: boolean
}

export const WORLD_1 = {
  id: 1,
  title: 'The First Expedition',
  blurb:
    'Your camp sits at the edge of the Frontier. Learn enough Python to bring its old mining rig back to life.',
}

export const missions: Mission[] = [
  {
    id: 'w1-satchel',
    world: 1,
    chapter: 'Making camp',
    order: 1,
    title: 'Packing the Satchel',
    concept: 'Variables & values',
    icon: '🎒',
    narrative:
      "Before anyone leaves camp, the quartermaster wants a record of who you are and what you're carrying. In Python, records like that start with variables.",
    objective: 'Store text, numbers and true/false values in variables.',
    prerequisites: [],
    lesson: [
      {
        kind: 'p',
        text: 'A **variable** is a name that points at a value. You create one with `=`: the name goes on the left, the value on the right.',
      },
      { kind: 'code', text: 'camp_name = "Ember Hollow"\ntorches = 4\nis_raining = False' },
      { kind: 'term', term: 'String', text: 'Text, written inside quotes: `"Ember Hollow"`.' },
      { kind: 'term', term: 'Integer', text: 'A whole number, no quotes: `4`.' },
      {
        kind: 'term',
        term: 'Boolean',
        text: 'Either `True` or `False`. The capital letter matters in Python.',
      },
      {
        kind: 'p',
        text: 'Once a value has a name, you can use the name anywhere you would use the value. `print()` shows a value on screen:',
      },
      { kind: 'code', text: 'print(camp_name)\nprint(torches + 1)' },
      { kind: 'output', text: 'Ember Hollow\n5', caption: 'Output' },
    ],
    task: [
      'Set `explorer_name` to your name, as a string.',
      'Set `rations` to the number `3`.',
      'Set `has_map` to `True`.',
    ],
    starterCode: `# Fill in the three values below.
# Text goes in quotes. Numbers and True/False do not.

explorer_name = ___
rations = ___
has_map = ___
`,
    tests: [
      { id: 'name_is_text', name: 'explorer_name is a string', expects: 'Any text in quotes, not empty.' },
      { id: 'rations_is_three', name: 'rations equals 3', expects: 'The integer 3 — no quotes.' },
      { id: 'has_map_true', name: 'has_map is True', expects: 'The Boolean True.' },
    ],
    hints: [
      'Each `___` is a blank you replace with a value.',
      'Strings need quotes: `"Robin"`. Numbers do not: `3`.',
      'Booleans are written exactly `True` or `False`, with a capital first letter.',
    ],
    feedback: {
      syntax: "Python couldn't even read that. Check the line it points at — usually a missing quote.",
      name: 'Python saw a word it doesn\'t know. Did you leave a `___` in, or forget the quotes around your name?',
      rations_is_three: 'Close. If you wrote `"3"` in quotes, that is text, not a number.',
      has_map_true: '`true` and `True` are different things to Python. Capitals matter.',
    },
    xp: 40,
    unlocks: ['w1-rocks'],
    frontierLink: 'The quartermaster will hand you camp supplies once your record is filed.',
  },
  {
    id: 'w1-rocks',
    world: 1,
    chapter: 'Making camp',
    order: 2,
    title: 'Reading the Rocks',
    concept: 'Functions & conditions',
    icon: '🪨',
    narrative:
      'Surveyor Marlo has a rule: never swing at a rock you can\'t break. Teach the camp\'s rig how to make that decision.',
    objective: 'Write a function that makes a yes/no decision with `if`.',
    prerequisites: ['w1-satchel'],
    lesson: [
      {
        kind: 'p',
        text: 'A **function** is a reusable recipe. It takes inputs called **parameters**, does some work, and hands back a result with `return`.',
      },
      { kind: 'code', text: 'def double(n):\n    return n * 2\n\nprint(double(5))' },
      { kind: 'output', text: '10', caption: 'Output' },
      {
        kind: 'p',
        text: '`if` lets a function choose. `==` asks "are these equal?" (one `=` assigns, two compare). `and` needs both sides to be true.',
      },
      {
        kind: 'code',
        text: 'def can_cross(river, has_boat):\n    if river == "shallow" or has_boat:\n        return True\n    return False',
      },
      {
        kind: 'p',
        text: 'Indentation matters: the four spaces under `if` mark which lines belong to it.',
      },
    ],
    task: [
      'Complete `can_mine(resource, tool)`.',
      'Return `True` only when `resource` is `"copper"` **and** `tool` is `"stone_pickaxe"`.',
      'Return `False` for every other combination.',
    ],
    starterCode: `def can_mine(resource, tool):
    # Return True only for copper mined with a stone_pickaxe.
    if ___:
        return True
    return False
`,
    tests: [
      { id: 'copper_with_pickaxe', name: 'copper + stone_pickaxe → True', expects: 'can_mine("copper", "stone_pickaxe") is True' },
      { id: 'copper_with_hands', name: 'copper + hands → False', expects: 'can_mine("copper", "hands") is False' },
      { id: 'other_resource', name: 'unknown rock → False', expects: 'can_mine("diamond", "stone_pickaxe") is False' },
    ],
    hints: [
      'You need two comparisons joined together: one about `resource`, one about `tool`.',
      'Compare with `==` and join with `and`.',
      'The condition looks like `resource == "copper" and tool == ...`.',
    ],
    feedback: {
      copper_with_hands: 'Your rig swings at copper with bare hands. Ouch. Did you check the tool too?',
      other_resource: "It said yes to a rock it shouldn't. Is the resource part of your condition?",
      missing_return: 'Your function finished without handing anything back. Every path needs a `return`.',
      syntax: 'Something about the shape of the code is off — check the colon after `if` and the indentation.',
    },
    xp: 50,
    unlocks: ['w1-ledger'],
    frontierLink: 'This exact decision will guard the mining rig later.',
  },
  {
    id: 'w1-ledger',
    world: 1,
    chapter: 'Making camp',
    order: 3,
    title: "The Surveyor's Ledger",
    concept: 'Dictionaries',
    icon: '📒',
    narrative:
      "Marlo's ledger lists which tool each ore needs. Hard-coding every ore in `if` statements won't scale — time for a lookup table.",
    objective: 'Store pairs of related data in a dictionary and look values up safely.',
    prerequisites: ['w1-rocks'],
    lesson: [
      {
        kind: 'p',
        text: 'A **dictionary** maps keys to values, inside curly braces. Look a value up with square brackets.',
      },
      { kind: 'code', text: 'prices = {"rope": 5, "lantern": 12}\nprint(prices["rope"])' },
      { kind: 'output', text: '5', caption: 'Output' },
      {
        kind: 'p',
        text: 'Asking for a key that isn\'t there crashes with a `KeyError`. Check first with `in`, or use `.get()`, which returns `None` instead of crashing.',
      },
      { kind: 'code', text: 'print("rope" in prices)\nprint(prices.get("compass"))' },
      { kind: 'output', text: 'True\nNone', caption: 'Output' },
    ],
    task: [
      'Add `"tin": "stone_pickaxe"` to the `REQUIRED_TOOL` dictionary.',
      'Complete `required_tool(resource)` so it returns the tool for a known resource.',
      'For an unknown resource, return `None` instead of crashing.',
    ],
    starterCode: `REQUIRED_TOOL = {
    "copper": "stone_pickaxe",
    # add tin here
}


def required_tool(resource):
    # Return the tool needed for this resource, or None if unknown.
    ___
`,
    tests: [
      { id: 'copper_lookup', name: 'copper needs a stone_pickaxe', expects: 'required_tool("copper") == "stone_pickaxe"' },
      { id: 'tin_added', name: 'tin is in the ledger', expects: 'REQUIRED_TOOL["tin"] == "stone_pickaxe"' },
      { id: 'unknown_is_none', name: 'unknown ore returns None', expects: 'required_tool("mithril") is None — no crash' },
    ],
    hints: [
      'Entries are separated by commas: `"key": "value",`.',
      '`REQUIRED_TOOL.get(resource)` already returns `None` for missing keys.',
      "Don't forget the word `return` in front of it.",
    ],
    feedback: {
      unknown_is_none: 'Asking for an unknown ore crashed. `.get()` is the polite way to ask.',
      tin_added: 'Tin is missing from the ledger. Check the comma between entries.',
      missing_return: 'You looked the value up but never handed it back. `return` it.',
    },
    xp: 50,
    unlocks: ['w1-signal'],
    frontierLink: "The mining route will read straight from this ledger.",
  },
  {
    id: 'w1-signal',
    world: 1,
    chapter: 'The Lost Signal',
    order: 4,
    title: 'The Lost Signal',
    concept: 'Requests & responses',
    icon: '📡',
    narrative:
      "The camp radio crackles: another camp is sending requests, but nobody here answers. Before building a real server, model what one does.",
    objective: 'Understand requests, responses, methods and status codes.',
    prerequisites: ['w1-ledger'],
    lesson: [
      {
        kind: 'p',
        text: 'On the web, a **client** (like a browser, or the game) sends a **request** to a **server**. The server sends back a **response**.',
      },
      {
        kind: 'term',
        term: 'Method',
        text: 'What the client wants to do. `GET` reads something; `POST` asks the server to do or create something.',
      },
      { kind: 'term', term: 'Path', text: 'Which thing it\'s about, like `/status` or `/mine`.' },
      {
        kind: 'term',
        term: 'Status code',
        text: 'A number summarising the answer. `200` OK, `404` not found, `405` method not allowed.',
      },
      {
        kind: 'term',
        term: 'JSON',
        text: 'The text format responses usually use. It looks almost exactly like a Python dictionary.',
      },
      {
        kind: 'code',
        text: 'GET /status\n\n→ 200 {"camp": "online"}',
        caption: 'A request and its response',
      },
    ],
    task: [
      'Complete `handle(method, path)`. It returns a dictionary with `"status"` and `"body"`.',
      'For `GET /status`, return status `200` and body `{"camp": "online"}`.',
      'For `/status` with any other method, return status `405`.',
      'For any other path, return status `404`.',
    ],
    starterCode: `def handle(method, path):
    if path == "/status":
        if method == "GET":
            return {"status": ___, "body": {"camp": "online"}}
        return {"status": ___, "body": {"detail": "Method not allowed"}}
    return {"status": ___, "body": {"detail": "Not found"}}
`,
    tests: [
      { id: 'get_status_200', name: 'GET /status → 200', expects: 'status 200 with body {"camp": "online"}' },
      { id: 'post_status_405', name: 'POST /status → 405', expects: 'status 405' },
      { id: 'unknown_path_404', name: 'GET /treasure → 404', expects: 'status 404' },
    ],
    hints: [
      'There are three blanks, one per status code.',
      'Success is `200`. Wrong method is `405`. Unknown path is `404`.',
    ],
    feedback: {
      post_status_405: 'Right path, wrong method. Which code means "I know this path, not with that method"?',
      unknown_path_404: 'Unknown paths should be "not found". You know that one from browsing the web.',
    },
    xp: 60,
    unlocks: ['w1-first-route'],
    frontierLink: 'Next, your answers stop being pretend: you will run a real server.',
  },
  {
    id: 'w1-first-route',
    world: 1,
    chapter: 'The Lost Signal',
    order: 5,
    title: 'Your First Route',
    concept: 'FastAPI GET',
    icon: '🛰️',
    narrative:
      'Time to answer the radio for real. FastAPI turns ordinary Python functions into web endpoints.',
    objective: 'Create a FastAPI app with one GET endpoint that returns JSON.',
    prerequisites: ['w1-signal'],
    lesson: [
      {
        kind: 'p',
        text: 'In the last mission you wrote the `if path == ...` logic yourself. FastAPI does that routing for you. You write one function per **route**, and mark it with a **decorator** — the `@` line above it.',
      },
      {
        kind: 'code',
        text: 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/weather")\ndef weather():\n    return {"sky": "clear"}',
      },
      {
        kind: 'p',
        text: '`@app.get("/weather")` means: "when a GET request arrives for `/weather`, run this function". Whatever dictionary you `return` becomes the JSON response, with status `200`.',
      },
      { kind: 'output', text: 'GET /weather → 200 {"sky": "clear"}', caption: 'What a client sees' },
      {
        kind: 'p',
        text: 'Wrong methods (`405`) and unknown paths (`404`) are handled automatically.',
      },
    ],
    task: [
      'Add a GET route at `/status`.',
      'It returns `{"camp": "online"}`.',
    ],
    starterCode: `from fastapi import FastAPI

app = FastAPI()


# Add a GET route for /status that returns {"camp": "online"}
`,
    tests: [
      { id: 'app_loads', name: 'the app starts', expects: 'A FastAPI object named app exists.' },
      { id: 'status_route_200', name: 'GET /status → 200', expects: 'The route answers with status 200.' },
      { id: 'status_body', name: 'body is {"camp": "online"}', expects: 'JSON body matches exactly.' },
    ],
    hints: [
      'Start with the decorator: `@app.get("/status")`.',
      'Under it, define a function — any name works, e.g. `def status():`.',
      'The function body is one line: `return {"camp": "online"}`.',
    ],
    feedback: {
      app_loads: 'The server didn\'t start. Is `app = FastAPI()` still there, with the import?',
      status_route_200: 'The request found no route. Check the path in the decorator — it needs the leading `/`.',
      status_body: 'The route answered, just not with the right words. Compare your keys and values letter by letter.',
    },
    xp: 80,
    unlocks: ['w1-copper-rights'],
    frontierLink: 'Your server is live. The mining rig is listening for it.',
    workshop: {
      examples: [
        { label: 'Camp status', method: 'GET', path: '/status' },
        { label: 'Wrong method', method: 'POST', path: '/status', body: {} },
      ],
    },
  },
  {
    id: 'w1-copper-rights',
    world: 1,
    chapter: 'Copper Rights',
    order: 6,
    title: 'Copper Rights',
    concept: 'POST + validation',
    icon: '⛏️',
    narrative:
      "The old mining rig won't move until a server tells it what's allowed. Every swing in the Frontier calls your `POST /mine` route — if your code says no, the rock stays a rock.",
    objective:
      'Build a POST endpoint that validates its input and returns the right status for each case.',
    prerequisites: ['w1-first-route'],
    lesson: [
      {
        kind: 'p',
        text: 'A `POST` request carries data in its **body**, as JSON. FastAPI reads it into a **Pydantic model**: a class that says which fields to expect and of what type.',
      },
      {
        kind: 'code',
        text: 'from pydantic import BaseModel\n\nclass Order(BaseModel):\n    item: str\n    qty: int\n\n@app.post("/order")\ndef order(req: Order):\n    return {"ok": True, "item": req.item}',
      },
      {
        kind: 'p',
        text: 'If the body is missing a field or has the wrong type, FastAPI rejects it with `422` before your function even runs.',
      },
      {
        kind: 'p',
        text: 'When the data is the right shape but breaks a rule, *you* refuse it by raising `HTTPException` with a status code:',
      },
      {
        kind: 'code',
        text: 'from fastapi import HTTPException\n\nif req.qty > 10:\n    raise HTTPException(status_code=400, detail="Too many")',
      },
      { kind: 'term', term: '400 Bad Request', text: 'The request doesn\'t make sense — e.g. an ore that doesn\'t exist.' },
      { kind: 'term', term: '403 Forbidden', text: 'The request makes sense, but isn\'t allowed — e.g. the wrong tool.' },
    ],
    task: [
      'Unknown resource (not in `REQUIRED_TOOL`) → raise `400`.',
      "Wrong tool for the resource → raise `403`.",
      'Otherwise return `{"mined": true, "resource": <resource>, "amount": 1}` with status `200`.',
    ],
    starterCode: `from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

REQUIRED_TOOL = {
    "copper": "stone_pickaxe",
    "tin": "stone_pickaxe",
}


class MineRequest(BaseModel):
    resource: str
    tool: str


@app.post("/mine")
def mine(req: MineRequest):
    # 1. Unknown resource?  raise HTTPException(status_code=400, detail="...")
    # 2. Wrong tool?        raise HTTPException(status_code=403, detail="...")
    # 3. Otherwise return the mined result.
    pass
`,
    tests: [
      { id: 'mine_success', name: 'copper + stone_pickaxe → 200', expects: '{"mined": true, "resource": "copper", "amount": 1}' },
      { id: 'mine_wrong_tool', name: 'copper + hands → 403', expects: 'The route refuses, nothing is mined.' },
      { id: 'mine_unknown', name: 'unknown ore → 400', expects: 'e.g. {"resource": "dragonglass"} is rejected.' },
      { id: 'mine_bad_body', name: 'missing field → 422', expects: 'Handled for you by the Pydantic model.' },
      { id: 'mine_amount_fixed', name: 'amount is exactly 1', expects: 'No route gets to hand out free copper.' },
    ],
    hints: [
      'Use your ledger: `if req.resource not in REQUIRED_TOOL:` catches unknown ore.',
      'For the tool check, compare `req.tool` with `REQUIRED_TOOL[req.resource]`.',
      'Check order matters: test for unknown ore *before* looking it up in the dictionary.',
      'The final line is `return {"mined": True, "resource": req.resource, "amount": 1}`.',
    ],
    feedback: {
      mine_success:
        'The request reached your route, but the answer wasn\'t what the rig expected. Check what you return at the end.',
      mine_wrong_tool: 'Your route let someone mine copper with their hands. The rig has standards. 403 them.',
      mine_unknown: 'An ore that doesn\'t exist got through — or crashed the route. Check it\'s in the ledger first.',
      mine_amount_fixed: 'Generous, but the simulator only accepts `amount: 1`. No copper inflation.',
      missing_return: 'Your route returned `null`. The rig needs an actual answer.',
    },
    xp: 120,
    achievementOnComplete: 'copper-rights',
    unlocks: ['w1-smelter'],
    frontierLink: 'Head to the Frontier: each copper deposit calls this route when you mine it.',
    game: { command: 'mine', label: 'Mine copper' },
    workshop: {
      examples: [
        { label: 'Mine copper', method: 'POST', path: '/mine', body: { resource: 'copper', tool: 'stone_pickaxe' } },
        { label: 'Bare hands', method: 'POST', path: '/mine', body: { resource: 'copper', tool: 'hands' } },
        { label: 'Unknown ore', method: 'POST', path: '/mine', body: { resource: 'dragonglass', tool: 'stone_pickaxe' } },
        { label: 'Missing field', method: 'POST', path: '/mine', body: { resource: 'copper' } },
      ],
    },
  },
  {
    id: 'w1-smelter',
    world: 1,
    chapter: 'Copper Rights',
    order: 7,
    title: 'The Smelter',
    concept: 'Crafting with state',
    icon: '🔥',
    narrative: 'Raw copper is only half the story. The smelter by the gate can turn it into something useful.',
    objective: 'Coming next: a crafting endpoint that reads and changes inventory state.',
    prerequisites: ['w1-copper-rights'],
    lesson: [],
    task: [],
    starterCode: '',
    tests: [],
    hints: [],
    feedback: {},
    xp: 0,
    unlocks: [],
    frontierLink: 'The gate past the smelter leads to World 2.',
    comingSoon: true,
  },
]

export const missionById = Object.fromEntries(missions.map((m) => [m.id, m])) as Record<string, Mission>

export const GAME_MISSION_ID = 'w1-copper-rights'
