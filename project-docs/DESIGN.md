# UX/UI Design Specification

## 1. Design philosophy
IncidentIQ is built for production reliability work, not generic AI chat experiences. The interface should feel serious, operational, and trustworthy. Engineers need to scan quickly, assess status, and understand why a recommendation is being made before they trust it.

The product should feel like a high-quality SRE or DevOps console: dark, structured, precise, and focused on evidence.

## 2. Visual direction
- Dark operational interface with strong contrast
- Professional neutral surfaces and restrained accent colours
- Clear information hierarchy and readable typography
- Avoid decorative gradients, glassmorphism, or excessive motion
- Prioritise trust, clarity, and technical utility
- Use consistent visual distinction between current evidence, historical memory, AI hypotheses, and verified root cause

## 3. Brand identity
The brand should communicate reliability, learning, and operational expertise. The tone is calm, technical, direct, and evidence-driven.

Core message: “Every incident teaches the next investigation.”

## 4. Colour system
| Role | HEX | Use |
|---|---|---|
| Background Base | #0B1220 | shell background |
| Surface Primary | #111827 | cards and containers |
| Surface Secondary | #172033 | alternate panels |
| Surface Tertiary | #1F2937 | nested UI surfaces |
| Border Subtle | #2A3445 | dividers and outlines |
| Text Primary | #E5E7EB | headings and body |
| Text Secondary | #9CA3AF | secondary labels |
| Text Muted | #6B7280 | metadata |
| Critical | #F87171 | highest-risk incidents |
| High | #FB923C | severe incidents |
| Medium | #FBBF24 | moderate incidents |
| Low | #34D399 | low-risk incidents |
| Info | #60A5FA | neutral information |
| Warning | #FBBF24 | failure risk |
| Success | #34D399 | resolved or validated |
| Accent | #7C3AED | Hindsight and memory emphasis |
| Error | #EF4444 | critical warnings |

## 5. Typography
- Font: Inter, Segoe UI, sans-serif
- Headings: compact and strong
- Body: 14–16px
- Labels: 11–12px uppercase or small caps
- KPIs: 24–32px for numeric emphasis

## 6. Spacing system
Use an 8px spacing scale:
- 4px: tight icon spacing
- 8px: standard gaps
- 12px: metadata and compact alignment
- 16px: card padding
- 24px: section spacing
- 32px: large separation
- 48px: page-level rhythm

## 7. Layout grid
- 12-column desktop grid
- Sidebar: 240px
- Page content: max-width 1600 with gutters
- Cards: 16px padding
- Tables: dense rows with consistent alignment

## 8. Sidebar navigation
Navigation items:
- Dashboard
- Investigation Center
- Memory Inspector
- Postmortem Center
- Guided Demo

Rules:
- Persistent on desktop
- Collapsible on smaller screens
- Active nav item uses subtle accent tint or border
- Icons remain 18–20px with consistent stroke weight

## 9. Dashboard design
The dashboard should present the current health of the investigation environment.

Top row:
- Total incidents
- Open incidents
- Resolved incidents
- Critical incidents

Middle row:
- recent incidents list
- severity distribution chart
- recurrence alerts

Bottom row:
- memory health summary
- basic analytics card

## 10. Investigation Center design
This page is the operational core.

Layout:
- Left column: incident submission form
- Right column: AI summary, root causes, recommendations, and memory views

Form fields:
- service name
- environment
- severity
- logs
- deployment metadata
- owner or team

Analysis area:
- summary panel
- likely causes
- recommendation cards
- evidence links
- historical incident matches
- memory off versus memory on comparison
- warnings for known failures

## 11. Memory Inspector design
This page is evidence-first and audit-oriented.

Sections:
- active Hindsight recall results
- retained experiences
- successful resolutions
- failed troubleshooting paths
- conflict warnings
- timeline

Each memory result card should include:
- memory type
- incident reference
- summary
- verification status
- confidence or caution tag

## 12. Postmortem Center design
This page should feel like a writing and review workspace.

Sections:
- incident selection or list
- markdown preview
- lessons learned
- preventive recommendations
- download action

The layout should be calm and readable, allowing detailed review before export.

## 13. Reusable components
- page shell
- sidebar
- page header
- KPI cards
- cards
- tables
- filters
- buttons
- form groups
- warning banners
- timeline
- empty states
- charts
- modals/drawers

