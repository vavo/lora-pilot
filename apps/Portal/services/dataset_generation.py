"""Small native ComfyUI graphs for the dataset builder (no partner nodes)."""
from fastapi import HTTPException
from .tagpilot_local import MODEL_NAME as CAPTION_MODEL

RECIPE_VERSION = 'qwen-2511-v1'
MODEL_FILES = {
    'dataset-qwen-edit': ('diffusion_models', 'qwen_image_edit_2511_fp8mixed.safetensors'),
    'hunyuanimage-2.1-comfy-qwen-encoder-fp8': ('text_encoders', 'qwen_2.5_vl_7b_fp8_scaled.safetensors'),
    'anima-vae': ('vae', 'qwen_image_vae.safetensors'),
}
CHECKPOINT = 'sd_xl_base_1.0.safetensors'
MODEL_SIZES = {'dataset-qwen-edit': 20533762817, 'hunyuanimage-2.1-comfy-qwen-encoder-fp8': 9384670680,
               'anima-vae': 253806246, 'sdxl-base': 6938078334}


def node(kind, **inputs):
    return dict(class_type=kind, inputs=inputs)


def reference_graph(prompt, seed, prefix):
    return {
        '1': node('CheckpointLoaderSimple', ckpt_name=CHECKPOINT),
        '2': node('CLIPTextEncode', clip=['1', 1], text=prompt),
        '3': node('CLIPTextEncode', clip=['1', 1], text='blurry, watermark, text, collage, multiple people'),
        '4': node('EmptyLatentImage', width=768, height=1024, batch_size=1),
        '5': node('KSampler', model=['1', 0], positive=['2', 0], negative=['3', 0],
                  latent_image=['4', 0], seed=seed, steps=30, cfg=7.0,
                  sampler_name='dpmpp_2m', scheduler='normal', denoise=1.0),
        '6': node('VAEDecode', samples=['5', 0], vae=['1', 2]),
        '7': node('SaveImage', images=['6', 0], filename_prefix=prefix),
    }


def variation_graph(image, prompt, seed, prefix):
    # Native 2511 recipe: Comfy-Org/workflow_templates image_qwen_image_edit_2511.json.
    # Keep full 40-step editing; do not silently mix a Lightning adapter into this recipe.
    return {
        '1': node('UNETLoader', unet_name=MODEL_FILES['dataset-qwen-edit'][1], weight_dtype='default'),
        '2': node('CLIPLoader', clip_name=MODEL_FILES['hunyuanimage-2.1-comfy-qwen-encoder-fp8'][1], type='qwen_image', device='default'),
        '3': node('VAELoader', vae_name=MODEL_FILES['anima-vae'][1]),
        '4': node('LoadImage', image=image),
        '5': node('FluxKontextImageScale', image=['4', 0]),
        '6': node('TextEncodeQwenImageEditPlus', clip=['2', 0], vae=['3', 0], image1=['5', 0], prompt=prompt),
        '7': node('TextEncodeQwenImageEditPlus', clip=['2', 0], vae=['3', 0], image1=['5', 0], prompt=''),
        '8': node('ModelSamplingAuraFlow', model=['1', 0], shift=3.1),
        '9': node('CFGNorm', model=['8', 0], strength=1.0),
        '10': node('VAEEncode', pixels=['5', 0], vae=['3', 0]),
        '11': node('KSampler', model=['9', 0], positive=['6', 0], negative=['7', 0],
                   latent_image=['10', 0], seed=seed, steps=40, cfg=4.0,
                   sampler_name='euler', scheduler='simple', denoise=1.0),
        '12': node('VAEDecode', samples=['11', 0], vae=['3', 0]),
        '13': node('SaveImage', images=['12', 0], filename_prefix=prefix),
    }


def validate_graph(graph, registry, uploaded=False):
    for item in graph.values():
        kind = item['class_type']
        if kind not in registry:
            raise HTTPException(409, f'ComfyUI is missing {kind}. Update or restart ComfyUI in Services.')
        schema = registry[kind].get('input', {})
        required = schema.get('required', {})
        known = {**required, **schema.get('optional', {})}
        if set(required) - item['inputs'].keys():
            raise HTTPException(409, f'ComfyUI {kind} requires different inputs. This dataset recipe needs updating.')
        for key, value in item['inputs'].items():
            if key not in known:
                raise HTTPException(409, f'ComfyUI {kind} does not support {key}.')
            allowed = known[key][0]
            if isinstance(value, list):
                if len(value) != 2 or value[0] not in graph:
                    raise HTTPException(500, 'Invalid dataset workflow link')
            elif isinstance(allowed, list) and value not in allowed:
                if kind == 'LoadImage' and (uploaded or value == 'reference.png'):
                    continue  # Uploaded after registry inspection; Comfy validates the actual filename.
                raise HTTPException(409, f'{value} is missing in ComfyUI. Install the required model in Models.')


def shot_plan(count, goal, vary_clothes, vary_hair):
    angles = ['front view', 'front-left three-quarter view', 'front-right three-quarter view',
              'left profile', 'right profile', 'slightly elevated front view']
    frames = ['close-up portrait', 'waist-up portrait', 'full-body photograph']
    scenes = ['plain studio background, soft daylight', 'outdoor park, overcast daylight',
              'simple indoor room, window light', 'city street, evening light']
    clothes = ['a plain blue shirt', 'a dark casual jacket', 'a cream sweater', 'a simple green T-shirt']
    result = []
    for i in range(count):
        frame, angle = frames[i % 3], angles[(i // 3) % len(angles)]
        details = [frame, angle, scenes[(i // 2) % len(scenes)],
                   ['neutral expression', 'gentle smile', 'relaxed expression'][i % 3]]
        if goal == 'identity' and vary_clothes:
            details.append('wearing ' + clothes[(i // 3) % len(clothes)])
        else:
            details.append('keep the original clothing exactly')
        details.append('hair tied back, preserving colour and hairline' if goal == 'identity' and vary_hair and i % 4 == 3
                       else 'keep the original hairstyle and hair colour')
        prompt = ('Create one photograph of the same single person or character from the reference. '
                  'Preserve their facial identity, age, skin tone, body proportions and defining features. '
                  + ', '.join(details) + '. Natural anatomy. No collage, labels or watermark.')
        result.append(dict(slot=i, shot=f'{frame}, {angle}', prompt=prompt, attempts=0, accepted=False))
    return result
