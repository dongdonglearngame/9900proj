def token_edit_distance(original: str, modified: str | None) -> int | None:
    if modified is None:
        return None
    a = original.split()
    b = modified.split()
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i, original_token in enumerate(a, start=1):
        for j, modified_token in enumerate(b, start=1):
            cost = 0 if original_token == modified_token else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[-1][-1]


def changed_word_fraction(original: str, modified: str | None) -> float | None:
    distance = token_edit_distance(original, modified)
    if distance is None:
        return None
    denominator = max(1, len(original.split()))
    return round(distance / denominator, 4)
