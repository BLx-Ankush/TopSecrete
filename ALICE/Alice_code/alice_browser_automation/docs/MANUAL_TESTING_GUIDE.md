# Alice Browser Automation - Manual Testing Guide

**Version:** 1.0.0  
**Date:** 2024  
**Task:** 23.2 - Perform Manual Testing  
**Requirements Coverage:** All (1.1-12.6)

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Testing Setup](#pre-testing-setup)
3. [Test Area 1: Voice Command Recognition](#test-area-1-voice-command-recognition)
4. [Test Area 2: Real Booking Websites](#test-area-2-real-booking-websites)
5. [Test Area 3: Browser Profile Persistence](#test-area-3-browser-profile-persistence)
6. [Test Area 4: Performance Testing](#test-area-4-performance-testing)
7. [Test Area 5: Security Verification](#test-area-5-security-verification)
8. [Test Results Template](#test-results-template)
9. [Issue Reporting](#issue-reporting)

---

## Overview

This manual testing guide provides comprehensive step-by-step instructions for testing the Alice Browser Automation system. The guide covers five critical testing areas:

1. **Voice Command Recognition** - Testing LiveKit integration and voice command accuracy
2. **Real Booking Websites** - Testing with actual booking platforms in test/sandbox modes
3. **Browser Profile Persistence** - Testing Chrome profile persistence across sessions
4. **Performance Testing** - Testing system performance under various conditions
5. **Security Verification** - Verifying security measures and log sanitization

### Testing Objectives

- Validate all requirements (1.1 through 12.6)
- Ensure voice command recognition accuracy through LiveKit
- Verify real-world booking website interactions
- Confirm browser profile persistence across restarts
- Measure performance metrics under load
- Verify security measures and data protection

### Testing Environment

- **OS:** Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python:** 3.9+
- **Ollama:** Latest version with Qwen 2.5 Coder 3B model
- **LiveKit:** Voice agent running
- **Browser:** Chrome/Chromium (installed via Playwright)

---

## Pre-Testing Setup

### 1. Environment Verification

Before starting tests, verify the system is properly configured:

```bash
# Navigate to project directory
cd ALICE/Alice_code/alice_browser_automation

# Verify installation
python verify_installation.py
```

**Expected Output:**
```
✓ Ollama Service: Running
✓ Qwen Model: Available (qwen2.5-coder:3b)
✓ Playwright: Installed
✓ Browser Engine: Ready
✓ System ready for browser automation!
```

### 2. Start LiveKit Voice Agent

```bash
# Start Alice voice agent (in separate terminal)
cd ALICE/agent-starter-react
npm run dev
```

**Verification:**
- Open browser to `http://localhost:3000`
- Verify Alice face animation is visible
- Test microphone access is granted
- Say "Hello Alice" and verify response

### 3. Configure Test Profiles

Create separate browser profiles for testing:

```bash
# Create test profiles
python -c "
from alice_browser_automation import ChromeProfileManager
pm = ChromeProfileManager()
pm.get_or_create_profile('test_booking')
pm.get_or_create_profile('test_apps')
pm.get_or_create_profile('test_security')
print('Test profiles created')
"
```

### 4. Prepare Test Accounts

**Required Test Accounts:**
- Gmail test account (for app access testing)
- Test booking platform accounts (use sandbox/test modes)
- GitHub test account (for app access testing)

**Security Note:** Use dedicated test accounts, never production accounts.

---

## Test Area 1: Voice Command Recognition

**Objective:** Test voice command recognition accuracy through LiveKit integration  
**Requirements:** 3.1, 3.2, 3.3, 3.4, 3.5, 11.1, 11.2, 11.3

### Test 1.1: Basic Voice Command Recognition

**Steps:**
1. Start Alice voice agent
2. Say: "Alice, check browser automation status"
3. Wait for response

**Expected Results:**
- Alice recognizes the command within 2 seconds
- Alice responds with system status
- Status includes: Ollama running, Qwen available, Playwright ready

**Pass Criteria:**
- [ ] Command recognized correctly
- [ ] Response received within 3 seconds
- [ ] Status information is accurate

**Actual Results:**
```
[Record your observations here]
```

---

### Test 1.2: Web Booking Voice Commands

**Steps:**
1. Say: "Alice, book a flight to Paris on December 25th"
2. Observe Alice's response
3. Follow any prompts for additional information

**Expected Results:**
- Alice recognizes booking intent
- Alice asks for missing information (origin, passengers, etc.)
- Alice confirms understanding before proceeding

**Pass Criteria:**
- [ ] Booking intent recognized
- [ ] Missing parameters identified
- [ ] Confirmation requested before action

**Actual Results:**
```
[Record your observations here]
```

---

### Test 1.3: Problem Solving Voice Commands

**Steps:**
1. Say: "Alice, help me fix a Python import error"
2. Observe Alice's response
3. Provide error details when prompted

**Expected Results:**
- Alice recognizes problem-solving intent
- Alice asks for error details
- Alice initiates web search for solutions

**Pass Criteria:**
- [ ] Problem-solving intent recognized
- [ ] Appropriate questions asked
- [ ] Search initiated correctly

**Actual Results:**
```
[Record your observations here]
```

---

### Test 1.4: Application Access Voice Commands

**Steps:**
1. Say: "Alice, check my Gmail inbox"
2. Observe Alice's response
3. Note any authentication prompts

**Expected Results:**
- Alice recognizes app access intent
- Alice identifies Gmail as target application
- Alice checks for existing session or prompts for login

**Pass Criteria:**
- [ ] App access intent recognized
- [ ] Correct application identified
- [ ] Session handling appropriate

**Actual Results:**
```
[Record your observations here]
```

---

### Test 1.5: Voice Command Interruption

**Steps:**
1. Start a long-running task: "Alice, search for hotels in New York"
2. While task is running, say: "Alice, cancel"
3. Observe cancellation behavior

**Expected Results:**
- Alice acknowledges cancellation request
- Task stops at next safe checkpoint
- Alice confirms task was cancelled

**Pass Criteria:**
- [ ] Cancellation command recognized
- [ ] Task stopped gracefully
- [ ] Confirmation provided

**Actual Results:**
```
[Record your observations here]
```

---

### Test 1.6: Voice Command with Complex Parameters

**Steps:**
1. Say: "Alice, book a round trip flight from San Francisco to Tokyo, leaving March 1st, returning March 15th, for 2 passengers in business class"
2. Observe parameter extraction

**Expected Results:**
- All parameters extracted correctly:
  - Origin: San Francisco
  - Destination: Tokyo
  - Departure: March 1st
  - Return: March 15th
  - Passengers: 2
  - Class: Business

**Pass Criteria:**
- [ ] All parameters extracted correctly
- [ ] No missing information prompts
- [ ] Parameters confirmed before action

**Actual Results:**
```
[Record your observations here]
```

---

## Test Area 2: Real Booking Websites

**Objective:** Test with real booking websites using test/sandbox modes  
**Requirements:** 5.1-5.8, 8.1-8.6, 9.1-9.6

### Test 2.1: Flight Search on Google Flights

**Steps:**
1. Say: "Alice, search for flights from New York to London on December 20th"
2. Wait for Alice to navigate to Google Flights
3. Observe form filling and search execution
4. Note search results

**Expected Results:**
- Alice navigates to Google Flights
- Origin field filled: "New York"
- Destination field filled: "London"
- Date field filled: "December 20th"
- Search executed successfully
- Results displayed

**Pass Criteria:**
- [ ] Navigation successful (within 3 seconds)
- [ ] All form fields filled correctly
- [ ] Search executed without errors
- [ ] Results page loaded

**Actual Results:**
```
[Record your observations here]
```

---

### Test 2.2: Hotel Search on Booking.com

**Steps:**
1. Say: "Alice, find hotels in Paris from December 25th to December 30th"
2. Observe navigation and form filling
3. Note search results

**Expected Results:**
- Alice navigates to Booking.com or similar
- Destination: "Paris"
- Check-in: December 25th
- Check-out: December 30th
- Search executed
- Hotel results displayed

**Pass Criteria:**
- [ ] Navigation successful
- [ ] Date range filled correctly
- [ ] Search executed
- [ ] Results displayed

**Actual Results:**
```
[Record your observations here]
```

---

### Test 2.3: Food Delivery Search (Uber Eats/DoorDash)

**Steps:**
1. Say: "Alice, find pizza restaurants on Uber Eats"
2. Observe navigation and search
3. Note restaurant results

**Expected Results:**
- Alice navigates to Uber Eats or DoorDash
- Search query: "pizza"
- Restaurant results displayed
- Menu browsing possible

**Pass Criteria:**
- [ ] Navigation successful
- [ ] Search executed correctly
- [ ] Results displayed
- [ ] Can browse menus

**Actual Results:**
```
[Record your observations here]
```

---

### Test 2.4: Error Handling - Element Not Found

**Steps:**
1. Navigate to a booking site manually
2. Change the page structure (using browser DevTools)
3. Ask Alice to interact with the modified page
4. Observe error handling

**Expected Results:**
- Alice detects element not found
- Alice retries with alternative selectors
- Alice reports error if all selectors fail
- Error message is user-friendly

**Pass Criteria:**
- [ ] Error detected correctly
- [ ] Retry attempted (up to 2 times)
- [ ] User-friendly error message
- [ ] No system crash

**Actual Results:**
```
[Record your observations here]
```

---

### Test 2.5: Error Handling - Page Load Timeout

**Steps:**
1. Disconnect internet temporarily
2. Say: "Alice, search for flights to Paris"
3. Observe timeout handling
4. Reconnect internet

**Expected Results:**
- Alice detects page load timeout
- Alice retries navigation (up to 2 times)
- Alice reports connectivity issue
- Task fails gracefully

**Pass Criteria:**
- [ ] Timeout detected
- [ ] Retry attempted
- [ ] Clear error message
- [ ] No system crash

**Actual Results:**
```
[Record your observations here]
```

---

### Test 2.6: Session Reuse for Same Domain

**Steps:**
1. Say: "Alice, search for flights to Paris"
2. Wait for search to complete
3. Immediately say: "Alice, search for flights to London"
4. Observe session handling

**Expected Results:**
- First search creates new session
- Second search reuses existing session
- No new browser window opened
- Faster execution for second search

**Pass Criteria:**
- [ ] Session reused correctly
- [ ] No duplicate sessions
- [ ] Performance improvement observed

**Actual Results:**
```
[Record your observations here]
```

---

## Test Area 3: Browser Profile Persistence

**Objective:** Test Chrome profile persistence across sessions  
**Requirements:** 7.1-7.7, 10.1, 10.2

### Test 3.1: Profile Creation and Storage

**Steps:**
1. Create a new profile:
   ```python
   from alice_browser_automation import ChromeProfileManager
   pm = ChromeProfileManager()
   profile_path = pm.get_or_create_profile('test_persistence')
   print(f"Profile created at: {profile_path}")
   ```
2. Verify profile directory structure

**Expected Results:**
- Profile directory created at `~/.alice/browser_profiles/test_persistence/`
- Contains: `cookies.db`, `local_storage/`, `session_storage/`, `preferences.json`

**Pass Criteria:**
- [ ] Profile directory exists
- [ ] All required files/folders present
- [ ] Preferences.json has valid JSON

**Actual Results:**
```
[Record your observations here]
```

---

### Test 3.2: Login Session Persistence

**Steps:**
1. Say: "Alice, open Gmail using test_persistence profile"
2. Complete login manually if prompted
3. Close Alice completely
4. Restart Alice
5. Say: "Alice, open Gmail using test_persistence profile"
6. Observe if login is required

**Expected Results:**
- First access: Login required
- After restart: Already logged in (session persisted)
- No re-authentication needed

**Pass Criteria:**
- [ ] Login session persisted across restart
- [ ] No re-authentication required
- [ ] Cookies restored correctly

**Actual Results:**
```
[Record your observations here]
```

---

### Test 3.3: Multiple Profile Isolation

**Steps:**
1. Create two profiles: `profile_a` and `profile_b`
2. Login to Gmail with `profile_a` (account A)
3. Login to Gmail with `profile_b` (account B)
4. Switch between profiles and verify isolation

**Expected Results:**
- Profile A shows account A's inbox
- Profile B shows account B's inbox
- No cross-contamination of sessions
- Each profile maintains separate cookies

**Pass Criteria:**
- [ ] Profiles are isolated
- [ ] Correct account shown for each profile
- [ ] No session mixing

**Actual Results:**
```
[Record your observations here]
```

---

### Test 3.4: Credential Encryption

**Steps:**
1. Store credentials for a profile:
   ```python
   from alice_browser_automation import ChromeProfileManager
   pm = ChromeProfileManager()
   pm.encrypt_credentials('test_security', {
       'username': 'test@example.com',
       'password': 'test_password_123'
   })
   ```
2. Verify credentials stored in system keychain
3. Retrieve credentials:
   ```python
   creds = pm.get_credentials('test_security')
   print(f"Retrieved: {creds}")
   ```

**Expected Results:**
- Credentials stored in system keychain (not in files)
- Credentials retrievable with correct profile name
- Credentials encrypted at rest

**Pass Criteria:**
- [ ] Credentials stored successfully
- [ ] Credentials retrievable
- [ ] Not stored in plain text files

**Actual Results:**
```
[Record your observations here]
```

---

### Test 3.5: Profile Deletion

**Steps:**
1. Create a test profile: `profile_to_delete`
2. Add some data (login to a site)
3. Delete the profile:
   ```python
   from alice_browser_automation import ChromeProfileManager
   pm = ChromeProfileManager()
   pm.delete_profile('profile_to_delete')
   ```
4. Verify profile directory removed
5. Verify credentials removed from keychain

**Expected Results:**
- Profile directory completely removed
- Credentials removed from keychain
- No residual data left

**Pass Criteria:**
- [ ] Profile directory deleted
- [ ] Credentials removed
- [ ] No errors during deletion

**Actual Results:**
```
[Record your observations here]
```

---

## Test Area 4: Performance Testing

**Objective:** Test performance under various conditions  
**Requirements:** 12.1-12.6

### Test 4.1: Browser Session Initialization Time

**Steps:**
1. Measure time to initialize browser session:
   ```python
   import time
   from alice_browser_automation import BrowserAutomationEngine
   
   engine = BrowserAutomationEngine()
   
   start = time.time()
   await engine.initialize()
   duration = time.time() - start
   
   print(f"Initialization time: {duration:.2f} seconds")
   ```

**Expected Results:**
- Initialization completes within 3 seconds
- All components initialized successfully

**Pass Criteria:**
- [ ] Initialization time ≤ 3 seconds
- [ ] No errors during initialization

**Actual Results:**
```
Initialization time: _____ seconds
[Record observations]
```

---

### Test 4.2: DOM Parsing Performance

**Steps:**
1. Navigate to a complex page (e.g., Amazon product page)
2. Measure DOM parsing time:
   ```python
   import time
   from alice_browser_automation import DOMParser
   
   parser = DOMParser()
   
   start = time.time()
   dom = await parser.parse_page(page)
   duration = time.time() - start
   
   print(f"DOM parsing time: {duration:.2f} seconds")
   print(f"Interactive elements found: {len(dom.interactive_elements)}")
   ```

**Expected Results:**
- DOM parsing completes within 2 seconds
- Interactive elements correctly identified

**Pass Criteria:**
- [ ] Parsing time ≤ 2 seconds
- [ ] Interactive elements > 0
- [ ] No parsing errors

**Actual Results:**
```
DOM parsing time: _____ seconds
Interactive elements: _____
[Record observations]
```

---

### Test 4.3: Qwen Model Response Time

**Steps:**
1. Measure Qwen model response time for action generation:
   ```python
   import time
   from alice_browser_automation import QwenModelClient
   
   client = QwenModelClient()
   
   start = time.time()
   response = await client.generate_action_plan(task, dom)
   duration = time.time() - start
   
   print(f"Qwen response time: {duration:.2f} seconds")
   ```

**Expected Results:**
- Response generated within 5 seconds
- Valid JSON action plan returned

**Pass Criteria:**
- [ ] Response time ≤ 5 seconds
- [ ] Valid JSON returned
- [ ] Action plan is executable

**Actual Results:**
```
Qwen response time: _____ seconds
[Record observations]
```

---

### Test 4.4: Concurrent Session Handling

**Steps:**
1. Start 3 concurrent browser tasks:
   ```python
   tasks = [
       engine.execute_task("Search flights to Paris", TaskType.WEB_BOOKING, {}),
       engine.execute_task("Search hotels in London", TaskType.WEB_BOOKING, {}),
       engine.execute_task("Check Gmail inbox", TaskType.APP_ACCESS, {})
   ]
   
   results = await asyncio.gather(*tasks)
   ```
2. Monitor system resources (CPU, memory)
3. Verify all tasks complete successfully

**Expected Results:**
- All 3 tasks execute concurrently
- No session limit errors
- All tasks complete successfully
- System remains responsive

**Pass Criteria:**
- [ ] All tasks complete successfully
- [ ] No session limit errors
- [ ] CPU usage < 80%
- [ ] Memory usage reasonable

**Actual Results:**
```
Task 1: [status]
Task 2: [status]
Task 3: [status]
CPU usage: _____%
Memory usage: _____ MB
[Record observations]
```

---

### Test 4.5: Idle Session Cleanup

**Steps:**
1. Create 3 browser sessions
2. Leave them idle for 6 minutes
3. Verify sessions are automatically closed

**Expected Results:**
- Sessions idle for > 5 minutes are closed
- Resources released properly
- No memory leaks

**Pass Criteria:**
- [ ] Idle sessions closed after 5 minutes
- [ ] Memory released
- [ ] No errors during cleanup

**Actual Results:**
```
Sessions before: _____
Sessions after 6 minutes: _____
[Record observations]
```

---

### Test 4.6: End-to-End Booking Performance

**Steps:**
1. Measure complete booking flow time:
   ```python
   import time
   
   start = time.time()
   result = await engine.execute_task(
       "Search for flights to Paris on December 25th",
       TaskType.WEB_BOOKING,
       {"origin": "SFO", "destination": "CDG"}
   )
   duration = time.time() - start
   
   print(f"Total booking time: {duration:.2f} seconds")
   ```

**Expected Results:**
- Complete flow within 60 seconds (excluding user input)
- Progress updates every 10 seconds

**Pass Criteria:**
- [ ] Total time ≤ 60 seconds
- [ ] Progress updates provided
- [ ] Task completes successfully

**Actual Results:**
```
Total booking time: _____ seconds
Progress updates: [list them]
[Record observations]
```

---

## Test Area 5: Security Verification

**Objective:** Verify security measures and log sanitization  
**Requirements:** 10.1-10.6

### Test 5.1: Sensitive Data Filtering in Logs

**Steps:**
1. Enable debug logging
2. Perform actions with sensitive data:
   - Enter password: "MySecretPass123"
   - Enter credit card: "4532 1234 5678 9010"
   - Enter OTP: "123456"
3. Check log files for sensitive data

**Expected Results:**
- Passwords replaced with `[REDACTED_PWD]`
- Credit cards replaced with `[REDACTED_CC]`
- OTPs replaced with `[REDACTED_OTP]`
- No sensitive data in plain text

**Pass Criteria:**
- [ ] No passwords in logs
- [ ] No credit card numbers in logs
- [ ] No OTP codes in logs
- [ ] All sensitive data redacted

**Actual Results:**
```
Log file location: ~/.alice/logs/browser_automation.log

Sample log entries:
[Copy relevant log entries here]

Sensitive data found: YES / NO
[Record observations]
```

---

### Test 5.2: Memory Clearing After Task Completion

**Steps:**
1. Execute a task that handles sensitive data
2. After completion, verify memory is cleared:
   ```python
   # Check sensitive data contexts
   print(f"Sensitive contexts: {len(engine.security_manager._sensitive_contexts)}")
   ```

**Expected Results:**
- All sensitive data contexts cleared
- No sensitive data in memory after task completion

**Pass Criteria:**
- [ ] Sensitive contexts list is empty
- [ ] Memory cleared successfully
- [ ] No residual sensitive data

**Actual Results:**
```
Sensitive contexts after task: _____
[Record observations]
```

---

### Test 5.3: SSL Certificate Validation

**Steps:**
1. Test with valid HTTPS site:
   ```python
   result = engine.security_manager.validate_ssl_certificate("https://www.google.com")
   print(f"Valid SSL: {result}")
   ```
2. Test with invalid SSL site (use a test site with expired cert):
   ```python
   try:
       result = engine.security_manager.validate_ssl_certificate("https://expired.badssl.com/")
   except ssl.SSLError as e:
       print(f"SSL Error caught: {e}")
   ```

**Expected Results:**
- Valid certificates pass validation
- Invalid certificates raise SSLError
- Connection blocked for invalid certificates

**Pass Criteria:**
- [ ] Valid certificates accepted
- [ ] Invalid certificates rejected
- [ ] SSLError raised for invalid certs

**Actual Results:**
```
Valid SSL test: [result]
Invalid SSL test: [result]
[Record observations]
```

---

### Test 5.4: Banking Website Permission Check

**Steps:**
1. Attempt to access banking website without permission:
   ```python
   try:
       engine.security_manager.check_banking_permission("https://www.chase.com")
   except PermissionError as e:
       print(f"Permission denied: {e}")
   ```
2. Grant permission and retry:
   ```python
   engine.security_manager.grant_banking_permission("https://www.chase.com")
   result = engine.security_manager.check_banking_permission("https://www.chase.com")
   print(f"Permission granted: {result}")
   ```

**Expected Results:**
- Banking sites blocked without permission (if configured)
- Permission can be granted explicitly
- Access allowed after permission granted

**Pass Criteria:**
- [ ] Banking sites detected correctly
- [ ] Permission check enforced
- [ ] Permission grant works

**Actual Results:**
```
Without permission: [result]
With permission: [result]
[Record observations]
```

---

### Test 5.5: Payment Confirmation Workflow

**Steps:**
1. Initiate a booking that requires payment
2. Observe payment confirmation prompt
3. Test confirmation and cancellation:
   ```python
   # Create payment confirmation
   confirmation = engine.security_manager.create_payment_confirmation(
       task_id="test_task",
       amount="$150.00",
       merchant="Test Airlines"
   )
   
   # Get summary
   summary = engine.security_manager.get_payment_summary("test_task")
   print(f"Payment summary: {summary}")
   
   # Confirm payment
   engine.security_manager.confirm_payment("test_task")
   ```

**Expected Results:**
- Payment confirmation required before processing
- Summary shows amount, merchant, payment method
- User must explicitly confirm
- Can cancel payment

**Pass Criteria:**
- [ ] Confirmation required
- [ ] Summary is clear and accurate
- [ ] Confirmation works
- [ ] Cancellation works

**Actual Results:**
```
Payment summary: [record summary]
Confirmation: [result]
[Record observations]
```

---

### Test 5.6: Credential Storage Security

**Steps:**
1. Store credentials in profile
2. Verify storage location:
   - Check profile directory for plain text files
   - Verify system keychain contains credentials
3. Attempt to read credentials from files

**Expected Results:**
- Credentials NOT stored in plain text files
- Credentials stored in system keychain
- Credentials encrypted at rest
- Cannot read credentials from files

**Pass Criteria:**
- [ ] No plain text credentials in files
- [ ] Credentials in system keychain
- [ ] Encrypted storage verified

**Actual Results:**
```
Plain text files found: YES / NO
Keychain storage: YES / NO
[Record observations]
```

---

## Test Results Template

Use this template to record overall test results:

### Test Execution Summary

**Date:** _______________  
**Tester:** _______________  
**Environment:** _______________  
**Version:** _______________

### Test Area Results

| Test Area | Tests Passed | Tests Failed | Pass Rate | Notes |
|-----------|--------------|--------------|-----------|-------|
| Voice Command Recognition | __ / 6 | __ | __% | |
| Real Booking Websites | __ / 6 | __ | __% | |
| Browser Profile Persistence | __ / 5 | __ | __% | |
| Performance Testing | __ / 6 | __ | __% | |
| Security Verification | __ / 6 | __ | __% | |
| **TOTAL** | **__ / 29** | **__** | **__%** | |

### Critical Issues Found

| Issue ID | Severity | Test Area | Description | Status |
|----------|----------|-----------|-------------|--------|
| | | | | |
| | | | | |

### Performance Metrics

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Browser initialization time | ≤ 3s | ___s | |
| DOM parsing time | ≤ 2s | ___s | |
| Qwen response time | ≤ 5s | ___s | |
| End-to-end booking time | ≤ 60s | ___s | |

### Security Verification

| Security Check | Pass/Fail | Notes |
|----------------|-----------|-------|
| No passwords in logs | | |
| No credit cards in logs | | |
| No OTP codes in logs | | |
| SSL validation working | | |
| Banking permission enforced | | |
| Payment confirmation required | | |
| Credentials encrypted | | |

### Overall Assessment

**System Ready for Production:** YES / NO

**Justification:**
```
[Provide detailed justification for production readiness decision]
```

**Recommended Actions:**
```
[List any recommended actions before production deployment]
```

---

## Issue Reporting

### Issue Report Template

```markdown
## Issue Report

**Issue ID:** [Unique identifier]
**Date:** [Date found]
**Tester:** [Your name]
**Severity:** Critical / High / Medium / Low

### Test Information
- **Test Area:** [Voice Command / Booking / Profile / Performance / Security]
- **Test Case:** [Specific test case number]
- **Environment:** [OS, Python version, etc.]

### Description
[Clear description of the issue]

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happened]

### Screenshots/Logs
[Attach relevant screenshots or log excerpts]

### Impact
[How does this affect the system?]

### Suggested Fix
[If you have suggestions]
```

### Severity Definitions

- **Critical:** System crash, data loss, security vulnerability
- **High:** Major functionality broken, workaround difficult
- **Medium:** Functionality impaired, workaround available
- **Low:** Minor issue, cosmetic problem, easy workaround

---

## Appendix A: Test Data

### Test Booking Websites

**Flight Search:**
- Google Flights: https://www.google.com/travel/flights
- Kayak: https://www.kayak.com (use test mode if available)

**Hotel Search:**
- Google Hotels: https://www.google.com/travel/hotels
- Booking.com: https://www.booking.com (use test properties)

**Food Delivery:**
- Uber Eats: https://www.ubereats.com
- DoorDash: https://www.doordash.com

**Note:** Always use test/sandbox modes when available. Never complete real bookings during testing.

### Test Accounts

Create dedicated test accounts for:
- Gmail (for app access testing)
- GitHub (for app access testing)
- Booking platforms (if test accounts available)

**Security:** Never use production accounts or real payment methods during testing.

---

## Appendix B: Performance Benchmarks

### Target Performance Metrics

| Operation | Target Time | Acceptable Range |
|-----------|-------------|------------------|
| Browser initialization | 3s | 2-4s |
| DOM parsing | 2s | 1-3s |
| Qwen action generation | 5s | 3-7s |
| Simple action (click/type) | 1s | 0.5-2s |
| Page navigation | 3s | 2-5s |
| End-to-end booking | 60s | 45-90s |

### Resource Usage Targets

| Resource | Target | Maximum |
|----------|--------|---------|
| CPU usage (idle) | < 5% | 10% |
| CPU usage (active) | < 50% | 80% |
| Memory usage | < 500MB | 1GB |
| Disk usage (per profile) | < 100MB | 500MB |

---

## Appendix C: Security Checklist

### Pre-Deployment Security Verification

- [ ] No sensitive data in logs (passwords, credit cards, OTPs)
- [ ] Credentials encrypted in system keychain
- [ ] SSL certificate validation enabled
- [ ] Banking website permissions enforced
- [ ] Payment confirmation required
- [ ] Sensitive data cleared from memory after tasks
- [ ] No plain text credential files
- [ ] Log files have appropriate permissions
- [ ] Profile directories have appropriate permissions
- [ ] No hardcoded credentials in code
- [ ] No API keys in logs
- [ ] Error messages don't expose sensitive data

---

## Appendix D: Troubleshooting

### Common Issues During Testing

**Issue:** Ollama not responding
**Solution:** 
```bash
# Restart Ollama service
ollama serve
# Verify model is loaded
ollama list
```

**Issue:** Playwright browser not found
**Solution:**
```bash
# Reinstall Playwright browsers
playwright install chromium
```

**Issue:** LiveKit connection failed
**Solution:**
- Check if LiveKit agent is running
- Verify network connectivity
- Check firewall settings

**Issue:** Profile directory permission denied
**Solution:**
```bash
# Fix permissions
chmod 700 ~/.alice/browser_profiles
```

---

**End of Manual Testing Guide**

**Version:** 1.0.0  
**Last Updated:** 2024  
**Maintained by:** Alice Browser Automation Team
