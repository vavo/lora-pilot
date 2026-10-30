/* One private browser draft. Workspace files change only when the user saves. */
function createTagPilotDraftStore() {
    let database, files = new Map(), queue = Promise.resolve();
    const completed = transaction => new Promise((resolve, reject) => {
        transaction.oncomplete = resolve;
        transaction.onabort = () => reject(transaction.error || new Error('Browser draft could not be saved.'));
        transaction.onerror = () => {}; // onabort reports the final transaction failure.
    });
    const value = request => new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
    return {
        async open() {
            if (!navigator.locks) throw new Error('Draft recovery needs a secure browser connection (HTTPS or localhost).');
            await new Promise((resolve, reject) => {
                navigator.locks.request('tagpilot-draft', {ifAvailable: true}, lock => {
                    if (!lock) { reject(new Error('Another TagPilot tab is using draft recovery. Close it, then reload.')); return; }
                    resolve();
                    return new Promise(() => {}); // Released automatically when this page closes.
                }).catch(reject);
            });
            const request = indexedDB.open('tagpilot-draft', 1);
            request.onupgradeneeded = () => {
                request.result.createObjectStore('draft');
                request.result.createObjectStore('images');
            };
            database = await value(request);
            const draft = await value(database.transaction('draft').objectStore('draft').get('current'));
            if (!draft) return null;
            const images = database.transaction('images').objectStore('images');
            draft.items = await Promise.all(draft.items.map(async item => {
                const file = await value(images.get(item.id));
                if (!file) throw new Error('The browser draft is incomplete. Open your saved dataset instead.');
                files.set(item.id, file);
                return {...item, file};
            }));
            return draft;
        },
        save(snapshot) {
            // Capture text now; a queued write must not pick up later edits or batch progress.
            const items = snapshot.items.map(({id, tags, type, file}) => ({id, tags, type, file}));
            const metadata = structuredClone({...snapshot, items: items.map(({file, ...item}) => item)});
            queue = queue.catch(() => {}).then(async () => {
                const transaction = database.transaction(['draft', 'images'], 'readwrite');
                const done = completed(transaction), images = transaction.objectStore('images');
                const next = new Map(items.map(item => [item.id, item.file]));
                for (const id of files.keys()) if (!next.has(id)) images.delete(id);
                for (const item of items) if (files.get(item.id) !== item.file) images.put(item.file, item.id);
                transaction.objectStore('draft').put(metadata, 'current');
                await done;
                files = next;
            });
            return queue;
        }
    };
}
