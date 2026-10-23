// Scripted, event-driven lines for Wick, the lantern sprite companion.
// `{name}`, `{mission}`, `{test}`, `{count}` and `{reason}` are filled from the event context.

export type CompanionEvent =
  | 'welcome'
  | 'welcome_back'
  | 'enter_academy'
  | 'enter_frontier'
  | 'enter_workshop'
  | 'mission_start'
  | 'run_start'
  | 'tests_failed'
  | 'tests_failed_repeat'
  | 'code_error'
  | 'timeout'
  | 'tests_passed'
  | 'tests_passed_first_try'
  | 'tests_passed_after_fail'
  | 'hint'
  | 'hints_exhausted'
  | 'achievement'
  | 'unlock'
  | 'level_up'
  | 'runner_offline'
  | 'explore'
  | 'mine_success'
  | 'mine_rejected'
  | 'mine_error'
  | 'mine_invalid'
  | 'mine_locked'
  | 'node_depleted'
  | 'pickup'
  | 'request_ok'
  | 'request_client_error'
  | 'request_server_error'

export type Mood = 'neutral' | 'happy' | 'proud' | 'smug' | 'worried' | 'curious'

export interface Line {
  text: string
  mood: Mood
}

const l = (mood: Mood, ...texts: string[]): Line[] => texts.map((text) => ({ text, mood }))

export const lines: Record<CompanionEvent, Line[]> = {
  welcome: l(
    'happy',
    "Oh good, a new explorer. I'm Wick. I glow, I know Python, and I have opinions.",
  ),
  welcome_back: l(
    'happy',
    'Welcome back, {name}. The Frontier missed you. I mostly just flickered.',
    "{name}! I kept the lantern lit. Where were we?",
  ),
  enter_academy: l(
    'neutral',
    'Academy time. Short lessons, real code, no pop quizzes. Probably.',
    'Pick a glowing node. The grey ones are sulking until you earn them.',
  ),
  enter_frontier: l(
    'curious',
    'Fresh air! Move with WASD or click a tile. Press E next to things to interact.',
    'Remember: when you mine here, your own route decides what happens. No pressure.',
  ),
  enter_workshop: l(
    'curious',
    "The Workshop. Poke your server and see what it says back — nothing here costs XP.",
    'Pick a route, send a request, read the response. Science!',
  ),
  mission_start: l(
    'neutral',
    "\"{mission}\". Read the short bit first — it has the clues.",
    'New mission: {mission}. The tests on the right tell you exactly what gets checked.',
  ),
  run_start: l('curious', 'Sending it to the runner…', 'Running your code. Fingers crossed. I have no fingers.'),
  tests_failed: l(
    'worried',
    '{count} test(s) failed. The first red one is usually the most honest.',
    "Not yet. Read the failing test's message — it says what it expected.",
  ),
  tests_failed_repeat: l(
    'smug',
    "That's attempt {count}. Maybe we investigate the evidence before creating another crime scene?",
    'Same test, same result. Try a hint — they get more specific each time.',
  ),
  code_error: l(
    'worried',
    "Python couldn't run this: {reason}. Look at the line it mentions.",
    'Crash on takeoff: {reason}. The error message is a map, not an insult.',
  ),
  timeout: l(
    'worried',
    'Your code ran out of time. Is something looping forever?',
  ),
  tests_passed: l(
    'proud',
    'All green! Look at you.',
    "Every test passed. I'd high-five you but I'm mostly flame.",
  ),
  tests_passed_first_try: l(
    'proud',
    'First try?! Suspiciously competent.',
  ),
  tests_passed_after_fail: l(
    'proud',
    "That's how it's done: read the failure, fix the cause. Character development!",
    'From red to green. That debugging was the real lesson.',
  ),
  hint: l(
    'neutral',
    "Here's a nudge. Not the answer — I believe in you that much.",
    "A hint, coming right up. Let's keep the 'aha' for you.",
  ),
  hints_exhausted: l(
    'neutral',
    "That's every hint I have. Line them up against your code, one at a time.",
  ),
  achievement: l(
    'proud',
    'Badge unlocked: {reason}. You\'re starting to look employable.',
    'New badge — {reason}. I\'m telling everyone.',
  ),
  unlock: l(
    'happy',
    'New mission unlocked: {mission}. The trail goes on.',
  ),
  level_up: l('proud', 'Level up! You are now a {reason}.'),
  runner_offline: l(
    'worried',
    "I can't reach the code runner, so I can't actually test anything. Is the backend running?",
  ),
  explore: l(
    'curious',
    '{reason}',
  ),
  mine_success: l(
    'proud',
    'Your route said yes, the rock agreed. Copper secured!',
    'Clean swing. That copper exists because your code was right.',
    "Another one. You're validating inputs before changing state — very professional.",
  ),
  mine_rejected: l(
    'smug',
    'Your route refused: {reason}. Which, honestly, might be correct.',
    'Rejected by your own code: {reason}. Check the Field Log to see the request.',
  ),
  mine_error: l(
    'worried',
    'The request reached your route and it fell over: {reason}. Back to the Academy?',
    "Mining failed because the route crashed. Open the Field Log — the request is right there.",
  ),
  mine_invalid: l(
    'worried',
    'Your route answered, but the rig didn\'t trust it: {reason}',
  ),
  mine_locked: l(
    'neutral',
    "The rig won't run until you've written a mining route. Copper Rights is in the Academy.",
  ),
  node_depleted: l('neutral', "That deposit's tapped out. Try another one."),
  pickup: l('happy', 'A pickaxe! Now your route has a reason to say yes.'),
  request_ok: l('happy', '{reason} — the server answered.'),
  request_client_error: l(
    'curious',
    'A {reason}. That\'s the server refusing on purpose — is that what you expected?',
  ),
  request_server_error: l('worried', 'The route crashed ({reason}). Check the diagnostics panel.'),
}

/** Explore text for world objects, shown when the player inspects them. */
export const objectLore: Record<string, string> = {
  tree: 'A pine. Not mineable. I checked.',
  rock: 'Plain stone. Your route would say 400 to this.',
  npc: "That's Surveyor Marlo. Grumpy, but their ledger is excellent.",
  campfire: 'The campfire. My cousin.',
  gate: 'Locked. Something about a smelter. Later.',
  tent: 'Your tent. Very rustic.',
}
