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
    
    # 游戏历史
    hand_history: List[Dict] = field(default_factory=list)
    
    def start_game(self):
        """开始游戏"""
        if len(self.table.get_connected_players()) < settings.min_players:
            raise ValueError(f"需要至少 {settings.min_players} 名玩家才能开始游戏")
        
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
            small_blind_player.bet(self.table.small_blind)
        
        if big_blind_player:
            big_blind_player.bet(self.table.big_blind)
        
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
        
        # 检查是否需要进入下一阶段
        await self.check_round_completion()
        
        # 重置行动计时器
        self.reset_action_timer()
        
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
        all_acted = all(
            p.has_acted or p.is_all_in or p.is_folded 
            for p in active_players
        )
        
        bets_equal = all(
            p.current_bet == self.table.current_max_bet or p.is_all_in or p.is_folded
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
        
        # 开始新阶段的行动计时
        self.start_action_timer()
        
        logger.info(f"进入 {self.table.stage} 阶段")
    
    async def proceed_to_showdown(self):
        """进入摊牌阶段"""
        self.table.stage = "showdown"
        
        # 收集所有下注
        self.table.collect_bets()
        self.table.calculate_side_pots()
        
        # 确定赢家
        winners = self.determine_winners()
        
        # 分配筹码
        self.distribute_pots(winners)
        
        # 记录手牌历史
        self.record_hand_history(winners)
        
        # 检查盲注升级
        if self.table.should_increase_blinds():
            self.table.increase_blinds()
            logger.info(f"盲注升级到 {self.table.small_blind}/{self.table.big_blind}")
        
        # 准备下一手牌
        await asyncio.sleep(5)  # 给玩家看结果的时间
        
        # 检查游戏是否结束（只剩一个玩家）
        active_players = [p for p in self.table.players.values() if p.is_active and p.chips > 0]
        if len(active_players) <= 1:
            await self.end_game()
        else:
            self.start_new_hand()
    
    def determine_winners(self) -> Dict[int, List[int]]:
        """确定赢家"""
        # 获取未弃牌玩家的手牌
        active_players = []
        player_hole_cards = []
        player_indices = []
        
        for position, player in self.table.players.items():
            if player.is_active and not player.is_folded and player.hole_cards:
                active_players.append(player)
                player_hole_cards.append(player.hole_cards)
                player_indices.append(position)
        
        if not active_players:
            return {}
        
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
    
    def distribute_pots(self, winners: Dict[int, List[Dict]]):
        """分配主池和边池"""
        if not winners:
            return
        
        # 分配主池
        best_score = min(winners.keys())
        main_pot_winners = winners[best_score]
        
        if main_pot_winners:
            # 平分主池
            share = self.table.pot_amount // len(main_pot_winners)
            remainder = self.table.pot_amount % len(main_pot_winners)
            
            for i, winner_info in enumerate(main_pot_winners):
                player = self.table.get_player_by_position(winner_info["position"])
                if player:
                    amount = share + (1 if i < remainder else 0)
                    player.chips += amount
                    logger.info(f"{player.username} 赢得主池 {amount} 筹码")
        
        # 分配边池（如果有）
        for side_pot in self.table.side_pots:
            # 找出有资格赢取此边池的玩家
            eligible_winners = [
                w for w in main_pot_winners 
                if w["user_id"] in side_pot["eligible_players"]
            ]
            
            if eligible_winners:
                share = side_pot["amount"] // len(eligible_winners)
                remainder = side_pot["amount"] % len(eligible_winners)
                
                for i, winner_info in enumerate(eligible_winners):
                    player = self.table.get_player_by_position(winner_info["position"])
                    if player:
                        amount = share + (1 if i < remainder else 0)
                        player.chips += amount
                        logger.info(f"{player.username} 赢得边池 {amount} 筹码")
    
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
        self.start_action_timer()
        
        logger.info(f"开始第 {self.hand_id} 手牌")
    
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
                if player and player.can_act():
                    # 超时自动弃牌
                    await self.process_player_action(player.user_id, "fold")
                    logger.info(f"玩家 {player.username} 行动超时，自动弃牌")
        
        except asyncio.CancelledError:
            pass
    
    async def handle_player_disconnect(self, user_id: int):
        """处理玩家断开连接"""
        player = self.table.get_player_by_user_id(user_id)
        if not player:
            return
        
        player.is_connected = False
        
        # 如果玩家正在行动，自动弃牌
        if (self.is_game_active and 
            self.table.current_player_position == player.position and 
            player.can_act()):
            await self.process_player_action(user_id, "fold")
            logger.info(f"玩家 {player.username} 断开连接，自动弃牌")
    
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