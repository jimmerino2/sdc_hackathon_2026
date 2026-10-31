<script setup lang="ts">
/**
 * Robbee the Corrupt CEO: the challenges' boss. A red hornet in a top hat and pinstripe suit, with a monocle, cigar and money bag.
 * pose: idle, hit (eyes squeezed shut, shaking) or defeated (X eyes, hat off, pockets empty, tumbling over: bankrupt and unemployed).
 */
withDefaults(defineProps<{ size?: number; bob?: boolean; pose?: 'idle' | 'hit' | 'defeated' }>(), { size: 160, bob: true, pose: 'idle' });
</script>

<template>
  <svg class="robbee" :class="[{ bob: bob && pose === 'idle' }, `pose-${pose}`]" :width="size" :height="size * 1.1" viewBox="0 0 200 220" role="img" aria-label="Robbee the Corrupt CEO">
    <defs>
      <clipPath id="robbee-suit"><rect x="50" y="136" width="100" height="54" rx="16" /></clipPath>
    </defs>
    <!-- smoke -->
    <g v-if="pose !== 'defeated'" fill="#b0a898">
      <circle cx="150" cy="96" r="9" /><circle cx="162" cy="78" r="12" /><circle cx="174" cy="56" r="8" />
    </g>
    <!-- wings -->
    <ellipse cx="42" cy="128" rx="22" ry="36" transform="rotate(-14 42 128)" fill="#fff" stroke="#d9cfae" stroke-width="3" />
    <ellipse cx="158" cy="128" rx="22" ry="36" transform="rotate(14 158 128)" fill="#fff" stroke="#d9cfae" stroke-width="3" />
    <!-- stinger -->
    <path d="M91 186 L100 214 L109 186 Z" fill="#1e1e1e" />
    <!-- head -->
    <rect x="45" y="80" width="110" height="110" rx="30" fill="#d93a35" />
    <!-- suit -->
    <rect x="50" y="136" width="100" height="54" rx="16" fill="#2b2f3c" />
    <g clip-path="url(#robbee-suit)" stroke="#444a5c" stroke-width="1.5">
      <path d="M66 136 V190 M82 136 V190 M118 136 V190 M134 136 V190" />
    </g>
    <path d="M84 136 L100 156 L116 136 Z" fill="#fff" />
    <path d="M84 136 L96 164 L76 160 Z M116 136 L104 164 L124 160 Z" fill="#1f2230" />
    <path d="M96 146 H104 L108 152 L102 180 H98 L92 152 Z" fill="#ffc107" />
    <!-- pockets: a coin and a letter while he is rich, linings turned out once he is broke -->
    <template v-if="pose !== 'defeated'">
      <circle cx="72" cy="168" r="6" fill="#ffc107" /><text x="72" y="172" text-anchor="middle" font-family="Nunito, sans-serif" font-weight="900" font-size="9" fill="#1e1e1e">$</text>
      <rect x="116" y="162" width="16" height="11" rx="1.5" fill="#fff" /><path d="M116 163 L124 169 L132 163" stroke="#ffc107" stroke-width="1.8" fill="none" />
    </template>
    <template v-else>
      <path d="M66 164 L80 164 L74 180 Z" fill="#e8e4d4" /><path d="M120 164 L134 164 L128 180 Z" fill="#e8e4d4" />
    </template>
    <!-- face -->
    <path d="M62 112 L90 124 M138 112 L110 124" stroke="#8a1f1f" stroke-width="6" stroke-linecap="round" />
    <template v-if="pose === 'idle'">
      <circle cx="80" cy="132" r="8" fill="#1e1e1e" /><circle cx="120" cy="132" r="8" fill="#1e1e1e" />
      <circle cx="82" cy="129.5" r="2.8" fill="#fff" /><circle cx="122" cy="129.5" r="2.8" fill="#fff" />
    </template>
    <path v-else-if="pose === 'hit'" d="M71 125 L88 133 L71 141 M129 125 L112 133 L129 141" stroke="#1e1e1e" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round" />
    <path v-else d="M72 125 L88 141 M88 125 L72 141 M112 125 L128 141 M128 125 L112 141" stroke="#1e1e1e" stroke-width="6" fill="none" stroke-linecap="round" />
    <!-- monocle -->
    <circle cx="80" cy="132" r="13" fill="none" stroke="#ffc107" stroke-width="3.5" />
    <path v-if="pose === 'defeated'" d="M72 122 L80 133 L90 140 M84 120 L80 133" stroke="#ffc107" stroke-width="1.5" fill="none" />
    <path d="M69 144 C64 156 66 166 70 172" stroke="#ffc107" stroke-width="2" fill="none" />
    <!-- mouth and cigar -->
    <path v-if="pose === 'idle'" d="M88 152 Q98 148 108 152" stroke="#1e1e1e" stroke-width="3" fill="none" stroke-linecap="round" />
    <path v-else d="M89 156 Q98 150 108 156" stroke="#1e1e1e" stroke-width="3" fill="none" stroke-linecap="round" />
    <g v-if="pose !== 'defeated'">
      <path d="M104 156 L140 142" stroke="#8a5530" stroke-width="9" stroke-linecap="round" />
      <path d="M138 143 L146 140" stroke="#e8702a" stroke-width="9" stroke-linecap="round" />
    </g>
    <!-- top hat: on his head, or knocked off -->
    <g :transform="pose === 'defeated' ? 'translate(54 52) rotate(32 100 70)' : ''">
      <rect x="72" y="40" width="56" height="38" rx="5" fill="#1e1e1e" />
      <rect x="72" y="64" width="56" height="10" fill="#ffc107" />
      <rect x="58" y="74" width="84" height="9" rx="4.5" fill="#1e1e1e" />
      <text x="100" y="60" text-anchor="middle" font-family="Nunito, sans-serif" font-weight="900" font-size="18" fill="#ffc107">R</text>
    </g>
    <!-- briefcase and money bag: gone when he is bankrupt -->
    <g v-if="pose !== 'defeated'">
      <rect x="18" y="168" width="34" height="26" rx="4" fill="#5c3a1e" /><rect x="30" y="176" width="10" height="7" fill="#ffc107" />
      <rect x="22" y="161" width="30" height="9" rx="2" fill="#4caf50" transform="rotate(-6 37 165)" />
      <path d="M158 178 Q146 190 150 204 Q160 212 172 204 Q176 190 164 178 Z" fill="#c8a24a" />
      <path d="M155 178 H167 L165 172 H157 Z" fill="#a8822c" />
      <text x="161" y="198" text-anchor="middle" font-family="Nunito, sans-serif" font-weight="900" font-size="16" fill="#1e1e1e">$</text>
    </g>
  </svg>
