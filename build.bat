@echo off
chcp 65001 >nul
echo ========================================
echo 阴阳师斗技自动挂机 - 打包脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo Python环境正常
echo.

echo [2/3] 安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)
echo 依赖安装完成
echo.

echo [3/3] 打包程序...
pyinstaller --noconfirm --windowed --onefile ^
    --name "阴阳师斗技&御魂自动化工具" ^
    --add-data "templates;templates" ^
    --add-data "logs;logs" ^
    --hidden-import=win32gui ^
    --hidden-import=win32ui ^
    --hidden-import=win32con ^
    --hidden-import=win32api ^
    --hidden-import=win32process ^
    --hidden-import=win32clipboard ^
    --hidden-import=psutil ^
    --hidden-import=pystray ^
    --collect-all pystray ^
    main.py

if %errorlevel% neq 0 (
    echo 错误: 打包失败
    pause
    exit /b 1
)

echo.
echo 复制模板目录到dist...
if not exist "dist\templates" mkdir "dist\templates"
xcopy /E /Y templates\* dist\templates\ >nul

echo.
echo ========================================
echo 打包完成！
echo 可执行文件: dist\阴阳师斗技&御魂自动化工具.exe
echo 模板图片请放入: dist\templates\
echo 操作记录保存在: dist\logs\
echo ========================================
pause
