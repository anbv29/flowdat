# SignalDesk glass interface

The frontend is an analytical workspace with translucent navigation and controls above readable data surfaces.

## Tokens

- Canvas: `#edf0f7`; background mixes pale blue and cool neutral surfaces.
- Foreground: `#182339`; secondary text: `#58657a`.
- Action accent: `#425bc0`.
- Glass surface: `rgba(255,255,255,.64)`.
- Rules: `rgba(58,76,111,.13)`.
- Elevation: offset, diffuse shadows with an inset white reflection.
- Blur: 20–32px on navigation, dialogs, and floating controls.
- Corners: 12–18px on content and controls; 24px on the navigation rail.

## Behavior

Navigation floats beside the content on desktop and becomes a keyboard-accessible drawer on phones.
Dataset search filters existing sources by name or filename.
Analysis remains viewport-bound with independently scrolling panels and a visible composer.
At tablet widths dataset metadata wraps beneath the title so Open remains reachable.
Transitions use `cubic-bezier(.16,1,.3,1)`; the content arrival shifts by six pixels without hiding content.
Reduced-motion and increased-contrast preferences have explicit overrides.

## Scope

The visual layer is in `src/app/liquid.css`, loaded after the existing foundation and polish styles.
Backend files and HTTP contracts are unchanged.
