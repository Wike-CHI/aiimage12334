import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface ImageMetadata {
  width?: number;
  height?: number;
  mimeType: string;
  createdAt: number;
  type: 'upload' | 'task';
}

interface ImageCacheEntry {
  key: string;
  blob: Blob;
  metadata: ImageMetadata;
}

interface ImageCacheDB extends DBSchema {
  images: {
    key: string;
    value: ImageCacheEntry;
    indexes: { 'by-type': string; 'by-created': number };
  };
}

const DB_NAME = 'image-cache-db';
const DB_VERSION = 1;
const MAX_ENTRIES = 50;

let dbInstance: IDBPDatabase<ImageCacheDB> | null = null;

async function getDB(): Promise<IDBPDatabase<ImageCacheDB>> {
  if (dbInstance) return dbInstance;

  dbInstance = await openDB<ImageCacheDB>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      const store = db.createObjectStore('images', { keyPath: 'key' });
      store.createIndex('by-type', 'metadata.type');
      store.createIndex('by-created', 'metadata.createdAt');
    },
  });

  return dbInstance;
}

/**
 * Save an image to IndexedDB cache
 */
export async function saveImage(
  key: string,
  blob: Blob,
  metadata: Omit<ImageMetadata, 'createdAt'>
): Promise<void> {
  const db = await getDB();

  // Check if we need to clean up old entries
  await cleanupIfNeeded(db);

  await db.put('images', {
    key,
    blob,
    metadata: {
      ...metadata,
      createdAt: Date.now(),
    },
  });
}

/**
 * Get an image from cache
 */
export async function getImage(key: string): Promise<Blob | null> {
  const db = await getDB();
  const entry = await db.get('images', key);
  return entry?.blob ?? null;
}

/**
 * Get image with metadata
 */
export async function getImageWithMetadata(key: string): Promise<ImageCacheEntry | null> {
  const db = await getDB();
  return (await db.get('images', key)) ?? null;
}

/**
 * Get the data URL for an image (for img src)
 */
export async function getImageDataURL(key: string): Promise<string | null> {
  const blob = await getImage(key);
  if (!blob) return null;

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Get blob URL for an image (for img src, more efficient)
 */
export async function getImageBlobURL(key: string): Promise<string | null> {
  const blob = await getImage(key);
  if (!blob) return null;
  return URL.createObjectURL(blob);
}

/**
 * Delete an image from cache
 */
export async function deleteImage(key: string): Promise<void> {
  const db = await getDB();
  await db.delete('images', key);
}

/**
 * Clear all cached images
 */
export async function clearCache(): Promise<void> {
  const db = await getDB();
  await db.clear('images');
}

/**
 * Get all cached images
 */
export async function getAllImages(): Promise<ImageCacheEntry[]> {
  const db = await getDB();
  return await db.getAll('images');
}

/**
 * Check if an image is cached
 */
export async function isCached(key: string): Promise<boolean> {
  const db = await getDB();
  const entry = await db.get('images', key);
  return entry !== undefined;
}

/**
 * Get cache size (number of entries)
 */
export async function getCacheSize(): Promise<number> {
  const db = await getDB();
  return await db.count('images');
}

/**
 * Clean up old entries if we exceed the max limit (LRU-like)
 */
async function cleanupIfNeeded(db: IDBPDatabase<ImageCacheDB>): Promise<void> {
  const count = await db.count('images');
  if (count < MAX_ENTRIES) return;

  // Get all entries ordered by creation time
  const allEntries = await db.getAllFromIndex('images', 'by-created');

  // Delete oldest entries until we're under the limit
  const toDelete = count - MAX_ENTRIES + 10; // Delete extra to avoid frequent cleanup
  const oldestKeys = allEntries.slice(0, toDelete).map((e) => e.key);

  const tx = db.transaction('images', 'readwrite');
  await Promise.all([
    ...oldestKeys.map((key) => tx.store.delete(key)),
    tx.done,
  ]);
}

/**
 * Cleanup images by type
 */
export async function cleanupByType(type: 'upload' | 'task'): Promise<void> {
  const db = await getDB();
  const entries = await db.getAllFromIndex('images', 'by-type', type);

  const tx = db.transaction('images', 'readwrite');
  await Promise.all([
    ...entries.map((entry) => tx.store.delete(entry.key)),
    tx.done,
  ]);
}
