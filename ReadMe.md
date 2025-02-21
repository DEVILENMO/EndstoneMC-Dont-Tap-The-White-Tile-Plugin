# ARC Don't Tap The White Tile Plugin

[English](#English) | [中文](#中文)

<div align="center">
    <img src="./demo.gif" alt="Game Demo">
    <p><em>Gameplay Demonstration / 游戏演示</em></p>
</div>

# English

## Introduction
ARC Don't Tap The White Tile is a classic mini-game plugin for Minecraft Bedrock servers. Players need to quickly tap black tiles to clear rows. The faster you clear them, the better ranking you'll get based on your completion time.

## Features
- Classic Don't Tap White Tile gameplay
- Custom configurations
- Multi-language support
- Player records and rankings system

## Installation
1. Place the plugin file in your server's plugins folder
2. Use /reload command in server
3. Configuration files will be automatically generated in `[server_root]/plugins/ARCDTWT/`

## Configuration
### Files Structure
- `DTWTConfig.yml`: Main configuration file
- `DTWTdata.db`: Database file for storing player records
- `ZH-CN.txt`: Chinese language file
- `ENG.txt`: English language file (optional, you can find in ./dist/ENG.txt)

### DTWTConfig.yml Parameters
```yaml
DEFAULT_LANGUAGE_CODE=ZH-CN  # Language setting (ZH-CN/ENG)
DATABASE_PATH=DTWTdata.db    # Database file path
TOTAL_BLACK_TILE_NUM=20      # Total rows to clear in each game
```

### Commands
- `/dtwt` : View plugin description, rankings and personal records
- `/createdtwt` : Create a new game facility (OP only)

### Creating Game Facility
1. Build a 4×5×1 rectangle screen in the overworld
2. Place an easily breakable block (e.g., yellow wool) nearby as game trigger
3. Type /createdtwt
4. Follow the prompts to:
- Right-click the bottom-left corner of the screen
- Right-click the top-right corner
- Right-click the trigger block
5. A hint message will be shown white when setup is complete
6. Break the trigger block to start playing

# 中文

## 简介
ARC别踩白块是一个经典的Minecraft基岩版服务器小游戏插件。玩家需要快速点击黑色方块来消除行，完成速度越快，根据用时排名就越高。

## 特性
- 经典别踩白块玩法
- 自定义配置选项
- 多语言支持
- 玩家记录与排名系统

## 安装
1. 将插件文件放入服务器插件文件夹
2. 启动/重启服务器
3. 配置文件将自动生成在`[服务器根目录]/plugins/ARCDTWT/`下

## 配置

### 文件结构
- `DTWTConfig.yml`: 主配置文件
- `DTWTdata.db`: 储存玩家记录的数据库文件
- `ZH-CN.txt`: 中文语言文件
- `ENG.txt`: 英文语言文件（可选）

### DTWTConfig.yml 参数说明
```yaml
DEFAULT_LANGUAGE_CODE=ZH-CN  # 语言设置（ZH-CN/ENG）
DATABASE_PATH=DTWTdata.db    # 数据库文件路径
TOTAL_BLACK_TILE_NUM=20      # 每局游戏需要消除的总行数
```

### 命令
- /dtwt: 查看插件说明、排行榜和个人记录
- /createdtwt: 创建新的游戏设施（仅OP可用）

### 创建游戏设施
1. 在主世界建造一个4×5×1的矩形屏幕
2. 在附近放置一个容易打碎的方块（如金色羊毛）作为触发器
3. 输入/createdtwt
4. 按提示依次：
- 右键点击屏幕左下角
- 右键点击屏幕右上角
- 右键点击触发方块
5. 设置完成后会有提示
6. 打碎触发方块即可开始游戏