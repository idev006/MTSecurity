# Troubleshooting Log: Advanced Rule Engine & UI Enhancements
**Date:** 2026-05-12
**Scope:** Rule Engine Logic, AI Label Handling, and Frontend Visualization

---

## 1. AI Detection "nan" Label Handling
### **Problem**
In some lighting conditions or specific camera angles, the AI detector was emitting a label of `nan` (Not a Number) instead of `person`. Because the Security Rules were strictly looking for the string "person", the alarm failed to trigger even when a person was clearly inside the zone.

### **Solution**
Updated `backend/rules/logic_validator.py` to handle "noisy" labels:
- Added **Case-Insensitive** comparison for all object classes.
- Implemented a **Safety Fallback**: If a detection has a `nan` or `none` label but is found inside a restricted zone, and the rule is looking for a `person`, the system now treats it as a potential match and triggers the alarm for maximum security.

---

## 2. Rule Engine Internal Import Error
### **Problem**
During the evaluation of complex rules, the backend crashed with an `ImportError: cannot import name 'BehaviorResult' from 'rules.behaviors.base'`. This was due to a legacy naming convention mismatch during the transition to the new Logic Tree architecture.

### **Solution**
Refactored `backend/rules/rule_engine.py`:
- Renamed the import and usage from `BehaviorResult` to `TriggerResult` to align with the standardized behavior plugin interface.
- Verified that the `RULE_TRIGGERED` payload is correctly populated with the detection confidence and metadata.

---

## 3. Missing Zone Overlays in Pilot View
### **Problem**
The Pilot (Cockpit) view was successfully showing AI bounding boxes but failed to render the red dashed lines (Security Zones), despite them being correctly configured and enabled in the UI settings.

### **Solution**
Fixed a data processing error in `frontend/src/views/PilotView.vue`:
- **The Root Cause:** The backend Pydantic models were already parsing coordinates into native JavaScript arrays, but the frontend was attempting a redundant `JSON.parse()` call, which threw an error and silenced the rendering.
- **The Fix:** Updated `scaleCoords` and `getCentroid` to handle both raw JSON strings and pre-parsed arrays, ensuring robust rendering regardless of the data source.

---

## 4. Advanced Logic: AND/OR Precedence
### **Problem**
Users were confused about how to set up logic like `Time AND (Dog OR Cat)`.

### **Solution**
- Refactored `RuleLogicBuilder.vue` to support **Nested Groups**.
- Standardized the UI to show explicit **AND/OR separators** between conditions to improve readability.
- Added a wide range of new object classes (animals, vehicles, items) to the selection list to support diverse monitoring scenarios.

---

## 5. Persistence & Edit Mode
### **Problem**
Users had to delete and recreate rules to make changes, which was inefficient for complex logic trees.

### **Solution**
- Implemented **PATCH** support in the Rules API.
- Integrated `SchedulePicker.vue` directly into the Edit Modal.
- Enabled automatic loading of recursive JSON logic into the builder when clicking the "Edit" (Pencil) icon.
---

## 6. Missing Overlays in Alert Snapshots
### **Problem**
While the live video feed showed bounding boxes, the captured snapshots (JPEG evidence) were raw frames with no annotations. This made it difficult for security officers to review exactly what triggered an alarm after the fact.

### **Solution**
Refactored the Alert/Snapshot pipeline:
- **RuleEngine Update:** Modified to pack the detection's `label` and `bbox` into the `RULE_TRIGGERED` message metadata.
- **AlertManager Update:** Upgraded the snapshot handler to extract this metadata and invoke `annotate_frame` before saving the image to disk.
- **Result:** Evidence images now have "Burned-in" overlays showing the object class, track ID, and confidence score, matching the live view.
