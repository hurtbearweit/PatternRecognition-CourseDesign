from ultralytics import YOLO
import multiprocessing
multiprocessing.freeze_support()

if __name__ == '__main__':
    # 统一使用YOLOv8s
    model = YOLO("yolov8s.pt")

    model.train(
        data="VisDrone.yaml",
        epochs=100,
        imgsz=960,
        batch=4,
        lr0=0.003,
        lrf=0.01,
        patience=20,
        # 数据增强
        mosaic=1.0,
        copy_paste=0.2,
        mixup=0.1,
        degrees=5.0,
        scale=0.3,
        # 损失函数与IOU
        cls=2.0,
        box=7.5,
        iou=0.5,
        # 硬件与训练设置
        device=0,
        workers=0,
        cache=False,
        amp=True,
        val=True,
        plots=True,
        seed=0
    )

    # 自动验证并导出模型
    metrics = model.val()
    model.export(format="onnx", opset=13)