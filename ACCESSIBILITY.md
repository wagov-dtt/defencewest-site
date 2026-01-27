# Accessibility

This site aims to conform to [WCAG 2.2 Level AA](https://www.w3.org/TR/WCAG22/).

## Architecture for Accessibility

This site uses a **static-first architecture** that inherently supports accessibility and SEO:

### Minimal JavaScript

- **Progressive enhancement**: All content is server-rendered HTML; JavaScript adds interactivity but isn't required for core functionality
- **No framework overhead**: Vanilla JavaScript only, reducing complexity and failure modes
- **Graceful degradation**: With JavaScript disabled, users still see all companies and can navigate via taxonomy pages

### Static Generation & Preprocessing

- **Pre-rendered content**: All company pages, taxonomy pages, and the directory are generated at build time as static HTML
- **Pre-computed data**: Search text and filter data are computed during build, not at runtime
- **Static map images**: Minimap thumbnails are pre-rendered as PNG images, ensuring they work without JavaScript and load instantly
- **Semantic HTML output**: Hugo templates generate clean, semantic markup that assistive technologies can parse reliably

### SEO & Accessibility Alignment

The same techniques that support accessibility also benefit SEO:

- Semantic landmarks (`<main>`, `<nav>`, `<article>`) help both screen readers and search engines understand page structure
- Pre-rendered content is immediately indexable by search engines
- Descriptive URLs (`/company/company-name/`, `/regions/perth/`) are human-readable and assistive-tech friendly

## Accessibility Features

### Navigation

- **Skip link**: Press Tab on page load to reveal "Skip to main content" link
- **Keyboard navigation**: All interactive elements accessible via Tab, Enter, Space
- **Focus indicators**: Visible focus outlines on all focusable elements
- **Logical tab order**: Focus moves through elements in a meaningful sequence

### Screen Reader Support

- **Semantic HTML**: Proper use of landmarks (`<main>`, `<nav>`, `<article>`, `<aside>`)
- **ARIA live regions**: Filter result counts announced automatically
- **Descriptive labels**: Form inputs and interactive elements have accessible names
- **Alt text**: All meaningful images have descriptive alt text

### Visual Accessibility

- **Color contrast**: Text meets WCAG AA contrast requirements (via PicoCSS)
- **Reduced motion**: Animations disabled when `prefers-reduced-motion` is set
- **Responsive design**: Content accessible at all viewport sizes
- **Print styles**: Optimized layout for printing

### Touch Accessibility

- **Touch targets**: Minimum 44px tap targets on touch devices
- **Touch gestures**: All interactions work with simple tap (no complex gestures required)

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search input |
| `Escape` | Close mobile filter panel or clear search |
| `Tab` | Move focus forward |
| `Shift+Tab` | Move focus backward |
| `Enter` | Activate buttons, links, checkboxes |
| `Space` | Activate buttons, toggle checkboxes |

## Testing Approach

### Manual Testing

- Keyboard-only navigation testing
- Screen reader testing (VoiceOver on macOS, NVDA on Windows)
- High contrast mode verification
- Zoom testing (up to 200%)
- Browser DevTools accessibility audit (Lighthouse)

### Automated Testing (CI)

- **HTML validation**: superhtml (`mise run htmlcheck`)
- **Link checking**: lychee (`mise run linkcheck`)
- **Accessibility testing**: pa11y-ci (`mise run a11ycheck`)

The pa11y tests run in CI where Chromium is available. For local a11y testing, use browser DevTools:
1. Open Chrome/Edge DevTools (F12)
2. Go to Lighthouse tab
3. Select "Accessibility" category
4. Run audit

## Known Limitations

1. **Map interaction**: The interactive map is optimized for mouse/touch; keyboard users can use the directory view or taxonomy pages for equivalent functionality
2. **Third-party controls**: MapLibre GL navigation controls have limited keyboard support
3. **Icon filters**: Icon-based filters use custom keyboard handling (Enter/Space to toggle)

## Reporting Issues

If you encounter accessibility barriers:

1. Open an issue on GitHub
2. Describe the problem and how you encountered it
3. Include your browser, operating system, and assistive technology (if applicable)
4. Suggest a solution if you have one

We take accessibility seriously and will address reported issues promptly.

## Standards Reference

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) - Web Content Accessibility Guidelines (current)
- [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/) - Accessible Rich Internet Applications
- [HTML Living Standard](https://html.spec.whatwg.org/) - Semantic HTML elements

### Why WCAG 2.2?

WCAG 2.2 (October 2023) is the current W3C recommendation. Key additions over 2.1 include:

- **2.4.11 Focus Not Obscured**: Focused elements must be at least partially visible
- **2.4.13 Focus Appearance**: Enhanced focus indicator requirements
- **2.5.7 Dragging Movements**: Alternatives for drag operations
- **3.2.6 Consistent Help**: Help mechanisms in consistent locations
- **3.3.7 Redundant Entry**: Don't require re-entering previously provided info

WCAG 3.0 is still in development and not yet a recommendation.
