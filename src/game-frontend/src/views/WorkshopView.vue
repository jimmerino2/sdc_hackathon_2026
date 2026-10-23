<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { missions, missionById, GAME_MISSION_ID, type RequestExample } from '@/content/missions'
import type { GameActionResult, HttpMethod, RequestResult } from '@/api/types'
import { useWorkspace } from '@/stores/workspace'
import { useRunner, type HistoryEntry } from '@/stores/runner'
import { useProgress } from '@/stores/progress'
import { useCompanion } from '@/stores/companion'
import { useGame } from '@/stores/game'
import { statusClass, STATUS_TEXT } from '@/lib/format'
import CodeEditor from '@/components/CodeEditor.vue'
import JsonView from '@/components/JsonView.vue'

const workspace = useWorkspace()
const runner = useRunner()
const progress = useProgress()
const companion = useCompanion()
const game = useGame()

const available = computed(() => missions.filter((m) => m.workshop && progress.missionState(m.id) !== 'locked'))
const missionId = ref<string>('')
const mission = computed(() => (missionId.value ? missionById[missionId.value] : null))

const code = computed({
  get: () => (missionId.value ? workspace.code(missionId.value) : ''),
  set: (v: string) => missionId.value && workspace.setCode(missionId.value, v),
})

const METHODS: HttpMethod[] = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const method = ref<HttpMethod>('GET')
const path = ref('/')
const query = ref<{ k: string; v: string }[]>([{ k: '', v: '' }])
const headers = ref<{ k: string; v: string }[]>([{ k: '', v: '' }])
const body = ref('{}')
const tab = ref<'body' | 'query' | 'headers'>('body')
const sending = ref(false)
const sendError = ref<string | null>(null)
const result = ref<RequestResult | null>(null)
const gameResult = ref<GameActionResult | null>(null)

