# Design System Notes

Implementation concept: `docs/design/ed-disposition-v3-concept.png`.

## Product Shape

- Research dashboard, not landing page.
- Left rail step navigation.
- Central workflow panel for safety, intake, worksheet, results, and report.
- Right evidence pane for endpoint rules and sources.
- Mobile collapses into stacked navigation, workflow, then evidence.

## Tokens

- Background: warm off-white `#f7f6f2`
- Surface: white/card `#ffffff`
- Text: ink `#172129`
- Muted text: slate `#60707a`
- Border: cool gray `#d8dedc`
- Primary: teal `#0f766e`
- Accent: amber `#d8a523`
- Destructive/safety: red `#b42318`
- Card radius: 8px via `rounded-lg`

## Typography

- Geist variable font with system fallbacks.
- Dense dashboard labels and controls.
- No viewport-scaled font sizes and no negative tracking.

## Component Rules

- shadcn/ui source components for buttons, cards, alerts, badges, field groups, tabs, selects, tables, progress, and toggle groups.
- Recharts for histogram and sensitivity ranking.
- No nested cards. Tables and metric rows sit inside top-level panels.
- Safety/eligibility gate blocks probability surfaces.
