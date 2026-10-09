/* Store only unfinished form choices, never configuration text or credentials. */
function createTrainingDraft(storage) {
  const key = 'lora-pilot.training-draft.v1';
  function clean(value) {
    if (!value || value.version !== 1 || !['sdxl', 'flux1', 'sd15', 'sd35_medium', 'sd35_large', 'anima', 'lumina2', 'hunyuan_image21'].includes(value.family) ||
        !['quick_test', 'regular', 'high_quality'].includes(value.profile) ||
        typeof value.dataset_name !== 'string' || value.dataset_name.length > 255 ||
        typeof value.output_name !== 'string' || value.output_name.length > 80) return null;
    const hardware = {};
    for (const [key, [min, max]] of Object.entries({train_batch_size:[1,8], gradient_accumulation_steps:[1,16], network_dim:[4,128], blocks_to_swap:[0,35]})) {
      const number = value.hardware?.[key];
      if (Number.isInteger(number) && number >= min && number <= max) hardware[key] = number;
    }
    return {version: 1, family: value.family, profile: value.profile, hardware,
      dataset_name: value.dataset_name, output_name: value.output_name,
      base_model: typeof value.base_model === 'string' && /^[a-z0-9.-]{0,100}$/.test(value.base_model) ? value.base_model : '',
      source_run_id: /^[a-f0-9]{32}$/.test(value.source_run_id || '') ? value.source_run_id : null};
  }
  return {
    read() { return clean(JSON.parse(storage.getItem(key))); },
    save(value) { const draft = clean({...value, version: 1}); if (draft) storage.setItem(key, JSON.stringify(draft)); },
    clear() { storage.removeItem(key); },
  };
}
