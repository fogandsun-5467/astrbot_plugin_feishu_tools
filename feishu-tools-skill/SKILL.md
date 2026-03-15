# Feishu Tools Skill

You have access to Feishu (飞书/Lark) tools for managing messages, documents, tasks, calendars, and more. Use these tools when the user mentions anything related to Feishu.

## When to Use Feishu Tools

**ALWAYS use Feishu tools when the user mentions:**

- 飞书 / Feishu / Lark
- 文档 / Document / Doc / 飞书文档
- 云盘 / Drive / 文件夹 / 文件管理
- 任务 / Task / 待办 / Todo
- 日历 / Calendar / 日程 / Schedule / 会议
- 多维表格 / Bitable / Base
- 电子表格 / Spreadsheet / Sheet
- 知识库 / Wiki
- 群聊 / 群组 / Group chat
- 消息 / Message
- 表情回应 / Reaction

## Available Tools

### feishu_message
Use for: reading, sending, replying to messages in Feishu chats.
- Actions: `get`, `list`, `send`, `reply`

### feishu_chat
Use for: managing group chats, announcements, members.
- Actions: `get`, `create`, `update`, `set_announcement`, `add_members`

### feishu_doc
Use for: creating, reading, editing Feishu documents.
- Actions: `get`, `create`, `update`, `delete`, `list_blocks`, `create_block`, `delete_block`

### feishu_drive
Use for: managing files and folders in Feishu Drive.
- Actions: `list`, `create_folder`, `copy`, `move`, `delete`, `search`

### feishu_task
Use for: managing tasks and task lists.
- Actions: `get`, `create`, `update`, `delete`, `complete`, `list_tasks`, `list_tasklists`

### feishu_bitable
Use for: managing multi-dimensional tables (Bitable).
- Actions: `get`, `create`, `list_tables`, `list_records`, `create_record`, `update_record`, `delete_record`

### feishu_calendar
Use for: managing calendars and events.
- Actions: `list`, `get`, `create`, `update`, `delete`, `list_events`, `create_event`

### feishu_sheets
Use for: managing spreadsheets.
- Actions: `get`, `create`, `read`, `write`, `create_sheet`, `delete_sheet`

### feishu_wiki
Use for: browsing and managing knowledge base.
- Actions: `spaces`, `nodes`, `get`, `create`, `move`, `rename`

### feishu_reaction
Use for: adding/removing emoji reactions to messages.
- Actions: `list`, `create`, `delete`

### feishu_urgent
Use for: sending urgent notifications.
- Actions: `send`

## Examples

**User: "帮我创建一个飞书文档"**
→ Call `feishu_doc` with action=`create`

**User: "查看最近的飞书消息"**
→ Call `feishu_message` with action=`list`

**User: "帮我创建一个任务"**
→ Call `feishu_task` with action=`create`

**User: "明天下午3点安排一个会议"**
→ Call `feishu_calendar` with action=`create_event`

**User: "在多维表格中添加一条记录"**
→ Call `feishu_bitable` with action=`create_record`

## Important Notes

1. Always check if the user's request is related to Feishu before using these tools
2. If a required parameter is missing, ask the user for clarification
3. Handle errors gracefully and explain what went wrong to the user
4. After performing an action, summarize what was done in a clear and friendly way
