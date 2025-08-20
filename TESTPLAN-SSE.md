# Test Plan - SSE Monitor Implementation

**Version**: 1.0  
**Date**: 2025-01-20  
**Test Target**: EAA Scanner SSE Real-time Monitor  
**Environments**: Development, Staging  

## Test Objectives

Verificare che il sistema SSE monitor:
1. ✅ Mostri eventi live entro 15s dall'avvio scansione
2. ✅ Non salti al report senza evento terminale `scan_complete`
3. ✅ Garantisca idempotenza (no stream duplicati, no memory leaks)
4. ✅ Implementi retry/backoff funzionanti e osservabili
5. ✅ Passi tutti i test E2E e lint

## Test Scope

### In Scope
- SSE connection establishment e retry logic
- Event handling e UI updates in real-time
- Resource cleanup e memory management  
- Fallback da SSE a polling
- Error handling e recovery scenarios
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)

### Out of Scope
- Backend SSE event generation (assumed working)
- Server-side performance testing
- Mobile browser testing (future iteration)
- Accessibility testing del monitor (separate test plan)

## Test Categories

## 1. **UNIT TESTS**

### 1.1 SSE Connection Management
```javascript
describe('SSE Connection', () => {
  test('should initialize SSE monitor with valid scan_id', () => {
    const monitor = new ScanMonitor('test_123', 'test-container');
    expect(monitor.scanId).toBe('test_123');
    expect(monitor.isConnected).toBe(false);
  });

  test('should establish EventSource connection', () => {
    const monitor = new ScanMonitor('test_123', 'test-container');
    monitor.connect();
    expect(monitor.eventSource).toBeDefined();
    expect(monitor.eventSource.url).toContain('/api/scan/stream/test_123');
  });

  test('should handle connection success', () => {
    const monitor = new ScanMonitor('test_123', 'test-container');
    const spy = jest.spyOn(monitor, 'updateConnectionStatus');
    
    monitor.eventSource.onopen();
    
    expect(monitor.isConnected).toBe(true);
    expect(spy).toHaveBeenCalledWith('connected');
  });
});
```

### 1.2 Exponential Backoff Logic
```javascript
describe('Retry Logic', () => {
  test('should calculate exponential backoff correctly', () => {
    const monitor = new ScanMonitor('test_123', 'test-container');
    
    // Test sequence: 1s, 2s, 4s, 8s, 16s, 30s (max)
    expect(monitor.calculateBackoffDelay(1)).toBe(1000);
    expect(monitor.calculateBackoffDelay(2)).toBe(2000);
    expect(monitor.calculateBackoffDelay(3)).toBe(4000);
    expect(monitor.calculateBackoffDelay(4)).toBe(8000);
    expect(monitor.calculateBackoffDelay(5)).toBe(16000);
    expect(monitor.calculateBackoffDelay(6)).toBe(30000);
    expect(monitor.calculateBackoffDelay(7)).toBe(30000); // capped
  });

  test('should stop retrying after max attempts', () => {
    const monitor = new ScanMonitor('test_123', 'test-container');
    monitor.reconnectAttempts = 8;
    
    const spy = jest.spyOn(monitor, 'showCriticalError');
    monitor.handleConnectionError();
    
    expect(spy).toHaveBeenCalled();
  });
});
```

### 1.3 Event Handling
```javascript
describe('Event Processing', () => {
  test('should handle scan_start event', () => {
    const scanner = new EAAScannerV2();
    const eventData = {
      event_type: 'scan_start',
      data: { company_name: 'Test Co', url: 'https://test.com' }
    };
    
    const spy = jest.spyOn(scanner, 'showNotification');
    scanner.handleSSEEvent(eventData);
    
    expect(spy).toHaveBeenCalledWith('🚀 Avvio scansione: Test Co', 'info');
  });

  test('should handle page_progress event', () => {
    const scanner = new EAAScannerV2();
    const eventData = {
      event_type: 'page_progress',
      data: { current_page: 2, total_pages: 5, progress_percent: 40 }
    };
    
    const spy = jest.spyOn(scanner, 'updateMainProgress');
    scanner.handleSSEEvent(eventData);
    
    expect(spy).toHaveBeenCalledWith(40);
  });
});
```

