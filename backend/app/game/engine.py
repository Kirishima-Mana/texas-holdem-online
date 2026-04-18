"""
德州扑克游戏引擎
核心游戏逻辑和状态管理 - 重构版
"""
import asyncio
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field

from .table import Table
from .player import Player
from ..config import settings

logger = logging.getLogger(__name__)


# 创建一副标准扑克牌
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['h', 'd', 'c', 's']


class GameEngine:
    """德州扑克游戏引擎 - 重构版"""

    def __init__(self):
        self.table = Table()
        self.hand_id: int = 0
        self.is_game_active: bool = False
        self.action_timer: Optional[asyncio.Task] = None
        self.hand_history: List[Dict] = []

        # 当前下注轮次追踪
        self.current_round_bets: Dict[int, int] = {}  # position -> bet this round
        self.last_raiser: Optional[int] = None  # 最后加注的玩家位置
        self.actions_this_round: int = 0  # 本轮行动计数

    # ==================== 游戏生命周期 ====================

    def start_game(self):
        """开始游戏（由房主触发）"""
        connected = self.table.get_connected_players()
        if len(connected) < settings.min_players:
            raise ValueError(f"需要至少 {settings.min_players} 名玩家才能开始游戏")

        self.is_game_active = True
        self._start_new_hand()

    def _start_new_hand(self):
        """开始新的一手牌"""
        self.hand_id += 1
        self.table.reset_for_new_hand()
        self._deal_hole_cards()
        self._collect_blinds()
        self._set_first_player_preflop()

        logger.info(f"第 {self.hand_id} 手牌开始, 阶段: {self.table.stage}")

    def _deal_hole_cards(self):
        """发底牌给所有活跃且连接的玩家"""
        for position in sorted(self.table.players.keys()):
            player = self.table.players[position]
            if player.is_active and player.is_connected:
                cards = [self.table.deck.pop(0), self.table.deck.pop(0)]
                player.hole_cards = cards

    def _collect_blinds(self):
        """收集盲注"""
        sb_pos = self.table.small_blind_position
        bb_pos = self.table.big_blind_position

        sb_player = self.table.get_player_by_position(sb_pos)
        bb_player = self.table.get_player_by_position(bb_pos)

        # 小盲注
        if sb_player:
            sb_amount = min(self.table.small_blind, sb_player.chips)
            sb_player.chips -= sb_amount
            sb_player.current_bet = sb_amount
            if sb_player.chips == 0:
                sb_player.is_all_in = True

        # 大盲注
        if bb_player:
            bb_amount = min(self.table.big_blind, bb_player.chips)
            bb_player.chips -= bb_amount
            bb_player.current_bet = bb_amount
            if bb_player.chips == 0:
                bb_player.is_all_in = True

        # 设置当前最大下注
        self.table.current_max_bet = max(
            sb_player.current_bet if sb_player else 0,
            bb_player.current_bet if bb_player else 0
        )

        # 初始化回合下注追踪
        self.current_round_bets = {}
        for pos, p in self.table.players.items():
            self.current_round_bets[pos] = p.current_bet

        self.last_raiser = bb_pos  # 大盲注视为初始"加注者"
        self.actions_this_round = 0

    def _set_first_player_preflop(self):
        """设置翻牌前第一个行动的玩家（大盲注左侧）"""
        self.table.current_player_position = self._find_next_acting_player(
            self.table.big_blind_position
        )
        self._start_action_timer()

    def _find_next_acting_player(self, after_position: int) -> Optional[int]:
        """从指定位置开始，找到下一个可以行动的玩家"""
        positions = sorted(self.table.players.keys())
        if not positions:
            return None

        try:
            start_idx = positions.index(after_position)
        except ValueError:
            start_idx = 0

        for i in range(1, len(positions) + 1):
            idx = (start_idx + i) % len(positions)
            pos = positions[idx]
            player = self.table.players[pos]
            if self._can_player_act(player):
                return pos

        return None

    def _can_player_act(self, player: Player) -> bool:
        """检查玩家是否可以行动"""
        return (
            player.is_active
            and not player.is_folded
            and not player.is_all_in
            and player.is_connected
        )

    def _count_actable_players(self) -> int:
        """统计可以行动的玩家数"""
        return sum(1 for p in self.table.players.values() if self._can_player_act(p))

    def _count_non_folded_players(self) -> int:
        """统计未弃牌的玩家数"""
        return sum(
            1 for p in self.table.players.values()
            if p.is_active and not p.is_folded
        )

    # ==================== 行动处理 ====================

    async def process_player_action(
        self, user_id: int, action: str, amount: Optional[int] = None
    ) -> Dict:
        """处理玩家行动"""
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return {"success": False, "error": "玩家不在牌桌上"}

        if self.table.current_player_position != player.position:
            return {"success": False, "error": "现在不是你的行动回合"}

        if not self._can_player_act(player):
            return {"success": False, "error": "玩家不能行动"}

        result = {"success": True, "action": action}

        if action == "fold":
            player.fold()
            result["message"] = f"{player.username} 弃牌"

        elif action == "check":
            call_amount = player.get_call_amount(self.table.current_max_bet)
            if call_amount > 0:
                return {"success": False, "error": "不能过牌，需要跟注或弃牌"}
            player.has_acted = True
            player.last_action_time = datetime.utcnow()
            result["message"] = f"{player.username} 过牌"

        elif action == "call":
            call_amount = player.get_call_amount(self.table.current_max_bet)
            if call_amount <= 0:
                return {"success": False, "error": "无需跟注，可以过牌"}
            actual_call = min(call_amount, player.chips)
            player.chips -= actual_call
            player.current_bet += actual_call
            player.has_acted = True
            if player.chips == 0:
                player.is_all_in = True
            player.last_action_time = datetime.utcnow()
            self.current_round_bets[player.position] = player.current_bet
            result["message"] = f"{player.username} 跟注 {actual_call}"

        elif action == "raise":
            if amount is None or amount <= 0:
                return {"success": False, "error": "需要指定加注金额"}

            call_amount = player.get_call_amount(self.table.current_max_bet)
            total_needed = call_amount + amount

            if total_needed > player.chips:
                # 如果加注额不够，改为全下
                if player.chips > call_amount:
                    total_needed = player.chips
                else:
                    return {"success": False, "error": "筹码不足以加注"}

            player.chips -= total_needed
            player.current_bet += total_needed
            player.has_acted = True
            self.table.current_max_bet = player.current_bet
            self.last_raiser = player.position
            if player.chips == 0:
                player.is_all_in = True
            player.last_action_time = datetime.utcnow()
            self.current_round_bets[player.position] = player.current_bet
            # 加注后，其他玩家的 has_acted 需要重置（他们需要重新回应）
            self._reset_acted_after_raise(player.position)
            result["message"] = f"{player.username} 加注到 {player.current_bet}"

        elif action == "all_in":
            all_in_amount = player.chips
            if all_in_amount <= 0:
                return {"success": False, "error": "没有筹码可以全下"}

            player.current_bet += all_in_amount
            player.chips = 0
            player.is_all_in = True
            player.has_acted = True
            if player.current_bet > self.table.current_max_bet:
                self.table.current_max_bet = player.current_bet
                self.last_raiser = player.position
                self._reset_acted_after_raise(player.position)
            player.last_action_time = datetime.utcnow()
            self.current_round_bets[player.position] = player.current_bet
            result["message"] = f"{player.username} 全下 {all_in_amount}"

        else:
            return {"success": False, "error": f"未知行动: {action}"}

        self.actions_this_round += 1

        # 取消当前计时器
        self.cancel_action_timer()

        # 检查并推进游戏
        await self._advance_game()

        return result

    def _reset_acted_after_raise(self, raiser_position: int):
        """加注后重置其他玩家的行动状态（他们需要重新回应）"""
        for pos, player in self.table.players.items():
            if pos != raiser_position and self._can_player_act(player):
                player.has_acted = False

    async def _advance_game(self):
        """推进游戏状态：检查回合是否结束，决定下一步"""
        # 先检查是否只剩一个未弃牌玩家
        non_folded = self._count_non_folded_players()
        if non_folded <= 1:
            await self._showdown()
            return

        # 检查当前下注轮是否结束
        if self._is_round_complete():
            await self._advance_to_next_stage()
        else:
            # 推进到下一个可行动的玩家
            next_pos = self._find_next_acting_player(self.table.current_player_position)
            if next_pos is not None:
                self.table.current_player_position = next_pos
                self._start_action_timer()
            else:
                # 没有可行动的玩家，进入下一阶段
                await self._advance_to_next_stage()

    def _is_round_complete(self) -> bool:
        """检查当前下注轮是否完成"""
        actable_players = [p for p in self.table.players.values() if self._can_player_act(p)]

        if not actable_players:
            return True

        # 所有可行动玩家都已行动 且 下注额都等于当前最大下注
        for player in actable_players:
            if not player.has_acted:
                return False
            if player.current_bet < self.table.current_max_bet:
                return False

        return True

    async def _advance_to_next_stage(self):
        """进入下一个游戏阶段"""
        # 收集下注到池中
        self._collect_bets_to_pot()

        # 重置玩家行动状态
        for player in self.table.players.values():
            player.has_acted = False
            player.current_bet = 0

        self.current_round_bets = {}
        self.last_raiser = None
        self.actions_this_round = 0

        # 推进阶段
        if self.table.stage == "preflop":
            # 翻牌：发3张公共牌
            self.table.stage = "flop"
            self._burn_and_deal_community(3)

        elif self.table.stage == "flop":
            self.table.stage = "turn"
            self._burn_and_deal_community(1)

        elif self.table.stage == "turn":
            self.table.stage = "river"
            self._burn_and_deal_community(1)

        elif self.table.stage == "river":
            await self._showdown()
            return

        # 检查是否有可行动的玩家（可能所有人都全下了）
        actable = self._count_actable_players()
        non_folded = self._count_non_folded_players()

        if non_folded <= 1:
            await self._showdown()
            return

        if actable <= 1:
            # 只剩0-1个可行动的玩家，直接发完所有牌
            # 需要把剩余的公共牌发完
            while len(self.table.community_cards) < 5 and self.table.stage != "showdown":
                if self.table.stage == "flop":
                    self.table.stage = "turn"
                    self._burn_and_deal_community(1)
                elif self.table.stage == "turn":
                    self.table.stage = "river"
                    self._burn_and_deal_community(1)
                else:
                    break
            await self._showdown()
            return

        # 设置第一个行动的玩家（庄家左侧第一个可行动的玩家）
        self.table.current_player_position = self._find_next_acting_player(
            self.table.dealer_position
        )
        self.table.current_max_bet = 0

        self._start_action_timer()
        logger.info(f"进入 {self.table.stage} 阶段")

    def _burn_and_deal_community(self, count: int):
        """烧牌并发公共牌"""
        if self.table.deck:
            self.table.deck.pop(0)  # 烧一张牌
        for _ in range(count):
            if self.table.deck:
                self.table.community_cards.append(self.table.deck.pop(0))

    def _collect_bets_to_pot(self):
        """收集所有下注到底池"""
        total = 0
        for player in self.table.players.values():
            total += player.current_bet
            player.current_bet = 0
        self.table.pot_amount += total

    # ==================== 摊牌和结算 ====================

    async def _showdown(self):
        """摊牌阶段"""
        self.table.stage = "showdown"
        self._collect_bets_to_pot()
        self.cancel_action_timer()

        non_folded_players = [
            p for p in self.table.players.values()
            if p.is_active and not p.is_folded and p.hole_cards
        ]

        if len(non_folded_players) == 1:
            # 只剩一个玩家，直接赢得底池
            winner = non_folded_players[0]
            winner.chips += self.table.pot_amount
            result_info = {
                "winners": [{"user_id": winner.user_id, "username": winner.username, "hand_rank": "无人对决"}],
                "pot": self.table.pot_amount
            }
        elif len(non_folded_players) >= 2:
            # 评估手牌
            result_info = self._evaluate_and_distribute(non_folded_players)
        else:
            result_info = {"winners": [], "pot": self.table.pot_amount}

        # 记录历史
        self.hand_history.append({
            "hand_id": self.hand_id,
            "timestamp": datetime.utcnow().isoformat(),
            "community_cards": self.table.community_cards.copy(),
            "pot_amount": self.table.pot_amount,
            "winners": result_info.get("winners", []),
            "players": [
                {
                    "user_id": p.user_id,
                    "username": p.username,
                    "position": p.position,
                    "is_folded": p.is_folded,
                    "end_chips": p.chips
                }
                for p in self.table.players.values()
            ]
        })

        # 检查盲注升级
        if self.table.should_increase_blinds():
            self.table.increase_blinds()
            logger.info(f"盲注升级到 {self.table.small_blind}/{self.table.big_blind}")

        # 等待后开始下一手或结束游戏
        await asyncio.sleep(3)

        # 检查游戏是否结束
        players_with_chips = [
            p for p in self.table.players.values()
            if p.is_active and p.chips > 0
        ]
        if len(players_with_chips) <= 1:
            await self._end_game()
        else:
            self._start_new_hand()

    def _evaluate_and_distribute(self, non_folded_players: List[Player]) -> Dict:
        """评估手牌并分配底池"""
        from ..utils.poker_logic import evaluator as poker_eval

        player_hands = []
        for p in non_folded_players:
            player_hands.append((p, p.hole_cards))

        # 评估所有手牌
        results = []
        for player, hole_cards in player_hands:
            try:
                score, hand_rank = poker_eval.evaluate_hand(hole_cards, self.table.community_cards)
                results.append((player, score, hand_rank))
            except Exception as e:
                logger.error(f"评估手牌失败 {player.username}: {e}")
                results.append((player, 9999999, "Invalid"))

        # 按分数排序（越低越好）
        results.sort(key=lambda x: x[1])

        # 找到赢家（可能有平局）
        best_score = results[0][1]
        winners = [(p, s, r) for p, s, r in results if s == best_score]

        # 分配底池
        share = self.table.pot_amount // len(winners)
        remainder = self.table.pot_amount % len(winners)

        winner_info = []
        for i, (player, score, hand_rank) in enumerate(winners):
            amount = share + (1 if i < remainder else 0)
            player.chips += amount
            winner_info.append({
                "user_id": player.user_id,
                "username": player.username,
                "hand_rank": hand_rank,
                "prize": amount
            })
            logger.info(f"{player.username} 赢得 {amount} 筹码 ({hand_rank})")

        return {"winners": winner_info, "pot": self.table.pot_amount}

    async def _end_game(self):
        """结束游戏"""
        self.is_game_active = False
        self.cancel_action_timer()

        remaining = [p for p in self.table.players.values() if p.is_active and p.chips > 0]
        if remaining:
            winner = max(remaining, key=lambda p: p.chips)
            logger.info(f"游戏结束！最终赢家: {winner.username}，筹码: {winner.chips}")

    # ==================== 计时器 ====================

    def _start_action_timer(self):
        """开始行动计时器"""
        self.cancel_action_timer()
        self.action_timer = asyncio.create_task(self._handle_action_timeout())

    def cancel_action_timer(self):
        """取消行动计时器"""
        if self.action_timer and not self.action_timer.done():
            self.action_timer.cancel()
        self.action_timer = None

    async def _handle_action_timeout(self):
        """处理行动超时：自动弃牌"""
        try:
            await asyncio.sleep(self.table.action_timeout)

            if self.is_game_active and self.table.current_player_position is not None:
                player = self.table.get_player_by_position(self.table.current_player_position)
                if player and self._can_player_act(player):
                    player.fold()
                    self.actions_this_round += 1
                    logger.info(f"玩家 {player.username} 行动超时，自动弃牌")
                    await self._advance_game()

        except asyncio.CancelledError:
            pass

    # ==================== 断线重连 ====================

    async def handle_player_disconnect(self, user_id: int):
        """处理玩家断开连接"""
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return

        player.is_connected = False

        # 如果轮到该玩家行动，自动弃牌
        if (self.is_game_active
                and self.table.current_player_position == player.position
                and self._can_player_act(player)):
            player.fold()
            self.actions_this_round += 1
            logger.info(f"玩家 {player.username} 断线，自动弃牌")
            await self._advance_game()

    async def handle_player_reconnect(self, user_id: int, websocket_id: str):
        """处理玩家重新连接"""
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return

        player.is_connected = True
        player.websocket_id = websocket_id
        logger.info(f"玩家 {player.username} 重新连接")

    # ==================== 游戏状态 ====================

    def get_game_state(self, user_id: Optional[int] = None) -> Dict:
        """获取游戏状态（区分玩家/旁观者视角）"""
        is_spectator = True
        if user_id:
            player = self.table.get_player_by_user_id(user_id)
            is_spectator = player is None or not player.is_active

        return {
            "is_game_active": self.is_game_active,
            "hand_id": self.hand_id,
            "table_state": self.table.to_dict(spectator_view=is_spectator),
            "blind_level": self.table.blind_level,
            "next_blind_increase": (
                self.table.last_blind_increase +
                timedelta(minutes=settings.blind_increase_minutes)
            ).isoformat() if self.is_game_active else None,
            "is_spectator": is_spectator
        }