@echo off
rem ===================================================================
rem  S2 LAUNCHER - DERLEME
rem
rem  Bu betik launcher'i KENDI BILGISAYARINIZDA derler.
rem  Hicbir sey indirmez, hicbir sey kurmaz, internete cikmaz.
rem
rem  Kullandigi derleyici Windows'un icinde HAZIR gelir:
rem      C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
rem  Yani kimseye ait bir arac indirmeniz gerekmiyor.
rem
rem  ---- CIKTI NEREYE GIDER --------------------------------------------
rem
rem    derle.cmd          cikti:  ..\S2Launcher.exe        (oyunun launcher'i)
rem    derle.cmd -ozel    cikti:  ..\S2Launcher-ozel.exe   (ayri kopya)
rem
rem  Ikisinin farki:
rem    * Parametresiz derlerseniz oyunun launcher'ini DEGISTIRIRSINIZ.
rem      Bir sonraki guncellemede resmi surum geri gelir ve sizinki gider.
rem    * "-ozel" ile derlerseniz ayri bir dosya olusur; guncelleme ona
rem      ASLA dokunmaz, kalici olur. Oyunu o dosyayla acarsiniz.
rem  Ayrintilar icin OKUBENI.md.
rem
rem  NOT (gelistirici): bu dosyada ">" karakteri KULLANMAYIN. cmd.exe onu
rem  echo ve rem satirlarinda bile yonlendirme sayar; "TAMAM -> dosya.exe"
rem  yazmak derlenen exe'nin uzerine metin yazip bozuyordu.
rem ===================================================================
setlocal
cd /d "%~dp0"

set "CIKTI=..\S2Launcher.exe"
set "KIP=Oyunun launcher'i (guncellemede resmi surum geri gelir)"
if /i "%~1"=="-ozel" (
  set "CIKTI=..\S2Launcher-ozel.exe"
  set "KIP=OZEL kopya (guncelleme bu dosyaya dokunmaz)"
)
if /i "%~1"=="ozel" (
  set "CIKTI=..\S2Launcher-ozel.exe"
  set "KIP=OZEL kopya (guncelleme bu dosyaya dokunmaz)"
)

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo.
  echo   HATA: .NET Framework derleyicisi bulunamadi.
  echo   Beklenen yer: %%WINDIR%%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
  echo   Windows 10/11'de bu dosya hazir gelir; yoksa .NET Framework 4.8 kurun.
  echo.
  pause
  exit /b 1
)

echo.
echo   Kip       : %KIP%
echo   Derleyici : %CSC%
echo   Cikti     : %CIKTI%
echo.

"%CSC%" /nologo /target:winexe /platform:anycpu /optimize+ ^
  /out:"%CIKTI%" ^
  /win32manifest:"kaynak\app.manifest" ^
  /win32icon:"kaynak\s2.ico" ^
  /r:System.dll ^
  /r:System.Core.dll ^
  /r:System.Drawing.dll ^
  /r:System.Windows.Forms.dll ^
  /r:System.Web.Extensions.dll ^
  /r:System.IO.Compression.dll ^
  /r:System.IO.Compression.FileSystem.dll ^
  "kaynak\Program.cs" "kaynak\Guncelleyici.cs" "kaynak\AnaPencere.cs" ^
  "kaynak\Tani.cs" "kaynak\AgIzi.cs" "kaynak\ApexKanal.cs" "kaynak\AssemblyInfo.cs" "kaynak\DiscordVarlik.cs" "kaynak\KumHavuzu.cs"

if errorlevel 1 (
  echo.
  echo   DERLEME BASARISIZ.
  echo.
  pause
  exit /b 1
)

echo.
echo   TAMAM. Uretilen dosya: %CIKTI%
echo.

rem ---- IMZALA (yalnizca GELISTIRME agacinda, sertifika ayarliysa) -----
rem Oyuncunun kopyasinda LAUNCHER\ klasoru yok; asagidaki yol tutmaz ve
rem satir sessizce atlanir. Yani bu satir oyuncunun derlemesini bozmaz.
rem
rem !! SIRA ONEMLI !!  Once derle, sonra IMZALA, EN SON yayin-hazirla.
rem Imza dosyayi degistiriyor; manifest hash'i imzadan SONRA hesaplanmali,
rem yoksa launcher kendi kendini sonsuz dongude guncellemeye calisir.
if exist "..\..\LAUNCHER\imza\imzala.cmd" call "..\..\LAUNCHER\imza\imzala.cmd" "%~dp0%CIKTI%"
echo   Bu SIZIN derlemenizin parmak izi. Kendi kopyaniz sonradan degisti mi
echo   diye bakmak icin bir kenara yazabilirsiniz.
echo   NOT: paylasilan S2Launcher.exe ile AYNI CIKMAZ - normaldir. Derleyici
echo   her derlemeye ayri bir kimlik gomuyor, ayni kaynak farkli bayt uretir.
powershell -NoProfile -Command "(Get-FileHash '%CIKTI%' -Algorithm SHA256).Hash" 2>nul
echo.
pause
