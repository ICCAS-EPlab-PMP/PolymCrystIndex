[中文版](README.zh.md)

# PolyCryIndex Server Deployment Guide

## Requirements

| Dependency | Minimum Version | Purpose |
|------------|----------------|---------|
| OS | Rocky 9 / Ubuntu 20.04+ / CentOS 7+ / macOS 12+ | Runtime |
| Python | 3.9+ | Backend runtime |
| Node.js | 16+ | Frontend build |
| gfortran | Any available version | Fortran optimizer compilation |
| curl | Any available version | Health check |

---

## Installation Directory Structure

```text
/opt/polycryindex-pre/
├── Workspace/
│   ├── backend/
│   │   ├── .env                  ← Auto-generated config (with keys)
│   │   ├── run_prod.py           ← Backend entry point
│   │   ├── users.db              ← User database (auto-created)
│   │   ├── temp/                 ← User uploads
│   │   ├── result/               ← Analysis results
│   │   ├── hdf5/                 ← HDF5 data
│   │   ├── userresult/           ← User-defined results
│   │   ├── workdir/              ← Working directory
│   │   └── figures/              ← Chart output
│   ├── frontend/
│   │   └── dist/                 ← Built frontend
│   ├── fortrancode/
│   │   ├── lm_opt2               ← Main optimizer
│   │   └── lm_postprocess        ← Post-processing program
│   └── fiber_diffraction_indexing/
├── venv/                         ← Python virtual environment
└── logs/                         ← Runtime logs
```

---

## First Deployment

### Linux (root)

```bash
# 1. Clone source code
git clone https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex.git
cd PolymCrystalIndex/deploy/server

# 2. One-click deployment (systemd for long-term running)
sudo APP_PROFILE=cloud DEPLOY_MODE=1 bash ./deploy_linux.sh

# Or standard mode (nohup, suitable for temporary testing)
sudo APP_PROFILE=cloud DEPLOY_MODE=0 bash ./deploy_linux.sh
```

### Linux (current user)

No root privileges required. Installs to `$HOME/.local/share/polycryindex-pre/`:

```bash
cd deploy/server
APP_PROFILE=cloud DEPLOY_MODE=1 bash ./install_user_linux.sh
```

> User-level systemd services do not continue running after logout by default. To enable persistent running:
> ```bash
> sudo loginctl enable-linger $USER
> ```

### macOS

> ⚠️ **WARNING: macOS deployment is NOT officially tested or supported. The following instructions are provided as a reference only and may require manual adjustments.**

macOS does not support systemd; manual deployment is required:

```bash
# 1. Install dependencies
brew install python node gfortran curl

# 2. Clone source code
git clone https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex.git
cd PolymCrystalIndex

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r fiber_diffraction_indexing/requirements.txt

# 4. Compile Fortran
cd fortrancode
gfortran -O2 -o lm_opt2 minpack.f90 lm_opt2.f90
gfortran -O2 -o lm_postprocess out.f90
cd ..

# 5. Build frontend
cd frontend
npm ci
APP_PROFILE=cloud VITE_APP_PROFILE=cloud npm run build
cd ..

# 6. Create runtime directories
mkdir -p backend/{temp,result,hdf5,userresult,workdir,figures}

# 7. Generate config file
cat > backend/.env <<'EOF'
SECRET_KEY=$(openssl rand -hex 32)
DEFAULT_ADMIN_PASSWORD=$(python3 -c "import secrets; print(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789') for _ in range(16)))")
FORTRAN_EXECUTABLE=$(pwd)/fortrancode/lm_opt2
FORTRAN_POSTPROCESS_EXECUTABLE=$(pwd)/fortrancode/lm_postprocess
APP_PROFILE=cloud
APP_ENV=production
HOST=127.0.0.1
PORT=8000
ENABLE_DOCS=false
LOG_LEVEL=warning
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MAX_JOBS=1
OMP_NUM_THREADS=4
UPLOAD_DIR=$(pwd)/backend/temp
RESULT_DIR=$(pwd)/backend/result
HDF5_DIR=$(pwd)/backend/hdf5
USER_RESULT_DIR=$(pwd)/backend/userresult
WORKING_DIR=$(pwd)/backend/workdir
EOF

# 8. Start the service
cd backend
nohup ../venv/bin/python run_prod.py > ../logs/polycryindex.out 2>&1 &
echo $! > ../logs/polycryindex.pid
```

---

## Updating (Upgrade to New Version)

### Update Principles

- When updating code, **user data is automatically preserved** (temp, result, hdf5, userresult, workdir, figures)
- **Secrets and admin password are automatically preserved** (will not be overwritten)
- Other `.env` configuration items will be updated to new version defaults

### Linux Update

```bash
# 1. Pull latest code
cd /path/to/PolymCrystalIndex
git pull

# 2. Re-run the deployment script (user data will be automatically preserved)
cd deploy/server
sudo APP_PROFILE=cloud DEPLOY_MODE=1 bash ./deploy_linux.sh

# The script will automatically:
# - Sync new code (preserving user data directories)
# - Preserve existing SECRET_KEY and admin password
# - Update Python dependencies
# - Recompile Fortran
# - Rebuild frontend
# - Restart the service
```

