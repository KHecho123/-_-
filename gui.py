import sys
import cv2
import time
import glob
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor, QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout,
                           QVBoxLayout, QMessageBox, QFrame, QStatusBar,
                           QProgressBar, QPushButton, QGroupBox,
                           QGridLayout, QSpinBox, QCheckBox, QComboBox,
                           QFileDialog)
from face_swap import FaceSwapper
from threading import Lock
import os
import logging


class LogHandler(QObject):
    """
    自定义日志处理器，用于将日志信息转发到GUI界面显示
    
    功能：
    1. 捕获日志信息
    2. 通过信号机制将日志信息发送到GUI界面
    3. 支持不同级别的日志显示（INFO、WARNING、ERROR）
    """
    log_signal = pyqtSignal(str, str)  # 定义信号，参数为消息内容和日志级别

    def __init__(self):
        super().__init__()
        # 创建日志处理器并设置格式
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        # 重写emit方法，将日志转发到GUI
        self.handler.emit = self.emit_log

    def emit_log(self, record):
        """
        重写日志处理器的emit方法，将日志信息通过信号发送
        
        参数：
        - record: 日志记录对象，包含日志信息和级别
        """
        msg = self.handler.format(record)
        self.log_signal.emit(msg, record.levelname)


class FaceSwapUI(QWidget):
    """
    人脸交换应用程序的主界面类
    
    主要功能：
    1. 提供用户界面用于选择源图片和摄像头输入
    2. 实时显示人脸交换效果
    3. 提供控制选项（分辨率、人脸检测等）
    4. 显示性能监控信息
    """
    
    def __init__(self):
        super().__init__()
        # 初始化人脸交换器
        self.swapper = FaceSwapper()
        # 存储源图片
        self.src_img = None
        self.src_images = {}  # 存储所有源图片
        self.current_src_index = 0
        # 线程锁，用于保护共享资源
        self.lock = Lock()
        # 摄像头相关变量
        self.cap = None
        self.timer = None
        # 性能监控变量
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        self.is_running = True

        # 设置日志处理器
        self.log_handler = LogHandler()
        self.log_handler.log_signal.connect(self.handle_log)
        logging.getLogger().addHandler(self.log_handler.handler)

        # 初始化界面
        self.init_ui()
        # 延迟1秒后初始化摄像头，等待模型加载
        QTimer.singleShot(1000, self.init_camera)

    def init_ui(self):
        """
        初始化用户界面
        
        布局结构：
        1. 左侧控制面板
           - 源图片控制
           - 摄像头控制
           - 换脸设置
           - 性能监控
        2. 右侧显示区域
           - 源图片显示
           - 摄像头预览
           - 状态栏
        """
        # 设置窗口标题和大小
        self.setWindowTitle("InSwapper 实时换脸")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 创建左侧控制面板
        control_panel = QFrame()
        # 设置控制面板样式
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #3c3c3c;
                border-radius: 10px;
                padding: 15px;
            }
            QGroupBox {
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QComboBox, QSpinBox {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QCheckBox {
                color: white;
            }
        """)
        control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(control_panel)

        # 源图片控制组
        source_group = QGroupBox("源图片控制")
        source_layout = QGridLayout()

        # 添加源图片按钮
        self.add_source_btn = QPushButton("添加源图片")
        self.add_source_btn.clicked.connect(self.add_source_image)
        source_layout.addWidget(self.add_source_btn, 0, 0, 1, 2)

        # 源图片选择下拉框
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self.change_source_image)
        source_layout.addWidget(QLabel("选择源图片:"), 1, 0)
        source_layout.addWidget(self.source_combo, 1, 1)

        source_group.setLayout(source_layout)
        control_layout.addWidget(source_group)

        # 摄像头控制组
        camera_group = QGroupBox("摄像头控制")
        camera_layout = QGridLayout()
        
        # 分辨率选择
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "1280x720", "1920x1080"])
        camera_layout.addWidget(QLabel("分辨率:"), 0, 0)
        camera_layout.addWidget(self.resolution_combo, 0, 1)

        # 开始/停止按钮
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.toggle_camera)
        camera_layout.addWidget(self.start_button, 1, 0, 1, 2)

        camera_group.setLayout(camera_layout)
        control_layout.addWidget(camera_group)

        # 换脸设置组
        settings_group = QGroupBox("换脸设置")
        settings_layout = QGridLayout()

        # 人脸检测开关
        self.face_detection_check = QCheckBox("启用人脸检测")
        self.face_detection_check.setChecked(True)
        settings_layout.addWidget(self.face_detection_check, 0, 0, 1, 2)

        # 质量调节
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(80)
        settings_layout.addWidget(QLabel("质量:"), 1, 0)
        settings_layout.addWidget(self.quality_spin, 1, 1)

        settings_group.setLayout(settings_layout)
        control_layout.addWidget(settings_group)

        # 性能监控组
        monitor_group = QGroupBox("性能监控")
        monitor_layout = QGridLayout()

        # FPS显示
        self.fps_label = QLabel("FPS: 0")
        monitor_layout.addWidget(self.fps_label, 0, 0, 1, 2)

        # CPU使用率显示
        self.cpu_label = QLabel("CPU: 0%")
        monitor_layout.addWidget(self.cpu_label, 1, 0, 1, 2)

        monitor_group.setLayout(monitor_layout)
        control_layout.addWidget(monitor_group)

        control_layout.addStretch()
        main_layout.addWidget(control_panel)

        # 右侧显示区域
        display_layout = QVBoxLayout()
        display_layout.setSpacing(20)

        # 标题
        title_label = QLabel("InSwapper 实时换脸")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 10px;
            background-color: #3c3c3c;
            border-radius: 10px;
            color: white;
        """)
        display_layout.addWidget(title_label)

        # 图像显示区域
        image_layout = QHBoxLayout()
        image_layout.setSpacing(20)

        # 源图像容器
        src_container = QFrame()
        src_container.setStyleSheet("""
            QFrame {
                background-color: #3c3c3c;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        src_layout = QVBoxLayout(src_container)
        src_layout.setContentsMargins(10, 10, 10, 10)

        # 源图像标题
        src_title = QLabel("源图像")
        src_title.setAlignment(Qt.AlignCenter)
        src_title.setStyleSheet("font-size: 16px; margin-bottom: 10px; color: white;")
        src_layout.addWidget(src_title)

        # 源图像显示标签
        self.src_label = QLabel()
        self.src_label.setMinimumSize(600, 450)
        self.src_label.setAlignment(Qt.AlignCenter)
        src_layout.addWidget(self.src_label)

        # 源图像状态标签
        self.src_status = QLabel("等待选择源图片...")
        self.src_status.setAlignment(Qt.AlignCenter)
        self.src_status.setStyleSheet("color: #888888;")
        src_layout.addWidget(self.src_status)
        image_layout.addWidget(src_container)

        # 摄像头容器
        cam_container = QFrame()
        cam_container.setStyleSheet("""
            QFrame {
                background-color: #3c3c3c;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        cam_layout = QVBoxLayout(cam_container)
        cam_layout.setContentsMargins(10, 10, 10, 10)

        # 摄像头标题
        cam_title = QLabel("实时预览")
        cam_title.setAlignment(Qt.AlignCenter)
        cam_title.setStyleSheet("font-size: 16px; margin-bottom: 10px; color: white;")
        cam_layout.addWidget(cam_title)

        # 摄像头显示标签
        self.cam_label = QLabel()
        self.cam_label.setMinimumSize(800, 600)
        self.cam_label.setAlignment(Qt.AlignCenter)
        cam_layout.addWidget(self.cam_label)

        # 摄像头状态标签
        self.cam_status = QLabel("等待检测人脸...")
        self.cam_status.setAlignment(Qt.AlignCenter)
        self.cam_status.setStyleSheet("color: #888888;")
        cam_layout.addWidget(self.cam_status)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3c3c3c;
                border-radius: 5px;
                text-align: center;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        cam_layout.addWidget(self.progress_bar)

        # 加载提示标签
        self.loading_label = QLabel("模型加载中...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            font-size: 20px;
            color: white;
            background: rgba(0,0,0,150);
            padding: 20px;
            border-radius: 10px;
        """)
        cam_layout.addWidget(self.loading_label, 0, Qt.AlignCenter)

        image_layout.addWidget(cam_container)
        display_layout.addLayout(image_layout)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #2b2b2b;
                color: #ffffff;
                border-top: 1px solid #3c3c3c;
            }
        """)
        self.status_bar.showMessage("就绪")
        display_layout.addWidget(self.status_bar)

        main_layout.addLayout(display_layout)
        self.setLayout(main_layout)

    def add_source_image(self):
        """
        添加源图片
        
        功能：
        1. 打开文件对话框选择图片
        2. 加载选中的图片
        3. 将图片添加到源图片列表
        4. 如果是第一张图片，自动选择
        """
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp)")
        
        if file_dialog.exec_():
            files = file_dialog.selectedFiles()
            for file in files:
                try:
                    img = cv2.imread(file)
                    if img is not None:
                        # 使用文件名作为显示名称
                        name = os.path.basename(file)
                        self.src_images[name] = img
                        self.source_combo.addItem(name)
                        
                        # 如果是第一张图片，自动选择
                        if len(self.src_images) == 1:
                            self.change_source_image(0)
                except Exception as e:
                    QMessageBox.warning(self, "警告", f"加载图片失败: {str(e)}")

    def change_source_image(self, index):
        """
        切换源图片
        
        参数：
        - index: 下拉框中的索引
        
        功能：
        1. 根据索引获取选中的图片
        2. 更新源图片显示
        3. 更新状态信息
        """
        if index >= 0 and index < self.source_combo.count():
            name = self.source_combo.currentText()
            self.src_img = self.src_images[name]
            src_pixmap = self.cv2_to_pixmap(self.src_img)
            self.src_label.setPixmap(src_pixmap.scaled(600, 450, Qt.KeepAspectRatio))
            self.src_status.setText("等待检测人脸...")
            self.src_status.setStyleSheet("color: #888888;")

    def toggle_camera(self):
        """
        切换摄像头状态（开始/停止）
        
        功能：
        1. 如果摄像头正在运行，则停止
        2. 如果摄像头已停止，则启动
        3. 更新按钮文本
        """
        if self.is_running:
            self.stop_camera()
            self.start_button.setText("开始")
        else:
            self.start_camera()
            self.start_button.setText("停止")

    def start_camera(self):
        """
        启动摄像头
        
        功能：
        1. 初始化摄像头
        2. 设置分辨率
        3. 启动定时器更新画面
        4. 更新状态信息
        """
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.critical(self, "错误", "无法打开摄像头")
                return

            # 设置分辨率
            resolution = self.resolution_combo.currentText().split('x')
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(resolution[0]))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(resolution[1]))

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
            self.is_running = True
            self.status_bar.showMessage("摄像头已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"摄像头初始化失败: {str(e)}")

    def stop_camera(self):
        """
        停止摄像头
        
        功能：
        1. 释放摄像头资源
        2. 停止定时器
        3. 更新状态信息
        """
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.timer:
            self.timer.stop()
        self.is_running = False
        self.status_bar.showMessage("摄像头已停止")

    def handle_log(self, message, level):
        """
        处理日志信息
        
        参数：
        - message: 日志消息
        - level: 日志级别
        
        功能：
        1. 根据日志级别显示不同的提示
        2. INFO级别显示在状态栏
        3. WARNING级别显示5秒
        4. ERROR级别弹出警告框
        """
        if level == "INFO":
            self.status_bar.showMessage(message)
        elif level == "WARNING":
            self.status_bar.showMessage(message, 5000)
        elif level == "ERROR":
            QMessageBox.warning(self, "警告", message)

    def init_camera(self):
        """
        初始化摄像头
        
        功能：
        1. 检查模型是否加载完成
        2. 如果未完成，显示进度条
        3. 如果完成，隐藏进度条和加载提示
        """
        if self.swapper.thread.is_alive():
            self.progress_bar.show()
            self.progress_bar.setValue(50)
            QTimer.singleShot(500, self.init_camera)
            return

        self.progress_bar.hide()
        self.loading_label.hide()

    def update_frame(self):
        """
        更新摄像头画面
        
        功能：
        1. 读取摄像头画面
        2. 计算FPS
        3. 如果启用了人脸检测且有源图片，执行换脸
        4. 更新显示画面
        """
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        # 计算FPS
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time
            self.fps_label.setText(f"FPS: {self.fps}")

        if self.lock.acquire(blocking=False):
            try:
                if self.face_detection_check.isChecked() and self.src_img is not None:
                    result = self.swapper.swap_face(self.src_img, frame)
                    display_frame = result if result is not None else frame
                    
                    # 更新状态信息
                    if result is not None:
                        self.cam_status.setText("检测到人脸")
                        self.cam_status.setStyleSheet("color: #4CAF50;")
                    else:
                        self.cam_status.setText("未检测到人脸")
                        self.cam_status.setStyleSheet("color: #f44336;")
                else:
                    display_frame = frame
                    if self.src_img is None:
                        self.cam_status.setText("请选择源图片")
                    else:
                        self.cam_status.setText("人脸检测已禁用")
                    self.cam_status.setStyleSheet("color: #888888;")
            finally:
                self.lock.release()
        else:
            display_frame = frame

        pixmap = self.cv2_to_pixmap(display_frame)
        self.cam_label.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio))

    def closeEvent(self, event):
        """
        窗口关闭事件处理
        
        功能：
        1. 停止摄像头
        2. 接受关闭事件
        """
        self.stop_camera()
        event.accept()

    def cv2_to_pixmap(self, frame):
        """
        将OpenCV图像转换为QPixmap
        
        参数：
        - frame: OpenCV图像
        
        返回：
        - QPixmap对象
        """
        if frame is None:
            return QPixmap()
        h, w, c = frame.shape
        bytes_per_line = 3 * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        return QPixmap.fromImage(qimg)


if __name__ == "__main__":
    """
    程序入口
    
    功能：
    1. 创建应用程序实例
    2. 创建主窗口
    3. 显示窗口
    4. 启动事件循环
    """
    app = QApplication(sys.argv)
    try:
        window = FaceSwapUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "错误", f"启动失败: {str(e)}")
        sys.exit(1)