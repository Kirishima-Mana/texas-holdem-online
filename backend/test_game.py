#!/usr/bin/env python3
"""
德州扑克游戏引擎测试
"""
import asyncio
import sys
from app.game.engine import GameEngine
from app.game.player import Player
from app.game.table import Table
from app.utils.poker_logic import create_deck, shuffle_deck

async def test_basic_game():
    """测试基本游戏流程"""
    print("🎯 开始测试德州扑克游戏引擎...")
    
    # 创建游戏引擎
    engine = GameEngine()
    
    # 创建测试玩家
    players = [
        Player(user_id=1, username="玩家1", session_token="token1"),
        Player(user_id=2, username="玩家2", session_token="token2"),
        Player(user_id=3, username="玩家3", session_token="token3"),
    ]
    
    # 添加玩家到牌桌
    for i, player in enumerate(players):
        player.chips = 20000  # 初始筹码
        engine.table.add_player(player, position=i)
        print(f"👤 添加玩家: {player.username} (位置: {i}, 筹码: {player.chips})")
    
    # 测试开始游戏
    try:
        engine.start_game()
        print("✅ 游戏开始成功")
        print(f"🃏 当前手牌ID: {engine.hand_id}")
        print(f"🎲 游戏阶段: {engine.table.stage}")
        print(f"👑 庄家位置: {engine.table.dealer_position}")
        print(f"💰 小盲注: {engine.table.small_blind}, 大盲注: {engine.table.big_blind}")
        
        # 检查玩家手牌
        for position, player in engine.table.players.items():
            if player.hole_cards:
                print(f"🎴 {player.username} 的手牌: {player.hole_cards}")
        
        # 测试玩家行动
        print("\n🎮 测试玩家行动...")
        
        # 玩家1弃牌
        result = await engine.process_player_action(1, "fold")
        print(f"玩家1弃牌: {result}")
        
        # 玩家2跟注
        result = await engine.process_player_action(2, "call")
        print(f"玩家2跟注: {result}")
        
        # 玩家3加注
        result = await engine.process_player_action(3, "raise", 200)
        print(f"玩家3加注: {result}")
        
        # 检查游戏状态
        print(f"\n📊 游戏状态:")
        print(f"底池: {engine.table.pot_amount}")
        print(f"当前最大下注: {engine.table.current_max_bet}")
        
        # 测试进入下一阶段
        print("\n➡️  测试进入下一阶段...")
        await engine.proceed_to_next_stage()
        print(f"新阶段: {engine.table.stage}")
        
        if engine.table.community_cards:
            print(f"公共牌: {engine.table.community_cards}")
        
        # 测试摊牌
        print("\n🏆 测试摊牌...")
        await engine.proceed_to_showdown()
        print(f"摊牌阶段: {engine.table.stage}")
        
        # 测试新的一手牌
        print("\n🔄 测试新的一手牌...")
        engine.start_new_hand()
        print(f"新手牌ID: {engine.hand_id}")
        print(f"新阶段: {engine.table.stage}")
        
        print("\n✅ 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_poker_logic():
    """测试扑克逻辑"""
    print("\n🎴 测试扑克逻辑...")
    
    from app.utils.poker_logic import evaluator, create_deck, shuffle_deck
    
    # 测试创建牌堆
    deck = create_deck()
    print(f"✅ 创建牌堆: {len(deck)} 张牌")
    
    # 测试洗牌
    shuffled = shuffle_deck(deck)
    print(f"✅ 洗牌完成")
    
    # 测试牌型评估
    hole_cards = ["Ah", "Kd"]
    board = ["Ts", "Jc", "Qh", "2d", "3s"]
    
    score, hand_rank = evaluator.evaluate_hand(hole_cards, board)
    print(f"✅ 牌型评估: {hole_cards} + {board}")
    print(f"   分数: {score}, 牌型: {hand_rank}")
    
    # 测试手牌比较
    players_cards = [
        ["Ah", "Kd"],  # 玩家1
        ["Qs", "Js"],  # 玩家2
        ["9h", "9d"],  # 玩家3
    ]
    
    results = evaluator.compare_hands(players_cards, board)
    print(f"✅ 手牌比较结果:")
    for i, (player_idx, score, rank) in enumerate(results):
        print(f"   第{i+1}名: 玩家{player_idx+1}, 分数: {score}, 牌型: {rank}")
    
    return True

async def main():
    """主测试函数"""
    print("=" * 60)
    print("德州扑克游戏引擎测试套件")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # 运行测试
    tests = [
        ("基本游戏流程", test_basic_game),
        ("扑克逻辑", test_poker_logic),
    ]
    
    for test_name, test_func in tests:
        tests_total += 1
        print(f"\n📋 运行测试: {test_name}")
        try:
            if await test_func():
                tests_passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print(f"✅ 通过: {tests_passed}/{tests_total}")
    print(f"❌ 失败: {tests_total - tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))