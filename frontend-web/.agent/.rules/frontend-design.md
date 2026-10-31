# Faultline Frontend Design Rules

Project name: **Faultline**. Use this name everywhere (UI copy, titles, metadata, comments, docs). Never invent or use any other product name.

Location in repo: `frontend-web/.agent/rules/frontend-design.md`

---

## 1. Source of truth

1. Designs live in Stitch. Always fetch the screen through the Stitch MCP before building a page. Do not design from imagination.
2. If the Stitch screen and these rules conflict on layout or visuals, Stitch wins. On code structure, these rules win.
3. If a screen is missing in Stitch, build it using existing tokens and components, keep it minimal, and flag it in the final summary.

## 2. Stack (fixed)

- Next.js (App Router), TypeScript strict
- Tailwind CSS + shadcn/ui (Radix primitives)
- TanStack Query for server state
- react-hook-form + zod for forms
- lucide-react for icons
- Do not add new UI libraries without asking.

## 3. Folder rules

Follow the existing structure in `frontend-web/src`:

- `app/`: routing only. Pages and layouts stay thin. No business logic.
- `features/<domain>/`: `api.ts`, `hooks.ts`, `schemas.ts`, `types.ts`, `components/`.
- `components/ui/`: shadcn primitives only.
- `components/layout/`: sidebar, topbar, page header, auth shell.
- `components/brand/`: logo and brand assets.
- `lib/`: api client, auth helpers, query client, utils.

Rules:

- A feature never imports another feature's internals.
- Only `features/*/api.ts` talks to the backend. Components never call `fetch`.
- Dependency direction: `app → features → components/lib`. Never reverse.

## 4. Design tokens

- Pull colors, typography, radius, and spacing from the Stitch design system.
- Map them once to CSS variables in `app/globals.css` and expose them in `tailwind.config.ts`.
- Never hardcode hex values, px font sizes, or random spacing in components. Use tokens and Tailwind scale only.
- Support light and dark mode through the same variables.
- Semantic tokens required: `background`, `foreground`, `card`, `muted`, `border`, `primary`, `destructive`, `success`, `warning`, `ring`.
- Admin side uses a slightly altered palette. Implement it as a theme override with `data-theme="admin"` on the admin layout root. Same token names, different values. Never fork components for admin.

## 5. Brand and logo

- Use a sample placeholder logo for now: `components/brand/logo.tsx`.
- Placeholder = simple SVG mark + the word "Faultline". Mark color uses `currentColor` or the primary token.
- Export two parts: `<LogoMark />` and `<Logo />` (mark + wordmark). All pages import from here only.
- Never inline the logo in pages. Replacing the real logo later must be a one-file change.
- Page titles format: `Page name | Faultline`.

## 6. Components

- Build on shadcn/ui. Wrap or extend, do not rewrite.
- Reuse before creating. Check `components/ui` and `components/layout` first.
- One component = one job. Keep files under about 150 lines. Split when larger.
- Use `cn()` helper for class merging. No inline `style` unless dynamic values require it.
- Icons: lucide-react only, consistent size (16 / 20 / 24).

## 7. Forms

- react-hook-form + zod resolver. Schema lives in `features/<domain>/schemas.ts`.
- Show inline field errors under the input. Show server errors in a form-level alert.
- Disable the submit button and show a spinner while submitting.
- Every input has a visible label, correct `type`, `autocomplete`, and `aria` attributes.

## 8. States (mandatory for every data view)

Every page or data component must handle:

- Loading: skeletons, not spinners, for content areas.
- Empty: clear message plus a primary action.
- Error: readable message plus a retry action.
- Success: toast for mutations.

## 9. Responsive and accessibility

- Desktop-first, must stay usable down to tablet. Auth pages must work on mobile.
- Keyboard navigable, visible focus ring, semantic HTML, WCAG AA contrast.
- Buttons are `button`, links are `a`/`Link`. No clickable divs.

## 10. Auth and routing conventions

- Route groups: `(auth)` for login, signup, verify-email. `(dashboard)/[workspaceSlug]/...` for the app. `(admin)` for the admin console.
- `[workspaceSlug]` is for navigation only. The real workspace comes from the JWT claim. Never trust the slug for authorization.
- Auth pages use a shared `AuthShell` layout (centered card, logo above).
- Never store tokens in code or logs. Use the helpers in `lib/auth/`.

## 11. Copy and content

- Product name is always "Faultline".
- Short, direct, developer-friendly copy. No marketing fluff in the app UI.
- Sample or placeholder data must look realistic (error names, stack traces, project names) and never reference other products or companies.

## 12. Definition of done (per page)

- [ ] Matches the Stitch screen
- [ ] Uses tokens only, no hardcoded colors
- [ ] Loading, empty, error states handled
- [ ] Form validation with zod
- [ ] Keyboard and screen-reader friendly
- [ ] Light and dark mode checked
- [ ] No lint or type errors
- [ ] Logo imported from `components/brand/logo.tsx`
