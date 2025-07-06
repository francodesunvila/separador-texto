@echo off
echo 🧹 Eliminando blobs grandes (>100MB) con git-filter-repo...

REM Si usás pip para instalar la herramienta
python -m git_filter_repo --strip-blobs-bigger-than 100M

REM Limpieza del historial
git reflog expire --expire=now --all
git gc --prune=now --aggressive

REM Push forzado al remoto
git push --force --set-upstream origin main

echo ✅ Repositorio limpiado y empujado a GitHub.
pause