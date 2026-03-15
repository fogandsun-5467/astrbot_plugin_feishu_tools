# AstrBot 飞书工具集插件

为 AstrBot 飞书机器人提供文档、云盘、任务、群聊管理等高级功能的 LLM 工具集。

## 功能特性

本插件为飞书机器人提供以下 LLM 工具，让 AI 助手能够执行飞书平台的各种操作：

| 工具名称 | 功能描述 |
|---------|---------|
| `feishu_message` | 消息读取 - 获取单条消息或列出聊天记录 |
| `feishu_chat` | 群聊管理 - 公告读写、创建群、添加成员 |
| `feishu_doc` | 文档操作 - 读写飞书文档、管理评论 |
| `feishu_drive` | 云盘管理 - 文件夹浏览、创建、移动、删除 |
| `feishu_task` | 任务管理 - 创建任务/子任务、评论、附件 |
| `feishu_reaction` | 表情回应 - 添加/移除/列出消息表情 |
| `feishu_perm` | 权限管理 - 管理文档/文件协作者权限 |
| `feishu_urgent` | 紧急通知 - 发送应用内/短信/电话通知 |

## 安装要求

1. **AstrBot 版本**: >= v4.0.0
2. **飞书平台**: 需要先在 AstrBot 中配置并启用飞书机器人

## 安装方法

1. 将插件目录放置到 `AstrBot/data/plugins/` 目录下
2. 重启 AstrBot 或在 WebUI 中重载插件

## 配置说明

插件配置文件 `_conf_schema.json` 支持以下配置项：

```json
{
  "enabled_tools": ["message", "chat", "doc", "drive", "task", "reaction", "perm", "urgent"],
  "message_tool": {
    "enabled": true,
    "max_list_size": 50
  },
  "doc_tool": {
    "enabled": true,
    "max_media_size_mb": 20
  },
  "task_tool": {
    "enabled": true,
    "default_assign_self": true
  },
  "perm_tool": {
    "enabled": false
  },
  "urgent_tool": {
    "enabled": true,
    "default_type": "app"
  }
}
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `enabled_tools` | 启用的工具列表 | 全部工具 |
| `message_tool.max_list_size` | 消息列表最大返回数量 | 50 |
| `doc_tool.max_media_size_mb` | 文档媒体文件最大大小 | 20MB |
| `task_tool.default_assign_self` | 任务默认分配给请求者 | true |
| `perm_tool.enabled` | 是否启用权限工具（敏感操作） | false |
| `urgent_tool.default_type` | 默认紧急通知类型 | app |

## 飞书权限配置

在飞书开发者后台，需要为应用开通以下权限：

### 基础权限（必需）
- `im:message` - 获取与发送消息
- `im:message:send_as_bot` - 以应用身份发消息
- `im:message:readonly` - 读取消息

### 文档权限
- `docx:document` - 文档操作
- `docx:document:readonly` - 读取文档
- `drive:drive` - 云盘操作
- `drive:drive:readonly` - 读取云盘

### 任务权限
- `task:task` - 任务操作
- `task:task:readonly` - 读取任务

### 其他权限（按需）
- `im:message.reactions:write_only` - 表情回应
- `im:message.urgent` - 紧急通知
- `drive:permission` - 权限管理

## 使用示例

安装插件后，用户可以通过与飞书机器人对话来使用这些功能：

### 消息相关
```
用户: 帮我查看最近的聊天记录
AI: [调用 feishu_message 工具获取消息列表]
```

### 文档相关
```
用户: 帮我创建一个名为"会议纪要"的文档
AI: [调用 feishu_doc 工具创建文档]
```

### 任务相关
```
用户: 帮我创建一个任务：完成项目报告，截止日期是下周五
AI: [调用 feishu_task 工具创建任务]
```

### 群聊相关
```
用户: 帮我创建一个群聊，邀请张三和李四
AI: [调用 feishu_chat 工具创建群聊并添加成员]
```

## 指令

插件提供以下调试指令：

- `/feishu_tools` - 查看已注册的工具列表
- `/feishu_test` - 测试飞书 API 连接状态

## 项目结构

```
astrbot_plugin_feishu_tools/
├── main.py                 # 插件入口
├── metadata.yaml           # 插件元数据
├── requirements.txt        # 依赖列表
├── _conf_schema.json       # 配置 Schema
├── README.md               # 说明文档
└── feishu/                 # 飞书工具模块
    ├── __init__.py
    ├── client.py           # 飞书 API 客户端
    └── tools/              # 工具实现
        ├── __init__.py
        ├── message.py      # 消息工具
        ├── chat.py         # 群聊工具
        ├── doc.py          # 文档工具
        ├── drive.py        # 云盘工具
        ├── task.py         # 任务工具
        ├── reaction.py     # 表情工具
        ├── perm.py         # 权限工具
        └── urgent.py       # 紧急通知工具
```

## 注意事项

1. **权限工具默认禁用**: `feishu_perm` 工具涉及敏感操作，默认禁用。如需启用，请在配置中设置 `perm_tool.enabled: true`

2. **紧急通知可能收费**: `sms` 和 `phone` 类型的紧急通知可能产生费用，建议使用默认的 `app` 类型

3. **机器人无根目录**: 飞书机器人没有"我的空间"概念，创建文件夹需要先手动创建一个文件夹并分享给机器人

4. **任务可见性**: 用户只能看到自己作为负责人的任务，创建任务时建议指定负责人

## 开发指南

### 添加新工具

1. 在 `feishu/tools/` 目录下创建新的工具文件
2. 实现 `create_xxx_tool(client: FeishuClient) -> FuncTool` 函数
3. 在 `feishu/tools/__init__.py` 中导出
4. 在 `main.py` 中注册

### 工具实现规范

```python
from astrbot.core.provider.func_tool_manager import FuncTool
from ..client import FeishuClient

def create_xxx_tool(client: FeishuClient) -> FuncTool:
    async def handler(**kwargs):
        # 实现工具逻辑
        return {"result": "..."}

    return FuncTool(
        name="feishu_xxx",
        parameters={
            "type": "object",
            "properties": {...},
            "required": [...]
        },
        description="工具描述",
        handler=handler,
    )
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
