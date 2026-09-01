from dataclasses import dataclass


@dataclass
class UsageBudget:
    token_limit: int
    used_tokens: int = 0

    def reserve(self, requested_tokens: int) -> int:
        if requested_tokens < 1 or self.token_limit < 1:
            raise ValueError("Usage limits must be positive")
        remaining = self.token_limit - self.used_tokens
        if remaining <= 0:
            raise PermissionError("AI usage limit exceeded")
        charged = min(requested_tokens, remaining)
        self.used_tokens += charged
        return charged

