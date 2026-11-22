"""Native ComfyUI comparison graphs, checked against the running node registry."""
import re
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from .comfy_access import internal_headers
from .service_registry import local_url


class ComparisonRequest(BaseModel):
    artifact: str | None = Field(default=None, min_length=1, max_length=200)
    all_checkpoints: bool = False
    prompt: str = Field(min_length=1, max_length=2000)
    seed: int = Field(default=31337, ge=0, le=2**32 - 1)
    strength: float = Field(default=1.0, ge=0, le=2)


def comfy(method, path, **kwargs):
    try:
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.request(method, f'{local_url("comfy")}/{path}', headers=internal_headers(), **kwargs)
            if response.status_code >= 400:
                raise HTTPException(400, 'ComfyUI rejected the comparison: ' + response.text[:1000])
            return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'ComfyUI is unavailable. Start it in Services and try again.')


def checkpoint_order(name):
    match = re.search(r'(?:-step|-)(\d+)\.safetensors$', name)
    return (0, int(match[1]), name) if match else (1, 0, name)



def comparison_unavailable(family):
    if family not in {'sdxl', 'sd15', 'sd35_medium', 'sd35_large', 'flux1', 'anima', 'lumina2', 'hunyuan_image21'}:
        return 'Built-in comparisons are not available for this model family.'
    return None

