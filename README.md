# AstrBot 飞书工具集插件

为 AstrBot 飞书机器人提供文档、云盘、任务、群聊管理等高级功能的 LLM 工具集。

## 功能特性

本插件为飞书机器人提供以下 LLM 工具，让 AI 助手能够执行飞书平台的各种操作：

| 工具名称 | 功能描述 |
|---------|---------|
| `feishu_message` | 消息管理 - 获取、列出、发送、回复消息 |
| `feishu_chat` | 群聊管理 - 公告读写、创建群、添加成员 |
| `feishu_doc` | 文档操作 - 读写飞书文档、管理 Block 和评论 |
| `feishu_drive` | 云盘管理 - 文件夹浏览、创建、复制、移动、删除 |
| `feishu_task` | 任务管理 - 创建/更新/删除任务和任务清单 |
| `feishu_bitable` | 多维表格 - 创建/管理多维表格、数据表、记录、字段 |
| `feishu_calendar` | 日历管理 - 创建/管理日历和日程事件 |
| `feishu_sheets` | 电子表格 - 创建/管理工作表、读写单元格 |
| `feishu_wiki` | 知识库 - 浏览知识库空间、管理知识库节点 |
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
  "enabled_tools": ["message", "chat", "doc", "drive", "task", "bitable", "calendar", "sheets", "wiki", "reaction", "urgent"],
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
  "bitable_tool": {
    "enabled": true
  },
  "calendar_tool": {
    "enabled": true
  },
  "sheets_tool": {
    "enabled": true
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
| `bitable_tool.enabled` | 是否启用多维表格工具 | true |
| `calendar_tool.enabled` | 是否启用日历工具 | true |
| `sheets_tool.enabled` | 是否启用电子表格工具 | true |
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

### 多维表格权限
- `bitable:app` - 多维表格操作
- `bitable:app:readonly` - 读取多维表格

### 日历权限
- `calendar:calendar` - 日历操作
- `calendar:calendar:readonly` - 读取日历
- `calendar:calendar_event` - 日程操作

### 电子表格权限
- `sheets:spreadsheet` - 电子表格操作
- `sheets:spreadsheet:readonly` - 读取电子表格

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

### 多维表格相关
```
用户: 帮我在多维表格中添加一条记录，项目名称是"新功能开发"
AI: [调用 feishu_bitable 工具创建记录]
```

### 日历相关
```
用户: 帮我创建一个明天下午3点的会议日程
AI: [调用 feishu_calendar 工具创建日程]
```

### 电子表格相关
```
用户: 帮我在电子表格的 A1 单元格写入"销售数据"
AI: [调用 feishu_sheets 工具写入数据]
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
└── feishu_tools_client/    # 飞书工具模块
    ├── __init__.py
    ├── client.py           # 飞书 API 客户端
    └── tools/              # 工具实现
        ├── __init__.py
        ├── message.py      # 消息工具
        ├── chat.py         # 群聊工具
        ├── doc.py          # 文档工具
        ├── drive.py        # 云盘工具
        ├── task.py         # 任务工具
        ├── bitable.py      # 多维表格工具
        ├── calendar.py     # 日历工具
        ├── sheets.py       # 电子表格工具
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

1. 在 `feishu_tools_client/tools/` 目录下创建新的工具文件
2. 实现 `create_xxx_tool(client: FeishuClient) -> FuncTool` 函数
3. 在 `feishu_tools_client/tools/__init__.py` 中导出
4. 在 `feishu_tools_client/__init__.py` 中导出
5. 在 `main.py` 中注册

### 工具实现规范

```python
from astrbot.core.provider.func_tool_manager import FuncTool
from ..client import FeishuClient

def create_xxx_tool(client: FeishuClient) -> FuncTool:
    async def handler(action: str, **kwargs):
        actions = {
            "action1": lambda: _action1(client, **kwargs),
            "action2": lambda: _action2(client, **kwargs),
        }
        if action not in actions:
            return {"error": f"Unknown action: {action}"}
        return await actions[action]()

    return FuncTool(
        name="feishu_xxx",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["action1", "action2"],
                    "description": "操作类型",
                },
                ...
            },
            "required": ["action"]
        },
        description="工具描述",
        handler=handler,
    )
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
