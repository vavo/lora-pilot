"""Native ComfyUI comparison graphs, checked against the running node registry."""
import os
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    artifact: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)
    seed: int = Field(default=31337, ge=0, le=2**32 - 1)
    strength: float = Field(default=1.0, ge=0, le=2)


def comfy(method, path, **kwargs):
    try:
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.request(method, f'http://127.0.0.1:{int(os.environ.get("COMFY_PORT", "5555"))}/{path}', **kwargs)
            if response.status_code >= 400:
                raise HTTPException(400, 'ComfyUI rejected the comparison: ' + response.text[:1000])
            return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'ComfyUI is unavailable. Start it in Services and try again.')


def graph(run, request, lora_name, registry):
    nodes = {}
    config = run['template']
    flux = run['spec']['family'] == 'flux1'

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

    if flux:
        model = add('1', 'UNETLoader', unet_name=model_name('pretrained_model_name_or_path', 'diffusion_models'), weight_dtype='default')
        clip = add('2', 'DualCLIPLoader', clip_name1=model_name('clip_l', 'text_encoders'), clip_name2=model_name('t5xxl', 'text_encoders'), type='flux')
        vae = add('3', 'VAELoader', vae_name=model_name('ae', 'vae'))
    else:
        model = add('1', 'CheckpointLoaderSimple', ckpt_name=model_name('pretrained_model_name_or_path', 'checkpoints'))
        clip, vae = ['1', 1], ['1', 2]
        if config.get('vae'):
            if 'checkpoints' in Path(config['vae']).parts:
                add('3', 'CheckpointLoaderSimple', ckpt_name=model_name('vae', 'checkpoints'))
                vae = ['3', 2]
            else:
                vae = add('3', 'VAELoader', vae_name=model_name('vae', 'vae'))
    add('4', 'LoraLoader', model=model, clip=clip, lora_name=lora_name,
        strength_model=request.strength, strength_clip=request.strength)
    latent = add('5', 'EmptySD3LatentImage' if flux else 'EmptyLatentImage', width=1024, height=1024, batch_size=1)
    for prefix, branch_model, branch_clip, label in [('10', model, clip, 'without-lora'), ('20', ['4', 0], ['4', 1], 'with-lora')]:
        base = int(prefix)
        positive = add(str(base), 'CLIPTextEncode', text=request.prompt, clip=branch_clip)
        negative = add(str(base + 1), 'CLIPTextEncode', text='', clip=branch_clip)
        if flux:
            positive = add(str(base + 2), 'FluxGuidance', conditioning=positive, guidance=3.5)
        samples = add(str(base + 3), 'KSampler', model=branch_model, positive=positive, negative=negative,
                      latent_image=latent, seed=request.seed, steps=20, cfg=1.0 if flux else 7.0,
                      sampler_name='euler' if flux else 'dpmpp_2m', scheduler='simple' if flux else 'normal', denoise=1.0)
        image = add(str(base + 4), 'VAEDecode', samples=samples, vae=vae)
        add(str(base + 5), 'SaveImage', images=image, filename_prefix=f'LoRA-Pilot/{run["id"]}/{label}')
    return nodes


def result_images(history):
    images = []
    for node, label in [('15', 'Without LoRA'), ('25', 'With LoRA')]:
        outputs = history.get('outputs', {}).get(node, {}).get('images', [])
        if outputs:
            item = outputs[0]
            images.append(dict(label=label, url='/proxy/comfy/view?' + urlencode({
                'filename': item['filename'], 'subfolder': item.get('subfolder', ''), 'type': 'output'})))
    return images