// Routes declared in the learner's code, so they can click instead of typing.
const routes = computed(() => {
  const found: { method: HttpMethod; path: string }[] = []
  const re = /@app\.(get|post|put|patch|delete)\(\s*["']([^"']+)["']/g
  for (const m of code.value.matchAll(re)) found.push({ method: m[1].toUpperCase() as HttpMethod, path: m[2] })
  return found
})

const bodyError = computed(() => {
  if (method.value === 'GET' || !body.value.trim()) return null
  try {
    JSON.parse(body.value)
    return null
  } catch (e) {
    return (e as Error).message
  }
})

const stage = computed(() => {
  if (!result.value) return 0
  if (!result.value.response) return 2
  return gameResult.value ? 4 : 3
})

onMounted(() => {
  companion.react('enter_workshop')
  const preferred = available.value.find((m) => m.id === GAME_MISSION_ID) ?? available.value.at(-1)
  if (preferred) selectMission(preferred.id)
})

watch(missionId, () => {
  result.value = null
  gameResult.value = null
})

function selectMission(id: string) {
  missionId.value = id
  const ex = missionById[id].workshop?.examples[0]
  if (ex) loadExample(ex)
}

function loadExample(ex: RequestExample) {
  method.value = ex.method
  path.value = ex.path
  body.value = ex.body !== undefined ? JSON.stringify(ex.body, null, 2) : '{}'
  query.value = [...Object.entries(ex.query ?? {}).map(([k, v]) => ({ k, v })), { k: '', v: '' }]
}

function pickRoute(r: { method: HttpMethod; path: string }) {
  method.value = r.method
  path.value = r.path
}

function rows(list: { k: string; v: string }[]) {
  return Object.fromEntries(list.filter((r) => r.k.trim()).map((r) => [r.k.trim(), r.v]))
}

function ensureBlankRow(list: { k: string; v: string }[]) {
  if (list.at(-1)?.k) list.push({ k: '', v: '' })
}

async function send() {
  if (!missionId.value || bodyError.value || sending.value) return
  sending.value = true
  sendError.value = null
  gameResult.value = null
  try {
    const r = await runner.sendRequest(missionId.value, code.value, {
      method: method.value,
      path: path.value.startsWith('/') ? path.value : '/' + path.value,
      query: rows(query.value),
      headers: rows(headers.value),
      body: method.value === 'GET' || !body.value.trim() ? null : JSON.parse(body.value),
    })
    result.value = r
    const sc = r.response?.status_code
    if (!sc) companion.react('request_server_error', { reason: r.error?.type ?? 'no response' })
    else if (sc >= 500) companion.react('request_server_error', { reason: `${sc}` })
    else if (sc >= 400) companion.react('request_client_error', { reason: `${sc} ${STATUS_TEXT[sc] ?? ''}`.trim() })
    else companion.react('request_ok', { reason: `${sc} ${STATUS_TEXT[sc] ?? ''}`.trim() })
  } catch (e) {
    sendError.value = e instanceof Error ? e.message : String(e)
    companion.react('runner_offline')
  } finally {
    sending.value = false
  }
}

async function sendAsGameAction() {
  if (!mission.value?.game) return
  sendError.value = null
  try {
    gameResult.value = await game.act('mine', 'copper-1', { missionId: missionId.value, code: code.value })
  } catch (e) {
    sendError.value = e instanceof Error ? e.message : String(e)
    companion.react('runner_offline')
  }
}

function restoreHistory(h: HistoryEntry) {
  if (h.missionId && missionById[h.missionId]) missionId.value = h.missionId
  method.value = h.result.request.method
  path.value = h.result.request.path
  body.value = h.result.request.body == null ? '{}' : JSON.stringify(h.result.request.body, null, 2)
  result.value = h.result
}

function resetCode() {
  if (missionId.value && confirm('Restore the example code for this mission?')) workspace.reset(missionId.value)
}

const time = (t: number) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
</script>

<template>
  <div class="workshop">
    <div v-if="!available.length" class="locked">
      <h1>The Workshop is still dark</h1>
      <p>Complete <strong>Your First Route</strong> in the Academy to get a server you can poke at.</p>
      <RouterLink to="/academy" class="btn btn-primary">To the Academy</RouterLink>
    </div>

    <template v-else>
      <section class="code-col">
        <div class="bar">
          <label class="sr-only" for="ws-mission">Mission code</label>
          <select id="ws-mission" :value="missionId" class="select" @change="selectMission(($event.target as HTMLSelectElement).value)">
            <option v-for="m in available" :key="m.id" :value="m.id">{{ m.icon }} {{ m.title }}</option>
          </select>
          <div class="spacer" />
          <button class="btn btn-ghost btn-sm muted" @click="resetCode">↺ Restore example</button>
        </div>
        <p class="shared-note">Same code as the Academy and Frontier — edits here are your real implementation.</p>
        <div class="editor">
          <CodeEditor v-if="missionId" :key="missionId" v-model="code" label="Server code" @run="send" />
        </div>
        <div class="routes">
          <span class="lbl">Routes in your code</span>
          <button v-for="r in routes" :key="r.method + r.path" class="route" @click="pickRoute(r)">
            <span class="m" :class="r.method">{{ r.method }}</span>{{ r.path }}
          </button>
          <span v-if="!routes.length" class="none">None yet — add an <code>@app.get(...)</code> or <code>@app.post(...)</code>.</span>
        </div>
      </section>

      <section class="req-col dev-scroll">
        <ol class="flow" aria-label="Request lifecycle">
          <li :class="{ on: stage >= 1 }">Request</li>
          <li :class="{ on: stage >= 2 }">Your route</li>
          <li :class="{ on: stage >= 3 }">Response</li>
          <li :class="{ on: stage >= 4 }">World</li>
        </ol>

        <div class="panel">
          <div class="req-line">
            <label class="sr-only" for="ws-method">Method</label>
            <select id="ws-method" v-model="method" class="select method" :class="method">
              <option v-for="m in METHODS" :key="m">{{ m }}</option>
            </select>
            <label class="sr-only" for="ws-path">Path</label>
            <input id="ws-path" v-model="path" class="path" spellcheck="false" @keydown.enter="send" />
            <button class="btn btn-primary" :disabled="sending || !!bodyError" @click="send">
              {{ sending ? 'Sending…' : 'Send' }}
            </button>
          </div>

          <div v-if="mission?.workshop" class="examples">
            <span class="lbl">Try</span>
            <button v-for="ex in mission.workshop.examples" :key="ex.label" class="chip" @click="loadExample(ex)">{{ ex.label }}</button>
          </div>

          <div class="tabs" role="tablist">
            <button role="tab" :aria-selected="tab === 'body'" :class="{ on: tab === 'body' }" @click="tab = 'body'">Body</button>
            <button role="tab" :aria-selected="tab === 'query'" :class="{ on: tab === 'query' }" @click="tab = 'query'">Query</button>
            <button role="tab" :aria-selected="tab === 'headers'" :class="{ on: tab === 'headers' }" @click="tab = 'headers'">Headers</button>
          </div>

          <div v-if="tab === 'body'" class="body-edit">
            <p v-if="method === 'GET'" class="hint">GET requests don't send a body.</p>
            <CodeEditor v-else v-model="body" language="json" label="Request body JSON" min-height="120px" @run="send" />
            <p v-if="bodyError" class="bad-json">Body isn't valid JSON: {{ bodyError }}</p>
          </div>
          <div v-else class="kv">
            <div v-for="(r, i) in tab === 'query' ? query : headers" :key="i" class="kv-row">
              <input v-model="r.k" placeholder="key" :aria-label="`${tab} key ${i + 1}`" @input="ensureBlankRow(tab === 'query' ? query : headers)" />
              <input v-model="r.v" placeholder="value" :aria-label="`${tab} value ${i + 1}`" />
            </div>
          </div>
        </div>

        <div class="panel response" aria-live="polite">
          <div class="resp-head">
            <h3>Response</h3>
            <template v-if="result">
              <span v-if="result.response" class="status-code" :class="statusClass(result.response.status_code)">
                {{ result.response.status_code }} {{ STATUS_TEXT[result.response.status_code] ?? '' }}
              </span>
              <span v-else class="status-code status-err">No response</span>
              <span class="ms">{{ result.duration_ms }} ms</span>
              <span v-if="result.simulated" class="sim">simulated</span>
            </template>
          </div>
          <p v-if="sendError" class="send-error" role="alert">{{ sendError }}</p>
          <p v-else-if="!result" class="hint">Send a request to see exactly what your server answers.</p>
          <template v-if="result">
            <JsonView v-if="result.response" :value="result.response.body" />
            <div v-if="result.error" class="diag">
              <strong>{{ result.error.type }}<template v-if="result.error.line"> (line {{ result.error.line }})</template></strong>
              <pre>{{ result.error.message }}</pre>
            </div>
            <details v-if="result.response && Object.keys(result.response.headers).length">
              <summary>Headers</summary>
              <JsonView :value="result.response.headers" />
            </details>
            <details v-if="result.logs">
              <summary>Server log</summary>
              <pre class="logs">{{ result.logs }}</pre>
            </details>
          </template>

          <div v-if="mission?.game" class="game-link">
            <div>
              <strong>⛏ Send as a game action</strong>
              <p>Ask the trusted simulator to mine <code>copper-1</code>. It calls this same route and decides what changes in the world.</p>
            </div>
            <button class="btn btn-secondary btn-sm" :disabled="game.busy" @click="sendAsGameAction">Mine via game</button>
          </div>
          <div v-if="gameResult" class="game-result" :class="gameResult.accepted ? 'ok' : 'bad'">
            <strong>{{ gameResult.accepted ? 'World updated' : 'World unchanged' }}</strong> — {{ gameResult.reason }}
            <div class="inv">
              Inventory:
              <span v-for="(q, item) in gameResult.state.inventory" :key="item" class="tag">{{ item }} × {{ q }}</span>
              <span v-if="!Object.keys(gameResult.state.inventory).length" class="tag">empty</span>
            </div>
          </div>
        </div>

        <div class="panel history">
          <h3>History</h3>
          <p v-if="!runner.history.length" class="hint">Requests from here and from the Frontier show up in this list.</p>
          <ul>
            <li v-for="h in runner.history" :key="h.id + h.at">
              <button @click="restoreHistory(h)">
                <span class="src" :title="h.source">{{ h.source === 'frontier' ? '🏕️' : '🔧' }}</span>
                <span class="m" :class="h.result.request.method">{{ h.result.request.method }}</span>
                <span class="p">{{ h.result.request.path }}</span>
                <span class="status-code" :class="statusClass(h.result.response?.status_code)">{{ h.result.response?.status_code ?? 'ERR' }}</span>
                <span class="t">{{ time(h.at) }}</span>
              </button>
            </li>
          </ul>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.workshop {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(380px, 1fr);
  min-height: 0;
  background: var(--c-dark);
  color: var(--c-panel-text);
}

.locked {
  grid-column: 1 / -1;
  place-self: center;
  text-align: center;
  max-width: 460px;
  padding: 24px;
}

.locked h1 {
  color: var(--c-primary);
}

.code-col {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  min-height: 0;
  border-right: 3px solid #000;
}

.bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--c-panel);
}

