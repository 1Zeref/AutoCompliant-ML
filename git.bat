@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          AutoCompliant-ML - Git Push Helper
echo =======================================================
echo.

:: Ensure safe.directory is configured to avoid Windows ownership issues
git config --global --add safe.directory "%cd%" >nul 2>&1

:: Check git status
echo [INFO] Current Git Status:
git status -s
echo.

:: Prompt for commit message
set /p COMMIT_MSG="Enter commit message (Press Enter for default: 'Update AutoCompliant-ML'): "
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=Update AutoCompliant-ML
)

echo.
echo [INFO] Staging all tracked and new changes...
git add .

echo [INFO] Committing changes...
git commit -m "%COMMIT_MSG%"
if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] If regular commit failed due to Windows file index locks, trying fallback helper...
    python -c "
import subprocess, os
env = os.environ.copy()
env['GIT_INDEX_FILE'] = os.path.abspath('.git/test_idx')
try:
    subprocess.run(['git', 'read-tree', 'HEAD'], env=env, check=True)
    subprocess.run(['git', 'add', '-A'], env=env, check=True)
    res_tree = subprocess.run(['git', 'write-tree'], env=env, capture_output=True, text=True, check=True)
    tree_id = res_tree.stdout.strip()
    res_head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
    parent_id = res_head.stdout.strip()
    res_commit = subprocess.run(['git', 'commit-tree', tree_id, '-p', parent_id, '-m', os.environ.get('COMMIT_MSG', 'Update AutoCompliant-ML')], capture_output=True, text=True, check=True)
    commit_id = res_commit.stdout.strip()
    subprocess.run(['git', 'read-tree', commit_id], env=env, check=True)
    with open('.git/refs/heads/main', 'wb') as f:
        f.write(f'{commit_id}\n'.encode())
    with open('.git/test_idx', 'rb') as fin:
        idx_data = fin.read()
    with open('.git/index', 'wb') as fout:
        fout.write(idx_data)
    if os.path.exists('.git/test_idx'):
        os.remove('.git/test_idx')
    print('[FALLBACK OK] Committed via plumbing helper:', commit_id)
except Exception as e:
    print('[FALLBACK ERROR]', e)
"
)

echo.
echo [INFO] Pushing to remote repository (origin main)...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push failed. Please check your network connection or GitHub credentials.
) else (
    :: Sync remote tracking branch reference if needed
    python -c "
try:
    with open('.git/refs/heads/main', 'rb') as f:
        c = f.read().strip()
    with open('.git/refs/remotes/origin/main', 'wb') as f:
        f.write(c + b'\n')
except:
    pass
" >nul 2>&1
    echo.
    echo =======================================================
    echo [SUCCESS] Changes pushed to https://github.com/1Zeref/AutoCompliant-ML
    echo =======================================================
)

echo.
pause
