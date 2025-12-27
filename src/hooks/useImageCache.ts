import { useState, useEffect, useCallback } from 'react';
import {
  saveImage,
  getImage,
  getImageDataURL,
  deleteImage,
  clearCache,
  isCached,
  getCacheSize,
  getAllImages,
  type ImageMetadata,
} from '@/lib/image-cache';

interface UseImageCacheOptions {
  type: 'upload' | 'task';
  autoLoad?: boolean;
}

interface UseImageCacheReturn {
  cacheImage: (key: string, blob: Blob, metadata?: Partial<ImageMetadata>) => Promise<void>;
  getCachedImage: (key: string) => Promise<string | null>;
  removeCachedImage: (key: string) => Promise<void>;
  clearAll: () => Promise<void>;
  isImageCached: (key: string) => Promise<boolean>;
  cacheSize: number;
  getAllCached: () => Promise<Array<{ key: string; url: string; metadata?: ImageMetadata }>>;
}

export function useImageCache(options: UseImageCacheOptions): UseImageCacheReturn {
  const { type } = options;
  const [cacheSize, setCacheSize] = useState(0);

  // Update cache size on mount
  useEffect(() => {
    getCacheSize().then(setCacheSize);
  }, []);

  const cacheImage = useCallback(
    async (key: string, blob: Blob, metadata?: Partial<ImageMetadata>) => {
      await saveImage(key, blob, { ...metadata, mimeType: blob.type, type });
      const newSize = await getCacheSize();
      setCacheSize(newSize);
    },
    [type]
  );

  const getCachedImage = useCallback(async (key: string): Promise<string | null> => {
    return await getImageDataURL(key);
  }, []);

  const removeCachedImage = useCallback(async (key: string) => {
    await deleteImage(key);
    const newSize = await getCacheSize();
    setCacheSize(newSize);
  }, []);

  const clearAll = useCallback(async () => {
    await clearCache();
    setCacheSize(0);
  }, []);

  const isImageCached = useCallback(async (key: string): Promise<boolean> => {
    return await isCached(key);
  }, []);

  const getAllCached = useCallback(async () => {
    const entries = await getAllImages();
    const result: Array<{ key: string; url: string; metadata?: ImageMetadata }> = [];

    for (const entry of entries) {
      const url = await getImageDataURL(entry.key);
      if (url) {
        result.push({
          key: entry.key,
          url,
          metadata: entry.metadata,
        });
      }
    }

    return result;
  }, []);

  return {
    cacheImage,
    getCachedImage,
    removeCachedImage,
    clearAll,
    isImageCached,
    cacheSize,
    getAllCached,
  };
}

/**
 * Hook for caching uploaded images
 */
export function useUploadImageCache() {
  const cache = useImageCache({ type: 'upload' });

  const cacheUpload = useCallback(
    async (file: File, customKey?: string) => {
      const key = customKey || `upload:${file.name}:${Date.now()}`;
      await cache.cacheImage(key, file, { mimeType: file.type });
      return key;
    },
    [cache]
  );

  return { ...cache, cacheUpload };
}

/**
 * Hook for caching task result images
 */
export function useTaskImageCache() {
  const cache = useImageCache({ type: 'task' });

  const cacheTaskImage = useCallback(
    async (taskId: number, blob: Blob, width?: number, height?: number) => {
      const key = `task:${taskId}`;
      await cache.cacheImage(key, blob, { width, height, mimeType: 'image/png' });
      return key;
    },
    [cache]
  );

  return { ...cache, cacheTaskImage };
}
