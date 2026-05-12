# Implementation Plan - Phase 2: Pilot's Console & LPR Expansion

This plan outlines the next steps to transform MTSecurity into a professional mission control center as envisioned in the v2 documentation.

## Goals
1. **Pilot's Console**: Create a unified control center view.
2. **LPR Management**: Implement License Plate Recognition whitelist management.
3. **Audit Visibility**: Expose audit logs in the UI.
4. **Enhanced Stability**: Refine background tasks and notification dispatching.

## Proposed Changes

### [NEW] Pilot's Console (Frontend)
- **File**: `frontend/src/views/PilotView.vue`
- **Design**:
    - Layout: Left side for Primary Feed (Top) and Camera Grid (Bottom). Right side for Alert Queue and System Health.
    - Integration: Uses `useCamerasStore`, `useEventsStore`, and `useSystemStore`.
    - Functionality: Clicking a camera in the grid switches the primary feed. Real-time alert popups.

### [NEW] LPR Management (Backend)
- **File**: `backend/api/routers/lpr.py`
- **Features**:
    - CRUD endpoints for `LPRWhitelist` model.
    - Search by plate number.
    - Audit logging for every change (via existing middleware).

### [NEW] LPR Management (Frontend)
- **File**: `frontend/src/views/LPRView.vue`
- **Features**:
    - Table of whitelisted plates.
    - Modal for adding/editing plates.
    - Integration with the new LPR API.

### [MODIFY] Navigation & Routing
- **File**: `frontend/src/router/index.ts`
    - Register `/pilot` and `/lpr`.
- **File**: `frontend/src/components/AppLayout.vue`
    - Add "Pilot's Console" and "LPR Whitelist" to the sidebar.

## Verification Plan
1. **Manual Test**: Verify the Pilot's Console updates in real-time when an alert is triggered (using the `/simulate/detection` API).
2. **Manual Test**: Add, Edit, and Delete LPR entries and verify they persist in the database.
3. **Audit Check**: Verify that LPR mutations appear in the `audit_logs` table.

## Open Questions
- Do you have a **LINE Notify Token** or **Discord Webhook** you'd like to test with now?
- For the Pilot's Console, should we make it the **default landing page** after login?
