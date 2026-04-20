# 🌱 EverGreen Box - M1 MacBook 植物监测系统

## 功能特性

✅ **实时 YOLO 检测**

- 植物种类识别（Model A）
- 植物健康状态检测（Model B）
- 基于 M1 GPU (MPS) 加速推理

✅ **异步后台上传**

- 每 15 秒自动打包上传当前帧和检测结果
- 不阻塞主检测线程
- 支持网络中断自动重试

✅ **Twilio WhatsApp 告警**

- 检测到不健康植物时发送 WhatsApp 消息
- 每天只发送一次告警（去重）
- 实时通知用户

✅ **Arduino 硬件控制**

- 通过串口与 Arduino 通信
- 基于植物类型发送控制命令
- 支持灌溉、风扇等设备控制

✅ **本地实时显示**

- 在 OpenCV 窗口实时显示检测结果
- 显示植物名称、健康状态、置信度、Arduino 连接状态等

✅ **安全关闭**

- 按 'q' 键优雅关闭程序
- 自动等待后台线程完成
- 正确释放所有资源

## 环境要求

- **硬件**: MacBook M1/M2/M3
- **Python**: 3.9+
- **摄像头**: USB 摄像头或内置摄像头
- **Arduino**: 可选（如需硬件控制）

## 安装步骤

### 1. 创建虚拟环境

```bash
cd /Users/uuxa/Desktop/EverGreenBox/webcam
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 准备 YOLO 模型

确保以下模型文件在同一目录中：

- `cactus_pothos_succulent_training_150epoches.pt` (植物种类)
- `health_best.pt` (植物健康状态)

### 4. 配置 Twilio（可选）

编辑代码中的这些变量：

```python
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Twilio 号码
YOUR_WHATSAPP_NUMBER = 'whatsapp:+your_number'    # 你的号码
```

### 5. 配置 Arduino（可选）

编辑代码中的这些变量：

```python
SERIAL_PORT = '/dev/cu.usbserial-*'  # 查看下面的诊断方法
BAUD_RATE = 9600
```

## 使用方法

### 基础运行

```bash
python3 plant_monitor_m1.py
```

### 配置参数

编辑 `plant_monitor_m1.py` 中的配置部分：

```python
RENDER_BACKEND_URL = "https://evergreen-box-backend.onrender.com"  # 后端 URL
UPLOAD_INTERVAL_SECONDS = 15  # 上传间隔（秒）
UPLOAD_TIMEOUT_SECONDS = 5    # 上传超时（秒）
CAMERA_INDEX = 0              # 摄像头索引（0=默认, 1=USB 外接等）
```

### 关键快捷键

- `q` - 安全关闭程序

## macOS 上的 Arduino 诊断

### 1. 查找串口

```bash
ls /dev/cu.*
```

输出例如：

```
/dev/cu.usbserial-1420
/dev/cu.usbmodem14201
```

### 2. 修改配置

将串口号复制到代码中：

```python
SERIAL_PORT = '/dev/cu.usbserial-1420'
```

### 3. 测试连接

```bash
python3 -c "
import serial
import time

try:
    ser = serial.Serial('/dev/cu.usbserial-1420', 9600, timeout=1)
    print('✅ 连接成功！')
    ser.close()
except Exception as e:
    print(f'❌ 连接失败：{e}')
"
```

## 程序流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    主程序启动                               │
└────────────────────┬────────────────────────────────────────┘
                     │
       ┌─────────────┼──────────────┐
       │             │              │
       ▼             ▼              ▼
   ┌────────────┐ ┌──────────┐ ┌──────────────┐
   │ 主线程：    │ │后台线程1:│ │后台线程2:    │
   │YOLO检测    │ │定时上传  │ │Twilio告警   │
   │            │ │          │ │              │
   │• 读取摄像头│ │• 每15秒  │ │• 检测异常时 │
   │• 运行检测  │ │• 上传帧+│ │• 发送消息   │
   │• 发Arduino │ │  YOLO   │ │• 线程隔离   │
   │• 显示画面  │ │• 5秒超时│ │              │
   └────────────┘ │          │ └──────────────┘
                  │          │
                  └──────────┘
```

## 上传数据格式

### 请求格式

```
POST /api/camera/upload-image
Content-Type: multipart/form-data

file: <JPEG 图像>
yolo_result: {
    "plant_name": "Pothos",
    "health_status": "Healthy",
    "confidence": 0.95,
    "timestamp": "2026-04-20T11:27:54.123456"
}
```

