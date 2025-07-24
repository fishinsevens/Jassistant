# Jassistant - 媒体文件助手

![Jassistant Logo](https://raw.githubusercontent.com/fishinsevens/Jassistant/main/logo.png)

## 项目简介

Jassistant是一款专为JAV媒体的工具，通过webhook获取EMBY最新媒体首页显示，可以查找高清替换，支持水印处理，NFO编辑等功能。

数据清洗只支持 通过 EMBY webhook 获取后写入数据库的影片

未写入数据库的影片在文件管理中双击 NFO 使用手作修正

## 版本历史

- **1.0.0** - 初始版本也是最终版本
- **1.0.1** - 新增TG机器人通知

## 快速开始

### 使用Docker Compose

```yaml
services:
  jassistant:
    image: aliez0lie1/jassistant:latest
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

CID_API_KEY，CID_API_URL为 aliez0lie1/avlink 番号与 DMM CID 匹配的API接口 不填则不使用 DMM 查询，手动查询即可

### 卷挂载

| 挂载点 | 描述 |
| --- | --- |
| /app/logs | 日志文件 |
| /app/db | 数据库文件 |
| /app/settings | 设置文件 |
| /app/assets | 水印资源文件 |
| /weiam | 媒体文件目录,与EMBY媒体库保持一致映射 |

### 水印资源文件请自备喜欢的

命名如下：

4K：4k.png

8K：8k.png

字幕：subs.png

破解：cracked.png

流出：leaked.png

有码：mosaic.png

无码：uncensored.png

### EMBY 通知设置

http://localhost:34711/api/webhook

application/json

勾选媒体库-新媒体已添加

## 浏览器访问

启动容器后，打开浏览器访问：`http://localhost:34711`
