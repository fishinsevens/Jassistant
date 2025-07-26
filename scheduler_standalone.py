#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import sys

# 添加当前目录到路径，确保能正确导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from scheduler import setup_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scheduler')

if __name__ == "__main__":
    logger.info("正在启动独立调度器进程...")

    try:
        # 创建应用实例，但不记录web服务启动日志
        app = create_app()

        # 在应用上下文中初始化和启动调度器
        with app.app_context():
            # 使用改进的启动日志控制机制，确保调度器日志不与web进程冲突
            from app import _ensure_startup_log_once
            should_log_startup = _ensure_startup_log_once(app, "scheduler")

            if should_log_startup:
                from config_utils import VERSION
                logger.info(f"=== Jassistant v{VERSION} 调度器启动成功 ===")
                logger.info(f"调度器进程已启动，PID: {os.getpid()}")

            logger.info("正在初始化调度器...")
            scheduler = setup_scheduler(standalone=True)

            logger.info("正在启动调度器...")
            scheduler.start()

            if should_log_startup:
                logger.info("调度器已成功启动，开始监听任务")

            # 保持进程运行
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("调度器进程接收到停止信号")
                scheduler.shutdown()
                logger.info("调度器已安全关闭")
    except Exception as e:
        logger.error(f"调度器启动失败: {str(e)}", exc_info=True)
        sys.exit(1)
