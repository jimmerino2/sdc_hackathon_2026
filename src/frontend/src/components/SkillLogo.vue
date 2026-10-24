<script setup lang="ts">
import cpp from '../assets/logos/cplusplus.svg';
import java from '../assets/logos/java.svg';
import node from '../assets/logos/nodejs.svg';
import python from '../assets/logos/python.svg';
import react from '../assets/logos/react.svg';
import typescript from '../assets/logos/typescript.svg';

/** The official marks for a few well-known skills (Devicon, see assets/logos/README.txt), drawn on a 32 x 32 grid. Renders an <image>, so it sits inside any <svg>. */
export type LogoName = 'react' | 'node' | 'typescript' | 'java' | 'python' | 'cpp';
const files: Record<LogoName, string> = { react, node, typescript, java, python, cpp };
defineProps<{ name: LogoName }>();
</script>

<template>
  <image :href="files[name]" x="0" y="0" width="32" height="32" />
</template>
