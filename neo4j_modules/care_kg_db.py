

from neo4j import GraphDatabase
from dotenv import load_dotenv
import os



class CareKgDB:
    def __init__(self, uri : str, user : str, password : str, user_uuid : str = None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.user_uuid = user_uuid

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



if __name__ == "__main__":
    # 使用例
    load_dotenv()

    db = CareKgDB(os.getenv("NEO4J_URI"), os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    instances = db.get_uot_nodes()
    #db.get_all()
    db.close()

    # 取得したインスタンスを表示

    for instance in instances:
        print(f"Name: {instance['name']}, Description: {instance['description']}")

    print(f"{len(instances)} instances found")
