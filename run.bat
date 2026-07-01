@echo off
chcp 65001 >nul
echo ========================================
echo 阴阳师斗技自动挂机 - 运行脚本
echo ========================================
echo.

python main.py
if %errorlevel% neq 0 (
    echo.
    echo 程序运行出错，请检查错误信息
    pause
)
