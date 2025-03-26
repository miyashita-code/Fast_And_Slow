# planning_modules/state_machine_modules/instruction_graph.py

from typing import List, Optional
import traceback
import eventlet

from neo4j_modules.care_kg_db import CareKgDB
from planning_modules.lending_ear_modules.uot_modules.item import Item
from planning_modules.state_machine_modules.base_node import BaseNode

class InstructionGraph:
    """
    複数トップノードを取得し、さらにトップノード間で follows 関係があればトポロジカルソート。
    そのうえで仮想ルート(VROOT)にまとめる。
    run()時には for top_node in sorted_top_nodes => もし center_node があれば center_target=..., なければ 普通に run()
    """

    def __init__(
        self,
        kg_db: CareKgDB,
        send_socket=None,  # send_socket関数を直接受け取る
        global_items: Optional[List[Item]] = None,
        is_debug: bool = False
    ):
        self.kg_db = kg_db
        self.is_debug = is_debug
        self.global_items = global_items or []
        self.send_socket = send_socket  # send_socket関数を保持

        # デバッグ追加
        self.debug_print(f"Initialized with {len(self.global_items)} global_items")
        if self.is_debug and self.global_items:
            self.debug_print(f"Global items names: {[item.name for item in self.global_items]}")

        self.virtual_root: Optional[BaseNode] = None
        self.top_nodes: List[BaseNode] = []
        self.center_node_name: Optional[str] = None

    def debug_print(self, msg: str):
        if self.is_debug:
            print(f"[InstructionGraph] {msg}")

    async def construct_graph(self, center_node_name):
        """
        1. get_all_top_nodes(): [top1, top2, ...]
        2. それら同士の follows を用いてトポロジカルソート
        3. base_node群を生成
        4. 仮想ルート(VROOT)を作り、children に並べる
        5. center_node_name を保持
        """
        self.debug_print(f"construct_graph: center_node_name={center_node_name}")
        
        # send_socketの確認
        print(f"##### >>> [DEBUG:InstructionGraph] send_socket is {'available' if self.send_socket else 'NOT available'}")
        
        # center_node_nameがNoneの場合のデフォルト処理
        if center_node_name is None:
            center_node_name = "prepare_for_toreliha"
        
        self.center_node_name = center_node_name
        self.debug_print(f"Starting construct_graph with {len(self.global_items)} global_items")

        try:
            # 1. すべてのトップノード名を取得
            top_names_all = await self.kg_db.get_all_top_nodes()
            self.debug_print(f"Found all top nodes: {top_names_all}")

            if center_node_name in top_names_all:
                top_names = [center_node_name]
            else:
                top_name = await self.kg_db.get_top_node(center_node_name)
                top_names = [top_name] if top_name else []
                self.debug_print(f"Got top node for {center_node_name}: {top_names}")

            if not top_names or top_names[0] is None:
                self.debug_print(f"No top_nodes found for center_node_name={center_node_name}")
                return
            
            # 2. トポロジカルソート(トップノード間でのfollows関係)
            #    まず follower情報を集める
            adjacency_lists = {}
            in_degree = {}
            for nm in top_names:
                in_degree[nm] = 0

            for nm in top_names:
                flist = await self.kg_db.get_followers(nm)
                # flist の中で top_namesにも入っているものを抽出
                flist_in = [x for x in flist if x in top_names and x != nm]
                if flist_in:
                    adjacency_lists[nm] = flist_in
                    for f in flist_in:
                        in_degree[f] += 1

            # トポロジカルソート
            sorted_top_names = self._topo_sort(top_names, adjacency_lists, in_degree)
            self.debug_print(f"Sorted top_nodes => {sorted_top_names}")

            # 3. base_node化
            top_nodes = []
            for nm in sorted_top_names:
                item_info = await self.kg_db.get_item_full_info(nm)
                if not item_info:
                    self.debug_print(f"No info for top_node={nm}, skip")
                    continue
                
                it = Item(
                    name=item_info['name'],
                    description=item_info['description'],
                    p_s=0,
                    time_to_achieve=item_info['time_to_achieve'],
                    name_jp=item_info['name_jp']
                )
                
                # global_itemsに追加
                if it not in self.global_items:
                    self.global_items.append(it)
                
                node = await BaseNode.create_from_item(
                    item=it,
                    kg_db=self.kg_db,
                    send_socket_func=self.send_socket,  # send_socket関数を直接渡す
                    global_items=self.global_items,
                    context_info={},
                    center_name=center_node_name,
                    is_debug=self.is_debug,
                    parent_node=None,
                    is_virtual_root=False
                )
                
                if node:
                    top_nodes.append(node)
                    self.debug_print(f"Successfully created node for {nm}")
                    print(f"##### >>> [DEBUG:InstructionGraph] Created node {node.name} with send_socket {'available' if node.send_socket else 'NOT available'}")
                else:
                    self.debug_print(f"Failed to create node for {nm}")

            self.top_nodes = top_nodes

            # 4. 仮想ルート作成
            vroot_item = Item(name="__VROOT__", description="multiple top node root", p_s=0)
            self.virtual_root = BaseNode(
                name=vroot_item.name,
                basic_description=vroot_item.description,
                p_s=vroot_item.p_s,
                kg_db=self.kg_db,
                send_socket_func=self.send_socket,  # send_socket関数を直接渡す
                global_items=self.global_items,
                is_debug=self.is_debug,
                context_info={},
                center_name=center_node_name,
                parent_node=None,
                is_virtual_root=True
            )
            self.virtual_root.children = self.top_nodes
            self.debug_print(f"virtual_root.children => {[n.name for n in self.top_nodes]}")

        except Exception as e:
            self.debug_print(f"Error in construct_graph: {e}")
            self.debug_print(traceback.format_exc())

    def _topo_sort(self, names: List[str], adjacency_lists: dict, in_degree: dict) -> List[str]:
        """
        シンプルなトップノード間のトポロジカルソート
        """
        from collections import deque
        queue = deque([n for n in names if in_degree[n] == 0])
        result = []
        while queue:
            cur = queue.popleft()
            result.append(cur)
            if cur in adjacency_lists:
                for nxt in adjacency_lists[cur]:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        queue.append(nxt)

        leftover = set(names) - set(result)
        if leftover:
            self.debug_print(f"[WARN] leftover top_nodes => {leftover}")
            # 末尾に並べる
            result.extend(list(leftover))
        return result

    async def run(self):
        """
        仮想ルートを実行せず、top_nodesをforで回す。
        - center_node_name が含まれるかを判定し、該当ノードは run(center_target=...) 
          そうでないノードは run() 普通に
        """
        if not self.virtual_root:
            self.debug_print("No virtual_root => nothing to run.")
            return

        if not self.top_nodes:
            self.debug_print("No top_nodes => nothing to run.")
            return

        self.debug_print("=== InstructionGraph run start (multiple top nodes) ===")

        for top_node in self.top_nodes:
            # center_node_name がこの top_node のサブツリーに存在するか確認
            if self.center_node_name and self.__find_node(top_node, self.center_node_name):
                self.debug_print(f"Top node {top_node.name} => has center_node => run with center_target={self.center_node_name}")
                result = await top_node.run(center_target=self.center_node_name)
                if result == "reset":
                    self.debug_print("Reset requested, propagating up")
                    return "reset"
            else:
                self.debug_print(f"Top node {top_node.name} => run normal (no center or not found).")
                result = await top_node.run()
                if result == "reset":
                    self.debug_print("Reset requested, propagating up")
                    return "reset"

        self.debug_print("=== InstructionGraph run end ===")

    def __find_node(self, current: BaseNode, target_name: str) -> Optional[BaseNode]:
        """DFSで target_name を探す"""
        if current.name == target_name:
            return current
        for c in current.children:
            res = self.__find_node(c, target_name)
            if res:
                return res
        for f in current.followers:
            res = self.__find_node(f, target_name)
            if res:
                return res
        return None

    def debug_print_tree(self):
        if self.virtual_root:
            self.debug_print("=== InstructionGraph debug_print_tree start ===")
            self.virtual_root.debug_print_tree()
            self.debug_print("=== InstructionGraph debug_print_tree end ===")
        else:
            self.debug_print("No virtual_root to show.")

    def visualize_graph(self):
        if self.virtual_root:
            dot = self.virtual_root.visualize_graph()
            dot.render('my_tree', format='png', cleanup=True)
        else:
            self.debug_print("No virtual_root to show.")

    async def send_message(self, message: str, title: Optional[str] = None):
        """メッセージ送信の統一インターフェース"""
        await self.socket_wrapper.send_instruction(message, is_lending_ear=False)

    def construct_graph_sync(self, center_node_name):
        """グラフ構築の同期バージョン"""
        try:
            # 仮想ルートの作成
            self.virtual_root = BaseNode.create_virtual_root()
            self.virtual_root.send_socket = self.send_socket
            self.center_node_name = center_node_name  # center_node_nameを保持
            
            # center_nodeがある場合はそれを作成
            if center_node_name:
                node = self._create_node_sync(center_node_name)
                if node:
                    node.is_center = True  # center_nodeフラグを設定
                    self.top_nodes = [node]
                    self.virtual_root.add_child(node)
                    print(f"##### >>> [DEBUG:InstructionGraph] Created center node {center_node_name}")
                    return True
            
            # デフォルトのトップノードを作成
            node = self._create_node_sync('prepare_for_toreliha')
            if node:
                self.top_nodes = [node]
                self.virtual_root.add_child(node)
                print("##### >>> [DEBUG:InstructionGraph] Created node prepare_for_toreliha")
                return True
            
        except Exception as e:
            print(f"Error constructing graph: {e}")
            traceback.print_exc()
            return False

    def _create_node_sync(self, node_name: str) -> Optional[BaseNode]:
        """ノード作成の同期バージョン"""
        try:
            node = BaseNode.create_from_item_sync(
                item_name=node_name,
                kg_db=self.kg_db,
                send_socket=self.send_socket,  # send_socket関数をそのまま渡す
                is_debug=self.is_debug
            )
            if node:
                node.send_socket = self.send_socket  # インスタンス変数としても設定
            return node
        except Exception as e:
            print(f"Error in _create_node_sync: {e}")
            traceback.print_exc()
            return None

    def run_sync(self):
        """グラフ実行の同期バージョン"""
        print("[InstructionGraph] === InstructionGraph run start (multiple top nodes) ===")
        
        if not self.virtual_root:
            print("[InstructionGraph] No virtual_root => nothing to run.")
            return

        if not self.top_nodes:
            print("[InstructionGraph] No top_nodes => nothing to run.")
            return

        try:
            for node in self.top_nodes:
                if node.is_center:
                    print(f"[InstructionGraph] Top node {node.name} => has center_node => run with center_target={node.name}")
                    result = node._standard_run()  # 同期バージョンを呼び出す
                    if result == "reset":
                        return "reset"
                else:
                    print(f"[InstructionGraph] Top node {node.name} => no center_node => standard run")
                    node._standard_run()  # 同期バージョンを呼び出す
                    
        except Exception as e:
            print(f"Error in graph run: {e}")
            traceback.print_exc()
            
        finally:
            print("[InstructionGraph] === InstructionGraph run end ===")
            eventlet.sleep(1)  # 次のループまで少し待つ