.spacer {
  flex: 1;
}

.select {
  font: inherit;
  font-weight: 700;
  background: var(--c-panel-2);
  color: var(--c-cream);
  border: 1px solid var(--c-panel-line);
  border-radius: var(--radius-s);
  padding: 6px 10px;
}

.muted {
  color: var(--c-panel-muted);
}

.shared-note {
  margin: 0;
  padding: 5px 14px;
  font-size: 0.78rem;
  color: var(--c-primary);
  background: rgba(255, 193, 7, 0.08);
}

.editor {
  min-height: 0;
  overflow: hidden;
}

.routes {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: var(--c-panel);
  border-top: 1px solid var(--c-panel-line);
}

.lbl {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--c-panel-muted);
  margin-right: 4px;
}

.route {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  padding: 3px 10px 3px 3px;
  background: var(--c-panel-2);
  border: 1px solid var(--c-panel-line);
  border-radius: var(--radius-s);
  cursor: pointer;
  color: var(--c-cream);
}

.route:hover {
  border-color: var(--c-primary);
}

.none {
  font-size: 0.82rem;
  color: var(--c-panel-muted);
}

.none code {
  background: #333;
  border-color: #444;
  color: var(--c-cream);
}

.m {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.72rem;
  padding: 1px 6px;
  border-radius: 4px;
  background: #3b3b3b;
}

