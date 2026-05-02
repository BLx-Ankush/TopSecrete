# Alice Browser Automation - Manual Testing Checklist

**Version:** 1.0.0  
**Task:** 23.2 - Perform Manual Testing  
**Quick Reference Checklist**

---

## Pre-Testing Setup ✓

- [ ] Ollama service running
- [ ] Qwen 2.5 Coder 3B model installed
- [ ] Playwright browsers installed
- [ ] LiveKit voice agent running
- [ ] Test profiles created
- [ ] Test accounts prepared
- [ ] Verification script passed

---

## Test Area 1: Voice Command Recognition (6 tests)

- [ ] **1.1** Basic voice command recognition
- [ ] **1.2** Web booking voice commands
- [ ] **1.3** Problem solving voice commands
- [ ] **1.4** Application access voice commands
- [ ] **1.5** Voice command interruption
- [ ] **1.6** Complex parameter extraction

**Pass Criteria:** All commands recognized within 2-3 seconds, correct intent identification

---

## Test Area 2: Real Booking Websites (6 tests)

- [ ] **2.1** Flight search on Google Flights
- [ ] **2.2** Hotel search on Booking.com
- [ ] **2.3** Food delivery search
- [ ] **2.4** Error handling - Element not found
- [ ] **2.5** Error handling - Page load timeout
- [ ] **2.6** Session reuse for same domain

**Pass Criteria:** Successful navigation, form filling, search execution, graceful error handling

---

## Test Area 3: Browser Profile Persistence (5 tests)

- [ ] **3.1** Profile creation and storage
- [ ] **3.2** Login session persistence across restarts
- [ ] **3.3** Multiple profile isolation
- [ ] **3.4** Credential encryption in keychain
- [ ] **3.5** Profile deletion cleanup

**Pass Criteria:** Profiles persist across restarts, sessions maintained, credentials encrypted

---

## Test Area 4: Performance Testing (6 tests)

- [ ] **4.1** Browser initialization time (≤ 3s)
- [ ] **4.2** DOM parsing performance (≤ 2s)
- [ ] **4.3** Qwen model response time (≤ 5s)
- [ ] **4.4** Concurrent session handling (3 sessions)
- [ ] **4.5** Idle session cleanup (5 min timeout)
- [ ] **4.6** End-to-end booking performance (≤ 60s)

**Pass Criteria:** All operations within target times, system remains responsive

---

## Test Area 5: Security Verification (6 tests)

- [ ] **5.1** Sensitive data filtering in logs
- [ ] **5.2** Memory clearing after task completion
- [ ] **5.3** SSL certificate validation
- [ ] **5.4** Banking website permission check
- [ ] **5.5** Payment confirmation workflow
- [ ] **5.6** Credential storage security

**Pass Criteria:** No sensitive data in logs, SSL validated, permissions enforced, credentials encrypted

---

## Critical Security Checks ⚠️

- [ ] No passwords in log files
- [ ] No credit card numbers in log files
- [ ] No OTP codes in log files
- [ ] Credentials stored in system keychain (not files)
- [ ] SSL validation enabled and working
- [ ] Banking permissions enforced
- [ ] Payment confirmation required
- [ ] Sensitive data cleared from memory

---

## Performance Benchmarks 📊

| Metric | Target | Actual | ✓ |
|--------|--------|--------|---|
| Browser init | ≤ 3s | ___s | [ ] |
| DOM parsing | ≤ 2s | ___s | [ ] |
| Qwen response | ≤ 5s | ___s | [ ] |
| E2E booking | ≤ 60s | ___s | [ ] |

---

## Requirements Coverage 📋

### Requirement 1: Browser Automation Engine Setup
- [ ] 1.1 - Install browser-use library
- [ ] 1.2 - Install Ollama with Qwen model
- [ ] 1.3 - Verify Playwright binaries
- [ ] 1.4 - Validate Qwen model availability
- [ ] 1.5 - Configure headless/headed modes

### Requirement 2: DOM-First Processing
- [ ] 2.1 - Extract DOM structure
- [ ] 2.2 - Parse accessibility tree
- [ ] 2.3 - Provide element selectors
- [ ] 2.4 - Convert page within 2 seconds
- [ ] 2.5 - Handle dynamic content
- [ ] 2.6 - Exclude non-interactive elements

