# Jobee frontend (Vue 3)

Vue 3 + Vite + vue-router implementation of the Jobee Figma flows (A Undergrad, B Fresh grad, C Working engineer, 11 screens each). All content is sample data in `src/data/flows.ts`; no backend calls yet.

```sh
cd src/frontend
npm install
npm run dev        # http://localhost:5173
npm run typecheck
npm run build
```

Routes are `/:persona(a|b|c)/:step`. A floating switcher (bottom-left) jumps between flows and screens.

Note: Flow A screens 09 and 11 and all of Flows B and C use placeholder content/layouts pending the Figma designs.
