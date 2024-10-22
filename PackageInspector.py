import importlib
import inspect
import math
import ace_tools
print(ace_tools.__file__)

class PackageInspector:
    def __init__(self, package_name):
        self.package_name = package_name
        self.package = None

    def import_package(self):
        """
        Dynamically import a package by name.
        """
        try:
            self.package = importlib.import_module(self.package_name)
            print(f"Package '{self.package_name}' successfully imported.")
        except ImportError as e:
            print(f"Error importing package '{self.package_name}': {e}")
            self.package = None

    def get_functions(self):
        """
        Retrieve all functions from the package.
        """
        if self.package is None:
            print(f"Package '{self.package_name}' is not imported.")
            return []

        functions = inspect.getmembers(self.package, inspect.isfunction)
        return functions

    def get_classes(self):
        """
        Retrieve all classes from the package.
        """
        if self.package is None:
            print(f"Package '{self.package_name}' is not imported.")
            return []

        classes = inspect.getmembers(self.package, inspect.isclass)
        return classes
class PackageInspector(PackageInspector):
    def analyze_function(self, func):
        """
        Analyze a single function: Get its name, parameters, and docstring.
        """
        func_name = func.__name__
        func_signature = inspect.signature(func)
        func_doc = inspect.getdoc(func)

        return {
            'name': func_name,
            'signature': str(func_signature),
            'docstring': func_doc or "No docstring available"
        }

    def breakdown_functions(self):
        """
        Provide a breakdown of all functions in the package, including their parameters and docstring.
        """
        functions = self.get_functions()
        if not functions:
            print("No functions found.")
            return

        breakdown = []
        for name, func in functions:
            func_info = self.analyze_function(func)
            breakdown.append(func_info)

        return breakdown
class PackageInspector(PackageInspector):
    def analyze_class(self, cls):
        """
        Analyze a class: List methods and their descriptions.
        """
        class_methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        methods_info = []

        for method_name, method in class_methods:
            method_info = self.analyze_function(method)
            methods_info.append(method_info)

        return {
            'class_name': cls.__name__,
            'methods': methods_info
        }

    def breakdown_classes(self):
        """
        Provide a breakdown of all classes and their methods in the package.
        """
        classes = self.get_classes()
        if not classes:
            print("No classes found.")
            return

        class_breakdown = []
        for name, cls in classes:
            class_info = self.analyze_class(cls)
            class_breakdown.append(class_info)

        return class_breakdown
if __name__ == "__main__":
    # Create an instance of the inspector
    inspector = PackageInspector('math')

    # Import the package
    inspector.import_package()

    # Get a breakdown of functions
    function_breakdown = inspector.breakdown_functions()
    for func in function_breakdown:
        print(f"Function: {func['name']}")
        print(f"Signature: {func['signature']}")
        print(f"Docstring: {func['docstring']}")
        print("\n")
