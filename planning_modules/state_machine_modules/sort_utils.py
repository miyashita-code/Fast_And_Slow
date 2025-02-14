# sorting_utils.py

import asyncio
from typing import List, Dict, Tuple
from collections import deque
import json
import traceback
import os
from dotenv import load_dotenv

# LangChain系 (あなたが提示したスタイル)
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables.base import RunnableSequence
# モデル例: ChatOpenAI

from langchain_openai import ChatOpenAI

# Pydantic
from pydantic import BaseModel, Field



class _SemanticSortResult(BaseModel):
    """
    Pydantic model for parsing LLM responses that deeply understands human behavioral sequences.
    
    The model analyzes and predicts natural task ordering by considering:
    """
    thoughts: str = Field(..., description="Detailed chain-of-thought reasoning that analyzes the deep behavioral patterns, cognitive load sequences, and natural workflow rhythms to justify the ordering decisions. Should consider both explicit technical dependencies and implicit human behavioral patterns.")
    sorted_list: List[str] = Field(..., description="Optimized sequence of nodes that respects both technical constraints and natural human task execution patterns, considering cognitive load, context switches, and physical/environmental flows to create maximally intuitive and efficient orderings. 個々には元のlistに含まれていたものをすべてもれなくかつ勝手に増やすことなく正確に含める必要があります.")
    

semantic_sort_prompt = """
あなたは与えられたノード群を「依存関係を破らない」前提で、可能な範囲で最も自然な順序に並べ替えてください。
最終的に以下のJSON形式のみを出力してください。

ノード一覧:
{item_list}

依存関係:
{constraints}

{format_instructions}

# 注意:
- JSON以外の文字は一切出力しない
- sorted_list はノード名の配列
- thoughts は思考過程(日本語/英語どちらでもOK)
- 依存関係に矛盾しない範囲で自由に並び替える
- 衝突がある場合や不可能な場合は思考過程に書く
"""

# 出力パーサ
output_parser_semantic_sort = JsonOutputParser(pydantic_object=_SemanticSortResult)

# PromptTemplate
prompt_template_semantic_sort = PromptTemplate.from_template(
    template=semantic_sort_prompt,
    partial_variables={
        "format_instructions": output_parser_semantic_sort.get_format_instructions()
    }
)


def get_semantic_sort_chain():
    """意味的な順序付けのためのLLMチェーン"""
    load_dotenv()
    print("[DEBUG] Starting get_semantic_sort_chain...")
    model_name = os.getenv("OPENAI_LIGHT_MODEL", "chatgpt-4o-latest")
    print(f"[DEBUG] Using model: {model_name}")
        
    llm = ChatOpenAI(
        model=model_name,
        api_key=os.getenv("OPENAI_API_KEY")
    ).bind(
        response_format={"type": "json_object"}
    )

    print("[DEBUG] Created ChatOpenAI instance")
    

    chain = prompt_template_semantic_sort | llm | output_parser_semantic_sort
    print("[DEBUG] Created chain")
    
    return chain



