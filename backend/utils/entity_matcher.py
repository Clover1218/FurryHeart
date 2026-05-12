import pickle
from collections import defaultdict


class AcNode:
    """Aho-Corasick 自动机节点"""
    
    def __init__(self):
        self.children = {}
        self.fail = None
        self.output = []  # 存储匹配到的实体 (node_id, entity_name)


class AcEntityMatcher:
    """基于 Aho-Corasick 算法的实体匹配器"""
    
    def __init__(self):
        self.root = AcNode()
        self.entities = {}  # entity_name -> node_id
    
    def add_node(self, node_id: str, entity_name: str):
        """添加实体节点"""
        self.entities[entity_name] = node_id
        self._insert(entity_name, node_id)
    
    def _insert(self, pattern: str, node_id: str):
        """向自动机插入模式串"""
        node = self.root
        for char in pattern:
            if char not in node.children:
                node.children[char] = AcNode()
            node = node.children[char]
        node.output.append((node_id, pattern))
    
    def build(self):
        """构建失败指针（BFS）"""
        from collections import deque
        
        queue = deque()
        
        # 初始化第一层节点的失败指针
        for child in self.root.children.values():
            child.fail = self.root
            queue.append(child)
        
        # BFS构建失败指针
        while queue:
            current_node = queue.popleft()
            
            for char, child in current_node.children.items():
                # 找到失败指针
                fail_node = current_node.fail
                while fail_node is not None and char not in fail_node.children:
                    fail_node = fail_node.fail
                
                child.fail = fail_node.children[char] if fail_node else self.root
                
                # 合并输出
                child.output += child.fail.output
                
                queue.append(child)
    
    def match(self, text: str):
        """匹配文本中的所有实体，返回详细信息（包含位置）"""
        results = []
        node = self.root
        
        for idx, char in enumerate(text):
            # 沿着失败链找匹配
            while node is not None and char not in node.children:
                node = node.fail
            
            if node is None:
                node = self.root
                continue
            
            node = node.children[char]
            
            # 收集所有匹配结果
            for node_id, entity_name in node.output:
                start = idx - len(entity_name) + 1
                end = idx + 1
                results.append((node_id, entity_name, start, end))
        
        return results
    
    def match_unique(self, text: str):
        """匹配文本中的唯一实体（去重）"""
        matches = self.match(text)
        seen = set()
        unique_results = []
        
        for node_id, entity_name, _, _ in matches:
            key = (node_id, entity_name)
            if key not in seen:
                seen.add(key)
                unique_results.append((node_id, entity_name))
        
        return unique_results
    
    def save(self, filepath: str):
        """保存匹配器到文件"""
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
    
    @staticmethod
    def load(filepath: str):
        """从文件加载匹配器"""
        with open(filepath, 'rb') as f:
            return pickle.load(f)
