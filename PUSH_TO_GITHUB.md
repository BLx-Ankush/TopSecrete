# 🚀 Push Alice to GitHub

## 📋 Pre-Push Checklist

Before pushing to GitHub, make sure:

- [ ] ✅ `.gitignore` created (excludes Hermes agent)
- [ ] ✅ `.env` files are NOT committed (only `.env.example`)
- [ ] ✅ `venv/` and `node_modules/` are excluded
- [ ] ✅ No API keys in committed files
- [ ] ✅ Documentation is complete

## 🔧 Step-by-Step Push Instructions

### Step 1: Navigate to Project Root

```powershell
cd "D:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)"
```

### Step 2: Check Git Status

```powershell
git status
```

You should see:
- ✅ ALICE folder (green/to be committed)
- ✅ Documentation files
- ❌ hermes-agent-main (should be untracked/ignored)
- ❌ .env files (should be untracked/ignored)
- ❌ venv/ (should be untracked/ignored)
- ❌ node_modules/ (should be untracked/ignored)

### Step 3: Check What Will Be Pushed

```powershell
git add --dry-run .
```

This shows what will be added WITHOUT actually adding it.

### Step 4: Remove Existing Remote (if needed)

```powershell
git remote -v
```

If you see an old remote, remove it:
```powershell
git remote remove origin
```

### Step 5: Add New GitHub Remote

```powershell
git remote add origin https://github.com/Project-ALICE-X/TopSecrete.git
```

Verify:
```powershell
git remote -v
```

### Step 6: Stage ALICE Files Only

```powershell
# Add ALICE folder and docs
git add ALICE/
git add .gitignore
git add README.md
git add ALICE_Architecture_Diagram.md
git add PLAN_ALPHA.md
```

### Step 7: Verify Staging

```powershell
git status
```

Make sure:
- ✅ Only ALICE files are staged
- ❌ NO hermes-agent-main
- ❌ NO .env files
- ❌ NO venv or node_modules

### Step 8: Commit Changes

```powershell
git commit -m "Initial commit: Alice AI Assistant with voice, vision, and OCR capabilities"
```

### Step 9: Push to GitHub

```powershell
# First push (if new repo)
git push -u origin main

# Or if branch is master
git push -u origin master
```

If you get an error about branch names, check current branch:
```powershell
git branch
```

Rename if needed:
```powershell
git branch -M main
git push -u origin main
```

## 🔐 Verify on GitHub

After pushing, visit:
https://github.com/Project-ALICE-X/TopSecrete

Check that:
- ✅ ALICE folder is present
- ✅ Documentation files are there
- ✅ `.env.example` files exist (templates)
- ❌ NO `.env` files (with real keys)
- ❌ NO hermes-agent-main folder
- ❌ NO venv or node_modules folders

## 🚨 If You Accidentally Committed Secrets

### Remove from Git History

```powershell
# Remove .env file from git tracking
git rm --cached ALICE/Alice_code/.env
git rm --cached ALICE/agent-starter-react/.env

# Commit the removal
git commit -m "Remove sensitive .env files"

# Force push (⚠️ WARNING: This rewrites history)
git push -f origin main
```

### Rotate All API Keys!

If you accidentally pushed API keys:
1. **OpenAI**: Revoke and create new key at https://platform.openai.com/api-keys
2. **LiveKit**: Rotate credentials at https://cloud.livekit.io/
3. **Google/Deepgram/Others**: Revoke and create new keys

## 📦 What Gets Pushed

### ✅ Included
```
ALICE/
├── alice_trigger.py
├── README.md
├── STARTUP_GUIDE.md
├── QUICK_FIX.md
├── ENV_SETUP_GUIDE.md
├── FINAL_SETUP_CHECKLIST.md
├── Alice_code/
│   ├── agent.py
│   ├── alice_vision_tools.py
│   ├── requirements.txt
│   └── .env.example         # Template only!
└── agent-starter-react/
    ├── app/
    ├── components/
    ├── package.json
    ├── pnpm-lock.yaml
    └── .env.example         # Template only!
```

### ❌ Excluded (by .gitignore)
```
hermes-agent-main/           # Entire folder
.env                         # All .env files
venv/                        # Python virtual env
node_modules/               # Node dependencies
__pycache__/                # Python cache
.next/                      # Next.js build
*.log                       # Log files
*.sqlite                    # Databases
```

## 🔄 Updating the Repository

### For Future Updates

```powershell
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Description of changes"

# Push to GitHub
git push origin main
```

### Best Practices

- Write clear commit messages
- Test before pushing
- Never commit sensitive data
- Review `git status` before committing
- Use branches for major changes

## 🌿 Branch Strategy (Optional)

### Create Feature Branch

```powershell
# Create and switch to new branch
git checkout -b feature/new-feature

# Make changes, commit
git add .
git commit -m "Add new feature"

# Push branch
git push -u origin feature/new-feature
```

### Merge to Main

```powershell
# Switch to main
git checkout main

# Merge feature branch
git merge feature/new-feature

# Push main
git push origin main
```

## 🆘 Troubleshooting

### "Repository not found"
- Check the URL is correct
- Verify you have access to the repository
- Make sure you're authenticated with GitHub

### "Permission denied"
- Set up GitHub authentication (SSH or Personal Access Token)
- For HTTPS: Use Personal Access Token as password

### "Everything up-to-date"
- You've already pushed these changes
- Make new commits to push updates

### "Failed to push some refs"
- Someone else pushed changes
- Pull first: `git pull origin main`
- Then push: `git push origin main`

## 🔑 GitHub Authentication

### Personal Access Token (Recommended)

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (all)
4. Use token as password when pushing

### SSH Key (Alternative)

1. Generate SSH key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Add to GitHub: Settings → SSH keys
3. Use SSH URL: `git@github.com:Project-ALICE-X/TopSecrete.git`

---

## ✅ Quick Command Reference

```powershell
# Setup
cd "D:\ALICE(NEW)\Alice Upgraded\Alice (Alpha)"
git remote add origin https://github.com/Project-ALICE-X/TopSecrete.git

# Add files
git add ALICE/
git add .gitignore
git add *.md

# Commit and push
git commit -m "Initial commit: Alice AI Assistant"
git push -u origin main
```

---

**Ready to push?** Follow the steps above carefully! 🚀
