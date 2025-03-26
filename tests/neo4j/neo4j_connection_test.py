import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, './')

from neo4j_modules.care_kg_db import CareKgDB

async def test_connection():
    print("Neo4j接続テストを開始します...")
    
    # 環境変数の読み込み
    load_dotenv()
    
    # 接続情報の表示（パスワードは表示しない）
    print(f"URI: {os.getenv('NEO4J_URI')}")
    print(f"Username: {os.getenv('NEO4J_USERNAME')}")
    
    try:
        # データベース接続
        db = CareKgDB(
            os.getenv("NEO4J_URI"),
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD")
        )
        
        # 簡単なクエリを実行
        print("\nテストクエリを実行します...")
        result = await db.get_item_description_async("デイサービス準備")
        print(f"クエリ結果: {result}")
        
        # 接続のクローズ
        await db.close()
        print("\n接続テスト成功！")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        import traceback
        print("\n詳細なエラー情報:")
        print(traceback.format_exc())

if __name__ == "__main__":
    import asyncio
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_connection()) 