# Ubundi Brand Guide

Apply this design language to every frontend surface unless the project brief explicitly overrides it.

## Brand posture

- The product should feel confident, modern, future-facing, and quietly premium.
- Prefer clarity and precision over hype, clutter, or visual noise.
- Interfaces should feel trustworthy, composed, and thoughtfully crafted.

## Color system

- The brand language combines deep indigo and navy presentation surfaces with luminous accent families.
- Use these published palette families when building tokens:
  - Plum: `#F5D9F4`, `#EBB3E9`, `#E18EDD`, `#D768D2`
  - Aqua: `#DDF6F9`, `#BAEDF3`, `#98E5EC`, `#75DCE6`
  - Electric violet: `#E8DBFE`, `#D0B7FD`, `#B992FB`, `#A16EFA`
  - Amber: `#FCEED5`, `#F9DDAB`, `#F6CC82`, `#F3BB58`
- Text on dark surfaces should stay near-white with strong contrast.
- Secondary text can soften toward cool greys, but should remain crisp and readable.
- Avoid flat white canvases and generic SaaS blues; the overall look should feel richer and more atmospheric.

## Surface treatment

- Dark, atmospheric presentation surfaces are the default brand expression.
- Use layered gradients, soft vignettes, fine texture, and diffused light blooms to create depth.
- Build hero areas and section dividers with blurred plum, aqua, violet, and amber glow fields over deep indigo backgrounds.
- Shadows should stay subtle; rely more on contrast, glow, texture, and soft edges than heavy elevation.

## Typography

- Use Manrope as the primary typeface.
- Support at least Light, Regular, and Bold weights.
- Follow the usage guidance from the brand file:
  - Headings: semibold, title case
  - Secondary headings: medium, sentence case
  - Body copy: light or regular, sentence case
  - Buttons and short UI labels: semibold, sentence case
- Type should feel crisp, spacious, and editorial rather than compressed or utilitarian.

## Components

- Buttons, chips, tabs, and inputs should feel sleek, modern, and intentional.
- Use clean geometry with rounded corners, but avoid bubbly or playful treatment.
- High-emphasis actions can use the brighter palette families, while neutral controls should sit comfortably on dark surfaces.
- Data-heavy UI should feel precise and professional, not casual or toy-like.

## Layout

- Use clear visual hierarchy with generous spacing around major sections.
- Favor strong alignment, broad margins, and deliberate asymmetry where it improves emphasis.
- Hero sections and dashboards should feel editorial and crafted, not template-like.
- Empty states, loading states, and onboarding surfaces should still look branded and polished.

## Motion

- Motion should be restrained and purposeful.
- Prefer short fades, subtle lifts, and staggered reveals over flashy transforms.
- Keep interactions smooth and premium, typically in the 150ms to 250ms range.

## Tone of voice

- Curious: speak with discovery, openness, and thoughtful exploration.
- Collaborative: use inclusive language and frame progress as shared effort.
- Credible: communicate with quiet confidence, clarity, and accuracy.
- Human: keep the voice warm, empathetic, and accessible.
- Visionary: point toward the future while staying grounded in real outcomes.
- Fluid: adapt the tone to context while keeping the overall brand coherent.

## Implementation guidance

- Encode this guide into reusable tokens and primitives: CSS variables, theme tokens, and shared component styles.
- Create starter components, page shells, and layout patterns that express the brand by default.
- Keep brand decisions centralized so new pages inherit the look without repeating styles.