### Requirement 3: LiveKit to Qwen Bridge
- [ ] 3.1 - Establish connection
- [ ] 3.2 - Implement function calling
- [ ] 3.3 - Translate voice commands
- [ ] 3.4 - Pass DOM to Qwen
- [ ] 3.5 - Return responses within 3 seconds
- [ ] 3.6 - Handle Qwen unavailability

### Requirement 4: Prompt Engineering
- [ ] 4.1 - Few-shot examples in prompt
- [ ] 4.2 - Generate valid JSON
- [ ] 4.3 - Include action details
- [ ] 4.4 - Demonstrate all action types
- [ ] 4.5 - Retry on invalid JSON
- [ ] 4.6 - Process within 5 seconds

### Requirement 5: Web Bookings
- [ ] 5.1 - Navigate to booking sites
- [ ] 5.2 - Fill booking forms
- [ ] 5.3 - Handle OTP verification
- [ ] 5.4 - Accept OTP via voice
- [ ] 5.5 - Complete booking process
- [ ] 5.6 - Handle food delivery
- [ ] 5.7 - Handle event bookings
- [ ] 5.8 - Report errors

### Requirement 6: Problem Solving
- [ ] 6.1 - Search for solutions
- [ ] 6.2 - Navigate search results
- [ ] 6.3 - Integrate with Open Interpreter
- [ ] 6.4 - Summarize solutions
- [ ] 6.5 - Execute approved solutions
- [ ] 6.6 - Verify effectiveness

### Requirement 7: Application Access
- [ ] 7.1 - Create Chrome profiles
- [ ] 7.2 - Store authentication cookies
- [ ] 7.3 - Use existing profiles
- [ ] 7.4 - Detect login requirements
- [ ] 7.5 - Navigate applications
- [ ] 7.6 - Extract information
- [ ] 7.7 - Persist across restarts

### Requirement 8: Session Management
- [ ] 8.1 - Launch headless by default
- [ ] 8.2 - Switch to headed for OTP
- [ ] 8.3 - Limit to 3 concurrent sessions
- [ ] 8.4 - Close idle sessions (5 min)
- [ ] 8.5 - Reuse sessions for same domain
- [ ] 8.6 - Restart crashed sessions

### Requirement 9: Error Handling
- [ ] 9.1 - Retry with alternative selectors
- [ ] 9.2 - Retry navigation (2 times)
- [ ] 9.3 - Request corrected actions
- [ ] 9.4 - Report connectivity issues
- [ ] 9.5 - Log errors with context
- [ ] 9.6 - Report failure reasons

### Requirement 10: Security and Privacy
- [ ] 10.1 - Encrypt credentials
- [ ] 10.2 - Don't log sensitive data
- [ ] 10.3 - Require payment confirmation
- [ ] 10.4 - Clear sensitive data
- [ ] 10.5 - Validate SSL certificates
- [ ] 10.6 - Banking site permissions

### Requirement 11: Alice Integration
- [ ] 11.1 - Recognize intent
- [ ] 11.2 - Provide status updates
- [ ] 11.3 - Prompt via voice
- [ ] 11.4 - Confirm completion
- [ ] 11.5 - Support interruption
- [ ] 11.6 - Maintain context

### Requirement 12: Performance
- [ ] 12.1 - Initiate session within 3s
- [ ] 12.2 - Parse DOM within 2s
- [ ] 12.3 - Generate plan within 5s
- [ ] 12.4 - Execute actions within 1s
- [ ] 12.5 - Progress updates every 10s
- [ ] 12.6 - Complete booking within 60s

---

## Test Summary

**Total Tests:** 29  
**Tests Passed:** ___  
**Tests Failed:** ___  
**Pass Rate:** ___%

**Requirements Covered:** 72  
**Requirements Passed:** ___  
**Requirements Failed:** ___  
**Coverage:** ___%

---

## Sign-Off

**Tester Name:** _____________________  
**Date:** _____________________  
**Signature:** _____________________

**System Ready for Production:** YES / NO

**Notes:**
```
[Add any final notes or observations]
```

---

## Quick Issue Log

| # | Severity | Area | Issue | Status |
|---|----------|------|-------|--------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

---

**For detailed testing instructions, see:** `MANUAL_TESTING_GUIDE.md`
