# rule_processor.py
def process_rules(speckle_objects: list[Base], rules: list[dict], action_handler) -> dict:
    """Process rules against objects and apply actions."""
    results = {}

    for obj in speckle_objects:
        for rule in rules:
            if evaluate_rule(obj, rule):
                action_handler.apply_action(obj, rule)
                results[obj.id] = rule["action_type"]

    return results