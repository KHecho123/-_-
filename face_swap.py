import cv2
import os
from insightface.app import FaceAnalysis
from insightface import model_zoo
from threading import Thread
import logging

# 配置日志系统，设置日志级别为INFO，这样会显示INFO及以上级别的日志信息1.人脸检测与识别
# `insightface`库的`buffalo模型进行高精度人脸检测和特征提取
# -基于`insightface`的预训练模型`inswapper_128.onnx，实现人脸替换
# -通过 opency捕获摄像头画面，结合多线程技术实现低延迟换脸
# -使用`Pyat5`开发图形界面，支持源图片选择、摄像头控制、性能监控等功能
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceSwapper:
    """
    人脸交换类，负责加载模型和执行人脸交换操作

    主要功能：
    1. 异步加载人脸检测和换脸模型
    2. 检测源图片和目标图片中的人脸
    3. 执行人脸交换操作
    """
    
    def __init__(self):
        """
        初始化FaceSwapper类
        
        属性：
        - app: FaceAnalysis对象，用于人脸检测
        - swapper: 换脸模型对象
        - thread: 用于异步加载模型的线程
        """
        self.app = None  # 人脸检测模型
        self.swapper = None  # 换脸模型
        # 创建并启动一个守护线程来加载模型，这样不会阻塞主线程
        self.thread = Thread(target=self._load_models)
        self.thread.daemon = True  # 设置为守护线程，主线程结束时自动退出
        self.thread.start()

    def _load_models(self):
        """
        异步加载所需模型
        
        加载过程：
        1. 加载人脸检测模型（buffalo_l）
        2. 检查并加载换脸模型（inswapper_128.onnx）
        
        如果加载失败，会记录错误日志并设置模型为None
        """
        try:
            # 加载人脸检测模型
            logger.info("开始加载人脸检测模型...")
            self.app = FaceAnalysis(name='buffalo_l')  # 使用buffalo_l模型进行人脸检测
            # 准备模型，设置GPU设备ID和检测尺寸
            self.app.prepare(ctx_id=0, det_size=(320, 320))
            logger.info("人脸检测模型加载完成")

            # 检查换脸模型文件是否存在
            model_path = os.path.expanduser('~/.insightface/models/inswapper_128.onnx')
            if not os.path.exists(model_path):
                logger.error(f"模型文件不存在: {model_path}")
                return

            # 加载换脸模型
            logger.info("开始加载换脸模型...")
            self.swapper = model_zoo.get_model(model_path)  # 加载inswapper_128模型
            logger.info("换脸模型加载完成")
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            self.app = None
            self.swapper = None

    def swap_face(self, src_img, dst_img):
        """
        执行人脸交换操作
        
        参数：
        - src_img: 源图片（要交换的人脸）
        - dst_img: 目标图片（要替换的人脸）
        
        返回：
        - 如果成功，返回换脸后的图片
        - 如果失败，返回原始目标图片
        
        处理流程：
        1. 检查模型是否加载完成
        2. 检测源图片和目标图片中的人脸
        3. 执行人脸交换
        4. 处理各种可能的错误情况
        """
        # 检查模型是否仍在加载中
        if self.thread.is_alive():
            logger.info("模型仍在加载中...")
            return dst_img
            
        # 检查模型是否成功加载
        if not self.swapper or not self.app:
            logger.error("模型未正确加载")
            return dst_img
            
        try:
            # 检测源图片和目标图片中的人脸
            src_faces = self.app.get(src_img)  # 获取源图片中的人脸信息
            dst_faces = self.app.get(dst_img)  # 获取目标图片中的人脸信息
            
            # 检查是否检测到人脸
            if len(src_faces) == 0:
                logger.warning("源图片中未检测到人脸")
                return dst_img
            if len(dst_faces) == 0:
                logger.warning("目标图片中未检测到人脸")
                return dst_img
                
            # 执行人脸交换
            # 使用第一个检测到的人脸进行交换
            # paste_back=True表示将换脸结果粘贴回原图
            result = self.swapper.get(dst_img, dst_faces[0], src_faces[0], paste_back=True)
            return result
        except Exception as e:
            # 处理换脸过程中的错误
            logger.error(f"换脸过程中出错: {str(e)}")
            return dst_img