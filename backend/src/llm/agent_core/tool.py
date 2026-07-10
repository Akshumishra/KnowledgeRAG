class Tool:
    def __init__(self, func, description: str = None, args_schema=None):
        self.name = func.__name__
        self.func = func
        self.description = description
        self.args_schema = args_schema

    def execute(self, **kwargs):
        return self.func(**kwargs)

    def schema(self):
        if self.args_schema is None:
            return {
                "type": "function",
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            }

        properties = {}
        required = []

        for name, args in self.args_schema.args:

            properties[name] = {
                "type": self._map_type(args.type),
                "description": args.description,
            }

            if args.enum is not None:
                properties[name]["enum"] = args.enum

            if args.default is not None:
                properties[name]["default"] = args.default

            if args.required:
                required.append(name)

        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    @staticmethod
    def _map_type(py_type):
        return {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
        }.get(py_type, "string")
