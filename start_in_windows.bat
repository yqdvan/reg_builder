@echo off

Title regBuild

Color 0A
:start_in_win

rem set timestamp=%time::=_%
rem set timestamp=%time:~0,2%h%time:~3,2%m%time:~3,2%s
echo.  
echo.  
echo ============================================
echo Reg builder Operation:
echo    1.Help info.
echo    2.Create template registers.xlsm.
echo    3.Generate verilog from registers.xlsm.
echo    4.Debug.
echo. 
set /p n=please input:
cls
if "%n%"=="" cls&goto :start_in_win
if "%n%"=="1" call :1
if "%n%"=="2" call :2
if "%n%"=="3" call :3
if "%n%"=="4" call :4
if /i "%n%"=="n" exit
pause
goto :eof

:1
echo Help info:
rem python reg_builder.py -h
echo. 
echo. 
echo --if already have excle sheet:
echo     step 1. copy xlsm file to this dir;
echo     step 2. click generate button on the xlsm CONFIG page to generate verilog.
echo. 
echo --if not:
echo     step 1. Select '2' to create excle sheet file, default file name is registers.xlsm.
echo     step 2. Edit and save registers.xlsm.
echo     step 2. Select '3' or click generate button on the xlsm CONFIG page to generate verilog.
echo. 
echo. 
goto :start_in_win

:2
echo copy sheet file.
python .\bin\reg_builder.py -t
rem set f_sufix=_registers.xlsm
rem set fName=%timestamp%%f_sufix%
rem copy ".\template\registers.xlsm" .\registers.xlsm
rem echo timestamp is: %timestamp%
rem echo fName is : %fName%
goto :start_in_win

:3
echo generating...
python .\bin\reg_builder.py -f registers.xlsm
goto :start_in_win

:4
echo nothing.
python .\bin\reg_builder.py -d
goto :start_in_win