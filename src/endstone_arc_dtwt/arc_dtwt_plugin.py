import math
import random
import time

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import event_handler, PlayerInteractEvent, BlockBreakEvent
from endstone.plugin import Plugin

from endstone_arc_dtwt.DatabaseManager import DatabaseManager
from endstone_arc_dtwt.LanguageManager import LanguageManager
from endstone_arc_dtwt.SettingManager import SettingManager

MAIN_PATH = 'plugins/ARCDTWT'

class ARCDTWTPlugin(Plugin):
    api_version = "0.5"
    commands = {
        "dtwt":
            {
                "description": "Show description of 'ARC Don't Tap the White Tile' plugin.",
                "usages": ["/dtwt"],
                "permissions": ["arc_dtwt.command.dtwt"],
            },
        "createdtwt": {
            "description": "Create a new game facility, will delete the old one if exists.",
            "usages": ["/createdtwt"]
        }
    }
    permissions = {
        "arc_dtwt.command.dtwt": {
            "description": "Can used by everyone.",
            "default": True,
        }
    }

    def __init__(self):
        super().__init__()
        self.setting_manager = SettingManager()
        default_language_dode = self.setting_manager.GetSetting('DEFAULT_LANGUAGE_CODE')
        self.language_manager = LanguageManager(default_language_dode if default_language_dode is not None else 'ZH-CN')
        # database
        self.db_manager = DatabaseManager(Path(MAIN_PATH) / self.setting_manager.GetSetting('DATABASE_PATH'))
        self._init_database()

        # Interact time record dict
        self.interact_time_dict = {}

        # Current Facility
        self.current_facility = self.get_game_facility()
        if self.current_facility is not None:
            print(f'[ARC DTWT]Successfully load game facility, game displayer ({self.current_facility['screen_start']} -> {self.current_facility['screen_end']}), start trigger at {self.current_facility['trigger_pos']}.')

        # Deploy new facility function
        self.if_in_deploying_state = False
        self.creator_name = None
        self.screen_start = None
        self.screen_end = None
        self.trigger_pos = None

        # Game function
        try:
            self.total_black_tile_num = int(self.setting_manager.GetSetting('TOTAL_BLACK_TILE_NUM'))
        except (ValueError, TypeError):
            self.total_black_tile_num = 20
        self.if_in_game = False
        self.game_start_time = None
        self.player_name = None
        self.current_display_seq = [None for _ in range(5)]
        self.current_black_tile_index = 0

    def on_load(self) -> None:
        self.logger.info(f"{ColorFormat.YELLOW}[ARC DTWT]Plugin loaded!")

    def on_enable(self) -> None:
        self.register_events(self)
        self.logger.info(f"{ColorFormat.YELLOW}[ARC DTWT]Plugin enabled!")

    def on_disable(self) -> None:
        self.logger.info(f"{ColorFormat.YELLOW}[ARC DTWT]Plugin disabled!")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name == "dtwt":
            if not isinstance(sender, Player):
                sender.send_message(f'[ARC DTWT]This command only works for players.')
                return True
            best_three_record = self.get_leaderboard(3)
            top1_record = 'null-∞' if len(best_three_record) < 1 else f'{best_three_record[0][0]}-{best_three_record[0][1]}'
            top2_record = 'null-∞' if len(best_three_record) < 2 else f'{best_three_record[1][0]}-{best_three_record[1][1]}'
            top3_record = 'null-∞' if len(best_three_record) < 3 else f'{best_three_record[2][0]}-{best_three_record[2][1]}'
            sender_player = self.server.get_player(sender.name)
            if sender_player is not None:
                sender_record = self.get_player_best_time(sender_player.xuid)
                if sender_record is None:
                    sender_record = '∞'
                sender_rank = self.get_player_rank(sender_player.xuid)
                if sender_rank is None:
                    sender_rank = '∞'
            else:
                sender_record = '∞'
                sender_rank = '∞'
            sender.send_message(self.language_manager.GetText('DTWT_DESCRIPTION').format(self.total_black_tile_num, top1_record, top2_record, top3_record, sender_record, sender_rank))
            return True
        if command.name == "createdtwt":
            if not isinstance(sender, Player):
                sender.send_message(f'[ARC DTWT]This command only works for players.')
                return True
            if not self.if_in_deploying_state or self.creator_name == sender.name:
                self.clear_deployment_memory()
                self.if_in_deploying_state = True
                self.creator_name = sender.name
                sender.send_message(self.language_manager.GetText('DTWT_CREATE_HINT1'))
            else:
                sender.send_message(self.language_manager.GetText('DTWT_HAS_ANOTHER_CREATOR_MESSAGE'))
            return True
        return False

    @event_handler
    def on_player_interact(self, event: PlayerInteractEvent):
        if self.if_in_deploying_state:
            if event.player.name == self.creator_name:
                if not self.check_if_valid_click(self.creator_name):
                    return
                if event.block.dimension.name != 'Overworld':
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DIMENSION_MESSAGE').format(event.block.dimension.name))
                    return
                if self.screen_start is None:
                    self.screen_start = (event.block.location.x, event.block.location.y, event.block.location.z)
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_START_CORNER_SET_MESSAGE').format(self.screen_start))
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_HINT2'))
                    return
                if self.screen_end is None:
                    possible_end_corner = (event.block.location.x, event.block.location.y, event.block.location.z)
                    # Judge if a 4 x 5 displayer
                    if self.screen_start[0] == possible_end_corner[0]:
                        # Width is supposed to be 4
                        if math.fabs(self.screen_start[2] - possible_end_corner[2]) != 3:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_WIDTH_MESSAGE'))
                            return
                        # Height = 5?
                        if possible_end_corner[1] - self.screen_start[1] != 4:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_HEIGHT_MESSAGE'))
                            return
                    elif self.screen_start[2] == possible_end_corner[2]:
                        # Width is supposed to be 4
                        if math.fabs(self.screen_start[0] - possible_end_corner[0]) != 3:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_WIDTH_MESSAGE'))
                            return
                        # Height = 5?
                        if possible_end_corner[1] - self.screen_start[1] != 4:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_HEIGHT_MESSAGE'))
                            return
                    else:
                        event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_NOT_A_PLANE_ERROR_MESSAGE'))
                        return
                    self.screen_end = possible_end_corner
                    # display green screen
                    # f'fill {' '.join([str(_) for _ in self.screen_start])} {' '.join([str(_) for _ in self.screen_end])} lime_wool'
                    self.server.dispatch_command(self.server.command_sender, self.get_fill_command(self.screen_start, self.screen_end, 'green_wool'))
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_END_CORNER_SET_MESSAGE').format(self.screen_end))
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_HINT3'))
                    return
                if self.trigger_pos is None:
                    self.trigger_pos = (event.block.location.x, event.block.location.y, event.block.location.z)
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_START_BLOCK_SET_MESSAGE').format(self.trigger_pos))
                    s = self.update_game_facility(self.screen_start, self.screen_end, self.trigger_pos)
                    if not s:
                        self.logger.error(f'[ARC DTWT]An error occurred while saving game facility to database.')
                    else:
                        self.display_single_color('white')
                        event.player.send_message(self.language_manager.GetText('DTWT_CREATE_HINT4'))
                        self.server.broadcast_message(self.language_manager.GetText('DTWT_CREATE_COMPLETED_BROADCAST').format(self.trigger_pos))
                        self.current_facility = self.get_game_facility()
                    self.clear_deployment_memory()
                    return
            else:
                return
        if self.if_in_game and event.player.name == self.player_name:
            if not self.check_if_valid_click(self.creator_name):
                return
            # Update game
            screen_pos = self.convert_world_pos_to_screen_pos((event.block.location.x, event.block.location.y, event.block.location.z))
            if screen_pos is None:
                event.player.send_message(self.language_manager.GetText('DTWT_PLAYER_CLICKED_INVALID_SCREEN_POS_MESSAGE'))
                return
            if screen_pos[1] != 0:
                event.player.send_message(self.language_manager.GetText('DTWT_PLAYER_CLICKED_WRONG_ROW_MESSGAE'))
                return
            if screen_pos[0] == self.current_display_seq[0]:
                self.current_black_tile_index += 1
                if self.current_black_tile_index == self.total_black_tile_num:
                    self.end_game(True, event.player)
                    return
                new_seq = self.current_display_seq[1:]
                if self.current_black_tile_index + 5 > self.total_black_tile_num:
                    new_seq.append(None)
                else:
                    new_seq.append(random.randint(0, 3))
                self.displayer_game_update(new_seq)
            else:
                self.end_game(False, event.player)
            return
        return

    @event_handler
    def on_block_breaked(self, event: BlockBreakEvent):
        if self.current_facility is not None:
            if not self.if_in_game:
                if (event.block.location.x == self.current_facility['trigger_pos'][0] and
                        event.block.location.y == self.current_facility['trigger_pos'][1] and
                        event.block.location.z == self.current_facility['trigger_pos'][2]):
                    self.start_game(event.player.name)
                    event.player.send_message(self.language_manager.GetText('DTWT_GAME_START_HINT'))
                    self.server.broadcast_message(self.language_manager.GetText('DTWT_GAME_START_BROADCAST').format(event.player.name))
                    event.cancelled = True
                    return
                return
            else:
                if event.block.location.x == self.current_facility['trigger_pos'][0] and event.block.location.y == self.current_facility['trigger_pos'][1] and event.block.location.z == self.current_facility['trigger_pos'][2]:
                    event.player.send_message(self.language_manager.GetText('DTWT_GAME_ALREADY_STARTED_MESSAGE').format(self.player_name))
                    event.cancelled = True
                    return
                return

    # Deploy
    def clear_deployment_memory(self):
        self.if_in_deploying_state = False
        self.creator_name = None
        self.screen_start = None
        self.screen_end = None
        self.trigger_pos = None

    # Game
    def start_game(self, player_name: str):
        self.if_in_game = True
        self.player_name = player_name
        self.game_start_time = time.time()

        # Random generate first 5 rows
        start_seq = []
        for _ in range(5):
            seed = int(time.time()) + _
            rg = random.Random(seed)
            start_seq.append(rg.randint(0, 3))
        self.displayer_game_update(start_seq)

    def end_game(self, if_successful: bool, player: Player):
        if if_successful:
            # Set displayer color
            self.display_single_color('lime')
            # Update record
            time_cost = time.time() - self.game_start_time
            self.update_player_record(player.xuid, player.name, time_cost)
            # Broadcast
            self.server.broadcast_message(self.language_manager.GetText('DTWT_PLAYER_WIN_BROADCAST').format(player.name, time_cost, self.get_player_rank(player.xuid)))
        else:
            # Set displayer color
            self.display_single_color('red')
            # Broadcast
            self.server.broadcast_message(self.language_manager.GetText('DTWT_PLAYER_GAME_OVER_BROADCAST').format(player.name))
        # clear game memory
        self.if_in_game = False
        self.player_name = None
        self.game_start_time = None
        self.current_display_seq = [None for _ in range(5)]
        self.current_black_tile_index = 0

    # Avoid interact jitter
    def check_if_valid_click(self, player_name: str) -> bool:
        current_time = time.time()
        _ = not player_name in self.interact_time_dict or (current_time - self.interact_time_dict[player_name]) > 0.125
        if _:
            self.interact_time_dict[player_name] = current_time
            return True
        else:
            return False

    # Displayer
    def display_single_color(self, color: str):
        # lime white red
        if self.current_facility is not None:
            self.server.dispatch_command(self.server.command_sender,
                                         self.get_fill_command(self.current_facility['screen_start'], self.current_facility['screen_end'], f'{color}_wool'))
            # f'fill {' '.join([str(_) for _ in self.current_facility['screen_start']])} {' '.join([str(_) for _ in self.current_facility['screen_end']])} {color}_wool'

    def displayer_game_update(self, new_seq: list):
        for _ in range(5):
            self.displayer_line_update(_, self.current_display_seq[_], new_seq[_])
        self.current_display_seq = new_seq

    def displayer_line_update(self, row: int, current_black_tile_pos: int, new_black_tile_pos: int):
        if new_black_tile_pos is None:
            for c in range(4):
                self.displayer_tile_update(row, c, 'green')
            return
        else:
            if current_black_tile_pos is None:
                for c in range(4):
                    if c == new_black_tile_pos:
                        self.displayer_tile_update(row, c, 'black')
                    else:
                        self.displayer_tile_update(row, c, 'white')
            else:
                if current_black_tile_pos == new_black_tile_pos:
                    return
                self.displayer_tile_update(row, current_black_tile_pos, 'white')
                self.displayer_tile_update(row, new_black_tile_pos, 'black')

    def displayer_tile_update(self, row: int, column: int, color: str):
        if self.current_facility['screen_start'][0] == self.current_facility['screen_end'][0]:
            if self.current_facility['screen_start'][2] > self.current_facility['screen_end'][2]:
                adjust = -1
            else:
                adjust = 1
            block_pos = (self.current_facility['screen_start'][0],
                         self.current_facility['screen_start'][1] + row,
                         self.current_facility['screen_start'][2] + column * adjust)
        elif self.current_facility['screen_start'][2] == self.current_facility['screen_end'][2]:
            if self.current_facility['screen_start'][0] > self.current_facility['screen_end'][0]:
                adjust = -1
            else:
                adjust = 1
            block_pos = (self.current_facility['screen_start'][0] + column * adjust,
                         self.current_facility['screen_start'][1] + row,
                         self.current_facility['screen_start'][2])
        else:
            self.logger.error('[ARC DTWT]An error occurred while updating screen, please recreate game facility.')
            return
        # self.server.dispatch_command(self.server.command_sender, f'fill {' '.join([str(_) for _ in block_pos])} {' '.join([str(_) for _ in block_pos])} {color}_wool')
        self.server.dispatch_command(self.server.command_sender, self.get_fill_command(block_pos, block_pos, f'{color}_wool'))

    def convert_world_pos_to_screen_pos(self, world_pos: tuple[float, float, float]):
        if self.current_facility['screen_start'][0] == self.current_facility['screen_end'][0]:
            if self.judge_if_number_in_range(self.current_facility['screen_start'][2], self.current_facility['screen_end'][2], world_pos[2]) \
                and self.current_facility['screen_start'][1] <= world_pos[1] <= self.current_facility['screen_end'][1]:
                return math.fabs(world_pos[2] - self.current_facility['screen_start'][2]), world_pos[1] - self.current_facility['screen_start'][1]
        elif self.current_facility['screen_start'][2] == self.current_facility['screen_end'][2]:
            if self.judge_if_number_in_range(self.current_facility['screen_start'][0], self.current_facility['screen_end'][0], world_pos[0]) \
                and self.current_facility['screen_start'][1] <= world_pos[1] <= self.current_facility['screen_end'][1]:
                return math.fabs(world_pos[0] - self.current_facility['screen_start'][0]), world_pos[1] - self.current_facility['screen_start'][1]
        else:
            self.logger.error('[ARC DTWT]An error occurred while calculating player clicked position, please recreate game facility.')
            return None

    # Player record
    def update_player_record(self, xuid: str, player_name: str, time: float) -> bool:
        """
        更新玩家记录
        :param xuid: 玩家的XUID
        :param player_name: 玩家名称
        :param time: 完成用时
        :return: 是否更新成功
        """
        # 查询现有记录
        existing_record = self.db_manager.query_one(
            "SELECT * FROM player_records WHERE xuid = ?",
            (xuid,)
        )

        if existing_record is None:
            # 玩家不存在，插入新记录
            return self.db_manager.insert("player_records", {
                "xuid": xuid,
                "player_name": player_name,
                "best_record": time
            })
        elif time < existing_record["best_record"]:
            # 玩家存在且新记录更好，更新记录
            return self.db_manager.update(
                "player_records",
                {"player_name": player_name, "best_record": time},
                "xuid = ?",
                (xuid,)
            )
        return False  # 现有记录更好，不更新

    def get_player_best_time(self, xuid: str) -> Optional[float]:
        """
        获取指定玩家的最佳用时
        :param xuid: 玩家XUID
        :return: 玩家最佳用时，如果玩家不存在返回None
        """
        result = self.db_manager.query_one(
            "SELECT best_record FROM player_records WHERE xuid = ?",
            (xuid,)
        )
        return result["best_record"] if result else None

    def get_player_rank(self, xuid: str) -> Optional[int]:
        """
        获取玩家排名
        :param xuid: 玩家XUID
        :return: 玩家排名（从1开始），未找到返回None
        """
        sql = """
        WITH RankedPlayers AS (
            SELECT xuid, 
                   ROW_NUMBER() OVER (ORDER BY best_record ASC) as rank
            FROM player_records
        )
        SELECT rank
        FROM RankedPlayers
        WHERE xuid = ?
        """
        result = self.db_manager.query_one(sql, (xuid,))
        return result["rank"] if result else None

    def get_leaderboard(self, limit: int, reverse: bool = False) -> List[Tuple[str, float]]:
        """
        获取排行榜
        :param limit: 获取数量
        :param reverse: 是否倒序（获取最慢记录）
        :return: [(玩家名, 用时)] 的列表
        """
        order = "DESC" if reverse else "ASC"
        sql = f"""
        SELECT player_name, best_record
        FROM player_records
        ORDER BY best_record {order}
        LIMIT ?
        """
        results = self.db_manager.query_all(sql, (limit,))
        return [(record["player_name"], record["best_record"]) for record in results]

    def get_average_time(self) -> Optional[float]:
        """
        获取所有玩家的平均用时
        :return: 平均用时，无记录返回None
        """
        sql = "SELECT AVG(best_record) as avg_time FROM player_records"
        result = self.db_manager.query_one(sql)
        return result["avg_time"] if result else None

    # Static function tools
    @staticmethod
    def judge_if_number_in_range(range_a, range_b, number) -> bool:
        return range_a <= number <= range_b if range_a <= range_b else range_b <= number <= range_a

    @staticmethod
    def get_fill_command(pos1: tuple, pos2: tuple, block_name: str) -> str:
        return f'fill {' '.join([str(_) for _ in pos1])} {' '.join([str(_) for _ in pos2])} {block_name}'

    # Database
    def _init_database(self):
        """初始化数据库表结构"""
        # 游戏设施信息表
        self.db_manager.create_table("game_facilities", {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "screen_start_x": "INTEGER NOT NULL",
            "screen_start_y": "INTEGER NOT NULL",
            "screen_start_z": "INTEGER NOT NULL",
            "screen_end_x": "INTEGER NOT NULL",
            "screen_end_y": "INTEGER NOT NULL",
            "screen_end_z": "INTEGER NOT NULL",
            "trigger_x": "INTEGER NOT NULL",
            "trigger_y": "INTEGER NOT NULL",
            "trigger_z": "INTEGER NOT NULL"
        })

        # 玩家记录表
        self.db_manager.create_table("player_records", {
            "xuid": "TEXT PRIMARY KEY",
            "player_name": "TEXT NOT NULL",
            "best_record": "REAL NOT NULL"
        })

    def update_game_facility(self, screen_start: tuple, screen_end: tuple, trigger_pos: tuple) -> bool:
        """
        更新游戏设施信息
        :param screen_start: 显示屏起点坐标 (x, y, z)
        :param screen_end: 显示屏终点坐标 (x, y, z)
        :param trigger_pos: 触发方块坐标 (x, y, z)
        :return: 是否更新成功
        """
        # 首先删除所有现有记录
        self.db_manager.execute("DELETE FROM game_facilities")

        # 插入新记录
        return self.db_manager.insert("game_facilities", {
            "screen_start_x": screen_start[0],
            "screen_start_y": screen_start[1],
            "screen_start_z": screen_start[2],
            "screen_end_x": screen_end[0],
            "screen_end_y": screen_end[1],
            "screen_end_z": screen_end[2],
            "trigger_x": trigger_pos[0],
            "trigger_y": trigger_pos[1],
            "trigger_z": trigger_pos[2]
        })

    def get_game_facility(self) -> Optional[Dict[str, Any]]:
        """
        获取游戏设施信息
        :return: 返回游戏设施信息字典，如果不存在则返回None
        格式：{
            'dimension': str,
            'screen_start': tuple(x, y, z),
            'screen_end': tuple(x, y, z),
            'trigger_pos': tuple(x, y, z)
        }
        """
        result = self.db_manager.query_one("SELECT * FROM game_facilities LIMIT 1")

        if result is None:
            return None

        return {
            'screen_start': (
                result['screen_start_x'],
                result['screen_start_y'],
                result['screen_start_z']
            ),
            'screen_end': (
                result['screen_end_x'],
                result['screen_end_y'],
                result['screen_end_z']
            ),
            'trigger_pos': (
                result['trigger_x'],
                result['trigger_y'],
                result['trigger_z']
            )
        }