async def run_semantic_sort(
    sorted_names: List[str],
    adjacency_lists: Dict[str, List[str]],
    description_map: Dict[str, str]
) -> List[str]:
    """
    1. constraints (child -> [parents]) 形式に再構築
    2. item_list としてノード名 + description を文字列化
    3. chain.ainvoke({...}) でLLM呼び出し
    4. 返ってきた Pydanticモデルの sorted_list を返す (失敗時は [])
    """
    try:
        print("[DEBUG] Starting semantic sort...")
        
        # 1) 依存関係 parent -> [children] にする (方向を反転)
        rev_map = {}
        for parent, children in adjacency_lists.items():
            for child in children:
                rev_map.setdefault(parent, []).append(child)

        constraints_str = json.dumps(rev_map, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Constraints: {constraints_str}")

        # 2) item_list 作成
        items_str = ""
        for nm in sorted_names:
            desc = description_map.get(nm, "")
            items_str += f"- name: {nm}, desc: {desc}\n"
        print(f"[DEBUG] Items list: {items_str}")

        # チェーン取得
        print("[DEBUG] Getting semantic sort chain...")
        chain = get_semantic_sort_chain()
        if not chain:
            print("[ERROR] Failed to get semantic sort chain")
            return []

        # asyncでainvoke
        print("[DEBUG] Invoking chain with inputs...")

        result_obj = chain.invoke({
            "item_list": items_str,
            "constraints": constraints_str,
        })
        print(f"[DEBUG] Chain result type: {type(result_obj)}")
        print(f"[DEBUG] Chain result: {result_obj}")

        # dictの場合の処理を追加
        if isinstance(result_obj, dict) and "sorted_list" in result_obj:
            print(f"[DEBUG] Returning sorted list from dict: {result_obj['sorted_list']}")
            return result_obj["sorted_list"]
        elif isinstance(result_obj, _SemanticSortResult):
            print(f"[DEBUG] Returning sorted list from model: {result_obj.sorted_list}")
            return result_obj.sorted_list
        else:
            print(f"[ERROR] Unexpected result type: {type(result_obj)}")
            return []

    except Exception as e:
        print(f"[ERROR] Semantic sort failed: {e}")
        print("[ERROR] Full traceback:")
        traceback.print_exc()
        return []


def topo_sort_with_parallel_check(
    includes: List[str],
    adjacency_lists: Dict[str, List[str]]
) -> Tuple[List[str], bool]:
    """
    follows に基づくトポロジカルソート
    (sorted_list, has_parallel) を返す
    has_parallel: queueに複数ノードが同時に入ったらTrue
    
    A-(follows)->B の時、[A->B]という順序制約とする
    """
    in_degree = {nm: 0 for nm in includes}
    graph = {nm: [] for nm in includes}

    # follows関係をそのままの向きで制約に変換
    for src, follows in adjacency_lists.items():
        for dst in follows:
            if src in graph and dst in graph:
                # A follows B => A->B の順序制約
                graph[src].append(dst)
                in_degree[dst] += 1

    queue = deque([n for n in includes if in_degree[n] == 0])
    result = []
    has_parallel = False

    while queue:
        if len(queue) > 1:
            has_parallel = True
        cur = queue.popleft()
        result.append(cur)
        for nxt in graph[cur]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    leftover = set(includes) - set(result)
    if leftover:
        print(f"[WARN] leftover => {leftover}")
        result.extend(list(leftover))

    return result, has_parallel


async def instruction_sort(
    includes: List[str],
    adjacency_lists: Dict[str, List[str]],
    description_map: Dict[str, str]
) -> List[str]:
    """
    - トポロジカルソートで最低限の依存関係を確定
    - 並列があれば run_semantic_sort
    - 失敗時はフォールバック (topo結果)
    """
    topo_result, has_parallel = topo_sort_with_parallel_check(includes, adjacency_lists)
    print(f"[INFO] topo_result={topo_result}, has_parallel={has_parallel}")

    if not has_parallel:
        # 並列が無い => そのまま返す
        print("[INFO] No parallel => skip semantic sort.")
        return topo_result

    # 並列がある => LLMで並び替え
    new_order = await run_semantic_sort(topo_result, adjacency_lists, description_map)
    if not new_order:
        print("[WARN] LLM reorder failed => fallback to topo_result.")
        return topo_result
    else:
        print(f"[INFO] LLM reorder success => {new_order}")
        return new_order


def instruction_sort_sync(
    includes: List[str],
    adjacency_lists: Dict[str, List[str]],
    description_map: Dict[str, str]
) -> List[str]:
    """
    同期バージョンのinstruction_sort
    - トポロジカルソートで最低限の依存関係を確定
    - 並列があれば run_semantic_sort
    - 失敗時はフォールバック (topo結果)
    """
    topo_result, has_parallel = topo_sort_with_parallel_check(includes, adjacency_lists)
    print(f"[INFO] topo_result={topo_result}, has_parallel={has_parallel}")

    if not has_parallel:
        # 並列が無い => そのまま返す
        print("[INFO] No parallel => skip semantic sort.")
        return topo_result

    # 並列がある場合も、とりあえずトポロジカルソートの結果を返す
    # LLMによる並び替えは非同期版のみで実装
    print("[INFO] Has parallel but sync version => use topo_result")
    return topo_result

