// Display metadata only. Downloads and installed state come from the manifest API.
window.modelFamilies = [
  { id: "ltx25", title: "LTX-2.5", task: "video", match: "ltx-2.5", summary: "Fast video iteration", tags: ["Text to video", "Image to video"], description: "Start with the bundled video workflow.", workflow: "video_ltx2_5_t2v.json" },
  { id: "minimax", title: "MiniMax H3", task: "video", match: "minimax-h3", summary: "Video with synchronized sound", tags: ["Text to video", "Image to video"], description: "Set up the components for the bundled H3 workflows.", workflow: "video_minimax_h3_t2v.json" },
  { id: "ltx23", title: "LTX-2.3", task: "video", match: "ltx-2.3", summary: "Video models and adapters", tags: ["Video generation", "LoRAs"], description: "Browse checkpoints, distilled variants and upscalers." },
  { id: "wan", title: "Wan", task: "video", match: "wan", summary: "Video and character animation", tags: ["Video generation", "Animation"], description: "Choose a model for your Wan workflow." },
  { id: "hunyuanvideo", title: "HunyuanVideo", task: "video", match: "hunyuan-video", summary: "Text to video", tags: ["Video generation"], description: "Browse video checkpoints and the accompanying VAE." },
  { id: "flux", title: "FLUX", task: "images", match: "flux", summary: "Image generation and editing", tags: ["Image generation", "Image editing"], description: "Choose a generation, Fill or Kontext model and its components.", training: true, editing: true },
  { id: "sdxl", title: "SDXL", task: "images", summary: "A familiar starting point", tags: ["Image generation", "LoRA training"], description: "Explore base models, refiners and community checkpoints.", training: true },
  { id: "zimage", title: "Z-Image Turbo", task: "images", match: "z-image", summary: "Fast image generation", tags: ["Image generation"], description: "Find the diffusion model, text encoder and VAE." },
  { id: "qwen", title: "Qwen Image", task: "editing", match: "qwen-image", summary: "Edit images with instructions", tags: ["Image editing"], description: "Browse the image editing models in your catalog.", editing: true },
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
  if (name.startsWith("pid-flux2")) return window.modelFamilies.find(f => f.id === "pixeldit");
  if (["sd15-base", "realistic-vision", "realistic-vision-xl", "realistic-vision-v6-sd15", "epicrealism", "rev-animated", "toonyou"].includes(name)) {
    return window.modelFamilies.find(f => f.id === "sd15");
  }
  if (model.category === "SDXL") return window.modelFamilies.find(f => f.id === "sdxl");
  return window.modelFamilies.find(f => f.id === "components");
};
