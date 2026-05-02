# Alice Security Configuration
# Change these settings to customize your security preferences

# Instructions:
# 1. Open alice_trigger.py in a text editor
# 2. Find the line: SECURITY_CODE = "1234"
# 3. Change "1234" to your preferred 4-digit code
# 4. Save the file
# 5. Your new code will be active next time you run the trigger

## Current Default Code: 1234

## Security Features:
- 4-digit numeric code required
- Maximum 3 attempts before lockout
- Hidden password input (code not visible while typing)
- Automatic Alice startup after successful authentication
- Clear screen security (clears previous terminal content)

## Usage:
1. Double-click start_alice.bat (Windows)
2. OR run: python alice_trigger.py
3. Enter your 4-digit code when prompted
4. Alice will start automatically after successful authentication

## Customization:
- Change SECURITY_CODE in alice_trigger.py
- Modify max_attempts for different attempt limits
- Add additional security features as needed

## Files Created:
- alice_trigger.py (Main security launcher)
- start_alice.bat (Windows quick launcher)
- alice_security_config.md (This instruction file)