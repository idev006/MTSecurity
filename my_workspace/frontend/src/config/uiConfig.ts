/**
 * UI display configuration — tweak these values to adjust overlay appearance
 * without touching component logic.
 */
export const UI_CONFIG = {
  overlay: {
    /** Font size (px) for bounding box label text */
    labelFontSize: 6,
    /** Background rect height (px) — should be ~labelFontSize + 4 */
    labelHeight: 10,
    /** Left padding inside label rect (px) */
    labelPaddingX: 2,
    /** Estimated character width (px) used to size the label background rect */
    labelCharWidth: 5.5,
    /** Bounding box stroke width (px) */
    boxStrokeWidth: 1.5,
    /** Centroid dot radius (px) */
    centroidRadius: 3,
  },
}
