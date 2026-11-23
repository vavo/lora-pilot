// Display metadata only. Downloads and installed state come from the manifest API.
window.modelFamilies = [
  { id: "ltx25", title: "LTX-2.5", task: "video", match: "ltx-2.5", summary: "Fast video iteration", tags: ["Text to video", "Image to video"], description: "Start with the bundled video workflow.", workflow: "video_ltx2_5_t2v.json" },
  { id: "minimax-image", title: "MiniMax H3 Image", task: "images", match: "minimax-h3-image", summary: "Still images and image editing", tags: ["Image generation", "Image editing", "LoRA training"], description: "Uses the H3 text encoder with its own image VAE. Training requires the image adapter.", training: true, editing: true, components: ["minimax-h3-qwen3vl-32b-nvfp4"] },
  { id: "minimax", title: "MiniMax H3 / FastH3", task: "video", match: "minimax-h3", summary: "Video with synchronized sound", tags: ["Text to video", "Image to video"], description: "The bundled workflows use MiniMax H3. FastH3 needs its own workflow and training adapter; Omni supports references, while 8-Step V2 is text-to-video/audio only.", workflow: "video_minimax_h3_t2v.json" },
  { id: "ltx23", title: "LTX-2.3", task: "video", match: "ltx-2.3", summary: "Video models and adapters", tags: ["Video generation", "LoRAs"], description: "Browse checkpoints, distilled variants and upscalers." },
  { id: "wan", title: "Wan", task: "video", match: "wan", summary: "Video and character animation", tags: ["Video generation", "Animation"], description: "Choose a model for your Wan workflow." },
  { id: "hunyuanvideo", title: "HunyuanVideo", task: "video", match: "hunyuan-video", summary: "Text to video", tags: ["Video generation"], description: "Browse video checkpoints and the accompanying VAE." },
  { id: "flux", title: "FLUX", task: "images", match: "flux", summary: "Image generation and editing", tags: ["Image generation", "Image editing"], description: "Choose FLUX.1, FLUX.2 or FLUX.3 Base. FLUX.3 and Fibo share the Qwen3-VL-4B encoder; FLUX.3 uses the FLUX.2 VAE.", training: true, editing: true, components: ["qwen3vl-4b-int8"] },
  { id: "sdxl", title: "SDXL", task: "images", summary: "A familiar starting point", tags: ["Image generation", "LoRA training"], description: "Explore base models, refiners and community checkpoints.", training: true },
  { id: "zimage", title: "Z-Image Turbo", task: "images", match: "z-image", summary: "Fast image generation", tags: ["Image generation"], description: "Find the diffusion model, text encoder and VAE." },
  { id: "qwen", title: "Qwen Image", task: "images", match: "qwen-image", summary: "Image generation and instruction editing", tags: ["Image generation", "Image editing", "LoRA training"], description: "Includes Qwen-Image 2.1 and Turbo with their own encoder and RGBA VAE. Turbo training needs its adapter.", training: true, editing: true },
  { id: "ming", title: "Ming-Image", task: "images", match: "ming-image", summary: "Design and image generation", tags: ["Image generation", "LoRA training"], description: "Design 0.1 with Ling Mini 2.0, an RGBA VAE and its training adapter.", training: true },
  { id: "moss", title: "MOSS-Image", task: "images", match: "moss-image", summary: "Base and SFT image models", tags: ["Image generation", "Image editing", "LoRA training"], description: "Uses Qwen3.5-9B and the small FLUX.2 VAE. Edit LoRAs require the separate ComfyUI-MOSS-Image-Ostris-Edit extension.", training: true, editing: true },
  { id: "fibo", title: "Fibo 2.0", task: "images", match: "fibo2", summary: "Image generation and editing", tags: ["Image generation", "Image editing", "LoRA training"], description: "Dev model with the shared Qwen3-VL-4B encoder and FLUX.2 VAE.", training: true, editing: true, components: ["qwen3vl-4b-int8", "flux2-vae"] },
  { id: "iris", title: "Iris-3B", task: "images", match: "iris3b", summary: "Pixel-space image generation", tags: ["Image generation", "LoRA training"], description: "Base checkpoint and Qwen3-VL-4B encoder. This pixel-space model does not use a VAE.", training: true },
  { id: "ph3", title: "Pruna P-H3-Image", task: "images", match: "p-h3-image", summary: "Eight-step images and edits", tags: ["Image generation", "Image editing", "LoRA training"], description: "Uses its own image encoder and VAE. Training requires the P-H3 adapter; H3 video components are not substitutes.", training: true, editing: true },
  { id: "yue2", title: "YuE2", task: "audio", match: "yue2", summary: "Music and audio LoRA training", tags: ["Audio generation", "LoRA training"], description: "Comfy repack with embedded tokenizer and VAE, community semantic tokenizer, MERT and optional SheetSage score conditioning. Use AI Toolkit for training.", training: true },
  { id: "anima", title: "Anima", task: "images", match: "anima", summary: "Illustration and LoRA training", tags: ["Image generation", "LoRA training"], description: "Find the base model, Qwen3 encoder and Qwen-Image VAE.", training: true },
  { id: "lumina2", title: "Lumina-Image 2.0", task: "images", match: "lumina2", summary: "Image generation and LoRA training", tags: ["Image generation", "LoRA training"], description: "Find the diffusion model and Gemma 2 encoder. Uses the shared FLUX autoencoder.", training: true },
  { id: "hunyuanimage", title: "HunyuanImage", task: "images", match: "hunyuanimage", summary: "Image generation", tags: ["Image generation"], description: "Choose a model pack or ComfyUI components." },
  { id: "ideogram", title: "Ideogram", task: "images", match: "ideogram", summary: "Image generation", tags: ["Image generation"], description: "Browse diffusion models and text encoders." },
  { id: "lens", title: "Lens", task: "images", match: "lens", summary: "Image generation", tags: ["Image generation"], description: "Find the model and its text encoder." },
  { id: "pixeldit", title: "PixelDiT", task: "images", match: "pixeldit", summary: "Image generation and upscaling", tags: ["Image generation", "Upscaling"], description: "Browse PixelDiT models and supporting components." },
  { id: "sd15", title: "Stable Diffusion 1.5", task: "images", summary: "Classic image checkpoints", tags: ["Image generation", "LoRA training"], description: "Browse SD1.5 base and community models.", training: true },
  { id: "sd3", title: "Stable Diffusion 3", task: "images", match: "sd3", summary: "SD3 and SD3.5", tags: ["Image generation"], description: "Choose a checkpoint and review its access requirements." },
  { id: "components", title: "Shared components", task: "components", summary: "The rest of your toolkit", tags: ["Encoders", "VAEs", "Upscalers"], description: "Find individual components and custom manifest entries." },
];

window.modelFamilyFor = function (model) {
  const name = model.name.toLowerCase();
  const direct = window.modelFamilies.find(f => f.match && name.startsWith(f.match));
  if (direct) return direct;
  if (name.startsWith("fasth3")) return window.modelFamilies.find(f => f.id === "minimax");
  if (name.startsWith("pid-flux2")) return window.modelFamilies.find(f => f.id === "pixeldit");
  if (["sd15-base", "realistic-vision", "realistic-vision-xl", "realistic-vision-v6-sd15", "epicrealism", "rev-animated", "toonyou"].includes(name)) {
    return window.modelFamilies.find(f => f.id === "sd15");
  }
  if (model.category === "SDXL") return window.modelFamilies.find(f => f.id === "sdxl");
  return window.modelFamilies.find(f => f.id === "components");
};
