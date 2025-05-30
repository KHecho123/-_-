# InSwapper 实时换脸应用


## 项目简介
基于 **InsightFace** 库和 **PyQt5** 开发的实时换脸工具，支持通过摄像头捕获画面并实时替换人脸。核心功能包括人脸检测、多源图片管理、性能监控以及直观的图形界面操作。

---

## 功能特性

### 1. 实时换脸
- 🎥 摄像头画面实时人脸替换
- 🔍 使用 `buffalo_l` 模型进行高精度人脸检测
- 🤖 基于 `inswapper_128.onnx` 模型实现高质量人脸交换

### 2. 图形界面
- 🖼️ 双画面显示：源图像区 + 实时预览区
- 📂 支持多张源图片动态添加/切换
- ⚙️ 分辨率调节（640x480 / 1280x720 / 1920x1080）
- 🎚️ 人脸检测开关与质量调节（1-100）

### 3. 性能优化
- ⚡ 异步模型加载防止界面卡顿
- 🔒 多线程资源锁保障稳定性
- 📊 实时 FPS 监控显示

### 4. 辅助功能
- 📝 状态栏日志分级提示（INFO/WARNING/ERROR）
- ⌛ 模型加载进度指示
- 🟢🔴 人脸检测状态可视化（颜色标记）

---

## 环境要求

### 系统配置
| 类别       | 要求                          |
|------------|-------------------------------|
| 操作系统   | Windows 10/11 或 Linux       |
| Python     | 3.8+                          |
| 推荐硬件   | NVIDIA GPU（支持 CUDA 加速） |
|            | 至少 4GB 显存                |
|            | USB3.0 摄像头                 |

---

## 安装步骤

### 1. 安装依赖
```bash
pip install opencv-python insightface PyQt5 # 注意版本匹配，具体这些库的版本可见requirements.txt，requirements里有不少多余的库，不需要全部下载。insightface可能需要本地下载。
```

### 2. 下载预训练模型
```bash
mkdir -p ~/.insightface/models
wget -P ~/.insightface/models/ https://github.com/deepinsight/insightface/releases/download/model-zoo/inswapper_128.onnx
```

### 2. 权限配置（Linux）
```bash
sudo usermod -a -G video $USER  # 授予摄像头访问权限
```

---

## 使用指南

### 1. 启动应用
```bash
python gui.py
```

### 2. 界面布局
+-------------------+-----------------------+
| 控制面板区         | 图像显示区            |
| - 源图片管理       | - 源图像预览          |
| - 摄像头控制       | - 实时换脸效果        |
| - 性能监控         | - 状态提示            |
+-------------------+-----------------------+

### 3. 操作流程
添加源图片：点击按钮选择人脸图片（支持多选）
选择源图像：通过下拉菜单切换人脸
设置分辨率：默认使用 640x480
启动摄像头：点击"开始"按钮
控制功能：通过复选框启用/禁用实时检测

### 4. 常见问题
❓ 模型文件缺失
```bash
Error: "模型文件不存在"
```
解决方案：
检查 ~/.insightface/models/ 目录是否存在 inswapper_128.onnx

❓ 摄像头无法启动
可能原因：
其他程序占用摄像头
Linux 权限问题

解决方案：
```bash
# 查看摄像头设备
ls /dev/video*
# 重启服务（Linux）
sudo service udev restart
```
