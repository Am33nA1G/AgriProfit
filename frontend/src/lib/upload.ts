import api from '@/lib/api';

// Supported image types
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];

// Max file size: 5MB
const MAX_FILE_SIZE = 5 * 1024 * 1024;

export interface UploadResult {
    url: string;
    filename: string;
}

export interface UploadError {
    code: 'INVALID_TYPE' | 'FILE_TOO_LARGE' | 'UPLOAD_FAILED' | 'NETWORK_ERROR';
    message: string;
}

/**
 * Validate image file before upload
 */
export function validateImageFile(file: File): UploadError | null {
    // Check file type
    if (!ALLOWED_TYPES.includes(file.type)) {
        return {
            code: 'INVALID_TYPE',
            message: `Invalid file type. Allowed types: ${ALLOWED_EXTENSIONS.join(', ')}`,
        };
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        return {
            code: 'FILE_TOO_LARGE',
            message: `File too large (${sizeMB}MB). Maximum size is 5MB.`,
        };
    }

    return null;
}

/**
 * Create a preview URL for an image file
 * Remember to revoke this URL when done using URL.revokeObjectURL()
 */
export function createImagePreview(file: File): string {
    return URL.createObjectURL(file);
}

/**
 * Revoke a preview URL to free memory
 */
export function revokeImagePreview(previewUrl: string): void {
    URL.revokeObjectURL(previewUrl);
}

/**
 * Upload an image file to the server
 *
 * @param file - The image file to upload
 * @returns Promise with the uploaded image URL
 * @throws UploadError if validation fails or upload fails
 *
 * NOTE: Backend endpoint /uploads/image needs to be implemented.
 * Expected backend behavior:
 * - Accept multipart/form-data with 'file' field
 * - Validate file type and size
 * - Store file (local storage or cloud like S3)
 * - Return { url: string, filename: string }
 */
export async function uploadImage(file: File): Promise<string> {
    // Validate file
    const validationError = validateImageFile(file);
    if (validationError) {
        throw validationError;
    }

    // Create FormData
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await api.post('/uploads/image', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        // Expected response: { url: string, filename: string }
        if (response.data?.url) {
            return response.data.url;
        }

        throw {
            code: 'UPLOAD_FAILED',
            message: 'Upload succeeded but no URL returned',
        } as UploadError;
    } catch (error: any) {
        // Check if it's already an UploadError
        if (error.code && error.message) {
            throw error;
        }

        // Handle axios errors
        if (error.response) {
            // Server responded with error
            const status = error.response.status;
            const detail = error.response.data?.detail || 'Upload failed';

            if (status === 413) {
                throw {
                    code: 'FILE_TOO_LARGE',
                    message: 'File too large for server',
                } as UploadError;
            }

            if (status === 415) {
                throw {
                    code: 'INVALID_TYPE',
                    message: 'File type not supported by server',
                } as UploadError;
            }

            throw {
                code: 'UPLOAD_FAILED',
                message: detail,
            } as UploadError;
        }

        if (error.request) {
            // Network error
            throw {
                code: 'NETWORK_ERROR',
                message: 'Network error. Please check your connection.',
            } as UploadError;
        }

        // Unknown error
        throw {
            code: 'UPLOAD_FAILED',
            message: error.message || 'Unknown upload error',
        } as UploadError;
    }
}

/**
 * Upload image with progress callback
 */
export async function uploadImageWithProgress(
    file: File,
    onProgress: (percent: number) => void
): Promise<string> {
    // Validate file
    const validationError = validateImageFile(file);
    if (validationError) {
        throw validationError;
    }

    // Create FormData
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await api.post('/uploads/image', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent) => {
                if (progressEvent.total) {
                    const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(percent);
                }
            },
        });

        if (response.data?.url) {
            return response.data.url;
        }

        throw {
            code: 'UPLOAD_FAILED',
            message: 'Upload succeeded but no URL returned',
        } as UploadError;
    } catch (error: any) {
        if (error.code && error.message) {
            throw error;
        }

        throw {
            code: 'UPLOAD_FAILED',
            message: error.message || 'Upload failed',
        } as UploadError;
    }
}

/**
 * Check if a URL is a valid image URL
 */
export function isValidImageUrl(url: string): boolean {
    if (!url) return false;

    try {
        const urlObj = new URL(url);
        const pathname = urlObj.pathname.toLowerCase();
        return ALLOWED_EXTENSIONS.some(ext => pathname.endsWith(ext));
    } catch {
        return false;
    }
}

/**
 * Get file extension from filename
 */
export function getFileExtension(filename: string): string {
    const lastDot = filename.lastIndexOf('.');
    if (lastDot === -1) return '';
    return filename.slice(lastDot).toLowerCase();
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
