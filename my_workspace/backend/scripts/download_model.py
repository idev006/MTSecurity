from pathlib import Path
from ultralytics import YOLO
import shutil

def main():
    base_dir = Path(__file__).parent.parent
    model_dir = base_dir / "data" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading YOLO11n model...")
    model = YOLO("yolo11n.pt")
    
    print("Exporting to OpenVINO format...")
    # This creates a folder named yolo11n_openvino_model
    export_dir = model.export(format="openvino")
    
    print(f"Exported to: {export_dir}")
    
    src_dir = Path(export_dir)
    
    # Move the OpenVINO files to our models directory
    print("Moving files to data/models...")
    for file in src_dir.iterdir():
        dest = model_dir / file.name
        shutil.copy2(file, dest)
        print(f"Copied {file.name} to {dest}")
        
    # Cleanup
    shutil.rmtree(src_dir)
    pt_file = Path("yolo11n.pt")
    if pt_file.exists():
        shutil.copy2(pt_file, model_dir / "yolo11n.pt")
        pt_file.unlink()
        
    print(f"Successfully prepared models in {model_dir}")

if __name__ == "__main__":
    main()
