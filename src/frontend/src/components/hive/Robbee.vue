<script setup lang="ts">
/** Robbee the Hornet Foreman: the challenges' boss. A red hornet in a cap, with a headset and a staff badge. */
withDefaults(defineProps<{ size?: number; bob?: boolean }>(), { size: 160, bob: true });
</script>

<template>
  <svg class="robbee" :class="{ bob }" :width="size" :height="size * 1.1" viewBox="0 0 200 220" role="img" aria-label="Robbee the Hornet Foreman">
    <defs>
      <clipPath id="robbee-body"><rect x="45" y="80" width="110" height="110" rx="30" /></clipPath>
    </defs>
    <!-- wings -->
    <ellipse cx="42" cy="128" rx="22" ry="36" transform="rotate(-14 42 128)" fill="#fff" stroke="#d9cfae" stroke-width="3" />
    <ellipse cx="158" cy="128" rx="22" ry="36" transform="rotate(14 158 128)" fill="#fff" stroke="#d9cfae" stroke-width="3" />
    <!-- antennae -->
    <path d="M84 74 L72 36 M116 74 L128 36" stroke="#1e1e1e" stroke-width="4" stroke-linecap="round" />
    <circle cx="72" cy="35" r="6" fill="#1e1e1e" /><circle cx="128" cy="35" r="6" fill="#1e1e1e" />
    <!-- stinger -->
    <path d="M91 186 L100 214 L109 186 Z" fill="#1e1e1e" />
    <!-- body and stripes -->
    <rect x="45" y="80" width="110" height="110" rx="30" fill="#d93a35" />
    <g clip-path="url(#robbee-body)" fill="#4a1616">
      <rect x="40" y="164" width="120" height="10" /><rect x="40" y="180" width="120" height="10" />
    </g>
    <!-- cap -->
    <path d="M47 104 C47 52 153 52 153 104 Z" fill="#1e1e1e" />
    <path d="M47 94 H153 V104 H47 Z" fill="#ffc107" />
    <path d="M138 96 C162 88 188 96 186 108 C172 112 152 108 138 104 Z" fill="#1e1e1e" />
    <circle cx="100" cy="66" r="4.5" fill="#ffc107" />
    <text x="100" y="89" text-anchor="middle" font-family="Nunito, sans-serif" font-weight="900" font-size="28" fill="#ffc107">R</text>
    <!-- face -->
    <path d="M128 110 L137 140" stroke="#8a1f1f" stroke-width="3" stroke-linecap="round" />
    <path d="M129 120 L136 118 M131 129 L138 127" stroke="#8a1f1f" stroke-width="2" stroke-linecap="round" />
    <path d="M66 116 L91 127 M134 116 L109 127" stroke="#1e1e1e" stroke-width="7" stroke-linecap="round" />
    <circle cx="80" cy="135" r="9" fill="#1e1e1e" /><circle cx="120" cy="135" r="9" fill="#1e1e1e" />
    <circle cx="83" cy="132" r="3" fill="#fff" /><circle cx="123" cy="132" r="3" fill="#fff" />
    <ellipse cx="64" cy="148" rx="8" ry="4.5" fill="#ff9a9a" opacity=".85" />
    <ellipse cx="136" cy="148" rx="8" ry="4.5" fill="#ff9a9a" opacity=".85" />
    <path d="M83 152 Q92 145 100 150 Q108 145 117 152 Q108 158 100 154 Q92 158 83 152 Z" fill="#1e1e1e" />
    <path d="M92 163 Q100 158 108 163" stroke="#1e1e1e" stroke-width="3" fill="none" stroke-linecap="round" />
    <!-- headset -->
    <rect x="38" y="122" width="13" height="24" rx="5" fill="#1e1e1e" />
    <path d="M46 146 Q50 170 80 168" stroke="#1e1e1e" stroke-width="4" fill="none" stroke-linecap="round" />
    <circle cx="82" cy="168" r="4.5" fill="#1e1e1e" />
    <!-- staff badge -->
    <rect x="113" y="165" width="27" height="19" rx="3" fill="#fff" stroke="#1e1e1e" stroke-width="2" />
    <rect x="117" y="169" width="8" height="8" fill="#ff9800" />
    <rect x="128" y="170" width="8" height="2.5" fill="#cfcabb" /><rect x="128" y="175" width="8" height="2.5" fill="#cfcabb" />
  </svg>
</template>

<style scoped>
.robbee { display: block; overflow: visible; }
.bob { animation: robbee-bob 2.4s ease-in-out infinite; transform-origin: 50% 100%; }
@keyframes robbee-bob { 0%, 100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-4px) rotate(-2deg); } }
@media (prefers-reduced-motion: reduce) { .bob { animation: none; } }
</style>
