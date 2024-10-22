import ast

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.assignments = []
        self.loops = 0

    def visit_FunctionDef(self, node):
        """Visit function definitions"""
        self.functions.append(node.name)
        print(f"Found function: {node.name}")
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Visit variable assignments"""
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        self.assignments.extend(targets)
        print(f"Found assignment to: {', '.join(targets)}")
        self.generic_visit(node)

    def visit_While(self, node):
        """Visit while loops"""
        self.loops += 1
        print(f"Found a while loop")
        self.generic_visit(node)

    def visit_For(self, node):
        """Visit for loops"""
        self.loops += 1
        print(f"Found a for loop")
        self.generic_visit(node)

    def analyze_code(self, code):
        """Analyze the provided Python code"""
        tree = ast.parse(code)
        self.visit(tree)

    def determine_next_action(self):
        """Decide what to do next based on the analysis"""
        if 'process_data' in self.functions:
            print("Next action: Call the process_data function.")
        elif 'config' in self.assignments:
            print("Next action: Initialize the config object.")
        elif self.loops > 0:
            print("Next action: Handle loop logic.")
        else:
            print("Next action: Default behavior - no functions, assignments, or loops found.")


# Example Python code to analyze
code_to_analyze = """
def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result

config = {'setting': 'value'}
while True:
    print("Running indefinitely")
"""

# Create the analyzer and run it
analyzer = CodeAnalyzer()
analyzer.analyze_code(code_to_analyze)
analyzer.determine_next_action()
import ast

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.assignments = []
        self.loops = 0

    def visit_FunctionDef(self, node):
        """Visit function definitions"""
        self.functions.append(node.name)
        print(f"Found function: {node.name}")
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Visit variable assignments"""
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        self.assignments.extend(targets)
        print(f"Found assignment to: {', '.join(targets)}")
        self.generic_visit(node)

    def visit_While(self, node):
        """Visit while loops"""
        self.loops += 1
        print(f"Found a while loop")
        self.generic_visit(node)

    def visit_For(self, node):
        """Visit for loops"""
        self.loops += 1
        print(f"Found a for loop")
        self.generic_visit(node)

    def analyze_code(self, code):
        """Analyze the provided Python code"""
        tree = ast.parse(code)
        self.visit(tree)

    def determine_next_action(self):
        """Decide what to do next based on the analysis"""
        if 'process_data' in self.functions:
            print("Next action: Call the process_data function.")
        elif 'config' in self.assignments:
            print("Next action: Initialize the config object.")
        elif self.loops > 0:
            print("Next action: Handle loop logic.")
        else:
            print("Next action: Default behavior - no functions, assignments, or loops found.")


# Example Python code to analyze
code_to_analyze = """
def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result

config = {'setting': 'value'}
while True:
    print("Running indefinitely")
"""

# Create the analyzer and run it
analyzer = CodeAnalyzer()
analyzer.analyze_code(code_to_analyze)
analyzer.determine_next_action()
