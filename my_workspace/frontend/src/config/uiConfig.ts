/**
 * UI display configuration — tweak these values to adjust overlay appearance
 * without touching component logic.
 */
export const UI_CONFIG = {
  overlay: {
    /** Font size (px) for bounding box label text — SVG viewBox units (640×360 default) */
    labelFontSize: 14,
    /** Background rect height (px) — should be ~labelFontSize + 6 */
    labelHeight: 20,
    /** Left padding inside label rect (px) */
    labelPaddingX: 4,
    /** Estimated character width (px) used to size the label background rect */
    labelCharWidth: 8.5,
    /** Bounding box stroke width (px) */
    boxStrokeWidth: 2,
    /** Centroid dot radius (px) */
    centroidRadius: 4,
  },
}