### 1.4 Resource Cleanup
```javascript
describe('Resource Management', () => {
  test('should cleanup SSE on destroy', () => {
    const scanner = new EAAScannerV2();
    scanner.sseMonitor = { disconnect: jest.fn() };
    
    scanner.cleanupSSE();
    
    expect(scanner.sseMonitor.disconnect).toHaveBeenCalled();
    expect(scanner.sseMonitor).toBeNull();
    expect(scanner.sseConnected).toBe(false);
  });

  test('should prevent memory leaks on page unload', () => {
    const scanner = new EAAScannerV2();
    const cleanupSpy = jest.spyOn(scanner, 'cleanup');
    
    // Simulate page unload
    window.dispatchEvent(new Event('beforeunload'));
    
    expect(cleanupSpy).toHaveBeenCalled();
  });
});
```

## 2. **INTEGRATION TESTS**

### 2.1 SSE to UI Integration
```javascript
describe('SSE-UI Integration', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="scan-monitor"></div>
      <div class="progress-fill"></div>
      <span id="pages-progress"></span>
      <span id="errors-found">0</span>
    `;
  });

  test('should update UI on progress events', async () => {
    const scanner = new EAAScannerV2();
    await scanner.initializeSSEMonitor();
    
    const progressEvent = {
      event_type: 'page_progress',
      data: { current_page: 3, total_pages: 10, progress_percent: 30 }
    };
    
    scanner.handleSSEEvent(progressEvent);
    
    expect(document.querySelector('.progress-fill').style.width).toBe('30%');
    expect(document.getElementById('pages-progress').textContent).toBe('3/10 pagine');
  });
});
```

### 2.2 Fallback Integration
```javascript
describe('SSE-Polling Fallback', () => {
  test('should activate polling when SSE fails', (done) => {
    const scanner = new EAAScannerV2();
    
    // Mock SSE failure
    scanner.sseConnected = false;
    
    const pollingSpy = jest.spyOn(scanner, 'startScanPolling');
    
    setTimeout(() => {
      scanner.sseFailure();
      expect(pollingSpy).toHaveBeenCalled();
      done();
    }, 100);
  });
});
```

## 3. **END-TO-END TESTS (Playwright)**

### 3.1 Happy Path - Complete Scan Flow
```javascript
test('should show real-time progress and complete successfully', async ({ page }) => {
  // Navigate to scanner
  await page.goto('/');
  
  // Setup scan configuration
  await page.fill('#url', 'https://principiadv.com');
  await page.fill('#company_name', 'Principia ADV');
  await page.fill('#email', 'test@example.com');
  
  // Start discovery
  await page.click('#start-discovery');
  
  // Wait for discovery to complete
  await page.waitForSelector('#phase-selection', { timeout: 30000 });
  
  // Select pages and start scan
  await page.click('#select-all-cb');
  await page.click('#start-scan');
  
  // Verify we're in scanning phase
  await page.waitForSelector('#phase-scanning.active', { timeout: 5000 });
  
  // Verify SSE monitor is visible
  const scanMonitor = page.locator('#scan-monitor');
  await expect(scanMonitor).toBeVisible();
  
  // Wait for progress updates (should appear within 15s)
  await page.waitForFunction(() => {
    const progressBar = document.querySelector('.progress-fill');
    return progressBar && progressBar.style.width !== '0%';
  }, { timeout: 15000 });
  
  // Verify progress elements are updating
  const progressBar = page.locator('.progress-fill');
  await expect(progressBar).not.toHaveAttribute('style', /width: 0%/);
  
  // Wait for scan completion (timeout 3 minutes)
  await page.waitForSelector('#phase-report.active', { 
    timeout: 180000,
    state: 'visible'
  });
  
  // Verify we reached report phase
  const reportPhase = page.locator('#phase-report');
  await expect(reportPhase).toHaveClass(/active/);
  
  // Verify no premature jumps occurred (scan monitor should have been visible)
  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push(msg.text()));
  
  expect(consoleLogs.some(log => 
    log.includes('SSE Event: scan_complete')
  )).toBe(true);
});
```

### 3.2 SSE Connection Failure Scenario
```javascript
test('should fallback to polling when SSE fails', async ({ page, context }) => {
  // Block SSE endpoint to simulate failure
  await context.route('/api/scan/stream/*', route => {
    route.abort();
  });
  
  await page.goto('/');
  
  // Setup and start scan
  await page.fill('#url', 'https://principiadv.com');
  await page.fill('#company_name', 'Test Company');
  await page.fill('#email', 'test@example.com');
  
  await page.click('#start-discovery');
  await page.waitForSelector('#phase-selection');
  
  await page.click('#select-all-cb');
  await page.click('#start-scan');
  
  // Verify fallback to polling occurs
  await page.waitForFunction(() => {
    return console.log.toString().includes('SSE failed to connect, falling back to polling');
  }, { timeout: 10000 });
  
  // Verify scan still progresses with polling
  await page.waitForSelector('#phase-report.active', { timeout: 180000 });
});
```

### 3.3 Network Interruption Recovery
```javascript
test('should recover from network interruption', async ({ page, context }) => {
  await page.goto('/');
  
  // Setup and start scan
  await setupScan(page);
  
  // Let scan start successfully
  await page.waitForSelector('#scan-monitor', { timeout: 5000 });
  
  // Simulate network interruption after 10 seconds
  await page.waitForTimeout(10000);
  
  // Block network temporarily
  await context.route('/api/scan/stream/*', route => route.abort());
  
  // Wait for retry attempts
  await page.waitForTimeout(5000);
  
  // Restore network
  await context.unroute('/api/scan/stream/*');
  
  // Verify scan continues and completes
  await page.waitForSelector('#phase-report.active', { timeout: 180000 });
});
```

## 4. **MANUAL TEST CASES**

### 4.1 Cross-Browser Compatibility
**Test Matrix**:
- Chrome 120+
- Firefox 115+  
- Safari 16+
- Edge 120+

**Procedure**:
1. Open EAA Scanner in each browser
2. Start scan with https://principiadv.com (3 pages)
3. Verify SSE connection establishes within 5s
4. Verify real-time progress updates
5. Verify completion and report transition

**Expected Result**: Consistent behavior across all browsers

### 4.2 Long-Running Scan Test
**Target**: Large website (10+ pages)
**Procedure**:
1. Configure scan for 10+ pages
2. Monitor memory usage in browser DevTools
3. Verify progress updates remain responsive
4. Check for memory leaks after completion

**Expected Result**: 
- Memory usage stable < 100MB growth
- Progress updates remain < 1s latency
- Cleanup successful (no lingering EventSource)

### 4.3 Concurrent Users Test
**Setup**: 5 simultaneous scans from different browser tabs
**Procedure**:
1. Open 5 tabs, each with different target URL
2. Start scans simultaneously
3. Monitor network tab for SSE connections
4. Verify each scan completes independently

**Expected Result**: All scans complete successfully without interference

## 5. **PERFORMANCE TESTS**

### 5.1 SSE vs Polling Comparison
```javascript
test('SSE should reduce network requests by 85%', async ({ page }) => {
  // Test polling version
  const pollingRequests = await measureNetworkRequests(page, 'polling');
  
  // Test SSE version  
  const sseRequests = await measureNetworkRequests(page, 'sse');
  
  const reduction = (pollingRequests - sseRequests) / pollingRequests;
  expect(reduction).toBeGreaterThan(0.8); // >80% reduction
});
```

### 5.2 Memory Leak Detection
```javascript
test('should not leak memory after scan completion', async ({ page }) => {
  // Measure baseline memory
  const baseline = await page.evaluate(() => performance.memory.usedJSHeapSize);
  
  // Run 3 complete scans
  for (let i = 0; i < 3; i++) {
    await runCompleteScan(page);
    await page.waitForTimeout(1000); // Let GC run
  }
  
  // Force garbage collection
  await page.evaluate(() => {
    if (window.gc) window.gc();
  });
  
  const final = await page.evaluate(() => performance.memory.usedJSHeapSize);
  const growth = final - baseline;
  
  // Should not grow by more than 10MB
  expect(growth).toBeLessThan(10 * 1024 * 1024);
});
```

## 6. **ERROR SCENARIOS**

### 6.1 Malformed SSE Events
**Test Data**: Invalid JSON, missing fields, wrong event types
**Procedure**: 
1. Mock SSE endpoint to send malformed events
2. Verify UI doesn't crash
3. Verify fallback mechanisms work

### 6.2 Server Errors
**Scenarios**: 
- SSE endpoint returns 500 error
- SSE connection drops mid-stream  
- Server sends duplicate events

**Expected Behavior**: Graceful degradation, user-friendly error messages

## 7. **ACCESSIBILITY TESTS**

### 7.1 Screen Reader Compatibility
**Tools**: NVDA, JAWS, VoiceOver
**Focus**: 
- Progress announcements
- Status updates
- Error messages

### 7.2 Keyboard Navigation
**Test**: Full scan flow using only keyboard
**Expected**: All interactive elements accessible via keyboard

## Test Data

### Primary Test URL
```
https://principiadv.com
```
**Rationale**: Real website, 3-4 pages, known performance characteristics

### Secondary Test URLs
```
https://example.com         (Simple site)
https://httpbin.org         (For error simulation)  
http://httpstat.us/500      (Server error simulation)
```

## Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **SSE Connection Time** | < 2s | Time to first event received |
| **Progress Visibility** | < 15s | Time to first progress update |
| **Update Latency** | < 500ms | Server event to UI update |
| **Memory Stability** | < 10MB growth | After 3 complete scans |
| **Network Efficiency** | 85% reduction | SSE vs polling requests |
| **Error Recovery** | < 30s | Max time to recover from connection drop |
| **Cross-Browser** | 100% | Success rate Chrome/Firefox/Safari/Edge |
| **Fallback Rate** | < 5% | Percentage requiring polling fallback |

## Test Environment Setup

### Prerequisites
```bash
# Install dependencies
npm install

# Start development server
npm run sse:dev

# Run lint
npm run sse:lint

# Run E2E tests
npm run sse:test:e2e
```

### Mock SSE Server (for testing)
```javascript
// test/mock-sse-server.js
const mockEvents = [
  { event_type: 'scan_start', data: { company_name: 'Test' } },
  { event_type: 'page_progress', data: { current_page: 1, total_pages: 3 } },
  // ... more events
];
```

## Debugging and Troubleshooting

### SSE Debug Checklist
1. ✅ Check browser Network tab for EventSource connection
2. ✅ Verify endpoint `/api/scan/stream/{scan_id}` returns 200
3. ✅ Check console for SSE connection messages
4. ✅ Verify scan_id matches between frontend and backend
5. ✅ Test manual curl connection: `curl -N -H "Accept: text/event-stream" http://localhost:8000/api/scan/stream/TEST123`

### Common Issues
- **CORS errors**: Check server CORS configuration
- **Connection refused**: Verify server running and port correct
- **Events not received**: Check event format and Content-Type headers
- **Memory leaks**: Verify EventSource.close() called on cleanup

---

**Test Plan Status**: ✅ Ready for Execution  
**Last Updated**: 2025-01-20  
**Next Review**: After implementation completion