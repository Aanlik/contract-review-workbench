# 本机 OCR 安装与扫描 PDF 调优

## 1. 推荐安装顺序

优先安装 RapidOCR，体积较轻，适合先验证本机扫描件链路：

```bash
cd backend
bash scripts/install_ocr_deps.sh rapid
```

如果 RapidOCR 新包在本机环境不可用，可以退回旧 onnxruntime 包：

```bash
cd backend
bash scripts/install_ocr_deps.sh rapid-legacy
```

PaddleOCR 适合中文合同准确率优先的场景，但依赖更重：

```bash
cd backend
bash scripts/install_ocr_deps.sh paddle
```

包名依据 PyPI 当前发布信息：`paddleocr`、`rapidocr`、`rapidocr-onnxruntime`。

## 2. 系统设置

前端进入“设置”页：

- OCR 引擎：先选 RapidOCR 验证链路，中文效果不够再切 PaddleOCR。
- OCR DPI：默认 260。
- 启用预处理：默认开启，会做灰度、自动对比度和锐化。

建议调参：

- 扫描清晰、文件很大：DPI 220-260。
- 小字合同、印章页：DPI 300-360。
- 识别很慢：降低 DPI 或先关闭 PaddleOCR 换 RapidOCR。
- 文字发虚：保持预处理开启。
- 印章/水印干扰严重：分别测试开启和关闭预处理，对比平均置信度和关键日期识别结果。

## 3. 真实扫描 PDF 烟测

准备一份真实扫描合同 PDF 后运行：

```bash
PYTHONPATH=backend python3 backend/scripts/ocr_smoke_test.py /path/to/scanned-contract.pdf --engine rapid --dpi 260
```

对比不同参数：

```bash
PYTHONPATH=backend python3 backend/scripts/ocr_smoke_test.py /path/to/scanned-contract.pdf --engine rapid --dpi 320

PYTHONPATH=backend python3 backend/scripts/ocr_smoke_test.py /path/to/scanned-contract.pdf --engine rapid --dpi 320 --no-preprocess
```

观察输出：

- `pages` 是否等于 PDF 页数。
- `blocks` 是否明显过少。
- `avg_confidence` 是否低于 0.75。
- `preview` 是否能看到合同签订日期、甲乙方、金额、签章信息。

## 4. 上传验证

1. 设置页选择 OCR 引擎和 DPI。
2. 新建审核，上传纯图片扫描 PDF 或 PNG/JPG。
3. 进入工作台，查看“上传材料”和“解析原文”。
4. 若解析原文为空，查看状态是否为 `needs_ocr`，通常表示 OCR 依赖未安装或当前引擎不可用。

## 5. 当前实现说明

- 扫描 PDF 会先用 PyMuPDF 按页渲染成 PNG，再送 OCR。
- 图片预处理使用 Pillow：灰度、自动对比度、锐化。
- OCR 结果会保存页码、文本块、坐标、置信度和来源。
- 合同 PDF 默认走 OCR；OA PDF 先抽文字层，文字不足再走 OCR。
