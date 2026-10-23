import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { missionById } from '@/content/missions'
import { storage } from '@/lib/storage'

const KEY = 'workspace.v1'

/**
 * The learner's source code, one file per mission. Academy, Frontier and
 * Workshop all read from here so they always exercise the same implementation.
 */
export const useWorkspace = defineStore('workspace', () => {
  const files = ref<Record<string, string>>(storage.load(KEY) ?? {})

  watch(files, () => storage.save(KEY, files.value), { deep: true })

  function code(missionId: string): string {
    return files.value[missionId] ?? missionById[missionId]?.starterCode ?? ''
  }

  function setCode(missionId: string, source: string) {
    files.value[missionId] = source
  }

  function reset(missionId: string) {
    delete files.value[missionId]
  }

  function isEdited(missionId: string) {
    return missionId in files.value && files.value[missionId] !== missionById[missionId]?.starterCode
  }

  return { files, code, setCode, reset, isEdited }
})
