import { computed, reactive } from 'vue';
import { useRoute } from 'vue-router';
import { personas, scenarios, type PersonaKey, type Role, type ScenarioKey } from './data/flows';

interface FlowState {
  who: number;
  mind: number[];
  levels: number[];
  scenario: ScenarioKey;
  chosenRoleId: string | null;
  doneNodes: number;
}

const store = reactive<Record<PersonaKey, FlowState>>({
  a: init('a'),
  b: init('b'),
  c: init('c'),
});

function init(k: PersonaKey): FlowState {
  const p = personas[k];
  return {
    who: p.whoIndex,
    mind: [...p.mindPicks],
    levels: p.skills.map((s) => s.level),
    scenario: 'accelerates',
    chosenRoleId: null,
    doneNodes: 0,
  };
}

export function resetPersona(k: PersonaKey) {
  Object.assign(store[k], init(k));
}

export function useFlow() {
  const route = useRoute();
  const key = computed(() => (route.params.persona as PersonaKey) || 'a');
  const persona = computed(() => personas[key.value]);
  const state = computed(() => store[key.value]);
  const scenario = computed(() => scenarios.find((s) => s.key === state.value.scenario)!);
  const roles = computed<Role[]>(() => persona.value.roles[state.value.scenario]);
  const chosenRole = computed<Role>(() => {
    const all = Object.values(persona.value.roles).flat();
    return all.find((r) => r.id === state.value.chosenRoleId) ?? persona.value.roles.accelerates[0]!;
  });
  return { key, persona, state, scenario, roles, chosenRole };
}
