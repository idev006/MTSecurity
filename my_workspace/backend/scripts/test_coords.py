import sys
from pathlib import Path
sys.path.insert(0, str(Path("d:/dev/MTSecurity/my_workspace/backend")))

import numpy as np
import cv2
from config import get_settings
from ai.model_registry import ModelRegistry
from ai.inference_engine import InferenceEngine
from ai.detector import postprocess_yolo
from ingestion.frame_codec import resize_for_inference

def test_infer_on_image():
    # 1. create a synthetic image of a white square on black background
    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    cv2.rectangle(frame, (150, 50), (170, 150), (255, 255, 255), -1) # "Person" like rectangle in middle
    
    cfg = get_settings()
    model_reg = ModelRegistry(device="CPU")
    engine = InferenceEngine(model_reg, "yolo11n", cfg.model_path)
    
    blob, scale, pad_top, pad_left = resize_for_inference(frame, 640)
    print(f"Scale: {scale}, Pad Top: {pad_top}, Pad Left: {pad_left}")
    
    outputs, _ = engine.infer(blob)
    raw = outputs[0]
    if raw.ndim == 3: raw = raw[0]
    raw = raw.T
    
    # Let's see the max confidence box
    conf = raw[:, 4:].max(axis=1)
    best_idx = np.argmax(conf)
    print(f"Best raw box (cx,cy,w,h): {raw[best_idx, :4]}, Conf: {conf[best_idx]}")
    
    det = postprocess_yolo(
        outputs,
        orig_w=640,
        orig_h=360,
        pad_top=pad_top,
        pad_left=pad_left,
        scale=scale,
        confidence_threshold=0.1
    )
    for d in det[:1]:
        print(f"Postprocessed: {d}")

if __name__ == "__main__":
    test_infer_on_image()
