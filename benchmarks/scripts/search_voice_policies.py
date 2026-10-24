"""Rejected decoder experiments, retained for reproducibility; not production config."""

SHOPPING_CONTEXT = (
    "Danh mục sản phẩm: giày dép, áo khoác, áo len, tai nghe, loa, "
    "bàn, ghế, đèn, túi xách. Màu sắc, chất liệu, giá tiền."
)


def decoding_options(policy: str = "long_prompt") -> dict:
    options = dict(
        language="vi",
        beam_size=3,
        best_of=3,
        temperature=0,
        condition_on_previous_text=False,
        vad_filter=False,
        max_new_tokens=160,
        repetition_penalty=1.1,
        no_repeat_ngram_size=3,
    )
    if policy == "long_prompt":
        options["initial_prompt"] = SHOPPING_CONTEXT
    elif policy == "short_prompt":
        options["initial_prompt"] = "Mua sắm: giày, dép, áo, tai nghe, bàn, ghế."
    elif policy == "beam5":
        options.update(
            beam_size=5, best_of=5, repetition_penalty=1.0, no_repeat_ngram_size=0
        )
    else:
        raise ValueError("Unknown experiment")
    return options
