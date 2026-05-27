# 1. Drop the files into place
#    .env.example   -> project root
#    config.py      -> project root
#    requirements.txt -> project root (replaces existing pyyaml-only file)
#    scripts/smoke_test.py -> scripts/

# 2. Create your actual .env from the template
cp .env.example .env

# 3. Verify .env is gitignored — CRITICAL
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore

# 4. Edit .env, paste in your real API key
#    (open in your editor of choice; do not paste here)

# 5. Install new dependencies
source .venv/bin/activate   # if not already active
pip install -r requirements.txt

# 6. Smoke test
python scripts/smoke_test.py