"""
德州扑克游戏引擎
核心游戏逻辑和状态管理
"""
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field

from .table import Table
from .player import Player
from ..config import settings
from ..utils.poker_logic import evaluator

logger = logging.getLogger(__name__)


@dataclass
class GameEngine:
    """游戏引擎"""

    table: Table = field(default_factory=Table)
    hand_id: int = 0
    is_game_active: bool = False
    action_timer: Optional[asyncio.Task] = None
    broadcast_callback: Optional[callable] = None  # 状态变化时回调广播
    game_winner: Optional[Dict] = None  # 整局冠军信息

    # 游戏历史
    hand_history: List[Dict] = field(default_factory=list)

    def set_broadcast_callback(self, cb: callable):
        """设置广播回调（由 WebSocketManager 注入）"""
        self.broadcast_callback = cb

    async def _notify_state_change(self):
        """通知外部状态变化"""
        if self.broadcast_callback:
            await self.broadcast_callback()
    
    def start_game(self):
        """开始游戏"""
        if len(self.table.get_connected_players()) < settings.min_players:
            raise ValueError(f"需要至少 {settings.min_players} 名玩家才能开始游戏")

        # 如果是全新的游戏（上一局已结束），重置所有筹码
        was_game_over = not self.is_game_active
        if was_game_over:
            for p in self.table.players.values():
                if p.is_active:
                    p.chips = settings.initial_chips
            self.table.blind_level = 1
            self.table.small_blind = settings.small_blind
            self.table.big_blind = settings.big_blind
            self.table.last_blind_increase = datetime.utcnow()
            self.hand_id = 0
            self.game_winner = None
            logger.info("新一局开始，所有玩家筹码重置")

        self.is_game_active = True
        self.hand_id += 1
        self.table.reset_for_new_hand()

        # 设置初始盲注
        self.collect_blinds()

        # 发底牌
        self.table.deal_hole_cards()

        # 开始行动计时
        self.start_action_timer()

        logger.info(f"游戏开始，第 {self.hand_id} 手牌")
    
    def collect_blinds(self):
        """收集盲注"""
        small_blind_player = self.table.get_player_by_position(self.table.small_blind_position)
        big_blind_player = self.table.get_player_by_position(self.table.big_blind_position)

        if small_blind_player:
            amount = min(self.table.small_blind, small_blind_player.chips)
            if amount > 0:
                small_blind_player.bet(amount)
            small_blind_player.has_acted = False

        if big_blind_player:
            amount = min(self.table.big_blind, big_blind_player.chips)
            if amount > 0:
                big_blind_player.bet(amount)
            big_blind_player.has_acted = False

        # 设置当前最大下注
        self.table.current_max_bet = self.table.big_blind
    
    async def process_player_action(
        self, 
        user_id: int, 
        action: str, 
        amount: Optional[int] = None
    ) -> Dict:
        """
        处理玩家行动
        
        Args:
            user_id: 玩家ID
            action: 行动类型 (fold, check, call, raise, all_in)
            amount: 加注金额（仅 raise 时需要）
        
        Returns:
            处理结果字典
        """
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return {"success": False, "error": "玩家不在牌桌上"}
        
        if self.table.current_player_position != player.position:
            return {"success": False, "error": "现在不是你的行动回合"}
        
        if not player.can_act():
            return {"success": False, "error": "玩家不能行动"}
        
        # 处理行动
        result = {"success": True, "action": action}
        
        if action == "fold":
            player.fold()
            result["message"] = f"{player.username} 弃牌"
        
        elif action == "check":
            call_amount = player.get_call_amount(self.table.current_max_bet)
            if call_amount == 0:
                player.check_or_call(0)
                result["message"] = f"{player.username} 过牌"
            else:
                return {"success": False, "error": "不能过牌，需要跟注"}
        
        elif action == "call":
            call_amount = player.get_call_amount(self.table.current_max_bet)
            if player.bet(call_amount):
                result["message"] = f"{player.username} 跟注 {call_amount}"
            else:
                return {"success": False, "error": "筹码不足"}
        
        elif action == "raise":
            if amount is None:
                return {"success": False, "error": "需要指定加注金额"}
            
            min_raise = self.table.big_blind * 2
            if amount < min_raise:
                return {"success": False, "error": f"加注金额必须至少为 {min_raise}"}
            
            total_needed = player.get_call_amount(self.table.current_max_bet) + amount
            if player.bet(total_needed):
                self.table.current_max_bet = player.current_bet
                result["message"] = f"{player.username} 加注到 {player.current_bet}"
            else:
                return {"success": False, "error": "筹码不足"}
        
        elif action == "all_in":
            amount = player.chips
            if player.bet(amount):
                if player.current_bet > self.table.current_max_bet:
                    self.table.current_max_bet = player.current_bet
                result["message"] = f"{player.username} 全下 {amount}"
            else:
                return {"success": False, "error": "全下失败"}
        
        else:
            return {"success": False, "error": f"未知行动: {action}"}
        
        # 更新行动计数
        self.table.players_acted_this_round += 1

        # 如果是加注或全下（增加了当前最大下注），重置其他在线玩家的 has_acted
        # 因为他们需要对新的下注额做出回应；断开/全下玩家排除
        if action in ("raise", "all_in"):
            for p in self.table.get_active_players():
                if p.position != player.position and not p.is_all_in and p.is_connected:
                    p.has_acted = False
            self.table.players_acted_this_round = 1  # 只有当前玩家已行动

        # 检查是否需要进入下一阶段
        stage_before = self.table.stage
        await self.check_round_completion()

        # 确保游戏状态一致：推进玩家 + 重置计时器
        if not self.is_game_active:
            return result

        if self.table.stage == stage_before:
            # 回合未结束：推进到下一个可行动玩家
            next_pos = self.table.get_next_player_position(player.position)
            if next_pos is not None:
                self.table.current_player_position = next_pos
                self.reset_action_timer()
            else:
                # 没有可行动玩家
                non_folded = [p for p in self.table.get_active_players() if not p.is_folded]
                if len(non_folded) <= 1:
                    await self.proceed_to_showdown()
                    return result
                # 全员 all-in：正在由 _auto_complete_all_in 处理，不启动计时器
                if all(p.is_all_in for p in non_folded):
                    logger.info("全员 all-in，等待自动完成，跳过计时器")
                else:
                    for p in self.table.get_active_players():
                        if p.position != player.position and p.is_active and p.is_connected and not p.is_all_in:
                            self.table.current_player_position = p.position
                            break
                    self.reset_action_timer()
        # 阶段已变化：proceed_to_next_stage / proceed_to_showdown 已处理计时器和玩家

        return result
    
    async def check_round_completion(self):
        """检查当前回合是否完成"""
        active_players = self.table.get_active_players()
        
        # 检查是否只剩一个未弃牌玩家
        non_folded_players = [p for p in active_players if not p.is_folded]
        if len(non_folded_players) <= 1:
            await self.proceed_to_showdown()
            return
        
        # 检查是否所有玩家都已行动且下注持平
        # 断线玩家（!is_connected）视为已行动，避免死锁
        all_acted = all(
            p.has_acted or p.is_all_in or p.is_folded or not p.is_connected
            for p in active_players
        )

        bets_equal = all(
            p.current_bet == self.table.current_max_bet or p.is_all_in or p.is_folded or not p.is_connected
            for p in active_players
        )
        
        if all_acted and bets_equal:
            await self.proceed_to_next_stage()
    
    async def proceed_to_next_stage(self):
        """进入下一阶段"""
        # 收集下注到主池
        self.table.collect_bets()
        
        # 重置玩家行动状态
        for player in self.table.players.values():
            player.has_acted = False
            player.current_bet = 0
        
        self.table.players_acted_this_round = 0
        
        # 根据当前阶段决定下一步
        if self.table.stage == "preflop":
            self.table.stage = "flop"
            self.table.deal_community_cards(3)
            self.table.current_player_position = self.table.get_next_active_position(self.table.dealer_position)
        
        elif self.table.stage == "flop":
            self.table.stage = "turn"
            self.table.deal_community_cards(1)
            self.table.current_player_position = self.table.get_next_active_position(self.table.dealer_position)
        
        elif self.table.stage == "turn":
            self.table.stage = "river"
            self.table.deal_community_cards(1)
            self.table.current_player_position = self.table.get_next_active_position(self.table.dealer_position)
        
        elif self.table.stage == "river":
            await self.proceed_to_showdown()
            return
        
        # 验证当前玩家有效性
        cp = self.table.current_player_position
        if cp is None:
            cp = self.table.get_next_active_position(self.table.dealer_position)
            self.table.current_player_position = cp
        else:
            player = self.table.get_player_by_position(cp)
            if not player or not player.can_act():
                cp = self.table.get_next_active_position(self.table.dealer_position)
                self.table.current_player_position = cp

        # 检查是否所有玩家都 all-in（无人可行动）→ 自动完成剩余阶段
        active = [p for p in self.table.get_active_players() if not p.is_folded]
        if active and all(p.is_all_in for p in active):
            logger.info(f"所有活跃玩家 all-in，自动完成剩余阶段")
            self.action_timer = asyncio.create_task(self._auto_complete_all_in())
            return

        # 开始新阶段的行动计时
        self.start_action_timer()

        logger.info(f"进入 {self.table.stage} 阶段，当前玩家: {cp}")

    async def _auto_complete_all_in(self):
        """所有玩家 all-in 时自动发完公共牌并进入摊牌"""
        try:
            while self.is_game_active and self.table.stage not in ("showdown", "waiting"):
                await asyncio.sleep(1.0)  # 每阶段间隔 1 秒视觉效果

                if self.table.stage == "preflop":
                    self.table.stage = "flop"
                    self.table.deal_community_cards(3)
                elif self.table.stage == "flop":
                    self.table.stage = "turn"
                    self.table.deal_community_cards(1)
                elif self.table.stage == "turn":
                    self.table.stage = "river"
                    self.table.deal_community_cards(1)
                elif self.table.stage == "river":
                    await self.proceed_to_showdown()
                    await self._notify_state_change()
                    return

                await self._notify_state_change()
        except asyncio.CancelledError:
            pass
    
    async def proceed_to_showdown(self):
        """进入摊牌阶段 — 立即计算结果，延迟开始下一局"""
        self.table.stage = "showdown"
        self.cancel_action_timer()

        # 收集所有下注
        self.table.collect_bets()
        self.table.calculate_side_pots()

        # 确定赢家
        try:
            winners = self.determine_winners()
        except Exception as e:
            logger.error(f"确定赢家时出错: {e}", exc_info=True)
            winners = {}

        # 分配筹码
        if winners:
            self.distribute_pots(winners)

        # 记录手牌历史
        self.record_hand_history(winners)

        # 检查盲注升级
        if self.table.should_increase_blinds():
            self.table.increase_blinds()
            logger.info(f"盲注升级到 {self.table.small_blind}/{self.table.big_blind}")

        # 延迟 5 秒后开始下一局（不阻塞当前调用链）
        self.action_timer = asyncio.create_task(self._finish_showdown())

    async def _finish_showdown(self):
        """摊牌后等待，然后开始下一局或结束游戏"""
        try:
            await asyncio.sleep(5)

            # 移出筹码归零的玩家
            busted = [p for p in self.table.players.values() if p.is_active and p.chips <= 0]
            for p in busted:
                logger.info(f"玩家 {p.username} 筹码归零，移出牌桌")
                self.table.remove_player(p.user_id, keep_chips=False)

            active_players = [p for p in self.table.players.values() if p.is_active and p.chips > 0]
            if len(active_players) <= 1:
                await self.end_game()
            else:
                self.start_new_hand()

            # 通知前端状态变化
            await self._notify_state_change()
        except asyncio.CancelledError:
            pass
    
    def determine_winners(self) -> Dict[int, List[int]]:
        """确定赢家"""
        # 收集未弃牌玩家
        active_players = []
        for position, player in self.table.players.items():
            if player.is_active and not player.is_folded:
                active_players.append((position, player))

        if not active_players:
            return {}

        # 只剩 1 人时无需评估手牌，直接获胜
        if len(active_players) == 1:
            pos, p = active_players[0]
            return {0: [{
                "position": pos,
                "user_id": p.user_id,
                "username": p.username,
                "hand_rank": "对手弃牌",
                "hole_cards": p.hole_cards or []
            }]}

        # 多人摊牌：需要足够牌数（至少 5 张：2+3）才能评估
        player_hole_cards = []
        player_indices = []
        for position, player in active_players:
            if player.hole_cards:
                player_hole_cards.append(player.hole_cards)
                player_indices.append(position)

        if len(player_hole_cards) < 2 or len(self.table.community_cards) < 3:
            # 牌数不足以评估，第一个活跃玩家获胜
            pos, p = active_players[0]
            return {0: [{
                "position": pos,
                "user_id": p.user_id,
                "username": p.username,
                "hand_rank": "自动获胜",
                "hole_cards": p.hole_cards or []
            }]}

        # 使用 treys 评估手牌
        results = evaluator.compare_hands(player_hole_cards, self.table.community_cards)

        # 分组赢家（可能有平局）
        winners_by_score = {}
        for idx, score, hand_rank in results:
            position = player_indices[idx]
            player = self.table.get_player_by_position(position)

            if score not in winners_by_score:
                winners_by_score[score] = []

            winners_by_score[score].append({
                "position": position,
                "user_id": player.user_id,
                "username": player.username,
                "hand_rank": hand_rank,
                "hole_cards": player.hole_cards
            })

        # 只返回最佳手牌的赢家
        best_score = min(winners_by_score.keys())
        winners = {best_score: winners_by_score[best_score]}

        return winners
    
    def _eval_hands(self) -> Dict[int, tuple]:
        """评估所有未弃牌玩家的手牌，返回 {user_id: (score, rank)}"""
        scores = {}
        for p in self.table.players.values():
            if p.is_active and not p.is_folded and p.hole_cards:
                try:
                    if len(self.table.community_cards) >= 3:
                        score, rank = evaluator.evaluate_hand(p.hole_cards, self.table.community_cards)
                    else:
                        score, rank = (0, "自动获胜")
                    scores[p.user_id] = (score, rank)
                except Exception as e:
                    logger.warning(f"评估 {p.username} 手牌失败: {e}")
                    scores[p.user_id] = (9999, "?")
        return scores

    def _award(self, user_id: int, amount: int, label: str = ""):
        """给玩家发放筹码"""
        for p in self.table.players.values():
            if p.user_id == user_id:
                p.chips += amount
                logger.info(f"{p.username} 赢得{label} {amount} 筹码")
                return

    def distribute_pots(self, winners: Dict[int, List[Dict]] = None):
        """分配主池和边池 — 每个边池从有资格的玩家中独立判定最优手牌"""
        scores = self._eval_hands()
        if not scores:
            return

        # 计算边池总额，主池 = 总底池 - 边池总额
        side_pot_total = sum(sp["amount"] for sp in self.table.side_pots)
        main_pot = max(0, self.table.pot_amount - side_pot_total)

        # 分配主池：所有未弃牌玩家中手牌最好的
        if main_pot > 0:
            eligible = list(scores.keys())
            best = min(scores[uid][0] for uid in eligible)
            main_winners = [uid for uid in eligible if scores[uid][0] == best]
            share = main_pot // len(main_winners)
            rem = main_pot % len(main_winners)
            for i, uid in enumerate(main_winners):
                self._award(uid, share + (1 if i < rem else 0), "主池")

        # 分配每个边池：在 eligible_players 中找最优手牌
        for sp in self.table.side_pots:
            eligible = [uid for uid in sp["eligible_players"] if uid in scores]
            if not eligible:
                continue
            best = min(scores[uid][0] for uid in eligible)
            side_winners = [uid for uid in eligible if scores[uid][0] == best]
            share = sp["amount"] // len(side_winners)
            rem = sp["amount"] % len(side_winners)
            for i, uid in enumerate(side_winners):
                self._award(uid, share + (1 if i < rem else 0), "边池")
    
    def record_hand_history(self, winners: Dict[int, List[Dict]]):
        """记录手牌历史"""
        hand_record = {
            "hand_id": self.hand_id,
            "timestamp": datetime.utcnow().isoformat(),
            "community_cards": self.table.community_cards.copy(),
            "pot_amount": self.table.pot_amount,
            "winners": [],
            "players": []
        }
        
        # 记录玩家信息
        for position, player in self.table.players.items():
            if player.is_active:
                hand_record["players"].append({
                    "user_id": player.user_id,
                    "username": player.username,
                    "position": position,
                    "hole_cards": player.hole_cards.copy() if player.hole_cards else [],
                    "is_folded": player.is_folded,
                    "end_chips": player.chips
                })
        
        # 记录赢家
        if winners:
            best_score = min(winners.keys())
            for winner_info in winners[best_score]:
                hand_record["winners"].append({
                    "user_id": winner_info["user_id"],
                    "username": winner_info["username"],
                    "hand_rank": winner_info["hand_rank"],
                    "prize_share": None  # 会在 distribute_pots 后更新
                })
        
        self.hand_history.append(hand_record)
    
    def start_new_hand(self):
        """开始新的一手牌"""
        self.hand_id += 1
        self.table.reset_for_new_hand()
        self.collect_blinds()
        self.table.deal_hole_cards()

        # 确保当前玩家有效
        cp = self.table.current_player_position
        if cp is None:
            cp = self.table.get_next_active_position(self.table.big_blind_position)
            self.table.current_player_position = cp
        else:
            player = self.table.get_player_by_position(cp)
            if not player or not player.can_act():
                cp = self.table.get_next_active_position(self.table.big_blind_position)
                self.table.current_player_position = cp

        self.start_action_timer()

        logger.info(f"开始第 {self.hand_id} 手牌，当前玩家: {self.table.current_player_position}")
    
    async def end_game(self):
        """结束游戏"""
        self.is_game_active = False

        # 找出最终赢家
        remaining_players = [
            p for p in self.table.players.values()
            if p.is_active and p.chips > 0
        ]

        if remaining_players:
            winner = max(remaining_players, key=lambda p: p.chips)
            self.game_winner = {
                "user_id": winner.user_id,
                "username": winner.username,
                "chips": winner.chips
            }
            logger.info(f"游戏结束！赢家是 {winner.username}，筹码: {winner.chips}")

        # 取消行动计时器
        self.cancel_action_timer()
    
    def start_action_timer(self):
        """开始行动计时器"""
        self.cancel_action_timer()  # 取消现有的计时器
        
        self.action_timer = asyncio.create_task(
            self.handle_action_timeout()
        )
    
    def reset_action_timer(self):
        """重置行动计时器"""
        self.start_action_timer()
    
    def cancel_action_timer(self):
        """取消行动计时器"""
        if self.action_timer and not self.action_timer.done():
            self.action_timer.cancel()
            self.action_timer = None
    
    async def handle_action_timeout(self):
        """处理行动超时"""
        try:
            await asyncio.sleep(self.table.action_timeout)

            if self.is_game_active and self.table.current_player_position is not None:
                player = self.table.get_player_by_position(self.table.current_player_position)
                if player and not player.is_folded and not player.is_all_in:
                    # 超时自动弃牌
                    await self.process_player_action(player.user_id, "fold")
                    logger.info(f"玩家 {player.username} 行动超时，自动弃牌")
                elif player and player.is_all_in and self.is_game_active:
                    # all-in 玩家不能行动，推进到下一个玩家
                    next_pos = self.table.get_next_player_position(player.position)
                    if next_pos is not None:
                        self.table.current_player_position = next_pos
                        self.reset_action_timer()
                        logger.info(f"all-in 玩家 {player.username} 跳过，推进到位置 {next_pos}")
                    else:
                        logger.info(f"all-in 玩家 {player.username} 无后续玩家，等待回合完成")

        except asyncio.CancelledError:
            pass
    
    async def handle_player_disconnect(self, user_id: int):
        """处理玩家断开连接"""
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return

        was_host = player.is_host
        player.is_connected = False

        # 房主转让：转让给下一个在线的活跃玩家
        if was_host:
            player.is_host = False
            transferred = False
            # 第一优先：在线活跃玩家
            for p in self.table.players.values():
                if p.is_active and p.is_connected and p.user_id != user_id:
                    p.is_host = True
                    self.table.host_user_id = p.user_id
                    logger.info(f"房主权限转让给 {p.username}")
                    transferred = True
                    break
            # 第二优先：任意活跃玩家（包括断线的）
            if not transferred:
                for p in self.table.players.values():
                    if p.is_active and p.user_id != user_id:
                        p.is_host = True
                        self.table.host_user_id = p.user_id
                        logger.info(f"房主权限转让给 {p.username}（已断线）")
                        transferred = True
                        break
            # 无人可转让
            if not transferred:
                self.table.host_user_id = None
                logger.info("没有其他玩家可转让房主，房主清空")

        # 如果玩家正在行动，自动弃牌
        if (self.is_game_active and
            self.table.current_player_position == player.position and
            not player.is_folded and not player.is_all_in):
            await self.process_player_action(user_id, "fold")
            logger.info(f"玩家 {player.username} 断开连接，自动弃牌")

        # 全员断线 → 结束游戏
        active = [p for p in self.table.players.values() if p.is_active]
        if active and not any(p.is_connected for p in active):
            logger.info("所有玩家已断线，自动结束游戏")
            self.is_game_active = False
            self.cancel_action_timer()
    
    def kick_player(self, host_user_id: int, target_user_id: int) -> str:
        """房主踢出玩家，返回错误信息或空字符串"""
        host = self.table.get_player_by_user_id(host_user_id)
        if not host or not host.is_host:
            return "只有房主可以移除玩家"

        target = self.table.get_player_by_user_id(target_user_id)
        if not target:
            return "目标玩家不存在"

        if target_user_id == host_user_id:
            return "不能移除自己"

        # 如果游戏进行中且目标正在行动，先弃牌
        if (self.is_game_active and
            self.table.current_player_position == target.position and
            not target.is_folded and not target.is_all_in):
            # 使用同步 fold，不等待
            target.fold()

        self.table.remove_player(target_user_id, keep_chips=False)
        target.is_connected = False
        logger.info(f"房主 {host.username} 移除了玩家 {target.username}")
        return ""

    async def handle_player_reconnect(self, user_id: int, websocket_id: str):
        """处理玩家重新连接"""
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return
        
        player.is_connected = True
        player.websocket_id = websocket_id
        
        # 如果玩家在牌桌上但游戏未开始，保持旁观状态
        if not self.is_game_active and player.is_active:
            # 玩家可以重新加入
            pass
        
        logger.info(f"玩家 {player.username} 重新连接")
    
    def get_game_state(self, user_id: Optional[int] = None) -> Dict:
        """获取游戏状态"""
        is_spectator = True
        if user_id:
            player = self.table.get_player_by_user_id(user_id)
            is_spectator = player is None or not player.is_active

        state = {
            "is_game_active": self.is_game_active,
            "hand_id": self.hand_id,
            "table_state": self.table.to_dict(spectator_view=is_spectator, requesting_user_id=user_id),
            "blind_level": self.table.blind_level,
            "next_blind_increase": (
                self.table.last_blind_increase +
                timedelta(minutes=settings.blind_increase_minutes)
            ).isoformat() if self.is_game_active else None,
            "is_spectator": is_spectator,
            "game_winner": self.game_winner
        }

        # 摊牌阶段附加手牌排名信息
        if self.table.stage == "showdown":
            player_hands = []
            for pos, p in self.table.players.items():
                if p.is_active and not p.is_folded:
                    try:
                        if p.hole_cards and len(self.table.community_cards) >= 3:
                            score, rank = evaluator.evaluate_hand(p.hole_cards, self.table.community_cards)
                        elif p.hole_cards:
                            # 公共牌不足 3 张但手牌存在
                            score, rank = (0, "自动获胜")
                        else:
                            # 无手牌（断线等情况）
                            score, rank = (9999, "无手牌")
                        player_hands.append({
                            "user_id": p.user_id,
                            "username": p.username,
                            "hole_cards": p.hole_cards or [],
                            "hand_rank": rank,
                            "score": score
                        })
                    except Exception as e:
                        logger.warning(f"评估手牌失败 for {p.username}: {e}")
                        player_hands.append({
                            "user_id": p.user_id,
                            "username": p.username,
                            "hole_cards": p.hole_cards or [],
                            "hand_rank": "?",
                            "score": 9999
                        })
            if player_hands:
                player_hands.sort(key=lambda x: x["score"])
                state["showdown"] = {
                    "players": player_hands,
                    "winner": player_hands[0]
                }
            else:
                # fallback: 未能正常评估手牌时，从活跃玩家中找一个作为 "赢家"
                fallback_players = [
                    {"user_id": p.user_id, "username": p.username, "hole_cards": p.hole_cards or [],
                     "hand_rank": "自动获胜" if not p.is_folded else "已弃牌", "score": 0 if not p.is_folded else 9999}
                    for p in self.table.players.values() if p.is_active
                ]
                if fallback_players:
                    fallback_players.sort(key=lambda x: x["score"])
                    state["showdown"] = {
                        "players": fallback_players,
                        "winner": fallback_players[0]
                    }

        return state