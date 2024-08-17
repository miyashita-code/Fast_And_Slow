

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os



class CareKgDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

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
            print([r for r in result])



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


