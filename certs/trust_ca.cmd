@echo off

net session >nul 2>&1
if /I %errorLevel% NEQ 0 (
	echo Administrator privilege required
	exit
)

certutil.exe -addstore root ca.crt
pause
