"""Static, bundled agent guidance; never read client-supplied filesystem paths."""
from pathlib import Path

SKILL_ROOT = Path(__file__).parent / 'skills' / 'lora-pilot'
SKILL_URI = 'lorapilot://skills/lora-pilot'
SKILL_RESOURCES = {
    SKILL_URI: ('LoRA Pilot agent skill', 'SKILL.md'),
    SKILL_URI + '/mcp-workflows': ('Dataset review, models, training and comparisons', 'references/mcp-workflows.md'),
    SKILL_URI + '/image-models': ('Image-model prompting and inference settings', 'references/image-models.md'),
    SKILL_URI + '/video-models': ('Video and audio prompting and settings', 'references/video-models.md'),
    SKILL_URI + '/inference': ('Inference tuning and controlled LoRA evaluation', 'references/inference.md'),
}


def read_skill_resource(uri):
    _, relative = SKILL_RESOURCES[uri]
    return (SKILL_ROOT / relative).read_text(encoding='utf-8')
