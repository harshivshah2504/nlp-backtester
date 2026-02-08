import ast
import os


def extract_classes(source_code):
    tree = ast.parse(source_code)
    main_code = []  
    BASE_FOLDER = "delta_one_template"
    strategy_class_name = None

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            if class_name not in ["TradeManagement", "RiskManagement"]:
                strategy_class_name = class_name
                break 

    if not strategy_class_name:
        raise ValueError("No unknown strategy class found in the code!")


    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            class_code = ast.unparse(node) 
            
            if class_name == "TradeManagement":
                folder = BASE_FOLDER
                filename = f"trade_management/trade_management_{strategy_class_name}.py"
            elif class_name == "RiskManagement":
                folder = BASE_FOLDER
                filename = f"risk_management/risk_management_{strategy_class_name}.py"
            else:
                folder = os.path.join(BASE_FOLDER, "strategies")
                filename = f"{class_name}.py"

            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, filename)
            with open(file_path, "w") as f:
                f.write(class_code)



    print(f"Classes extracted to respective folders in '{BASE_FOLDER}/'")