.m.GET {
  color: #8be08f;
}

.m.POST {
  color: var(--c-primary);
}

.m.DELETE {
  color: #ff8a83;
}

.req-col {
  overflow-y: auto;
  padding: 14px 16px 120px;
  display: grid;
  align-content: start;
  gap: 14px;
}

.flow {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}

.flow li {
  text-align: center;
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 6px 4px;
  background: var(--c-panel-2);
  color: var(--c-panel-muted);
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%, 10px 50%);
  transition: background 0.3s, color 0.3s;
}

.flow li.on {
  background: var(--c-primary);
  color: var(--c-ink);
}

.panel {
  background: var(--c-panel);
  border: 1px solid var(--c-panel-line);
  border-radius: var(--radius-m);
  padding: 12px;
}

.req-line {
  display: flex;
  gap: 8px;
}

.method {
  font-family: var(--font-mono);
}

.method.GET {
  color: #8be08f;
}

.method.POST {
  color: var(--c-primary);
}

.path {
  flex: 1;
  min-width: 0;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  background: #1a1a1a;
  color: var(--c-cream);
  border: 1px solid var(--c-panel-line);
  border-radius: var(--radius-s);
  padding: 6px 10px;
}

.path:focus,
.kv input:focus {
  outline: none;
  border-color: var(--c-primary);
}

.examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 10px 0 2px;
}

.chip {
  font-size: 0.8rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--c-panel-line);
  background: var(--c-panel-2);
  color: var(--c-cream);
  cursor: pointer;
}

.chip:hover {
  border-color: var(--c-secondary);
  color: var(--c-secondary);
}

.tabs {
  display: flex;
  gap: 2px;
  margin: 12px 0 8px;
  border-bottom: 1px solid var(--c-panel-line);
}

.tabs button {
  background: none;
  border: none;
  padding: 6px 12px;
  font-weight: 700;
  font-size: 0.88rem;
  color: var(--c-panel-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tabs button.on {
  color: var(--c-primary);
  border-bottom-color: var(--c-primary);
}

.body-edit {
  border-radius: var(--radius-s);
  overflow: hidden;
}

.bad-json,
.send-error {
  color: #ff8a83;
  font-size: 0.85rem;
  margin: 6px 0 0;
}

.kv {
  display: grid;
  gap: 6px;
}

.kv-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.kv input {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  background: #1a1a1a;
  color: var(--c-cream);
  border: 1px solid var(--c-panel-line);
  border-radius: var(--radius-s);
  padding: 5px 8px;
}

.hint {
  font-size: 0.85rem;
  color: var(--c-panel-muted);
  margin: 0;
}

.resp-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

h3 {
  font-size: 1rem;
  margin: 0;
  color: var(--c-primary);
}

.ms {
  font-size: 0.78rem;
  color: var(--c-panel-muted);
}

.sim {
  font-size: 0.7rem;
  font-weight: 800;
  background: rgba(255, 152, 0, 0.2);
  color: var(--c-secondary);
  padding: 0 7px;
  border-radius: 999px;
}

.diag {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(229, 83, 75, 0.14);
  border-left: 3px solid var(--c-danger);
  border-radius: var(--radius-s);
}

.diag pre,
.logs {
  margin: 4px 0 0;
  white-space: pre-wrap;
  font-size: 0.82rem;
}

details {
  margin-top: 8px;
  font-size: 0.85rem;
}

summary {
  cursor: pointer;
  color: var(--c-panel-muted);
  margin-bottom: 4px;
}

.game-link {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--c-panel-line);
}

.game-link p {
  margin: 2px 0 0;
  font-size: 0.82rem;
  color: var(--c-panel-muted);
}

.game-link code {
  background: #333;
  border-color: #444;
  color: var(--c-cream);
}

.game-result {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-s);
  font-size: 0.88rem;
}

.game-result.ok {
  background: rgba(76, 175, 80, 0.14);
}

.game-result.bad {
  background: rgba(229, 83, 75, 0.14);
}

.inv {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.inv .tag {
  background: #333;
  color: var(--c-cream);
  text-transform: none;
  letter-spacing: 0;
}

.history ul {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
  display: grid;
  gap: 2px;
}

.history button {
  width: 100%;
  display: grid;
  grid-template-columns: 22px auto 1fr auto auto;
  gap: 8px;
  align-items: center;
  background: none;
  border: none;
  border-radius: var(--radius-s);
  padding: 5px 6px;
  cursor: pointer;
  color: var(--c-panel-text);
  text-align: left;
  font-size: 0.85rem;
}

.history button:hover {
  background: var(--c-panel-2);
}

.p {
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
}

.t {
  font-size: 0.75rem;
  color: var(--c-panel-muted);
}

@media (max-width: 900px) {
  .workshop {
    grid-template-columns: 1fr;
    flex: none;
  }

  .code-col {
    grid-template-rows: auto auto 360px auto;
    border-right: none;
    border-bottom: 3px solid #000;
  }
}
</style>
