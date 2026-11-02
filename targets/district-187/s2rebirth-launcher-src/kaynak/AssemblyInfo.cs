// =====================================================================
//  SURUM VE KIMLIK BILGISI
//
//  Bu nitelikler exe'nin Windows "Ayrintilar" sekmesindeki alanlarini
//  doldurur (Urun adi, Sirket, Aciklama, Surum). Eskiden hepsi BOSTU.
//
//  NEDEN EKLENDI: antivirus motorlari ve SmartScreen, imzasi olmayan bir
//  dosyayi degerlendirirken bu alanlara da bakiyor. Bos surum kaynagi +
//  bos sirket alani + "internetten dosya indirip diske yazma" davranisi,
//  sezgisel puani yukselten klasik ucludur. Alanlari doldurmak imzanin
//  yerini TUTMAZ ama imzayla birlikte tutarli bir kimlik olusturur.
//
//  KURAL: buradaki "Requ" ile kod imzalama sertifikasindaki ad ve
//  kaldirma kaydindaki `Publisher` BIREBIR AYNI kalmali - itibar
//  dosyaya degil, tutarli kimlige birikiyor.
//  Ayrintilar: LAUNCHER\imza\OKUBENI.md
// =====================================================================
using System.Reflection;
using System.Runtime.InteropServices;

[assembly: AssemblyTitle("S2 Son Silah Rebirth Launcher")]
[assembly: AssemblyDescription("S2: Son Silah Rebirth guncelleyici ve baslatici")]
[assembly: AssemblyProduct("S2: Son Silah Rebirth")]
[assembly: AssemblyCompany("Requ")]
[assembly: AssemblyCopyright("Requ · kar amaci gutmeyen hobi projesi")]
[assembly: AssemblyTrademark("")]
[assembly: AssemblyCulture("")]

[assembly: ComVisible(false)]

// Her YAYINDA artir. Geri gitmesi itibar birikimini sifirlar.
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]
