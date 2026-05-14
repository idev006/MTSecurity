# MTSecurity Frontend UI/UX Overhaul & Performance Tuning

This document details the changes and improvements made during the frontend UI/UX overhaul, specifically focusing on the integration of DaisyUI v5, TailwindCSS v4, and performance optimizations.

## 1. Theme Switcher Implementation (DaisyUI v5)

We implemented a robust, fully client-side theme switcher that supports all 35 built-in themes provided by DaisyUI v5. The architecture avoids any jarring browser `alert()` popups and ensures themes persist across page reloads.

### `src/stores/theme.ts` (New Pinia Store)
A centralized Pinia store manages the application's theme state.
*   **Single Source of Truth**: Eliminates duplicated theme logic across different views (like `SettingsView` and `AppLayout`).
*   **LocalStorage Persistence**: The chosen theme (`mtsec_theme`) is saved to `localStorage`.
*   **Immediate Application**: The `setTheme` action immediately applies the `data-theme` attribute to the `<html>` tag, triggering a CSS variable swap.
*   **Boot Initialization**: The `init` method is called on application boot (in `App.vue`) to restore the saved theme before any child component renders, preventing a Flash of Unstyled Content (FOUC).

### `src/style.css` (CSS-First Configuration)
Leveraging the new DaisyUI v5 CSS-first approach, we enabled all 35 themes directly within the `@plugin` directive.
*   **Smooth Transitions**: We added a global CSS rule to apply a 150ms `transition` to color-related properties (`background-color`, `border-color`, `color`, etc.). This makes theme switching feel fluid and premium rather than instantaneous and jarring.
*   **Performance Exclusions**: We explicitly disabled these transitions on performance-sensitive elements like `<canvas>`, `<video>`, `<progress>`, and elements with the `data-no-transition` attribute to prevent UI stuttering.

### `src/App.vue`
Added the initialization call to `themeStore.init()` within the `onMounted` hook to ensure the persisted theme is applied as early as possible in the Vue lifecycle.

## 2. Component Refactoring & Premium UI

We focused on enhancing the visual appeal and code maintainability of key components.

### `src/components/AppLayout.vue`
*   **Theme Switcher Dropdown**: Added a new dropdown menu in the top navigation bar. It displays all 35 themes with mini color swatches (Primary, Secondary, Accent) representing each theme's palette, allowing users to visually preview the theme before clicking.
*   **Data-Driven Navigation**: Refactored the sidebar navigation items into a computed array (`navItems`). This significantly reduces HTML template bloat by rendering the links via a `v-for` loop, eliminating repetitive SVG icon markup.
*   **Accessibility (a11y)**: Added `aria-label` and `aria-hidden="true"` attributes to various buttons and icons for improved screen reader support.

### `src/views/LoginView.vue`
*   **Premium Aesthetics**: Redesigned the login page to feel more modern.
    *   Added a subtle, animated SVG grid background.
    *   Included a decorative "glowing orb" behind the login card for depth.
    *   The card itself uses a glassmorphism-inspired design with pronounced shadows (`shadow-2xl`).
*   **Accessible Theme Switcher**: Placed a minimal, glass-styled theme switcher in the top-right corner, allowing users to choose their preferred theme *before* logging in.
*   **UX Improvements**: Added `autofocus` to the username field and implemented `.trim()` on the username input before submission to prevent accidental trailing spaces from causing authentication failures.

### `src/views/SettingsView.vue`
*   **Logic Deduplication**: Removed the local, hardcoded theme logic and replaced it entirely with the shared `useThemeStore`.
*   **Enhanced Theme Preview**: The "Display" tab now renders all 35 themes as clickable buttons, complete with 4-color swatches (Primary, Secondary, Accent, Neutral) rendered in the context of that specific theme, providing a highly accurate preview.

## 3. Performance & Code Standard Improvements

We identified and resolved several performance bottlenecks and code standard issues.

### `src/composables/useUiHelpers.ts` (New Shared Composable)
Created a new composable to centralize repetitive UI formatting logic.
*   **Eliminated Copy-Paste**: Moved functions like `gaugeColor`, `progressColor`, `sevBadgeClass`, `statusBadgeClass`, and time formatters (`fmtTime`, `fmtDateTime`) into this single file.
*   **Consistency**: Ensured that the visual representation of states (like a camera being 'ONLINE' or an event being 'CRITICAL') is calculated identically across `DashboardView`, `EventsView`, `CamerasView`, and `SettingsView`.

### `src/views/EventsView.vue`
*   **Server-Side Filtering**: Fixed a significant performance flaw. Previously, filtering by "Behavior" (e.g., 'intrusion', 'loitering') was done entirely client-side *after* fetching a large batch of events. We updated the API call to pass `filters.value.behavior` to the backend, offloading the filtering work to the server and reducing payload sizes.
*   **Optimized Reactivity**: Refactored the `busy` state (used for disabling buttons while an API request is in flight) to use a `Set<number>` wrapped in a `ref`.

### `src/views/DashboardView.vue`
*   **Helper Integration**: Updated the component to import all color and formatting functions from `useUiHelpers.ts`, removing dozens of lines of duplicated code.
*   **Bug Fix**: Corrected an inconsistency in `gaugeColor` where it previously returned `text-base-content` for normal loads, which didn't align with the rest of the application's styling.

### TypeScript Compilation Fixes
Addressed pre-existing TypeScript compilation errors that were preventing the build (`npm run build`) from completing successfully:
1.  **`src/api/client.ts`**: Fixed `TS1294` (Erasable Syntax Only constraint) by removing the parameter property shorthand in the `ApiError` constructor and explicitly assigning the `status` property inside the constructor body.
2.  **`vite.config.ts`**: Fixed `TS6133` by removing an unused `wsUrl` variable that was a remnant of an older WebSocket configuration.

---
**Status**: Completed
**Date**: May 14, 2026
