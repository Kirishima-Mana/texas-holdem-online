"""
德州扑克牌型判断工具
使用 treys 库进行高效的牌型评估
"""
from treys import Card, Evaluator
from typing import List, Tuple, Optional


class PokerEvaluator:
    """扑克牌型评估器"""
    
    def __init__(self):
        self.evaluator = Evaluator()
    
    def evaluate_hand(self, hole_cards: List[str], board: List[str]) -> Tuple[int, str]:
        """
        评估手牌强度
        
        Args:
            hole_cards: 玩家手牌列表，如 ["Ah", "Kd"]
            board: 公共牌列表，如 ["Ts", "Jc", "Qh", "2d", "3s"]
        
        Returns:
            Tuple[score, hand_rank]: 分数（越低越好）和牌型描述
        """
        # 转换牌面字符串为 treys Card 对象
        hole = [Card.new(card) for card in hole_cards]
        community = [Card.new(card) for card in board]
        
        # 评估手牌
        score = self.evaluator.evaluate(hole, community)
        hand_class = self.evaluator.get_rank_class(score)
        hand_rank = self.evaluator.class_to_string(hand_class)
        
        return score, hand_rank
    
    def compare_hands(self, players_hole_cards: List[List[str]], board: List[str]) -> List[Tuple[int, int, str]]:
        """
        比较多个玩家的手牌，确定胜负
        
        Args:
            players_hole_cards: 每个玩家的手牌列表
            board: 公共牌列表
        
        Returns:
            List[Tuple[player_index, score, hand_rank]]: 按分数排序的玩家列表
        """
        results = []
        
        for i, hole_cards in enumerate(players_hole_cards):
            if len(hole_cards) == 2:  # 只有未弃牌的玩家
                score, hand_rank = self.evaluate_hand(hole_cards, board)
                results.append((i, score, hand_rank))
        
        # 按分数排序（德州扑克分数越低越好）
        results.sort(key=lambda x: x[1])
        return results
    
    def get_winner_indices(self, players_hole_cards: List[List[str]], board: List[str]) -> List[int]:
        """
        获取赢家索引（可能有多个平局）
        
        Returns:
            List[int]: 赢家索引列表
        """
        if not players_hole_cards:
            return []
        
        results = self.compare_hands(players_hole_cards, board)
        if not results:
            return []
        
        # 找到最低分数（最好牌型）
        best_score = results[0][1]
        winners = [idx for idx, score, _ in results if score == best_score]
        
        return winners
    
    def card_to_string(self, card_int: int) -> str:
        """将 treys Card 整数转换为字符串表示"""
        return Card.int_to_str(card_int)
    
    def string_to_card(self, card_str: str) -> int:
        """将字符串转换为 treys Card 整数"""
        return Card.new(card_str)


# 全局评估器实例
evaluator = PokerEvaluator()


def create_deck() -> List[str]:
    """创建一副标准的52张扑克牌"""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    suits = ['h', 'd', 'c', 's']  # 红桃, 方块, 梅花, 黑桃
    
    deck = []
    for rank in ranks:
        for suit in suits:
            deck.append(f"{rank}{suit}")
    
    return deck


def shuffle_deck(deck: List[str]) -> List[str]:
    """洗牌"""
    import random
    shuffled = deck.copy()
    random.shuffle(shuffled)
    return shuffled


def deal_cards(deck: List[str], num_cards: int) -> Tuple[List[str], List[str]]:
    """
    发牌
    
    Returns:
        Tuple[dealt_cards, remaining_deck]: 发出的牌和剩余的牌堆
    """
    if num_cards > len(deck):
        raise ValueError("牌堆中没有足够的牌")
    
    dealt = deck[:num_cards]
    remaining = deck[num_cards:]
    
    return dealt, remaining


def is_valid_card(card_str: str) -> bool:
    """检查牌面字符串是否有效"""
    if len(card_str) != 2:
        return False
    
    rank, suit = card_str[0], card_str[1]
    valid_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    valid_suits = ['h', 'd', 'c', 's']
    
    return rank in valid_ranks and suit in valid_suits