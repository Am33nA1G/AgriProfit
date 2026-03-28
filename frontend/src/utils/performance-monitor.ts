interface APICall {
  endpoint: string;
  duration: number;
  timestamp: number;
  status: number;
}

interface PerformanceReport {
  pageLoadTime: number | null;
  apiCalls: APICall[];
  slowQueries: APICall[];
  totalAPIDuration: number;
  longestCall: APICall | null;
}

const SLOW_THRESHOLD_MS = 500;
const ENABLED = process.env.NEXT_PUBLIC_PERF_MONITOR === 'true' || process.env.NODE_ENV === 'development';

class PerformanceMonitor {
  private calls: APICall[] = [];
  private pageLoadStart: number = 0;
  private pageLoadEnd: number = 0;

  startPageLoad(): void {
    if (!ENABLED) return;
    this.calls = [];
    this.pageLoadStart = performance.now();
    this.pageLoadEnd = 0;
  }

  recordAPI(endpoint: string, duration: number, status: number): void {
    if (!ENABLED) return;
    const call: APICall = {
      endpoint,
      duration,
      timestamp: Date.now(),
      status,
    };
    this.calls.push(call);

    if (duration > SLOW_THRESHOLD_MS) {
      console.warn(`[Perf] SLOW API: ${endpoint} took ${duration.toFixed(0)}ms (status ${status})`);
    }
  }

  endPageLoad(): void {
    if (!ENABLED) return;
    this.pageLoadEnd = performance.now();
    this.logReport();
  }

  getReport(): PerformanceReport {
    const slowQueries = this.calls.filter(c => c.duration > SLOW_THRESHOLD_MS);
    const totalAPIDuration = this.calls.reduce((sum, c) => sum + c.duration, 0);
    const longestCall = this.calls.length
      ? this.calls.reduce((a, b) => (a.duration > b.duration ? a : b))
      : null;

    return {
      pageLoadTime: this.pageLoadEnd ? this.pageLoadEnd - this.pageLoadStart : null,
      apiCalls: [...this.calls],
      slowQueries,
      totalAPIDuration,
      longestCall,
    };
  }

  private logReport(): void {
    const report = this.getReport();
    const pageTime = report.pageLoadTime?.toFixed(0) ?? '?';
    const status = (report.pageLoadTime ?? 0) < 2000 ? '\u2705' : '\u26a0\ufe0f';

    console.groupCollapsed(`[Perf] ${status} Page loaded in ${pageTime}ms (${this.calls.length} API calls)`);
    for (const call of this.calls) {
      const icon = call.duration > SLOW_THRESHOLD_MS ? '\u26a0\ufe0f' : '\u2705';
      console.log(`  ${icon} ${call.endpoint}: ${call.duration.toFixed(0)}ms`);
    }
    if (report.slowQueries.length > 0) {
      console.warn(`  ${report.slowQueries.length} slow queries (>${SLOW_THRESHOLD_MS}ms)`);
    }
    console.groupEnd();
  }

  reset(): void {
    this.calls = [];
    this.pageLoadStart = 0;
    this.pageLoadEnd = 0;
  }
}

export const perfMonitor = new PerformanceMonitor();
export type { APICall, PerformanceReport };
