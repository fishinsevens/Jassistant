# Dockerfile

# --- Stage 1: Build React Frontend ---
FROM node:18-alpine AS build-stage
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Build Python Backend ---
FROM python:3.10-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装依赖项和supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends libjpeg-dev zlib1g-dev supervisor && \
    rm -rf /var/lib/apt/lists/*

# 复制和安装Python依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 复制前端构建文件
COPY --from=build-stage /app/frontend/build ./static

# 复制supervisor配置文件
COPY supervisord.conf /etc/supervisor/conf.d/

# 确保脚本可执行
RUN chmod +x /app/scheduler_standalone.py

EXPOSE 34711

# 使用supervisor替代直接运行gunicorn
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