## 14. Buttons
Button styles:
- Primary: accent or blue fill, white text
- Secondary: muted dark surface with border
- Destructive: red for dangerous actions
- Minimal: text-only link actions

Sizes:
- small for compact actions
- medium for forms
- large for main CTAs

## 15. Forms
Rules:
- labels above fields
- clear helper text
- consistent spacing
- inline validation errors
- large text fields for logs and incident notes
- grouped sections for service and deployment metadata

## 16. Cards
Cards should contain no more than one primary concept each. Use them for:
- recommendations
- incident summaries
- memory cards
- failure warnings
- KPI metrics
- historical matches

Card design rules:
- 1px border
- 12px radius
- 16px internal padding
- subtle hover highlight

## 17. Tables
Use tables for incidents, metrics, and logs. Rules:
- clear header row
- readable monospace or numeric alignment when needed
- severity badges inline
- minimal but visible row hover
- sticky headers if list is long

## 18. Severity badges
- Critical: red, bold
- High: orange
- Medium: yellow
- Low: green

These badges should appear throughout the product with consistent styling.

## 19. Warning components
Use a warning pattern for:
- failed remediation paths
- memory conflict
- recurrence risk
- low confidence evidence

Pattern:
- amber or red background
- icon at left
- short reason text
- recommended action or next step

## 20. Memory evidence cards
These cards highlight the knowledge retrieved by Hindsight.

Include:
- memory type
- related incident ID
- relevant summary
- verification state
- confidence or caution

This visual treatment should distinguish memory evidence from ordinary generated text.

## 20.1 Evidence provenance styling
Each evidence item must have a clear provenance tag:
- Current incident evidence: neutral blue label
- Historical Hindsight memory: purple label
- AI-generated hypothesis: amber label
- Engineer-verified root cause: green label

The UI should allow users to distinguish each category without ambiguity. Historical memory may support a recommendation, but it must never appear as if it is equivalent to a verified root cause.

## 21. Timeline components
Use a vertical, linear timeline style with:
- time labels
- event titles
- event metadata
- connector line
- tags for memory and incident actions

## 22. Charts
- Bar charts for severity distribution
- Donut or ring chart for workload distribution
- Line charts for incident trends
- Small sparklines for trend health if used

Charts should remain readable in dark mode and avoid heavy gradient effects.

## 23. Loading states
- skeleton cards for dashboard metrics
- inline spinner for actions
- container-based loading for investigation results
- progress bars only if necessary

## 24. Empty states
Examples:
- No incidents yet
- No historical matches
- No Hindsight memory retained
- No postmortems available

Each empty state should describe why it is empty and what action the user can take next.

## 25. Error states
Examples:
- Hindsight recall failed
- Groq unavailable
- incident validation failed
- database error

Use red error containers with clear action guidance.

## 26. Interaction patterns
- Input flows should be structured and single-purpose.
- Recommendation cards appear directly next to the evidence they represent.
- Memory and timeline views should be expandable rather than hidden.
- Users should be able to switch between raw incident data and high-level recommendations without losing context.

## 27. Animation guidelines
Use restrained motion:
- 120–180ms for hover transitions
- 150–200ms for panel expansion
- subtle chart animations only when needed

Avoid heavy motion, parallax, or decorative transitions that reduce clarity.

## 28. Responsive design
- Desktop: multi-column layouts with sidebar and side panels
- Tablet: condensed but complete layout
- Mobile: stacked cards and simpler navigation

The app must remain usable when reviewing incident details and memory evidence.

## 29. Accessibility
- high contrast in dark mode
- keyboard focus states
- semantic headings
- accessible labels for buttons and forms
- readable text sizing and contrast ratios

## 30. Page-level layout specification
### Dashboard
- KPI cards in first row
- incident trend + severity chart in second row
- recent incidents + recurrence alerts in third row

### Investigation Center
- form on left, analysis on right
- evidence and recommendations in stacked cards
- warnings and recurrence details near the recommendation panel

### Memory Inspector
- summary bar at top
- memory cards in the main body
- timeline and conflict warnings below

### Postmortem Center
- left list of incidents
- right preview/editor
- export actions at top or right

## Summary design rules
- maintain an operational, enterprise feel
- use dark backgrounds with restrained accent colour
- keep evidence and memory signals clearly visible
- avoid generic AI SaaS visuals and high-noise decoration
- let users trust the product because it is clear, precise, and auditable
