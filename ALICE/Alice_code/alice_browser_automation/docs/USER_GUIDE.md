# Alice Browser Automation - User Guide

## Overview

Alice Browser Automation extends Alice's voice agent capabilities with intelligent browser automation. This guide will help you get started and make the most of the system's features.

**Version:** 1.0.0  
**Requirements Coverage:** 5.1, 6.1, 7.1, 10.1, 11.1

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Voice Command Examples](#voice-command-examples)
3. [Supported Booking Types](#supported-booking-types)
4. [Supported Applications](#supported-applications)
5. [Troubleshooting](#troubleshooting)
6. [Security Best Practices](#security-best-practices)
7. [FAQ](#faq)

---

## Quick Start

### Installation

1. **Install the package:**
   ```bash
   cd ALICE/Alice_code/alice_browser_automation
   pip install -e .
   ```

2. **Install Ollama and Qwen model:**
   ```bash
   # Install Ollama (visit https://ollama.ai)
   # Then pull the Qwen model
   ollama pull qwen2.5-coder:3b
   ```

3. **Verify installation:**
   ```bash
   python verify_installation.py
   ```

4. **Configure (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your preferences
   ```

### First Use

1. **Start Alice voice agent** (if not already running)

2. **Say a voice command:**
   - "Alice, book a flight to Paris on December 25th"
   - "Alice, order pizza from Pizza Palace"
   - "Alice, check my Gmail inbox"

3. **Follow voice prompts** for any additional information needed

4. **Confirm actions** when prompted (especially for payments)

---

## Voice Command Examples

### Travel Bookings

#### Flights

**Basic flight booking:**
```
"Book a flight to Paris on December 25th"
"Find flights from New York to London next Friday"
"Book a round trip to Tokyo, leaving March 1st, returning March 15th"
```

**With preferences:**
```
"Book a business class flight to San Francisco on Monday"
"Find direct flights to Miami for 2 passengers"
"Book an economy flight to Chicago with flexible dates"
```

**What Alice will ask:**
- Departure city (if not specified)
- Number of passengers (if not specified)
- Return date (for round trips)
- Class preference (economy/business/first)

#### Hotels

**Basic hotel booking:**
```
"Book a hotel in Paris from December 25th to December 30th"
"Find hotels in New York for next weekend"
"Reserve a room in San Francisco for 3 nights starting Friday"
```

**With preferences:**
```
"Book a hotel with a pool in Miami"
"Find a hotel with free wifi near Times Square"
"Reserve a 4-star hotel in downtown Chicago"
```

**What Alice will ask:**
- Check-in and check-out dates
- Number of guests
- Specific preferences (pool, wifi, location, etc.)

#### Car Rentals

**Basic car rental:**
```
"Rent a car in Los Angeles from Monday to Friday"
"Book a rental car at JFK airport for next week"
```

**With preferences:**
```
"Rent an SUV in Denver for the weekend"
"Book an automatic transmission car in San Francisco"
```

### Food Delivery

**Basic food orders:**
```
"Order pizza from Pizza Palace"
"Get Chinese food from Golden Dragon"
"Order a burger and fries from Five Guys"
```

**With details:**
```
"Order a large pepperoni pizza and garlic bread from Pizza Palace"
"Get pad thai and spring rolls from Thai Kitchen, deliver to 123 Main St"
"Order breakfast from IHOP using DoorDash"
```

**What Alice will ask:**
- Specific items to order
- Delivery address
- Special instructions (optional)
- Preferred delivery platform (if multiple available)

### Event Bookings

**Basic event booking:**
```
"Book tickets for Hamilton on Broadway"
"Get 2 tickets for the Lakers game next Friday"
"Reserve seats for the concert at Madison Square Garden"
```

**With preferences:**
```
"Book VIP tickets for the Taylor Swift concert"
"Get front row seats for the comedy show"
"Reserve 4 tickets in the middle section for the musical"
```

**What Alice will ask:**
- Event date (if not specified)
- Number of tickets
- Seat preference (front/middle/back/VIP)
- Ticket type (general/VIP/premium)

### Problem Solving

**Technical issues:**
```
"Help me fix this Python import error"
"How do I resolve this Windows update issue"
"Find a solution for my WiFi connection problem"
```

**Software problems:**
```
"My application won't start, help me fix it"
"How do I uninstall this program completely"
"Find solutions for this error message: [error text]"
```

**What Alice will do:**
1. Search for solutions online
2. Present top solutions with steps
3. Ask if you want to execute the solution
4. Execute approved commands
5. Verify if the problem is resolved

### Application Access

**Email (Gmail):**
```
"Check my Gmail inbox"
"Show me unread emails in Gmail"
"Open my Gmail sent folder"
"Search for emails from John in Gmail"
```

**GitHub:**
```
"Show my GitHub repositories"
"Check my GitHub notifications"
"Open my GitHub pull requests"
```

**LinkedIn:**
```
"Check my LinkedIn messages"
"Show my LinkedIn feed"
"View my LinkedIn network"
```

**What Alice will do:**
1. Open the application using your saved profile
2. Check if you're logged in
3. Re-authenticate if session expired (with your permission)
4. Navigate to the requested section
5. Extract and report the information

---

## Supported Booking Types

### Travel Bookings

| Type | Platforms | Features |
|------|-----------|----------|
| **Flights** | Google Flights, Kayak, Expedia | • One-way & round-trip<br>• Multiple passengers<br>• Class selection<br>• Flexible dates<br>• Direct flights filter |
| **Hotels** | Google Hotels, Booking.com, Hotels.com | • Date range selection<br>• Guest count<br>• Amenity filters<br>• Location preferences<br>• Star rating |
| **Car Rentals** | Google Cars, Kayak, Enterprise | • Pickup/return dates<br>• Vehicle type<br>• Transmission preference<br>• Insurance options |

### Food Delivery

| Platform | Features |
|----------|----------|
| **Uber Eats** | • Restaurant search<br>• Menu browsing<br>• Cart management<br>• Delivery tracking |
| **DoorDash** | • Same features as Uber Eats |
| **Grubhub** | • Same features as Uber Eats |

**Supported cuisines:** All cuisines available on the platforms

### Event Bookings

| Type | Platforms | Features |
|------|-----------|----------|
| **Concerts** | Ticketmaster, StubHub | • Venue selection<br>• Date selection<br>• Seat selection<br>• Ticket type |
| **Sports** | Ticketmaster, SeatGeek | • Team/game selection<br>• Seat location<br>• Group tickets |
| **Theater** | Ticketmaster, Broadway.com | • Show selection<br>• Performance date<br>• Seat preference |

---

## Supported Applications

### Pre-configured Applications

| Application | Type | Sections | Features |
|-------------|------|----------|----------|
| **Gmail** | Email | Inbox, Sent, Drafts, Starred | • Read emails<br>• Check unread count<br>• Search emails<br>• Navigate folders |
| **GitHub** | Development | Repositories, Issues, PRs, Notifications | • View repos<br>• Check notifications<br>• Browse issues<br>• Review PRs |
| **LinkedIn** | Social | Feed, Network, Jobs, Messages | • View feed<br>• Check messages<br>• Browse network<br>• Search jobs |

### Adding Custom Applications

You can add custom applications by creating a configuration:

```yaml
# In your config file
app_access:
  applications:
    my_app:
      app_name: "My Application"
      app_type: "productivity"
      url: "https://myapp.com"
      login_url: "https://myapp.com/login"
      profile_name: "myapp_profile"
      logged_in_indicator: "div.user-menu"
      sections:
        dashboard: "https://myapp.com/dashboard"
        settings: "https://myapp.com/settings"
```

Then use it with:
```
"Alice, open My Application dashboard"
```

---

## Troubleshooting

### Common Issues

#### 1. "Qwen model not available"

**Problem:** Ollama or Qwen model is not running.

**Solution:**
```bash
# Check if Ollama is running
ollama list

# If not installed, install Ollama from https://ollama.ai

# Pull the Qwen model
ollama pull qwen2.5-coder:3b

# Verify it's running
ollama run qwen2.5-coder:3b "Hello"
```

#### 2. "Session limit reached"

**Problem:** Too many browser sessions are open.

**Solution:**
- Alice will automatically close idle sessions after 5 minutes
- You can manually close sessions by saying: "Alice, close all browser sessions"
- Increase the limit in configuration if needed:
  ```yaml
  browser:
    max_concurrent_sessions: 5  # Increase from default 3
  ```

#### 3. "Element not found"

**Problem:** Web page structure changed or element is not visible.

**Solution:**
- Alice will automatically retry with alternative selectors
- If it persists, the website may have changed
- Report the issue so we can update the selectors

#### 4. "OTP verification required"

**Problem:** Website requires one-time password.

**Solution:**
- Alice will automatically switch to headed mode (visible browser)
- You'll see the browser window
- Alice will ask you to provide the OTP via voice
- Say the digits clearly: "1 2 3 4 5 6"
- Alice will enter the OTP and continue

#### 5. "Payment confirmation required"

**Problem:** Alice needs your approval before making a payment.

**Solution:**
- Alice will describe the payment action
- Review the details carefully
- Say "Yes, proceed" or "Confirm" to approve
- Say "No" or "Cancel" to abort
- This is a security feature and cannot be disabled

#### 6. "Session expired"

**Problem:** Your login session expired.

**Solution:**
- Alice will detect this automatically
- She'll ask if you want to re-authenticate
- Say "Yes" to log in again
- Your credentials are stored securely in your system keychain

#### 7. "Browser crashed"

**Problem:** Browser session crashed unexpectedly.

**Solution:**
- Alice will automatically restart the session
- Your task will resume from where it left off
- If crashes persist, check system resources (RAM, CPU)

### Performance Issues

#### Slow response times

**Possible causes:**
- Qwen model running on CPU instead of GPU
- Too many concurrent sessions
- Slow internet connection
- Complex web pages

**Solutions:**
```bash
# Check system resources
# Close unnecessary applications

# Reduce concurrent sessions
# Edit config:
browser:
  max_concurrent_sessions: 2

# Use faster model (if available)
qwen:
  model: "qwen2.5-coder:1.5b"  # Smaller, faster model
```

#### High memory usage

**Solution:**
```yaml
# Reduce idle timeout to close sessions faster
browser:
  idle_timeout_seconds: 180  # 3 minutes instead of 5

# Reduce max sessions
browser:
  max_concurrent_sessions: 2
```

### Getting Help

If you encounter issues not covered here:

1. **Check logs:**
   ```bash
   tail -f ~/.alice/logs/browser_automation.log
   ```

2. **Run diagnostics:**
   ```bash
   python verify_installation.py
   ```

3. **Report issues:**
   - Include log excerpts
   - Describe what you were trying to do
   - Mention any error messages

---

## Security Best Practices

### Credential Management

**DO:**
- ✅ Use system keychain for credential storage
- ✅ Use separate browser profiles for different accounts
- ✅ Enable 2FA on all accounts
- ✅ Review Alice's actions before confirming payments

**DON'T:**
- ❌ Share your browser profiles
- ❌ Disable payment confirmations
- ❌ Use Alice on public/shared computers
- ❌ Store passwords in plain text

### Payment Security

**Requirements:** 10.3

Alice requires explicit voice confirmation for all payment actions:

1. **Alice will describe the payment:**
   - "I'm about to complete a payment of $150.00 for flight booking"
   - "This will charge your saved payment method"

2. **You must confirm:**
   - Say: "Yes, proceed" or "Confirm payment"
   - Alice will NOT proceed without confirmation

3. **You can cancel:**
   - Say: "No" or "Cancel"
   - Alice will abort the transaction

**Never disable this feature.** It's your protection against unauthorized charges.

### Data Privacy

**What Alice stores:**
- Browser profiles (cookies, session data)
- Encrypted credentials in system keychain
- Task execution logs (no sensitive data)

**What Alice does NOT store:**
- Credit card numbers
- Passwords (except encrypted in keychain)
- OTP codes
- Personal messages or emails

**Requirements:** 10.2, 10.4

### Secure Browsing

**SSL Validation:**
- Alice validates SSL certificates by default
- Blocks connections to insecure sites
- Warns about certificate issues

**Banking Sites:**
- Alice can be configured to block banking sites
- Enable this in config for extra security:
  ```yaml
  security:
    block_banking_sites: true
  ```

**Requirements:** 10.5, 10.6

### Profile Isolation

Use separate profiles for different purposes:

```bash
# Work profile
"Alice, use work profile to check GitHub"

# Personal profile
"Alice, use personal profile to check Gmail"

# Shopping profile
"Alice, use shopping profile to order food"
```

This keeps your accounts and data separated.

### Session Security

**Automatic cleanup:**
- Idle sessions close after 5 minutes
- Sensitive data cleared after tasks
- Cookies encrypted at rest

**Manual cleanup:**
```
"Alice, close all browser sessions"
"Alice, clear browser data"
```

---

## FAQ

### General Questions

**Q: Do I need to keep the browser window open?**  
A: No, Alice runs in headless mode by default. You won't see browser windows unless OTP verification is needed.

**Q: Can I use Alice while doing other work?**  
A: Yes! Alice runs in the background. You can continue using your computer normally.

**Q: How many tasks can Alice handle at once?**  
A: Alice can handle up to 3 concurrent browser sessions by default. You can increase this in configuration.

**Q: Does Alice work offline?**  
A: No, Alice needs internet connection for:
- Web browsing
- Qwen model (runs locally but needs initial download)
- Accessing web applications

### Voice Commands

**Q: What if Alice doesn't understand my command?**  
A: Alice will ask for clarification. Try rephrasing or providing more details.

**Q: Can I interrupt Alice during a task?**  
A: Yes, say "Alice, cancel" or "Alice, stop" to cancel the current task.

**Q: Does Alice support multiple languages?**  
A: Currently, Alice primarily supports English. Multi-language support is planned.

### Bookings

**Q: Can Alice complete bookings without my payment info?**  
A: No, you need to have payment methods saved in your browser profile, or Alice will prompt you to add them.

**Q: What if the booking fails?**  
A: Alice will report the error and suggest alternatives. You can retry or try a different platform.

**Q: Can Alice find the best prices?**  
A: Alice can search and compare options, but you should verify prices before confirming.

### Security

**Q: Is it safe to let Alice access my accounts?**  
A: Yes, when following security best practices:
- Use strong passwords
- Enable 2FA
- Review actions before confirming
- Use separate profiles

**Q: Can Alice see my passwords?**  
A: No, passwords are stored encrypted in your system keychain. Alice only uses them for authentication.

**Q: What happens if I say "no" to a payment confirmation?**  
A: Alice immediately cancels the transaction. No payment will be processed.

### Technical

**Q: Why is Qwen model required?**  
A: Qwen processes web pages and generates browser actions. It runs locally for privacy and speed.

**Q: Can I use a different model?**  
A: Currently, Qwen 2.5 Coder 3B is required. Support for other models may be added.

**Q: How much disk space does Alice need?**  
A: Approximately:
- Qwen model: 2-3 GB
- Browser profiles: 100-500 MB per profile
- Logs: 10-50 MB

**Q: Does Alice work on all operating systems?**  
A: Alice supports:
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+)

---

## Tips and Tricks

### Efficient Voice Commands

**Be specific:**
- ❌ "Book a flight"
- ✅ "Book a flight to Paris on December 25th for 2 passengers"

**Use natural language:**
- ✅ "Find hotels in New York for next weekend"
- ✅ "Order pizza from my favorite place"
- ✅ "Check my work email"

**Provide context:**
- ✅ "Book a business class flight to San Francisco for my work trip"
- ✅ "Order dinner from Thai Kitchen, same as last time"

### Faster Bookings

1. **Save payment methods** in browser profiles
2. **Use profiles** for different purposes (work, personal)
3. **Provide all details** in one command
4. **Enable auto-fill** in browser settings

### Managing Profiles

```bash
# List profiles
python -c "from alice_browser_automation import ChromeProfileManager; \
           pm = ChromeProfileManager(); print(pm.list_profiles())"

# Create new profile
"Alice, create a new browser profile called 'shopping'"

# Switch profiles
"Alice, switch to work profile"
```

### Monitoring Tasks

```bash
# View active tasks
"Alice, what tasks are running?"

# Check task status
"Alice, status of my flight booking"

# View recent tasks
"Alice, show my recent bookings"
```

---

## Getting Started Checklist

- [ ] Install Alice Browser Automation
- [ ] Install Ollama and Qwen model
- [ ] Run verification script
- [ ] Configure settings (optional)
- [ ] Create browser profiles
- [ ] Try a simple command ("Alice, search for flights to Paris")
- [ ] Complete a test booking (use a test site if available)
- [ ] Set up payment methods in profiles
- [ ] Review security settings
- [ ] Read troubleshooting section

---

## Next Steps

- **Read the [Developer Guide](DEVELOPER_GUIDE.md)** to customize Alice
- **Check the [API Reference](API_REFERENCE.md)** for programmatic usage
- **Join the community** for tips and support
- **Report issues** to help improve Alice

---

## Support

**Documentation:** [Link to full documentation]  
**Community:** [Link to forum/Discord]  
**Issues:** [Link to GitHub issues]  
**Email:** support@alice-automation.com

---

**Last Updated:** 2024  
**Version:** 1.0.0  
**Requirements Coverage:** 5.1, 6.1, 7.1, 10.1, 11.1
