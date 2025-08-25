@echo off
echo Updating GitHub...

git -C C:\Users\thysd\Code\Botrecove add .
git -C C:\Users\thysd\Code\Botrecove commit -m "Automated update"
git -C C:\Users\thysd\Code\Botrecove push

echo Update complete.
pause