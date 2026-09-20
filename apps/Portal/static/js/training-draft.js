/* Store only unfinished form choices, never configuration text or credentials. */
function createTrainingDraft(storage) {
  const key = 'lora-pilot.training-draft.v1';
  function clean(value) {
    if (!value || value.version !== 1 || !['sdxl', 'flux1'].includes(value.family) ||
        !['quick_test', 'regular', 'high_quality'].includes(value.profile) ||
        typeof value.dataset_name !== 'string' || value.dataset_name.length > 255 ||
        typeof value.output_name !== 'string' || value.output_name.length > 80) return null;
    return {version: 1, family: value.family, profile: value.profile,
      dataset_name: value.dataset_name, output_name: value.output_name,
      source_run_id: /^[a-f0-9]{32}$/.test(value.source_run_id || '') ? value.source_run_id : null};
  }
  return {
    read() { return clean(JSON.parse(storage.getItem(key))); },
    save(value) { const draft = clean({...value, version: 1}); if (draft) storage.setItem(key, JSON.stringify(draft)); },
    clear() { storage.removeItem(key); },
  };
}