### macOS Update

> ⚠️ **WARNING: macOS deployment is NOT officially tested or supported. The following instructions are provided as a reference only and may require manual adjustments.**

```bash
# 1. Pull latest code
cd /path/to/PolymCrystalIndex
git pull

# 2. Stop old service
kill $(cat logs/polycryindex.pid)

# 3. Update dependencies
source venv/bin/activate
pip install -r backend/requirements.txt
pip install -r fiber_diffraction_indexing/requirements.txt

# 4. Recompile Fortran
cd fortrancode
gfortran -O2 -o lm_opt2 minpack.f90 lm_opt2.f90
gfortran -O2 -o lm_postprocess out.f90
cd ..

# 5. Rebuild frontend
cd frontend
npm ci
APP_PROFILE=cloud VITE_APP_PROFILE=cloud npm run build
cd ..

# 6. Restart service
cd backend
nohup ../venv/bin/python run_prod.py > ../logs/polycryindex.out 2>&1 &
echo $! > ../logs/polycryindex.pid
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_PROFILE` | Runtime mode | `cloud` (server) |
| `APP_ENV` | Environment identifier | `production` |
| `SECRET_KEY` | JWT signing key | Auto-generated (preserved on update) |
| `DEFAULT_ADMIN_PASSWORD` | Admin initial password | Auto-generated (preserved on update) |
| `HOST` | Listening address | `0.0.0.0` (Linux) / `127.0.0.1` (macOS) |
| `PORT` | Listening port | `8000` |
| `APP_HOST` | Server domain/IP (for CORS) | `0.0.0.0` |
| `FORTRAN_EXECUTABLE` | Main optimizer path | Auto-set |
| `FORTRAN_POSTPROCESS_EXECUTABLE` | Post-processing program path | Auto-set |
| `ENABLE_DOCS` | Expose API docs | `false` |
| `LOG_LEVEL` | Log level | `warning` |
| `MAX_JOBS` | Max parallel tasks | `1` |
| `OMP_NUM_THREADS` | OpenMP thread count | `4` |

---

## Service Management

### systemd (Linux)

```bash
# Check status
sudo systemctl status polycryindex-pre

# View logs
sudo journalctl -u polycryindex-pre -f
sudo journalctl -u polycryindex-pre --since "1 hour ago"

# Restart
sudo systemctl restart polycryindex-pre

# Stop
sudo systemctl stop polycryindex-pre
```

### nohup (Linux / macOS)

```bash
# View logs
tail -f logs/polycryindex.out

# Stop
kill $(cat logs/polycryindex.pid)

# Restart
kill $(cat logs/polycryindex.pid)
cd backend && nohup ../venv/bin/python run_prod.py > ../logs/polycryindex.out 2>&1 &
echo $! > ../logs/polycryindex.pid
```

---

## Health Check

```bash
curl -fsS http://127.0.0.1:8000/health
```

Expected response:
- `status=healthy`
- `profile=cloud`
- `app_env=production`

---

## Uninstallation

### Linux (root)

```bash
cd deploy/server
sudo bash ./uninstall_linux.sh
```

By default, the installation directory `/opt/polycryindex-pre/` will be deleted. To preserve data:

```bash
sudo REMOVE_INSTALL_DIR=0 bash ./uninstall_linux.sh
```

### Linux (user)

```bash
cd deploy/server
bash ./uninstall_user_linux.sh
```

### macOS

> ⚠️ **WARNING: macOS deployment is NOT officially tested or supported. The following instructions are provided as a reference only and may require manual adjustments.**

```bash
# Stop service
kill $(cat logs/polycryindex.pid)

# Delete installation directory
rm -rf /path/to/PolymCrystalIndex
```

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Fortran not found | Check `FORTRAN_EXECUTABLE` path in `backend/.env` |
| Insufficient permissions | Check permissions on `backend/` and `logs/` directories |
| Port in use | `lsof -i :8000` or `ss -ltnp | grep :8000` |
| Frontend 404 | Confirm `frontend/dist/` has been built |
| Health check fails | First run `curl http://127.0.0.1:8000/health`, then check logs |
| CORS errors | Set `APP_HOST` to the server's actual IP or domain |
| Password changed after update | Should not happen — the script automatically preserves existing passwords |

---

## Disk Cleanup

```bash
# Clean temporary upload files
rm -rf /opt/polycryindex-pre/Workspace/backend/temp/*

# Clean user results (use with caution)
rm -rf /opt/polycryindex-pre/Workspace/backend/userresult/*
```

---

## Verification Checklist

- [ ] Browser access to `http://server-ip:8000` loads frontend
- [ ] Registration / login / logout working
- [ ] Data file upload successful
- [ ] Analysis task launched (Fortran called correctly)
- [ ] Task status and logs viewable
- [ ] Results downloadable (zip / hdf5 / cell / miller)
- [ ] Peak extraction working
- [ ] Admin login and backend features working
- [ ] `/health` returns `profile=cloud`
- [ ] Service auto-recovers after restart
- [ ] Browser page refresh does not 404
