# Jassistant - 媒体文件助手

![Jassistant Logo](https://raw.githubusercontent.com/fishinsevens/Jassistant/main/logo.png)

## 项目简介

Jassistant是一款专为媒体文件管理设计的工具，可以帮助您管理媒体库，实现高清替换，支持水印处理，文件管理等功能。

## 快速开始

### 使用Docker Compose

```yaml
services:
  jassistant:
    image: aliez0lie1/jassistant:1.0.0
    container_name: jassistant
    ports:
      - "34711:34711"
    volumes:
      - ./data/logs:/app/logs
      - ./data/db:/app/db
      - ./data/settings:/app/settings
      - ./data/watermarks:/app/assets
      - /your/media/path:/weiam
    environment:
      - TZ=Asia/Shanghai
      - CID_API_KEY=your_api_key
      - CID_API_URL=your_api_url
    restart: unless-stopped
```

## 配置说明

### 环境变量

| 环境变量 | 描述 | 默认值 |
| --- | --- | --- |
| TZ | 时区 | Asia/Shanghai |
| CID_API_KEY | CID API密钥 | - |
| CID_API_URL | CID API URL | - |

### 卷挂载

| 挂载点 | 描述 |
| --- | --- |
| /app/logs | 日志文件 |
| /app/db | 数据库文件 |
| /app/settings | 设置文件 |
| /app/assets | 水印资源文件 |
| /weiam | 媒体文件目录 |

## 浏览器访问

启动容器后，打开浏览器访问：`http://localhost:34711`

## 版本历史

- **1.0.0** - 初始版本也是最终版本
