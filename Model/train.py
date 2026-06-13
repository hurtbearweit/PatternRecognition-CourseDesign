from ultralytics import YOLO
import multiprocessing
multiprocessing.freeze_support()

if __name__ == '__main__':
    model = YOLO("D:/大三下/模式识别课设/Model/runs/detect/train-6/weights/best.pt")

    model.train(
        data="D:/大三下/模式识别课设/visdrone.yaml",
        epochs=100,
        imgsz=960,
        batch=4,
        lr0=0.001,
        patience=10,
        mosaic=1.0,
        copy_paste=0.2,
        device=0,
        workers=0,
        plots=True
    )