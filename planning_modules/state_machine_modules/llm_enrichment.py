from typing import Optional, Dict, Any
import eventlet
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableSequence
from pydantic import BaseModel, Field
import json
import os
from dotenv import load_dotenv

load_dotenv()

class _NodeEnrichmentResult(BaseModel):
    """認知症の方に配慮した、ノード情報の拡充結果を表すPydanticモデル"""
    detail_instruction: str = Field(
        ..., 
        description="詳細モードに入る前の説明。なぜ詳しく見る必要があるのか、どんな内容が含まれているのかを、認知症の方にも分かりやすく説明"
    )
    call_to_action: str = Field(
        ..., 
        description="次のアクションを促す短い文。具体的で分かりやすい言葉を使用し、行動を明確に示す"
    )
    jp_title: str = Field(
        ..., 
        description="日本語での分かりやすい見出し。専門用語を避け、日常的な表現を使用"
    )

def get_enrichment_chain():
    """意味的な順序付けのためのLLMチェーン"""
    load_dotenv()
    print("[DEBUG] Starting get_enrichment_chain...")
    model_name = os.getenv("OPENAI_MIDDLE_MODEL", "gpt-4o")
    print(f"[DEBUG] Using model: {model_name}")
        
    llm = ChatOpenAI(
        model=model_name,
        api_key=os.getenv("OPENAI_API_KEY")
    ).bind(
        response_format={"type": "json_object"}
    )

    print("[DEBUG] Created ChatOpenAI instance")
    
    # 出力パーサー
    output_parser = JsonOutputParser(pydantic_object=_NodeEnrichmentResult)
    
    # プロンプトテンプレート
    prompt = PromptTemplate.from_template(
        template=PROMPT,
        partial_variables={"format_instructions": output_parser.get_format_instructions()}
    )
    
    chain = prompt | llm | output_parser
    print("[DEBUG] Created chain")
    
    return chain

class LLMEnrichment:
    def __init__(self):
        self.chain = get_enrichment_chain()
        self._enrichment_cache = {}
        
    def enrich_node_info(
        self,
        node_name: str,
        description: str,
        state_info: Optional[Dict] = None
    ) -> None:
        """ノード情報を拡充し、キャッシュに保存（eventlet対応）"""
        try:
            input_data = {
                "node_name": node_name,
                "description": description,
            }
            
            # eventletを使用して非同期実行
            future = eventlet.spawn(self._call_chain, input_data)
            self._enrichment_cache[node_name] = future
            
        except Exception as e:
            print(f"Error in enrich_node_info: {e}")
    
    def _call_chain(self, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """チェーンを実行する同期メソッド"""
        try:
            result = self.chain.invoke(input_data)
            return result.dict() if hasattr(result, 'dict') else result
        except Exception as e:
            print(f"Error in _call_chain: {e}")
            return None
            
    def get_enriched_info(self, node_name: str) -> Optional[Dict[str, Any]]:
        """キャッシュから拡充情報を取得（非ブロッキング）"""
        future = self._enrichment_cache.get(node_name)
        if future and future.ready():
            try:
                return future.wait()
            except Exception:
                return None
        return None

PROMPT = """
認知症の方をサポートするための情報を拡充します。以下の情報を元に、分かりやすく具体的な説明を生成してください。

###基本情報
ノード名: {node_name}
基本説明: {description}

###出力フォーマット
{format_instructions}

###注意点:
1. detail_instruction について:
   - 認知症の方にも理解しやすい、具体的で明確な説明を心がけてください
   - 専門用語は避け、日常的な表現を使用してください
   - 必要な情報は省略せず、段階的に説明してください
   - 長すぎず、かつ必要な情報は確実に含めてください

2. call_to_action について:
   - 具体的で明確な次のステップを示してください
   - 「〜しましょう」「〜してみましょう」など、優しい口調で表現してください
   - 一つのアクションに絞って、シンプルに表現してください

3. jp_title について:
   - 短く分かりやすい日本語のタイトルをつけてください
   - 専門用語は避け、日常的な表現を使用してください
   - 必要に応じて、具体的な動作や目的を含めてください
"""