### 响应格式（成功）

```json
{
  "status": "success",
  "image_url": "/static/images/20260420_112754_023.jpg",
  "filename": "20260420_112754_023.jpg",
  "storage_type": "render_disk",
  "image_count": 15
}
```

## Arduino 命令协议

程序会根据检测到的植物类型发送数字命令到 Arduino：

| 植物类型  | Arduino 命令 | 用途           |
| --------- | ------------ | -------------- |
| Cactus    | '0'          | 控制仙人掌浇灌 |
| Pothos    | '1'          | 控制绿萝浇灌   |
| Succulent | '2'          | 控制多肉浇灌   |
| 未检测    | 'N'          | 无操作         |

在 Arduino 侧编程时接收这些字符并执行相应的操作。

## WhatsApp 告警示例

```
🌿 AIoT Plant Alert: Unhealthy leaves detected on your Pothos at 2026-04-20 11:30:45. Please check the environment parameters!
```

## 日志输出示例

```
2026-04-20 11:27:54 [INFO] ============================================================
2026-04-20 11:27:54 [INFO] 🌱 EverGreen Box - M1 植物监测系统
2026-04-20 11:27:54 [INFO]    YOLO 检测 + 后端上传 + Twilio 告警 + Arduino 控制
2026-04-20 11:27:54 [INFO] ============================================================
2026-04-20 11:27:54 [INFO] 🤖 加载 YOLO 模型...
2026-04-20 11:27:58 [INFO] ✅ 模型 A（植物种类）加载成功 - 使用 MPS 设备
2026-04-20 11:27:59 [INFO] ✅ 模型 B（植物健康）加载成功 - 使用 MPS 设备
2026-04-20 11:27:59 [INFO] 📷 初始化摄像头 (索引: 0)...
2026-04-20 11:27:59 [INFO] ✅ 摄像头已初始化
2026-04-20 11:27:59 [INFO] 🔌 尝试连接 Arduino (/dev/cu.usbserial-1420, 9600 baud)...
2026-04-20 11:27:59 [INFO] ✅ Arduino 已连接: /dev/cu.usbserial-1420
2026-04-20 11:27:59 [INFO] 🔄 启动后台上传线程...
2026-04-20 11:27:59 [INFO] ✅ 系统已启动，按 'q' 停止程序
...
2026-04-20 11:28:14 [INFO] ✅ 上传成功 - Pothos (Healthy)
2026-04-20 11:30:45 [WARNING] ⚠️ 检测到不健康植物！发送告警...
2026-04-20 11:30:46 [INFO] ✅ WhatsApp 消息已发送! SID: SM1234567890abcdef...
```

## 性能指标

- **YOLO 推理**: 使用 MPS (M1 GPU) 加速
- **检测延迟**: ~50-100ms/帧（取决于模型大小）
- **上传间隔**: 15 秒
- **网络超时**: 5 秒
- **Arduino 发送**: 每 0.5 秒
- **内存占用**: ~500MB-1GB

## 故障排查

### 问题：摄像头无法打开

- 检查摄像头权限（系统偏好设置 > 安全与隐私 > 摄像头）
- 尝试修改 `CAMERA_INDEX`（从 0 改为 1 等）

### 问题：Arduino 连接失败

```
⚠️ Arduino 连接失败: ...
📝 继续运行（仅视觉模式，不控制硬件）
```

这是正常的，表示没有 Arduino 连接。程序会在纯视觉模式下运行。

### 问题：YOLO 推理很慢

- 确认已启用 MPS 设备（日志中应该显示 "MPS 设备"）
- 检查模型文件是否正确加载

### 问题：上传失败

- 检查网络连接
- 确认 `RENDER_BACKEND_URL` 配置正确
- 查看日志中的错误信息

### 问题：WhatsApp 不发送

- 检查 Twilio 账户是否有效
- 验证电话号码格式（包括国家代码）
- 确认账户余额充足

## 扩展功能

可以添加以下功能：

- [ ] 本地数据库记录检测历史
- [ ] WebUI 查看历史数据
- [ ] 多摄像头支持
- [ ] 邮件告警通知
- [ ] 性能分析和统计
- [ ] 湿度/温度传感器数据集成

## 许可证

MIT License