def graph(run, request, lora_name, registry):
    nodes = {}
    config = run['template']
    family = run['spec']['family']
    if reason := comparison_unavailable(family):
        raise HTTPException(400, reason)
    flux = family == 'flux1'
    sd3 = family in {'sd35_medium', 'sd35_large'}

    def add(node_id, kind, **inputs):
        if kind not in registry:
            raise HTTPException(400, f'ComfyUI node {kind} is unavailable. Check the installed ComfyUI version.')
        definition = registry[kind].get('input', {})
        known = {**definition.get('required', {}), **definition.get('optional', {})}
        for key, value in inputs.items():
            if key not in known:
                raise HTTPException(400, f'ComfyUI node {kind} does not support {key}')
            allowed = known[key][0]
            if isinstance(allowed, list) and value not in allowed:
                raise HTTPException(400, f'{kind}: {value} is unavailable. Refresh ComfyUI models or check the training base model.')
        nodes[node_id] = {'class_type': kind, 'inputs': inputs}
        return [node_id, 0]

    def model_name(key, folder):
        path = Path(config[key])
        parts = path.parts
        try:
            return Path(*parts[parts.index(folder) + 1:]).as_posix()
        except ValueError:
            raise HTTPException(400, f'The training {key} must be available in ComfyUI’s {folder} folder')

    if family in {'anima', 'lumina2', 'hunyuan_image21'}:
        model = add('1', 'UNETLoader', unet_name=model_name('pretrained_model_name_or_path', 'diffusion_models'), weight_dtype='default')
        if family == 'hunyuan_image21':
            clip = add('2', 'DualCLIPLoader', clip_name1=model_name('text_encoder', 'text_encoders'),
                       clip_name2=model_name('byt5', 'text_encoders'), type='hunyuan_image')
        else:
            clip = add('2', 'CLIPLoader', clip_name=model_name('qwen3' if family == 'anima' else 'gemma2', 'text_encoders'),
                       type='stable_diffusion' if family == 'anima' else 'lumina2')
        vae = add('3', 'VAELoader', vae_name=model_name('ae' if family == 'lumina2' else 'vae', 'vae'))
        if family == 'lumina2':
            model = add('6', 'ModelSamplingAuraFlow', model=model, shift=6.0)
    elif flux:
        model = add('1', 'UNETLoader', unet_name=model_name('pretrained_model_name_or_path', 'diffusion_models'), weight_dtype='default')
        clip = add('2', 'DualCLIPLoader', clip_name1=model_name('clip_l', 'text_encoders'), clip_name2=model_name('t5xxl', 'text_encoders'), type='flux')
        vae = add('3', 'VAELoader', vae_name=model_name('ae', 'vae'))
    else:
        model = add('1', 'CheckpointLoaderSimple', ckpt_name=model_name('pretrained_model_name_or_path', 'checkpoints'))
        clip, vae = ['1', 1], ['1', 2]
        if sd3:
            clip = add('2', 'TripleCLIPLoader', clip_name1=model_name('clip_l', 'text_encoders'),
                       clip_name2=model_name('clip_g', 'text_encoders'), clip_name3=model_name('t5xxl', 'text_encoders'))
            model = add('6', 'ModelSamplingSD3', model=model, shift=3.0)
        if config.get('vae'):
            if 'checkpoints' in Path(config['vae']).parts:
                add('3', 'CheckpointLoaderSimple', ckpt_name=model_name('vae', 'checkpoints'))
                vae = ['3', 2]
            else:
                vae = add('3', 'VAELoader', vae_name=model_name('vae', 'vae'))
    size = 512 if family == 'sd15' else 2048 if family == 'hunyuan_image21' else 1024
    latent_type = 'EmptyLatentImage'
    if flux or sd3 or family == 'lumina2':
        latent_type = 'EmptySD3LatentImage'
    if family == 'hunyuan_image21':
        latent_type = 'EmptyHunyuanImageLatent'
    latent = add('5', latent_type, width=size, height=size, batch_size=1)
    steps, cfg, sampler, scheduler = {
        'anima': (30, 4.0, 'euler', 'simple'),
        'lumina2': (25, 4.0, 'res_multistep', 'simple'),
        'hunyuan_image21': (20, 3.5, 'euler', 'simple'),
    }.get(family, (20, 1.0 if flux else 4.5 if sd3 else 7.0,
                   'euler' if flux or sd3 else 'dpmpp_2m', 'simple' if flux or sd3 else 'normal'))
    names = [lora_name] if isinstance(lora_name, str) else lora_name
    for index, name in enumerate([None, *names]):
        base = 10 + index * 10
        branch_model, branch_clip = model, clip
        label = 'Without LoRA' if name is None else Path(name).name
        if name is not None:
            loader = '4' if index == 1 else str(base + 6)
            branch_model = add(loader, 'LoraLoader', model=model, clip=clip, lora_name=name,
                               strength_model=request.strength, strength_clip=request.strength)
            branch_clip = [loader, 1]
        text = request.prompt
        if family == 'lumina2':
            text = config.get('system_prompt', 'You are an assistant designed to generate superior images with the superior degree of image-text alignment based on textual prompts or user prompts.') + ' <Prompt Start> ' + text
        positive = add(str(base), 'CLIPTextEncode', text=text, clip=branch_clip)
        negative = add(str(base + 1), 'CLIPTextEncode', text='', clip=branch_clip)
        if flux:
            positive = add(str(base + 2), 'FluxGuidance', conditioning=positive, guidance=3.5)
        samples = add(str(base + 3), 'KSampler', model=branch_model, positive=positive, negative=negative,
                      latent_image=latent, seed=request.seed, steps=steps, cfg=cfg,
                      sampler_name=sampler, scheduler=scheduler, denoise=1.0)
        image = add(str(base + 4), 'VAEDecode', samples=samples, vae=vae)
        add(str(base + 5), 'SaveImage', images=image, filename_prefix=f'LoRA-Pilot/{run["id"]}/{index:03d}')
        nodes[str(base + 5)]['_meta'] = {'title': label}
    return nodes


def comparison_outputs(workflow):
    return [dict(node_id=node_id, label=node['_meta']['title'])
            for node_id, node in workflow.items() if node['class_type'] == 'SaveImage']


def result_images(history, expected=None):
    images = []
    expected = expected or [dict(node_id='15', label='Without LoRA'), dict(node_id='25', label='With LoRA')]
    for entry in expected:
        outputs = history.get('outputs', {}).get(entry['node_id'], {}).get('images', [])
        if outputs:
            item = outputs[0]
            images.append(dict(label=entry['label'], url='/proxy/comfy/view?' + urlencode({
                'filename': item['filename'], 'subfolder': item.get('subfolder', ''), 'type': 'output'})))
    return images
