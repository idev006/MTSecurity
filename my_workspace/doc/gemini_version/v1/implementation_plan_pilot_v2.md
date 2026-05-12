# Implementation Plan: AI Real-time Overlay & Pilot's Console Completion

This document outlines the technical steps to achieve a full "Pilot's Console" (v2) with real-time AI overlays and professional control features.

## 1. AI Real-time Overlay System

### Goal
Render dynamic AI metadata (Bounding Boxes, Zone Polygons) directly on top of the live video feed in `PilotView.vue`.

### Technical Approach
- **Data Source**: Subscribe to WebSocket messages of type `TRACK_UPDATE`.
- **Rendering Engine**: Use an **SVG layer** positioned absolutely over the primary video `<img>` tag.
- **Coordinate Mapping**: 
    - AI provides normalized coordinates `(0.0 to 1.0)`.
    - Frontend will calculate: `pixel_x = normalized_x * video_width`.
- **Zone Visualization**: Fetch zone coordinates from `ZonesStore` and render them as semi-transparent polygons.

### Tasks
- [ ] Implement `OverlayLayer.vue` component.
- [ ] Connect WebSocket `TRACK_UPDATE` to the store and then to `PilotView`.
- [ ] Add logic to "fade out" bboxes when updates stop (prevent ghosting).
- [ ] Implement responsive resizing (re-calculating BBoxes when window resizes).

---

## 2. Pilot's Console Completion (Full Capability)

### Goal
Transform the current layout into a high-efficiency mission control center.

### A. Advanced HUD (Heads-Up Display)
- [ ] **Object Labels**: Display `Class Name` (e.g., Person) and `Confidence` score above each BBox.
- [ ] **Zone Names**: Show the name of the zone on the overlay.
- [ ] **Active Indicator**: Change the border color of the primary feed based on the active rule's severity.

### B. Keyboard Shortcuts (The "Pilot" Experience)
- [ ] `Space`: Acknowledge the most recent active alert.
- [ ] `1-9`: Switch Primary Feed to Camera 1-9.
- [ ] `0`: Switch to Camera 10.
- [ ] `F`: Toggle Fullscreen for the Primary Feed.
- [ ] `Esc`: Close any open Snapshot modals.

### C. Enhanced Alert Queue
- [ ] **Filter Toggle**: Add "Show High Only" and "Hide Acknowledged" buttons.
- [ ] **Inline Notes**: Allow operators to type a quick note before clicking ACK.
- [ ] **Escalation Button**: Integration with LINE Notify (triggering the backend escalation flow).

### D. System Health & Telemetry
- [ ] **Camera Bitrate/FPS**: Display actual FPS and estimated bandwidth usage per camera.
- [ ] **AI Latency**: Display the time taken for the last inference cycle (from `HEALTH_BEAT`).

---

## 3. Implementation Workflow

1. **Phase A (The Eyes)**: Implement Real-time Overlay (BBoxes + Zones).
2. **Phase B (The Hands)**: Implement Keyboard Shortcuts and UI Action refinements.
3. **Phase C (The Details)**: Implement Telemetry and Queue Filtering.

## 4. Verification Plan
- **Real-time Latency**: Ensure the overlay matches the movement in the video (visual sync).
- **Stress Test**: Verify the UI remains responsive with 50+ objects being tracked simultaneously.
- **Usability**: Test that all keyboard shortcuts work without focus conflicts.
