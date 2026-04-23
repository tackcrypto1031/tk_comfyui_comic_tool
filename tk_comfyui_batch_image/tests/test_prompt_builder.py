from tk_comfyui_batch_image.core.prompt_builder import build_prompt_pair


def test_all_layers_concatenated_with_commas():
    pos, neg = build_prompt_pair(
        style={"positive": "anime style", "negative": "blurry"},
        character={"positive": "a girl", "negative": "extra limbs"},
        page={"positive": "night", "negative": "daylight"},
        scene={"positive": "looking at sky", "negative": "crowd"},
        positive_suffix="masterpiece",
        negative_suffix="lowres",
    )
    assert pos == "anime style, a girl, night, looking at sky, masterpiece"
    assert neg == "blurry, extra limbs, daylight, crowd, lowres"


def test_empty_layers_are_skipped():
    pos, neg = build_prompt_pair(
        style={"positive": "", "negative": ""},
        character={"positive": "a girl", "negative": ""},
        page={"positive": "", "negative": ""},
        scene={"positive": "smile", "negative": ""},
        positive_suffix="",
        negative_suffix="",
    )
    assert pos == "a girl, smile"
    assert neg == ""


def test_whitespace_only_layers_are_skipped():
    pos, neg = build_prompt_pair(
        style={"positive": "   ", "negative": "  "},
        character={"positive": "hero", "negative": ""},
        page={"positive": "", "negative": ""},
        scene={"positive": "scene", "negative": ""},
        positive_suffix="",
        negative_suffix="",
    )
    assert pos == "hero, scene"
    assert neg == ""


def test_trailing_commas_in_layers_are_handled():
    pos, neg = build_prompt_pair(
        style={"positive": "anime,", "negative": ""},
        character={"positive": "girl, ", "negative": ""},
        page={"positive": "", "negative": ""},
        scene={"positive": "smile", "negative": ""},
        positive_suffix="",
        negative_suffix="",
    )
    assert pos == "anime, girl, smile"
