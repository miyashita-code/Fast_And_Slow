import os
import json
import asyncio
import traceback
import sys
import eventlet
from neo4j import GraphDatabase  # AsyncGraphDatabaseではなく通常のドライバーを使用
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv

class CareKgDB:
    def __init__(self, uri, user, password, user_uuid=None):
        # URIのバリデーション
        if not uri.startswith(('neo4j://', 'neo4j+s://', 'bolt://', 'bolt+s://')):
            uri = f"neo4j+s://{uri}"
        
        self.debug_print(f"Connecting to Neo4j at: {uri}")
        
        # 同期版ドライバーを使用
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password)
        )
        self.user_uuid = user_uuid
        
        self.debug_print("Neo4j driver initialized successfully")

    def get_all_top_nodes(self):
        """トップノードを取得"""
        self.debug_print("Starting get_all_top_nodes")
        query = """
        MATCH (n:instance)
        WHERE NOT EXISTS((n)<-[:INCLUDES]-(:instance))
        RETURN n.name as name, n.description as description, 
               n.time_to_achieve as time_to_achieve, n.name_jp as name_jp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query)
                nodes = [record for record in result]
                self.debug_print(f"Found {len(nodes)} top nodes")
                return [node['name'] for node in nodes]  # 従来の戻り値を維持
        except Exception as e:
            self.debug_print(f"Error in get_all_top_nodes: {e}")
            traceback.print_exc()
            return []

    def close(self):
        """クローズ処理"""
        if self.driver:
            self.driver.close()

    def debug_print(self, msg: str):
        print(f"[CareKgDB] {msg}")

    def get_uot_nodes(self):
        query = """
        MATCH (n:instance)
        WHERE n:Trouble OR n:Activity OR n:Action OR n:Task OR n:Condition OR n:Mood
        RETURN n.name AS name, n.detail_description AS description
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [{"name": record["name"], "description": record["description"]} for record in result]
    
    def get_all(self):
        query = """
        MATCH (n)
        RETURN n
        """
        with self.driver.session() as session:
            result = session.run(query)
            print([record for record in result])

    def get_item_full_info(self, item_name: str) -> Optional[Dict[str, Any]]:
        """アイテムの全情報を取得（同期版）"""
        try:
            query = """
            MATCH (n:instance {name: $name})
            RETURN n.name as name, 
                   COALESCE(n.detail_description, n.description) as description,
                   n.time_to_achieve as time_to_achieve, 
                   n.name_jp as name_jp
            """
            with self.driver.session() as session:
                result = session.run(query, name=item_name)
                record = result.single()
                if record:
                    return {
                        'name': record['name'],
                        'description': record['description'] or "No description available",
                        'time_to_achieve': record['time_to_achieve'],
                        'name_jp': record['name_jp']
                    }
                self.debug_print(f"No record found for item: {item_name}")
                return None
        except Exception as e:
            self.debug_print(f"Error in get_item_full_info: {e}")
            traceback.print_exc()
            return None
        
    def get_item_time_to_achieve(self, item_name):
        query = """
        MATCH (n:instance)
        WHERE n.name = $item_name
        RETURN n.time_to_achieve AS time_to_achieve
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {"item_name": item_name})
                record = result.single()
                return record["time_to_achieve"] if record else None
        except Exception as e:
            self.debug_print(f"Error in get_item_time_to_achieve: {e}")
            self.debug_print(traceback.format_exc())
            return None
        
    def get_item_name_jp(self, item_name):
        query = """
        MATCH (n:instance)
        WHERE n.name = $item_name
        RETURN n.name_jp AS name_jp
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {"item_name": item_name})
                record = result.single()
                return record["name_jp"] if record else None
        except Exception as e:
            self.debug_print(f"Error in get_item_name_jp: {e}")
            self.debug_print(traceback.format_exc())
            return None
        
    def get_children(self, item_name):
        query = """
        MATCH (n:instance)
        WHERE n.name = $item_name
        MATCH (n)-[:INCLUDES]->(child)
        RETURN child.name AS child_name
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {"item_name": item_name})
                records = result.data()
                return [record["child_name"] for record in records] if records else []
        except Exception as e:
            self.debug_print(f"Error in get_children: {e}")
            self.debug_print(traceback.format_exc())
            return []

    def get_related_nodes(self, item_name):
        query = """
        MATCH (n:instance)
        WHERE n.name =~ $search_pattern
        MATCH (n)-[r1]->(m)
        OPTIONAL MATCH (m)-[r2]->(n)
        WITH n, m, 
             CASE WHEN r2 IS NOT NULL THEN [r1, r2] ELSE [r1] END AS relationships
        UNWIND relationships AS R
        OPTIONAL MATCH (m)-[gc:HAPPENS_AT|TAKES_PLACE_AT|PLACED_AT]->(context)
        WHERE type(R) ='USES_OBJECT' OR m:DailyEvent
        RETURN n.name AS source_name, 
               {type: type(R), direction: CASE WHEN startNode(R) = n THEN 'outgoing' ELSE 'incoming' END} AS relationship,
               m.name AS target_name, 
               m.detail_description AS target_description,
               labels(m) AS target_labels,
               CASE WHEN gc IS NOT NULL THEN
                 {type: type(gc), context_name: context.name, context_type: labels(context)[0]}
               ELSE null END AS global_context
        """
        search_pattern = f'(?i).*{item_name}.*'
        
        with self.driver.session() as session:
            result = session.run(query, {"search_pattern": search_pattern})
            records = result.data()
            
            global_context = {}
            local_context = []
            
            for record in records:
                context_info = {
                    'source_name': record['source_name'],
                    'relationship': record['relationship'],
                    'target_name': record['target_name'],
                    'target_description': record['target_description'],
                    'target_labels': record['target_labels']
                }
                
                if record['global_context']:
                    gc = record['global_context']
                    global_context[gc['type']] = {
                        'name': gc['context_name'],
                        'type': gc['context_type']
                    }
                
                if record['relationship']['type'] in self.ontology_info['relations']['local_context']:
                    local_context.append(context_info)
            
            # Convert global_context and local_context to JSON strings
            global_context_str = json.dumps(global_context, ensure_ascii=False, indent=2)
            local_context_str = json.dumps(local_context, ensure_ascii=False, indent=2)

            print(f"global_context: {global_context_str}")
            print(f"local_context: {local_context_str}")
            
            return {
                'global_context': global_context_str,
                'local_context': local_context_str
            }
        
    def get_followers(self, item_name):
        query = """
        MATCH (n:instance)-[:FOLLOWS]->(follower)
        WHERE n.name = $item_name
        RETURN follower.name AS follower_name
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {"item_name": item_name})
                records = result.data()
                return [record["follower_name"] for record in records] if records else []
        except Exception as e:
            self.debug_print(f"Error in get_followers: {e}")
            self.debug_print(traceback.format_exc())
            return []
        
    def get_top_node(self, item_name):
        query = """
        MATCH (center:instance {name: $item_name})
        MATCH path = (top:instance)-[:INCLUDES*]->(center)
        WHERE NOT (top)<-[:INCLUDES]-()
        RETURN top.name as top_name
        LIMIT 1
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {"item_name": item_name})
                record = result.single()
                return record["top_name"] if record else None
        except Exception as e:
            self.debug_print(f"Error in get_top_node: {e}")
            self.debug_print(traceback.format_exc())
            return None

    def get_ontology_info(self):
        return (
            {
                "relations": {
                    "global_context": [
                        "happensAt",
                        "takesPlaceAt",
                        "placedAt",
                    ],
                    "local_context": [
                        "includes",
                        "affects",
                        "usesMethod",
                        "supports",
                        "follows",
                        "causesTrouble",
                        "hasPrompting",
                        "usesObject",
                        "performs",
                        "experiencesMood"
                    ]
                },
                "types": {
                    "main":[
                        "Trouble",
                        "Activity",
                        "Action",
                        "Task",
                        "Condition",
                        "Mood"

                    ],
                    "sub":[
                        "PromptingDescription",
                        "Object",
                        "Person",
                        "DailyEvent",
                        "Method",
                        "Support"

                    ],
                    "context":[
                        "Place",
                        "Time"
                    ]
                }
            }
        )

    def get_item_description(self, item_name):
        """アイテムの説明を取得（互換性のため）"""
        query = """
        MATCH (n:instance {name: $name})
        RETURN COALESCE(n.detail_description, n.description) as description
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, name=item_name)
                record = result.single()
                return record["description"] if record else None
        except Exception as e:
            self.debug_print(f"Error in get_item_description_: {e}")
            return None

    # エイリアスの設定
    get_item_full_info_sync = get_item_full_info
    get_children_sync = get_children
    get_followers_sync = get_followers
    get_item_description_sync = get_item_description

    def get_activity_top_nodes(self) -> List[Dict[str, Any]]:
        """Activityクラスのトップノードを取得"""
        self.debug_print("Starting get_activity_top_nodes")
        query = """
        MATCH (n:instance:Activity)
        WHERE NOT EXISTS((n)<-[:INCLUDES]-(:instance))
        RETURN n.name as name, 
               COALESCE(n.detail_description, n.description) as description, 
               n.time_to_achieve as time_to_achieve, 
               n.name_jp as name_jp
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query)
                nodes = [record for record in result]
                self.debug_print(f"Found {len(nodes)} Activity top nodes")
                return [{
                    'name': node['name'],
                    'description': node['description'] or "No description available",
                    'time_to_achieve': node['time_to_achieve'],
                    'name_jp': node['name_jp']
                } for node in nodes]
        except Exception as e:
            self.debug_print(f"Error in get_activity_top_nodes: {e}")
            traceback.print_exc()
            return []



'''
# 使用例
load_dotenv()

db = CareKgDB(os.getenv("NEO4J_DEV_SAMPLE_URL"), "neo4j", os.getenv("NEO4J_PASSWORD"))
instances = db.get_lending_ear_options()
#db.get_all()
db.close()

# 取得したインスタンスを表示

for instance in instances:
    print(f"Name: {instance['name']}, Description: {instance['description']}")

print(f"{len(instances)} instances found")
'''



