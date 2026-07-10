from typing import Any, Optional, Type, List


class ArgsSchema:
    def __init__(
        self,
        type: Type,
        description: str,
        required: bool = True,
        default: Optional[Any] = None,
        enum: Optional[List[Any]] = None,
    ):
        self.type = type
        self.description = description
        self.required = required
        self.default = default
        self.enum = enum
