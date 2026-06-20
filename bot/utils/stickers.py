import random

# Har bir hodisa uchun stiker to'plami — random tanlanadi
# Agar stiker ishlamasa bot normal davom etadi (try/except)

# ─── Waifu tutilganda rarityga qarab ───
CATCH_COMMON = [
    'CAACAgIAAxkBAAEL1HFmK2AAARcgJLOeOKXgCbVXC-RPAAJ4AQACB8GhS8y3X-MOmEjGNAQ',
    'CAACAgIAAxkBAAEL1HNmK2AAARdTVVkP_OgOpMqCQnl7AAJ5AQACB8GhS1UsvPGGbBM2NAQ',
    'CAACAgIAAxkBAAEL1HVmK2AAAc2GmRFXBTpQvYkOulvhAAJ6AQACB8GhS0bOxnFd7g6oNAQ',
]

CATCH_RARE = [
    'CAACAgIAAxkBAAEL8GBmMhKBhXfOQ8ZMRKfhE_UHF9FSAAJ_DwACFMShS3tS3OAcefX5NAQ',
    'CAACAgIAAxkBAAEL8GJmMhKBqFZaQ2lnIhFrAgJMgYr6AAKADwACFMShSyXNhOeQJGFHNAQ',
    'CAACAgIAAxkBAAEL8GRmMhKBJ0XLrwMEAWyuvFHXW0ETAAJ_DwACFMShS5bZs72GHoGxNAQ',
]

CATCH_SR = [
    'CAACAgIAAxkBAAEMFqRmmjGPAAHarjCOjLvLVz-HY0T_QgACYgQAAqMv4Es4c3T5wWgFGjQE',
    'CAACAgIAAxkBAAEMFqZmmjGPHMKOQ1rCXAyLpJ1dFLoXHAACYgQAAqMv4Es5cxH7x1tqXjQE',
    'CAACAgIAAxkBAAEMFqhmmjGPzWHTh6sxkfzDxj_IiuVSAAJiBAACoS_4S-9tFnqG0XJWNAQ',
]

CATCH_EPIC = [
    'CAACAgIAAxkBAAENBsZm0WrqSlYpVFJbpK8tAAmKNaGaAAJyBwACFSCoS9wFWW3EhqFgNAQ',
    'CAACAgIAAxkBAAENBspm0WrqFBGRuCLdB3gbdG9rFbzUAAJ0BwACFSCoS0OHlcxHbPe5NAQ',
    'CAACAgIAAxkBAAENBsxm0WrqS2UBdGYDsK4YaLBkGb_BAAJ2BwACFSCoS4FPHKHuCXYwNAQ',
]

CATCH_MYTHIC = [
    'CAACAgIAAxkBAAENItBm1A2jPpCIFf5kJ_GBBi2sNtIRAALxCQACmFqoS3ggonLcDa3VNAQ',
    'CAACAgIAAxkBAAENItJm1A2jxQvBTVFLWbEbxHFXbKH6AALzCQACmFqoS4FpzDJbpXL0NAQ',
    'CAACAgIAAxkBAAENIt5m1A2jWaA2mvkbYUX3g6wNkf5OAAL1CQACmFqoS39kJFdgjqPXNAQ',
]

CATCH_LEGENDARY = [
    'CAACAgIAAxkBAAENQVVm3K4hT3e9yJZ5sRcPzUqIL2VKAAL6CwACvPaoS7dJkuYH3OmYNAQ',
    'CAACAgIAAxkBAAENQVdm3K4h-N3rBL5EMdmJ_UlYOHSFAAL8CwACvPaoS4P3hRXnSoExNAQ',
    'CAACAgIAAxkBAAENQVlm3K4hzJxuOjSwIXG7mHMvFz6GAAL-CwACvPaoS_v1fDMvRAQmNAQ',
]

CATCH_PREMIUM = [
    'CAACAgIAAxkBAAENdXFm5OGtMq3T9iBCOiPAAUtTpTFuAAITDgACXxqpS6YvMU2F6fhCNAQ',
    'CAACAgIAAxkBAAENdXNm5OGtqOW0UYd4k1Rm3kHJe7CFAAITDQACV-SpSzH7qYzDZo--NAQ',
]

CATCH_EXCLUSIVE = [
    'CAACAgIAAxkBAAENoCVm8xIi7VCkuBvhpf-tU9SAAXI1AAI5DgACvyapS0YNXI8kqjlkNAQ',
    'CAACAgIAAxkBAAENoClm8xIiMn1TDxdxJHpueFG5xpM9AAI7DgACvyapSwZkfqGkPfFDNAQ',
]

# ─── Kunlik mukofot ───
DAILY_NORMAL = [
    'CAACAgIAAxkBAAEL1HFmK2AAARcgJLOeOKXgCbVXC-RPAAJ4AQACB8GhS8y3X-MOmEjGNAQ',
    'CAACAgIAAxkBAAEL8GBmMhKBhXfOQ8ZMRKfhE_UHF9FSAAJ_DwACFMShS3tS3OAcefX5NAQ',
    'CAACAgIAAxkBAAEMFqRmmjGPAAHarjCOjLvLVz-HY0T_QgACYgQAAqMv4Es4c3T5wWgFGjQE',
]

DAILY_STREAK7 = [
    'CAACAgIAAxkBAAENoCVm8xIi7VCkuBvhpf-tU9SAAXI1AAI5DgACvyapS0YNXI8kqjlkNAQ',
    'CAACAgIAAxkBAAENQVVm3K4hT3e9yJZ5sRcPzUqIL2VKAAL6CwACvPaoS7dJkuYH3OmYNAQ',
]

SPAWN_NEW = [
    'CAACAgIAAxkBAAEL8GJmMhKBqFZaQ2lnIhFrAgJMgYr6AAKADwACFMShSyXNhOeQJGFHNAQ',
    'CAACAgIAAxkBAAEMFqhmmjGPzWHTh6sxkfzDxj_IiuVSAAJiBAACoS_4S-9tFnqG0XJWNAQ',
    'CAACAgIAAxkBAAENBsZm0WrqSlYpVFJbpK8tAAmKNaGaAAJyBwACFSCoS9wFWW3EhqFgNAQ',
]


def get_catch_sticker(rarity: str) -> str:
    mapping = {
        'Common':    CATCH_COMMON,
        'Rare':      CATCH_RARE,
        'Super Rare': CATCH_SR,
        'Epic':      CATCH_EPIC,
        'Mythic':    CATCH_MYTHIC,
        'Legendary': CATCH_LEGENDARY,
        'Premium':   CATCH_PREMIUM,
        'Exclusive': CATCH_EXCLUSIVE,
    }
    pool = mapping.get(rarity, CATCH_COMMON)
    return random.choice(pool)


def get_daily_sticker(streak: int) -> str:
    if streak >= 7:
        return random.choice(DAILY_STREAK7)
    return random.choice(DAILY_NORMAL)


async def send_sticker(bot, chat_id: int, file_id: str):
    """Stiker yuboradi; xato bo'lsa jimgina o'tkazib yuboradi."""
    try:
        await bot.send_sticker(chat_id=chat_id, sticker=file_id)
    except Exception:
        pass