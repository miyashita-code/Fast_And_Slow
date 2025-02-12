class Item:
    def __init__(self, name, description, p_s, ontology_type: str = None, context_info: dict = None, time_to_achieve: float = None, name_jp: str = None):
        self.name = name
        self.description = description
        self.p_s = p_s
        self.ontology_type = ontology_type
        self.context_info = context_info or {'global_context': '', 'local_context': []}
        self.time_to_achieve = time_to_achieve
        self.name_jp = name_jp


    def update_p_s(self, p_s):
        self.p_s = p_s

    def get_name(self):
        return self.name

    def get_item_info(self) -> str:
        "Debug function"
        return f"name={self.name}, description={self.description}, p_s={self.p_s}, time_to_achieve={self.time_to_achieve}, name_jp={self.name_jp}"