</template>

<style scoped>
.robbee { display: block; overflow: visible; }
.robbee { transform-origin: 50% 70%; }
.bob { animation: robbee-bob 2.4s ease-in-out infinite; transform-origin: 50% 100%; }
.pose-hit { animation: robbee-hit .5s ease-out both; }
.pose-defeated { animation: robbee-fall 1.4s cubic-bezier(.4, 0, .6, 1) forwards; }
@keyframes robbee-hit {
  0% { transform: translateX(0) scale(1); filter: brightness(1); }
  15% { transform: translateX(-10px) rotate(-6deg) scale(.94); filter: brightness(2.2) saturate(.4); }
  35% { transform: translateX(9px) rotate(5deg); }
  60% { transform: translateX(-5px) rotate(-2deg); filter: brightness(1.1); }
  100% { transform: translateX(0) rotate(0); filter: brightness(1); }
}
@keyframes robbee-fall {
  0% { transform: translateY(0) rotate(0); }
  35% { transform: translateY(-18px) rotate(-14deg); }
  100% { transform: translateY(46px) rotate(98deg) scale(.92); }
}
@keyframes robbee-bob { 0%, 100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-4px) rotate(-2deg); } }
@media (prefers-reduced-motion: reduce) { .bob, .pose-hit { animation: none; } .pose-defeated { animation: none; transform: rotate(98deg) translateY(30px); } }
</style>
