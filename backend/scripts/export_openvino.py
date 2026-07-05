"""
Export YOLOv8n to OpenVINO IR format for ~30% faster inference on Intel CPUs.

Run once after first startup:
    cd backend
    python scripts/export_openvino.py

Then set in .env:
    FRESHVISION_YOLO_WEIGHTS=yolov8n_openvino/yolov8n.xml

OpenVINO is Intel's open-source inference engine — free, no registration,
optimised for Intel Core/Xeon/UHD Graphics and works entirely on CPU.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import YOLO_WEIGHTS, YOLO_IMGSZ


def export():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    print(f"Loading {YOLO_WEIGHTS}…")
    model = YOLO(YOLO_WEIGHTS)

    print(f"Exporting to OpenVINO IR (imgsz={YOLO_IMGSZ})…")
    out_path = model.export(
        format="openvino",
        imgsz=YOLO_IMGSZ,
        half=False,     # FP32 for CPU; FP16 only helps on iGPU
        int8=False,
    )
    print(f"\nExported to: {out_path}")
    print("\nAdd to your .env:")
    xml_file = next(Path(out_path).glob("*.xml"), None)
    if xml_file:
        print(f"  FRESHVISION_YOLO_WEIGHTS={xml_file.relative_to(Path.cwd())}")
    print("\nRestart the backend to pick up the new model.")


if __name__ == "__main__":
    export()
