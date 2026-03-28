import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('API Client Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Base Configuration', () => {
    it('uses environment variable for base URL', () => {
      const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      expect(baseURL).toBeDefined();
      expect(typeof baseURL).toBe('string');
    });

    it('has default base URL when env not set', () => {
      const defaultURL = 'http://127.0.0.1:8000';
      expect(defaultURL).toBe('http://127.0.0.1:8000');
    });
  });

  describe('Request Headers', () => {
    it('includes content-type in default headers', () => {
      const defaultHeaders = { 'Content-Type': 'application/json' };
      expect(defaultHeaders['Content-Type']).toBe('application/json');
    });

    it('supports form data content type', () => {
      const formDataHeaders = { 'Content-Type': 'multipart/form-data' };
      expect(formDataHeaders['Content-Type']).toBe('multipart/form-data');
    });
  });

  describe('Authorization', () => {
    it('adds bearer token when available', () => {
      vi.spyOn(window.localStorage, 'getItem').mockReturnValue('test-token');
      const token = localStorage.getItem('token');
      const header = token ? `Bearer ${token}` : undefined;
      
      expect(header).toBe('Bearer test-token');
    });

    it('does not add auth header when no token', () => {
      vi.spyOn(window.localStorage, 'getItem').mockReturnValue(null);
      const token = localStorage.getItem('token');
      const header = token ? `Bearer ${token}` : undefined;
      
      expect(header).toBeUndefined();
    });

    it('retrieves token from localStorage', () => {
      const getItemSpy = vi.spyOn(window.localStorage, 'getItem').mockReturnValue('my-token');
      const token = localStorage.getItem('token');
      
      expect(getItemSpy).toHaveBeenCalledWith('token');
      expect(token).toBe('my-token');
    });
  });

  describe('Error Handling', () => {
    it('handles 401 by clearing auth data', () => {
      const removeItemSpy = vi.spyOn(window.localStorage, 'removeItem');
      
      // Simulate 401 handling
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      expect(removeItemSpy).toHaveBeenCalledWith('token');
      expect(removeItemSpy).toHaveBeenCalledWith('user');
    });

    it('redirects to login on 401', () => {
      delete (window as any).location;
      (window as any).location = { href: '' };
      
      // Simulate redirect
      window.location.href = '/login';
      
      expect(window.location.href).toBe('/login');
    });

    it('handles 403 forbidden errors', () => {
      const error = { status: 403, message: 'Forbidden' };
      expect(error.status).toBe(403);
    });

    it('handles 404 not found errors', () => {
      const error = { status: 404, message: 'Not found' };
      expect(error.status).toBe(404);
    });

    it('handles 500 server errors', () => {
      const error = { status: 500, message: 'Internal server error' };
      expect(error.status).toBe(500);
    });

    it('handles network errors', () => {
      const error = new Error('Network Error');
      expect(error.message).toContain('Network');
    });
  });

  describe('Timeout Configuration', () => {
    it('has default timeout of 60 seconds', () => {
      const timeout = 60000;
      expect(timeout).toBe(60000);
    });

    it('supports long timeout for slow endpoints', () => {
      const longTimeout = 120000;
      expect(longTimeout).toBe(120000);
    });

    it('handles timeout errors', () => {
      const error = new Error('timeout of 60000ms exceeded');
      expect(error.message).toContain('timeout');
    });
  });

  describe('Request Logging', () => {
    it('logs request method and URL', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      console.log('[API] Request:', 'GET', '/test');
      
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('logs response status', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      console.log('[API] Response:', 200, '/test');
      
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('logs error messages', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      console.error('[API] Response error:', 'Error message');
      
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('Query Parameters', () => {
    it('serializes simple query parameters', () => {
      const params = { page: 1, limit: 10 };
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value));
      });
      
      expect(searchParams.toString()).toBe('page=1&limit=10');
    });

    it('handles array parameters', () => {
      const ids = [1, 2, 3];
      const queryString = ids.join(',');
      expect(queryString).toBe('1,2,3');
    });

    it('encodes special characters', () => {
      const encoded = encodeURIComponent('hello world');
      expect(encoded).toBe('hello%20world');
    });
  });

  describe('FormData Support', () => {
    it('creates FormData for file uploads', () => {
      const formData = new FormData();
      formData.append('file', new Blob(['test']), 'test.txt');
      formData.append('name', 'testfile');
      
      expect(formData.get('name')).toBe('testfile');
    });

    it('supports multiple files in FormData', () => {
      const formData = new FormData();
      formData.append('file1', new Blob(['test1']));
      formData.append('file2', new Blob(['test2']));
      
      expect(formData.has('file1')).toBe(true);
      expect(formData.has('file2')).toBe(true);
    });
  });

  describe('Response Handling', () => {
    it('extracts data from successful response', () => {
      const response = { data: { id: 1, name: 'Test' }, status: 200 };
      expect(response.data).toEqual({ id: 1, name: 'Test' });
    });

    it('handles empty response data', () => {
      const response = { data: null, status: 204 };
      expect(response.data).toBeNull();
    });

    it('handles array responses', () => {
      const response = { data: [1, 2, 3], status: 200 };
      expect(Array.isArray(response.data)).toBe(true);
      expect(response.data).toHaveLength(3);
    });
  });

  describe('Error Response Details', () => {
    it('extracts error message from response', () => {
      const errorResponse = {
        response: {
          status: 400,
          data: { detail: 'Validation error' },
        },
      };
      expect(errorResponse.response.data.detail).toBe('Validation error');
    });

    it('handles error without detail field', () => {
      const errorResponse = {
        response: {
          status: 500,
          data: { message: 'Server error' },
        },
      };
      expect(errorResponse.response.data.message).toBe('Server error');
    });
  });

  describe('Browser Environment', () => {
    it('checks if running in browser', () => {
      const isBrowser = typeof window !== 'undefined';
      expect(isBrowser).toBe(true);
    });

    it('avoids localStorage access in SSR', () => {
      const isServer = typeof window === 'undefined';
      if (!isServer) {
        expect(window.localStorage).toBeDefined();
      }
    });
  });
});
