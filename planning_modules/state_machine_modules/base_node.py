# state_machine_modules/base_node.py

import traceback
from typing import Optional, List, Dict, Any, Callable
import eventlet

from planning_modules.lending_ear_modules.uot_modules.item import Item
from planning_modules.state_machine_modules.context_info import ContextInfo
from neo4j_modules.care_kg_db import CareKgDB
from planning_modules.state_machine_modules.sort_utils import instruction_sort, instruction_sort_sync
from planning_modules.state_machine_modules.socket_constants import SocketEventType
from planning_modules.state_machine_modules.llm_enrichment import LLMEnrichment


class BaseNode:
    """
    完成版 BaseNode:
      - includes/followsによるサブツリー構築
      - go_detail 時は children をまとめて全部実行
      - [フォロワーノード] は保持するが、自動実行はしない
      - イベントフラグ方式で待機(go_next, go_detail, back_to_start)
      - 仮想ルート対応フラグ(is_virtual_root)は残してあるが必要に応じて使用
    """

    def __init__(
        self,
        name: str,
        basic_description: str,
        p_s: float,
        time_to_achieve: float = None,
        name_jp: str = None,
        kg_db: Optional[CareKgDB] = None,
        send_socket_func: Optional[Callable] = None,
        global_items: Optional[List[Item]] = None,
        is_debug: bool = False,
        context_info: Optional[Dict] = None,
        center_name: Optional[str] = None,
        parent_node: Optional['BaseNode'] = None,
        is_virtual_root: bool = False,
        japanese_name: Optional[str] = None
    ):
        # ノード基本情報
        self.name = name
        self.basic_description = basic_description
        self.p_s = p_s
        self.kg_db = kg_db
        self.send_socket = send_socket_func
        self.is_debug = is_debug
        self.global_items = global_items or []
        self.__debug_print__(f"[INIT] Initialized with {len(self.global_items)} global_items")  # デバッグ追加

        # コンテキスト情報 (global, local)
        self.context_info = ContextInfo.from_dict(context_info)

        # 親ノード
        self.parent = parent_node

        # 子ノード(=includes), フォロワーノード(=follows)
        self.children: List[BaseNode] = []
        self.followers: List[BaseNode] = []
        self.any_tree: Dict[str, Any] = {}

        # 中心ノード関係
        self.global_center_name = center_name
        self.is_center = (self.name == center_name) if center_name else False

        # 仮想ルート対応フラグ
        self.is_virtual_root = is_virtual_root

        # 状態 (Init, Explain, Done等)
        self.local_state = "Init"
        self.user_response: Optional[str] = None

        # 日本語名
        self.name_jp = name_jp

        # イベントフラグをeventletのEventに変更
        self.event_flags = {
            "go_next": eventlet.Event(),
            "go_detail": eventlet.Event(),
            "back_to_start": eventlet.Event(),
            "back_previous": eventlet.Event()
        }

        # 親コンテキストをローカルへ継承
        if self.parent and self.parent.context_info:
            self.__merge_contexts__(self.parent.context_info.to_dict())

        self.time_to_achieve = time_to_achieve #min
        self.name_jp = name_jp

        self.debug_print = self.__debug_print__  # debug_printのエイリアスを追加

        self.enriched_info: Optional[Dict[str, Any]] = None
        self._llm_enrichment = LLMEnrichment()

        self.__debug_print__(
            f"Initialized BaseNode => name={self.name}, center={self.is_center}, parent={(parent_node.name if parent_node else 'None')}, is_virtual={self.is_virtual_root}"
        )

    def __debug_print__(self, msg: str):
        """デバッグ情報の出力"""
        if self.is_debug:
            prefix = f"[DEBUG:BaseNode:{self.name}]"
            print(f"{prefix} {msg}")

    def __merge_contexts__(self, parent_context: Dict[str, Any]):
        """親ノードから local_context を引き継ぐ"""
        if not parent_context or 'local_context' not in parent_context:
            return
        try:
            local_ctx = parent_context['local_context']
            if isinstance(local_ctx, str):
                import json
                try:
                    local_ctx = json.loads(local_ctx)
                    if not isinstance(local_ctx, list):
                        local_ctx = [local_ctx]
                except json.JSONDecodeError:
                    local_ctx = [local_ctx]
            elif not isinstance(local_ctx, list):
                local_ctx = [local_ctx]

            if not isinstance(self.context_info.local_context, list):
                if self.context_info.local_context is None:
                    self.context_info.local_context = []
                else:
                    self.context_info.local_context = [self.context_info.local_context]

            self.context_info.local_context.extend(local_ctx)
        except Exception as e:
            self.__debug_print__(f"Error in merging contexts: {e}")
            self.context_info.local_context = []

    # ---------------------------------------------------------------------
    # includes/follows に基づくサブツリー構築
    # ---------------------------------------------------------------------
    async def construct_children_subtree(self, visited: Optional[set] = None):
        """
        includes + follows で子ノードを再帰生成
        semantic sortにより children に格納。
        """
        self.__debug_print__(f"Starting construct_children_subtree for {self.name}")
        
        if not self.kg_db:
            self.__debug_print__("No CareKgDB => cannot construct subtree.")
            return

        if visited is None:
            visited = set()
            self.__debug_print__("Initializing visited set")

        # ループ回避
        if self.name in visited:
            self.__debug_print__(f"{self.name} already visited => skip")
            return

        visited.add(self.name)
        self.__debug_print__(f"Added {self.name} to visited set. Current visited: {visited}")

        # ノード再生成の重複を避けるためのグローバルキャッシュ
        if not hasattr(self.__class__, '_processed_nodes'):
            self.__debug_print__("Initializing _processed_nodes cache")
            self.__class__._processed_nodes = {}
        else:
            self.__debug_print__(f"Current cached nodes: {list(self.__class__._processed_nodes.keys())}")

        try:
            # 現在のイベントループを取得
            loop = eventlet.get_event_loop()  # 変更点: get_event_loopの代わりにget_running_loop
            self.__debug_print__("Got event loop successfully")
            
            # 1) includes
            self.__debug_print__("Fetching children from kg_db...")
            includes_names = await self.kg_db.get_children(self.name)
            self.__debug_print__(f"{self.name} includes => {includes_names}")
            
            if not includes_names:
                self.__debug_print__(f"{self.name}: no includes found")
                return

            # 2) follows (親->子のリストを adjacency_lists にまとめる)
            self.__debug_print__("Starting to fetch followers...")
            adjacency_lists: Dict[str, List[str]] = {}
            tasks = [self.kg_db.get_followers(nm) for nm in includes_names]
            
            # 同じループで実行するように修正
            self.__debug_print__("Gathering follower results...")
            results = await eventlet.gather(*tasks, loop=loop)  # 変更点: loopを明示的に指定
            
            for inc_name, flist in zip(includes_names, results):
                self.__debug_print__(f"[DEBUG] Processing followers for {inc_name}: {flist}")
                if flist:
                    # 同じ includes内 かつ 自己参照でないものを対象
                    flist_in = [
                        f for f in flist
                        if f in includes_names
                        and f not in visited
                        and f != inc_name
                    ]
                    self.__debug_print__(f"Filtered followers for {inc_name}: {flist_in}")
                    if flist_in:
                        # inc_name FOLLOWS flist_in なので flist_in -> inc_name にしたい
                        for parent_node in flist_in:
                            adjacency_lists.setdefault(parent_node, []).append(inc_name)
                            self.__debug_print__(f"Added edge: {parent_node} -> {inc_name}")

                        self.__debug_print__(f"{inc_name} follows => {flist_in}")

            # 3) 各ノードの description_map を準備 (LLMに渡すため)
            self.__debug_print__("Building description map...")
            description_map = {}
            for inc_nm in includes_names:
                desc = await self.kg_db.get_item_description_async(inc_nm)
                self.__debug_print__(f"[DEBUG] Description for {inc_nm}: {desc}")
                if desc:
                    description_map[inc_nm] = desc
                else:
                    description_map[inc_nm] = ""
                    self.__debug_print__(f"Warning: No description found for {inc_nm}")

            # 4) instruction_sortで最終順序を決定
            self.__debug_print__("Starting instruction sort...")
            sorted_names = await instruction_sort(
                includes=includes_names,
                adjacency_lists=adjacency_lists,
                description_map=description_map
            )
            
            self.__debug_print__(f"[{self.name}] final sorted children => {sorted_names}")

            # 5) ノードを順序通りに生成
            self.__debug_print__("Starting node creation...")
            all_nodes = {}
            for cname in sorted_names:
                self.__debug_print__(f"Processing node: {cname}")
                # ループ回避
                if cname in visited:
                    self.__debug_print__(f"[DEBUG] {cname} already visited => skipping")
                    continue

                # すでに生成済みなら再利用
                if cname in self.__class__._processed_nodes:
                    self.__debug_print__(f"[DEBUG] Using cached node for {cname}")
                    all_nodes[cname] = self.__class__._processed_nodes[cname]
                    continue

                # global_itemsの内容確認
                self.__debug_print__(f"[DEBUG] Available global_items: {[item.name for item in self.global_items]}")

                # 新規生成
                self.__debug_print__(f"Creating new node for {cname}...")
                cnode = await self.__create_node__(cname)
                if cnode:
                    self.__debug_print__(f"[DEBUG] Successfully created node for {cname}")
                    all_nodes[cname] = cnode
                    self.__class__._processed_nodes[cname] = cnode
                    self.__debug_print__(f"Starting recursive construction for {cname}")
                    await cnode.construct_children_subtree(visited)
                else:
                    self.__debug_print__(f"[ERROR] Failed to create node for {cname}")

            # 6) self.children にセット
            self.__debug_print__("Setting final children list...")
            self.children = [all_nodes[n] for n in sorted_names if n in all_nodes]
            self.any_tree = {
                "sorted_includes": sorted_names,
                "follows_graph": adjacency_lists
            }

            self.__debug_print__(f"{self.name} => children = {[c.name for c in self.children]}")

        except Exception as e:
            self.__debug_print__(f"Error in construct_children_subtree: {e}")
            self.__debug_print__(traceback.format_exc())

    async def __create_node__(self, node_name: str) -> Optional['BaseNode']:
        """
        includes 先のノード名から BaseNode を作成するヘルパー
        """
        self.__debug_print__(f"Starting __create_node__ for {node_name}")
        
        if not self.kg_db:
            self.__debug_print__("No kg_db available")
            return None
        try:
            self.__debug_print__(f"[CREATE_NODE] Starting creation of {node_name} with {len(self.global_items)} global_items")
            
            # 全ての情報を取得
            info = await self.kg_db.get_item_full_info(node_name)
            if not info:
                self.__debug_print__(f"No info found for {node_name}")
                return None

            # LLM拡充を非同期で開始
            await self._llm_enrichment.enrich_node_info(
                node_name=info['name'],
                description=info['description']
            )
            
            # 新しいItemを作成（全ての情報を渡す）
            it = Item(
                name=info['name'],
                description=info['description'],
                p_s=0,
                time_to_achieve=info['time_to_achieve'],
                name_jp=info['name_jp']
            )
            if it not in self.global_items:
                self.global_items.append(it)
                self.__debug_print__(f"Added new Item {node_name} to global_items")

            self.__debug_print__(f"Creating BaseNode from item {node_name}")
            node = await BaseNode.create_from_item(
                item=it,
                kg_db=self.kg_db,
                send_socket_func=self.send_socket,
                global_items=self.global_items,
                context_info={},
                center_name=self.global_center_name,
                is_debug=self.is_debug,
                parent_node=self,
                is_virtual_root=self.is_virtual_root
            )
            if node:
                self.__debug_print__(f"Successfully created child node => {node.name}, parent={self.name}")

            # 非同期で拡充情報を確認
            node.enriched_info = self._llm_enrichment.get_enriched_info(node_name)
            
            return node
        except Exception as e:
            self.__debug_print__(f"Error in __create_node__: {str(e)}")
            self.__debug_print__(traceback.format_exc())
            return None
    #  ステートマシン
    # ---------------------------------------------------------------------
    async def run(self, center_target: Optional[str] = None):
        """
        ノードの実行開始
        """
        if center_target and self._is_top_node():
            path = self._find_path_to(center_target)
            if path is None:
                self.__debug_print__(f"No path to {center_target} from top node={self.name}")
                await self._standard_run()
                return
            await self.auto_run_to_center(path)
        else:
            await self._standard_run()

    def _is_top_node(self) -> bool:
        """parent が None ならトップノード扱い, ただしフォロワーノード実行はしない"""
        if self.parent is None:
            return not self.is_virtual_root  # 仮想ルートはtopではない or top扱いでもOK
        return False

    def _find_path_to(self, target_name: str) -> Optional[List['BaseNode']]:
        """
        DFS で target_name へのパスを探す (children + followers + 親)
        """
        visited = set()
        path: List[BaseNode] = []

        def dfs(node: 'BaseNode') -> bool:
            if node.name in visited:
                return False
            visited.add(node.name)
            path.append(node)
            if node.name == target_name:
                return True

            for c in node.children:
                if dfs(c):
                    return True
            for f in node.followers:
                if dfs(f):
                    return True
            if node.parent and dfs(node.parent):
                return True

            path.pop()
            return False

        if dfs(self):
            return path
        return None

    async def auto_run_to_center(self, path: List['BaseNode']):
        """[topNode, ..., centerNode] path を go_detail / go_next で擬似的に降りる"""
        if not path:
            return
        if len(path) == 1:
            await path[0]._standard_run()
            return

        for i in range(len(path) - 1):
            cur = path[i]
            nxt = path[i + 1]
            if nxt in cur.children:
                await self._simulate_event(cur, "go_detail")
            elif nxt in cur.followers:
                await self._simulate_event(cur, "go_next")
            else:
                self.__debug_print__(f"Cannot auto descend from {cur.name} -> {nxt.name}")
                return

        await path[-1]._standard_run()

    async def _simulate_event(self, node: 'BaseNode', event_name: str):
        """擬似的に event_name を発火 (go_detail, go_next等)"""
        self.__debug_print__(f"Simulate event={event_name} on {node.name}")
        if node.local_state == "Done":
            return
        node.set_event_flag(event_name)
        eventlet.sleep(0.05)

    def wait_for_event(self) -> str:
        """イベント待機（優先順位付き）"""
        while True:
            # eventletのEventを使用
            if self.event_flags["back_to_start"].ready():
                self.event_flags["back_to_start"].reset()
                return "back_to_start"
            elif self.event_flags["back_previous"].ready():
                self.event_flags["back_previous"].reset()
                return "back_previous"
            elif self.event_flags["go_detail"].ready() and self.children:
                self.event_flags["go_detail"].reset()
                return "go_detail"
            elif self.event_flags["go_next"].ready():
                self.event_flags["go_next"].reset()
                return "go_next"
            eventlet.sleep(0.1)  # CPU使用率を抑える

    def set_event_flag(self, event_name: str):
        """イベントフラグをセット"""
        if event_name not in self.event_flags:
            self.__debug_print__(f"[WARN] Unknown event_name => {event_name}")
            return
        self.__debug_print__(f"set_event_flag => {event_name}")
        self.event_flags[event_name].send()  # eventletのEventはsendを使用

    def _standard_run(self):
        """標準的な実行フロー"""
        self.debug_print(f"Start _standard_run => {self.name}")
        self.send_socket("custom_ping", "5")
        
        self.send_socket("next_state_info", self._create_state_info())
        
        self.debug_print(f"Loop: local_state={self.local_state}")
        while True:
            event_name = self.wait_for_event()
            self.debug_print(f"Got event => {event_name}")

            if event_name == "back_to_start":
                return "reset"
            elif event_name == "back_previous":
                return "previous"
            elif event_name == "go_detail" and self.children:
                self.debug_print(f"[{self.name}] go_detail => run all children")
                for idx, child in enumerate(self.children):
                    self.debug_print(f"Detail run child={child.name}, index={idx}")
                    result = child._standard_run()
                    if result == "reset":
                        return "reset"
                    elif result == "previous":
                        if idx > 0:
                            idx = max(0, idx - 2)
                            continue
                        return "previous"
                self.send_socket("detail_finished", {})
                return "next"
            elif event_name == "go_next":
                if not self._create_state_info().get("has_next", True):
                    self.send_socket("finish_instruction", {})
                return "next"

    def _create_state_info(self, **additional_flags) -> Dict[str, Any]:
        """共通のstate_info生成ロジック"""
        # 基本情報を構築
        has_detail = len(self.children) > 0
        is_last_top_node = (
            self.parent and 
            self.parent.is_virtual_root and 
            self.parent.children and 
            self.parent.children[-1] == self
        )
        has_next = not is_last_top_node

        # 基本のstate_info
        state_info = {
            "current_state": self.name,
            "description": self.basic_description,
            "title": self.name if not self.name_jp else self.name_jp,
            "call_to_action": "",
            "detail_instruction": "",
            "has_detail": has_detail,
            "has_next": has_next
        }

        # LLMによる拡充情報を取得
        enriched_info = self.get_enriched_info()
        if enriched_info:
            # 拡充情報で更新（必要最小限の情報のみ）
            state_info.update({
                "detail_instruction": enriched_info.get("detail_instruction", ""),
                "call_to_action": enriched_info.get("call_to_action", ""),
                "title": enriched_info.get("jp_title", state_info["title"])
            })
        else:
            # まだ拡充情報がない場合は非同期で取得を開始
            eventlet.spawn(
                self._llm_enrichment.enrich_node_info,
                self.name,
                self.basic_description,
                state_info
            )

        # 追加のフラグを適用
        state_info.update(additional_flags)
        return state_info

            
    @classmethod
    async def create_from_item(
        cls,
        item: Item,
        kg_db: CareKgDB,
        send_socket_func: Optional[Callable],
        global_items: List[Item],
        context_info: Dict,
        center_name: str,
        is_debug: bool = False,
        parent_node: Optional['BaseNode'] = None,
        is_virtual_root: bool = False
    ) -> Optional['BaseNode']:
        """
        Item から BaseNode を生成し、子ノードを再帰構築
        """
        if not item or not item.name or not item.description:
            if is_debug:
                print(f"[create_from_item] Invalid item: {item}")
            return None

        # デバッグ追加
        if is_debug:
            print(f"[create_from_item] Creating node {item.name} with {len(global_items or [])} global_items")

        node = cls(
            name=item.name,
            basic_description=item.description,
            p_s=item.p_s,
            time_to_achieve=item.time_to_achieve,
            name_jp=item.name_jp,
            kg_db=kg_db,
            send_socket_func=send_socket_func,
            global_items=global_items,
            is_debug=is_debug,
            context_info=context_info,
            center_name=center_name,
            parent_node=parent_node,
            is_virtual_root=is_virtual_root
        )

        # デバッグ追加
        if is_debug:
            print(f"[create_from_item] After node creation: {node.name} has {len(node.global_items)} global_items")

        if is_debug:
            p = parent_node.name if parent_node else "None"
            print(f"[create_from_item] => node={node.name}, parent={p}, virtual={is_virtual_root}")

        # 下位ノードの構築
        await node.construct_children_subtree()
        return node

    # ---------------------------------------------------------------------
    # (A) 文字ベースでツリーを表示 (followersは無視)
    # ---------------------------------------------------------------------
    def debug_print_tree(self, indent: int = 0):
        """再帰的に子ノードをたどってツリーを表示 (標準出力用)"""
        prefix = "  " * indent
        label_virtual = " (VROOT)" if self.is_virtual_root else ""
        print(f"{prefix}- {self.name}{label_virtual}")

        # followersを無視して、childrenのみ再帰表示
        for c in self.children:
            c.debug_print_tree(indent + 1)

    # ---------------------------------------------------------------------
    # (B) Graphvizでツリーを可視化 (PNGなど)
    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # Graphviz描画 (b階層ごとに枠線色を変え、fillは白、エッジラベルにinclude/follow)
    # ---------------------------------------------------------------------
    def visualize_graph(self):
        """
        1. __VROOT__ は描画スキップ（その子をトップ階層）
        2. (START)/(END) とトップノードを同じrankに
        3. BFSで node->depth
        4. 同depthを rank="same" に
        5. ノードは円形固定サイズ、階層ごとに枠線色 + 半透明で塗る
        6. 子が複数 => (a->b: start, b->c: next, c->d: next, d->a: end)
        """

        import graphviz
        from collections import deque

        # -----------------------------
        # 1) __VROOT__ スキップしてトップノード決定
        # -----------------------------
        if self.name == "__VROOT__":
            real_tops = self.children
        else:
            real_tops = [self]

        # -----------------------------
        # 2) BFSで (node->depth)
        # -----------------------------
        depth_map = {}
        visited = set()
        queue = deque()
        for top_node in real_tops:
            queue.append((top_node, 0))

        all_nodes = []
        while queue:
            node, d = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            depth_map[node] = d
            all_nodes.append(node)

            # 子 & followers を深さ+1
            for c in node.children:
                if c not in visited:
                    queue.append((c, d + 1))
            for f in node.followers:
                if f not in visited:
                    queue.append((f, d + 1))

        if not all_nodes:
            return graphviz.Digraph("empty")

        # -----------------------------
        # 3) Graphviz初期設定
        # -----------------------------
        dot = graphviz.Digraph("final_graph")
        dot.attr("graph", rankdir="TB", ranksep="0.5", nodesep="0.5")
        # ノードの大きさは変えず、円形固定サイズ
        dot.attr("node",
                shape="circle",
                fixedsize="true",
                width="2.5",
                height="2",
                style="filled",       # 塗りつぶし
                fontname="MS Gothic",
                fontweight="bold",
                fontsize="15")    # フォントを太字に設定
        dot.attr("edge", fontname="MS Gothic")

        # (START)/(END)は白背景・黒枠で固定
        start_node = "(START)"
        end_node   = "(END)"
        dot.node(start_node, label="(START)", color="black", fillcolor="white", penwidth="2")
        dot.node(end_node,   label="(END)",   color="black", fillcolor="white", penwidth="2")

        # depthごとに仕分け
        depth2nodes = {}
        for nd, d in depth_map.items():
            depth2nodes.setdefault(d, []).append(nd)

        min_depth = min(depth2nodes.keys())
        max_depth = max(depth2nodes.keys())

        # 半透明用の色リスト (下記は例: #RRGGBB + 80 (hexで約50%透明))
        layer_colors = [
            "#ff000030", "#ff800030", "#ffff0030", "#80ff0030", "#00ff0030",
            "#00ff8030", "#00ffff30", "#0080ff30", "#0000ff30", "#8000ff30",
            "#ff00ff30", "#ff008030"
        ]

        colors = [
            "#ff0000", "#ff8000", "#ffff00", "#80ff00", "#00ff00",
            "#00ff80", "#00ffff", "#0080ff", "#0000ff", "#8000ff",
            "#ff00ff", "#ff0080"
        ]

        # -----------------------------
        # 4) 同じdepthを rank="same" で横並び
        # -----------------------------
        for d, nodes_d in depth2nodes.items():
            sub_name = f"depth_{d}"
            with dot.subgraph(name=sub_name) as sub:
                sub.attr(rank="same")
                cidx = d % len(layer_colors)
                # RGBA形式
                fillcol = layer_colors[cidx]
                edgecol = colors[cidx]

                for n in nodes_d:
                    # 枠線色は同色? or 黒? => 好みに応じて
                    # ここでは枠線=黒, 内部半透明 fillcolor
                    sub.node(
                        n.name,
                        label=f"{n.name}\n({n.local_state})",
                        color=edgecol,      # 枠線の色
                        fillcolor=fillcol,  # 半透明
                        penwidth="5"
                    )

        # (START)&(END) もトップ階層に rank="same" で配置（色は白固定）
        with dot.subgraph(name="rank_startend") as sub:
            sub.attr(rank="same")
            sub.node(start_node)  # 既に設定済みの白背景・黒枠を使用
            sub.node(end_node)    # 既に設定済みの白背景・黒枠を使用

        # -----------------------------
        # 5) (START)->top, top->(END) constraint="false"
        # -----------------------------
        top_depth_nodes = depth2nodes[min_depth]
        visited_edges = set()
        for tnode in top_depth_nodes:
            if ("(START)", tnode.name) not in visited_edges:
                dot.edge("(START)", tnode.name, label="start", constraint="false", penwidth="5")
                visited_edges.add(("(START)", tnode.name))
            if (tnode.name, "(END)") not in visited_edges:
                dot.edge(tnode.name, "(END)", label="end", constraint="false", penwidth="5")
                visited_edges.add((tnode.name, "(END)"))

        # -----------------------------
        # 6) 子ノード a.child=[b,c,d] => a->b(start), b->c(next), c->d(next), d->a(end)
        # -----------------------------
        for node in all_nodes:
            ch = node.children
            if len(ch) > 0:
                e_start = (node.name, ch[0].name)
                if e_start not in visited_edges:
                    dot.edge(node.name, ch[0].name, label="detail", penwidth="5", color="#cccccc")
                    visited_edges.add(e_start)

                for i in range(len(ch) - 1):
                    e_mid = (ch[i].name, ch[i+1].name)
                    if e_mid not in visited_edges:
                        dot.edge(ch[i].name, ch[i+1].name, label="next", penwidth="5", color="black")
                        visited_edges.add(e_mid)

                e_end = (ch[-1].name, node.name)
                if e_end not in visited_edges:
                    dot.edge(ch[-1].name, node.name, label="back", penwidth="5", color="#cccccc")
                    visited_edges.add(e_end)

        return dot

    @classmethod
    def create_virtual_root(cls) -> 'BaseNode':
        """仮想ルートノードを作成"""
        return cls(
            name="VROOT",
            basic_description="Virtual Root Node",
            p_s=1.0,
            is_virtual_root=True,
            is_debug=True
        )

    def add_child(self, child: 'BaseNode'):
        """子ノードを追加"""
        if child not in self.children:
            self.children.append(child)
            child.parent = self

    @classmethod
    def create_from_item_sync(cls, item_name: str, kg_db: CareKgDB, send_socket, is_debug: bool = False) -> 'BaseNode':
        """アイテムからノードを作成する同期バージョン"""
        try:
            # アイテム情報を取得（既存の同期メソッドを使用）
            item_info = kg_db.get_item_full_info(item_name)  # _syncを付けない
            if not item_info:
                print(f"[BaseNode] No info for item={item_name}")
                return None

            # ノードを作成
            node = cls(
                name=item_name,
                basic_description=item_info.get('description', ''),
                p_s=1.0,
                time_to_achieve=item_info.get('time_to_achieve'),
                name_jp=item_info.get('name_jp'),
                kg_db=kg_db,
                send_socket_func=send_socket,
                is_debug=is_debug,
                japanese_name=item_info.get('name_jp')
            )

            # 子ノードを構築
            node.construct_children_subtree_sync()
            return node

        except Exception as e:
            print(f"Error in create_from_item_sync: {e}")
            traceback.print_exc()
            return None

    def construct_children_subtree_sync(self):
        """子ノードのサブツリーを構築する同期バージョン"""
        if not self.kg_db:
            return

        try:
            # includesを取得
            includes_names = self.kg_db.get_children_sync(self.name)
            if not includes_names:
                return

            # followsを取得
            adjacency_lists = {}
            for inc_name in includes_names:
                flist = self.kg_db.get_followers_sync(inc_name)
                if flist:
                    flist_in = [f for f in flist if f in includes_names and f != inc_name]
                    if flist_in:
                        adjacency_lists[inc_name] = flist_in

            # descriptionを取得
            description_map = {}
            for inc_name in includes_names:
                desc = self.kg_db.get_item_description_sync(inc_name)
                description_map[inc_name] = desc or ""

            # トポロジカルソート
            sorted_names = instruction_sort_sync(includes_names, adjacency_lists, description_map)

            # ノードを作成
            for name in sorted_names:
                child = BaseNode.create_from_item_sync(
                    item_name=name,
                    kg_db=self.kg_db,
                    send_socket=self.send_socket,
                    is_debug=self.is_debug
                )
                if child:
                    self.add_child(child)

        except Exception as e:
            print(f"Error in construct_children_subtree_sync: {e}")
            traceback.print_exc()

    def get_enriched_info(self) -> Optional[Dict[str, Any]]:
        """
        非ブロッキングで拡充情報を取得
        """
        if self.enriched_info is None:
            self.enriched_info = self._llm_enrichment.get_enriched_info(self.name)
        return self.enriched_info
