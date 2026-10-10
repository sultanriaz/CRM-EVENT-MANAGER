# Design System

- Tokens: scoped background, surface, text, muted, border, brand, accent, blue, and shadow CSS variables.
- Themes: light default; dark mode scoped to Campus LWC and persisted with `localStorage`; native Lightning global dark mode is not forced.
- Layout: five-column KPI grid and two-column dashboard content; record workspaces use a responsive header, wrapping filter toolbar, contained data table, and mobile stacking.
- Components: SLDS Lightning buttons/icons/inputs/comboboxes/datatable/formatters, semantic sections, focus-visible treatment, status pills, skeletons, pagination, empty and error states.
- Motion: subtle color transitions and skeleton shimmer; animation is disabled for `prefers-reduced-motion`.
- Native record forms and Salesforce analytics inherit org theme and SLDS; cross-shadow-DOM global overrides are intentionally avoided.
