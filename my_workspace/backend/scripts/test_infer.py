import asyncio
import numpy as np
from pathlib import Path

def test_inference():
    import sys
    sys.path.insert(0, str(Path("d:/dev/MTSecurity/my_workspace/backend")))
    from config import get_settings
    from ai.model_registry import ModelRegistry
    from ai.inference_engine import InferenceEngine
    from ai.detector import postprocess_yolo
    
    cfg = get_settings()
    model_reg = ModelRegistry(device=cfg.model_device)
    engine = InferenceEngine(model_reg, "yolo11n", cfg.model_path)
    
    if not engine.is_ready:
        print("Engine NOT ready!")
        return
        
    print("Engine ready. Running dummy inference...")
    dummy_frame = np.zeros((360, 640, 3), dtype=np.uint8)
    
    from ingestion.frame_codec import resize_for_inference
    blob, scale, pad_top, pad_left = resize_for_inference(dummy_frame, 640)
    outputs, elapsed_ms = engine.infer(blob)
    
    print(f"Inference done in {elapsed_ms}ms. Output len: {len(outputs)}")
    
    detections = postprocess_yolo(
        outputs,
        orig_w=640,
        orig_h=360,
        input_size=640,
        confidence_threshold=cfg.ai_confidence_threshold,
    )
    print(f"Detections: {detections}")

if __name__ == "__main__":
    test_inference()
