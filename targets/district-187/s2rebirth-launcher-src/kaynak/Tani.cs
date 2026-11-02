// =====================================================================
//  TANI - KARA KUTU
//
//  HER OTURUMU KAYDEDER, SORUN OLUNCA YOLLAR. Bu ayrim onemli ve
//  olculmus bir sebebi var:
//
//    "ErrorCode : 02" ve "ErrorCode : 03" COKME DEGIL. Istemci
//    `sub_10021340` case 9'da duzgunce `MessageBoxW` gosterip kapaniyor -
//    istisna yok, dolayisiyla dokum de yok, hicbir zaman olmayacak.
//    Yani "cokerse paketle" kurali oyuncularin en cok sikayet ettigi iki
//    hatayi HIC yakalamaz. Kayit her oturumda tutulmali.
//
//  ---- UC KAYNAK, UCU DE OLCULDU -------------------------------------
//
//  1. ClientLog.log        OYUNUN KENDI GUNLUGU
//     `ShowLog` cvar'i 1 iken aciliyor (launcher `+ShowLog 1` geciriyor).
//     Dort kategori: Scaleform->Client, Client->Flash, Server (lobi),
//     Dedi (DEDICATED). Son ikisi ErrorCode 02/03'un gectigi kanallar.
//     Paketleri ADIYLA yaziyor:
//         [GameServer -> Client] tPacket_NLaunch_NLock_SN_ItemList
//         [GameServer -> Client] INVALIED CODE = 221211
//     Boyut: lobi oturumu 24-34 KB. Her acilista sifirlaniyor (fopen
//     modu "wtc"), yani buyumuyor.
//
//  2. Build_731\<MAKINE>\REQUnn.log      OYUNUN KENDI COKME RAPORCUSU
//     `AssertWin32DLL.dll` gercek bir cokmede yaziyor: istisna turu,
//     zaman, surum, CPU/GPU, ve CAGRI YIGINI. 1 KB civari.
//
//  3. REQUnn.dmp                          TAM DOKUM
//     300-500 MB. YOLLANMAZ - yerelde durur, istenirse elle alinir.
//
//  ⚠ RAPOR KLASORUNUN YOLU TUZAKLI: raporcu cikti yolunu kurarken
//  BOSLUKLARI ALT CIZGIYE ceviriyor. Oyun `C:\Danger Zone\...` altindaysa
//  raporlar `C:\Danger_Zone\...` altina dusuyor. Aylarca kimsenin
//  bulamamasinin sebebi buydu; `RaporKlasoru()` bu donusumu yapiyor.
//
//  ---- WER NEDEN YOK -------------------------------------------------
//
//  Windows Error Reporting yolu DENENDI VE BIRAKILDI. Oyunun kendi
//  raporcusu cokmeyi zaten karsiliyor ve WER'e hic sira gelmiyor
//  (olculdu: iki ayri cokmede de raporcunun penceresi cikti, WER olay
//  kaydi olusmadi). Ayrica raporcu 13.08.2026'dan beri, hicbir yama
//  yokken calisiyordu. Bu yuzden ne kayit defteri anahtari ne de
//  istisna suzgeci yamasi gerekiyor.
//
//  ---- NE GONDERILIYOR -----------------------------------------------
//
//  Sikistirilmis paket, tipik 10-40 KB:
//      oturum.json    baslangic/bitis, cikis kodu, sure, surum
//      makine.json    donanim, isletim sistemi, ekran
//      butunluk.txt   onemli dosyalarin SHA-256'si
//      ClientLog.log  oyunun kendi gunlugu
//      cokme\*.log    varsa cokme raporu (dokum DEGIL, yalniz metin)
//
//  Gonderilmeyen: kisisel dosya, ekran goruntusu, tarayici gecmisi,
//  calisan diger programlar, tus kaydi, ve DOKUM DOSYALARI.
//
//  ---- ANAHTAR YOK ---------------------------------------------------
//
//  Bu dosyada gizli anahtar YOK. Launcher portaldan 10 dakikalik, tek
//  nesneye ve tek boyuta bagli, TEK KULLANIMLIK imzali bir bilet alir;
//  paketi Cloudflare Worker'a koyar; Worker bileti dogrulayip R2'ye
//  yazar (kovaya `binding` ile bagli, orada da anahtar yok). Bu programi
//  sokerek elde edilebilecek en fazla sey bilet isteme yoludur.
// =====================================================================
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace S2Launcher
{
    public static class Tani
    {
        /// <summary>Rapor bicimi surumu - sunucu tarafi buna bakarak ayristiriyor.</summary>
        const int SURUM = 2;

        /// <summary>Diskte tutulan oturum sayisi. Eskisi silinir.</summary>
        const int SAKLANAN_OTURUM = 3;

        /// <summary>Diskte tutulan DOKUM sayisi (300-500 MB/adet!).</summary>
        const int SAKLANAN_DOKUM = 2;

        /// <summary>Paket bundan buyukse gonderilmez (portal tavani 96 MB).</summary>
        const long TAVAN = 90L * 1024 * 1024;

        /// <summary>
        /// `ClientLog.log`tan alinacak EN COK bayt (sondan). Gerekce
        /// `KuyrukKopyala` icinde; ozet: hata gunlugun sonundadir ve
        /// olculen normal boyut ~2 MB, 8 MB rahat pay birakir.
        /// </summary>
        const long GUNLUK_TAVANI = 8L * 1024 * 1024;

        /// <summary>
        /// Butunluk raporuna giren dosyalar. Liste BILEREK kisa: oyunun
        /// 1 GB'lik arsivlerini hashlemek dakikalar surer. Buradakiler
        /// bir sorunu aciklayabilecek CALISTIRILABILIR dosyalar.
        /// </summary>
        static readonly string[] BUTUNLUK = {
            "TheRaw.exe",
            "Game/GameClient.dll",
            "Engine_Server.dll",
            "AssertWin32DLL.dll",
            "GameDatabase.dll",
            "S2Launcher.exe",
        };

        // =============================================================
        //  YOLLAR
        // =============================================================
        public static string Klasor(string oyun) { return Path.Combine(oyun, "cokme_raporlari"); }
        static string OturumKok(string oyun) { return Path.Combine(Klasor(oyun), "oturum"); }
        static string BekleyenKlasoru(string oyun) { return Path.Combine(Klasor(oyun), "bekleyen"); }
        static string GonderilenDefteri(string oyun) { return Path.Combine(Klasor(oyun), "gonderilen.txt"); }

        // =============================================================
        //  K-377  MINIDUMP OZETI - fay adresi + modul + RVA
        // =============================================================
        //
        //  NEDEN: cokme raporunun (.log) cagri yigini SEMBOLSUZ. TheRaw.exe
        //  cok az sembol disa aktardigi icin her cerceve en yakin export'a
        //  yuvarlaniyor - hicbir sey ogrenilemiyor. Oysa .dmp icinde istisna
        //  kaydi duruyor ve fay adresi oradan birkac yuz bayt okuyarak cikiyor.
        //
        //  DOSYANIN TAMAMI OKUNMUYOR: yalniz baslik, akis dizini, istisna
        //  akisi ve modul listesi. 300 MB dosyadan ~50 KB.
        //
        //  Sunucu tarafinda ayni cozumleme: EMULATOR/tools/dokum-oku.js
        //
        //  MINIDUMP duzeni (MSDN MINIDUMP_*):
        //     baslik   +0 MDMP  +8 akisSayisi  +12 dizinRva
        //     dizin    her giris 12 bayt: tur(4) boyut(4) rva(4)
        //     tur 4    ModuleList : adet(4) + 108 baytlik kayitlar
        //                 taban(0..7) boyut(8) ... adRva(20)
        //     tur 6    Exception  : iplik(0) hiza(4)
        //                 kod(8) bayrak(12) kayit(16) adres(24)
        //                 parametreSayisi(32) parametreler(40+)
        //     AV-de parametre[0] = 0 okuma / 1 yazma / 8 DEP,
        //           parametre[1] = erisilmek istenen adres.
        static string DokumOzeti(string dmp)
        {
            try
            {
                if (!File.Exists(dmp)) return null;
                using (var f = new FileStream(dmp, FileMode.Open, FileAccess.Read,
                                              FileShare.ReadWrite))
                {
                    byte[] b = Al(f, 0, 32);
                    if (b[0] != (byte)77 || b[1] != (byte)68 ||
                        b[2] != (byte)77 || b[3] != (byte)80) return null;
                    int akisSayisi = BitConverter.ToInt32(b, 8);
                    int dizin = BitConverter.ToInt32(b, 12);
                    if (akisSayisi <= 0 || akisSayisi > 4096) return null;

                    int exRva = 0, mlRva = 0;
                    for (int i = 0; i < akisSayisi; i++)
                    {
                        byte[] g = Al(f, dizin + i * 12, 12);
                        int tur = BitConverter.ToInt32(g, 0);
                        int rva = BitConverter.ToInt32(g, 8);
                        if (tur == 6) exRva = rva;
                        else if (tur == 4) mlRva = rva;
                    }
                    if (exRva == 0) return null;

                    byte[] e = Al(f, exRva, 168);
                    uint kod = BitConverter.ToUInt32(e, 8);
                    ulong adres = BitConverter.ToUInt64(e, 24);
                    int pSay = BitConverter.ToInt32(e, 32);
                    ulong p0 = pSay > 0 ? BitConverter.ToUInt64(e, 40) : 0;
                    ulong p1 = pSay > 1 ? BitConverter.ToUInt64(e, 48) : 0;

                    string modAd = "(bilinmiyor)";
                    ulong modTaban = 0;
                    if (mlRva != 0)
                    {
                        int adet = BitConverter.ToInt32(Al(f, mlRva, 4), 0);
                        for (int i = 0; i < Math.Min(adet, 512); i++)
                        {
                            byte[] m = Al(f, mlRva + 4 + i * 108, 108);
                            ulong taban = BitConverter.ToUInt64(m, 0);
                            uint boyut = BitConverter.ToUInt32(m, 8);
                            if (adres < taban || adres >= taban + boyut) continue;
                            modTaban = taban;
                            int adRva = BitConverter.ToInt32(m, 20);
                            int uz = BitConverter.ToInt32(Al(f, adRva, 4), 0);
                            if (uz > 0 && uz < 4096)
                                modAd = Path.GetFileName(
                                    Encoding.Unicode.GetString(Al(f, adRva + 4, uz)));
                            break;
                        }
                    }

                    string ihlal = kod == 0xC0000005
                        ? (p0 == 0 ? "OKUMA" : p0 == 1 ? "YAZMA" : p0 == 8 ? "DEP" : "?")
                          + " -> 0x" + p1.ToString("x8")
                        : "-";

                    var sb = new StringBuilder();
                    sb.Append("dosya   : ").Append(Path.GetFileName(dmp)).Append("\r\n");
                    sb.Append("istisna : 0x").Append(kod.ToString("x8")).Append("\r\n");
                    sb.Append("ihlal   : ").Append(ihlal).Append("\r\n");
                    sb.Append("adres   : 0x").Append(adres.ToString("x8")).Append("\r\n");
                    sb.Append("modul   : ").Append(modAd).Append("\r\n");
                    sb.Append("taban   : 0x").Append(modTaban.ToString("x8")).Append("\r\n");
                    sb.Append("RVA     : 0x").Append((adres - modTaban).ToString("x8")).Append("\r\n");
                    return sb.ToString();
                }
            }
            catch { return null; }
        }

        /// <summary>Dokumden konumdan uzunluk kadar bayt okur.</summary>
        static byte[] Al(FileStream f, long konum, int uzunluk)
        {
            byte[] b = new byte[uzunluk];
            f.Position = konum;
            int okundu = 0;
            while (okundu < uzunluk)
            {
                int n = f.Read(b, okundu, uzunluk - okundu);
                if (n <= 0) break;
                okundu += n;
            }
            return b;
        }

        /// <summary>
        /// Oyunun COKME RAPORCUSUNUN yazdigi klasor.
        ///
        /// ⚠ Raporcu yolu kurarken BOSLUKLARI ALT CIZGIYE ceviriyor:
        ///     C:\Danger Zone\...\S2SonSilah
        ///  -> C:\Danger_Zone\...\S2SonSilah\Build_731\<MAKINE>\
        /// Olculdu: 11 rapor aylarca orada birikmis, kimse bulamamis.
        /// </summary>
        public static string RaporKlasoru(string oyun)
        {
            string bosluksuz = oyun.Replace(' ', '_');
            return Path.Combine(bosluksuz, "Build_731", Environment.MachineName);
        }

        /// <summary>Tani acik mi - adres yoksa ya da oyuncu kapattiysa hayir.</summary>
        public static bool Acik(Ayarlar a)
        {
            return a != null && !string.IsNullOrEmpty(a.Tani) && a.TaniGonder;
        }

        // =============================================================
        //  SEANS
        // =============================================================
        public class Seans
        {
            public string OyunKlasoru;
            public Ayarlar Ayar;
            public DateTime Basladi;
            public string Kimlik;
            public HashSet<string> OncekiRaporlar;
            /// <summary>Ag izi ornekleyicisi - null olabilir ([[AgIzi]]).</summary>
            public AgIzi Iz;
        }

        static HashSet<string> RaporListesi(string oyun)
        {
            var kume = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            try
            {
                string k = RaporKlasoru(oyun);
                if (Directory.Exists(k))
                    foreach (string d in Directory.GetFiles(k, "*.log")) kume.Add(Path.GetFileName(d));
            }
            catch { }
            return kume;
        }

        /// <summary>Oyun acilmadan HEMEN once.</summary>
        public static Seans Basla(string oyun, Ayarlar ayar)
        {
            var s = new Seans
            {
                OyunKlasoru = oyun,
                Ayar = ayar,
                Basladi = DateTime.UtcNow,
                Kimlik = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture),
                OncekiRaporlar = RaporListesi(oyun)
            };
            try { OkubeniYaz(oyun); } catch { }
            return s;
        }

        /// <summary>
        /// Oyun kapandiktan sonra. Kayit HER ZAMAN tutulur; gonderim
        /// yalnizca sorun isareti varsa. HICBIR KOSULDA disari istisna
        /// atmaz - launcher'in kapanis yolunu bozmasi kabul edilemez.
        /// </summary>
        /// <summary>
        /// AG IZINI BASLAT. `Basla`dan AYRI cagriliyor cunku oyun sureci
        /// o an henuz yok - `Process.Start` bir satir SONRA donuyor.
        ///
        /// Iz dogrudan OTURUM KLASORUNE yaziyor; `Paketle` zaten klasorun
        /// tamamini zipliyor, ayrica kopyalama gerekmiyor.
        ///
        /// ⚠ Firlatmaz. Basarisiz olursa oturum ag izi olmadan devam eder.
        /// </summary>
        public static void AgIziBasla(Seans s, Process oyun)
        {
            try
            {
                if (s == null || oyun == null || !Acik(s.Ayar)) return;
                string klasor = Path.Combine(OturumKok(s.OyunKlasoru), s.Kimlik);
                s.Iz = AgIzi.Basla(klasor, oyun);
            }
            catch { }
        }

        public static void Bitir(Seans s, int cikisKodu)
        {
            try
            {
                if (s == null || !Acik(s.Ayar)) return;

                // ⚠ IZ ONCE DURSUN: hala yaziyorken zipleseydik dosya
                //   yarim kalirdi. `Bitir` en fazla 1 sn bekliyor.
                try { if (s.Iz != null) s.Iz.Bitir(); } catch { }

                // Yeni cokme raporu belirdi mi?
                var simdiki = RaporListesi(s.OyunKlasoru);
                simdiki.ExceptWith(s.OncekiRaporlar);
                var yeniRaporlar = new List<string>(simdiki);
                yeniRaporlar.Sort();

                string klasor = Topla(s, cikisKodu, yeniRaporlar);
                Saklama(s.OyunKlasoru);
                if (klasor == null) return;

                string sebep = SorunSebebi(s, cikisKodu, yeniRaporlar, klasor);
                if (sebep == null) return;

                string paket = Paketle(s, klasor, sebep);
                if (paket != null) Gonder(s.OyunKlasoru, s.Ayar, paket);
            }
            catch { }
        }

        /// <summary>
        /// Oturumu SINIFLANDIRIR. HER oturum gonderiliyor - burasi yalnizca
        /// "ne oldu" etiketini koyuyor.
        ///
        /// ---- HER OTURUM NEDEN --------------------------------------------
        ///
        /// Ilk tasarim "yalnizca sorun olunca yolla" idi. Iki olcum onu
        /// degistirdi:
        ///
        ///  1. BOYUT. Bir mac oturumunun gunlugu, gurultulu kategori
        ///     kapatildiktan sonra 1.3 MB; sikistirilmis 140 KB. 100 oyuncu
        ///     gunde 3 oturum oynasa gunde 60 MB, 30 gunluk saklamayla
        ///     duragan halde ~1.8 GB. Bedeli yok denecek kadar az.
        ///
        ///  2. SORUNSUZ OTURUM DA VERIDIR. Neyin ANORMAL oldugunu ancak
        ///     normalin neye benzedigini bilirsek anlariz. Yalnizca hatali
        ///     oturumlari toplarsak karsilastirma grubumuz hic olmaz.
        ///
        /// ⚠ Bu karar OYUNCUYA SOYLENEN metni de degistirdi: `OKUBENI.txt`
        /// ve `launcher.cfg` artik "her oturum gonderilir" diyor. Ikisi
        /// ayrisirsa soyledigimizle yaptigimiz ayrisir - degistirirken
        /// UCUNU BIRLIKTE degistir.
        /// </summary>
        static string SorunSebebi(Seans s, int cikisKodu, List<string> yeniRaporlar, string klasor)
        {
            if (yeniRaporlar.Count > 0) return "cokme";
            if (cikisKodu != 0) return "cikis-kodu-" + cikisKodu;

            // ErrorCode 02/03 cokmuyor, cikis kodu da temiz. Tek izi
            // oyunun kendi gunlugundeki baglanti hatasi satirlari:
            //     [ ClientConnect - eClientConnectionState_Error - ... ]
            // On daldan DOKUZU bunu basiyor. Case 9 (= ErrorCode 03)
            // basmiyor, ama 02 dahil digerleri basiyor - o yuzden bu
            // etiket 03'u kacirir, digerlerini yakalar. 03'un tespiti
            // sunucu tarafinda (`tani-defteri.js`) ve Dedi kanalinda.
            try
            {
                string g = Path.Combine(klasor, "ClientLog.log");
                if (File.Exists(g))
                {
                    foreach (string satir in File.ReadLines(g))
                        if (satir.Contains("eClientConnectionState_Error")) return "baglanti-hatasi";
                }
            }
            catch { }
            return "normal";
        }

        // =============================================================
        //  TOPLAMA
        // =============================================================
        static string Topla(Seans s, int cikisKodu, List<string> yeniRaporlar)
        {
            try
            {
                string klasor = Path.Combine(OturumKok(s.OyunKlasoru), s.Kimlik);
                Directory.CreateDirectory(klasor);

                var oturum = new Dictionary<string, object>
                {
                    { "surum", SURUM },
                    { "kimlik", s.Kimlik },
                    { "basladi", s.Basladi.ToString("o", CultureInfo.InvariantCulture) },
                    { "bitti", DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture) },
                    { "sureSn", Math.Round((DateTime.UtcNow - s.Basladi).TotalSeconds, 1) },
                    { "cikisKodu", cikisKodu },
                    { "launcher", Surum() },
                    { "paket", PaketAdi(s.OyunKlasoru) },
                    { "sunucu", s.Ayar.Ip + ":" + s.Ayar.Port },
                    { "yeniCokmeRaporu", yeniRaporlar.ToArray() },
                };
                Yaz(Path.Combine(klasor, "oturum.json"),
                    new JavaScriptSerializer().Serialize(oturum));
                Yaz(Path.Combine(klasor, "makine.json"),
                    new JavaScriptSerializer().Serialize(MakineBilgisi()));
                Yaz(Path.Combine(klasor, "butunluk.txt"), Butunluk(s.OyunKlasoru));

                // Oyunun kendi gunlugu - bir sonraki acilista SIFIRLANIYOR,
                // o yuzden simdi kopyalanmali. YALNIZ SONU alinir: hata
                // her zaman gunlugun sonundadir, basi degil.
                KuyrukKopyala(Path.Combine(s.OyunKlasoru, "ClientLog.log"),
                    Path.Combine(klasor, "ClientLog.log"), GUNLUK_TAVANI);
                Kopyala(s.OyunKlasoru, "error.log", klasor);
                // 14.10.2026: ANTI-HILE KOPRUSUNUN GUNLUGU (ApexKanal.cs).
                // "Launcher'la aciyorum ama sunucu kalp gormuyor" sikayetinin
                // tek kaniti bu dosya: kanal acildi mi, POST neden dustu
                // (HTTP kodu / zaman asimi), kac kalp okundu. Oyun klasorunde
                // degil %LOCALAPPDATA%\S2Rebirth altinda durdugu icin pakete
                // girmiyordu; destek her seferinde elle istiyordu.
                try
                {
                    string kopru = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                        "S2Rebirth", "apex-kopru.log");
                    if (File.Exists(kopru))
                        KuyrukKopyala(kopru, Path.Combine(klasor, "apex-kopru.log"), GUNLUK_TAVANI);
                }
                catch { }
                Kopyala(s.OyunKlasoru, "settings.cfg", klasor);

                // Cokme raporunun METNI (dokum DEGIL - o 300 MB).
                if (yeniRaporlar.Count > 0)
                {
                    string ck = Path.Combine(klasor, "cokme");
                    Directory.CreateDirectory(ck);
                    string kaynak = RaporKlasoru(s.OyunKlasoru);
                    foreach (string ad in yeniRaporlar)
                    {
                        try { File.Copy(Path.Combine(kaynak, ad), Path.Combine(ck, ad), true); }
                        catch { }
                    }
                    // K-377: DOKUMUN OZETI. Dosyanin kendisi 300-500 MB ve
                    // yollanmiyor - ama icindeki TEK ise yarar bilgi birkac
                    // yuz bayt: fay adresi + modul + RVA. Cokme raporunun
                    // metin yigini SEMBOLSUZ (her cerceve "SetMasterDatabase"
                    // diye yuvarlaniyor) ve hicbir sey ogretmiyor; RVA ise
                    // dogrudan fonksiyonu veriyor.
                    foreach (string ad in yeniRaporlar)
                    {
                        string dmp = Path.Combine(kaynak,
                            Path.GetFileNameWithoutExtension(ad) + ".dmp");
                        string ozet = DokumOzeti(dmp);
                        if (ozet == null) continue;
                        try
                        {
                            File.WriteAllText(Path.Combine(ck,
                                Path.GetFileNameWithoutExtension(ad) + ".ozet.txt"),
                                ozet, new UTF8Encoding(false));
                        }
                        catch { }
                    }
                }
                return klasor;
            }
            catch { return null; }
        }

        static string Butunluk(string oyun)
        {
            var sb = new StringBuilder();
            sb.AppendLine("# <sha256>  <boyut>  <degistirilme UTC>  <yol>");
            foreach (string bagil in BUTUNLUK)
            {
                string tam = Path.Combine(oyun, bagil.Replace('/', '\\'));
                if (!File.Exists(tam)) { sb.AppendLine("YOK  -  -  " + bagil); continue; }
                try
                {
                    var b = new FileInfo(tam);
                    sb.AppendLine(Guncelleyici.HashHesapla(tam) + "  " + b.Length + "  "
                        + b.LastWriteTimeUtc.ToString("o", CultureInfo.InvariantCulture)
                        + "  " + bagil);
                }
                catch (Exception e) { sb.AppendLine("HATA  -  -  " + bagil + "  " + e.Message); }
            }
            return sb.ToString();
        }

        // =============================================================
        //  SAKLAMA - disk sismesin
        //
        //  Iki ayri tavan, hangisi once dolarsa o keser:
        //     oturum klasoru : en yeni 3
        //     DOKUM dosyasi  : en yeni 2   (300-500 MB/adet)
        //  Cokme raporunun METNI (1 KB) SILINMEZ - gecmis onda duruyor.
        // =============================================================
        static void Saklama(string oyun)
        {
            try
            {
                var kok = new DirectoryInfo(OturumKok(oyun));
                if (kok.Exists)
                {
                    var liste = new List<DirectoryInfo>(kok.GetDirectories());
                    liste.Sort((a, b) => string.CompareOrdinal(b.Name, a.Name));
                    for (int i = SAKLANAN_OTURUM; i < liste.Count; i++)
                        try { liste[i].Delete(true); } catch { }
                }
            }
            catch { }

            try
            {
                var rapor = new DirectoryInfo(RaporKlasoru(oyun));
                if (!rapor.Exists) return;
                var dokumler = new List<FileInfo>(rapor.GetFiles("*.dmp"));
                dokumler.Sort((a, b) => b.LastWriteTimeUtc.CompareTo(a.LastWriteTimeUtc));
                for (int i = SAKLANAN_DOKUM; i < dokumler.Count; i++)
                    try { dokumler[i].Delete(); } catch { }
            }
            catch { }
        }

        // =============================================================
        //  OKUBENI - oyuncu icine bakabilsin
        // =============================================================
        static void OkubeniYaz(string oyun)
        {
            string yol = Path.Combine(Klasor(oyun), "OKUBENI.txt");
            Directory.CreateDirectory(Klasor(oyun));
            if (File.Exists(yol)) return;
            File.WriteAllText(yol,
                "S2: SON SILAH - TANI KAYITLARI\r\n" +
                "=====================================================\r\n\r\n" +
                "Bu klasorde oyunun her acilisinda bir kayit tutulur. Amaci tek\r\n" +
                "sey: oyun coktugunde ya da seni maçtan attiginda sebebini\r\n" +
                "bulabilmek. Icine bakabilirsin, hepsi duz metindir.\r\n\r\n" +
                "oturum\\<tarih>\\\r\n" +
                "    oturum.json    ne zaman acildi/kapandi, ne kadar surdu\r\n" +
                "    makine.json    islemci, ekran karti, isletim sistemi, ekran\r\n" +
                "    butunluk.txt   oyun dosyalarinin parmak izleri\r\n" +
                "    ClientLog.log  oyunun kendi tuttugu gunluk\r\n" +
                "    cokme\\         cokme olduysa raporun metni\r\n\r\n" +
                "EN YENI " + SAKLANAN_OTURUM + " OTURUM saklanir, eskisi silinir.\r\n" +
                "Cokme dokumleri (buyuk dosyalar) en yeni " + SAKLANAN_DOKUM + " tanesi kalir.\r\n\r\n" +
                "NE GONDERILIYOR\r\n" +
                "---------------\r\n" +
                "Oyunu her kapattiginda yukaridaki metin dosyalari sikistirilip\r\n" +
                "sunucuya yollanir. Tipik boyut 150 KB.\r\n\r\n" +
                "EVET, SORUN OLMASA DA GONDERILIYOR. Sebebi su: bir seyin\r\n" +
                "BOZUK oldugunu ancak duzgun calisirken neye benzedigini\r\n" +
                "bilirsek anlayabiliyoruz. Yalnizca hatali oturumlari\r\n" +
                "toplasaydik karsilastiracak bir sey olmazdi.\r\n\r\n" +
                "NE GONDERILMIYOR\r\n" +
                "----------------\r\n" +
                "Kisisel dosyalarin, ekran goruntusu, tarayici gecmisi, calisan\r\n" +
                "diger programlarin listesi, tus kaydi. Ve cokme dokumleri -\r\n" +
                "onlar buyuk oldugu icin yalnizca senin bilgisayarinda kalir.\r\n\r\n" +
                "KAPATMAK ICIN\r\n" +
                "-------------\r\n" +
                "Oyun klasorundeki launcher-ozel.cfg dosyasina su satiri ekle:\r\n" +
                "    tani_gonder = 0\r\n",
                new UTF8Encoding(false));
        }

        // =============================================================
        //  PAKETLEME VE GONDERIM
        // =============================================================
        static string Paketle(Seans s, string oturumKlasoru, string sebep)
        {
            try
            {
                Yaz(Path.Combine(oturumKlasoru, "sebep.txt"), sebep);
                string bekleyen = BekleyenKlasoru(s.OyunKlasoru);
                Directory.CreateDirectory(bekleyen);
                string hedef = Path.Combine(bekleyen, s.Kimlik + ".s2tani");
                if (File.Exists(hedef)) File.Delete(hedef);
                ZipFile.CreateFromDirectory(oturumKlasoru, hedef, CompressionLevel.Optimal, false);
                if (new FileInfo(hedef).Length > TAVAN) { File.Delete(hedef); return null; }
                return hedef;
            }
            catch { return null; }
        }

        /// <summary>
        /// Onceki seanstan kalan paketleri yollar. Makine kapandiysa, ag
        /// yoksa ya da launcher olduyse paket diskte bekliyor olabilir.
        /// </summary>
        public static void ArtiklariGonder(string oyun, Ayarlar ayar)
        {
            try
            {
                if (!Acik(ayar)) return;
                string k = BekleyenKlasoru(oyun);
                if (!Directory.Exists(k)) return;
                foreach (string p in Directory.GetFiles(k, "*.s2tani")) Gonder(oyun, ayar, p);
            }
            catch { }
        }

        static void Gonder(string oyun, Ayarlar ayar, string paket)
        {
            try
            {
                if (!File.Exists(paket)) return;
                byte[] govde = File.ReadAllBytes(paket);
                if (govde.Length <= 0 || govde.Length > TAVAN) { File.Delete(paket); return; }

                ServicePointManager.SecurityProtocol =
                    SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11;

                // ---- 1. bilet ------------------------------------------
                string cevap;
                using (var wc = new WebClient())
                {
                    wc.Headers[HttpRequestHeader.ContentType] = "application/json";
                    wc.Encoding = Encoding.UTF8;
                    cevap = wc.UploadString(ayar.Tani, "POST", "{\"boyut\":" + govde.Length + "}");
                }
                var b = (Dictionary<string, object>)new JavaScriptSerializer().DeserializeObject(cevap);
                string adres = Convert.ToString(b["adres"]);
                string bilet = Convert.ToString(b["bilet"]);
                if (string.IsNullOrEmpty(adres) || string.IsNullOrEmpty(bilet)) return;

                // ---- 2. paket ------------------------------------------
                var istek = (HttpWebRequest)WebRequest.Create(adres);
                istek.Method = "PUT";
                istek.ContentType = "application/octet-stream";
                istek.ContentLength = govde.Length;   // Worker bunu bilete karsi olcuyor
                istek.Headers.Add("X-Tani-Bilet", bilet);
                // ⚠ Rakam ayiraci (30_000) KULLANMA: derleyici v4.0.30319
                // csc.exe ve o C# 5 - ayirac C# 7 ozelligi.
                istek.Timeout = 30000;
                istek.ReadWriteTimeout = 300000;
                istek.AllowWriteStreamBuffering = false;
                using (Stream akis = istek.GetRequestStream()) akis.Write(govde, 0, govde.Length);
                using (var y = (HttpWebResponse)istek.GetResponse())
                {
                    if (y.StatusCode == HttpStatusCode.OK)
                    {
                        File.Delete(paket);
                        try
                        {
                            File.AppendAllText(GonderilenDefteri(oyun),
                                DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture)
                                + "  " + Path.GetFileName(paket) + "\r\n");
                        }
                        catch { }
                    }
                }
            }
            catch (WebException we)
            {
                // 4xx = tekrar denemenin faydasi yok (bilet suresi gecmis,
                // tavan asilmis, uc kapali) -> paketi sil. 5xx / ag hatasi
                // ise BIRAK; bir dahaki aciliste `ArtiklariGonder` dener.
                try
                {
                    var y = we.Response as HttpWebResponse;
                    if (y != null && (int)y.StatusCode >= 400 && (int)y.StatusCode < 500)
                        File.Delete(paket);
                }
                catch { }
            }
            catch { }
        }

        // =============================================================
        //  YARDIMCILAR
        // =============================================================
        static void Yaz(string yol, string metin)
        {
            try { File.WriteAllText(yol, metin, new UTF8Encoding(false)); } catch { }
        }

        /// <summary>
        /// Buyuk gunlugun YALNIZ SONUNU kopyalar.
        ///
        /// NEDEN: hata her zaman gunlugun SONUNDADIR. 17.08.2026 olcumu -
        /// dort kategori acikken bir mac oturumu 88 MB oldu ve %97.6'si
        /// tek bir satirdi (`inGame.minimap.mapImageMove`, her karede).
        /// O kategori artik kapali ve gunluk ~2 MB'a dustu, ama uzun bir
        /// oturum yine sisebilir - bu tavan onun emniyet supabi.
        ///
        /// Kesme noktasi satir basina hizalanir, yoksa ilk satir yarim
        /// baslar ve ayristirici yaniltir.
        /// </summary>
        static void KuyrukKopyala(string kaynak, string hedef, long tavan)
        {
            try
            {
                if (!File.Exists(kaynak)) return;
                var bilgi = new FileInfo(kaynak);
                using (var g = new FileStream(kaynak, FileMode.Open, FileAccess.Read,
                           FileShare.ReadWrite | FileShare.Delete))
                using (var c = new FileStream(hedef, FileMode.Create, FileAccess.Write))
                {
                    bool kirpildi = bilgi.Length > tavan;
                    if (kirpildi)
                    {
                        g.Seek(bilgi.Length - tavan, SeekOrigin.Begin);
                        // Yarim satiri at.
                        int b;
                        while ((b = g.ReadByte()) != -1 && b != '\n') { }
                        byte[] not = Encoding.UTF8.GetBytes(
                            "### BU DOSYA KIRPILDI - kaynak " + bilgi.Length
                            + " bayt, son " + tavan + " bayt alindi ###\r\n");
                        c.Write(not, 0, not.Length);
                    }
                    g.CopyTo(c);
                }
            }
            catch { }
        }

        static void Kopyala(string kok, string bagil, string hedefKlasor)
        {
            try
            {
                string tam = Path.Combine(kok, bagil);
                if (!File.Exists(tam)) return;
                File.Copy(tam, Path.Combine(hedefKlasor, Path.GetFileName(bagil)), true);
            }
            catch { }
        }

        static string PaketAdi(string oyun)
        {
            try
            {
                string y = Path.Combine(oyun, @".launcher\paket.json");
                if (!File.Exists(y)) return "?";
                var d = (Dictionary<string, object>)new JavaScriptSerializer()
                    .DeserializeObject(File.ReadAllText(y));
                return Convert.ToString(d["paket"]);
            }
            catch { return "?"; }
        }

        static string Surum()
        {
            try
            {
                string yol = System.Reflection.Assembly.GetExecutingAssembly().Location;
                return FileVersionInfo.GetVersionInfo(yol).FileVersion
                    + " (" + new FileInfo(yol).LastWriteTimeUtc.ToString("yyyy-MM-dd") + ")";
            }
            catch { return "?"; }
        }

        // ---- makine bilgisi ------------------------------------------
        [StructLayout(LayoutKind.Sequential)]
        class MEMORYSTATUSEX
        {
            public uint dwLength = (uint)Marshal.SizeOf(typeof(MEMORYSTATUSEX));
            public uint dwMemoryLoad;
            public ulong ullTotalPhys, ullAvailPhys, ullTotalPageFile, ullAvailPageFile,
                         ullTotalVirtual, ullAvailVirtual, ullAvailExtendedVirtual;
        }

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        static extern bool GlobalMemoryStatusEx([In, Out] MEMORYSTATUSEX lpBuffer);

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        struct DISPLAY_DEVICE
        {
            public int cb;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceString;
            public int StateFlags;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceID;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceKey;
        }

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern bool EnumDisplayDevices(string lpDevice, uint iDevNum,
            ref DISPLAY_DEVICE lpDisplayDevice, uint dwFlags);

        /// <summary>
        /// ⚠ Oyunun kendi raporundaki OSInfo ve MemoryInfo YANLIS
        /// (Windows 11'de "Windows7_OR_Vista", RAM sabit 2048MB). Tespit
        /// kodu 2011'den kalma. Dogrusunu burada olcuyoruz.
        /// </summary>
        static Dictionary<string, object> MakineBilgisi()
        {
            var d = new Dictionary<string, object>();
            try
            {
                d["os"] = Environment.OSVersion.VersionString;
                d["x64"] = Environment.Is64BitOperatingSystem;
                d["cekirdek"] = Environment.ProcessorCount;
                d["clr"] = Environment.Version.ToString();
                d["dil"] = CultureInfo.CurrentUICulture.Name;
                d["saatDilimi"] = TimeZoneInfo.Local.Id;
            }
            catch { }
            try
            {
                var m = new MEMORYSTATUSEX();
                if (GlobalMemoryStatusEx(m))
                {
                    d["ramMb"] = (long)(m.ullTotalPhys / (1024 * 1024));
                    d["ramBosMb"] = (long)(m.ullAvailPhys / (1024 * 1024));
                }
            }
            catch { }
            try
            {
                using (var k = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(
                    @"HARDWARE\DESCRIPTION\System\CentralProcessor\0"))
                    if (k != null) d["cpu"] = Convert.ToString(k.GetValue("ProcessorNameString"));
            }
            catch { }
            try
            {
                var gpu = new List<string>();
                for (uint i = 0; i < 8; i++)
                {
                    var dd = new DISPLAY_DEVICE();
                    dd.cb = Marshal.SizeOf(typeof(DISPLAY_DEVICE));
                    if (!EnumDisplayDevices(null, i, ref dd, 0)) break;
                    if (!string.IsNullOrEmpty(dd.DeviceString) && !gpu.Contains(dd.DeviceString))
                        gpu.Add(dd.DeviceString);
                }
                d["gpu"] = gpu.ToArray();
            }
            catch { }
            try
            {
                var e = Screen.PrimaryScreen.Bounds;
                d["ekran"] = e.Width + "x" + e.Height;
                d["ekranSayisi"] = Screen.AllScreens.Length;
            }
            catch { }
            try
            {
                var s = new DriveInfo(Path.GetPathRoot(
                    System.Reflection.Assembly.GetExecutingAssembly().Location));
                d["diskBosGb"] = Math.Round(s.AvailableFreeSpace / 1024.0 / 1024 / 1024, 1);
            }
            catch { }
            return d;
        }
    }
}
