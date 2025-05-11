# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config({
  extends: [
    // Remove ...tseslint.configs.recommended and replace with this
    ...tseslint.configs.recommendedTypeChecked,
    // Alternatively, use this for stricter rules
    ...tseslint.configs.strictTypeChecked,
    // Optionally, add this for stylistic rules
    ...tseslint.configs.stylisticTypeChecked,
  ],
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config({
  plugins: {
    // Add the react-x and react-dom plugins
    'react-x': reactX,
    'react-dom': reactDom,
  },
  rules: {
    // other rules...
    // Enable its recommended typescript rules
    ...reactX.configs['recommended-typescript'].rules,
    ...reactDom.configs.recommended.rules,
  },
})

```

---

## Project Chronos Progress (2025‑05‑11)

### ✅ What we’ve shipped so far

| Area | Milestone | Details |
|------|-----------|---------|
| **Backend API** | **/sos/{state}** demo scraper | Parses Delaware HTML sample and returns a `CorporateEntity`, then stores it in the in‑memory portfolio. |
| | **/status** snapshot | Aggregates entity counts by `Status`; used by the dashboard chart. |
| | **/search** unified lookup | Searches *both* the live portfolio (SQLite when enabled) and state scrapers; powers the React search page. |
| | CORS enabled | `fastapi.middleware.cors` allows the Vite dev server (`localhost:5173`) to call the API. |
| **Persistence** | SQLite schema & helpers | `chronos.db` + `portfolio_db.py` with `SQLModel`―entities survive process restarts once we swap the in‑memory store. |
| **Frontend** | Vite + React + TS scaffold | Project bootstrapped with `npm create vite@latest --template react-ts`. |
| | Tailwind 4 configured | PostCSS plugin added (`@tailwindcss/postcss`) and `index.css` wired up. |
| | **Search page** | `SearchForm`, `useApi` hook, and `Search` page fetch `/search` and render a basic results list + detail pane. |
| | **StatusChart** skeleton | Bar chart component renders; awaits live data from `/status`. |
| **Dev Tooling** | Hot‑reload loops | `uvicorn --reload` and `npm run dev` scripts documented; proxy free thanks to CORS. |

### 🔜 Next up (per the proposal)

1. **Polish UI/UX**
   - Style forms & results with Tailwind components.
   - Bind `StatusChart` to `/status` JSON for live counts.
   - Add empty‑state & loading spinners.

2. **Entity CRUD**
   - Wire *Add → Portfolio* button to `POST /entities`.
   - Inline “lifecycle” transitions → `PATCH /entities/{slug}`.

3. **Ownership graph**
   - New API route `/graph` to expose parent/child edges.
   - React canvas (e.g. D3 force graph) on `/dashboard`.

4. **SQLite switch‑over**
   - Enable `SQLITE_URL` env var, call `create_all()` at startup, and persist scraper inserts.

5. **Finishing touches**
   - README gif of the dashboard.
   - Dockerfile for full‑stack dev spin‑up.

_The immediate focus is **Step 1 – front‑end polish** so we have a demo‑ready interface for the live presentation._

---
