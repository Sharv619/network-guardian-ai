# Network Guardian AI - Design Guidelines

This project uses Impeccable design principles for frontend development.

## Design Principles

### Typography
- Use distinctive, purposeful fonts - avoid generic choices like Inter or Arial
- Implement proper type scales and modular typography
- Ensure readable line heights and character spacing

### Color & Contrast
- Never use gray text on colored backgrounds
- Avoid pure black (#000000) - always tint with color
- Use OKLCH color space for consistency
- Ensure WCAG accessibility compliance

### Spatial Design
- Use consistent spacing systems (not arbitrary pixels)
- Don't over-card everything - use whitespace intentionally
- Create clear visual hierarchy through spacing

### Motion
- Avoid bounce/elastic easing (feels dated)
- Use purposeful, meaningful animations
- Respect reduced-motion preferences
- Implement proper staggering for lists

### Interaction
- Design clear focus states for accessibility
- Create meaningful loading patterns
- Provide clear feedback on user actions

### Anti-Patterns to Avoid
- ❌ Nested cards inside cards
- ❌ Generic Inter font
- ❌ Purple/blue gradients everywhere
- ❌ Gray text on colored backgrounds
- ❌ Pure black on white
- ❌ Bounce animations

## Available Commands
When working with AI coding agents, use:
- `/audit` - Check for design issues
- `/polish` - Final design cleanup
- `/normalize` - Align with design system
- `/distill` - Simplify the design
