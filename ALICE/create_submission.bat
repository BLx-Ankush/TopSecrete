@echo off
echo ========================================
echo ALICE Submission Package Creator
echo ========================================
echo.

cd /d "%~dp0"

echo Creating package directory...
if exist "ALICE_Submission_Package" rd /s /q "ALICE_Submission_Package"
mkdir "ALICE_Submission_Package"
mkdir "ALICE_Submission_Package\Alice_code"
mkdir "ALICE_Submission_Package\frontend_config"

echo Copying core Python files...
copy "Alice_code\agent.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_personal_safe.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_vision_tools.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_vision.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_whatsapp_automation.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\Alice_prompts.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\memory_loop.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\memory_store.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_system_controller.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\Alice_duckduckgo_search.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_get_weather.py" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\requirements.txt" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\alice_app_database.json" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\apps_database.json" "ALICE_Submission_Package\Alice_code\" >nul
copy "Alice_code\ALICE_VISION_README.md" "ALICE_Submission_Package\Alice_code\" >nul

echo Copying mcp_client folder...
xcopy "Alice_code\mcp_client" "ALICE_Submission_Package\Alice_code\mcp_client\" /E /I /Q >nul

echo Copying frontend configs...
copy "agent-starter-react\package.json" "ALICE_Submission_Package\frontend_config\" >nul 2>nul
copy "agent-starter-react\next.config.ts" "ALICE_Submission_Package\frontend_config\" >nul 2>nul
copy "agent-starter-react\tsconfig.json" "ALICE_Submission_Package\frontend_config\" >nul 2>nul

echo Copying launcher files...
copy "alice_trigger.py" "ALICE_Submission_Package\" >nul
copy "start_alice.bat" "ALICE_Submission_Package\" >nul
copy "README.md" "ALICE_Submission_Package\" >nul 2>nul

echo Creating README...
(
echo # ALICE AI Assistant - Submission Package
echo.
echo ## About
echo ALICE is an advanced voice-based AI assistant with vision, OCR, and Windows automation capabilities.
echo.
echo ## Quick Start
echo 1. Install Python 3.11+
echo 2. cd Alice_code
echo 3. python -m venv venv
echo 4. venv\Scripts\activate
echo 5. pip install -r requirements.txt
echo 6. Create .env file with API keys
echo 7. python ..\alice_trigger.py
echo.
echo ## Features
echo - Voice AI ^(Hinglish^)
echo - Vision and OCR ^(11 tools^)
echo - System Automation ^(14 functions^)
echo - WhatsApp Integration
echo - Persistent Memory
echo.
echo ## Requirements
echo - Windows 10/11
echo - Python 3.11+
echo - Google Gemini API Key
echo - LiveKit credentials
echo.
echo ## Developer
echo Ankush - March 2026
) > "ALICE_Submission_Package\README.md"

echo.
echo Creating zip file...
powershell -Command "Compress-Archive -Path 'ALICE_Submission_Package\*' -DestinationPath 'ALICE_Submission.zip' -CompressionLevel Optimal -Force"

echo.
echo Checking size...
powershell -Command "$size = [math]::Round((Get-Item 'ALICE_Submission.zip').Length / 1MB, 2); Write-Host 'Package size:' $size 'MB'; if ($size -le 35) { Write-Host 'SUCCESS: Under 35 MB limit!' -ForegroundColor Green } else { Write-Host 'WARNING:' ([math]::Round($size - 35, 2)) 'MB over limit' -ForegroundColor Yellow }"

echo.
echo Cleaning up...
rd /s /q "ALICE_Submission_Package"

echo.
echo ========================================
echo Done! Check ALICE_Submission.zip
echo ========================================
pause
