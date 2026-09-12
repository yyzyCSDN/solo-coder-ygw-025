class DomainRules:
    """Room-grade and sensor validation used before current single-room control."""
    GRADES={"A","B","C","D"}
    @classmethod
    def room_grade(cls,value: str) -> str:
        value=value.strip().upper()
        if value not in cls.GRADES: raise ValueError("unknown room grade")
        return value
    @staticmethod
    def particle_count(value: float) -> float:
        value=float(value)
        if value<0: raise ValueError("negative particle count")
        return value
    @staticmethod
    def door_contact(value: str) -> str:
        if value not in {"open","closed","unknown"}: raise ValueError("bad door contact")
        return value
